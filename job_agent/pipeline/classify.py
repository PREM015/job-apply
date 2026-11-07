"""Deterministic, evidence-based classification."""
from __future__ import annotations

import re

SOFTWARE_TERMS = [
    "software", "developer", "engineer", "programmer", "sde", "frontend", "front-end",
    "backend", "back-end", "full stack", "fullstack", "full-stack", "data", "ml",
    "devops", "qa", "sre", "cloud", "python", "java", "javascript", "typescript",
    "react", "node.js", "sql", "c++", "c#", ".net",
]
SOFTWARE_RE = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(t) for t in SOFTWARE_TERMS) + r")(?![A-Za-z0-9])", re.I)
FALSE_POSITIVES = [
    "sales engineer", "support engineer", "civil engineer", "mechanical engineer",
    "network engineer", "accountant", "recruiter", "designer", "marketing",
    "business development", "customer success", "product manager",
]
EXCLUDED_TITLE_TERMS = ["senior", "staff", "principal", "architect", "manager", "director",
                        "head of", "vp", "chief", "lead "]
INTERNSHIP_RE = re.compile(r"\b(intern|internship|trainee)\b", re.I)
FRESHER_RE = re.compile(r"\b(fresher|entry[- ]level|graduate|new grad|no experience)\b", re.I)
RANGE_RE = re.compile(r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:\+)?\s*years?", re.I)
PLUS_RE = re.compile(r"(\d+)\s*\+\s*years?", re.I)
YEARS_RE = re.compile(r"(\d+)\s*(?:\+)?\s*years?", re.I)


def software_classification(title: str, description: str = "") -> tuple[bool, list[str]]:
    combined = f"{title} {description}"
    lowered = combined.lower()
    for phrase in FALSE_POSITIVES:
        if phrase in lowered and not any(term in lowered for term in ("python", "java", "javascript", "software", "developer", "devops", "data engineer")):
            return False, []
    evidence = sorted({m.group(0).lower() for m in SOFTWARE_RE.finditer(combined)})
    return bool(evidence), evidence


def is_excluded_title(title: str) -> bool:
    lowered = title.lower()
    return any(term in lowered for term in EXCLUDED_TITLE_TERMS)


def experience_level(title: str, description: str = "", employment_type: str = "") -> str:
    combined = f"{title} {description} {employment_type}"
    if INTERNSHIP_RE.search(combined):
        return "internship"
    if FRESHER_RE.search(combined):
        return "fresher"
    match = RANGE_RE.search(combined)
    if match:
        low = int(match.group(1))
        high = int(match.group(2))
        if high <= 1:
            return "0-1"
        if high <= 2:
            return "1-2"
        if high <= 3:
            return "2-3"
        return "3plus"
    plus = PLUS_RE.search(combined)
    if plus:
        years = int(plus.group(1))
        if years <= 1:
            return "0-1"
        if years == 2:
            return "2-3"
        return "3plus"
    years_match = YEARS_RE.search(combined)
    if years_match:
        years = int(years_match.group(1))
        if years <= 1:
            return "0-1"
        if years == 2:
            return "1-2"
        if years == 3:
            return "2-3"
        return "3plus"
    return "unknown"


def work_mode(location: str, description: str = "") -> str:
    text = f"{location} {description}".lower()
    if re.search(r"\bremote\b", text):
        return "remote"
    if re.search(r"\bhybrid\b", text):
        return "hybrid"
    if re.search(r"\bonsite\b|\bon-site\b|\bin office\b", text):
        return "onsite"
    return "unknown"


COUNTRY_NAMES = {"india": "IN", "united states": "US", "usa": "US", "uk": "GB",
                 "united kingdom": "GB", "canada": "CA", "germany": "DE", "singapore": "SG"}


def country_eligibility(location: str, description: str, allowed: set[str]) -> tuple[str, bool]:
    text = f"{location} {description}".lower()
    for name, code in COUNTRY_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", text):
            return code, code in allowed
    upper = re.findall(r"\b(IN|US|GB|CA|DE|SG)\b", f"{location} {description}")
    for code in upper:
        return code, code in allowed
    return "unknown", True


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
    mode = work_mode(job.get("location_raw", ""), description)
    allowed = {str(c).upper() for c in prefs.get("locations", {}).get("countries", [])}
    country, eligible = country_eligibility(job.get("location_raw", ""), description, allowed)
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
