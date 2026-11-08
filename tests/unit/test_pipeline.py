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
    assert result["counters"]["queued_count"] == 3
    assert db.counts()["jobs"] == 3
    assert db.counts()["queue"] == 6


def test_stored_eligible_jobs_are_queued_when_a_later_run_fetches_nothing(db, prefs):
    fixture = seed(db)
    first = run_pipeline(db, prefs, fixture["batches"])
    second = run_pipeline(db, prefs, [])
    assert first["counters"]["queued_count"] == 3
    assert second["counters"]["queued_count"] == 3
    assert {item["job_id"] for item in second["queue"]} == {
        item["job_id"] for item in first["queue"]
    }


def test_existing_job_refreshes_latest_ineligible_evidence(db, prefs):
    fixture = seed(db)
    first = run_pipeline(db, prefs, fixture["batches"])
    engineer = next(item for item in first["queue"] if item["title"] == "Software Engineer")
    fixture["batches"][0]["jobs"][0]["description"] = (
        "Python and React. Requires 5+ years of professional experience."
    )

    next_run = run_pipeline(db, prefs, fixture["batches"])

    stored = db.get_job(engineer["job_id"])
    assert stored["experience_level"] == "3plus"
    assert engineer["job_id"] not in {item["job_id"] for item in next_run["queue"]}


def test_dismissed_job_stays_excluded_and_saved_state_is_preserved(db, prefs):
    fixture = seed(db)
    first = run_pipeline(db, prefs, fixture["batches"])
    dismissed_id = first["queue"][0]["job_id"]
    saved_id = first["queue"][1]["job_id"]
    db.update_queue_state(first["queue"][0]["queue_id"], "dismissed")
    db.update_queue_state(first["queue"][1]["queue_id"], "saved")

    next_run = run_pipeline(db, prefs, [])

    next_by_id = {item["job_id"]: item for item in next_run["queue"]}
    assert dismissed_id not in next_by_id
    assert next_by_id[saved_id]["state"] == "saved"


def test_incomplete_or_failed_scans_never_close_jobs(db, prefs):
    fixture = seed(db)
    run_pipeline(db, prefs, fixture["batches"])
    greenhouse_job = next(job for job in db.list_jobs() if job["source_id"] == 1)

    run_pipeline(db, prefs, [{
        "source_id": 1, "source_type": "greenhouse", "scan_complete": False, "jobs": [],
    }])
    assert db.get_job(greenhouse_job["job_id"])["status"] == "active"

    run_pipeline(db, prefs, [{
        "source_id": 1, "source_type": "greenhouse", "scan_complete": True,
        "jobs": [], "error": "http_503",
    }])
    assert db.get_job(greenhouse_job["job_id"])["status"] == "active"
    assert db.connection.execute(
        "SELECT COUNT(*) FROM job_source_scan_state WHERE source_id=1"
    ).fetchone()[0] == 0


def test_two_successful_complete_scans_close_missing_job_with_reason(db, prefs):
    fixture = seed(db)
    run_pipeline(db, prefs, fixture["batches"])
    greenhouse_job = next(job for job in db.list_jobs() if job["source_id"] == 1)
    empty_complete_scan = {
        "source_id": 1, "source_type": "greenhouse", "scan_complete": True, "jobs": [],
    }

    run_pipeline(db, prefs, [empty_complete_scan])
    assert db.get_job(greenhouse_job["job_id"])["status"] == "active"
    run_pipeline(db, prefs, [{
        "source_id": 1, "source_type": "greenhouse", "scan_complete": True,
        "jobs": [], "error": "http_503",
    }])
    assert db.get_job(greenhouse_job["job_id"])["status"] == "active"
    misses = db.connection.execute(
        "SELECT consecutive_misses FROM job_source_scan_state WHERE source_id=1 AND job_id=?",
        (greenhouse_job["job_id"],),
    ).fetchone()[0]
    assert misses == 1
    run_pipeline(db, prefs, [empty_complete_scan])

    closed = db.get_job(greenhouse_job["job_id"])
    assert closed["status"] == "closed"
    assert closed["is_active"] == 0
    assert closed["closed_at"]
    assert closed["closed_reason"] == (
        "missing from two consecutive successful complete source scans"
    )


def test_invalid_record_makes_an_otherwise_complete_scan_incomplete(db, prefs):
    fixture = seed(db)
    run_pipeline(db, prefs, fixture["batches"])
    greenhouse_job = next(job for job in db.list_jobs() if job["source_id"] == 1)
    db.record_complete_source_scan(1, set())
    invalid_job = {
        "source_id": 1, "source_type": "greenhouse", "source_job_id": "bad",
        "title": "", "company_name": "Acme", "url": "https://example.com/job",
    }

    run_pipeline(db, prefs, [{
        "source_id": 1, "source_type": "greenhouse", "scan_complete": True,
        "jobs": [invalid_job],
    }])

    row = db.connection.execute(
        "SELECT consecutive_misses FROM job_source_scan_state WHERE source_id=1 AND job_id=?",
        (greenhouse_job["job_id"],),
    ).fetchone()
    assert row[0] == 1
    assert db.get_job(greenhouse_job["job_id"])["status"] == "active"


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
