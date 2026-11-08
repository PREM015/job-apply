from __future__ import annotations

from ..models import RawJob
from .base import BaseAdapter, SourceParseError, SourceRef, decode_json


class AshbyAdapter(BaseAdapter):
    source_type = "ashby"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        data = decode_json(payload, self.source_type)
        jobs = data.get("jobs") if isinstance(data, dict) else data if isinstance(data, list) else None
        if not isinstance(jobs, list):
            raise SourceParseError("ashby:unexpected_response_shape")
        results = []
        for job in jobs:
            if not isinstance(job, dict):
                raise SourceParseError("ashby:job_entry_is_not_an_object")
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
                description=job.get("descriptionPlain") or job.get("description", ""),
                posted_at=job.get("publishedAt") or job.get("updatedAt"),
                workplace_type=job.get("workplaceType"),
                is_remote=job.get("isRemote") if isinstance(job.get("isRemote"), bool) else None,
                structured_location=location or None,
                raw=job,
            ))
        return results
