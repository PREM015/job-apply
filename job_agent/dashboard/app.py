"""Streamlit dashboard. Local-only review tool; no network and no Excel writes."""
from __future__ import annotations

from ..config import load_config
from ..db.repository import Database
from ..errors import SafetyLockError
from ..io.excel_exporter import export_workbook
from . import actions, queries

DASHBOARD_PAGES = (
    "Today's Apply List", "Needs Review", "Job Detail", "All Jobs", "Applications",
    "Companies", "Source Health", "Stats", "Portal Links", "Saved Alert Checklist",
    "Add Job", "Runs", "Rejections", "Exports",
)


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
        page = st.sidebar.radio("Page", list(DASHBOARD_PAGES))
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
            links = queries.portal_links(db)
            classes = sorted({str(link.get("handling_class") or "link_only") for link in links})
            selected_class = st.selectbox("Handling class", ["Active classes", "All", *classes])
            sections = sorted({
                section.strip()
                for link in links
                for section in str(link.get("sections") or "").split(",")
                if section.strip()
            })
            selected_section = st.selectbox("Owner-list section", ["All", *sections])
            if selected_class in {"Active classes", "All"} and (
                selected_section == "All"
                or any("3 Freelancing Platforms" in s for s in selected_section.split(","))
            ):
                st.caption("Freelance (off by default); select its class to show those links.")
            practice_heading = False
            for link in links:
                handling = str(link.get("handling_class") or "link_only")
                if selected_class not in {"All", "Active classes"} and handling != selected_class:
                    continue
                if selected_class == "Active classes" and handling == "freelance_out_of_scope":
                    continue
                sections = str(link.get("sections") or "")
                if selected_section != "All" and selected_section not in sections.split(","):
                    continue
                if handling in {"community", "program_seasonal"} and not practice_heading:
                    st.subheader("Practice & Programs")
                    practice_heading = True
                if handling == "freelance_out_of_scope":
                    st.subheader("Freelance (off by default)")
                if handling == "never_touch":
                    st.caption("restricted: link only")
                elif handling == "open_feed_candidate":
                    st.caption("needs terms approval")
                label = link.get("name") or link.get("company") or "Portal"
                st.markdown(f"[{label}]({link['url']})")
                if sections:
                    st.caption(f"{handling} | {sections}")
                elif link.get("notes"):
                    st.caption(f"{handling} | {link['notes']}")
                account = st.checkbox(
                    "Owner has account", value=bool(link.get("owner_has_account")),
                    key=f"portal-account-{link.get('platform_id', label)}",
                )
                alert = st.checkbox(
                    "Alerts set", value=bool(link.get("alerts_set")),
                    key=f"portal-alert-{link.get('platform_id', label)}",
                )
                if link.get("platform_id") and (
                    account != bool(link.get("owner_has_account"))
                    or alert != bool(link.get("alerts_set"))
                ):
                    db.update_registry_platform(
                        link["platform_id"], owner_has_account=account, alerts_set=alert,
                    )
        elif page == "Saved Alert Checklist":
            st.header("Saved Alert Checklist")
            alerts = queries.saved_alerts(db)
            if not alerts:
                st.info("Run import-registry to load keyword-based alert items.")
            for item in alerts:
                checked = st.checkbox(
                    f"{item['keyword_group']}: {item['keyword']}",
                    value=bool(item["checked"]), disabled=not bool(item["enabled"]),
                    key=f"saved-alert-{item['alert_id']}",
                )
                if checked != bool(item["checked"]) and item["enabled"]:
                    db.set_saved_alert_checked(item["alert_id"], checked)
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
