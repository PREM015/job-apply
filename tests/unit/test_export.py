from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from job_agent.io.excel_exporter import export_workbook
from tests.support import make_job


def seed_job(db):
    db.upsert_company({"master_id": 1, "name": "Acme"})
    source_id = db.add_source({"company_master_id": 1, "source_type": "greenhouse",
                               "url": "https://boards.greenhouse.io/acme"})
    job_id, _ = db.upsert_job(make_job(source_id=source_id))
    run_id = db.create_run()
    db.enqueue(run_id, job_id, 1, 80, "role_title:30")
    db.finish_run(run_id, {"source_count": 1, "fetched_count": 1, "queued_count": 1}, [])
    return job_id


def test_export_creates_new_workbook(db, tmp_path):
    seed_job(db)
    result = export_workbook(db, tmp_path / "exports" / "jobs.xlsx", tmp_path / "exports")
    workbook = openpyxl.load_workbook(result["path"], read_only=True)
    assert set(workbook.sheetnames) == {"Daily Queue", "All Jobs", "Applications", "Companies", "Runs", "Rejected"}
    workbook.close()


def test_export_refuses_master_and_outside_and_existing(db, tmp_path):
    seed_job(db)
    with pytest.raises(PermissionError):
        export_workbook(db, tmp_path / "Master_Job_Tracker_final.xlsx", tmp_path)
    with pytest.raises(PermissionError):
        export_workbook(db, tmp_path / "outside.xlsx", tmp_path / "exports")
    target = tmp_path / "exports" / "jobs.xlsx"
    export_workbook(db, target, tmp_path / "exports")
    with pytest.raises(FileExistsError):
        export_workbook(db, target, tmp_path / "exports")
    export_workbook(db, target, tmp_path / "exports", force=True)
