# Project status

Snapshot date: **2026-11-07**
Current task: **Stage C-F build complete; paused at Stage F gate**
Status: **97 tests pass; offline fixture E2E proven; no commits; awaiting `PREFERENCES APPROVED`**
Repository mode: **Dry-run only; branch `rebuild`; zero commits**.

## 1. One-line status

The new `job_agent` package now has a SQLite-backed pipeline, offline source adapters,
safe Excel import/export, a local dashboard, a safety-locked CLI, and 97 passing tests.
The offline fixture run produced 3 queued jobs and a new export workbook. Live mode is
refused. Sections 3-13 below are the historical 2026-11-06 snapshot; see section 14 for
the current verification.

## 2. Scope decisions

| Decision | Status | Effect |
|---|---|---|
| Telegram notifications | **REMOVED by owner decision** | `notify.py` is an archive candidate; no Telegram config, tests, or docs |
| Local dashboard | **Phase 5, primary interface** | Tasks A-057 - A-060; local-only; DB-only; no workbook access |
| Application submission | **Human-only** | No auto-apply, no form submission, no recruiter contact |
| Optional email/desktop notifications | **Deferred** | Not in current scope; requires a future owner decision |
| Master workbook | **Read-only input confirmed** | H-01 path: `D:\code\plans\PLACEMENT\job\Master_Job_Tracker_final.xlsx`; never written by the pipeline or dashboard |

## 3. Health indicators

| Area | State | Evidence |
|---|---|---|
| End-to-end pipeline | **Not working** | Missing discovery helpers; `NameError` in decision path |
| Safety | **Unsafe** | Live mode and simulated apply path are reachable in the prototype |
| Data layer | **Missing** | No SQLite, no migrations, no repository |
| Tests | **Missing** | No `tests/` and no test files |
| Version control | **Initialized** | `.git/` created; 32 files staged; no commit made |
| Repository skeleton | **Created** | `job_agent/`, `tests/`, `config/`, `data/`, `docs/`, `archive/` |
| Dependencies | **Incomplete** | Python 3.15; missing `pytest`, `playwright`, `Pillow`, `schedule`, `python-dateutil`, `rich` |
| Workbook resolution | **Wrong** | Local 2-row starter is still preferred by the prototype resolver |
| Authoritative workbook | **Confirmed** | H-01 path recorded; read-only |
| Dashboard | **Missing** | No dashboard code; Phase 5 plan only |
| Telegram | **Removed** | Scope decision; archive candidate |
| Privacy posture | **Improved** | Private files ignored; filename/content PII scan 0; logging/redaction still missing |

## 4. Baseline counts

| Item | Count |
|---|---:|
| Existing files classified | 29 |
| New planning docs | 9 |
| Local starter companies | 2 |
| Parent master companies | 693 |
| Parent master sheets | 19 |
| Parent careers URLs | 526 |
| Parent openings URLs | 545 |
| Parent unique URL hosts | 440 |
| Global product targets | 50 |
| Recruiter contact data rows | 694 |
| Known ATS URL cells | 6 (Keka 4, Zoho 2) |
| Application Tracker populated company rows | 5 |
| Python version | 3.15.0 |
| Git-tracked files after A-002 | 31 |
| Git-tracked files after A-003 | 32 |
| Forbidden tracked files | 0 |
| Content-PII files in tracked text | 0 |
| Blank example YAML templates | 3 |
| Skeleton directories created | 6 |
| Cache files moved to archive | 5 |
| `.pyc` files left outside archive | 0 |

## 5. Baseline SHA-256 (before A-000 writes)

These hashes were captured before the planning documents were created.

| Asset | SHA-256 |
|---|---|
| Local starter workbook `Master_Job_Tracker_final.xlsx` | `D638434124DDD30812E32B90AEC4EA43D14A04EA3854DD21E8A01F0E3F023D47` |
| Parent master `../Master_Job_Tracker_final.xlsx` | `26E8B200858392942FFF291E5574BEF57E78446E859E828368B87A48AEBF59C2` |
| `config.yaml` | `FAAC29462943D3B12ACF05493165B2ECA5DD7279F837AB8D8C3B113308564BC9` |
| `profile.yaml` | `CCD7F0C5208C9277CC9345F0356A6DD5ECA3BD3F9BF883BBCC1D2CEA5609E9B6` |
| `answers.yaml` | `0652D75A03DEE41FCA345DD60C6AE2ED4D91B17FB35833CDEA7FB62AC8F93F6A` |
| `requirements.txt` | `AFE9A51BBD96B88D7383BC43D2A0329D03FAAFF0111D51E661E8033133808B41` |
| `.env.example` | `D65635761376533DEE70D6273AB4448C81240668D5100813242AC55CEF9990C4` |
| `.gitignore` | `C4E4D63B15B8D9F9511124D9C8E96D771840607D08CC734FF889BE617C46354B` |
| `<resume-pdf>` | `7F386B19A03F60A29E40896D1DA89F8220FB88653EFEDA3842D7B1F0A092EAC6` |

The resume filename is withheld. `profile.yaml` and `answers.yaml` were hashed only; their contents were not read.

## 6. After A-000 writes

A-000 only adds files under `project-planning/`. The workbooks, resume, configs, and requirements should therefore be byte-identical.

| Asset | SHA-256 after | Match? |
|---|---|---|
| Local starter workbook | `D638434124DDD30812E32B90AEC4EA43D14A04EA3854DD21E8A01F0E3F023D47` | Yes |
| Parent master | `26E8B200858392942FFF291E5574BEF57E78446E859E828368B87A48AEBF59C2` | Yes |
| `config.yaml` | `FAAC29462943D3B12ACF05493165B2ECA5DD7279F837AB8D8C3B113308564BC9` | Yes |
| `profile.yaml` | `CCD7F0C5208C9277CC9345F0356A6DD5ECA3BD3F9BF883BBCC1D2CEA5609E9B6` | Yes |
| `answers.yaml` | `0652D75A03DEE41FCA345DD60C6AE2ED4D91B17FB35833CDEA7FB62AC8F93F6A` | Yes |
| `requirements.txt` | `AFE9A51BBD96B88D7383BC43D2A0329D03FAAFF0111D51E661E8033133808B41` | Yes |
| `.env.example` | `D65635761376533DEE70D6273AB4448C81240668D5100813242AC55CEF9990C4` | Yes |
| `.gitignore` | `C4E4D63B15B8D9F9511124D9C8E96D771840607D08CC734FF889BE617C46354B` | Yes |
| `<resume-pdf>` | `7F386B19A03F60A29E40896D1DA89F8220FB88653EFEDA3842D7B1F0A092EAC6` | Yes |

Verification command: `Get-FileHash -Algorithm SHA256` on each asset, run after the planning docs were written. All nine hashes match the baseline. Planning docs count: 9.

## 6A. A-002 verification

A-002 added the Git safety baseline and blank example templates. The sensitive assets listed in section 5 were rehashed after A-002 and all match their baseline values.

| Check | Result |
|---|---|
| Sensitive hashes (workbook, parent, config, profile, answers, requirements, `.env.example`, resume) | All match section 5 |
| `.gitignore` | Intentionally changed: `C4E4D63B15B8D9F9511124D9C8E96D771840607D08CC734FF889BE617C46354B` -> `B816BF459423B8F6DEAC96F8524F0C8C2ACE706BEE4E814F4CD301B83CCD50DC` |
| Git initialized | Yes; `.git/` present |
| Skeleton directories | 6/6 present |
| Blank example templates | 3; each parses as YAML `NoneType` |
| Git-tracked files | 31 |
| Forbidden tracked files (`.env`, `profile.yaml`, `answers.yaml`, `config.yaml`, PDF, Excel) | 0 |
| Content-PII scan in tracked text files | 0 files |
| Commit made | No |

Commands: `git init`; `git check-ignore -q`; `git add -A`; `git ls-files`; PowerShell SHA-256 checks; YAML parse via PyYAML; PowerShell filename and content scan. No source, workbook, resume, private config, or `.env` file was modified.

## 6B. A-003 verification

A-003 moved the five root `__pycache__` bytecode files into `archive/legacy_20261106/cache/__pycache__/`. No permanent deletion. Source files were not changed.

| Check | Result |
|---|---|
| Cache files moved | 5 |
| Destination | `archive/legacy_20261106/cache/__pycache__/` |
| Permanent deletions | 0 |
| `.pyc` files outside archive | 0 |
| `__pycache__` directories outside archive | 0 |
| Move log | `archive/MOVE_LOG.md` |
| Archived cache ignored by Git | Yes |
| Move log tracked by Git | Yes |
| Source imports parsed | All 9 top-level Python files parsed; import graph unchanged |
| Source changes | 0 |
| Sensitive hashes | All match section 5 |
| Commit made | No |

Commands: `Move-Item`; `Get-FileHash`; `git check-ignore -q`; `git status --short`; `python -B` AST parse. AST parsing emitted pre-existing invalid-escape `SyntaxWarning`s from source regex strings; no file was changed.

## 7. What exists now

Planning documents:

- `README.md`
- `CURRENT_PROJECT_AUDIT.md`
- `FILE_CLEANUP_MANIFEST.md`
- `TARGET_ARCHITECTURE.md`
- `MASTER_DEVELOPMENT_ROADMAP.md`
- `AGENT_TASK_BOARD.md`
- `HUMAN_TASK_CHECKLIST.md`
- `PROJECT_EXECUTION_RULES.md`
- `PROJECT_STATUS.md`

A-002 additions:

- `.git/` initialized; 31 files staged; no commit
- `job_agent/`, `tests/`, `config/`, `data/`, `docs/`, `archive/`
- `config/profile.example.yaml`
- `config/answers.example.yaml`
- `config/preferences.example.yaml`
- updated `.gitignore`

A-003 additions:

- `archive/MOVE_LOG.md`
- `archive/legacy_20261106/cache/__pycache__/` containing 5 archived `.pyc` files
- root `__pycache__/` removed after archiving

No source file, workbook, resume, private config, or `.env` file was modified. The archive is ignored by Git; the move log is tracked.

## 8. Blockers

| Blocker | Owner action | Blocks |
|---|---|---|
| Full planning approval | `G1 APPROVED` for later phases | A-005, A-006, and later implementation |
| Authoritative workbook | **Confirmed** via H-01 | No longer blocked |
| Cleanup approval | **G2 confirmed for Batch 1** | Batch 2 still needs explicit G2 |
| Dependency approval | `G3 APPROVED: <package list>` | A-004, A-014, A-057 |
| First import approval | `G4 APPROVED: read-only company import` | A-012 |
| Live spike approval | `G5 APPROVED: <source> <stage> <cap>` | A-029 |
| Phase 6 approval | `G6 APPROVED: <feature>` | Phase 6 |

## 9. Next action

1. Owner reviews the A-003 report and cache-move evidence.
2. Owner sends `G3 APPROVED: <package list>` if dependency work should start.
3. Agent starts **A-004 only** and stops with the required report.

Do not start A-004 or any later task until G3 is approved.

## 10. Known risks

| Risk | Current state | Mitigation |
|---|---|---|
| Accidental live submission | Prototype reaches live mode and simulates apply | Freeze; A-005 refuses live; archive `apply.py` |
| Workbook corruption | Resolver writes any resolved workbook | Read-only importer; explicit path; hash checks |
| PII leak | Ignore rules now protect private files; logging/redaction still missing | A-002 done; A-005 pending |
| Wrong data source | Local starter still preferred by the prototype resolver | H-01 confirmed; explicit path implementation pending |
| False positives | Skill scoring ignores job text | A-033 and A-035 |
| Duplicate jobs | No 3-layer dedupe | A-037 |
| Scope creep | Telegram and auto-apply are attractive shortcuts | Written scope decisions; A-053 removed |
| Dependency breakage | Python 3.15 with old pins | A-004 |
| Missing backups | Historical backup claim contradicted | A-052 SQLite backup; no reliance on old backups |

## 11. Approval status

| Gate | Status | Date | Note |
|---|---|---|---|
| G1 planning | Pending | - | A-002/A-003 scope approved only; full plan approval not stated |
| A-002 execution | **Approved** | 2026-11-06 | Owner approved A-002 only |
| G2 cleanup | **Approved for Batch 1** | 2026-11-06 | Owner replied `okay proceed` after A-002 report |
| A-003 execution | **Complete** | 2026-11-06 | Cache hygiene only |
| G3 dependencies | Pending | - | - |
| G4 first import | Pending | - | - |
| G5 live spike | Not requested | - | - |
| G6 Phase 6 | Not requested | - | - |
| H-01 workbook | **Confirmed** | 2026-11-06 | `D:\code\plans\PLACEMENT\job\Master_Job_Tracker_final.xlsx` |
| Telegram removal | **Confirmed** | 2026-11-06 | Removed by owner decision |
| Dashboard Phase 5 | **Confirmed** | 2026-11-06 | Phase 5, local-only |

## 12. Session log

| Date | Task | Result | Files | Notes |
|---|---|---|---|---|
| 2026-11-06 | A-000 | Complete | 9 new planning docs | Read-only audit; no source/workbook/config changes; hashes recorded; no network; no installs |
| 2026-11-06 | A-002 | Complete | `.gitignore`, 3 example templates, 6 directories, `.git/` | Git initialized; 31 tracked; forbidden 0; content PII 0; sensitive hashes unchanged; no commit; no network; no installs |
| 2026-11-06 | A-003 | Complete | `archive/MOVE_LOG.md`, `archive/legacy_20261106/cache/` | 5 cache files archived; 0 permanent deletions; 0 `.pyc` outside archive; imports parsed; sensitive hashes unchanged; no commit; no network; no installs |

## 13. Report index

- Audit and claims: `CURRENT_PROJECT_AUDIT.md`
- Cleanup and file classes: `FILE_CLEANUP_MANIFEST.md`
- Architecture: `TARGET_ARCHITECTURE.md`
- Roadmap and gates: `MASTER_DEVELOPMENT_ROADMAP.md`
- Task board: `AGENT_TASK_BOARD.md`
- Owner actions: `HUMAN_TASK_CHECKLIST.md`
- Rules: `PROJECT_EXECUTION_RULES.md`

## 14. 2026-11-07 build verification (current)

| Check | Result | Evidence |
|---|---|---|
| Compile | `COMPILE_OK` | `evidence/C_compile.txt` |
| Tests | `97 passed in 3.32s` | `evidence/C_pytest_final.txt` |
| Offline fixture run | 5 fetched, 5 normalized, 2 rejected, 0 duplicates, 3 queued; `source_error:jsonld:http_403` | `evidence/C_fixture_run.txt` |
| Report | 3 companies, 2 sources, 3 jobs, 1 run, 3 queued | `evidence/C_report.txt` |
| Export | 6 sheets; SHA-256 `927b997bcca0280bd904ebd16ded749efd2d12fe3487d9c941d8eb916ec2b4f8` | `evidence/C_export.txt` |
| DB check | `data/job_agent.sqlite3`; 3 companies, 3 jobs, 3 queued | `evidence/C_db_check.txt` |
| Live refusal | `SAFETY LOCK: --live is not supported; dry-run only`; exit 2 | `evidence/C_live_refusal.txt` |
| Git history | `fatal: your current branch 'rebuild' does not have any commits yet` | `evidence/C_git_log.txt` |
| Protected hashes | workbook/config/profile/answers/resume match the approved baseline | `evidence/C_protected_hashes.txt` |
| `main.py` | safety lock and legacy `run()` disabled; SHA-256 `5FA4138BAFCEDB482377E1CF11946EB32D1A779B0193B6D79F9F87D624BC1301` | `evidence/C_protected_hashes_final.txt` |
| Scheduler launchers | explicit command required; no pause; logs; exit 2 without args | `evidence/C_scheduler_dbcheck.txt` |
| Preferences | draft only; not approved | `PREFERENCES_DRAFT.md` |
| Commits | none | `RUN_LOG.md` |

The build is paused at Stage F. Do not start PART 4 until the owner sends the exact line
`PREFERENCES APPROVED`. Do not commit or push without explicit owner approval.
