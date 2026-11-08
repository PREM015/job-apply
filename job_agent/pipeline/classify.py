"""Deterministic, evidence-based classification."""
from __future__ import annotations

import re

SOFTWARE_TERMS = (
    "software engineer", "software developer", "developer", "programmer", "sde",
    "frontend", "front-end", "backend", "back-end", "full stack", "fullstack",
    "full-stack", "data engineer", "data scientist", "machine learning", "ml engineer",
    "devops", "qa engineer", "sre", "cloud engineer", "python", "java",
    "javascript", "typescript", "react", "node.js", "sql", "c++", "c#", ".net",
)
SOFTWARE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(term) for term in SOFTWARE_TERMS) + r")(?![A-Za-z0-9])",
    re.I,
)
FALSE_POSITIVE_TITLE = re.compile(
    r"\b(?:data entry|sales engineer|support engineer|civil engineer|mechanical engineer|"
    r"network engineer|accountant|recruiter|designer|marketing|business development|"
    r"customer success|product manager|staffing platform)\b",
    re.I,
)
EXCLUDED_TITLE = re.compile(
    r"(?:\b(?:senior|sr\.?|principal|architect|manager|director|head of|vp|chief|lead)\b|"
    r"\bstaff\s+(?:software|data|platform|site reliability|devops)?\s*engineer\b|"
    r"\bsde\s*[- ]?3\b)",
    re.I,
)
INTERNSHIP_RE = re.compile(r"\b(intern|internship|trainee)\b", re.I)
FRESHER_RE = re.compile(
    r"\b(?:fresher|entry[- ]level|new grad|graduate (?:hiring|recruitment|development) "
    r"program|graduate program|graduate programme|no experience)\b",
    re.I,
)
RANGE_RE = re.compile(r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:\+)?\s*years?", re.I)
PLUS_RE = re.compile(r"(\d+)\s*\+\s*years?", re.I)
YEARS_RE = re.compile(r"(\d+)\s*years?", re.I)
COUNTRY_NAMES = {
    "india": "IN", "united states": "US", "usa": "US", "uk": "GB",
    "united kingdom": "GB", "canada": "CA", "germany": "DE", "singapore": "SG",
}
INDIAN_CITIES = {
    "bengaluru", "bangalore", "hyderabad", "pune", "chennai", "noida",
    "gurugram", "gurgaon", "mumbai", "delhi", "kolkata", "ahmedabad",
}


def software_classification(title: str, description: str = "") -> tuple[bool, list[str]]:
    title = title or ""
    description = description or ""
    if FALSE_POSITIVE_TITLE.search(title):
        return False, []
    title_evidence = {match.group(0).lower() for match in SOFTWARE_RE.finditer(title)}
    description_evidence = {match.group(0).lower() for match in SOFTWARE_RE.finditer(description)}
    evidence = sorted(title_evidence or description_evidence)
    return bool(evidence), evidence


def is_excluded_title(title: str) -> bool:
    return bool(EXCLUDED_TITLE.search(title or ""))


def _years_level(years: int) -> str:
    if years <= 1:
        return "0-1"
    if years == 2:
        return "1-2"
    if years <= 3:
        return "2-3"
    return "3plus"


def experience_level(title: str, description: str = "", employment_type: str = "") -> str:
    title = title or ""
    description = description or ""
    employment_type = employment_type or ""
    combined = f"{title} {description} {employment_type}"

    range_match = RANGE_RE.search(combined)
    if range_match:
        return _years_level(int(range_match.group(2)))
    plus_match = PLUS_RE.search(combined)
    if plus_match:
        return _years_level(int(plus_match.group(1)))
    years_match = YEARS_RE.search(combined)
    if years_match:
        return _years_level(int(years_match.group(1)))

    sde_level = re.search(r"\bsde\s*[- ]?([1-9])\b", title, re.I)
    if sde_level:
        return "3plus" if int(sde_level.group(1)) >= 3 else _years_level(int(sde_level.group(1)))
    engineer_level = re.search(r"\bengineer\s+(ii|iii|iv)\b", title, re.I)
    if engineer_level:
        level = {"ii": 2, "iii": 3, "iv": 4}[engineer_level.group(1).lower()]
        return "2-3" if level == 2 else "3plus"
    if FRESHER_RE.search(combined):
        return "fresher"
    if INTERNSHIP_RE.search(title) or re.search(r"\bintern(?:ship)?\b", employment_type, re.I):
        return "internship"
    if INTERNSHIP_RE.search(description):
        return "internship"
    return "unknown"


def work_mode(
    location: str,
    description: str = "",
    workplace_type: str | None = None,
    is_remote: bool | None = None,
) -> str:
    structured = (workplace_type or "").strip().lower().replace("_", " ")
    if structured:
        if "hybrid" in structured:
            structured_mode = "hybrid"
        elif "remote" in structured or "work from home" in structured:
            structured_mode = "remote"
        elif "on site" in structured or "on-site" in structured or "onsite" in structured or "office" in structured:
            structured_mode = "onsite"
        else:
            structured_mode = "unknown"
    else:
        structured_mode = "unknown"

    if is_remote is True:
        remote_mode = "remote"
    elif is_remote is False:
        remote_mode = "unknown"
    else:
        remote_mode = "unknown"

    evidence = f"{location or ''} {description or ''}".lower()
    remote_negated = bool(re.search(
        r"\b(?:no|not|never|does not|doesn't|do not|don't|cannot|can't)\s+"
        r"(?:offer|support|allow|provide|available(?:\s+for)?)?\s*(?:fully\s+)?remote"
        r"(?:\s+work)?\b|\bremote(?:\s+work)?\s+(?:is\s+)?not\s+"
        r"(?:offered|available|supported|provided|allowed)\b",
        evidence,
    ))
    hybrid_negated = bool(re.search(
        r"\b(?:no|not|never|does not|doesn't|do not|don't|cannot|can't)\s+"
        r"(?:offer|support|allow|provide|available(?:\s+for)?)?\s*hybrid\b|"
        r"\bhybrid(?:\s+work)?\s+(?:is\s+)?not\s+(?:offered|available|supported|provided|allowed)\b",
        evidence,
    ))
    onsite_negated = bool(re.search(
        r"\b(?:no|not|never|does not|doesn't|do not|don't|cannot|can't)\s+"
        r"(?:offer|support|allow|provide|available(?:\s+for)?)?\s*(?:on[- ]?site|onsite|office-based)\b",
        evidence,
    ))
    remote_positive = bool(re.search(
        r"\b(?:fully\s+)?remote(?:\s+(?:work|role|position))?\b|"
        r"\bwork from (?:anywhere|home)\b",
        evidence,
    )) and not remote_negated
    hybrid_positive = bool(re.search(r"\bhybrid\b", evidence)) and not hybrid_negated
    onsite_positive = bool(re.search(r"\b(?:onsite|on-site|in office|office-based)\b", evidence)) and not onsite_negated

    textual_modes = {
        mode for present, mode in (
            (remote_positive, "remote"),
            (hybrid_positive, "hybrid"),
            (onsite_positive, "onsite"),
        ) if present
    }
    if structured_mode != "unknown":
        textual_modes.add(structured_mode)
    if remote_mode != "unknown":
        textual_modes.add(remote_mode)
    if remote_negated and "remote" in textual_modes:
        return "needs_review"
    if (
        (structured_mode == "remote" and remote_negated)
        or (structured_mode == "hybrid" and hybrid_negated)
        or (structured_mode == "onsite" and onsite_negated)
    ):
        return "needs_review"
    if (
        (is_remote is False and ("remote" in textual_modes or structured_mode == "remote"))
        or (is_remote is True and structured_mode in {"onsite", "hybrid"})
    ):
        return "needs_review"
    if len(textual_modes) > 1:
        return "needs_review"
    if textual_modes:
        return next(iter(textual_modes))
    return "unknown"


def country_eligibility(location: str, description: str, allowed: set[str]) -> tuple[str, bool]:
    location_text = (location or "").lower()
    allowed_codes = {str(code).upper() for code in allowed}
    location_country = None
    for name, code in COUNTRY_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", location_text):
            location_country = code
            break
    if location_country is None and any(
        re.search(rf"\b{re.escape(city)}\b", location_text) for city in INDIAN_CITIES
    ):
        location_country = "IN"

    requirement = re.search(
        r"(?:must be based in|only applicants in|authorized to work in|work authorization in)\s+"
        r"(india|united states|usa|uk|united kingdom|canada|germany|singapore)\b",
        description or "",
        re.I,
    )
    required_country = COUNTRY_NAMES[requirement.group(1).lower()] if requirement else None
    if location_country and required_country and location_country != required_country:
        return "unknown", False
    if location_country:
        return location_country, location_country in allowed_codes
    if required_country:
        return required_country, required_country in allowed_codes
    return "unknown", False


ALIASES = {"js": "javascript", "node": "node.js", "nodejs": "node.js", "reactjs": "react",
           "postgres": "postgresql", "full stack": "fullstack"}


def _skill_pattern(skill: str) -> re.Pattern:
    escaped = re.escape(skill)
    if skill.startswith("."):
        escaped = r"(?<![A-Za-z0-9])" + escaped + r"(?![A-Za-z0-9])"
    elif skill.endswith("+") or skill.endswith("#"):
        escaped = re.escape(skill) + r"(?![A-Za-z0-9])"
    else:
        escaped = r"(?<![A-Za-z0-9])" + escaped + r"(?![A-Za-z0-9])"
    return re.compile(escaped, re.I)


def extract_skills(text: str, required: list[str], preferred: list[str], aliases: dict | None = None) -> dict:
    aliases = {**ALIASES, **(aliases or {})}
    found_required: list[str] = []
    found_preferred: list[str] = []
    evidence: list[str] = []
    for skill in required:
        canonical = aliases.get(skill.lower(), skill.lower())
        if _skill_pattern(canonical).search(text):
            found_required.append(canonical)
            evidence.append(f"required:{canonical}")
    for skill in preferred:
        canonical = aliases.get(skill.lower(), skill.lower())
        if canonical in found_required:
            continue
        if _skill_pattern(canonical).search(text):
            found_preferred.append(canonical)
            evidence.append(f"preferred:{canonical}")
    return {"required": sorted(set(found_required)), "preferred": sorted(set(found_preferred)), "evidence": evidence}


def classify_job(job: dict, prefs: dict) -> dict:
    title = job.get("title", "")
    description = job.get("description_text", "")
    is_software, software_evidence = software_classification(title, description)
    experience = experience_level(title, description, job.get("employment_type", ""))
    mode = work_mode(
        job.get("location_raw", ""),
        description,
        job.get("workplace_type"),
        job.get("is_remote"),
    )
    location = job.get("structured_location") or job.get("location_raw", "")
    allowed = {str(country).upper() for country in prefs.get("locations", {}).get("countries", [])}
    country, eligible = country_eligibility(location, description, allowed)
    skills = extract_skills(
        f"{title} {description}",
        prefs.get("skills", {}).get("required", []),
        prefs.get("skills", {}).get("preferred", []),
        prefs.get("skills", {}).get("aliases", {}),
    )
    job.update({
        "is_software": int(is_software),
        "software_evidence": software_evidence,
        "experience_level": experience,
        "work_mode": mode,
        "country": country,
        "country_eligible": eligible,
        "is_internship": int(experience == "internship"),
        "skills_required": skills["required"],
        "skills_preferred": skills["preferred"],
        "skill_evidence": skills["evidence"],
    })
    return job
