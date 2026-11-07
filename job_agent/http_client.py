"""Bounded HTTP client. No live calls are made unless explicitly invoked."""
from __future__ import annotations

import time
from collections import defaultdict
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

from .models import FetchResult


class HttpClient:
    def __init__(self, timeout: float = 10.0, max_retries: int = 2, per_host_delay: float = 1.0,
                 request_cap: int = 20, user_agent: str = "JobAgent/1.0 (offline-first)",
                 session: requests.Session | None = None):
        self.timeout = timeout
        self.max_retries = max_retries
        self.per_host_delay = per_host_delay
        self.request_cap = request_cap
        self.user_agent = user_agent
        self.session = session or requests.Session()
        self.requests_made = 0
        self._last_host_time: dict[str, float] = {}
        self._host_counts: dict[str, int] = defaultdict(int)

    def _rate_limit(self, host: str) -> None:
        last = self._last_host_time.get(host, 0.0)
        wait = self.per_host_delay - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_host_time[host] = time.monotonic()

    def get(self, url: str) -> FetchResult:
        if self.requests_made >= self.request_cap:
            return FetchResult(ok=False, error="request_cap_reached")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return FetchResult(ok=False, error="invalid_url")
        host = parsed.hostname or ""
        if self._host_counts[host] >= 5:
            return FetchResult(ok=False, error="host_cap_reached")
        self._rate_limit(host)
        self.requests_made += 1
        self._host_counts[host] += 1
        start = time.monotonic()
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
                elapsed = int((time.monotonic() - start) * 1000)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = float(retry_after) if retry_after else 2.0
                    except ValueError:
                        try:
                            delay = max(0.0, (parsedate_to_datetime(retry_after).timestamp() - time.time()))
                        except (TypeError, ValueError):
                            delay = 2.0
                    if attempt < self.max_retries:
                        time.sleep(delay)
                        continue
                    return FetchResult(ok=False, status=429, error="rate_limited", elapsed_ms=elapsed)
                if response.status_code in {401, 403}:
                    return FetchResult(ok=False, status=response.status_code, error="blocked", elapsed_ms=elapsed)
                if response.status_code >= 400:
                    last_error = f"http_{response.status_code}"
                    if attempt < self.max_retries:
                        continue
                    return FetchResult(ok=False, status=response.status_code, error=last_error, elapsed_ms=elapsed)
                return FetchResult(ok=True, status=response.status_code, payload=response.content, elapsed_ms=elapsed)
            except requests.RequestException as exc:
                last_error = exc.__class__.__name__
                if attempt < self.max_retries:
                    time.sleep(0.1 * (attempt + 1))
                    continue
        return FetchResult(ok=False, error=last_error or "request_failed",
                           elapsed_ms=int((time.monotonic() - start) * 1000))
