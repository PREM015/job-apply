from __future__ import annotations

from ..models import RawJob
from .base import BaseAdapter, SourceParseError, SourceRef, decode_json


class GreenhouseAdapter(BaseAdapter):
    source_type = "greenhouse"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        data = decode_json(payload, self.source_type)
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise SourceParseError("greenhouse:unexpected_response_shape")
        jobs = data["jobs"]
        results = []
        for job in jobs:
            if not isinstance(job, dict):
                raise SourceParseError("greenhouse:job_entry_is_not_an_object")
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
                workplace_type=job.get("workplace_type"),
                is_remote=job.get("is_remote") if isinstance(job.get("is_remote"), bool) else None,
                structured_location=location or None,
                raw=job,
            ))
        return results
