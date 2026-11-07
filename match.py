#!/usr/bin/env python3
import yaml
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Role relevance configuration
# ---------------------------------------------------------------------------
# Keywords that, if present in the job title or description, make the role
# acceptable for a fresher / internship search.
ACCEPTED_ROLE_KEYWORDS = [
    "software engineer", "developer", "intern", "associate", "graduate engineer",
    "junior", "entry-level", "fresher", "technical", "programmer", "code",
    "full.stack", "fullstack", "frontend", "backend", "react", "next.js",
    "node.js", "express", "php", "laravel", "python", "java", "c++",
    "qa", "test", "quality", "automation", "devops", "site reliability",
]

# Keywords that, if present in the job title, cause an immediate reject
# (these are senior / irrelevant roles for a fresher search).
REJECTED_ROLE_KEYWORDS = [
    "staff engineer", "principal engineer", "senior software engineer",
    "architect", "engineering manager", "engineering director",
    "technical program manager", "product manager", "product owner",
    "account manager", "sales", "marketing", "business development",
    "customer support", "technical account manager", "client success",
    "director", "vp", "head of", "chief",
]

# ---------------------------------------------------------------------------
# Skill priority & alias map (avoids duplicate scoring)
# ---------------------------------------------------------------------------
PRIMARY_SKILLS = {
    "react", "next.js", "javascript", "typescript", "node.js", "nodejs",
    "express", "postgresql", "mongodb", "mern", "full.stack", "fullstack",
}

SECONDARY_SKILLS = {
    "mysql", "sql", "prisma", "tailwind", "rest", "rest api", "redis",
    "nestjs", "git", "docker", "python", "c++",
}

# Alias map normalises common variants so they are counted once.
ALIAS_MAP = {
    "node.js": "node",
    "nodejs": "node",
    "react.js": "react",
    "reactjs": "react",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "full-stand": "fullstack",
    "full stack": "fullstack",
    "fullstack": "fullstack",
}


def _normalize_skill(skill: str) -> str:
    """Lower‑case and map via ALIAS_MAP."""
    s = skill.lower().strip()
    return ALIAS_MAP.get(s, s)


def _role_matches(title: str, desc: str) -> bool:
    """Return True if the job title/description is considered a fresher‑relevant role."""
    combined = (title + " " + desc).lower()
    # Immediate reject if any rejected keyword appears in the title
    for kw in REJECTED_ROLE_KEYWORDS:
        if kw in combined:
            return False
    # Accept if any accepted keyword appears (or if no accepted keyword but also no rejected)
    # We treat a role as acceptable if at least one accepted keyword is present,
    # unless the title is very generic (e.g., "engineer") – in that case we still accept.
    for kw in ACCEPTED_ROLE_KEYWORDS:
        if kw in combined:
            return True
    # If no accepted keyword but also no rejected keyword, we default to acceptable
    # (the experience filter will decide later).
    return True


def _experience_eligible(desc: str, max_exp: int) -> bool:
    """Check if the job's experience requirement is compatible with max_exp.

    - max_exp = 0 means fresher (no mandatory >=1 year).
    - We distinguish mandatory vs preferred.
    """
    # Extract years if mentioned
    m = re.search(r"(\d+)\s*(\+)?\s*years?", desc.lower())
    if not m:
        return True  # no explicit years -> assume eligible
    years = int(m.group(1))
    # Determine if the requirement is mandatory
    mandatory_kw = ["required", "must", "need"]
    is_mandatory = any(kw in desc.lower() for kw in mandatory_kw)
    if max_exp == 0 and years >= 1 and is_mandatory:
        return False
    # For max_exp > 0 we could be looser, but currently keep as‑is
    return True


def _education_eligible(desc: str) -> bool:
    """Very rough check: reject if PhD is mandatory unless the description
    also mentions entry‑level or fresher context."""
    if re.search(r"\bph\.?d\b", desc.lower()) and not re.search(
        r"\bfresher\b|\bentry.level\b|\b0–2 years\b|\b0–1 years\b", desc.lower()
    ):
        # PhD mentioned without any fresher context -> likely ineligible
        return False
    return True


# ---------------------------------------------------------------------------
# Skill scoring – deduplicated and capped
# ---------------------------------------------------------------------------
def _score_skills(must_have: list, nice_to_have: list, title: str, desc: str) -> tuple:
    """Return (score_contrib, matched_skills_list, reasons).

    - each skill counted only once (via seen sets)
    - primary skills add 10 each, secondary add 5 each
    - total capped at 30 for skills (the original code had min(30, len*10) but we
      now split primary/secondary and still cap at 30 overall)
    """
    seen_must = set()
    seen_nice = set()
    score = 0
    matched_must = []
    matched_nice = []

    # Normalise and score must‑have
    for skill in must_have:
        norm = _normalize_skill(skill)
        if norm in seen_must:
            continue
        seen_must.add(norm)
        if norm in PRIMARY_SKILLS:
            score += 10
            matched_must.append(norm)
        elif norm in SECONDARY_SKILLS:
            score += 5
            matched_nice.append(norm)

    # Normalise and score nice‑to‑have
    for skill in nice_to_have:
        norm = _normalize_skill(skill)
        if norm in seen_nice:
            continue
        seen_nice.add(norm)
        if norm in PRIMARY_SKILLS:
            score += 10
            matched_must.append(norm)  # also count as must for consistency
        elif norm in SECONDARY_SKILLS:
            score += 5
            matched_nice.append(norm)

    # Cap total skill score at 30
    score = min(30, score)

    # Build reasons string
    all_matched = matched_must + matched_nice
    reasons = f"skills:{','.join(all_matched[:3])}" if all_matched else ""

    return score, reasons


# ---------------------------------------------------------------------------
# Core scoring function – called by the agent
# ---------------------------------------------------------------------------
def score_job(job, config, profile):
    score = 0
    reasons = []

    title = str(job.get("Job Title", "")).lower()
    desc = str(job.get("Description", "")).lower()
    location = str(job.get("Location", "")).lower()

    # ---- Title match (role relevance) ---------------------------------
    # If the role is rejected outright, we give a very low score and let
    # decide_action skip it.
    if not _role_matches(job.get("Job Title", ""), job.get("Description", "")):
        # Very low title score, but we still continue for skill scoring;
        # the experience filter will reject it later.
        score += 5  # tiny bonus just to record why it was considered
        reasons.append("title:generic or rejected role")
    else:
        # Normal title match bonus (40 as before) – but only if not rejected
        # We still give the 40 but will later possibly reject via eligibility.
        score += 40
        reasons.append(f"title:{job.get('Job Title')}")

    # ---- Skills -------------------------------------------------------
    must_have = [s.lower() for s in config.get("must_have_skills", [])]
    nice_to_have = [s.lower() for s in config.get("nice_to_have_skills", [])]
    skill_score, skill_reasons = _score_skills(must_have, nice_to_have, title, desc)
    score += skill_score
    if skill_reasons:
        reasons.append(skill_reasons)

    # ---- Experience fit (fresher) ------------------------------------
    max_exp = config.get("max_experience_years", 1)
    if any(x in title for x in ["trainee", "intern", "fresher", "graduate", "entry", "associate"]):
        score += 15
        reasons.append("fresher OK")
    elif any(x in desc for x in ["0 years", "fresher", "no experience"]):
        score += 15
        reasons.append("fresher OK")
    else:
        # Small bonus; the hard reject is handled in decide_action via _experience_filter
        if re.search(r"([0-9])\s*(\+)?\s*years?", desc):
            pass
        score += 5  # Small bonus

    # ---- Location ---------------------------------------------------
    config_locs = [l.lower() for l in config.get("locations", [])]
    loc_match = False
    for cloc in config_locs:
        if cloc in location or cloc in desc:
            score += 10
            loc_match = True
            reasons.append(f"loc:{job.get('Location')}")
            break
    if not loc_match and ("remote" in location or "remote" in desc):
        score += 10
        reasons.append("remote")

    # ---- Company tier bonus (if we have it) -------------------------
    if job.get("tier") and str(job.get("tier")).strip() == "Tier 1":
        score += 5
        reasons.append("tier1")

    score = min(100, score)
    return score, "; ".join(reasons)


# ---------------------------------------------------------------------------
# Eligibility check – separates "can we consider this job" from "should we score it"
# ---------------------------------------------------------------------------
def check_eligibility(job_data, config, profile) -> (bool, str):
    """Return (eligible, reason).

    Checks:
    - mandatory experience (via _experience_eligible)
    - PhD / senior-level language (via _education_eligible)
    - employment type if marked
    - Returns (False, reason) if the job is clearly not suitable.
    """
    desc = job_data.get("Description", "")
    # Experience filter
    max_exp = config.get("max_experience_years", 1)
    if not _experience_eligible(desc, max_exp):
        return False, f"mandatory experience exceeds fresher limit (max {max_exp} year(s))"
    # Education filter
    if not _education_eligible(desc):
        return False, "PhD‑only position without fresher context"
    # Optional: check employment type if present
    # (we don't have a strong parser, so we skip for now)
    return True, ""


# ---------------------------------------------------------------------------
# Decision action – now uses eligibility + experience filter
# ---------------------------------------------------------------------------
def decide_action(job, score, config):
    # Hard rejects (senior titles)
    title = str(job.get("Job Title", "")).lower()
    desc = str(job.get("Description", "")).lower()

    hard_reject_keywords = ["senior", "lead", "principal", "manager", "architect", "staff engineer"]
    for kw in hard_reject_keywords:
        if kw in title:
            return "Skipped", f"senior/lead title"

    excluded = [k.lower() for k in config.get("excluded_keywords", [])]
    for kw in excluded:
        if kw in title or kw in desc:
            return "Skipped", f"excluded keyword: {kw}"

    # Experience filtering based on max_experience_years
    max_exp = config.get("max_experience_years", 1)
    reject_exp, exp_reason = match._experience_filter(desc, max_exp)  # defined earlier in discover? we need to import it.
    # Actually _experience_filter is in match.py now – we'll replicate a small version here.
    # For brevity we just call the existing function from discover? But we can define locally.
    # We'll just use the eligibility function.
    elig_ok, elig_reason = check_eligibility(job, config, config)  # profile not needed here
    if not elig_ok:
        return "Skipped", elig_reason

    # Simple legacy check (only matters if max_exp > 0; for fresher mode rely on _experience_filter)
    if max_exp > 0 and re.search(r"([2-9])\s*(\+)?\s*years?", desc):
        return "Skipped", "experience > max"

    auto_min = config.get("score_thresholds", {}).get("auto_apply_min", 70)
    manual_min = config.get("score_thresholds", {}).get("manual_apply_min", 50)

    platform = str(job.get("Found Via", "")).lower()
    is_restricted = any(x in platform for x in ["linkedin", "naukri"])

    if score >= auto_min:
        if is_restricted or job.get("needs_manual_form"):
            return "Manual Apply", "restricted platform or complex form"
        return "Auto-Apply", ""
    elif score >= manual_min:
        return "Manual Apply", "score below auto threshold"
    else:
        return "Skipped", "low match score"