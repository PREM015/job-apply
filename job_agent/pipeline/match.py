"""Hard filters. A rejected job never reaches the scorer."""
from __future__ import annotations

from .classify import is_excluded_title


def hard_filter(job: dict, prefs: dict) -> tuple[bool, str | None]:
    if not job.get("is_software"):
        return False, "non_software"
    if is_excluded_title(job.get("title", "")):
        return False, "excluded_title"
    experience = job.get("experience_level", "unknown")
    if experience == "unknown":
        return False, "experience_unknown"
    if experience in set(prefs.get("experience", {}).get("reject_levels", [])):
        return False, "experience_too_high"
    ceiling = int(prefs.get("experience", {}).get("ceiling_years", 2))
    if experience == "3plus" and ceiling < 3:
        return False, "experience_too_high"
    if job.get("country_eligible") is not True:
        if job.get("country") == "unknown":
            return False, "country_unknown"
        return False, "ineligible_country"
    if job.get("status") in {"closed", "expired"}:
        return False, "closed"
    if job.get("work_mode") == "needs_review":
        return False, "work_mode_needs_review"
    if job.get("suppressed"):
        return False, "suppressed"
    if job.get("already_applied"):
        return False, "already_applied"
    return True, None
