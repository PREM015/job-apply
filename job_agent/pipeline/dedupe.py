"""Three-layer deduplication primitives."""
from __future__ import annotations

import hashlib
import re

from rapidfuzz import fuzz

from .normalize import canonicalize_url, clean_text


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_identity(source_id: int | None, source_job_id: str | None) -> str | None:
    if source_id is None or not source_job_id:
        return None
    return _hash(f"{source_id}|{source_job_id}")


def canonical_url_key(url: str) -> str:
    return _hash(canonicalize_url(url))


def fingerprint(company: str, title: str, location: str, description: str) -> str:
    normalized = "|".join([
        clean_text(company).lower(),
        clean_text(title).lower(),
        clean_text(location).lower(),
        re.sub(r"\W+", " ", clean_text(description).lower())[:2000],
    ])
    return _hash(normalized)


def possible_duplicate(a: dict, b: dict, threshold: int = 92) -> bool:
    left = f"{a.get('title', '')} {a.get('company_name', '')} {a.get('location_raw', '')}"
    right = f"{b.get('title', '')} {b.get('company_name', '')} {b.get('location_raw', '')}"
    return fuzz.token_set_ratio(left, right) >= threshold and a.get("company_name", "").lower() == b.get("company_name", "").lower()
