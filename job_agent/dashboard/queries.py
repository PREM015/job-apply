"""Read-only dashboard queries. All SQL goes through Database/repository."""
from __future__ import annotations

from ..db.repository import Database


def queue(db: Database, run_id: int | None = None) -> list[dict]:
    return db.list_queue(run_id)


def job_detail(db: Database, job_id: int) -> dict | None:
    return db.get_job(job_id)


def applications(db: Database) -> list[dict]:
    return db.list_applications()


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
