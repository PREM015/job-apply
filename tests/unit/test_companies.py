from __future__ import annotations

from pathlib import Path

import openpyxl

from job_agent.companies.importer import data_quality_report, import_companies, read_companies
from job_agent.companies.resolver import detect_ats, resolve_company, source_coverage_report
from tests.support import sha256


def make_workbook(path: Path) -> Path:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Companies"
    sheet.append(["Master ID", "Company Name", "Priority Tier (Best Available)",
                  "Application Status", "Official Careers Page", "Current Openings URL", "Company Website"])
    sheet.append([1, "Acme", "Tier 1", "New", "https://boards.greenhouse.io/acme", "", "https://acme.example.com"])
    sheet.append([2, "Beta", "Tier 2", "New", "https://jobs.lever.co/beta", "", "https://beta.example.com"])
    sheet.append(["", "Broken", "Tier 3", "", "", "", ""])
    workbook.save(path)
    return path


def test_read_companies_is_read_only(tmp_path):
    path = make_workbook(tmp_path / "companies.xlsx")
    before = sha256(path)
    report = read_companies(path)
    assert sha256(path) == before
    assert report["hash_unchanged"] is True
    assert len(report["companies"]) == 2
    assert report["errors"] == [{"row": 4, "error": "missing_master_id"}]


def test_import_companies_commit_and_quality(tmp_path, db):
    path = make_workbook(tmp_path / "companies.xlsx")
    report = import_companies(db, path, commit=True)
    assert len(report["companies"]) == 2
    assert db.count_companies() == 2
    quality = data_quality_report(report["companies"])
    assert quality["total"] == 2
    assert quality["tiers"]["Tier 1"] == 1
    assert quality["ats_counts"]["unknown"] == 2


def test_import_companies_without_commit(tmp_path, db):
    path = make_workbook(tmp_path / "companies.xlsx")
    import_companies(db, path, commit=False)
    assert db.count_companies() == 0


def test_resolver_detects_ats_and_override():
    assert detect_ats("https://boards.greenhouse.io/acme") == ("greenhouse", "acme")
    assert detect_ats("https://jobs.lever.co/beta") == ("lever", "beta")
    assert detect_ats("https://acme.example.com/careers") == ("jsonld", None)
    company = {"master_id": 1, "name": "Acme", "careers_url": "https://boards.greenhouse.io/acme"}
    assert resolve_company(company)["source_type"] == "greenhouse"
    override = {"1": {"source_type": "lever", "url": "https://jobs.lever.co/acme"}}
    assert resolve_company(company, override)["resolution_status"] == "manual"
    assert resolve_company({"master_id": 2, "name": "None"})["resolution_status"] == "unresolved"


def test_coverage_report():
    companies = [{"master_id": 1, "name": "Acme", "careers_url": "https://boards.greenhouse.io/acme"},
                 {"master_id": 2, "name": "None"}]
    report = source_coverage_report(companies)
    assert report["total"] == 2
    assert report["unresolved"] == 1
