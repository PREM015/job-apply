from __future__ import annotations

import json

from job_agent.live_discovery import (
    assess_terms,
    adapter_url,
    _adapter_status,
    find_ats_link,
    find_terms_url,
    select_company_candidates,
    verify_adapter_sample,
)
from job_agent.models import RawJob
from job_agent.sources.base import SourceRef


def test_company_selection_is_tier_limited_ats_first_and_skips_portals():
    companies = [
        {"master_id": 1, "name": "Tier Three", "tier": "Tier 3",
         "careers_url": "https://boards.greenhouse.io/three"},
        {"master_id": 2, "name": "Career Site", "tier": "Tier 1",
         "careers_url": "https://careers.example.com/jobs"},
        {"master_id": 3, "name": "Lever Board", "tier": "Tier 2",
         "careers_url": "https://jobs.lever.co/lever-board"},
        {"master_id": 4, "name": "Portal", "tier": "Tier 1",
         "careers_url": "https://www.linkedin.com/company/portal/jobs"},
        {"master_id": 5, "name": "Greenhouse Board", "tier": "Tier 1",
         "careers_url": "https://boards.greenhouse.io/greenhouse-board"},
    ]

    candidates = select_company_candidates(
        companies,
        {"greenhouse": True, "lever": True, "jsonld": True},
    )

    assert [item["company"]["master_id"] for item in candidates] == [5, 3, 2]
    assert [item["resolved"]["source_type"] for item in candidates] == [
        "greenhouse", "lever", "jsonld",
    ]


def test_adapter_url_uses_supported_public_feed_patterns():
    assert adapter_url({
        "source_type": "greenhouse",
        "identifier": "acme",
        "url": "https://boards.greenhouse.io/acme",
    }) == "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"
    assert adapter_url({
        "source_type": "lever",
        "identifier": "acme",
        "url": "https://jobs.lever.co/acme",
    }) == "https://api.lever.co/v0/postings/acme?mode=json"


def test_find_terms_url_and_restriction_summary():
    html = b'<a href="/legal/terms">Terms of Use</a>'

    assert find_terms_url(html, "https://careers.example.com/jobs") == (
        "https://careers.example.com/legal/terms"
    )
    restricted = assess_terms(b"We prohibit automated crawling of this site.")
    permitted = assess_terms(b"Please review our general terms of service.")
    assert restricted["status"] == "restricted"
    assert permitted["status"] == "no_explicit_restriction_found"


def test_find_supported_ats_link_only_one_hop():
    html = (
        b'<a href="https://jobs.lever.co/acme">Open roles</a>'
        b'<a href="https://www.linkedin.com/jobs/acme">Other jobs</a>'
    )
    found = find_ats_link(
        html,
        "https://careers.example.com",
        {"lever": True, "jsonld": True},
    )

    assert found is not None
    assert found["source_type"] == "lever"
    assert found["identifier"] == "acme"


def test_adapter_sample_verification_compares_real_payload_fields():
    source = SourceRef(
        company_master_id=12,
        source_type="greenhouse",
        url="https://boards.greenhouse.io/acme",
        identifier="Acme Incorporated",
    )
    payload = json.dumps({
        "jobs": [{
            "id": 101,
            "title": "Software Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
            "location": {"name": "Bengaluru"},
        }],
    }).encode()
    from job_agent.sources.greenhouse import GreenhouseAdapter

    jobs = GreenhouseAdapter().parse(payload, source)
    result = verify_adapter_sample("greenhouse", jobs)

    assert result["verified"] is True
    assert result["field_names"] == ["absolute_url", "id", "location", "title"]


def test_adapter_sample_mismatch_is_unverified():
    job = RawJob(
        source_type="greenhouse",
        source_job_id="101",
        title="Different title",
        company_name="Acme",
        url="https://boards.greenhouse.io/acme/jobs/101",
        raw={
            "id": 101,
            "title": "Software Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
        },
    )

    result = verify_adapter_sample("greenhouse", [job])

    assert result["verified"] is False
    assert result["reason"] == "title_mismatch"


def test_adapter_status_reports_unverified_source_without_parsed_sample():
    result = _adapter_status([{
        "company": "Acme",
        "source_type": "greenhouse",
        "status": "skipped",
        "reason": "source_terms_unverified",
    }])

    assert result["greenhouse"]["status"] == "UNVERIFIED"
    assert result["greenhouse"]["reason"] == "source_terms_unverified"
