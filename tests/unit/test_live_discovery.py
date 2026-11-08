from __future__ import annotations

import json

import responses

from job_agent.http_client import HttpClient
from job_agent.live_discovery import (
    assess_terms,
    adapter_url,
    _adapter_status,
    _feed_is_complete,
    find_ats_link,
    find_terms_url,
    select_company_candidates,
    verify_adapter_sample,
    _attach_sources,
    _fetch_company,
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
    assert adapter_url({
        "source_type": "ashby",
        "identifier": "acme",
        "url": "https://jobs.ashbyhq.com/acme",
    }) == "https://api.ashbyhq.com/posting-api/job-board/acme"


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


def test_feed_with_incomplete_metadata_is_not_used_for_closure():
    payload = json.dumps({
        "jobs": [{"id": 101}],
        "meta": {"total": 2},
    }).encode()

    assert _feed_is_complete("greenhouse", payload) is False


@responses.activate
def test_known_ats_fetches_api_directly_and_marks_complete(monkeypatch):
    from tests.support import FIXTURES

    monkeypatch.setattr("job_agent.http_client.time.sleep", lambda _seconds: None)
    endpoint = "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"
    responses.add(responses.GET, "https://boards-api.greenhouse.io/robots.txt", status=404)
    responses.add(
        responses.GET,
        endpoint,
        body=(FIXTURES / "sources" / "greenhouse_api.fixture.json").read_bytes(),
        status=200,
        content_type="application/json",
    )
    candidate = {
        "company": {"master_id": 41, "name": "Acme Registry Ltd", "tier": "Tier 1"},
        "resolved": {
            "source_type": "greenhouse",
            "url": "https://boards.greenhouse.io/acme",
            "identifier": "acme",
        },
        "method": "known_ats",
    }

    batch, attempt = _fetch_company(candidate, HttpClient(per_host_delay=0), {"greenhouse": True}, set())

    assert batch is not None
    assert batch["scan_complete"] is True
    assert batch["url"] == endpoint
    assert batch["jobs"][0].company_name == "Acme Registry Ltd"
    assert attempt["response"]["content_type"] == "application/json"
    assert [call.request.url for call in responses.calls] == [
        "https://boards-api.greenhouse.io/robots.txt",
        endpoint,
    ]


@responses.activate
def test_known_ats_rejects_non_json_content_type(monkeypatch):
    monkeypatch.setattr("job_agent.http_client.time.sleep", lambda _seconds: None)
    endpoint = "https://api.lever.co/v0/postings/acme?mode=json"
    responses.add(responses.GET, "https://api.lever.co/robots.txt", status=404)
    responses.add(
        responses.GET, endpoint, body="<html>maintenance</html>",
        status=200, content_type="text/html",
    )
    candidate = {
        "company": {"master_id": 42, "name": "Beta Inc", "tier": "Tier 1"},
        "resolved": {
            "source_type": "lever", "url": "https://jobs.lever.co/acme",
            "identifier": "acme",
        },
        "method": "known_ats",
    }
    batch, attempt = _fetch_company(candidate, HttpClient(per_host_delay=0), {"lever": True}, set())
    assert batch is None
    assert attempt["reason"] == "unexpected_content_type"
    assert attempt["source_error"]["bytes"] > 0
    assert len(attempt["source_error"]["sha256"]) == 64


@responses.activate
def test_known_ats_reports_malformed_json_instead_of_zero_jobs(monkeypatch):
    monkeypatch.setattr("job_agent.http_client.time.sleep", lambda _seconds: None)
    endpoint = "https://api.ashbyhq.com/posting-api/job-board/acme"
    responses.add(responses.GET, "https://api.ashbyhq.com/robots.txt", status=404)
    responses.add(
        responses.GET, endpoint, body="{", status=200, content_type="application/json",
    )
    candidate = {
        "company": {"master_id": 43, "name": "Gamma Corp", "tier": "Tier 2"},
        "resolved": {
            "source_type": "ashby", "url": "https://jobs.ashbyhq.com/acme",
            "identifier": "acme",
        },
        "method": "known_ats",
    }
    batch, attempt = _fetch_company(candidate, HttpClient(per_host_delay=0), {"ashby": True}, set())
    assert batch is None
    assert attempt["reason"] == "ashby:invalid_json"
    assert attempt["source_error"]["status"] == 200


@responses.activate
def test_known_ats_http_error_is_a_source_error(monkeypatch):
    monkeypatch.setattr("job_agent.http_client.time.sleep", lambda _seconds: None)
    endpoint = "https://api.ashbyhq.com/posting-api/job-board/acme"
    responses.add(responses.GET, "https://api.ashbyhq.com/robots.txt", status=404)
    responses.add(responses.GET, endpoint, body="unavailable", status=503, content_type="text/plain")
    candidate = {
        "company": {"master_id": 44, "name": "Delta Ltd", "tier": "Tier 2"},
        "resolved": {
            "source_type": "ashby", "url": "https://jobs.ashbyhq.com/acme",
            "identifier": "acme",
        },
        "method": "known_ats",
    }
    batch, attempt = _fetch_company(candidate, HttpClient(per_host_delay=0), {"ashby": True}, set())
    assert batch is None
    assert attempt["reason"] == "http_503"
    assert attempt["source_error"]["status"] == 503


@responses.activate
def test_valid_empty_ats_feed_is_complete_but_not_sample_verified(monkeypatch):
    monkeypatch.setattr("job_agent.http_client.time.sleep", lambda _seconds: None)
    endpoint = "https://api.lever.co/v0/postings/acme?mode=json"
    responses.add(responses.GET, "https://api.lever.co/robots.txt", status=404)
    responses.add(
        responses.GET, endpoint, body="[]", status=200, content_type="application/json",
    )
    candidate = {
        "company": {"master_id": 45, "name": "Epsilon Ltd", "tier": "Tier 2"},
        "resolved": {
            "source_type": "lever", "url": "https://jobs.lever.co/acme",
            "identifier": "acme",
        },
        "method": "known_ats",
    }
    batch, attempt = _fetch_company(candidate, HttpClient(per_host_delay=0), {"lever": True}, set())
    assert batch is not None
    assert batch["scan_complete"] is True
    assert batch["jobs"] == []
    assert attempt["verification"]["verified"] is False


def test_configured_source_cap_is_used(db):
    from job_agent.live_discovery import _attach_sources

    db.upsert_company({"master_id": 901, "name": "Fixture", "tier": "Tier 1"})
    batches = [{
        "company_master_id": 901,
        "source_type": "greenhouse",
        "url": "https://boards.greenhouse.io/fixture",
    }]
    _attach_sources(db, batches, {"greenhouse": 17})
    assert db.list_sources()[0]["request_cap"] == 17


def test_adapter_status_reports_unverified_source_without_parsed_sample():
    result = _adapter_status([{
        "company": "Acme",
        "source_type": "greenhouse",
        "status": "skipped",
        "reason": "source_terms_unverified",
    }])

    assert result["greenhouse"]["status"] == "UNVERIFIED"
    assert result["greenhouse"]["reason"] == "source_terms_unverified"
