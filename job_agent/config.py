"""Strict, safety-first configuration loading."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError, SafetyLockError

TOP_LEVEL_KEYS = {
    "dry_run", "database_path", "exports_dir", "logs_dir", "authoritative_workbook",
    "dashboard", "http", "limits",
}
HTTP_KEYS = {"timeout_seconds", "max_retries", "per_host_delay_seconds", "request_cap", "user_agent"}
LIMIT_KEYS = {"max_description_chars", "max_jobs_per_run", "backup_keep"}
DASHBOARD_KEYS = {"host", "port"}
WEIGHT_KEYS = {"role_title", "required_skills", "experience", "location", "education", "company_tier", "recency"}
PREF_KEYS = {"roles", "skills", "experience", "locations", "weights", "quotas", "thresholds"}


def _load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except OSError as exc:
        raise ConfigError(f"cannot read configuration: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML: {path}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"configuration root must be a mapping: {path}")
    return data


def _reject_unknown(data: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ConfigError(f"unknown keys in {where}: {', '.join(unknown)}")


def _require_mapping(data: dict[str, Any], key: str, where: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{where}.{key} must be a mapping")
    return value


def load_config(path: str | Path = "config/config.yaml") -> dict[str, Any]:
    data = _load_yaml(path)
    _reject_unknown(data, TOP_LEVEL_KEYS, "config")
    if data.get("dry_run") is not True:
        raise SafetyLockError("dry_run must be true; live mode is not available")
    dashboard = _require_mapping(data, "dashboard", "config")
    _reject_unknown(dashboard, DASHBOARD_KEYS, "config.dashboard")
    if dashboard.get("host") != "127.0.0.1":
        raise SafetyLockError("dashboard host must be 127.0.0.1")
    port = dashboard.get("port")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigError("dashboard.port must be an integer in 1..65535")
    http = _require_mapping(data, "http", "config")
    _reject_unknown(http, HTTP_KEYS, "config.http")
    limits = _require_mapping(data, "limits", "config")
    _reject_unknown(limits, LIMIT_KEYS, "config.limits")
    if not isinstance(limits.get("max_description_chars"), int) or limits["max_description_chars"] <= 0:
        raise ConfigError("limits.max_description_chars must be a positive integer")
    if not isinstance(limits.get("max_jobs_per_run"), int) or limits["max_jobs_per_run"] <= 0:
        raise ConfigError("limits.max_jobs_per_run must be a positive integer")
    for key in ("database_path", "exports_dir", "logs_dir"):
        if not isinstance(data.get(key), str) or not data[key]:
            raise ConfigError(f"config.{key} must be a non-empty path string")
    return data


def load_preferences(path: str | Path = "config/preferences.yaml") -> dict[str, Any]:
    data = _load_yaml(path)
    _reject_unknown(data, PREF_KEYS, "preferences")
    for key in PREF_KEYS:
        if key not in data:
            raise ConfigError(f"preferences.{key} is required")
    weights = _require_mapping(data, "weights", "preferences")
    _reject_unknown(weights, WEIGHT_KEYS, "preferences.weights")
    if any(not isinstance(weights[k], int) or weights[k] < 0 for k in WEIGHT_KEYS):
        raise ConfigError("preference weights must be non-negative integers")
    if sum(weights.values()) != 100:
        raise ConfigError("preference weights must sum to 100")
    quotas = _require_mapping(data, "quotas", "preferences")
    if not isinstance(quotas.get("total_per_day"), int) or quotas["total_per_day"] <= 0:
        raise ConfigError("preferences.quotas.total_per_day must be positive")
    if not isinstance(quotas.get("per_tier"), dict) or not isinstance(quotas.get("per_company"), int):
        raise ConfigError("preferences.quotas.per_tier and per_company are required")
    experience = _require_mapping(data, "experience", "preferences")
    if not isinstance(experience.get("ceiling_years"), int):
        raise ConfigError("preferences.experience.ceiling_years must be an integer")
    skills = _require_mapping(data, "skills", "preferences")
    for key in ("required", "preferred", "aliases"):
        if key not in skills:
            raise ConfigError(f"preferences.skills.{key} is required")
    return data


def load_sources(path: str | Path = "config/sources.yaml") -> dict[str, Any]:
    data = _load_yaml(path)
    if set(data) != {"sources"} or not isinstance(data["sources"], dict):
        raise ConfigError("sources.yaml must contain exactly one mapping named sources")
    for name, spec in data["sources"].items():
        if not isinstance(spec, dict) or "enabled" not in spec:
            raise ConfigError(f"source {name} must have enabled")
        if not isinstance(spec["enabled"], bool):
            raise ConfigError(f"source {name}.enabled must be boolean")
        request_cap = spec.get("request_cap")
        if isinstance(request_cap, bool) or not isinstance(request_cap, int) or request_cap <= 0:
            raise ConfigError(f"source {name}.request_cap must be a positive integer")
    return data["sources"]


def load_overrides(path: str | Path = "config/overrides.yaml") -> dict[str, Any]:
    data = _load_yaml(path)
    if set(data) != {"overrides"} or not isinstance(data["overrides"], dict):
        raise ConfigError("overrides.yaml must contain exactly one mapping named overrides")
    return data["overrides"]
