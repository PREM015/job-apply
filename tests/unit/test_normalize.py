from __future__ import annotations

from job_agent.pipeline.normalize import (bounded_text, canonicalize_url, clean_text,
                                          normalize_job, parse_date, strip_html)


def test_canonicalize_url_removes_tracking_and_fragment():
    url = "HTTPS://Example.COM:443/jobs/1/?utm_source=x&b=2&a=1#top"
    assert canonicalize_url(url) == "https://example.com/jobs/1/?a=1&b=2"


def test_canonicalize_url_resolves_relative():
    assert canonicalize_url("jobs/1", "https://acme.example.com/careers/") == "https://acme.example.com/careers/jobs/1"


def test_canonicalize_url_rejects_non_http():
    assert canonicalize_url("javascript:alert(1)") == ""
    assert canonicalize_url("") == ""


def test_strip_html_and_clean_text():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert clean_text("  a\n\tb  ") == "a b"


def test_bounded_text_respects_limit():
    assert bounded_text("a" * 50, limit=10) == "a" * 10


def test_parse_date_variants():
    assert parse_date("2026-11-06T10:00:00Z") == "2026-11-06T10:00:00+00:00"
    assert parse_date("Fri, 06 Nov 2026 10:00:00 GMT") == "2026-11-06T10:00:00+00:00"
    assert parse_date("not a date") is None
    assert parse_date(None) is None


def test_normalize_job_accepts_dataclass():
    from job_agent.models import RawJob

    raw = RawJob(source_type="greenhouse", title="Dev", company_name="Acme",
                 url="https://acme.example.com/jobs/1?utm_source=x", location="Pune",
                 description="<p>Python</p>", posted_at="2026-11-06T00:00:00Z")
    job = normalize_job(raw)
    assert job["canonical_url"] == "https://acme.example.com/jobs/1"
    assert job["description_text"] == "Python"
    assert job["posted_at"] == "2026-11-06T00:00:00+00:00"
