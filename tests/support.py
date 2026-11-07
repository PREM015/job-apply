from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def make_job(**overrides) -> dict:
    job = {
        "source_id": 1,
        "company_master_id": 1,
        "source_job_id": "job-1",
        "canonical_url": "https://acme.example.com/jobs/1",
        "apply_url": "https://acme.example.com/jobs/1",
        "title": "Software Engineer",
        "company_name": "Acme",
        "location_raw": "Bengaluru, India",
        "country": "IN",
        "work_mode": "onsite",
        "employment_type": "full_time",
        "experience_level": "fresher",
        "is_internship": 0,
        "is_software": 1,
        "software_evidence": ["python"],
        "skills_required": ["python"],
        "skills_preferred": [],
        "description_text": "Python and React. Bachelor degree. Fresher.",
        "posted_at": "2026-11-06T10:00:00+00:00",
        "score_total": 80,
        "score_breakdown": {"role_title": 30},
        "dedupe_key": "key-1",
        "fingerprint": "fp-1",
    }
    job.update(overrides)
    return job


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
