"""Daily report generation from SQLite only."""
from __future__ import annotations

import json

from .db.repository import Database


def daily_report(db: Database, run_id: int | None = None) -> dict:
    runs = db.list_runs()
    if not runs:
        return {"run": None, "counts": db.counts(), "queue": [], "errors": []}
    run = next((r for r in runs if run_id is None or r["run_id"] == run_id), runs[0])
    queue = db.list_queue(run["run_id"])
    try:
        errors = json.loads(run.get("errors_json") or "[]")
    except ValueError:
        errors = []
    return {
        "run": run,
        "counts": db.counts(),
        "queue": [{"rank": item["rank"], "score": item["score"], "company": item["company_name"],
                   "title": item["title"], "reason": item["reason"]} for item in queue],
        "errors": errors,
    }
