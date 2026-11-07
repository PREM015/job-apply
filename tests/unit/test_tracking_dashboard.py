from __future__ import annotations

from job_agent.dashboard import actions, queries
from job_agent.tracking.applications import log_application
from job_agent.tracking.queue import set_state
from tests.support import make_job


def seed(db):
    db.upsert_company({"master_id": 1, "name": "Acme"})
    source_id = db.add_source({"company_master_id": 1, "source_type": "greenhouse",
                               "url": "https://boards.greenhouse.io/acme"})
    job_id, _ = db.upsert_job(make_job(source_id=source_id))
    run_id = db.create_run()
    queue_id = db.enqueue(run_id, job_id, 1, 80, "role_title:30")
    db.finish_run(run_id, {"source_count": 1, "fetched_count": 1, "queued_count": 1}, [])
    return job_id, queue_id


def test_tracking_and_dashboard_queries(db):
    job_id, queue_id = seed(db)
    assert len(queries.queue(db)) == 1
    assert queries.job_detail(db, job_id)["title"] == "Software Engineer"
    assert queries.runs(db)[0]["queued_count"] == 1
    actions.update_status(db, queue_id, "interested", "good fit")
    assert queries.queue(db)[0]["state"] == "interested"
    app_id = actions.add_application(db, job_id, "applied", notes="owner")
    assert queries.applications(db)[0]["application_id"] == app_id
    actions.update_application_status(db, app_id, "interview")
    assert queries.applications(db)[0]["status"] == "interview"


def test_tracking_refuses_automatic_submission(db):
    job_id, _ = seed(db)
    try:
        log_application(db, job_id, "auto")
    except PermissionError:
        pass
    else:
        raise AssertionError("automatic submission was accepted")


def test_invalid_queue_state(db):
    _, queue_id = seed(db)
    try:
        set_state(db, queue_id, "not-a-state")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid state was accepted")
