"""Safe Excel export. Never opens the master workbook."""
from __future__ import annotations

import hashlib
from pathlib import Path

import openpyxl

from ..db.repository import Database

MASTER_NAMES = {"Master_Job_Tracker_final.xlsx", "master_job_tracker_final.xlsx"}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _guard_path(out_path: str | Path, exports_dir: str | Path, force: bool) -> Path:
    target = Path(out_path).resolve()
    allowed = Path(exports_dir).resolve()
    if target.name.lower() in MASTER_NAMES:
        raise PermissionError("refusing to write the authoritative/master workbook")
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise PermissionError(f"export must stay inside {allowed}") from exc
    if target.exists() and not force:
        raise FileExistsError(f"export exists; pass force=True: {target}")
    return target


def export_workbook(db: Database, out_path: str | Path, exports_dir: str | Path = "data/exports",
                    force: bool = False) -> dict:
    target = _guard_path(out_path, exports_dir, force)
    target.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    queue_sheet = workbook.active
    queue_sheet.title = "Daily Queue"
    queue_sheet.append(["Rank", "Score", "Company", "Title", "URL", "Experience", "Work Mode", "State", "Reason"])
    for item in db.list_queue():
        queue_sheet.append([item["rank"], item["score"], item["company_name"], item["title"],
                            item["canonical_url"], item["experience_level"], item["work_mode"],
                            item["state"], item["reason"]])

    jobs_sheet = workbook.create_sheet("All Jobs")
    jobs_sheet.append(["Job ID", "Company", "Title", "URL", "Status", "Score", "Experience", "Software"])
    for job in db.list_jobs():
        jobs_sheet.append([job["job_id"], job["company_name"], job["title"], job["canonical_url"],
                           job["status"], job["score_total"], job["experience_level"], job["is_software"]])

    apps_sheet = workbook.create_sheet("Applications")
    apps_sheet.append(["Application ID", "Job ID", "Company", "Title", "Status", "Applied At", "Notes"])
    for app in db.list_applications():
        apps_sheet.append([app["application_id"], app["job_id"], app["company_name"], app["title"],
                           app["status"], app["applied_at"], app["notes"]])

    companies_sheet = workbook.create_sheet("Companies")
    companies_sheet.append(["Master ID", "Name", "Tier", "Careers URL", "Resolution Status"])
    for company in db.list_companies():
        companies_sheet.append([company["master_id"], company["name"], company["tier"],
                                company["careers_url"], company["resolution_status"]])

    runs_sheet = workbook.create_sheet("Runs")
    runs_sheet.append(["Run ID", "Started", "Finished", "Fetched", "Rejected", "Duplicates", "Queued", "Errors"])
    for run in db.list_runs():
        runs_sheet.append([run["run_id"], run["started_at"], run["finished_at"], run["fetched_count"],
                           run["rejected_count"], run["duplicate_count"], run["queued_count"], run["errors_json"]])

    rejected_sheet = workbook.create_sheet("Rejected")
    rejected_sheet.append(["Company", "Title", "Reason"])
    workbook.save(target)
    return {"path": str(target), "sha256": _hash(target), "sheets": workbook.sheetnames}
