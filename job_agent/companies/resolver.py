"""Company source resolution. Pure URL reasoning; no network."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from ..sources.base import SourceRef

ATS_PATTERNS = [
    ("greenhouse", re.compile(r"^(?:boards|job-boards)\.greenhouse\.io$")),
    ("lever", re.compile(r"^jobs\.lever\.co$")),
    ("ashby", re.compile(r"^jobs\.ashbyhq\.com$")),
    ("smartrecruiters", re.compile(r"^(?:jobs|careers)\.smartrecruiters\.com$")),
    ("workable", re.compile(r"^[^./]+\.workable\.com$")),
    ("keka", re.compile(r"^[^./]+\.keka\.com$")),
    ("zoho", re.compile(r"^[^./]+\.zohorecruit\.com$")),
]


def detect_ats(url: str) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    try:
        parts = urlsplit(url)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return None, None
    except ValueError:
        return None, None
    host = parts.hostname.lower()
    path_segments = [segment for segment in parts.path.split("/") if segment]
    if host == "boards-api.greenhouse.io" and len(path_segments) >= 3:
        if path_segments[:2] == ["v1", "boards"]:
            return "greenhouse", path_segments[2]
    if host == "api.lever.co" and len(path_segments) >= 3:
        if path_segments[:2] == ["v0", "postings"]:
            return "lever", path_segments[2]
    if host == "api.ashbyhq.com" and len(path_segments) >= 3:
        if path_segments[:2] == ["posting-api", "job-board"]:
            return "ashby", path_segments[2]
    if host == "apply.workable.com":
        return ("workable", path_segments[0]) if path_segments else (None, None)
    for source_type, pattern in ATS_PATTERNS:
        if pattern.fullmatch(host) and path_segments:
            return source_type, path_segments[0]
    if parts.path.lower().endswith(".xml") or "sitemap" in parts.path.lower():
        return "sitemap", None
    return None, None


def resolve_company(company: dict, overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    master_id = company.get("master_id")
    override = overrides.get(str(master_id)) or overrides.get(master_id)
    if override:
        return {"company_master_id": master_id, "source_type": override["source_type"],
                "url": override["url"], "identifier": override.get("identifier"),
                "resolution_status": "manual", "resolution_reason": "override"}
    for key in ("openings_url", "careers_url"):
        url = company.get(key)
        if not url:
            continue
        ats_type, identifier = detect_ats(str(url))
        if ats_type:
            return {"company_master_id": master_id, "source_type": ats_type,
                    "url": str(url), "identifier": identifier or company.get("name"),
                    "resolution_status": "resolved", "resolution_reason": key}
        return {"company_master_id": master_id, "source_type": None,
                "url": str(url), "identifier": company.get("name"),
                "resolution_status": "manual_check", "resolution_reason": key}
    return {"company_master_id": master_id, "source_type": None, "url": None,
            "identifier": None, "resolution_status": "unresolved", "resolution_reason": "no_url"}


def to_source_ref(resolved: dict) -> SourceRef | None:
    if not resolved.get("url") or not resolved.get("source_type"):
        return None
    return SourceRef(
        company_master_id=resolved.get("company_master_id"),
        source_type=resolved["source_type"],
        url=resolved["url"],
        identifier=resolved.get("identifier"),
    )


def source_coverage_report(companies: list[dict], overrides: dict | None = None) -> dict:
    counts: dict[str, int] = {}
    unresolved = 0
    for company in companies:
        resolved = resolve_company(company, overrides)
        key = resolved["source_type"] or "unresolved"
        counts[key] = counts.get(key, 0) + 1
        if resolved["resolution_status"] == "unresolved":
            unresolved += 1
    return {"total": len(companies), "by_type": counts, "unresolved": unresolved}
