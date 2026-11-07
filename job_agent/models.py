from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawJob:
    source_type: str
    title: str
    company_name: str
    url: str
    source_job_id: str | None = None
    location: str = ""
    description: str = ""
    posted_at: str | None = None
    employment_type: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchResult:
    ok: bool
    status: int | None = None
    payload: bytes = b""
    error: str | None = None
    elapsed_ms: int = 0


@dataclass
class ScoreResult:
    total: int
    breakdown: dict[str, int]
    reasons: list[str]
