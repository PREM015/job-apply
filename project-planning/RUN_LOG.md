# Project run log

This file is append-only. Commit hashes are recorded only when `git log` prints them.
Unverified claims are not recorded here.

## 2026-11-07 - compile check

Command:

```powershell
.\.venv\Scripts\python.exe -m compileall -q job_agent
```

Output:

```text
COMPILE_OK
```

Evidence: `project-planning/evidence/C_compile.txt`

## 2026-11-07 - test suite

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Output:

```text
........................................................................ [ 75%]
........................                                                 [100%]
96 passed in 3.32s
```

Evidence: `project-planning/evidence/C_pytest.txt`

## 2026-11-07 - offline fixture run

Command:

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml run --fixtures tests/fixtures/e2e_fixture.json --preferences config/preferences.example.yaml
```

Output:

```json
{
  "run_id": 1,
  "counters": {
    "source_count": 3,
    "fetched_count": 5,
    "normalized_count": 5,
    "rejected_count": 2,
    "duplicate_count": 0,
    "queued_count": 3
  },
  "errors": [
    "source_error:jsonld:http_403"
  ],
  "rejections": [
    {"title": "Accountant", "reason": "non_software"},
    {"title": "Senior Software Engineer", "reason": "excluded_title"}
  ],
  "queue": [
    {"rank": 1, "score": 81, "title": "Frontend Engineer", "company_name": "Beta"},
    {"rank": 2, "score": 80, "title": "Software Engineer", "company_name": "Acme"},
    {"rank": 3, "score": 79, "title": "Backend Developer", "company_name": "Beta"}
  ]
}
```

Evidence: `project-planning/evidence/C_fixture_run.txt`

## 2026-11-07 - report

Command:

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml report
```

Output:

```json
{
  "run": {"run_id": 1, "mode": "dry", "source_count": 3, "fetched_count": 5, "normalized_count": 5, "rejected_count": 2, "duplicate_count": 0, "queued_count": 3, "errors_json": "[\"source_error:jsonld:http_403\"]"},
  "counts": {"companies": 3, "sources": 2, "jobs": 3, "applications": 0, "daily_runs": 1, "queue": 3, "suppressions": 0},
  "queue": [
    {"rank": 1, "score": 81, "company": "Beta", "title": "Frontend Engineer"},
    {"rank": 2, "score": 80, "company": "Acme", "title": "Software Engineer"},
    {"rank": 3, "score": 79, "company": "Beta", "title": "Backend Developer"}
  ],
  "errors": ["source_error:jsonld:http_403"]
}
```

Evidence: `project-planning/evidence/C_report.txt`

## 2026-11-07 - export

Command:

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml export --out data/exports/fixture_queue.xlsx
```

Output:

```json
{
  "path": "D:\\code\\plans\\PLACEMENT\\job\\job-agent\\data\\exports\\fixture_queue.xlsx",
  "sha256": "927b997bcca0280bd904ebd16ded749efd2d12fe3487d9c941d8eb916ec2b4f8",
  "sheets": ["Daily Queue", "All Jobs", "Applications", "Companies", "Runs", "Rejected"]
}
```

Evidence: `project-planning/evidence/C_export.txt`

## 2026-11-07 - database check

Command:

```powershell
.\.venv\Scripts\python.exe -m job_agent --config config/config.yaml db-check
```

Output:

```json
{
  "database": "data\\job_agent.sqlite3",
  "applied_migrations": [],
  "counts": {"companies": 3, "sources": 2, "jobs": 3, "applications": 0, "daily_runs": 1, "queue": 3, "suppressions": 0}
}
```

Evidence: `project-planning/evidence/C_db_check.txt`

## 2026-11-07 - live refusal

Command:

```powershell
.\.venv\Scripts\python.exe -m job_agent --live --config config/config.yaml db-check
```

Output:

```text
SAFETY LOCK: --live is not supported; dry-run only
EXIT=2
```

Evidence: `project-planning/evidence/C_live_refusal.txt`

## 2026-11-07 - repository state

Command:

```powershell
git log --oneline -n 5
```

Output:

```text
fatal: your current branch 'rebuild' does not have any commits yet
```

Evidence: `project-planning/evidence/C_git_log.txt`

No commits exist. No commit hash is recorded here because `git log` printed none.

## 2026-11-07 - protected file hashes

Command:

```powershell
Get-FileHash -LiteralPath .gitignore,main.py,.env.example,requirements.txt,requirements-dev.txt,Master_Job_Tracker_final.xlsx,Prem_resume_01.pdf,config.yaml,profile.yaml,answers.yaml -Algorithm SHA256
```

Output:

```text
.gitignore                         62A0EC577EC1148F972FD5DA88087C81FBCD7B4B0D856FD63743ABE5E08ADFD9
main.py                            1713AFE9790C8BD6305CD4D8E68AA3548BC76B24FCC71887581CC9B9FABF5759
.env.example                       99C97D298D3950E2F357F258514C675E70757075F5EC0D44C6A50C606023A87F
requirements.txt                   659D80D1D32BDC498F670A4BA69E8F1A05D6759D99E8FDD68B8FBFC5200906D1
requirements-dev.txt               C9B16A4888C1A7FCA9C3AE8C6CBBA7BF8518CFC3F9113CF84BA8AFF8B419EE30
Master_Job_Tracker_final.xlsx      D638434124DDD30812E32B90AEC4EA43D14A04EA3854DD21E8A01F0E3F023D47
Prem_resume_01.pdf                 7F386B19A03F60A29E40896D1DA89F8220FB88653EFEDA3842D7B1F0A092EAC6
config.yaml                        FAAC29462943D3B12ACF05493165B2ECA5DD7279F837AB8D8C3B113308564BC9
profile.yaml                       CCD7F0C5208C9277CC9345F0356A6DD5ECA3BD3F9BF883BBCC1D2CEA5609E9B6
answers.yaml                       0652D75A03DEE41FCA345DD60C6AE2ED4D91B17FB35833CDEA7FB62AC8F93F6A
```

Evidence: `project-planning/evidence/C_protected_hashes.txt`

## 2026-11-07 - archive move-log repair

Command:

```powershell
Get-ChildItem -LiteralPath archive\legacy_20261106 -File | ForEach-Object { '{0} {1}' -f $_.Name, (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
Get-ChildItem -LiteralPath archive\legacy_20261106\cache\__pycache__ -File | ForEach-Object { 'cache/__pycache__/{0} {1}' -f $_.Name, (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
```

Output:

```text
apply.py CE6101C0A0DAFFAADE91BF9BD4CDEA5594EC64DBC6DC1025E3524AEC170E6A84
clear_tracker.py BD6CDFA748E9D0957FAA58205A20E86B8B31E08BF100643D5F5112FA5CF39BAA
create_tracker.py 367BCCF520A4B23A404EC47288CCCCDADB05288744AD41005D3D113032EE3FC6
notify.py A7DE9034139F2135A88225700B53453012ED6AC4DEC152DE695BC6ED86AEE346
require.md E403360CA84E7EB229BAC956D759DFEA0571E093F4AD9E30D0812E2452EA15C9
cache/__pycache__/apply.cpython-315.pyc 2CCE7DFC25FE907C85F24E6E3D9872E03A9C94B342BF7F457FD5F0FBBE3D41CE
cache/__pycache__/discover.cpython-315.pyc 1339F7C4877DE75405619ED759195BFDA63BADB5B1D2BC5CFA2F3981DFB60D25
cache/__pycache__/excel_io.cpython-315.pyc C507AD4156673347C1892598A6703D08FE6A8CE087FFB15C682F772E53B0F48B
cache/__pycache__/match.cpython-315.pyc 21BC9AC2F93658FF9B9AC7A0FBCAD346AF9CB02BD7DE6F124F36C04D578FB6BA
cache/__pycache__/notify.cpython-315.pyc 477CDDA7533C918FFD124A97DE606F900DA2E70B2141E2CD39A9F65022462588
```

All archive destinations exist. `notify.py` was present, so no restore was needed.
`archive/MOVE_LOG.md` was repaired append-only with these real hashes.

Evidence: `project-planning/evidence/C_archive_hashes.txt`

## 2026-11-07 - final safety guard and verification

`main.py` `JobAgent.run()` was disabled so the legacy flow cannot open a workbook or
make a network request. A regression test was added.

Commands:

```powershell
.\.venv\Scripts\python.exe -m compileall -q job_agent main.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py --live
Get-FileHash -LiteralPath main.py,Master_Job_Tracker_final.xlsx,config.yaml,profile.yaml,answers.yaml,Prem_resume_01.pdf -Algorithm SHA256
```

Output:

```text
COMPILE_OK
97 passed in 3.32s
SAFETY LOCK: live mode is not available; dry-run only
EXIT=2
main.py 5FA4138BAFCEDB482377E1CF11946EB32D1A779B0193B6D79F9F87D624BC1301
Master_Job_Tracker_final.xlsx D638434124DDD30812E32B90AEC4EA43D14A04EA3854DD21E8A01F0E3F023D47
config.yaml FAAC29462943D3B12ACF05493165B2ECA5DD7279F837AB8D8C3B113308564BC9
profile.yaml CCD7F0C5208C9277CC9345F0356A6DD5ECA3BD3F9BF883BBCC1D2CEA5609E9B6
answers.yaml 0652D75A03DEE41FCA345DD60C6AE2ED4D91B17FB35833CDEA7FB62AC8F93F6A
Prem_resume_01.pdf 7F386B19A03F60A29E40896D1DA89F8220FB88653EFEDA3842D7B1F0A092EAC6
```

Evidence: `project-planning/evidence/C_compile_final.txt`,
`project-planning/evidence/C_pytest_final.txt`,
`project-planning/evidence/C_legacy_live_refusal.txt`,
`project-planning/evidence/C_protected_hashes_final.txt`

This supersedes the earlier 96-test and `main.py` `1713AFE9...` entries. Protected
workbook/config/profile/answers/resume hashes are unchanged.

## 2026-11-07 - scheduler-safe launchers

Commands:

```powershell
cmd /c "run_job_agent.bat"
cmd /c "run_job_agent.bat db-check"
cmd /c "run_job_agent.bat --live"
```

Output:

```text
Usage: run_job_agent.bat <command> [args]
BATCH_EXIT=2

BATCH_EXIT=0
{
  "database": "data\\job_agent.sqlite3",
  "applied_migrations": [],
  "counts": {"companies": 3, "sources": 2, "jobs": 3, "applications": 0, "daily_runs": 1, "queue": 3, "suppressions": 0}
}
[07-11-2026 11:13:47.26] exit=0

usage: job_agent [-h] [--config CONFIG] [--db DB] [--live]
                 {run,report,import-companies,export,db-check} ...
job_agent: error: the following arguments are required: command
[07-11-2026 11:13:55.24] exit=2
BATCH_EXIT=2
```

The launcher logs to `logs/scheduler.log`, never pauses, returns non-zero on failure,
and requires an explicit command. `README.md`, `docs/OPERATIONS.md`, and
`docs/SAFETY.md` now describe the safe dry-run-only behavior.

Evidence: `project-planning/evidence/C_scheduler_noargs.txt`,
`project-planning/evidence/C_scheduler_dbcheck.txt`,
`project-planning/evidence/C_scheduler_live_refusal.txt`
