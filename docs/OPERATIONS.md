# Operations

## Install

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Database

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml db-check
```

Creates `data/job_agent.sqlite3` and applies forward-only migrations. Backups are written
to `data/backups/` when an existing database is reopened.

## Offline fixture run

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml run `
  --fixtures tests/fixtures/e2e_fixture.json `
  --preferences config/preferences.example.yaml
```

This is the only supported run mode. It never opens a network socket.

## Report and export

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml report
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml export --out data/exports/daily.xlsx
```

Exports are new files inside `data/exports/`; the master workbook is never touched.

## Dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run job_agent/dashboard/app.py
```

The dashboard refuses any bind address other than `127.0.0.1`.

## Company import

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml import-companies `
  --workbook "D:\code\plans\PLACEMENT\job\Master_Job_Tracker_final.xlsx"
```

The import defaults to `--commit` off and always verifies the workbook hash before and
after reading. Do not commit the real master import until the owner approves G4.

## Limits and performance

- Global HTTP request cap: 20 per run (`config/config.yaml`).
- Per-source caps: 2-5 requests per source (`config/sources.yaml`).
- Maximum jobs per run: 100.
- Maximum description length: 20,000 characters.
- HTTP timeout: 10 seconds; retries: 2; per-host delay: 1.0 second.
- Keka and Zoho are disabled and fixture-only.
- The offline fixture run takes under one second on the development machine.

## Scheduler

```powershell
.\run_job_agent.bat db-check
.\run_job_agent.bat run --fixtures tests\fixtures\e2e_fixture.json --preferences config\preferences.example.yaml
```

The launchers require an explicit command, append to `logs/scheduler.log`, never pause,
and return the CLI exit code. `--live` remains refused.

## Legacy entry point

`main.py` still exists for compatibility only. `--live` exits with code 2,
`JobAgent(dry_run=False)` raises `SafetyLockError`, and `JobAgent.run()` is disabled so
the legacy flow cannot touch a workbook or make a request. Use `python -m job_agent`.
