"""Company source resolution. Pure URL reasoning; no network."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from ..sources.base import SourceRef

ATS_PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/([^/?#]+)")),
    ("lever", re.compile(r"jobs\.lever\.co/([^/?#]+)")),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([^/?#]+)")),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([^/?#]+)")),
    ("workable", re.compile(r"([^./]+)\.workable\.com")),
    ("keka", re.compile(r"([^./]+)\.keka\.com")),
    ("zoho", re.compile(r"([^./]+)\.zohorecruit\.com")),
]


def detect_ats(url: str) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    for source_type, pattern in ATS_PATTERNS:
        match = pattern.search(url)
        if match:
            return source_type, match.group(1)
    if url.lower().endswith(".xml") or "sitemap" in url.lower():
        return "sitemap", None
    return "jsonld", None


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
        return {"company_master_id": master_id, "source_type": ats_type or "jsonld",
                "url": str(url), "identifier": identifier or company.get("name"),
                "resolution_status": "resolved", "resolution_reason": key}
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
