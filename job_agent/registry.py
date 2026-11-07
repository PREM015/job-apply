"""Offline owner registry loading and idempotent imports."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from .companies.importer import read_companies
from .db.repository import Database

NEVER_TOUCH = {"linkedin jobs", "indeed india", "glassdoor", "naukri", "naukri campus"}
OPEN_FEEDS = {
    "remotive", "remote ok", "we work remotely", "himalayas", "working nomads",
    "jobspresso", "hacker news who is hiring", "y combinator jobs",
    "work at a startup", "eu remote jobs",
}
PROGRAMS = {
    "outreachy", "google summer of code", "microsoft research programs",
    "major league hacking", "devpost",
}
COMMUNITY = {
    "github", "hackerrank", "hackerearth", "codechef", "leetcode",
    "good first issue", "codetriage", "bountysource", "gitcoin", "topcoder",
    "dev community", "hashnode", "indie hackers", "reddit r forhire",
    "reddit r remotework",
}
KNOWN_AMBIGUOUS = {
    "meta", "apple", "hp", "google", "dell", "intel", "samsung", "navi",
    "linear", "notion", "docker", "elastic",
}
CORPORATE_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "ltd", "limited", "llc",
    "plc", "company", "co",
}
PLATFORM_ALIASES = {"f6s jobs": "f6s", "hacker news who is hiring": "hacker news who is hiring"}


def _read_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"registry YAML root must be a mapping: {path}")
    return value


def _normalized_name(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    value = re.sub(r"\s+", " ", value)
    return PLATFORM_ALIASES.get(value, value)


def _domain(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    parts = hostname.split(".")
    if len(parts) >= 3 and parts[-1] in {"uk", "in", "au"} and parts[-2] in {"co", "gov", "org", "ac"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname


def _platform_class(name: str, sections: set[str]) -> tuple[str, str | None]:
    normalized = _normalized_name(name)
    lower_sections = {section.lower() for section in sections}
    if normalized in NEVER_TOUCH:
        return "never_touch", "Restricted portal: link only; no adapter and never fetched."
    if normalized in OPEN_FEEDS:
        return "open_feed_candidate", "Terms approval required; feed URL unknown; no adapter."
    if normalized in PROGRAMS:
        return "program_seasonal", ""
    if "6 developer communities" in " ".join(lower_sections) or normalized in COMMUNITY:
        return "community", ""
    if lower_sections == {"3 freelancing platforms"}:
        return "freelance_out_of_scope", "Hidden by default; not part of job discovery."
    return "link_only", ""


def load_platform_registry(path: str | Path) -> tuple[list[dict[str, Any]], int]:
    raw = _read_yaml(path)
    sections = raw.get("sections")
    if not isinstance(sections, dict):
        raise ValueError("platform registry must contain a sections mapping")
    merged: dict[str, dict[str, Any]] = {}
    raw_count = 0
    for section, entries in sections.items():
        if not isinstance(entries, list):
            raise ValueError(f"platform section must be a list: {section}")
        for item in entries:
            if not isinstance(item, str) or "|" not in item:
                raise ValueError(f"invalid platform entry in {section}: expected Name|URL")
            name, url = (part.strip() for part in item.split("|", 1))
            if not name or not url or urlsplit(url).scheme not in {"http", "https"}:
                raise ValueError(f"invalid platform name or URL in {section}")
            raw_count += 1
            key = f"{_domain(url)}|{_normalized_name(name)}"
            row = merged.setdefault(key, {
                "normalized_key": key, "name": name, "url": url,
                "sections": set(), "owner_groups": set(),
            })
            if name == "F6S Jobs":
                row["url"] = url
            row["sections"].add(section)
    for row in merged.values():
        handling_class, note = _platform_class(row["name"], row["sections"])
        row["handling_class"] = handling_class
        row["notes"] = note or ""
        row["feed_url"] = "unknown" if handling_class == "open_feed_candidate" else None
        row["terms_url"] = "unknown" if handling_class == "open_feed_candidate" else None
        row["url_verified"] = False
        row["approved"] = False
        row["tags"] = sorted(row.pop("sections"))
        row.pop("owner_groups")
    return list(merged.values()), raw_count


def normalize_company_name(name: str) -> str:
    parts = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    while parts and parts[-1] in CORPORATE_SUFFIXES:
        parts.pop()
    return " ".join(parts)


def _stable_owner_id(name: str) -> int:
    value = int(hashlib.sha256(name.lower().encode("utf-8")).hexdigest()[:12], 16)
    return -(value or 1)


def import_registry(db: Database, platforms_path: str | Path, keywords_path: str | Path,
                    companies_path: str | Path | None = None,
                    master_workbook: str | Path | None = None) -> dict[str, Any]:
    platforms, raw_count = load_platform_registry(platforms_path)
    for platform in platforms:
        for section in platform["tags"]:
            db.upsert_registry_platform({
                **platform, "section": section,
            })
        if platform["handling_class"] == "link_only":
            db.upsert_saved_alert(
                label=f"portal: {platform['normalized_key']}",
                keyword_group="portal",
                keyword=f"Review saved alert on {platform['name']}",
                portal_key=platform["normalized_key"],
            )

    keywords = _read_yaml(keywords_path)
    keyword_count = 0
    for group, values in keywords.items():
        if group == "contract_optional":
            enabled = bool(values.get("enabled", False))
            values = values.get("keywords", [])
        else:
            enabled = True
        if not isinstance(values, list):
            raise ValueError(f"keyword group must be a list: {group}")
        for keyword in values:
            db.upsert_saved_alert(
                label=f"{group}: {keyword}", keyword_group=group,
                keyword=str(keyword), enabled=enabled,
            )
            keyword_count += 1

    owner_rows = []
    matched_count = 0
    matched_names: list[str] = []
    unmatched_names: list[str] = []
    needs_review: list[str] = []
    careers_url_differences: list[dict[str, str]] = []
    company_duplicate_names: list[str] = []
    if companies_path:
        group_data = _read_yaml(companies_path).get("groups", {})
        for group, entries in group_data.items():
            for entry in entries:
                name, url = (part.strip() for part in entry.split("|", 1))
                owner_rows.append({"name": name, "url": url, "owner_group": group})

    if owner_rows and master_workbook:
        company_keys: dict[str, int] = {}
        for owner in owner_rows:
            company_key = f"{_domain(owner['url'])}|{normalize_company_name(owner['name'])}"
            company_keys[company_key] = company_keys.get(company_key, 0) + 1
        company_duplicate_names = [
            owner_rows[index]["name"]
            for index, owner in enumerate(owner_rows)
            if company_keys[f"{_domain(owner['url'])}|{normalize_company_name(owner['name'])}"] > 1
            and not any(
                previous["name"] == owner["name"]
                for previous in owner_rows[:index]
            )
        ]
        master = read_companies(master_workbook)["companies"]
        by_name = {normalize_company_name(str(row.get("name", ""))): row for row in master}
        by_domain: dict[str, dict[str, Any]] = {}
        for row in master:
            for field in ("careers_url", "openings_url"):
                if row.get(field):
                    by_domain.setdefault(_domain(str(row[field])), row)
        for owner in owner_rows:
            normalized = normalize_company_name(owner["name"])
            candidate = None
            candidate = by_name.get(normalized)
            if candidate is None:
                candidate = by_domain.get(_domain(owner["url"]))
            if candidate:
                master_id = int(re.sub(r"\D", "", str(candidate["master_id"])))
                db.add_company_career_candidate(master_id, owner["url"])
                matched_count += 1
                matched_names.append(owner["name"])
                if candidate.get("careers_url") and str(candidate["careers_url"]) != owner["url"]:
                    careers_url_differences.append({
                        "company": owner["name"],
                        "master_url": str(candidate["careers_url"]),
                        "owner_url": owner["url"],
                    })
            else:
                master_id = _stable_owner_id(owner["name"])
                db.upsert_company({
                    "master_id": master_id, "name": owner["name"], "tier": "unknown",
                    "careers_url": None, "openings_url": None, "origin": "owner_list",
                    "region": "unknown", "owner_group": owner["owner_group"],
                    "needs_review": True,
                })
                db.add_company_career_candidate(master_id, owner["url"])
                unmatched_names.append(owner["name"])
                needs_review.append(owner["name"])

    return {
        "platform_raw_entries": raw_count,
        "platform_unique": len(platforms),
        "merged_duplicates": [
            {"name": row["name"], "sections": row["tags"]}
            for row in platforms if len(row["tags"]) > 1
        ],
        "keyword_count": keyword_count,
        "platform_counts_by_class": {
            cls: sum(row["handling_class"] == cls for row in platforms)
            for cls in sorted({row["handling_class"] for row in platforms})
        },
        "company_owner_entries": len(owner_rows),
        "company_owner_unique": len({
            f"{_domain(owner['url'])}|{normalize_company_name(owner['name'])}"
            for owner in owner_rows
        }),
        "company_merged_duplicates": company_duplicate_names,
        "company_matched": matched_count,
        "company_unmatched": len(owner_rows) - matched_count,
        "matched_names": matched_names,
        "unmatched_names": unmatched_names,
        "needs_review": needs_review,
        "careers_url_differences": careers_url_differences,
    }
