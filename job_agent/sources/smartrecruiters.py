from __future__ import annotations

import json

from ..models import RawJob
from .base import BaseAdapter, SourceRef


class SmartRecruitersAdapter(BaseAdapter):
    source_type = "smartrecruiters"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        jobs = data.get("content", []) if isinstance(data, dict) else []
        results = []
        for job in jobs:
            location = job.get("location") or {}
            if isinstance(location, dict):
                location = ", ".join(str(location.get(k, "")) for k in ("city", "country") if location.get(k))
            results.append(RawJob(
                source_type=self.source_type,
                source_job_id=str(job.get("id")) if job.get("id") is not None else None,
                title=job.get("name", ""),
                company_name=source.identifier or "",
                url=job.get("ref", ""),
                location=location or "",
                description=job.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "") if isinstance(job.get("jobAd"), dict) else "",
                posted_at=job.get("releasedDate"),
                raw=job,
            ))
        return results
