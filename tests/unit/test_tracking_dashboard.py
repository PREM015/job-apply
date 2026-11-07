from __future__ import annotations

import ast
from pathlib import Path

import pytest

from job_agent.dashboard import actions, queries
from job_agent.dashboard.app import DASHBOARD_PAGES, assert_local_host
from job_agent.errors import SafetyLockError
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


def test_dashboard_pages_and_manual_add(db):
    seed(db)
    assert len(queries.today_apply_list(db)) == 1
    assert len(queries.needs_review(db)) == 1
    assert len(queries.all_jobs(db)) == 1
    assert len(queries.companies(db)) == 1
    assert len(queries.source_health(db)) == 1
    assert queries.stats(db)["jobs"] == 1
    job_id, created = actions.add_manual_job(
        db, "https://example.com/jobs/manual", "Backend Engineer", "Example",
        "Remote", "remote", "Python",
    )
    assert created is True
    assert queries.job_detail(db, job_id)["company_name"] == "Example"
    assert queries.job_detail(db, job_id)["origin"] == "manual"
    same_id, created_again = actions.add_manual_job(
        db, "https://example.com/jobs/manual", "Backend Engineer", "Example",
    )
    assert same_id == job_id
    assert created_again is False


def test_dashboard_is_local_only_and_has_no_network_imports():
    assert_local_host("127.0.0.1")
    with pytest.raises(SafetyLockError):
        assert_local_host("0.0.0.0")
    dashboard_dir = Path(__file__).resolve().parents[2] / "job_agent" / "dashboard"
    network_modules = {"requests", "httpx", "urllib", "socket", "aiohttp"}
    for path in dashboard_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or "", *(alias.name for alias in node.names)]
            else:
                modules = []
            for module in modules:
                parts = module.split(".")
                assert not network_modules.intersection(parts)
                assert not {"apply", "submit"}.intersection(parts)
            if isinstance(node, ast.Call):
                called = node.func
                while isinstance(called, ast.Attribute):
                    called = called.value
                if isinstance(called, ast.Name):
                    assert called.id not in network_modules


def test_dashboard_pages_and_launcher_are_local():
    required_pages = {
        "Today's Apply List", "Job Detail", "All Jobs", "Applications", "Needs Review",
        "Companies", "Source Health", "Stats", "Portal Links", "Saved Alert Checklist", "Add Job",
    }
    assert required_pages.issubset(DASHBOARD_PAGES)
    root = Path(__file__).resolve().parents[2]
    launcher = (root / "run_dashboard.bat").read_text(encoding="utf-8")
    assert r".venv\Scripts\activate.bat" in launcher
    assert "--server.address 127.0.0.1" in launcher
    assert "-m streamlit run job_agent\\dashboard\\app.py" in launcher


def test_invalid_queue_state(db):
    _, queue_id = seed(db)
    try:
        set_state(db, queue_id, "not-a-state")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid state was accepted")
