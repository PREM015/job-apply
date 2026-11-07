from __future__ import annotations

from pathlib import Path

import openpyxl

from job_agent.companies.importer import (data_quality_report, import_companies, read_companies,
                                          read_global_targets)
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


def add_global_targets(path: Path) -> Path:
    workbook = openpyxl.load_workbook(path)
    sheet = workbook.create_sheet("Global Product Targets")
    headers = [""] * 15
    headers[0] = "#"
    headers[1] = "Company"
    headers[2] = "Tier"
    headers[7] = "Careers Page"
    headers[9] = "Status"
    headers[13] = "Matched Master ID (Companies)"
    headers[14] = "Source"
    sheet.append(headers)
    row = [""] * 15
    row[0] = 1
    row[1] = "Acme"
    row[2] = "Tier 1"
    row[7] = "https://boards.greenhouse.io/acme"
    row[9] = "Not Started"
    row[13] = 1
    row[14] = "TRK"
    sheet.append(row)
    workbook.save(path)
    return path


def test_read_global_targets_maps_columns_and_is_read_only(tmp_path):
    path = add_global_targets(make_workbook(tmp_path / "companies.xlsx"))
    before = sha256(path)
    report = read_global_targets(path)
    assert sha256(path) == before
    assert report["hash_unchanged"] is True
    assert report["columns"] == {"target_id": 1, "company": 2, "tier": 3, "careers_url": 8,
                                 "status": 10, "matched_master_id": 14, "source": 15}
    assert report["global_targets"][0]["matched_master_id"] == 1
    assert report["global_targets"][0]["careers_url"] == "https://boards.greenhouse.io/acme"


def test_import_global_targets_commit(tmp_path, db):
    path = add_global_targets(make_workbook(tmp_path / "companies.xlsx"))
    report = import_companies(db, path, commit=True)
    assert len(report["global_targets"]) == 1
    assert db.count_global_targets() == 1
    assert db.list_global_targets()[0]["status"] == "Not Started"


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
