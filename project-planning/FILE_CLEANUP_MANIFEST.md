# File cleanup manifest

Task: **A-000 read-only inventory**, updated with evidence.  
This manifest classifies every file and directory found in the repository. It does not authorize any move or deletion. Cleanup starts only after **G2**.

**Post-A-002 update:** A-002 created `.git/`, `job_agent/`, `tests/`, `config/`, `data/`, `docs/`, and `archive/`, plus three blank example YAML templates. Those are safety additions, not cleanup moves. Classifications below are unchanged. See `PROJECT_STATUS.md` for current state.

**Post-A-003 update:** Batch 1 moved five root `__pycache__` `.pyc` files to `archive/legacy_20261106/cache/__pycache__/`; `archive/MOVE_LOG.md` records the moves and hashes. No permanent deletion. No source classification changed.

## 1. Classification key

| Code | Meaning |
|---|---|
| `KEEP` | Keep in place. No cleanup action. |
| `MODIFY` | Keep the path for now, but edit later under a named task. No move in A-000. |
| `REPLACE` | The file's responsibility moves to a new module or document. Freeze until the replacement exists. |
| `ARCHIVE` | Move to `archive/legacy_<YYYYMMDD>/` after G2 and after the import graph confirms no live dependents. |
| `DELETE` | Only cache/regenerable data. Prefer archiving; permanent deletion needs explicit owner approval. |
| `INVESTIGATE` | Not enough evidence to classify safely. Do not move. |

## 2. File inventory and classification

| Path | Class | Reason | Useful data? | Dependents | Replacement | Risk | Batch |
|---|---|---|---|---|---|---|---|
| `.env.example` | MODIFY | Contains obsolete portal credential names and `TELEGRAM_*` names; no secrets present | Environment-key inventory | Docs | Updated `.env.example` with only approved keys | P1 | A-006 / A-002 (no move) |
| `.gitignore` | MODIFY | Misses profile, answers, actual resume, workbooks, SQLite, data, `.venv` | Current ignore patterns | None | Expanded ignore rules | P0 | A-002 (no move) |
| `add_companies.py` | ARCHIVE | Hard-coded absolute path, writes sample rows, can overwrite the local workbook | Sample header layout | None | Read-only company importer | P1 | 2 |
| `answers.yaml` | KEEP | Sensitive owner answers; must not be moved, copied, or printed | Yes, private | `main.py`, `apply.py` | Future `config/answers.yaml` only with owner action | P0 privacy | No move |
| `apply.py` | ARCHIVE | Unwired Playwright form-filling code; latent submission risk; unused | ATS detection strings, form-flow reference | None | `docs/ats_patterns.md` plus human-assisted packet only | P0 | 2 after extracting patterns |
| `clear_tracker.py` | ARCHIVE | Permanently deletes all `Job Openings` data rows | None | None | Repository/database maintenance command (later) | P0 | 2 |
| `config.yaml` | MODIFY | Contains Telegram settings, local resume path, prototype thresholds, and no strict validation | Preferences, thresholds | `main.py`, `apply.py`, `notify.py` | `config/config.yaml` + `config/preferences.yaml` | P1 | A-004 / A-006 (no move) |
| `create_tracker.py` | ARCHIVE | Overwrites the local workbook and creates a 5-sheet starter | Starter headers | None | Test fixture generator only | P1 | 2 |
| `discover.py` | REPLACE | HTML heuristic only; drops relative URLs; no ATS adapters, rate limit, Retry-After, or circuit breaker | HTML parsing ideas, robots helper | `main.py` | `job_agent/sources/*` + resolver | P1 | Frozen until Phase 2 |
| `excel_io.py` | REPLACE | Wrong tracker precedence; writes any resolved path; deletes old backups; no lock detection | Workbook headers, append helpers | `main.py` | `job_agent/io/excel_exporter.py` + read-only importer | P1 | Frozen until Phase 1/4 |
| `main.py` | REPLACE | Calls missing helpers, reaches live mode, simulates apply, calls notify, ignores CLI modes | Orchestration skeleton, stats shape | None | `job_agent/cli.py` + `pipeline/run.py` | P0 | Frozen until Phase 1/4 |
| `Master_Job_Tracker_final.xlsx` (local) | ARCHIVE | 5-sheet starter, 2 sample companies, 3 dry-run log rows, no real jobs; resolver currently picks it first | Header layout, dry-run log example | `excel_io.get_tracker_path` | Authoritative parent workbook with explicit path (H-01) | P0 | 2 after H-01 |
| `match.py` | REPLACE | NameError in decision path; skill scoring ignores job text; substring role matching | Scoring heuristics | `main.py` | `pipeline/classify.py`, `pipeline/score.py`, `pipeline/dedupe.py` | P0 | Frozen until Phase 3 |
| `notify.py` | ARCHIVE | Telegram/email sender; Telegram removed by owner decision; called on every run | Message templates, redaction ideas | `main.py`, `apply.py` | None for Telegram; optional notifications deferred | P0 | 2 after call sites are removed |
| `<resume-pdf>` (filename withheld) | KEEP | Owner resume; read-only; must not be copied or printed | Yes, private | `config.yaml` resume paths | None | P0 privacy | No move |
| `profile.yaml` | KEEP | Sensitive owner profile; read-only; must not be moved or printed | Yes, private | `main.py`, `apply.py` | Future `config/profile.yaml` only with owner action | P0 privacy | No move |
| `README.md` | REPLACE | Overclaims ATS feeds, safe auto-apply, modes, and pending updates | Product intent and claims | None | Rewritten README after Phase 1 | P2 | A-005 (no move) |
| `require.md` | ARCHIVE | Historical audit; contains contradicted backup/resume/ATS claims | Historical evidence | None | This audit and future `docs/` | P2 | 2 |
| `requirements.txt` | MODIFY | Pins old versions; Python 3.15 mismatch; missing test/runtime packages | Dependency inventory | None | Pins for the chosen Python runtime | P1 | A-004 (no move) |
| `run_job_agent.bat` | MODIFY | Contains `pause`; not scheduler-safe; always dry-run | Launcher intent | `main.py` | Scheduler-safe launcher | P2 | A-056 (no move) |
| `run_job_agent.sh` | MODIFY | No virtualenv, no logging, always dry-run | Launcher intent | `main.py` | Scheduler-safe launcher | P2 | A-056 (no move) |
| `shareable-project-report/PROJECT_OVERVIEW.md` | MODIFY | Useful analysis; repeats outdated backup and ATS claims | Yes, analysis | None | Reconciled shareable report | P2 | A-000 follow-up (no move) |
| `shareable-project-report/PROJECT_STATUS.md` | MODIFY | Useful status; repeats outdated backup/ATS claims | Yes, analysis | None | Reconciled shareable report | P2 | A-000 follow-up (no move) |
| `shareable-project-report/TRACKER_WORKBOOK_REPORT.md` | MODIFY | Useful workbook analysis; backup claim no longer matches filesystem | Yes, analysis | None | Reconciled shareable report | P2 | A-000 follow-up (no move) |
| `__pycache__/apply.cpython-315.pyc` | DELETE | Regenerable cache | No | None | None | P3 | 1 (archive or delete) |
| `__pycache__/discover.cpython-315.pyc` | DELETE | Regenerable cache | No | None | None | P3 | 1 (archive or delete) |
| `__pycache__/excel_io.cpython-315.pyc` | DELETE | Regenerable cache | No | None | None | P3 | 1 (archive or delete) |
| `__pycache__/match.cpython-315.pyc` | DELETE | Regenerable cache | No | None | None | P3 | 1 (archive or delete) |
| `__pycache__/notify.cpython-315.pyc` | DELETE | Regenerable cache | No | None | None | P3 | 1 (archive or delete) |
| `project-planning/README.md` | KEEP | New planning entry point | Yes | None | None | P3 | No move |
| `project-planning/CURRENT_PROJECT_AUDIT.md` | KEEP | New audit | Yes | None | None | P3 | No move |
| `project-planning/FILE_CLEANUP_MANIFEST.md` | KEEP | This manifest | Yes | None | None | P3 | No move |
| `project-planning/TARGET_ARCHITECTURE.md` | KEEP | Target design | Yes | None | None | P3 | No move |
| `project-planning/MASTER_DEVELOPMENT_ROADMAP.md` | KEEP | Phase plan | Yes | None | None | P3 | No move |
| `project-planning/AGENT_TASK_BOARD.md` | KEEP | Task board | Yes | None | None | P3 | No move |
| `project-planning/HUMAN_TASK_CHECKLIST.md` | KEEP | Owner checklist | Yes | None | None | P3 | No move |
| `project-planning/PROJECT_EXECUTION_RULES.md` | KEEP | Safety and approval rules | Yes | None | None | P3 | No move |
| `project-planning/PROJECT_STATUS.md` | KEEP | Current status | Yes | None | None | P3 | No move |

## 3. Directory inventory

| Path | Class | Reason | Action |
|---|---|---|---|
| `browser_profile/` | KEEP | Runtime browser profile directory; currently empty; must stay ignored | No move |
| `logs/` | KEEP | Future rotating logs; currently empty | No move |
| `proofs/` | ARCHIVE | Legacy fake-proof output directory; currently empty; no submissions in scope | Move after G2 if still empty |
| `shareable-project-report/` | MODIFY | Useful reports with outdated claims | Edit later; no move now |
| `__pycache__/` | DELETE | Regenerable cache | Empty after file cleanup |
| `project-planning/` | KEEP | New planning pack | No move |
| `backups/` | INVESTIGATE | Referenced by `require.md` and `shareable-project-report/`, but not present now | Determine whether it was deleted or never existed; do not recreate until G2 |

Absent but referenced: `.env`, `job_agent.lock`, `pending_updates.json`, `job_agent/`, `tests/`, `config/`, `data/`, `docs/`, `archive/`, `backups/`, SQLite files, notebooks.

## 4. Read-only assets outside the repository

| Asset | Class | Reason |
|---|---|---|
| Parent workbook `../Master_Job_Tracker_final.xlsx` | KEEP / READ-ONLY | 19 sheets, 693 companies; candidate authoritative master, pending H-01 |
| Authoritative workbook path (owner-confirmed) | KEEP / READ-ONLY | Must be configured explicitly; never auto-searched |
| Resume PDF | KEEP / READ-ONLY | Private; hash only |
| `profile.yaml`, `answers.yaml` | KEEP / READ-ONLY | Private; do not read contents in planning |
| `.env` (absent) | KEEP / NEVER COMMIT | Secrets only; not present |

## 5. Proposed target directory structure

```text
job-agent/
├── config/
│   ├── config.yaml
│   ├── preferences.yaml
│   ├── preferences.example.yaml
│   ├── profile.yaml                # ignored, private
│   ├── profile.example.yaml        # blank template
│   ├── answers.yaml                # ignored, private
│   ├── answers.example.yaml        # blank template
│   └── sources.yaml                # per-source enable flags
├── job_agent/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── logging_setup.py
│   ├── http_client.py
│   ├── db/
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── backup.py
│   ├── companies/
│   │   ├── importer.py
│   │   ├── resolver.py
│   │   └── overrides.py
│   ├── sources/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   ├── ashby.py
│   │   ├── smartrecruiters.py
│   │   ├── workable.py
│   │   ├── jsonld.py
│   │   ├── sitemap.py
│   │   └── email_alerts/
│   ├── pipeline/
│   │   ├── normalize.py
│   │   ├── validate.py
│   │   ├── classify.py
│   │   ├── match.py
│   │   ├── score.py
│   │   ├── dedupe.py
│   │   ├── quota.py
│   │   └── run.py
│   ├── io/
│   │   ├── excel_importer.py
│   │   └── excel_exporter.py
│   ├── tracking/
│   │   ├── applications.py
│   │   └── queue.py
│   └── dashboard/
│       ├── app.py
│       ├── queries.py
│       ├── pages/
│       └── actions.py
├── tests/
│   ├── unit/
│   ├── integration_offline/
│   ├── fixtures/
│   └── live_spikes/
├── data/
│   ├── exports/
│   └── job_agent.sqlite3
├── docs/
│   ├── CANONICAL_SCHEMA.md
│   └── ats_patterns.md
├── project-planning/
├── logs/
├── browser_profile/
├── archive/
│   ├── legacy_<YYYYMMDD>/
│   └── MOVE_LOG.md
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

`proofs/`, the local starter workbook, and the prototype root modules are not part of the target structure. The authoritative workbook stays outside the repository and is referenced by an explicit config path.

## 6. Approval batches

### Batch 1 - cache hygiene

- Move `__pycache__/` and all `.pyc` files to `archive/legacy_<date>/cache/`.
- No source, data, workbook, resume, or config move.
- Confirm no process is running and no lock file exists.
- If the owner prefers permanent deletion of regenerable caches, that is a separate explicit approval. Default is archive.

### Batch 2 - prototype retirement

- Re-run the import graph and paste the dependents before each move.
- Extract ATS detection strings from `apply.py` into `docs/ats_patterns.md` first.
- Move `apply.py`, `notify.py`, `create_tracker.py`, `add_companies.py`, `clear_tracker.py`, `require.md`, and the local starter workbook.
- Do **not** move `main.py`, `discover.py`, `match.py`, or `excel_io.py` until their replacements exist; keep them frozen.
- Remove `notify.py` call sites before moving `notify.py`.
- Log every move in `archive/MOVE_LOG.md` with source, destination, reason, and SHA-256.

### Batch 3 - owner-named only

- Real data, backups, resume, `profile.yaml`, `answers.yaml`, `.env`, the authoritative workbook, and any ambiguous file.
- Never automatic. The owner must name each item in writing.

## 7. Pre-move checklist

1. G2 approval for the exact batch and item list.
2. Import graph re-run and pasted.
3. SHA-256 before the move.
4. Destination path under `archive/legacy_<YYYYMMDD>/` created.
5. No live dependents.
6. No workbook, resume, private config, or `.env` in the move set.
7. Move logged in `archive/MOVE_LOG.md`.
8. Post-move import/CLI smoke test.
9. SHA-256 after the move; source and destination match.

## 8. Classification counts

Existing files (29 total):

| Class | Count | Files |
|---|---:|---|
| KEEP | 3 | `profile.yaml`, `answers.yaml`, `<resume-pdf>` |
| MODIFY | 9 | `.env.example`, `.gitignore`, `config.yaml`, `requirements.txt`, 2 launchers, 3 shareable reports |
| REPLACE | 5 | `README.md`, `main.py`, `discover.py`, `match.py`, `excel_io.py` |
| ARCHIVE | 7 | `apply.py`, `notify.py`, `create_tracker.py`, `add_companies.py`, `clear_tracker.py`, `require.md`, local starter workbook |
| DELETE | 5 | 5 `__pycache__` files |
| INVESTIGATE | 1 item | missing `backups/` set (no file present) |

New planning files (9 total): all `KEEP`.

Directories: `KEEP` 3 (`browser_profile`, `logs`, `project-planning`), `MODIFY` 1 (`shareable-project-report`), `ARCHIVE` 1 (`proofs`), `DELETE` 1 (`__pycache__` after files), `INVESTIGATE` 1 (`backups`, absent).
