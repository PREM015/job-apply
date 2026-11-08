"""Common source adapter contract."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol

from ..http_client import HttpClient
from ..models import FetchResult, RawJob


class SourceParseError(ValueError):
    """A fetched source response does not match the adapter's expected API shape."""


def decode_json(payload: bytes, source_type: str):
    try:
        return json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise SourceParseError(f"{source_type}:invalid_json") from exc


def is_json_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


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
