#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import hashlib
from datetime import datetime
from pathlib import Path
import yaml
from dotenv import load_dotenv

import excel_io
import discover
import match
from job_agent.errors import SafetyLockError
# Stage tracker
load_dotenv()

LOCK_FILE = "job_agent.lock"
PENDING_FILE = "pending_updates.json"


class JobAgent:
    def __init__(self, dry_run=True):
        if dry_run is not True:
            raise SafetyLockError("live mode is not available")
        self.dry_run = True
        self.mode = "dry"
        self.config = self.load_config()
        self.profile = self.load_profile()
        self.answers = self.load_answers()
        self.stats = {
            "companies_checked": 0,
            "sources": 0,
            "sources_failed": 0,
            "new_jobs": 0,
            "matched": 0,
            "applied": 0,
            "manual_needed": 0,
            "skipped": 0,
            "errors": 0
        }
        self.applied_jobs = []
        self.manual_jobs = []
        self.skipped_reasons = {}

    def load_config(self):
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_profile(self):
        with open("profile.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_answers(self):
        with open("answers.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def acquire_lock(self):
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE) as f:
                    pid = f.read().strip()
                raise Exception("Another instance may be running. Remove job_agent.lock if stale.")
            except:
                raise
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))

    def release_lock(self):
        try:
            os.remove(LOCK_FILE)
        except:
            pass

    def run(self):
        raise SafetyLockError("legacy job flow is disabled; use job_agent.cli")
        try:
            self.acquire_lock()
            print(f"Starting job agent in {self.mode} mode...")

            tracker_path = excel_io.get_tracker_path()
            print(f"Using tracker: {tracker_path}")

            # Backup
            backup_path = excel_io.backup_workbook(tracker_path, self.config.get("keep_backups", 14))
            print(f"Backup created: {backup_path}")

            # Load workbook
            wb = excel_io.load_workbook_safe(tracker_path)
            wb = excel_io.ensure_new_sheets(wb)

            # Get existing data for dedup
            existing_keys = excel_io.get_job_openings_keys(wb)
            applied_urls = excel_io.get_applied_urls(wb)

            # Stage 1: Build watch list
            companies = excel_io.get_companies_to_watch(wb, self.config.get("tiers_to_watch", [1,2,3]))
            # Add global targets
            if "Global Product Targets" in wb.sheetnames:
                ws_gt = wb["Global Product Targets"]
                for row in range(2, ws_gt.max_row + 1):
                    companies.append({
                        "row": None,
                        "master_id": ws_gt.cell(row=row, column=1).value,
                        "company_name": ws_gt.cell(row=row, column=2).value,
                        "tier": "Global",
                        "status": ws_gt.cell(row=row, column=4).value,
                        "careers_page": ws_gt.cell(row=row, column=3).value,
                        "openings_url": ws_gt.cell(row=row, column=3).value,
                        "website": None,
                    })

            max_companies = self.config.get("max_companies_per_run", 150)
            companies = companies[:max_companies]
            self.stats["companies_checked"] = len(companies)
            print(f"Watching {len(companies)} companies")

            # Stage 2 & 3: Discover and match
            new_jobs_found = []
            for comp in companies:
                try:
                    self.stats["sources"] += 1
                    # ---- REAL DISCOVERY -------------------------------------------------
                    jobs = discover.real_discover_jobs(comp)
                    # -------------------------------------------------------------------------
                    for job in jobs:
                        # Build job_data dict (same schema as before)
                        job_key = discover.compute_job_key(comp["company_name"], job.get("title"), job.get("location"), job.get("link"))
                        job_url = job.get("link", "")
                        if discover.is_duplicate_job(job_key, job_url, existing_keys) or job_url in applied_urls:
                            continue
                        if not discover.is_posted_recent(job.get("posted_date"), 7):
                            continue

                        self.stats["new_jobs"] += 1
                        job_data = {
                            "Job Key": job_key,
                            "Date Found": datetime.now().strftime("%Y-%m-%d"),
                            "Master ID": comp["master_id"],
                            "Company": comp["company_name"],
                            "Job Title": job.get("title"),
                            "Location": job.get("location"),
                            "Work Mode": "",  # will be filled later if available
                            "Experience Required": "",  # will be extracted later
                            "Posted Date": job.get("posted_date", ""),
                            "Job Link": job.get("link"),
                            "Found Via": job.get("source", "careers_page"),
                            "Description": job.get("snippet", "")
                        }

                        score, reasons = match.score_job(job_data, self.config, self.profile)
                        self.stats["matched"] += 1
                        decision, skip_reason = match.decide_action(job_data, score, self.config)

                        job_data["Match Score"] = score
                        job_data["Match Reasons"] = reasons
                        job_data["Decision"] = decision
                        job_data["Skip Reason"] = skip_reason
                        job_data["Apply Status"] = "Queued" if decision in ["Auto-Apply", "Manual Apply"] else "Closed"
                        job_data["Last Checked"] = datetime.now().strftime("%Y-%m-%d")

                        new_jobs_found.append(job_data)

                        if decision == "Skipped":
                            self.stats["skipped"] += 1
                            self.skipped_reasons[skip_reason] = self.skipped_reasons.get(skip_reason, 0) + 1
                        elif decision == "Manual Apply":
                            self.stats["manual_needed"] += 1
                            self.manual_jobs.append({**job_data, "reason": skip_reason or "Manual apply required"})
                        # Auto-Apply will be handled in stage 4
                except Exception as e:
                    self.stats["errors"] += 1
                    self.stats["sources_failed"] += 1
                    print(f"Error processing {comp['company_name']}: {e}")

            # Save discovered jobs
            for job in new_jobs_found:
                try:
                    excel_io.append_job_opening(wb, job)
                    existing_keys.add(job["Job Key"])
                except Exception as e:
                    print(f"Error saving job: {e}")

            # Stage 4: Apply (limited)
            daily_limit = self.config.get("daily_limit", 10)
            auto_jobs = [j for j in new_jobs_found if j.get("Decision") == "Auto-Apply"]
            auto_jobs.sort(key=lambda x: x.get("Match Score", 0), reverse=True)

            if not self.dry_run and self.stats["applied"] < daily_limit:
                for job in auto_jobs:
                    if self.stats["applied"] >= daily_limit:
                        break
                    try:
                        success = self.apply_job(job)
                        if success:
                            self.stats["applied"] += 1
                            self.applied_jobs.append(job)
                            # Update job status
                            excel_io.update_companies_row(wb, job.get("Master ID"), {
                                "Application Status": "Applied",
                                "Date Applied": datetime.now().strftime("%Y-%m-%d"),
                                "Next Action Date": (datetime.now().replace(day=datetime.now().day+7)).strftime("%Y-%m-%d") if datetime.now().day < 24 else datetime.now().strftime("%Y-%m-%d"),
                                "My Notes": f"Applied: {job.get('Job Title')}"
                            })
                            # Add to tracker
                            tracker_row = excel_io.append_to_application_tracker(wb, {
                                "Entry Source": "Auto-agent",
                                "Date Logged": datetime.now().strftime("%Y-%m-%d"),
                                "Company": job.get("Company"),
                                "Job / Internship Title": job.get("Job Title"),
                                "Application URL": job.get("Job Link"),
                                "Outreach Status": "Applied",
                                "Notes": f"Applied via agent; score {job.get('Match Score')}; proof: proofs/{datetime.now().strftime('%Y-%m-%d')}/{job.get('Job Key')}.png"
                            })
                        else:
                            self.manual_jobs.append({**job, "reason": "Auto-apply failed - needs manual"})
                            self.stats["manual_needed"] += 1
                    except Exception as e:
                        print(f"Error applying to {job.get('Company')}: {e}")
                        self.stats["errors"] += 1
            elif self.dry_run:
                print(f"DRY RUN: Would apply to {len(auto_jobs)} auto-apply jobs (limited to {daily_limit})")

            # Stage 5: Save Excel
            excel_io.save_workbook_safe(wb, tracker_path)
            print("Excel updated")

            # Stage 6: Placeholder
            self.stats["limit"] = daily_limit
            self.stats["mode"] = self.mode
            self.stats["tomorrow_notes"] = "Continue rotation"
            print("Stage 6: placeholder digest")

            # Log run
            wb2 = excel_io.load_workbook_safe(wb)
            excel_io.append_daily_log(wb2, {
                "Run Date": datetime.now().strftime("%Y-%m-%d"),
                "Mode (dry/live)": self.mode,
                "Companies Checked": self.stats["companies_checked"],
                "Sources Failed": self.stats["sources_failed"],
                "New Jobs Found": self.stats["new_jobs"],
                "Matched": self.stats["matched"],
                "Applied": self.stats["applied"],
                "Manual Needed": self.stats["manual_needed"],
                "Skipped": self.stats["skipped"],
                "Errors": self.stats["errors"],
                "Notes": f"Dry-run: {self.dry_run}"
            })
            excel_io.save_workbook_safe(wb2, tracker_path)

            print("Run complete!")
            return self.stats

        except Exception as e:
            print(f"Error: {e}")
            self.stats["errors"] += 1
            print("Error logged placeholder")
            raise
        finally:
            self.release_lock()

    def discover_jobs_for_company(self, comp):
        # Kept for backward compatibility but now delegates to real discovery
        return discover.real_discover_jobs(comp)

    def apply_job(self, job):
        raise SafetyLockError("application submission is not supported")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Daily Job Search + Apply Automation")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (default)")
    parser.add_argument("--live", action="store_true", help="Live mode")
    parser.add_argument("--discover-only", action="store_true", help="Discover only, no apply")
    parser.add_argument("--report", action="store_true", help="Generate report only")
    args = parser.parse_args()

    if args.live:
        print("SAFETY LOCK: live mode is not available; dry-run only", file=sys.stderr)
        raise SystemExit(2)

    agent = JobAgent(dry_run=True)
    try:
        stats = agent.run()
        print(json.dumps(stats, indent=2))
    except Exception as e:
        print(f"Failed: {e}")


if __name__ == "__main__":
    main()