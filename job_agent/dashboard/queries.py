"""Read-only dashboard queries. All SQL goes through Database/repository."""
from __future__ import annotations

from ..db.repository import Database


def queue(db: Database, run_id: int | None = None) -> list[dict]:
    return db.list_queue(run_id)


def latest_queue(db: Database) -> list[dict]:
    runs = db.list_runs()
    if not runs:
        return []
    return db.list_queue(max(run["run_id"] for run in runs))


def today_apply_list(db: Database) -> list[dict]:
    return [item for item in latest_queue(db) if item.get("state") == "queued"]


def needs_review(db: Database) -> list[dict]:
    return [item for item in latest_queue(db) if item.get("state") in {"queued", "reviewed"}]


def all_jobs(db: Database) -> list[dict]:
    return db.list_jobs()


def companies(db: Database) -> list[dict]:
    return db.list_companies()


def global_targets(db: Database) -> list[dict]:
    return db.list_global_targets()


def job_detail(db: Database, job_id: int) -> dict | None:
    return db.get_job(job_id)


def applications(db: Database) -> list[dict]:
    return db.list_applications()


def source_health(db: Database) -> list[dict]:
    return db.list_sources()


def stats(db: Database) -> dict:
    result = db.counts()
    states: dict[str, int] = {}
    for item in latest_queue(db):
        state = str(item.get("state") or "unknown")
        states[state] = states.get(state, 0) + 1
    result["latest_queue_states"] = states
    return result


def portal_links(db: Database) -> list[dict]:
    links = []
    for company in db.list_companies():
        for field in ("careers_url", "openings_url"):
            url = company.get(field)
            if url:
                links.append({"master_id": company["master_id"], "company": company["name"],
                              "kind": field, "url": url})
    return links


def sources(db: Database) -> list[dict]:
    return db.list_sources()


def runs(db: Database) -> list[dict]:
    return db.list_runs()


def rejections(db: Database) -> list[dict]:
    result = []
    for run in db.list_runs():
        import json
        try:
            errors = json.loads(run.get("errors_json") or "[]")
        except ValueError:
            errors = []
        result.extend({"run_id": run["run_id"], "reason": error} for error in errors)
    return result
