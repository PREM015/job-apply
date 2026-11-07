"""Application tracking is human-owned; no submission path exists."""
from __future__ import annotations

from ..db.repository import Database


def log_application(db: Database, job_id: int, status: str = "applied", applied_at: str | None = None,
                    notes: str = "") -> int:
    if status.lower() in {"submitted", "auto", "auto-apply"}:
        raise PermissionError("automatic application submission is not supported")
    return db.create_application(job_id, status, applied_at=applied_at, notes=notes)


def update_application(db: Database, application_id: int, status: str, notes: str | None = None) -> None:
    db.update_application(application_id, status, notes)
