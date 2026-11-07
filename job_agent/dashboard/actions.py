"""Dashboard write actions are DB-only."""
from __future__ import annotations

import hashlib

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


def add_manual_job(db: Database, canonical_url: str, title: str, company_name: str,
                   location_raw: str = "", work_mode: str = "unknown",
                   description_text: str = "", apply_url: str | None = None) -> tuple[int, bool]:
    if not canonical_url.lower().startswith(("http://", "https://")):
        raise ValueError("canonical_url must be an http(s) URL")
    if not title.strip() or not company_name.strip():
        raise ValueError("title and company_name are required")
    digest = hashlib.sha256(
        f"{canonical_url.strip()}\n{title.strip()}\n{company_name.strip()}".encode("utf-8")
    ).hexdigest()
    return db.upsert_job({
        "canonical_url": canonical_url.strip(),
        "apply_url": (apply_url or canonical_url).strip(),
        "title": title.strip(),
        "company_name": company_name.strip(),
        "location_raw": location_raw.strip(),
        "work_mode": work_mode.strip() or "unknown",
        "employment_type": "unknown",
        "experience_level": "unknown",
        "description_text": description_text.strip(),
        "status": "active",
        "score_total": 0,
        "score_breakdown": {"source": "manual"},
        "dedupe_key": f"manual:{digest}",
        "fingerprint": digest,
    })
