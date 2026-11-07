from __future__ import annotations

import json

from ..models import RawJob
from .base import BaseAdapter, SourceRef


class WorkableAdapter(BaseAdapter):
    source_type = "workable"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        jobs = data.get("jobs", []) if isinstance(data, dict) else data
        results = []
        for job in jobs:
            location = job.get("location") or {}
            if isinstance(location, dict):
                location = location.get("location_str") or location.get("city", "")
            results.append(RawJob(
                source_type=self.source_type,
                source_job_id=str(job.get("shortcode") or job.get("id") or "") or None,
                title=job.get("title", ""),
                company_name=source.identifier or "",
                url=job.get("url") or job.get("application_url", ""),
                location=location or "",
                description=job.get("description", ""),
                posted_at=job.get("published_on") or job.get("created_at"),
                raw=job,
            ))
        return results
