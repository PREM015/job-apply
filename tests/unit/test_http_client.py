from __future__ import annotations

import pytest
import responses

from job_agent.http_client import HttpClient


@responses.activate
def test_http_success():
    responses.add(responses.GET, "https://acme.example.com/jobs", body=b"ok", status=200)
    result = HttpClient(per_host_delay=0).get("https://acme.example.com/jobs")
    assert result.ok is True
    assert result.payload == b"ok"


@responses.activate
def test_http_403_is_blocked_without_retry():
    responses.add(responses.GET, "https://acme.example.com/jobs", status=403)
    client = HttpClient(per_host_delay=0, max_retries=3)
    result = client.get("https://acme.example.com/jobs")
    assert result.ok is False
    assert result.error == "blocked"
    assert len(responses.calls) == 1


@responses.activate
def test_http_429_honours_retry_after(monkeypatch):
    delays = []
    monkeypatch.setattr("job_agent.http_client.time.sleep", lambda seconds: delays.append(seconds))
    responses.add(responses.GET, "https://acme.example.com/jobs", status=429, headers={"Retry-After": "0.5"})
    responses.add(responses.GET, "https://acme.example.com/jobs", body=b"ok", status=200)
    client = HttpClient(per_host_delay=0, max_retries=1)
    result = client.get("https://acme.example.com/jobs")
    assert result.ok is True
    assert 0.5 in delays


def test_request_cap_and_invalid_url():
    client = HttpClient(request_cap=0)
    assert client.get("https://acme.example.com").error == "request_cap_reached"
    assert HttpClient().get("ftp://acme.example.com").error == "invalid_url"


def test_per_host_cap():
    client = HttpClient(per_host_delay=0, request_cap=100)
    client._host_counts["acme.example.com"] = 5
    assert client.get("https://acme.example.com/jobs").error == "host_cap_reached"
