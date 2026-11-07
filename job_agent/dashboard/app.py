"""Streamlit dashboard. Local-only review tool; no network and no Excel writes."""
from __future__ import annotations

from pathlib import Path

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

    config_path = st.sidebar.text_input("Config", "config/config.yaml")
    config = load_config(config_path)
    assert_local_host(config["dashboard"]["host"])
    st.set_page_config(page_title="Job Agent", layout="wide")
    db = Database(config["database_path"], backup_keep=config["limits"].get("backup_keep", 14))
    db.connect()
    db.migrate()
    try:
        page = st.sidebar.radio("Page", ["Daily Queue", "Job Detail", "Applications", "Sources", "Runs", "Rejections", "Exports"])
        if page == "Daily Queue":
            st.header("Daily Queue")
            st.dataframe(queries.queue(db), use_container_width=True)
        elif page == "Job Detail":
            job_id = st.number_input("Job ID", min_value=1, step=1)
            job = queries.job_detail(db, int(job_id))
            if job:
                st.subheader(job["title"])
                st.write(job["company_name"], job["canonical_url"])
                st.json(job.get("score_breakdown", "{}"))
            else:
                st.info("No job with that ID")
        elif page == "Applications":
            st.header("Applications")
            st.dataframe(queries.applications(db), use_container_width=True)
        elif page == "Sources":
            st.header("Sources")
            st.dataframe(queries.sources(db), use_container_width=True)
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
