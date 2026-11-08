"""Pipeline orchestration. This is the only pipeline module that writes."""
from __future__ import annotations

from typing import Any

from ..db.repository import Database
from .classify import classify_job
from .dedupe import canonical_url_key, fingerprint, possible_duplicate, source_identity
from .match import hard_filter
from .normalize import normalize_job
from .quota import select_quota
from .score import score_job
from .validate import validate_jobs


def run_pipeline(
    db: Database,
    prefs: dict,
    batches: list[dict[str, Any]],
    actor: str = "system",
    *,
    minimum_score: int | None = None,
    run_mode: str = "dry",
) -> dict[str, Any]:
    if minimum_score is not None and (
        isinstance(minimum_score, bool) or not isinstance(minimum_score, int) or not 0 <= minimum_score <= 100
    ):
        raise ValueError("minimum_score must be an integer in 0..100")
    if run_mode not in {"dry", "live_discovery"}:
        raise ValueError("run_mode must be 'dry' or 'live_discovery'")

    run_id = db.create_run(mode=run_mode)
    counters = {"source_count": len(batches), "fetched_count": 0, "normalized_count": 0,
                "rejected_count": 0, "score_floor_rejected_count": 0,
                "duplicate_count": 0, "queued_count": 0}
    errors: list[str] = []
    normalized: list[dict[str, Any]] = []
    rejection_reasons: list[dict[str, Any]] = []

    for batch in batches:
        raw_jobs = batch.get("jobs", [])
        counters["fetched_count"] += len(raw_jobs)
        if batch.get("error"):
            errors.append(f"source_error:{batch.get('source_type', 'unknown')}:{batch['error']}")
            if batch.get("source_id") is not None:
                db.update_source_health(int(batch["source_id"]), "http_error", False)
            continue
        if batch.get("source_id") is not None:
            db.update_source_health(int(batch["source_id"]), "ok", True)
        metadata = {
            "source_id": batch.get("source_id"),
            "company_master_id": batch.get("company_master_id"),
            "source_type": batch.get("source_type", "unknown"),
            "tier": batch.get("tier"),
        }
        if batch.get("origin") is not None:
            metadata["origin"] = batch["origin"]
        for raw in raw_jobs:
            normalized_job = normalize_job(raw, batch.get("url"))
            normalized_job.update(metadata)
            normalized.append(normalized_job)

    counters["normalized_count"] = len(normalized)
    accepted, validation_rejects = validate_jobs(normalized)
    counters["rejected_count"] += len(validation_rejects)
    rejection_reasons.extend(validation_rejects)

    classified: list[dict[str, Any]] = []
    for job in accepted:
        classify_job(job, prefs)
        company_key = job.get("company_name", "").lower()
        job["suppressed"] = bool(company_key and db.is_suppressed("company", company_key))
        job["dedupe_key"] = source_identity(job.get("source_id"), job.get("source_job_id")) or canonical_url_key(job["canonical_url"])
        job["fingerprint"] = fingerprint(job.get("company_name", ""), job.get("title", ""),
                                          job.get("location_raw", ""), job.get("description_text", ""))
        existing = None
        if job.get("source_id") is not None and job.get("source_job_id"):
            existing = db.find_job_by_source(int(job["source_id"]), str(job["source_job_id"]))
        if existing is None:
            existing = db.find_job_by_url(job["canonical_url"])
        job["already_applied"] = job["canonical_url"] in db.applied_keys() or job["fingerprint"] in db.applied_keys()
        ok, reason = hard_filter(job, prefs)
        if not ok:
            counters["rejected_count"] += 1
            rejection_reasons.append({"job": job, "reason": reason})
            continue
        result = score_job(job, prefs, job.get("tier"))
        job["score_total"] = result.total
        job["score_breakdown"] = result.breakdown
        job["score_reasons"] = result.reasons
        if minimum_score is not None and result.total < minimum_score:
            counters["rejected_count"] += 1
            counters["score_floor_rejected_count"] += 1
            rejection_reasons.append({"job": job, "reason": "score_below_manual_apply_min"})
            continue
        job["is_new"] = existing is None
        job_id, created = db.upsert_job(job)
        job["job_id"] = job_id
        if not created:
            counters["duplicate_count"] += 1
            continue
        classified.append(job)

    for index, left in enumerate(classified):
        for right in classified[index + 1:]:
            if possible_duplicate(left, right):
                left["possible_duplicate"] = True
                right["possible_duplicate"] = True

    selected = select_quota(classified, prefs, db.applied_keys(), set())
    for rank, job in enumerate(selected, start=1):
        db.enqueue(run_id, int(job["job_id"]), rank, int(job["score_total"]), "; ".join(job.get("score_reasons", [])))
    counters["queued_count"] = len(selected)
    db.finish_run(run_id, counters, errors)
    return {
        "run_id": run_id,
        "counters": counters,
        "errors": errors,
        "rejections": [{"title": r["job"].get("title", ""), "reason": r["reason"]} for r in rejection_reasons],
        "queue": db.list_queue(run_id),
    }
