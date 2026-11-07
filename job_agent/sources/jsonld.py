"""JSON-LD JobPosting adapter."""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from ..models import RawJob
from .base import BaseAdapter, SourceRef


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


class JsonLdAdapter(BaseAdapter):
    source_type = "jsonld"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            html = payload.decode("utf-8")
        except UnicodeDecodeError:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
            except (ValueError, TypeError):
                continue
            for node in _walk(data):
                if node.get("@type") != "JobPosting":
                    continue
                org = node.get("hiringOrganization") or {}
                if isinstance(org, dict):
                    org = org.get("name", "")
                location = node.get("jobLocation") or {}
                if isinstance(location, list):
                    location = location[0] if location else {}
                if isinstance(location, dict):
                    address = location.get("address") or {}
                    location = ", ".join(str(address.get(k, "")) for k in ("addressLocality", "addressRegion", "addressCountry") if address.get(k))
                results.append(RawJob(
                    source_type=self.source_type,
                    source_job_id=str(node.get("identifier", {}).get("value", "")) or None if isinstance(node.get("identifier"), dict) else None,
                    title=node.get("title", ""),
                    company_name=org or source.identifier or "",
                    url=node.get("url", ""),
                    location=location or "",
                    description=node.get("description", ""),
                    posted_at=node.get("datePosted"),
                    employment_type=", ".join(node.get("employmentType", [])) if isinstance(node.get("employmentType"), list) else str(node.get("employmentType", "")),
                    raw=node,
                ))
        return results
