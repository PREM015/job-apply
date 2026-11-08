"""Pure, deterministic scoring with an explainable breakdown."""
from __future__ import annotations

from datetime import datetime, timezone

from ..models import ScoreResult


def _role_points(title: str, prefs: dict, weight: int) -> int:
    lowered = title.lower()
    for role in prefs.get("roles", {}).get("accepted", []):
        if role.lower() in lowered:
            return weight
    return 0


def _skill_points(job: dict, prefs: dict, weight: int) -> int:
    required = prefs.get("skills", {}).get("required", [])
    if not required:
        return 0
    matched = set(job.get("skills_required", []))
    return int(round(weight * len(matched) / len(required)))


def _experience_points(level: str, prefs: dict, weight: int) -> int:
    return weight if level in set(prefs.get("experience", {}).get("acceptable_levels", [])) else 0


def _location_points(job: dict, prefs: dict, weight: int) -> int:
    location_cfg = prefs.get("locations", {})
    location = f"{job.get('structured_location', '')} {job.get('location_raw', '')}".lower()
    if job.get("work_mode") == "remote" and location_cfg.get("allow_remote", True):
        return weight
    for city in location_cfg.get("cities", []):
        if city.lower() in location:
            return weight
    if job.get("country") in {str(c).upper() for c in location_cfg.get("countries", [])}:
        return weight
    return 0


def _education_points(description: str, weight: int) -> int:
    text = description.lower()
    markers = ("bachelor", "b.tech", "b.e", "be/", "degree", "bsc", "b.sc", "undergraduate")
    return weight if any(marker in text for marker in markers) else 0


def _tier_points(tier: str | None, weight: int) -> int:
    mapping = {"1": 1.0, "2": 0.75, "3": 0.5, "4": 0.25}
    text = str(tier or "").lower().replace("tier", "").strip()
    return int(round(weight * mapping.get(text, 0.0)))


def _recency_points(posted_at: str | None, weight: int) -> int:
    if not posted_at:
        return 0
    try:
        posted = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
    except ValueError:
        return 0
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    days = max(0, (datetime.now(timezone.utc) - posted).days)
    if days <= 7:
        return weight
    if days <= 30:
        return int(round(weight / 2))
    return 0


def score_job(job: dict, prefs: dict, tier: str | None = None) -> ScoreResult:
    weights = prefs["weights"]
    breakdown = {
        "role_title": _role_points(job.get("title", ""), prefs, weights["role_title"]),
        "required_skills": _skill_points(job, prefs, weights["required_skills"]),
        "experience": _experience_points(job.get("experience_level", "unknown"), prefs, weights["experience"]),
        "location": _location_points(job, prefs, weights["location"]),
        "education": _education_points(job.get("description_text", ""), weights["education"]),
        "company_tier": _tier_points(tier or job.get("tier"), weights["company_tier"]),
        "recency": _recency_points(job.get("posted_at"), weights["recency"]),
    }
    total = sum(breakdown.values())
    reasons = [f"{key}:{value}" for key, value in breakdown.items() if value]
    return ScoreResult(total=int(min(100, max(0, total))), breakdown=breakdown, reasons=reasons)
