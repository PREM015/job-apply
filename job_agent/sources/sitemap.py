"""Sitemap adapter with lastmod filtering and conservative URL filtering."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..models import RawJob
from .base import BaseAdapter, SourceRef

JOB_HINT_RE = re.compile(r"(job|career|position|opening|vacanc)", re.I)


class SitemapAdapter(BaseAdapter):
    source_type = "sitemap"

    def parse(self, payload: bytes, source: SourceRef) -> list[RawJob]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return []
        results = []
        for node in root.iter():
            if not node.tag.endswith("url"):
                continue
            loc = None
            lastmod = None
            for child in node:
                if child.tag.endswith("loc"):
                    loc = child.text
                elif child.tag.endswith("lastmod"):
                    lastmod = child.text
            if not loc or not JOB_HINT_RE.search(loc):
                continue
            slug = loc.rstrip("/").rsplit("/", 1)[-1]
            title = slug.replace("-", " ").replace("_", " ").strip().title()
            results.append(RawJob(
                source_type=self.source_type,
                source_job_id=loc,
                title=title or "Unknown role",
                company_name=source.identifier or "",
                url=loc,
                posted_at=lastmod,
                raw={"loc": loc, "lastmod": lastmod},
            ))
        return results
