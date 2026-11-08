"""Pure normalization. No I/O."""
from __future__ import annotations

import html
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                   "gclid", "fbclid", "ref", "source", "mc_cid", "mc_eid"}
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", str(value)).strip()


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    try:
        return clean_text(BeautifulSoup(value, "html.parser").get_text(" "))
    except Exception:
        return clean_text(html.unescape(re.sub(r"<[^>]+>", " ", value)))


def bounded_text(value: str | None, limit: int = 20000) -> str:
    text = clean_text(value)
    return text[:limit]


def canonicalize_url(value: str | None, base: str | None = None) -> str:
    if not value:
        return ""
    absolute = urljoin(base or "", str(value).strip())
    parts = urlsplit(absolute)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        return ""
    host = parts.hostname.lower() if parts.hostname else ""
    port = parts.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
    query.sort()
    return urlunsplit((scheme, netloc, parts.path or "/", urlencode(query), ""))


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def normalize_job(raw: dict | object, base_url: str | None = None) -> dict:
    if is_dataclass(raw):
        raw = asdict(raw)
    if not isinstance(raw, dict):
        raise TypeError("raw job must be a mapping or dataclass")
    url = canonicalize_url(raw.get("url") or raw.get("apply_url"), base_url)
    raw_payload = raw.get("raw") if isinstance(raw.get("raw"), dict) else {}
    structured_location = (
        raw.get("structured_location")
        or raw_payload.get("jobLocation")
        or raw_payload.get("location")
        or raw.get("location")
    )
    if isinstance(structured_location, dict):
        address = structured_location.get("address")
        if isinstance(address, dict):
            structured_location = ", ".join(
                str(address[key]) for key in ("addressLocality", "addressRegion", "addressCountry")
                if address.get(key)
            ) or structured_location.get("name", "")
        else:
            structured_location = structured_location.get("name", "")
    workplace_type = raw.get("workplace_type") or raw_payload.get("workplaceType")
    is_remote = raw.get("is_remote")
    if not isinstance(is_remote, bool):
        is_remote = raw_payload.get("isRemote")
    return {
        "source_type": raw.get("source_type", "unknown"),
        "source_job_id": str(raw["source_job_id"]) if raw.get("source_job_id") not in (None, "") else None,
        "title": clean_text(raw.get("title")),
        "company_name": clean_text(raw.get("company_name")),
        "canonical_url": url,
        "apply_url": canonicalize_url(raw.get("apply_url") or url, base_url),
        "location_raw": clean_text(raw.get("location")),
        "structured_location": clean_text(str(structured_location)) if structured_location else "",
        "workplace_type": clean_text(str(workplace_type)) if workplace_type else "",
        "is_remote": is_remote if isinstance(is_remote, bool) else None,
        "description_text": bounded_text(strip_html(raw.get("description") or raw.get("description_text"))),
        "posted_at": parse_date(raw.get("posted_at")),
        "employment_type": clean_text(raw.get("employment_type")).lower() or "unknown",
    }
