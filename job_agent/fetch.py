"""Source fetching orchestration. Only called with an explicit, bounded client."""
from __future__ import annotations

from dataclasses import asdict

from .http_client import HttpClient
from .sources.base import SourceRef
from .sources.registry import get_adapter


def fetch_source(source: SourceRef, client: HttpClient, adapter=None) -> dict:
    adapter = adapter or get_adapter(source.source_type)
    result = adapter.fetch(source, client)
    base = {
        "source_id": source.source_id,
        "company_master_id": source.company_master_id,
        "source_type": source.source_type,
        "url": source.url,
    }
    if not result.ok:
        base.update({"jobs": [], "error": result.error or "fetch_failed"})
        return base
    jobs = []
    for job in adapter.parse(result.payload, source):
        jobs.append(asdict(job) if not isinstance(job, dict) else job)
    base["jobs"] = jobs
    return base
