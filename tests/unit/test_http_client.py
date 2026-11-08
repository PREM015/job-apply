from __future__ import annotations

import responses

from job_agent.http_client import HttpClient


def allow_robots(host: str, *, body: str = "User-agent: *\nAllow: /\n", status: int = 200) -> None:
    responses.add(
        responses.GET,
        f"https://{host}/robots.txt",
        body=body,
        status=status,
    )


@responses.activate
def test_http_success_and_honest_user_agent():
    allow_robots("acme.example.com")
    responses.add(responses.GET, "https://acme.example.com/jobs", body=b"ok", status=200)

    client = HttpClient(per_host_delay=0)
    result = client.get("https://acme.example.com/jobs")

    assert result.ok is True
    assert result.payload == b"ok"
    assert client.requests_made == 2
    assert responses.calls[1].request.headers["User-Agent"] == client.user_agent


@responses.activate
def test_http_403_is_blocked_without_retry():
    allow_robots("acme.example.com")
    responses.add(responses.GET, "https://acme.example.com/jobs", status=403)
    client = HttpClient(per_host_delay=0, max_retries=1)

    result = client.get("https://acme.example.com/jobs")

    assert result.ok is False
    assert result.error == "blocked"
    assert len(responses.calls) == 2
    assert client.requests_made == 2


@responses.activate
def test_http_429_honours_retry_after(monkeypatch):
    delays = []
    monkeypatch.setattr("job_agent.http_client.time.sleep", lambda seconds: delays.append(seconds))
    allow_robots("acme.example.com")
    responses.add(
        responses.GET, "https://acme.example.com/jobs", status=429,
        headers={"Retry-After": "0.5"},
    )
    responses.add(responses.GET, "https://acme.example.com/jobs", body=b"ok", status=200)

    client = HttpClient(per_host_delay=0, max_retries=1)
    result = client.get("https://acme.example.com/jobs")

    assert result.ok is True
    assert 0.5 in delays
    assert client.requests_made == 3


def test_request_cap_and_invalid_url():
    client = HttpClient(request_cap=0)
    assert client.get("https://acme.example.com").error == "request_cap_reached"
    assert HttpClient().get("ftp://acme.example.com").error == "invalid_url"
    assert HttpClient().get("https://user:pass@acme.example.com").error == "invalid_url"


@responses.activate
def test_robots_disallow_skips_job_request():
    responses.add(
        responses.GET,
        "https://acme.example.com/robots.txt",
        body="User-agent: *\nDisallow: /private\n",
        status=200,
    )
    client = HttpClient(per_host_delay=0)

    result = client.get("https://acme.example.com/private/jobs")

    assert result.error == "robots_disallowed"
    assert client.requests_made == 1
    assert len(responses.calls) == 1


@responses.activate
def test_robots_404_allows_request_and_counts_both_gets():
    responses.add(responses.GET, "https://acme.example.com/robots.txt", status=404)
    responses.add(responses.GET, "https://acme.example.com/jobs", body=b"ok", status=200)
    client = HttpClient(per_host_delay=0)

    result = client.get("https://acme.example.com/jobs")

    assert result.ok
    assert client.requests_made == 2


@responses.activate
def test_robots_failure_fails_closed():
    responses.add(responses.GET, "https://acme.example.com/robots.txt", status=503)
    client = HttpClient(per_host_delay=0)

    result = client.get("https://acme.example.com/jobs")

    assert result.error == "robots_unavailable:503"
    assert client.requests_made == 2
    assert len(responses.calls) == 2


@responses.activate
def test_redirect_is_a_counted_get_and_same_host_redirect_is_allowed():
    allow_robots("acme.example.com")
    responses.add(
        responses.GET,
        "https://acme.example.com/jobs",
        status=302,
        headers={"Location": "/careers"},
    )
    responses.add(responses.GET, "https://acme.example.com/careers", body=b"ok", status=200)
    client = HttpClient(per_host_delay=0, request_cap=3)

    result = client.get("https://acme.example.com/jobs")

    assert result.ok
    assert result.payload == b"ok"
    assert client.requests_made == 3
    assert len(responses.calls) == 3


@responses.activate
def test_cross_host_redirect_is_rejected_before_following():
    allow_robots("acme.example.com")
    responses.add(
        responses.GET,
        "https://acme.example.com/jobs",
        status=302,
        headers={"Location": "https://jobs.other.example/jobs"},
    )
    client = HttpClient(per_host_delay=0)

    result = client.get("https://acme.example.com/jobs")

    assert result.error == "redirect_not_allowed"
    assert client.requests_made == 2
    assert len(responses.calls) == 2


@responses.activate
def test_global_cap_includes_robots_and_redirect_hops():
    allow_robots("acme.example.com")
    responses.add(
        responses.GET,
        "https://acme.example.com/jobs",
        status=302,
        headers={"Location": "/careers"},
    )
    client = HttpClient(per_host_delay=0, request_cap=2)

    result = client.get("https://acme.example.com/jobs")

    assert result.error == "request_cap_reached"
    assert client.requests_made == 2
    assert len(responses.calls) == 2


@responses.activate
def test_cookie_from_robots_response_is_not_sent_to_source():
    responses.add(
        responses.GET,
        "https://acme.example.com/robots.txt",
        body="User-agent: *\nAllow: /\n",
        status=200,
        headers={"Set-Cookie": "session=secret; Path=/"},
    )
    responses.add(responses.GET, "https://acme.example.com/jobs", body=b"ok", status=200)
    client = HttpClient(per_host_delay=0)

    result = client.get("https://acme.example.com/jobs")

    assert result.ok
    assert "Cookie" not in responses.calls[1].request.headers
    assert not client.session.cookies


@responses.activate
def test_host_is_skipped_after_two_403_or_429_responses():
    allow_robots("acme.example.com")
    responses.add(responses.GET, "https://acme.example.com/jobs", status=403)
    responses.add(responses.GET, "https://acme.example.com/jobs", status=429)
    client = HttpClient(per_host_delay=0, max_retries=0)

    first = client.get("https://acme.example.com/jobs")
    second = client.get("https://acme.example.com/jobs")
    third = client.get("https://acme.example.com/jobs")

    assert first.status == 403
    assert second.status == 429
    assert third.error == "host_blocked"
    assert client.requests_made == 3
    assert len(responses.calls) == 3
    assert client.blocked_host_details == [{
        "host": "acme.example.com",
        "reason": "two_or_more_403_or_429_responses",
        "status_codes": [403, 429],
    }]


@responses.activate
def test_retry_limit_is_never_more_than_one(monkeypatch):
    monkeypatch.setattr("job_agent.http_client.time.sleep", lambda _seconds: None)
    allow_robots("acme.example.com")
    responses.add(responses.GET, "https://acme.example.com/jobs", status=500)
    responses.add(responses.GET, "https://acme.example.com/jobs", status=500)
    responses.add(responses.GET, "https://acme.example.com/jobs", body=b"unexpected", status=200)
    client = HttpClient(per_host_delay=0, max_retries=10)

    result = client.get("https://acme.example.com/jobs")

    assert result.status == 500
    assert client.requests_made == 3
    assert len(responses.calls) == 3
