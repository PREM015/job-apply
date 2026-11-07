"""Dashboard write actions are DB-only."""
from __future__ import annotations

from ..db.repository import Database
from ..tracking.applications import log_application, update_application
from ..tracking.queue import set_state


def update_status(db: Database, queue_id: int, state: str, note: str = "") -> None:
    set_state(db, queue_id, state, actor="owner", note=note)


def add_application(db: Database, job_id: int, status: str = "applied", applied_at: str | None = None,
                    notes: str = "") -> int:
    return log_application(db, job_id, status=status, applied_at=applied_at, notes=notes)


def update_application_status(db: Database, application_id: int, status: str, notes: str | None = None) -> None:
    update_application(db, application_id, status, notes)


def suppress_company(db: Database, company: str, reason: str = "") -> None:
    db.suppress("company", company.lower(), reason)
