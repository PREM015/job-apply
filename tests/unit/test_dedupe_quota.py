from __future__ import annotations

from job_agent.pipeline.dedupe import (canonical_url_key, fingerprint, possible_duplicate,
                                       source_identity)
from job_agent.pipeline.quota import select_quota


def test_source_identity_and_url_key():
    assert source_identity(None, "1") is None
    assert source_identity(1, None) is None
    assert source_identity(1, "1") == source_identity(1, "1")
    assert source_identity(1, "1") != source_identity(2, "1")
    assert canonical_url_key("https://a.example.com/x?utm_source=a") == canonical_url_key("https://a.example.com/x")


def test_fingerprint_changes_with_description():
    a = fingerprint("Acme", "Engineer", "Pune", "Python")
    b = fingerprint("Acme", "Engineer", "Pune", "Python and SQL")
    assert a != b
    assert a == fingerprint(" Acme ", "Engineer", "Pune", "Python")


def test_possible_duplicate():
    left = {"title": "Software Engineer", "company_name": "Acme", "location_raw": "Pune"}
    right = {"title": "Software Engineer", "company_name": "Acme", "location_raw": "Pune"}
    other = {"title": "Software Engineer", "company_name": "Beta", "location_raw": "Pune"}
    assert possible_duplicate(left, right) is True
    assert possible_duplicate(left, other) is False


def test_quota_limits_total_tier_company_and_applied(prefs):
    prefs = {**prefs, "quotas": {"total_per_day": 3, "per_tier": {"1": 2, "2": 2}, "per_company": 1}}
    jobs = [
        {"job_id": 1, "score_total": 90, "tier": "Tier 1", "company_name": "A", "canonical_url": "u1", "fingerprint": "f1"},
        {"job_id": 2, "score_total": 85, "tier": "Tier 1", "company_name": "A", "canonical_url": "u2", "fingerprint": "f2"},
        {"job_id": 3, "score_total": 80, "tier": "Tier 1", "company_name": "B", "canonical_url": "u3", "fingerprint": "f3"},
        {"job_id": 4, "score_total": 75, "tier": "Tier 2", "company_name": "C", "canonical_url": "u4", "fingerprint": "f4"},
        {"job_id": 5, "score_total": 70, "tier": "Tier 2", "company_name": "D", "canonical_url": "u5", "fingerprint": "f5"},
    ]
    selected = select_quota(jobs, prefs)
    assert len(selected) == 3
    assert [job["job_id"] for job in selected] == [1, 3, 4]


def test_quota_skips_applied_and_suppressed(prefs):
    jobs = [{"job_id": 1, "score_total": 90, "tier": "Tier 1", "company_name": "A",
             "canonical_url": "u1", "fingerprint": "f1", "already_applied": True},
            {"job_id": 2, "score_total": 80, "tier": "Tier 1", "company_name": "B",
             "canonical_url": "u2", "fingerprint": "f2", "suppressed": True}]
    assert select_quota(jobs, prefs) == []
