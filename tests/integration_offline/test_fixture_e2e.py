from __future__ import annotations

import json

import openpyxl
import pytest

from job_agent.io.excel_exporter import export_workbook
from job_agent.pipeline.run import run_pipeline
from tests.support import FIXTURES


def test_fixture_pipeline_never_touches_network(db, prefs, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr("requests.Session.get", forbidden)
    fixture = json.loads((FIXTURES / "e2e_fixture.json").read_text(encoding="utf-8"))
    for company in fixture["companies"]:
        db.upsert_company(company)
    source_ids = [db.add_source(source) for source in fixture["sources"]]
    for batch, source_id in zip(fixture["batches"][:2], source_ids):
        batch["source_id"] = source_id
    result = run_pipeline(db, prefs, fixture["batches"])
    assert result["counters"]["queued_count"] == 3
    exports = tmp_path / "exports"
    exported = export_workbook(db, exports / "fixture.xlsx", exports)
    workbook = openpyxl.load_workbook(exported["path"], read_only=True)
    assert "Daily Queue" in workbook.sheetnames
    assert workbook["Daily Queue"].max_row == 4
    workbook.close()
