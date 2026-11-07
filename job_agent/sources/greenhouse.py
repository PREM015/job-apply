from __future__ import annotations

import json

from ..models import RawJob
from .base import BaseAdapter, SourceRef


class GreenhouseAdapter(BaseAdapter):
    source_type = "greenhouse"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        results = []
        for job in jobs:
            location = job.get("location") or {}
            if isinstance(location, dict):
                location = location.get("name", "")
            results.append(RawJob(
                source_type=self.source_type,
                source_job_id=str(job.get("id")) if job.get("id") is not None else None,
                title=job.get("title", ""),
                company_name=source.identifier or "",
                url=job.get("absolute_url", ""),
                location=location or "",
                description=job.get("content", ""),
                posted_at=job.get("updated_at") or job.get("created_at"),
                raw=job,
            ))
        return results
