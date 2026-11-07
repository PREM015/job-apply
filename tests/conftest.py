from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from job_agent.config import load_preferences
from job_agent.db.repository import Database
from tests.support import ROOT


@pytest.fixture
def prefs() -> dict:
    return load_preferences(ROOT / "config" / "preferences.example.yaml")


@pytest.fixture
def db(tmp_path: Path):
    database = Database(tmp_path / "job_agent.sqlite3")
    database.connect()
    database.migrate()
    yield database
    database.close()


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    data = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    data["database_path"] = str(tmp_path / "db.sqlite3")
    data["exports_dir"] = str(tmp_path / "exports")
    data["logs_dir"] = str(tmp_path / "logs")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path
