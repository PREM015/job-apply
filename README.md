# Job Agent

Local-first, offline-capable job review tooling. Imported company records and
jobs are stored in SQLite; the dashboard is bound to `127.0.0.1`. Applications
remain manual. LIVE discovery and submission are disabled in this build.

## Quickstart

```powershell
.\.venv\Scripts\python.exe -m job_agent doctor
.\.venv\Scripts\python.exe -m pytest -q
.\run_fixture_demo.bat
.\run_dashboard.bat
```

`run_fixture_demo.bat` writes only to `data\fixture_job_agent.sqlite3` and
labels its output FIXTURE. It must not be interpreted as real job data.

## Data separation

- `data\job_agent.sqlite3` is the LIVE-designated database for owner company
  imports. No LIVE job fetching is enabled.
- `data\fixture_job_agent.sqlite3` is used exclusively by fixture runs.
- Workbook imports open the workbook read-only. Exports create a separate
  workbook and never modify the master.
- Registry URLs are stored exactly as provided and are not verified or fetched.

## Owner approval gate

Review `config\preferences.draft.yaml`, edit it as needed, and save the approved
copy as `config\preferences.yaml`. The owner must then send the exact phrase
`PREFERENCES APPROVED` before PART 4 can begin. This build does not create the
approved file and does not start PART 4.

## Main folders

- `job_agent\`: application, CLI, database, pipeline, sources, dashboard.
- `tests\`: offline FIXTURE tests; tests do not fetch job URLs.
- `config\`: safe config examples, registry input, and keyword groups.
- `data\`: ignored local databases and exports.
- `project-planning\`: audit, task, and owner-gate documentation.
- `archive\`: retained legacy material; never permanently deleted.

The three owner-maintained personalization files are `profile.yaml`,
`answers.yaml`, and `config\preferences.yaml`. The owner reviews the draft and
creates the approved preferences file manually.

## Run helpers

- `run_dashboard.bat`: launches Streamlit on loopback only.
- `run_tests.bat`: runs the FIXTURE test suite.
- `run_fixture_demo.bat`: runs and exports the offline fixture demo.
- `run_daily.bat`: requires owner preferences and currently runs FIXTURE data
  only; LIVE discovery remains disabled.
- `run_job_agent.bat`: invokes the guarded CLI.

`python -m job_agent import-registry` imports the bundled owner registry and
keyword groups into the configured local database without network access.
`python -m job_agent doctor` reports local environment and database status.

## Safety

- `--live` is refused; automatic applications and submissions are unavailable.
- Portal links are rendered as ordinary hyperlinks and are never fetched by
  the dashboard.
- `never_touch` portals have no adapters or fetch targets.
- `open_feed_candidate` portals have no configured feed URL or adapter and
  require terms approval before any future implementation.
- Adapter endpoint patterns remain UNVERIFIED until checked against an
  owner-approved real response.
