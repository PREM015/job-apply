"""Bounded GET-only HTTP client with robots, pacing, and request accounting."""
from __future__ import annotations

import time
from collections import defaultdict
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

from .models import FetchResult

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
TRANSIENT_STATUSES = {500, 502, 503, 504}
MAX_REDIRECTS = 5


class HttpClient:
    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 1,
        per_host_delay: float = 1.0,
        request_cap: int = 20,
        user_agent: str = "JobAgent/1.0 (public job listing discovery; GET-only)",
        session: requests.Session | None = None,
    ):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if per_host_delay < 0:
            raise ValueError("per_host_delay cannot be negative")
        if request_cap < 0:
            raise ValueError("request_cap cannot be negative")
        if not user_agent.strip():
            raise ValueError("user_agent must not be empty")

        self.timeout = timeout
        self.max_retries = min(max_retries, 1)
        self.per_host_delay = per_host_delay
        self.request_cap = request_cap
        self.user_agent = user_agent
        self.session = session or requests.Session()
        self.requests_made = 0
        self.request_ledger: list[dict[str, int | str | None]] = []
        self.robots_skips: list[dict[str, str]] = []
        self._last_host_time: dict[str, float] = {}
        self._blocked_hosts: set[str] = set()
        self._blocked_status_count: dict[str, int] = defaultdict(int)
        self._blocked_statuses: dict[str, list[int]] = defaultdict(list)
        self._robots: dict[tuple[str, str, int | None], RobotFileParser | None] = {}
        self._last_location: str | None = None

    @property
    def blocked_hosts(self) -> set[str]:
        return set(self._blocked_hosts)

    @property
    def blocked_host_details(self) -> list[dict[str, object]]:
        return [
            {
                "host": host,
                "reason": "two_or_more_403_or_429_responses",
                "status_codes": list(self._blocked_statuses[host]),
            }
            for host in sorted(self._blocked_hosts)
        ]

    @staticmethod
    def _parts(url: str):
        try:
            parts = urlsplit(url)
            _ = parts.port
        except (TypeError, ValueError):
            return None
        if (
            parts.scheme.lower() not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
        ):
            return None
        return parts

    @staticmethod
    def _host(parts) -> str:
        return parts.hostname.lower()

    @staticmethod
    def _origin_key(parts) -> tuple[str, str, int | None]:
        return parts.scheme.lower(), parts.hostname.lower(), parts.port

    def _rate_limit(self, host: str) -> None:
        last = self._last_host_time.get(host)
        if last is not None:
            wait = self.per_host_delay - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_host_time[host] = time.monotonic()

    def _retry_after(self, value: str | None) -> float:
        if not value:
            return 1.0
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                return 1.0

    def _record_attempt(self, url: str) -> dict[str, int | str | None]:
        parts = urlsplit(url)
        self.requests_made += 1
        entry: dict[str, int | str | None] = {
            "host": parts.hostname.lower() if parts.hostname else "",
            "path": parts.path or "/",
            "status_code": None,
            "request_count": self.requests_made,
        }
        self.request_ledger.append(entry)
        return entry

    def _send_get(self, url: str) -> tuple[requests.Response | None, str | None]:
        parts = self._parts(url)
        if parts is None:
            return None, "invalid_url"
        host = self._host(parts)
        if host in self._blocked_hosts:
            return None, "host_blocked"
        if self.requests_made >= self.request_cap:
            return None, "request_cap_reached"

        self._rate_limit(host)
        ledger_entry = self._record_attempt(url)
        self._last_location = None
        self.session.cookies.clear()
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent, "Accept": "*/*"},
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            self.session.cookies.clear()
            return None, exc.__class__.__name__
        finally:
            self.session.cookies.clear()

        ledger_entry["status_code"] = response.status_code
        self._last_location = response.headers.get("Location")
        if response.status_code in {403, 429}:
            self._blocked_status_count[host] += 1
            self._blocked_statuses[host].append(response.status_code)
            if self._blocked_status_count[host] >= 2:
                self._blocked_hosts.add(host)
        return response, None

    def _get_with_retries(self, url: str) -> FetchResult:
        start = time.monotonic()
        parts = self._parts(url)
        if parts is None:
            return FetchResult(ok=False, error="invalid_url")
        host = self._host(parts)
        last_error: str | None = None

        for attempt in range(self.max_retries + 1):
            response, error = self._send_get(url)
            if error:
                elapsed = int((time.monotonic() - start) * 1000)
                if error in {"request_cap_reached", "host_blocked", "invalid_url"}:
                    return FetchResult(ok=False, error=error, elapsed_ms=elapsed)
                last_error = error
                if attempt < self.max_retries and host not in self._blocked_hosts:
                    time.sleep(1.0)
                    continue
                return FetchResult(ok=False, error=last_error, elapsed_ms=elapsed)

            assert response is not None
            elapsed = int((time.monotonic() - start) * 1000)
            if response.status_code == 429:
                if attempt < self.max_retries and host not in self._blocked_hosts:
                    time.sleep(self._retry_after(response.headers.get("Retry-After")))
                    continue
                return FetchResult(ok=False, status=429, error="rate_limited", elapsed_ms=elapsed)
            if response.status_code == 403:
                return FetchResult(ok=False, status=403, error="blocked", elapsed_ms=elapsed)
            if response.status_code in TRANSIENT_STATUSES:
                last_error = f"http_{response.status_code}"
                if attempt < self.max_retries:
                    time.sleep(1.0)
                    continue
                return FetchResult(ok=False, status=response.status_code, error=last_error, elapsed_ms=elapsed)
            if response.status_code >= 400:
                return FetchResult(
                    ok=False,
                    status=response.status_code,
                    error=f"http_{response.status_code}",
                    elapsed_ms=elapsed,
                )
            return FetchResult(
                ok=True,
                status=response.status_code,
                payload=response.content,
                elapsed_ms=elapsed,
            )

        return FetchResult(
            ok=False,
            error=last_error or "request_failed",
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )

    def _get_redirect_chain(self, url: str, *, check_robots: bool = True) -> FetchResult:
        initial_parts = self._parts(url)
        if initial_parts is None:
            return FetchResult(ok=False, error="invalid_url")
        initial_host = self._host(initial_parts)
        current_url = url

        for _ in range(MAX_REDIRECTS + 1):
            result = self._get_with_retries(current_url)
            if not result.ok or result.status not in REDIRECT_STATUSES:
                return result

            location = self._last_location
            if not location:
                return FetchResult(
                    ok=False,
                    status=result.status,
                    error="redirect_without_location",
                    elapsed_ms=result.elapsed_ms,
                )

            next_url = urljoin(current_url, location)
            next_parts = self._parts(next_url)
            if next_parts is None or self._host(next_parts) != initial_host:
                return FetchResult(
                    ok=False,
                    status=result.status,
                    error="redirect_not_allowed",
                    elapsed_ms=result.elapsed_ms,
                )
            if check_robots and not self._robots_allowed(next_url):
                return FetchResult(
                    ok=False,
                    status=result.status,
                    error="robots_disallowed",
                    elapsed_ms=result.elapsed_ms,
                )
            current_url = next_url

        return FetchResult(ok=False, error="redirect_limit")

    def _fetch_robots(self, url: str) -> RobotFileParser | None:
        parts = self._parts(url)
        assert parts is not None
        key = self._origin_key(parts)
        if key in self._robots:
            return self._robots[key]

        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        result = self._get_redirect_chain(robots_url, check_robots=False)
        if result.status == 404:
            self._robots[key] = None
            return None
        if not result.ok:
            raise RuntimeError(f"robots_unavailable:{result.status or result.error or 'unknown'}")

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(result.payload.decode("utf-8", errors="replace").splitlines())
        self._robots[key] = parser
        return parser

    def _robots_allowed(self, url: str) -> bool:
        parts = self._parts(url)
        if parts is None:
            return False
        host = self._host(parts)
        if host in self._blocked_hosts:
            return False
        try:
            parser = self._fetch_robots(url)
        except RuntimeError as exc:
            self.robots_skips.append({"host": host, "path": parts.path or "/", "reason": str(exc)})
            return False
        allowed = parser is None or parser.can_fetch(self.user_agent, url)
        if not allowed:
            self.robots_skips.append(
                {"host": host, "path": parts.path or "/", "reason": "robots_disallowed"}
            )
        return allowed

    def get(self, url: str) -> FetchResult:
        parts = self._parts(url)
        if parts is None:
            return FetchResult(ok=False, error="invalid_url")
        if self._host(parts) in self._blocked_hosts:
            return FetchResult(ok=False, error="host_blocked")
        if self.requests_made >= self.request_cap:
            return FetchResult(ok=False, error="request_cap_reached")
        if not self._robots_allowed(url):
            error = self.robots_skips[-1]["reason"] if self.robots_skips else "robots_unavailable"
            return FetchResult(ok=False, error=error)
        return self._get_redirect_chain(url)
