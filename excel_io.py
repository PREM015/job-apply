#!/usr/bin/env python3
import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

TRACKER_FILE = "Master_Job_Tracker_final.xlsx"
AUTHORITATIVE_TRACKER = Path(r"D:\code\plans\PLACEMENT\job\Master_Job_Tracker_final.xlsx")
JOB_OPENINGS_SHEET = "Job Openings"
DAILY_RUN_LOG_SHEET = "Daily Run Log"

COMPANIES_SHEET = "Companies"
APP_TRACKER_SHEET = "Application Tracker"
GLOBAL_TARGETS_SHEET = "Global Product Targets"

# Columns we can write in Companies (yellow columns as per spec)
COMPANIES_WRITE_COLS = ["Application Status", "Date Applied", "Next Action Date", "My Notes"]

# Job Openings headers
JOB_OPENINGS_HEADERS = [
    "Job Key", "Date Found", "Master ID", "Company", "Job Title", "Location",
    "Work Mode", "Experience Required", "Posted Date", "Job Link", "Found Via",
    "Match Score", "Match Reasons", "Decision", "Skip Reason", "Apply Status",
    "Date Applied", "Application Tracker #", "Last Checked"
]

DAILY_LOG_HEADERS = [
    "Run Date", "Mode (dry/live)", "Companies Checked", "Sources Failed",
    "New Jobs Found", "Matched", "Applied", "Manual Needed", "Skipped", "Errors", "Notes"
]

APP_TRACKER_HEADERS = [
    "#", "Entry Source", "Date Logged", "Company", "Master ID (auto)",
    "Contact First Name", "Contact Last Name", "Contact Name (as given)",
    "Contact Role / Title", "LinkedIn URL", "Email", "Email Source",
    "Job / Internship Title", "Application URL", "Hook (one specific line)",
    "Outreach Status", "Date Sent", "Days Since Sent", "Opened?", "Replied?",
    "Response Status", "Follow-up Sent?", "Follow-up Date", "Interview Status",
    "Outcome", "Notes"
]


def get_tracker_path():
    if AUTHORITATIVE_TRACKER.exists():
        return str(AUTHORITATIVE_TRACKER)
    # Legacy fallback is used only when the configured authoritative file is absent.
    for base in [Path("."), Path(".."), Path("D:/code/plans/PLACEMENT/job/apply project")]:
        candidate = base / TRACKER_FILE
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(f"Could not find {TRACKER_FILE}")


def backup_workbook(tracker_path, keep_last=14):
    backups_dir = Path("backups")
    backups_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    backup_path = backups_dir / f"Master_Job_Tracker_{date_str}.xlsx"
    shutil.copy2(tracker_path, backup_path)
    # Clean old backups
    backups = sorted(backups_dir.glob("Master_Job_Tracker_*.xlsx"))
    if len(backups) > keep_last:
        for old in backups[:-keep_last]:
            try:
                old.unlink()
            except Exception:
                pass
    return str(backup_path)


def load_workbook_safe(tracker_path, retries=3):
    for i in range(retries):
        try:
            wb = openpyxl.load_workbook(tracker_path)
            return wb
        except Exception as e:
            if i == retries - 1:
                raise
            # Try to wait a bit
            import time
            time.sleep(2)
    raise


def ensure_new_sheets(wb):
    # Create Job Openings if missing
    if JOB_OPENINGS_SHEET not in wb.sheetnames:
        ws = wb.create_sheet(JOB_OPENINGS_SHEET)
        for c, h in enumerate(JOB_OPENINGS_HEADERS, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        # Add validations
        dv_decision = DataValidation(type="list", formula1='"Auto-Apply,Manual Apply,Skipped,Needs Input"', allow_blank=True)
        dv_status = DataValidation(type="list", formula1='"Queued,Applied,Failed,Needs Manual,Closed"', allow_blank=True)
        ws.add_data_validation(dv_decision)
        ws.add_data_validation(dv_status)
        for row in range(2, 10000):
            dv_decision.add(ws[f"N{row}"])
            dv_status.add(ws[f"P{row}"])
    
    # Create Daily Run Log if missing
    if DAILY_RUN_LOG_SHEET not in wb.sheetnames:
        ws = wb.create_sheet(DAILY_RUN_LOG_SHEET)
        for c, h in enumerate(DAILY_LOG_HEADERS, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    
    return wb


def save_workbook_safe(wb, tracker_path):
    try:
        wb.save(tracker_path)
        return True
    except Exception as e:
        # Try to save with a temp name and copy back
        tmp = tracker_path + ".tmp"
        wb.save(tmp)
        shutil.copy2(tmp, tracker_path)
        try:
            os.remove(tmp)
        except:
            pass
        return True


def get_companies_to_watch(wb, tiers=[1,2,3], excluded_statuses=None):
    if excluded_statuses is None:
        excluded_statuses = ["Applied", "Interview", "Offer", "Rejected", "Withdrawn", "Closed"]
    ws = wb[COMPANIES_SHEET]
    companies = []
    # Find header
    headers = [cell.value for cell in ws[1]]
    try:
        master_id_idx = headers.index("Master ID")
        company_idx = headers.index("Company Name")
        tier_idx = headers.index("Priority Tier (Best Available)")
        status_idx = headers.index("Application Status")
        careers_idx = headers.index("Official Careers Page") if "Official Careers Page" in headers else None
        openings_idx = headers.index("Current Openings URL") if "Current Openings URL" in headers else None
        website_idx = headers.index("Company Website") if "Company Website" in headers else None
    except ValueError as e:
        raise ValueError(f"Missing required column in Companies: {e}")
    
    for row in range(2, ws.max_row + 1):
        tier = ws.cell(row=row, column=tier_idx+1).value
        if tier and str(tier).strip() in [f"Tier {t}" for t in tiers]:
            status = ws.cell(row=row, column=status_idx+1).value
            if status and str(status).strip() in excluded_statuses:
                continue
            companies.append({
                "row": row,
                "master_id": ws.cell(row=row, column=master_id_idx+1).value,
                "company_name": ws.cell(row=row, column=company_idx+1).value,
                "tier": tier,
                "status": status,
                "careers_page": ws.cell(row=row, column=careers_idx+1).value if careers_idx else None,
                "openings_url": ws.cell(row=row, column=openings_idx+1).value if openings_idx else None,
                "website": ws.cell(row=row, column=website_idx+1).value if website_idx else None,
            })
    return companies


def get_job_openings_keys(wb):
    if JOB_OPENINGS_SHEET not in wb.sheetnames:
        return set()
    ws = wb[JOB_OPENINGS_SHEET]
    keys = set()
    for row in range(2, ws.max_row + 1):
        key = ws.cell(row=row, column=1).value  # Job Key
        if key:
            keys.add(str(key).strip().lower())
        # Also check URL
        url = ws.cell(row=row, column=10).value
        if url:
            keys.add(str(url).strip())
    return keys


def get_applied_urls(wb):
    urls = set()
    # Check Application Tracker
    if APP_TRACKER_SHEET in wb.sheetnames:
        ws = wb[APP_TRACKER_SHEET]
        headers = [cell.value for cell in ws[1]]
        try:
            url_idx = headers.index("Application URL")
            for row in range(2, ws.max_row + 1):
                url = ws.cell(row=row, column=url_idx+1).value
                if url:
                    urls.add(str(url).strip())
        except ValueError:
            pass
    # Check Job Openings
    if JOB_OPENINGS_SHEET in wb.sheetnames:
        ws = wb[JOB_OPENINGS_SHEET]
        for row in range(2, ws.max_row + 1):
            url = ws.cell(row=row, column=10).value
            status = ws.cell(row=row, column=16).value
            if url and status in ["Applied"]:
                urls.add(str(url).strip())
    return urls


def append_job_opening(wb, job_data):
    ws = wb[JOB_OPENINGS_SHEET]
    # Find next empty row
    row = ws.max_row + 1
    # Map data to columns
    mapping = {
        "Job Key": 1, "Date Found": 2, "Master ID": 3, "Company": 4, "Job Title": 5,
        "Location": 6, "Work Mode": 7, "Experience Required": 8, "Posted Date": 9,
        "Job Link": 10, "Found Via": 11, "Match Score": 12, "Match Reasons": 13,
        "Decision": 14, "Skip Reason": 15, "Apply Status": 16, "Date Applied": 17,
        "Application Tracker #": 18, "Last Checked": 19
    }
    for key, col in mapping.items():
        if key in job_data:
            ws.cell(row=row, column=col, value=job_data[key])
    return row


def update_companies_row(wb, master_id, updates):
    ws = wb[COMPANIES_SHEET]
    headers = [cell.value for cell in ws[1]]
    try:
        master_id_idx = headers.index("Master ID")
    except ValueError:
        return False
    # Find row
    target_row = None
    for row in range(2, ws.max_row + 1):
        if ws.cell(row=row, column=master_id_idx+1).value == master_id:
            target_row = row
            break
    if not target_row:
        return False
    # Update only allowed columns
    for col_name, value in updates.items():
        if col_name in COMPANIES_WRITE_COLS and col_name in headers:
            col_idx = headers.index(col_name)
            ws.cell(row=target_row, column=col_idx+1, value=value)
    return True


def append_to_application_tracker(wb, data):
    ws = wb[APP_TRACKER_SHEET]
    # Find first empty row (Company is empty)
    headers = [cell.value for cell in ws[1]]
    try:
        company_idx = headers.index("Company")
    except ValueError:
        return None
    # Start from row 2, find first empty Company
    for row in range(2, ws.max_row + 200):  # Look ahead
        if ws.cell(row=row, column=company_idx+1).value is None or str(ws.cell(row=row, column=company_idx+1).value).strip() == "":
            # Write data
            mapping = {h: i+1 for i, h in enumerate(headers)}
            for key, value in data.items():
                if key in mapping:
                    ws.cell(row=row, column=mapping[key], value=value)
            return row
    return None


def append_daily_log(wb, log_data):
    ws = wb[DAILY_RUN_LOG_SHEET]
    row = ws.max_row + 1
    mapping = {h: i+1 for i, h in enumerate(DAILY_LOG_HEADERS)}
    for key, value in log_data.items():
        if key in mapping:
            ws.cell(row=row, column=mapping[key], value=value)
    return row
