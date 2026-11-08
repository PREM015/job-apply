from __future__ import annotations

import json

import pytest

from job_agent.sources.ashby import AshbyAdapter
from job_agent.sources.base import SourceRef
from job_agent.sources.base import SourceParseError
from job_agent.sources.greenhouse import GreenhouseAdapter
from job_agent.sources.jsonld import JsonLdAdapter
from job_agent.sources.keka_zoho import KekaAdapter, ZohoAdapter
from job_agent.sources.lever import LeverAdapter
from job_agent.sources.sitemap import SitemapAdapter
from job_agent.sources.smartrecruiters import SmartRecruitersAdapter
from job_agent.sources.workable import WorkableAdapter
from tests.support import FIXTURES


def ref(source_type: str, identifier: str = "Acme") -> SourceRef:
    return SourceRef(company_master_id=1, source_type=source_type,
                     url="https://acme.example.com", identifier=identifier)


@pytest.mark.parametrize("adapter,fixture,expected_title", [
    (GreenhouseAdapter(), "greenhouse.json", "Software Engineer"),
    (LeverAdapter(), "lever.json", "Backend Developer"),
    (AshbyAdapter(), "ashby.json", "Frontend Engineer"),
    (SmartRecruitersAdapter(), "smartrecruiters.json", "Data Engineer"),
    (WorkableAdapter(), "workable.json", "QA Automation Engineer"),
    (KekaAdapter(), "keka.json", "Junior Developer"),
    (ZohoAdapter(), "zoho.json", "Software Trainee"),
])
def test_json_adapters(adapter, fixture, expected_title):
    payload = (FIXTURES / "sources" / fixture).read_bytes()
    jobs = adapter.parse(payload, ref(adapter.source_type))
    assert len(jobs) == 1
    assert jobs[0].title == expected_title
    assert jobs[0].url.startswith("http")
    assert jobs[0].company_name == "Acme"


def test_jsonld_adapter():
    payload = (FIXTURES / "sources" / "jsonld.html").read_bytes()
    jobs = JsonLdAdapter().parse(payload, ref("jsonld"))
    assert len(jobs) == 1
    assert jobs[0].title == "Full Stack Developer"
    assert jobs[0].company_name == "Acme"
    assert "Bengaluru" in jobs[0].location


def test_sitemap_adapter_filters_non_job_urls():
    payload = (FIXTURES / "sources" / "sitemap.xml").read_bytes()
    jobs = SitemapAdapter().parse(payload, ref("sitemap"))
    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer"


@pytest.mark.parametrize("adapter", [GreenhouseAdapter(), LeverAdapter(), AshbyAdapter(),
                                     SmartRecruitersAdapter(), WorkableAdapter(), KekaAdapter(),
                                     ZohoAdapter()])
def test_adapters_return_empty_on_bad_payload(adapter):
    if adapter.source_type in {"greenhouse", "lever", "ashby"}:
        with pytest.raises(SourceParseError, match="invalid_json"):
            adapter.parse(b"not json", ref(adapter.source_type))
    else:
        assert adapter.parse(b"not json", ref(adapter.source_type)) == []


@pytest.mark.parametrize("adapter,fixture,expected_title", [
    (GreenhouseAdapter(), "greenhouse_api.fixture.json", "Software Engineer Intern"),
    (LeverAdapter(), "lever_api.fixture.json", "Backend Developer"),
    (AshbyAdapter(), "ashby_api.fixture.json", "Frontend Engineer"),
])
def test_ats_api_shape_fixtures(adapter, fixture, expected_title):
    payload = (FIXTURES / "sources" / fixture).read_bytes()
    parsed = adapter.parse(payload, ref(adapter.source_type))
    assert len(parsed) == 1
    assert parsed[0].title == expected_title
    assert parsed[0].company_name == "Acme"
    assert parsed[0].url.startswith("https://")


def test_lever_epoch_milliseconds_becomes_utc_datetime():
    payload = (FIXTURES / "sources" / "lever_api.fixture.json").read_bytes()
    posted_at = LeverAdapter().parse(payload, ref("lever"))[0].posted_at
    assert posted_at == "2026-10-25T10:30:00+00:00"


@pytest.mark.parametrize("value", [None, "invalid", "not-a-number", 10**30])
def test_lever_invalid_created_at_is_missing(value):
    payload = json.dumps([{
        "id": "x", "text": "Engineer", "createdAt": value,
        "hostedUrl": "https://jobs.lever.co/acme/x",
    }]).encode()
    assert LeverAdapter().parse(payload, ref("lever"))[0].posted_at is None


def test_ashby_prefers_description_plain():
    payload = (FIXTURES / "sources" / "ashby_api.fixture.json").read_bytes()
    job = AshbyAdapter().parse(payload, ref("ashby"))[0]
    assert job.description == "React and TypeScript role for an early-career engineer."
    assert "descriptionHtml" in job.raw


def test_ats_parser_rejects_unexpected_envelopes():
    with pytest.raises(SourceParseError, match="unexpected_response_shape"):
        GreenhouseAdapter().parse(b'{"postings":[]}', ref("greenhouse"))
    with pytest.raises(SourceParseError, match="unexpected_response_shape"):
        LeverAdapter().parse(b'{"jobs":[]}', ref("lever"))
    with pytest.raises(SourceParseError, match="unexpected_response_shape"):
        AshbyAdapter().parse(b'{"results":[]}', ref("ashby"))
