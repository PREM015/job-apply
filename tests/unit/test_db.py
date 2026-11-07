from __future__ import annotations

from pathlib import Path

from tests.support import make_job


def test_migrations_apply_once(db):
    assert db.migrate() == []
    assert db.counts()["jobs"] == 0


def test_company_source_job_roundtrip(db):
    db.upsert_company({"master_id": 1, "name": "Acme", "tier": "Tier 1",
                       "careers_url": "https://acme.example.com", "resolution_status": "resolved"})
    source_id = db.add_source({"company_master_id": 1, "source_type": "greenhouse",
                               "url": "https://boards.greenhouse.io/acme", "enabled": True})
    job = make_job(source_id=source_id)
    job_id, created = db.upsert_job(job)
    assert created is True
    assert db.get_job(job_id)["title"] == "Software Engineer"
    again, created_again = db.upsert_job({**job, "title": "Software Engineer II"})
    assert again == job_id
    assert created_again is False
    assert db.counts()["jobs"] == 1


def test_queue_and_events(db):
    db.upsert_company({"master_id": 1, "name": "Acme"})
    source_id = db.add_source({"company_master_id": 1, "source_type": "greenhouse",
                               "url": "https://boards.greenhouse.io/acme"})
    job_id, _ = db.upsert_job(make_job(source_id=source_id))
    run_id = db.create_run()
    queue_id = db.enqueue(run_id, job_id, 1, 80, "role_title:30")
    db.finish_run(run_id, {"source_count": 1, "fetched_count": 1, "queued_count": 1}, [])
    assert db.get_run(run_id)["queued_count"] == 1
    assert db.list_queue(run_id)[0]["title"] == "Software Engineer"
    db.update_queue_state(queue_id, "reviewed", "owner", "looks good")
    events = db.list_queue_events(queue_id)
    assert [event["new_state"] for event in events] == ["queued", "reviewed"]


def test_applications_and_applied_keys(db):
    db.upsert_company({"master_id": 1, "name": "Acme"})
    source_id = db.add_source({"company_master_id": 1, "source_type": "greenhouse",
                               "url": "https://boards.greenhouse.io/acme"})
    job_id, _ = db.upsert_job(make_job(source_id=source_id))
    app_id = db.create_application(job_id, "applied", notes="owner logged")
    assert db.list_applications()[0]["notes"] == "owner logged"
    keys = db.applied_keys()
    assert "https://acme.example.com/jobs/1" in keys
    assert "fp-1" in keys
    db.update_application(app_id, "interview")
    assert db.list_applications()[0]["status"] == "interview"


def test_suppression(db):
    db.suppress("company", "acme", "no response")
    assert db.is_suppressed("company", "acme") is True
    assert db.is_suppressed("company", "other") is False
    assert db.list_suppressions()[0]["reason"] == "no response"


def test_backup_on_reconnect(tmp_path: Path):
    from job_agent.db.repository import Database

    path = tmp_path / "db.sqlite3"
    db = Database(path)
    db.connect()
    db.migrate()
    db.close()
    db2 = Database(path)
    db2.connect()
    db2.close()
    backups = list((tmp_path / "backups").glob("*.sqlite3"))
    assert backups


def test_restore_database(tmp_path: Path):
    from job_agent.db.backup import restore_database

    source = tmp_path / "backup.sqlite3"
    source.write_bytes(b"backup")
    target = tmp_path / "restored" / "db.sqlite3"
    assert restore_database(source, target) == str(target)
    assert target.read_bytes() == b"backup"


def test_nested_transactions_roll_back_bulk_operations(db):
    import pytest

    with pytest.raises(RuntimeError, match="abort bulk write"):
        with db.transaction():
            db.upsert_company({"master_id": 1, "name": "Acme"})
            db.upsert_company({"master_id": 2, "name": "Beta"})
            raise RuntimeError("abort bulk write")
    assert db.count_companies() == 0
