"""Queue state transitions with an append-only audit event."""
from __future__ import annotations

from ..db.repository import Database

VALID_STATES = {"queued", "reviewed", "interested", "applied", "skipped", "rejected", "archived"}


def set_state(db: Database, queue_id: int, new_state: str, actor: str = "owner", note: str = "") -> None:
    if new_state not in VALID_STATES:
        raise ValueError(f"invalid queue state: {new_state}")
    db.update_queue_state(queue_id, new_state, actor=actor, note=note)
