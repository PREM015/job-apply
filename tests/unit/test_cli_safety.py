from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from job_agent import cli
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


def test_tracker_resolution_prefers_authoritative_master(tmp_path, monkeypatch):
    import excel_io

    authoritative = tmp_path / "authoritative.xlsx"
    local_starter = tmp_path / "Master_Job_Tracker_final.xlsx"
    authoritative.touch()
    local_starter.touch()
    monkeypatch.setattr(excel_io, "AUTHORITATIVE_TRACKER", authoritative)
    monkeypatch.chdir(tmp_path)
    assert excel_io.get_tracker_path() == str(authoritative)


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


def test_cli_run_report_export_and_db_check(config_path, tmp_path, capsys, monkeypatch):
    prefs = ROOT / "config" / "preferences.example.yaml"
    assert prefs.exists()
    fixture_db = tmp_path / "fixture_job_agent.sqlite3"
    monkeypatch.setattr(cli, "FIXTURE_DATABASE_PATH", fixture_db)
    run = main(["--config", str(config_path), "run", "--fixtures", str(FIXTURES / "e2e_fixture.json"),
                "--preferences", str(prefs)])
    assert run == 0
    output = json.loads(capsys.readouterr().out)
    assert output["counters"]["queued_count"] == 3
    assert output["dataset"] == "FIXTURE"
    configured_real_db = Path(yaml.safe_load(config_path.read_text(encoding="utf-8"))["database_path"])
    assert not configured_real_db.exists()

    report = main(["--config", str(config_path), "--db", str(fixture_db), "report"])
    assert report == 0
    report_data = json.loads(capsys.readouterr().out)
    assert len(report_data["queue"]) == 3

    export = main(["--config", str(config_path), "--db", str(fixture_db), "export", "--out",
                   str(tmp_path / "exports" / "daily.xlsx")])
    assert export == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["sha256"]
    assert (tmp_path / "exports" / "daily.xlsx").exists()

    check = main(["--config", str(config_path), "--db", str(fixture_db), "db-check"])
    assert check == 0
    counts = json.loads(capsys.readouterr().out)
    assert counts["counts"]["jobs"] == 3


def test_cli_fixture_run_rejects_real_database(config_path, tmp_path, capsys):
    code = main([
        "--config", str(config_path), "--db", str(tmp_path / "real.sqlite3"),
        "run", "--fixtures", str(FIXTURES / "e2e_fixture.json"),
    ])
    assert code == 2
    assert "fixture runs are confined to data/fixture_job_agent.sqlite3" in capsys.readouterr().err


def test_cli_run_requires_preferences_file(config_path, tmp_path, capsys):
    code = main([
        "--config", str(config_path),
        "run", "--fixtures", str(FIXTURES / "e2e_fixture.json"),
        "--preferences", str(tmp_path / "missing-preferences.yaml"),
    ])
    assert code == 2
    assert "NETWORK LOCK: preferences file is required" in capsys.readouterr().err


def test_daily_launcher_is_locked_without_owner_preferences(config_path, capsys):
    root = ROOT
    launcher = (root / "run_daily.bat").read_text(encoding="utf-8")
    assert 'if not exist "config\\preferences.yaml"' in launcher
    assert "NETWORK LOCK:" in launcher
    code = main([
        "--config", str(config_path), "doctor",
        "--preferences", str(root / "config" / "preferences.yaml.missing"),
    ])
    assert code == 0
    output = capsys.readouterr().out
    assert "Live mode: DISABLED" in output
    assert "Network lock: LOCKED" in output


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
