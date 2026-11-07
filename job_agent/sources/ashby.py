from __future__ import annotations

import json

from ..models import RawJob
from .base import BaseAdapter, SourceRef


class AshbyAdapter(BaseAdapter):
    source_type = "ashby"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        jobs = data.get("jobs", []) if isinstance(data, dict) else data
        results = []
        for job in jobs:
            location = job.get("location") or job.get("locationName") or ""
            if isinstance(location, dict):
                location = location.get("name", "")
            results.append(RawJob(
                source_type=self.source_type,
                source_job_id=str(job.get("id")) if job.get("id") is not None else None,
                title=job.get("title", ""),
                company_name=source.identifier or "",
                url=job.get("jobUrl") or job.get("url", ""),
                location=location,
                description=job.get("descriptionHtml") or job.get("description", ""),
                posted_at=job.get("publishedAt") or job.get("updatedAt"),
                raw=job,
            ))
        return results
