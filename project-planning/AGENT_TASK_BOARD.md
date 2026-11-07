# Agent task board

Last updated: **2026-11-07**
Current task: **Correction 4 local safety and registry implementation**
Next task: **PART 4 only after exact `PREFERENCES APPROVED`**.

## Execution update (2026-11-07)

The detailed task rows below are the original planning snapshot, not current
execution evidence. Use the latest local commits, test output, and
`project-planning/BLOCKED.md` to determine present status. The current build is
offline-only: fixture jobs are separated from the owner company database,
registry URLs are stored unverified, and no LIVE source or apply request is
authorized. The real G4 import has not been confirmed in this session.

## 1. Status legend

| Status | Meaning |
|---|---|
| `DONE` | Completed with evidence in this document |
| `TODO` | Approved later; not started |
| `BLOCKED` | Waiting for a gate, owner decision, or dependency |
| `REMOVED` | Removed from scope by owner decision |

Do not start a task whose dependencies are not `DONE`. Do not start a second task in the same session. One task = one report = one stop.

## 2. Summary

| Phase | Task range | Done | Removed | Blocked/TODO |
|---|---|---:|---:|---:|
| 0 | A-000 - A-001 | 1 | 0 | 1 |
| 1 | A-002 - A-014 | 2 | 0 | 11 |
| 2 | A-015 - A-029 | 0 | 0 | 15 |
| 3 | A-030 - A-042 | 0 | 0 | 13 |
| 4 | A-043 - A-056 | 0 | 1 | 13 |
| 5 | A-057 - A-060 | 0 | 0 | 4 |
| **Total** | **A-000 - A-060** | **3** | **1** | **57** |

A-053 is the removed Telegram task. Phase 6 has no assigned IDs yet.

## 3. Phase 0 - Audit and approval

| ID | Task | Status | Priority | Depends on | Acceptance | Evidence |
|---|---|---|---|---|---|---|
| A-000 | Read-only inventory, claim verification, workbook counts, cleanup manifest, hashes, planning pack | **DONE** | P0 | None | 9 planning docs; no source/workbook/config change; hashes recorded | `CURRENT_PROJECT_AUDIT.md`, `FILE_CLEANUP_MANIFEST.md`, this pack; counts: 693 companies, 526 careers URLs, 545 openings URLs, 694 recruiter data rows; Python 3.15; no Git/tests; 1 resume PDF; no backups dir |
| A-001 | Owner review and authoritative workbook confirmation | **BLOCKED** | P0 | G1 + H-01 | Owner approves architecture/roadmap and names the workbook path | H-01 confirmed `D:\code\plans\PLACEMENT\job\Master_Job_Tracker_final.xlsx`; Telegram/dashboard confirmed; full G1 not stated |

## 4. Phase 1 - Foundation and data safety

| ID | Task | Status | Priority | Depends on | Acceptance | Evidence |
|---|---|---|---|---|---|---|
| A-002 | Repository safety baseline: skeleton, `.gitignore`, Git approval, example configs | **DONE** | P0 | Owner A-002 approval, H-01 | Private files/workbook/resume/data ignored; no secrets tracked; directories exist | Git initialized; 6 dirs created; 3 example YAML templates; 31 tracked files; forbidden tracked 0; content PII 0; sensitive hashes unchanged |
| A-003 | Cleanup Batch 1: cache hygiene | **DONE** | P1 | A-002, G2 | No `.pyc`/`__pycache__` in tree; move log; imports unchanged | 5 cache files moved to `archive/legacy_20261106/cache/__pycache__/`; 0 permanent deletions; 0 `.pyc` outside archive; `archive/MOVE_LOG.md`; 9 source files parsed; sensitive hashes unchanged |
| A-004 | Dependency decision and pinned requirements | BLOCKED | P1 | A-002, G3 | Owner-approved pins; clean virtualenv install; no unpinned surprise | — |
| A-005 | Logging, redaction, and dry-run guard | TODO | P0 | A-002 | JSON logs; secrets/PII redacted; `dry_run: false` refused; `--live` refused | — |
| A-006 | Config schema and example files | TODO | P0 | A-005 | Strict validation; no secrets; examples contain no personal data | — |
| A-007 | SQLite schema, migrations, backup hook | TODO | P0 | A-006 | Tables and FKs correct; WAL; migration test; backup before migration | — |
| A-008 | Canonical schema doc and fixture contract | TODO | P1 | A-007 | Doc matches migrations; fixture schema documented | — |
| A-009 | Repository layer and transactions | TODO | P0 | A-007, A-008 | CRUD tests; rollback on error; no raw SQL outside `db/` | — |
| A-010 | Read-only company workbook importer | BLOCKED | P0 | A-009, H-01 | Read-only open; header validation; refuses save; hash unchanged; row errors reported | — |
| A-011 | Company data-quality report | BLOCKED | P1 | A-010 | Counts by tier/URL/ATS/duplicate/missing; no names in logs | — |
| A-012 | First read-only import into SQLite | BLOCKED | P0 | A-010, A-011, G4 | Idempotent; counts approved; workbook hash unchanged | — |
| A-013 | Cleanup Batch 2: archive prototypes | BLOCKED | P1 | A-002, A-005, A-009, G2 | Notify call sites removed first; no live dependents; move log; smoke test | — |
| A-014 | Baseline tests, lint, typecheck, offline harness | TODO | P1 | A-002 - A-013 | All offline tests pass; commands documented | — |

## 5. Phase 2 - Discovery and sources

| ID | Task | Status | Priority | Depends on | Acceptance | Evidence |
|---|---|---|---|---|---|---|
| A-015 | HTTP client: timeout, retries, Retry-After, rate limit, caps | TODO | P0 | A-005, A-006 | Mock-server tests; 403/429 behavior; no real network in tests | — |
| A-016 | Adapter base and registry | TODO | P0 | A-015 | Uniform contract; one failure isolated; config validated | — |
| A-017 | JSON-LD `JobPosting` adapter | TODO | P1 | A-016 | Fixture parse; missing fields safe; no guessing | — |
| A-018 | Sitemap adapter | TODO | P1 | A-016 | Fixture test; lastmod filter; cap respected | — |
| A-019 | Greenhouse adapter | TODO | P1 | A-016 | Fixture test; token and source ID preserved | — |
| A-020 | Lever adapter | TODO | P1 | A-016 | Fixture test; source ID preserved | — |
| A-021 | Ashby adapter | TODO | P1 | A-016 | Fixture test; source ID preserved | — |
| A-022 | SmartRecruiters adapter | TODO | P2 | A-016 | Fixture test; source ID preserved | — |
| A-023 | Workable adapter | TODO | P2 | A-016 | Fixture test; source ID preserved | — |
| A-024 | Keka and Zoho research plus fixtures | TODO | P2 | A-016 | Pattern documented; offline fixture; no live claim | — |
| A-025 | Source resolver and overrides | TODO | P0 | A-010, A-016 | Resolution order; override wins; unresolved report | — |
| A-026 | Source health and circuit breaker | TODO | P1 | A-016, A-025 | Repeated failure stops source, not run; jobs stay active | — |
| A-027 | Offline adapter tests and fixtures | TODO | P1 | A-017 - A-024 | Every adapter has a fixture; no network | — |
| A-028 | Source coverage report | TODO | P2 | A-025 | Counts by type/status; no company names in logs | — |
| A-029 | First approved read-only live spike | BLOCKED | P1 | A-015 - A-028, G5 | Terms noted; cap respected; results labeled LIVE; no workbook writes; stop on block | — |

## 6. Phase 3 - Normalize, classify, score, dedupe

| ID | Task | Status | Priority | Depends on | Acceptance | Evidence |
|---|---|---|---|---|---|---|
| A-030 | Normalizer | TODO | P0 | A-008 | Pure tests; relative URLs kept; tracking params removed; bounded text | — |
| A-031 | Validator with reason codes | TODO | P0 | A-030 | Rejections have reasons; malformed input does not raise | — |
| A-032 | Experience classifier | TODO | P0 | A-031 | Full enum; ambiguous -> unknown | — |
| A-033 | Software vs non-software classifier | TODO | P0 | A-031 | Word boundaries; false positives rejected; evidence stored | — |
| A-034 | Work mode and country eligibility | TODO | P1 | A-031 | Explicit-only; unknown stays unknown | — |
| A-035 | Word-boundary skill extraction | TODO | P0 | A-031 | `C++`, `C#`, `.NET`, `Node.js`; evidence stored | — |
| A-036 | Gated scorer with breakdown | TODO | P0 | A-032 - A-035 | Weights sum to 100; missing data 0; non-software unscoreable; deterministic | — |
| A-037 | Three-layer dedupe | TODO | P0 | A-009, A-030 | Source ID, canonical URL, fingerprint; flag possible duplicates | — |
| A-038 | Applied-history and suppression | TODO | P0 | A-009, A-037 | Applied jobs never re-enter; suppression auditable | — |
| A-039 | Quota selector | TODO | P1 | A-036 - A-038 | Tier/day/company caps; rejects excluded | — |
| A-040 | Pipeline orchestration and run record | TODO | P0 | A-030 - A-039 | One transaction; counters match; failures isolated | — |
| A-041 | Offline pipeline integration tests | TODO | P1 | A-030 - A-040 | Fixture run yields expected queue; invariants pass | — |
| A-042 | Scoring calibration with owner | BLOCKED | P1 | A-036, A-041, owner | Owner approves weights or changes them in writing | — |

## 7. Phase 4 - Tracking, Excel, CLI, and daily queue

| ID | Task | Status | Priority | Depends on | Acceptance | Evidence |
|---|---|---|---|---|---|---|
| A-043 | Application tracking repository and transitions | TODO | P0 | A-009 | Manual statuses; timestamps; notes; no auto-apply | — |
| A-044 | Queue state and append-only events | TODO | P1 | A-009, A-039 | Every state change has actor and timestamp | — |
| A-045 | Excel exporter from SQLite | TODO | P0 | A-043, A-044 | Never opens master; new file only; `data/exports/` only | — |
| A-046 | Export validation and hashes | TODO | P1 | A-045 | Export validates; master hash unchanged; export hash recorded | — |
| A-047 | CLI: run/report/import/export/db-check | TODO | P1 | A-040, A-043 - A-046 | Non-interactive; dry-run only; `--live` exits non-zero | — |
| A-048 | Scheduler-safe launchers | TODO | P2 | A-047 | No `pause`; logs; non-zero on failure | — |
| A-049 | Daily run report | TODO | P1 | A-040, A-047 | Counts, failures, top rejects, queue size; no PII | — |
| A-050 | Daily queue generation | TODO | P1 | A-039, A-044, A-049 | Persisted rank/score/reason; applied/duplicate/suppressed excluded | — |
| A-051 | End-to-end offline integration test | TODO | P1 | A-047 - A-050 | Fixtures -> queue -> export; no network; invariants pass | — |
| A-052 | SQLite backup and restore | TODO | P1 | A-007, A-043 | Backup before migration; restore tested | — |
| A-053 | Telegram notifications and config | **REMOVED** | P0 | - | Removed by owner decision; do not implement | Scope decision in `README.md` and `PROJECT_STATUS.md` |
| A-054 | Operator runbook and README rewrite | TODO | P1 | A-047 - A-052 | Install/test/import/run/export/dashboard documented; no overclaims | — |
| A-055 | Performance and request-cap review | TODO | P2 | A-049 - A-051 | Bounded run time; caps documented | — |
| A-056 | Scheduled dry-run rehearsal | BLOCKED | P2 | A-048, A-051, A-055 | One scheduled offline run; logs and run record verified | — |

## 8. Phase 5 - Local dashboard

| ID | Task | Status | Priority | Depends on | Acceptance | Evidence |
|---|---|---|---|---|---|---|
| A-057 | Dashboard skeleton and read-only queue/detail | BLOCKED | P2 | A-043 - A-050, G3 | `127.0.0.1` only; DB via queries; no workbook; no outbound network | — |
| A-058 | Status, notes, suppression, application log actions | BLOCKED | P2 | A-057, A-043, A-044 | DB-only writes; actor/timestamp audit; no submit/contact | — |
| A-059 | Sources, runs, rejections, export pages | BLOCKED | P2 | A-057, A-028, A-045, A-049 | Read-only health; new export only; master untouched | — |
| A-060 | Dashboard tests, no-network guard, docs | BLOCKED | P2 | A-057 - A-059 | Mocked HTTP asserts zero calls; local bind test; docs updated | — |

## 9. Task details for A-000

### A-000 completed work

- Read-only inventory of all files, hidden files, directories, caches, stray scripts, and environment.
- Import graph for all local Python modules.
- Bounded verification of missing helpers, `NameError`, skill-scoring behavior, URL handling, tracker resolution, and workbook counts.
- Claim-by-claim verification with `VERIFIED` / `CONTRADICTED` / `UNVERIFIED` / `PARTIAL` statuses.
- Read-only workbook analysis: counts and headers only.
- SHA-256 baseline for both workbooks, config, profile, answers, requirements, `.env.example`, `.gitignore`, and the resume.
- Created this planning pack. No source, config, workbook, resume, or private file was modified.

### A-000 evidence index

| Evidence | Location |
|---|---|
| Full audit and claim table | `CURRENT_PROJECT_AUDIT.md` |
| Every-file classification and batches | `FILE_CLEANUP_MANIFEST.md` |
| Target design | `TARGET_ARCHITECTURE.md` |
| Phase plan and gates | `MASTER_DEVELOPMENT_ROADMAP.md` |
| Owner actions | `HUMAN_TASK_CHECKLIST.md` |
| Safety and approval rules | `PROJECT_EXECUTION_RULES.md` |
| Current status and hashes | `PROJECT_STATUS.md` |
| Planning entry point | `README.md` |

### A-000 outputs that must not be repeated without approval

- Reading `profile.yaml`/`answers.yaml` contents.
- Reading the resume PDF.
- Writing any workbook.
- Network calls or live probes.
- Moving or deleting any file.
- Installing or updating packages.

## 10. Board maintenance rules

- Update only the row for the task just completed and the "Current task" line.
- Evidence must be a factual command, count, test result, or file reference. No PII.
- Do not mark a task `DONE` until its acceptance criteria and tests pass.
- If a task is blocked, state the exact gate or dependency; do not guess.
- If a task changes scope, record the owner decision here and in `PROJECT_STATUS.md`.
- Keep `A-053` as `REMOVED`; do not reuse the ID for another task.
- Phase 6 IDs are assigned only after G6.
