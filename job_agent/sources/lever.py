from __future__ import annotations

from datetime import datetime, timezone

from ..models import RawJob
from .base import BaseAdapter, SourceParseError, SourceRef, decode_json


def _created_at(value) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        milliseconds = value
    elif isinstance(value, str) and value.strip().isdigit():
        milliseconds = int(value.strip())
    else:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    try:
        return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc).replace(
            microsecond=0,
        ).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


class LeverAdapter(BaseAdapter):
    source_type = "lever"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        data = decode_json(payload, self.source_type)
        jobs = data if isinstance(data, list) else data.get("postings") if isinstance(data, dict) else None
        if not isinstance(jobs, list):
            raise SourceParseError("lever:unexpected_response_shape")
        results = []
        for job in jobs:
            if not isinstance(job, dict):
                raise SourceParseError("lever:posting_entry_is_not_an_object")
            categories = job.get("categories") or {}
            results.append(RawJob(
                source_type=self.source_type,
                source_job_id=str(job.get("id")) if job.get("id") is not None else None,
                title=job.get("text", ""),
                company_name=source.identifier or "",
                url=job.get("hostedUrl") or job.get("applyUrl", ""),
                location=categories.get("location", "") if isinstance(categories, dict) else str(categories),
                description=job.get("descriptionPlain") or job.get("description", ""),
                posted_at=_created_at(job.get("createdAt")),
                workplace_type=job.get("workplaceType"),
                is_remote=job.get("isRemote") if isinstance(job.get("isRemote"), bool) else None,
                structured_location=categories.get("location") if isinstance(categories, dict) else None,
                raw=job,
            ))
        return results
