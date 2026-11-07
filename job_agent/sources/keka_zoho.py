"""Keka and Zoho research adapters (fixture-only; disabled in config)."""
from __future__ import annotations

import json

from ..models import RawJob
from .base import BaseAdapter, SourceRef

KEKA_PATTERN = "https://<tenant>.keka.com/careers/"
ZOHO_PATTERN = "https://<tenant>.zohorecruit.com/jobs/Careers"


class KekaAdapter(BaseAdapter):
    source_type = "keka"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        return [RawJob(
            source_type=self.source_type,
            source_job_id=str(job.get("id")) if job.get("id") is not None else None,
            title=job.get("title", ""),
            company_name=source.identifier or "",
            url=job.get("url", ""),
            location=job.get("location", ""),
            description=job.get("description", ""),
            posted_at=job.get("posted_at"),
            raw=job,
        ) for job in jobs]


class ZohoAdapter(BaseAdapter):
    source_type = "zoho"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        jobs = data.get("data", []) if isinstance(data, dict) else []
        return [RawJob(
            source_type=self.source_type,
            source_job_id=str(job.get("id")) if job.get("id") is not None else None,
            title=job.get("Posting_Title") or job.get("title", ""),
            company_name=source.identifier or "",
            url=job.get("url", ""),
            location=job.get("City") or job.get("location", ""),
            description=job.get("Job_Description") or job.get("description", ""),
            posted_at=job.get("Date_Opened") or job.get("posted_at"),
            raw=job,
        ) for job in jobs]
