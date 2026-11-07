# Folder guide

This guide describes the repository layout and distinguishes live owner data
from offline test fixtures.

| Path | Purpose | Data and safety notes |
|---|---|---|
| `job_agent/` | Python application: CLI, database, company import, pipeline, sources, tracking, and dashboard. | Source adapters are unverified until separately checked against live endpoints. |
| `tests/` | Automated unit and offline integration tests. | Test jobs are FIXTURE data; tests must not make network requests. |
| `config/` | Application settings, registry inputs, keyword groups, and the unapproved preferences draft. | Do not create `config/preferences.yaml` until the owner reviews the draft and approves it. |
| `data/` | Local SQLite databases, backups, and generated exports. | `job_agent.sqlite3` is the LIVE owner-company database; `fixture_job_agent.sqlite3` is FIXTURE-only. Keep these datasets separate. |
| `docs/` | Schema, operating, and repository documentation. | Documentation does not authorize network requests or submissions. |
| `project-planning/` | Audit evidence, task board, gates, and owner actions. | Treat task-board snapshots as historical where identified; see `BLOCKED.md` for current gates. |
| `archive/` | Retained legacy files and append-only move/hash records. | Archive rather than permanently delete; update `archive/MOVE_LOG.md` for each move. |
| `tools/` | Local maintenance and safety utilities, including the PII scanner. | Utilities should not contact external services. |
| `logs/` | Local run output. | Logs may contain operational details; do not commit generated logs without review. |
| `proofs/` | Owner-provided application proof material. | Retention and disposition require owner review. |
| `browser_profile/` | Local browser profile data. | Keep private; do not commit or archive pending owner direction. |
| `shareable-project-report/` | Prepared project-report material. | Review for personal or sensitive data before sharing. |

## Root-level entry points

- `run_tests.bat` runs the offline test suite.
- `run_fixture_demo.bat` runs the explicitly labeled FIXTURE demonstration.
- `run_dashboard.bat` starts the local dashboard bound to `127.0.0.1`.
- `run_daily.bat` is guarded by the owner preferences gate; LIVE discovery is
  disabled in this build.
- `run_job_agent.bat` invokes the guarded CLI.
- `README.md` documents setup, owner approval, and safety constraints.

The master workbook, resume, `.env`, `profile.yaml`, `answers.yaml`,
`config.yaml`, and the Python installer are owner/protected files. Do not edit,
move, stage, or delete them as part of routine application changes.
