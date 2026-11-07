"""Common source adapter contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..http_client import HttpClient
from ..models import FetchResult, RawJob


@dataclass
class SourceRef:
    company_master_id: int | None
    source_type: str
    url: str
    source_id: int | None = None
    identifier: str | None = None


class SourceAdapter(Protocol):
    source_type: str

    def fetch(self, source: SourceRef, client: HttpClient) -> FetchResult: ...
    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]: ...


class BaseAdapter:
    source_type = "base"

    def fetch(self, source: SourceRef, client: HttpClient) -> FetchResult:
        return client.get(source.url)

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        return []
