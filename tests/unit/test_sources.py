from __future__ import annotations

import json

import pytest

from job_agent.sources.ashby import AshbyAdapter
from job_agent.sources.base import SourceRef
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
    assert adapter.parse(b"not json", ref(adapter.source_type)) == []
