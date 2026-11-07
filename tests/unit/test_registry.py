from __future__ import annotations

import yaml
import openpyxl

from job_agent.companies.importer import import_companies
from job_agent.registry import import_registry, load_platform_registry
from tests.support import ROOT, sha256


def test_registry_import_is_idempotent_and_offline(db):
    platforms_path = ROOT / "config" / "registry" / "platforms.yaml"
    keywords_path = ROOT / "config" / "search_keywords.yaml"
    first = import_registry(db, platforms_path, keywords_path)
    first_platform_count = len(db.list_registry_platforms())
    first_alert_count = len(db.list_saved_alerts())
    first_tag_count = db.connection.execute("SELECT COUNT(*) FROM platform_tags").fetchone()[0]
    second = import_registry(db, platforms_path, keywords_path)
    assert first == second
    assert len(db.list_registry_platforms()) == first_platform_count
    assert len(db.list_saved_alerts()) == first_alert_count
    assert db.connection.execute("SELECT COUNT(*) FROM platform_tags").fetchone()[0] == first_tag_count
    assert db.list_sources() == []
    assert first["platform_raw_entries"] == 114
    assert first["keyword_count"] == 24
    duplicate_names = {item["name"] for item in first["merged_duplicates"]}
    assert {"LinkedIn Jobs", "Toptal", "Arc.dev", "Turing", "F6S",
            "Internshala", "Unstop", "Freshersworld", "Naukri Campus",
            "LetsIntern", "Y Combinator Jobs", "HackerRank", "HackerEarth"} <= duplicate_names


def test_registry_duplicate_collapse_and_classes():
    platforms, raw_count = load_platform_registry(
        ROOT / "config" / "registry" / "platforms.yaml"
    )
    assert raw_count == 114
    by_name = {row["name"]: row for row in platforms}
    assert by_name["LinkedIn Jobs"]["tags"] == [
        "1 Indian Job Platforms", "2 International Remote Job Platforms",
    ]
    assert by_name["Toptal"]["tags"] == [
        "2 International Remote Job Platforms", "3 Freelancing Platforms",
    ]
    assert by_name["F6S"]["tags"] == [
        "1 Indian Job Platforms", "2 International Remote Job Platforms",
        "4 Internship & Fresher Platforms",
    ]
    assert by_name["F6S"]["url"] == "https://www.f6s.com/jobs"
    assert by_name["F6S"]["handling_class"] == "link_only"
    assert by_name["LinkedIn Jobs"]["handling_class"] == "never_touch"
    assert by_name["Remotive"]["handling_class"] == "open_feed_candidate"
    assert by_name["Remotive"]["approved"] is False
    assert by_name["Remotive"]["feed_url"] == "unknown"
    assert by_name["Remotive"]["terms_url"] == "unknown"
    assert all(row["url_verified"] is False for row in platforms)
    assert by_name["Outreachy"]["handling_class"] == "program_seasonal"
    assert by_name["GitHub"]["handling_class"] == "community"
    assert all("adapter" not in row for row in platforms)
    assert all(not row["approved"] for row in platforms)


def test_registry_source_counts_and_contract_keywords():
    platform_data = yaml.safe_load(
        (ROOT / "config" / "registry" / "platforms.yaml").read_text(encoding="utf-8")
    )
    assert {key: len(value) for key, value in platform_data["sections"].items()} == {
        "1 Indian Job Platforms": 30,
        "2 International Remote Job Platforms": 30,
        "3 Freelancing Platforms": 24,
        "4 Internship & Fresher Platforms": 15,
        "6 Developer Communities & Opportunity Platforms": 15,
    }
    company_data = yaml.safe_load(
        (ROOT / "config" / "registry" / "companies_extra.yaml").read_text(encoding="utf-8")
    )
    assert {key: len(value) for key, value in company_data["groups"].items()} == {
        "Global Technology Companies": 20,
        "Indian IT Services Companies": 15,
        "Indian Product & SaaS Companies": 25,
        "International Product & SaaS Companies": 25,
    }
    keywords = yaml.safe_load(
        (ROOT / "config" / "search_keywords.yaml").read_text(encoding="utf-8")
    )
    assert sum(len(values) for key, values in keywords.items() if key != "contract_optional") == 22
    assert keywords["contract_optional"] == {
        "enabled": False,
        "keywords": ["Freelance Full Stack Developer", "Junior Full Stack Contractor"],
    }


def test_owner_company_registry_matches_exactly_and_keeps_urls_unverified(db, tmp_path):
    master_path = tmp_path / "master.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Companies"
    sheet.append(["Master ID", "Company Name", "Official Careers Page"])
    sheet.append(["JT-0001", "Google", "https://careers.google.com/jobs"])
    workbook.save(master_path)
    before = sha256(master_path)
    import_companies(db, master_path, commit=True)

    companies_path = tmp_path / "companies.yaml"
    companies_path.write_text(yaml.safe_dump({
        "url_verified": False,
        "groups": {
            "Global Technology Companies": [
                "Google|https://www.google.com/about/careers/applications/jobs/results/",
                "Google|https://www.google.com/about/careers/applications/jobs/results/",
                "Apple|https://www.apple.com/careers/",
            ],
        },
    }), encoding="utf-8")

    result = import_registry(
        db,
        ROOT / "config" / "registry" / "platforms.yaml",
        ROOT / "config" / "search_keywords.yaml",
        companies_path,
        master_path,
    )
    assert sha256(master_path) == before
    assert result["company_matched"] == 1
    assert result["company_owner_entries"] == 3
    assert result["company_owner_unique"] == 2
    assert result["company_merged_duplicates"] == ["Google"]
    assert result["matched_names"] == ["Google"]
    assert result["unmatched_names"] == ["Apple"]
    assert result["needs_review"] == ["Apple"]
    candidate = db.connection.execute(
        "SELECT company_master_id, url, url_verified FROM company_career_candidates"
    ).fetchone()
    assert tuple(candidate) == (1, "https://www.google.com/about/careers/applications/jobs/results/", 0)
    unmatched = db.connection.execute(
        "SELECT origin, tier, region, owner_group, needs_review FROM companies WHERE master_id < 0"
    ).fetchone()
    assert tuple(unmatched) == ("owner_list", "unknown", "unknown", "Global Technology Companies", 1)
