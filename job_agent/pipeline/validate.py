"""Validation with explicit reason codes."""
from __future__ import annotations

from urllib.parse import urlsplit


def validate_job(job: dict) -> tuple[bool, str | None]:
    if not job.get("title"):
        return False, "missing_title"
    if not job.get("company_name"):
        return False, "missing_company"
    url = job.get("canonical_url") or ""
    parts = urlsplit(url)
    if not url or parts.scheme not in {"http", "https"} or not parts.netloc:
        return False, "malformed_url"
    if len(job.get("title", "")) > 300:
        return False, "title_too_long"
    if len(job.get("company_name", "")) > 300:
        return False, "company_too_long"
    if job.get("posted_at"):
        try:
            from datetime import datetime
            datetime.fromisoformat(job["posted_at"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return False, "malformed_date"
    return True, None


def validate_jobs(jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    accepted: list[dict] = []
    rejected: list[dict] = []
    seen_source: set[tuple[str, str]] = set()
    for job in jobs:
        ok, reason = validate_job(job)
        if ok:
            key = (str(job.get("source_type")), str(job.get("source_job_id")))
            if job.get("source_job_id") and key in seen_source:
                ok, reason = False, "duplicate_source_id"
            else:
                seen_source.add(key)
        if ok:
            accepted.append(job)
        else:
            rejected.append({"job": job, "reason": reason})
    return accepted, rejected
