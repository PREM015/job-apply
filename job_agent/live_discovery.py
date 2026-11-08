"""Owner-authorized public GET discovery; never submits applications."""
from __future__ import annotations

import re
import sqlite3
import tempfile
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

from bs4 import BeautifulSoup

from .companies.resolver import detect_ats, resolve_company
from .config import ConfigError, load_sources
from .db.repository import Database
from .http_client import HttpClient
from .models import RawJob
from .pipeline.run import run_pipeline
from .sources.base import SourceRef
from .sources.registry import get_adapter

ATS_TYPES = {"greenhouse", "lever", "ashby", "smartrecruiters", "workable"}
PORTAL_DOMAINS = {"linkedin.com", "naukri.com", "indeed.com", "glassdoor.com"}
TERMS_RESTRICTION = re.compile(
    r"(?:automated|scrap|crawl|bot|robot).{0,120}"
    r"(?:prohibit|forbid|may not|must not|not permitted|not allowed|restricted)"
    r"|(?:prohibit|forbid|may not|must not|not permitted|not allowed|restricted).{0,120}"
    r"(?:automated|scrap|crawl|bot|robot)",
    re.IGNORECASE | re.DOTALL,
)

_RESPONSE_FIELDS: dict[str, dict[str, str]] = {
    "greenhouse": {"title": "title", "url": "absolute_url", "source_job_id": "id"},
    "lever": {"title": "text", "url": "hostedUrl", "source_job_id": "id"},
    "ashby": {"title": "title", "url": "jobUrl", "source_job_id": "id"},
    "smartrecruiters": {"title": "name", "url": "ref", "source_job_id": "id"},
    "workable": {"title": "title", "url": "url", "source_job_id": "shortcode"},
    "jsonld": {"title": "title", "url": "url"},
    "sitemap": {"url": "loc"},
}


def _tier_number(value: object) -> int | None:
    match = re.search(r"\b([1-4])\b", str(value or ""))
    return int(match.group(1)) if match else None


def _is_portal_url(url: str) -> bool:
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return True
    return any(host == domain or host.endswith(f".{domain}") for domain in PORTAL_DOMAINS)


def _slug_matches_company(name: str, identifier: str) -> bool:
    normalize = lambda value: re.sub(r"[^a-z0-9]", "", value.lower())
    normalized_name = normalize(name)
    normalized_identifier = normalize(identifier)
    if len(normalized_identifier) < 3 or not normalized_name:
        return False
    return SequenceMatcher(None, normalized_name, normalized_identifier).ratio() >= 0.65


def _board_url(source_type: str, identifier: str) -> str | None:
    token = quote(identifier.strip(), safe="")
    if not token:
        return None
    templates = {
        "greenhouse": f"https://boards.greenhouse.io/{token}",
        "lever": f"https://jobs.lever.co/{token}",
        "ashby": f"https://jobs.ashbyhq.com/{token}",
        "smartrecruiters": f"https://jobs.smartrecruiters.com/{token}",
        "workable": f"https://{token}.workable.com",
    }
    return templates.get(source_type)


def _source_candidate(
    company: dict[str, Any],
    enabled_sources: dict[str, bool],
    overrides: dict | None,
) -> dict[str, Any] | None:
    override = (overrides or {}).get(str(company.get("master_id"))) or (
        overrides or {}
    ).get(company.get("master_id"))
    urls: list[tuple[str, str]] = []
    if override and override.get("url"):
        urls.append(("override", str(override["url"])))
    else:
        for field in ("openings_url", "careers_url"):
            if company.get(field):
                urls.append((field, str(company[field])))

    candidates: list[dict[str, Any]] = []
    for field, url in urls:
        if _is_portal_url(url):
            continue
        resolved = resolve_company(
            {**company, "openings_url": url, "careers_url": None},
            overrides if field == "override" else None,
        )
        detected_type, detected_identifier = detect_ats(url)
        stored_type = str(company.get("ats_type") or "").lower()
        source_type = str(
            (override or {}).get("source_type")
            or (stored_type if stored_type in ATS_TYPES and detected_type == "jsonld" else detected_type)
            or resolved.get("source_type")
            or ""
        ).lower()
        if not source_type or not enabled_sources.get(source_type, False):
            continue
        identifier = (
            (override or {}).get("identifier")
            or company.get("ats_identifier")
            or detected_identifier
            or company.get("name")
        )
        resolved.update(
            source_type=source_type,
            url=url,
            identifier=str(identifier or ""),
            resolution_reason=field,
        )
        candidates.append({
            "company": company,
            "resolved": resolved,
            "method": "known_ats" if source_type in ATS_TYPES else "stored_url",
            "priority": 0 if source_type in ATS_TYPES else 1,
        })

    if candidates:
        return min(candidates, key=lambda item: (item["priority"], item["resolved"]["resolution_reason"] != "openings_url"))

    source_type = str(company.get("ats_type") or "").lower()
    identifier = str(company.get("ats_identifier") or "")
    name = str(company.get("name") or "")
    if (
        source_type in ATS_TYPES
        and enabled_sources.get(source_type, False)
        and _slug_matches_company(name, identifier)
    ):
        url = _board_url(source_type, identifier)
        if url:
            return {
                "company": company,
                "resolved": {
                    "company_master_id": company.get("master_id"),
                    "source_type": source_type,
                    "url": url,
                    "identifier": identifier,
                    "resolution_status": "resolved",
                    "resolution_reason": "bounded_slug_probe",
                },
                "method": "slug_probe",
                "priority": 0,
            }
    return None


def select_company_candidates(
    companies: list[dict[str, Any]],
    enabled_sources: dict[str, bool],
    overrides: dict | None = None,
) -> list[dict[str, Any]]:
    candidates = []
    for company in companies:
        tier = _tier_number(company.get("tier"))
        if tier not in {1, 2}:
            continue
        candidate = _source_candidate(company, enabled_sources, overrides)
        if candidate:
            candidate["tier_number"] = tier
            candidates.append(candidate)
    return sorted(
        candidates,
        key=lambda item: (
            item["priority"],
            item["tier_number"],
            str(item["company"].get("name") or "").casefold(),
            int(item["company"].get("master_id") or 0),
        ),
    )


def adapter_url(resolved: dict[str, Any]) -> str:
    source_type = str(resolved.get("source_type") or "")
    url = str(resolved.get("url") or "")
    identifier = quote(str(resolved.get("identifier") or "").strip(), safe="")
    if not identifier:
        return url

    host = (urlsplit(url).hostname or "").lower()
    if source_type == "greenhouse":
        if host == "boards-api.greenhouse.io":
            return url
        return f"https://boards-api.greenhouse.io/v1/boards/{identifier}/jobs?content=true"
    if source_type == "lever":
        if host == "api.lever.co":
            return url
        return f"https://api.lever.co/v0/postings/{identifier}?mode=json"
    if source_type == "ashby":
        if host == "api.ashbyhq.com":
            return url
        return f"https://api.ashbyhq.com/posting-api/job-board/{identifier}"
    if source_type == "smartrecruiters":
        if host == "api.smartrecruiters.com":
            return url
        return f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings"
    if source_type == "workable":
        if host == "apply.workable.com" and "/api/" in url:
            return url
        return f"https://apply.workable.com/api/v1/accounts/{identifier}/jobs"
    return url


def find_terms_url(payload: bytes, base_url: str) -> str | None:
    soup = BeautifulSoup(payload, "html.parser")
    for link in soup.find_all("a", href=True):
        label = f"{link.get_text(' ', strip=True)} {link.get('href', '')}".lower()
        if re.search(r"\bterms?\b|conditions|legal", label):
            candidate = urljoin(base_url, str(link["href"]))
            parts = urlsplit(candidate)
            if parts.scheme in {"http", "https"} and parts.hostname:
                return candidate
    return None


def assess_terms(payload: bytes) -> dict[str, str]:
    text = BeautifulSoup(payload, "html.parser").get_text(" ", strip=True)
    if TERMS_RESTRICTION.search(text):
        return {
            "status": "restricted",
            "summary": "terms page contains an explicit automated-access restriction",
        }
    return {
        "status": "no_explicit_restriction_found",
        "summary": "terms page fetched; no explicit automated-access restriction matched",
    }


def find_ats_link(
    payload: bytes,
    base_url: str,
    enabled_sources: dict[str, bool],
) -> dict[str, str] | None:
    soup = BeautifulSoup(payload, "html.parser")
    for link in soup.find_all("a", href=True):
        candidate_url = urljoin(base_url, str(link["href"]))
        if _is_portal_url(candidate_url):
            continue
        source_type, identifier = detect_ats(candidate_url)
        if source_type in ATS_TYPES and enabled_sources.get(source_type, False) and identifier:
            return {
                "source_type": source_type,
                "identifier": identifier,
                "url": candidate_url,
            }
    return None


def _raw_field(raw: dict[str, Any], key: str) -> Any:
    if key == "identifier.value":
        identifier = raw.get("identifier")
        return identifier.get("value") if isinstance(identifier, dict) else identifier
    value = raw.get(key)
    if key == "hostedUrl" and not value:
        value = raw.get("applyUrl")
    if key == "jobUrl" and not value:
        value = raw.get("url")
    if key == "url" and not value:
        value = raw.get("application_url")
    if key == "shortcode" and not value:
        value = raw.get("id")
    return value


def verify_adapter_sample(source_type: str, jobs: list[RawJob]) -> dict[str, Any]:
    if not jobs:
        return {"verified": False, "reason": "no_jobs_parsed", "field_names": []}
    job = jobs[0]
    raw = job.raw if isinstance(job.raw, dict) else {}
    field_names = sorted(str(key) for key in raw)
    mapping = _RESPONSE_FIELDS.get(source_type)
    if not mapping:
        return {"verified": False, "reason": "no_response_field_contract", "field_names": field_names}

    for parsed_field, raw_field in mapping.items():
        expected = _raw_field(raw, raw_field)
        if parsed_field == "source_job_id" and expected in (None, ""):
            continue
        parsed_value = getattr(job, parsed_field, None)
        if expected in (None, ""):
            return {
                "verified": False,
                "reason": f"missing_raw_{raw_field}",
                "field_names": field_names,
            }
        if str(parsed_value).strip() != str(expected).strip():
            return {
                "verified": False,
                "reason": f"{parsed_field}_mismatch",
                "field_names": field_names,
            }
    return {"verified": True, "reason": None, "field_names": field_names}


def _manual_apply_min(prefs: dict[str, Any]) -> int:
    thresholds = prefs.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ConfigError("preferences.thresholds must be a mapping")
    value = thresholds.get("manual_apply_min")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise ConfigError("preferences.thresholds.manual_apply_min must be an integer in 0..100")
    return value


def _terms_check(
    payload: bytes,
    base_url: str,
    client: HttpClient,
    checked_hosts: set[str],
) -> dict[str, str]:
    host = (urlsplit(base_url).hostname or "").lower()
    if host in checked_hosts:
        return {"status": "already_checked", "summary": "terms for this host were checked earlier"}
    terms_url = find_terms_url(payload, base_url)
    if not terms_url:
        return {"status": "unverified", "summary": "no terms link found on source page"}
    result = client.get(terms_url)
    if not result.ok:
        return {"status": "unverified", "summary": f"terms fetch failed: {result.error or result.status}"}
    checked_hosts.add(host)
    assessment = assess_terms(result.payload)
    assessment["url"] = terms_url
    return assessment


def _fetch_company(
    candidate: dict[str, Any],
    client: HttpClient,
    enabled_sources: dict[str, bool],
    checked_terms_hosts: set[str],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    company = candidate["company"]
    resolved = dict(candidate["resolved"])
    company_name = str(company.get("name") or "")
    source_type = str(resolved["source_type"])
    source_url = str(resolved["url"])
    attempt = {
        "company": company_name,
        "method": candidate["method"],
        "source_type": source_type,
        "status": "skipped",
        "reason": None,
    }

    page_result = client.get(source_url)
    if not page_result.ok:
        attempt["reason"] = page_result.error or f"http_{page_result.status}"
        return None, attempt
    terms = _terms_check(page_result.payload, source_url, client, checked_terms_hosts)
    attempt["terms"] = terms
    if terms["status"] == "restricted":
        attempt["reason"] = "source_terms_restrict_automated_access"
        return None, attempt
    if terms["status"] == "unverified":
        attempt["reason"] = "source_terms_unverified"
        return None, attempt

    payload = page_result.payload
    feed_url = source_url
    if source_type == "jsonld":
        linked = find_ats_link(payload, source_url, enabled_sources)
        if linked:
            board = client.get(linked["url"])
            if not board.ok:
                attempt["reason"] = board.error or f"http_{board.status}"
                return None, attempt
            linked_terms = _terms_check(board.payload, linked["url"], client, checked_terms_hosts)
            attempt["terms"] = {"company_site": terms, "ats_site": linked_terms}
            if linked_terms["status"] in {"restricted", "unverified"}:
                attempt["reason"] = f"ats_terms_{linked_terms['status']}"
                return None, attempt
            source_type = linked["source_type"]
            resolved.update(source_type=source_type, identifier=linked["identifier"], url=linked["url"])
            feed_url = adapter_url(resolved)
            if feed_url != linked["url"]:
                feed_result = client.get(feed_url)
                if not feed_result.ok:
                    attempt["reason"] = feed_result.error or f"http_{feed_result.status}"
                    return None, attempt
                payload = feed_result.payload
            else:
                payload = board.payload
        else:
            source_type = "jsonld"
    elif source_type in ATS_TYPES:
        feed_url = adapter_url(resolved)
        if feed_url != source_url:
            feed_result = client.get(feed_url)
            if not feed_result.ok:
                attempt["reason"] = feed_result.error or f"http_{feed_result.status}"
                return None, attempt
            payload = feed_result.payload

    adapter = get_adapter(source_type)
    source_ref = SourceRef(
        company_master_id=int(company["master_id"]),
        source_type=source_type,
        url=feed_url,
        identifier=company_name,
    )
    jobs = adapter.parse(payload, source_ref)
    verification = verify_adapter_sample(source_type, jobs)
    attempt["source_type"] = source_type
    attempt["verification"] = verification
    if not verification["verified"]:
        attempt["reason"] = verification["reason"]
        return None, attempt

    for job in jobs:
        job.company_name = company_name
    attempt["status"] = "parsed"
    return {
        "company_master_id": int(company["master_id"]),
        "company_name": company_name,
        "tier": company.get("tier"),
        "source_type": source_type,
        "url": feed_url,
        "origin": "LIVE",
        "jobs": jobs,
    }, attempt


def _copy_database(source: sqlite3.Connection, path: Path) -> None:
    target = sqlite3.connect(str(path))
    try:
        source.backup(target)
    finally:
        target.close()


def _attach_sources(
    db: Database,
    batches: list[dict[str, Any]],
    source_request_caps: dict[str, int],
) -> list[dict[str, Any]]:
    result = []
    for batch in batches:
        copied = dict(batch)
        copied["source_id"] = db.add_source({
            "company_master_id": batch["company_master_id"],
            "source_type": batch["source_type"],
            "url": batch["url"],
            "enabled": True,
            "request_cap": source_request_caps[batch["source_type"]],
        })
        result.append(copied)
    return result


def _run_preview(
    source: sqlite3.Connection,
    prefs: dict[str, Any],
    batches: list[dict[str, Any]],
    score_floor: int,
    source_request_caps: dict[str, int],
) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    with tempfile.TemporaryDirectory(prefix="job-agent-live-preview-") as directory:
        path = Path(directory) / "preview.sqlite3"
        _copy_database(source, path)
        preview = Database(path, backup_on_connect=False, read_only=False)
        preview.connect()
        try:
            preview_batches = _attach_sources(preview, batches, source_request_caps)
            result = run_pipeline(
                preview,
                prefs,
                preview_batches,
                minimum_score=score_floor,
                run_mode="live_discovery",
            ) if preview_batches else {
                "counters": {
                    "source_count": 0, "fetched_count": 0, "normalized_count": 0,
                    "rejected_count": 0, "score_floor_rejected_count": 0,
                    "duplicate_count": 0, "queued_count": 0,
                },
                "errors": [],
                "rejections": [],
                "queue": [],
            }
            job_details = {
                int(item["job_id"]): preview.get_job(int(item["job_id"]))
                for item in result["queue"][:5]
            }
            return result, job_details
        finally:
            preview.close()


def _add_real_sources(
    db: Database,
    prefs: dict[str, Any],
    batches: list[dict[str, Any]],
    score_floor: int,
    source_request_caps: dict[str, int],
) -> dict[str, Any]:
    attached = _attach_sources(db, batches, source_request_caps)
    if not attached:
        return {
            "counters": {
                "source_count": 0, "fetched_count": 0, "normalized_count": 0,
                "rejected_count": 0, "score_floor_rejected_count": 0,
                "duplicate_count": 0, "queued_count": 0,
            },
            "errors": [],
            "rejections": [],
            "queue": [],
        }
    return run_pipeline(
        db,
        prefs,
        attached,
        minimum_score=score_floor,
        run_mode="live_discovery",
    )


def run_live_discovery(
    db: Database,
    prefs: dict[str, Any],
    config: dict[str, Any],
    *,
    max_companies: int = 25,
    max_requests: int = 300,
    dry_report: bool = False,
) -> dict[str, Any]:
    if not 1 <= max_companies <= 25:
        raise ValueError("max_companies must be in 1..25")
    if not 1 <= max_requests <= 300:
        raise ValueError("max_requests must be in 1..300")
    if db.connection is None:
        raise RuntimeError("database must be connected")
    fixture_path = Path("data/fixture_job_agent.sqlite3").resolve()
    if not dry_report and db.path.resolve() == fixture_path:
        raise ValueError("LIVE discovery cannot write to the fixture database")
    if not dry_report and db.read_only:
        raise ValueError("LIVE discovery requires a writable real database")
    score_floor = _manual_apply_min(prefs)
    enabled_sources = load_sources()
    candidates = select_company_candidates(db.list_companies(), {
        key: bool(spec["enabled"]) for key, spec in enabled_sources.items()
    })
    http_config = config["http"]
    client = HttpClient(
        timeout=float(http_config["timeout_seconds"]),
        max_retries=min(int(http_config["max_retries"]), 1),
        per_host_delay=max(1.0, float(http_config["per_host_delay_seconds"])),
        request_cap=max_requests,
        user_agent=str(http_config["user_agent"]),
    )
    source_request_caps = {
        source_type: max(1, int(spec.get("request_cap", 1)))
        for source_type, spec in enabled_sources.items()
    }
    attempted: list[dict[str, Any]] = []
    batches: list[dict[str, Any]] = []
    method_counts: Counter[str] = Counter()
    checked_terms_hosts: set[str] = set()
    attempts_by_master: set[int] = set()

    def fetch_pass(pass_candidates: list[dict[str, Any]]) -> None:
        for candidate in pass_candidates:
            if client.requests_made >= max_requests:
                break
            master_id = int(candidate["company"].get("master_id") or 0)
            if master_id in attempts_by_master:
                continue
            attempts_by_master.add(master_id)
            method_counts[candidate["method"]] += 1
            batch, attempt = _fetch_company(
                candidate,
                client,
                {key: bool(spec["enabled"]) for key, spec in enabled_sources.items()},
                checked_terms_hosts,
            )
            attempted.append(attempt)
            if batch:
                batches.append(batch)

    first_pass = candidates[:max_companies]
    fetch_pass(first_pass)
    preview_result, preview_jobs = _run_preview(
        db.connection, prefs, batches, score_floor, source_request_caps,
    )
    widened = False
    if len(preview_result["queue"]) < 5 and client.requests_made < max_requests:
        remaining = [
            item for item in candidates
            if int(item["company"].get("master_id") or 0) not in attempts_by_master
        ][:max_companies]
        if remaining:
            widened = True
            fetch_pass(remaining)
            preview_result, preview_jobs = _run_preview(
                db.connection, prefs, batches, score_floor, source_request_caps,
            )

    if dry_report:
        pipeline_result = preview_result
        job_details = preview_jobs
    else:
        pipeline_result = _add_real_sources(db, prefs, batches, score_floor, source_request_caps)
        job_details = {
            int(item["job_id"]): db.get_job(int(item["job_id"]))
            for item in pipeline_result["queue"][:5]
        }

    top_jobs = []
    for item in pipeline_result["queue"][:5]:
        job = job_details.get(int(item["job_id"])) or {}
        apply_url = str(job.get("apply_url") or job.get("canonical_url") or "")
        apply_check = client.get(apply_url) if apply_url else None
        top_jobs.append({
            "company": job.get("company_name") or item.get("company_name"),
            "title": job.get("title") or item.get("title"),
            "location": job.get("location_raw") or "",
            "work_mode": job.get("work_mode") or item.get("work_mode"),
            "score": int(job.get("score_total") or item.get("score") or 0),
            "apply_url": apply_url,
            "apply_url_status_code": apply_check.status if apply_check else None,
            "apply_url_error": apply_check.error if apply_check and not apply_check.ok else None,
            "label": "LIVE",
        })

    rejection_counts = Counter(
        str(item.get("reason") or "unknown") for item in pipeline_result.get("rejections", [])
    )
    return {
        "dataset": "LIVE",
        "preferences_keys": sorted(prefs.keys()),
        "experience_key": "experience.ceiling_years",
        "legacy_max_years_experience": "unsupported",
        "work_modes": "unsupported by preference schema; classification only, not filtered",
        "companies_selected": len(candidates),
        "companies_attempted": len(attempted),
        "companies_resolved_by_method": dict(method_counts),
        "attempts": attempted,
        "widening_pass_used": widened,
        "jobs_fetched": sum(len(batch["jobs"]) for batch in batches),
        "rejected_by_gate": dict(rejection_counts),
        "score_floor": score_floor,
        "score_floor_rejected_count": pipeline_result["counters"].get("score_floor_rejected_count", 0),
        "deduped": pipeline_result["counters"].get("duplicate_count", 0),
        "queued": pipeline_result["counters"].get("queued_count", 0),
        "pipeline_counters": pipeline_result["counters"],
        "errors": pipeline_result.get("errors", []),
        "top_jobs": top_jobs,
        "adapter_status": _adapter_status(attempted),
        "terms_summary": [
            {
                "company": item["company"],
                "source_type": item["source_type"],
                "terms": item.get("terms", {}).get("summary", "not checked"),
                "status": item.get("terms", {}).get("status", "unverified"),
            }
            for item in attempted
        ],
        "requests_used": client.requests_made,
        "request_cap": max_requests,
        "hosts_skipped": client.blocked_host_details,
        "robots_skips": client.robots_skips,
        "request_ledger": client.request_ledger,
        "dry_report": dry_report,
    }


def _adapter_status(attempts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        source_type = str(attempt.get("source_type") or "")
        verification = attempt.get("verification")
        if not source_type:
            continue
        verified = isinstance(verification, dict) and verification.get("verified") is True
        status = "VERIFIED-ON-1-SAMPLE" if verified else "UNVERIFIED"
        current = result.get(source_type)
        if current is None or status == "UNVERIFIED":
            result[source_type] = {
                "status": status,
                "company": attempt.get("company"),
                "reason": (
                    verification.get("reason")
                    if isinstance(verification, dict)
                    else attempt.get("reason") or "no_adapter_sample"
                ),
                "first_job_field_names": (
                    verification.get("field_names", [])
                    if isinstance(verification, dict)
                    else []
                ),
            }
    return result


def write_live_evidence(report: dict[str, Any], evidence_dir: str | Path = "project-planning/evidence") -> None:
    directory = Path(evidence_dir)
    directory.mkdir(parents=True, exist_ok=True)
    ledger_path = directory / "LIVE_request_ledger.txt"
    with ledger_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("host\tpath\tstatus_code\trequest_count\n")
        for entry in report.get("request_ledger", []):
            handle.write(
                f"{entry['host']}\t{entry['path']}\t{entry['status_code'] or ''}\t"
                f"{entry['request_count']}\n"
            )
    summary_path = directory / "LIVE_discovery_summary.txt"
    import json

    summary_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
