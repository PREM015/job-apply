from __future__ import annotations

import json
import subprocess
import sys

import yaml

from job_agent.cli import main
from job_agent.dashboard.app import assert_local_host
from job_agent.errors import SafetyLockError
from tests.support import FIXTURES, ROOT


def test_live_flag_is_refused(config_path, capsys):
    code = main(["--live", "--config", str(config_path), "db-check"])
    assert code == 2
    assert "SAFETY LOCK" in capsys.readouterr().err


def test_legacy_main_refuses_live():
    result = subprocess.run([sys.executable, "main.py", "--live"], cwd=ROOT,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 2
    assert "SAFETY LOCK" in result.stderr


def test_legacy_job_agent_constructor_refuses_live():
    import main as legacy

    try:
        legacy.JobAgent(dry_run=False)
    except SafetyLockError:
        pass
    else:
        raise AssertionError("live JobAgent was constructed")


def test_legacy_run_is_disabled():
    import main as legacy

    agent = legacy.JobAgent(dry_run=True)
    try:
        agent.run()
    except SafetyLockError:
        pass
    else:
        raise AssertionError("legacy run was allowed")


def test_dashboard_binds_localhost_only():
    assert assert_local_host("127.0.0.1") is None
    try:
        assert_local_host("0.0.0.0")
    except SafetyLockError:
        pass
    else:
        raise AssertionError("non-local host was accepted")


def test_cli_run_report_export_and_db_check(config_path, tmp_path, capsys):
    prefs = ROOT / "config" / "preferences.example.yaml"
    assert prefs.exists()
    run = main(["--config", str(config_path), "run", "--fixtures", str(FIXTURES / "e2e_fixture.json"),
                "--preferences", str(prefs)])
    assert run == 0
    output = json.loads(capsys.readouterr().out)
    assert output["counters"]["queued_count"] == 3

    report = main(["--config", str(config_path), "report"])
    assert report == 0
    report_data = json.loads(capsys.readouterr().out)
    assert len(report_data["queue"]) == 3

    export = main(["--config", str(config_path), "export", "--out",
                   str(tmp_path / "exports" / "daily.xlsx")])
    assert export == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["sha256"]
    assert (tmp_path / "exports" / "daily.xlsx").exists()

    check = main(["--config", str(config_path), "db-check"])
    assert check == 0
    counts = json.loads(capsys.readouterr().out)
    assert counts["counts"]["jobs"] == 3


def test_cli_import_companies(config_path, tmp_path, capsys):
    import openpyxl

    path = tmp_path / "companies.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Companies"
    sheet.append(["Master ID", "Company Name", "Priority Tier (Best Available)",
                  "Application Status", "Official Careers Page", "Current Openings URL", "Company Website"])
    sheet.append([7, "Seven", "Tier 1", "", "https://boards.greenhouse.io/seven", "", ""])
    workbook.save(path)
    code = main(["--config", str(config_path), "import-companies", "--workbook", str(path), "--commit"])
    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["companies"] == 1
    assert output["hash_unchanged"] is True
