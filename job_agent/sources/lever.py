from __future__ import annotations

import json

from ..models import RawJob
from .base import BaseAdapter, SourceRef


class LeverAdapter(BaseAdapter):
    source_type = "lever"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        jobs = data if isinstance(data, list) else data.get("postings", [])
        results = []
        for job in jobs:
            categories = job.get("categories") or {}
            results.append(RawJob(
                source_type=self.source_type,
                source_job_id=str(job.get("id")) if job.get("id") is not None else None,
                title=job.get("text", ""),
                company_name=source.identifier or "",
                url=job.get("hostedUrl") or job.get("applyUrl", ""),
                location=categories.get("location", "") if isinstance(categories, dict) else str(categories),
                description=job.get("descriptionPlain") or job.get("description", ""),
                posted_at=job.get("createdAt"),
                raw=job,
            ))
        return results
