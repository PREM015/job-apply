# Job Agent

Read-only job discovery and scoring pipeline for a fresher/entry-level software job
search. It builds a ranked daily queue in SQLite and exports a new workbook. It does
**not** submit applications, contact recruiters, create accounts, or write the
authoritative master workbook.

## Current status

- Dry-run only; `--live` exits with code 2.
- Offline fixture pipeline is working: 5 jobs fetched, 2 rejected, 3 queued.
- 97 tests pass.
- The real preferences file is not approved yet. Stage F is paused until the owner
  sends the exact line `PREFERENCES APPROVED`.
- No commits have been made on branch `rebuild`.

## Quick start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Create and inspect the local database:

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml db-check
```

Run the offline fixture pipeline:

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml run `
  --fixtures tests/fixtures/e2e_fixture.json `
  --preferences config/preferences.example.yaml
```

Report and export:

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml report
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml export --out data/exports/daily.xlsx
```

Dashboard:

```powershell
.\.venv\Scripts\python.exe -m streamlit run job_agent/dashboard/app.py
```

The dashboard binds to `127.0.0.1` only.

## What it does

1. Reads company rows from an explicit workbook path, read-only.
2. Resolves public ATS/source URLs from fixtures or an allowlisted public source.
3. Normalizes, validates, classifies, deduplicates, scores, and applies quotas.
4. Stores runs and queue ranks in `data/job_agent.sqlite3`.
5. Exports a new workbook under `data/exports/` without opening the master workbook.
6. Lets a human mark queue items and log applications in the dashboard.

## What it never does

- Automatic form filling or application submission.
- Playwright/browser automation.
- Recruiter email, LinkedIn, or Naukri scraping.
- CAPTCHA, 2FA, login bypass, or account creation.
- Writing `D:\code\plans\PLACEMENT\job\Master_Job_Tracker_final.xlsx`.
- Setting `dry_run: false` or running `--live`.

## Files

- `job_agent/cli.py` - canonical entrypoint: `run`, `report`, `import-companies`,
  `export`, `db-check`.
- `job_agent/pipeline/` - normalize, validate, classify, dedupe, score, quota, run.
- `job_agent/sources/` - fixture-tested public source adapters.
- `job_agent/companies/` - read-only workbook importer and source resolver.
- `job_agent/io/excel_exporter.py` - new-workbook-only exporter.
- `job_agent/tracking/` - human-owned queue and application state.
- `job_agent/dashboard/` - localhost-only dashboard.
- `main.py` - legacy compatibility wrapper; `run()` is disabled.
- `config/config.yaml`, `config/sources.yaml`, `config/overrides.yaml` - safe defaults.
- `config/preferences.example.yaml` - scoring example, not the owner's real preferences.
- `docs/OPERATIONS.md`, `docs/SAFETY.md`, `docs/CANONICAL_SCHEMA.md`,
  `docs/ats_patterns.md` - operator and safety documentation.
- `project-planning/RUN_LOG.md` - evidence-backed run history.
- `project-planning/PREFERENCES_DRAFT.md` - draft awaiting owner approval.

## Scheduling

The schedulers are safe by default. They take an explicit CLI command and exit
non-zero on failure or missing arguments. They do not run live mode.

```powershell
.\run_job_agent.bat run --fixtures tests\fixtures\e2e_fixture.json --preferences config\preferences.example.yaml
```

Output is appended to `logs/scheduler.log`. Scheduled live discovery is blocked until a
future owner approval.

## Safety gates

- `--live` is refused in both the new CLI and the legacy wrapper.
- `JobAgent(dry_run=False)` raises `SafetyLockError`.
- Legacy `JobAgent.run()` raises `SafetyLockError` before any workbook or network access.
- The master workbook, resume, `.env`, `profile.yaml`, and `answers.yaml` are protected
  and ignored by Git.
- Real preferences remain owner-only; this repository ships an example only.
