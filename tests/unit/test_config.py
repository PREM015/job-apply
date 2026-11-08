from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from job_agent.config import load_config, load_overrides, load_preferences, load_sources
from job_agent.errors import ConfigError, SafetyLockError
from tests.support import ROOT


def test_valid_config_loads():
    config = load_config(ROOT / "config" / "config.yaml")
    assert config["dry_run"] is True
    assert config["database_path"] == "data/job_agent.sqlite3"


def test_live_mode_is_rejected(tmp_path):
    data = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    data["dry_run"] = False
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(SafetyLockError):
        load_config(path)


def test_non_local_dashboard_is_rejected(tmp_path):
    data = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    data["dashboard"]["host"] = "0.0.0.0"
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(SafetyLockError):
        load_config(path)


def test_unknown_config_key_is_rejected(tmp_path):
    data = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    data["surprise"] = True
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_preferences_example_is_valid_and_weights_sum_100():
    prefs = load_preferences(ROOT / "config" / "preferences.example.yaml")
    assert sum(prefs["weights"].values()) == 100


def test_preferences_example_loads_with_application_schema():
    prefs = load_preferences(ROOT / "config" / "preferences.example.yaml")
    assert prefs["experience"]["ceiling_years"] == 2
    assert prefs["locations"]["countries"] == ["IN"]


def test_old_owner_preferences_keys_are_rejected(tmp_path: Path):
    path = tmp_path / "preferences.owner-original.yaml"
    path.write_text(
        """
target_roles: [Developer]
skills: [Python]
max_years_experience: 2
locations: [Bihar, India]
work_modes: [hybrid]
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="unknown keys.*max_years_experience"):
        load_preferences(path)


def test_bad_weights_are_rejected(tmp_path):
    data = yaml.safe_load((ROOT / "config" / "preferences.example.yaml").read_text(encoding="utf-8"))
    data["weights"]["role_title"] = 99
    path = tmp_path / "prefs.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_preferences(path)


def test_sources_and_overrides_load():
    sources = load_sources(ROOT / "config" / "sources.yaml")
    assert sources["greenhouse"]["enabled"] is True
    assert sources["keka"]["enabled"] is False
    assert load_overrides(ROOT / "config" / "overrides.yaml") == {}
