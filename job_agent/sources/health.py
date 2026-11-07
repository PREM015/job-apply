"""Source health and circuit-breaker helpers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceHealth:
    source_id: int
    fail_count: int = 0
    max_failures: int = 3

    def record(self, ok: bool) -> None:
        if ok:
            self.fail_count = 0
        else:
            self.fail_count += 1

    @property
    def open(self) -> bool:
        return self.fail_count >= self.max_failures
