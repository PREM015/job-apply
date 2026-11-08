from __future__ import annotations

import json

from job_agent.pipeline.run import run_pipeline
from tests.support import FIXTURES


def seed(db):
    fixture = json.loads((FIXTURES / "e2e_fixture.json").read_text(encoding="utf-8"))
    for company in fixture["companies"]:
        db.upsert_company(company)
    ids = []
    for source in fixture["sources"]:
        ids.append(db.add_source(source))
    for batch, source_id in zip(fixture["batches"][:2], ids):
        batch["source_id"] = source_id
    return fixture


def test_pipeline_end_to_end(db, prefs):
    fixture = seed(db)
    result = run_pipeline(db, prefs, fixture["batches"])
    assert result["counters"]["fetched_count"] == 5
    assert result["counters"]["normalized_count"] == 5
    assert result["counters"]["rejected_count"] == 2
    assert result["counters"]["duplicate_count"] == 0
    assert result["counters"]["queued_count"] == 3
    assert result["errors"] == ["source_error:jsonld:http_403"]
    assert {item["title"] for item in result["queue"]} == {"Software Engineer", "Backend Developer", "Frontend Engineer"}
    assert db.counts()["jobs"] == 3
    assert db.counts()["queue"] == 3
    assert db.list_sources()[0]["last_status"] == "ok"
    assert db.list_sources()[0]["fail_count"] == 0


def test_pipeline_second_run_is_idempotent(db, prefs):
    fixture = seed(db)
    run_pipeline(db, prefs, fixture["batches"])
    result = run_pipeline(db, prefs, fixture["batches"])
    assert result["counters"]["duplicate_count"] == 3
    assert result["counters"]["queued_count"] == 0
    assert db.counts()["jobs"] == 3
    assert db.counts()["queue"] == 3


def test_pipeline_skips_already_applied(db, prefs):
    fixture = seed(db)
    first = run_pipeline(db, prefs, fixture["batches"])
    applied_job_id = first["queue"][0]["job_id"]
    db.create_application(applied_job_id, "applied")
    result = run_pipeline(db, prefs, fixture["batches"])
    assert any(reason["reason"] == "already_applied" for reason in result["rejections"])
    assert result["counters"]["queued_count"] < 3


def test_pipeline_records_source_failure(db, prefs):
    fixture = seed(db)
    fixture["batches"][0]["error"] = "timeout"
    fixture["batches"][0]["jobs"] = []
    run_pipeline(db, prefs, fixture["batches"])
    source = db.list_sources()[0]
    assert source["fail_count"] == 1
    assert source["last_status"] == "http_error"


def test_pipeline_preserves_origin_and_optional_score_floor(db, prefs):
    fixture = seed(db)
    batches = fixture["batches"][:2]
    for batch in batches:
        batch["origin"] = "LIVE"

    result = run_pipeline(db, prefs, batches, minimum_score=0, run_mode="live_discovery")

    assert result["counters"]["queued_count"] == 3
    assert all(db.get_job(item["job_id"])["origin"] == "LIVE" for item in result["queue"])
    assert db.get_run(result["run_id"])["mode"] == "live_discovery"


def test_pipeline_rejects_live_jobs_below_score_floor(db, prefs):
    fixture = seed(db)
    result = run_pipeline(db, prefs, fixture["batches"], minimum_score=100)

    assert result["counters"]["score_floor_rejected_count"] == 3
    assert result["counters"]["queued_count"] == 0
    assert db.counts()["jobs"] == 0
    assert sum(item["reason"] == "score_below_manual_apply_min" for item in result["rejections"]) == 3


def test_pipeline_rejects_invalid_score_floor(db, prefs):
    fixture = seed(db)

    try:
        run_pipeline(db, prefs, fixture["batches"], minimum_score=101)
    except ValueError as exc:
        assert "minimum_score" in str(exc)
    else:
        raise AssertionError("invalid score floor was accepted")
