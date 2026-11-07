"""Streamlit dashboard. Local-only review tool; no network and no Excel writes."""
from __future__ import annotations

from ..config import load_config
from ..db.repository import Database
from ..errors import SafetyLockError
from ..io.excel_exporter import export_workbook
from . import actions, queries


def assert_local_host(host: str) -> None:
    if host != "127.0.0.1":
        raise SafetyLockError("dashboard may bind only to 127.0.0.1")


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Job Agent", layout="wide")
    config_path = st.sidebar.text_input("Config", "config/config.yaml")
    config = load_config(config_path)
    assert_local_host(config["dashboard"]["host"])
    db = Database(config["database_path"], backup_keep=config["limits"].get("backup_keep", 14))
    db.connect()
    db.migrate()
    try:
        page = st.sidebar.radio("Page", [
            "Today's Apply List", "Needs Review", "Job Detail", "All Jobs", "Applications",
            "Companies", "Source Health", "Stats", "Portal Links", "Saved Alert Checklist",
            "Add Job", "Runs", "Rejections", "Exports",
        ])
        if page == "Today's Apply List":
            st.header("Today's Apply List")
            st.dataframe(queries.today_apply_list(db), use_container_width=True)
        elif page == "Needs Review":
            st.header("Needs Review")
            st.dataframe(queries.needs_review(db), use_container_width=True)
        elif page == "Job Detail":
            job_id = st.number_input("Job ID", min_value=1, step=1)
            job = queries.job_detail(db, int(job_id))
            if job:
                st.subheader(job["title"])
                st.write(job["company_name"], job["canonical_url"])
                st.json(job.get("score_breakdown", "{}"))
            else:
                st.info("No job with that ID")
        elif page == "All Jobs":
            st.header("All Jobs")
            st.dataframe(queries.all_jobs(db), use_container_width=True)
        elif page == "Applications":
            st.header("Applications")
            st.dataframe(queries.applications(db), use_container_width=True)
        elif page == "Companies":
            st.header("Companies")
            st.dataframe(queries.companies(db), use_container_width=True)
            st.subheader("Global Targets")
            st.dataframe(queries.global_targets(db), use_container_width=True)
        elif page == "Source Health":
            st.header("Source Health")
            st.dataframe(queries.source_health(db), use_container_width=True)
        elif page == "Stats":
            st.header("Stats")
            st.json(queries.stats(db))
        elif page == "Portal Links":
            st.header("Portal Links")
            st.caption("Plain links only. The dashboard never fetches them.")
            for link in queries.portal_links(db):
                st.markdown(f"[{link['company']} - {link['kind']}]({link['url']})")
        elif page == "Saved Alert Checklist":
            st.header("Saved Alert Checklist")
            for item in ("LinkedIn saved search reviewed", "Naukri alerts reviewed",
                         "Instahyre alerts reviewed", "Wellfound alerts reviewed",
                         "Cutshort alerts reviewed", "Company career pages checked"):
                st.checkbox(item, key=f"alert-{item}")
        elif page == "Add Job":
            st.header("Add Job Manually")
            with st.form("manual-job"):
                canonical_url = st.text_input("Canonical URL")
                title = st.text_input("Title")
                company_name = st.text_input("Company")
                location_raw = st.text_input("Location")
                work_mode = st.selectbox("Work mode", ["unknown", "onsite", "hybrid", "remote"])
                description_text = st.text_area("Description")
                submitted = st.form_submit_button("Add job")
            if submitted:
                try:
                    job_id, created = actions.add_manual_job(
                        db, canonical_url, title, company_name, location_raw, work_mode,
                        description_text,
                    )
                    st.success(f"{'Created' if created else 'Updated'} job {job_id}")
                except ValueError as exc:
                    st.error(str(exc))
        elif page == "Runs":
            st.header("Runs")
            st.dataframe(queries.runs(db), use_container_width=True)
        elif page == "Rejections":
            st.header("Rejections")
            st.dataframe(queries.rejections(db), use_container_width=True)
        else:
            st.header("Exports")
            out = st.text_input("New export filename", "data/exports/job_agent_export.xlsx")
            if st.button("Create export"):
                st.success(export_workbook(db, out, config["exports_dir"], force=False))
    finally:
        db.close()


if __name__ == "__main__":
    main()
