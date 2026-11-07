# Owner TODO

The build is paused at Stage F. Do not start PART 4 until the owner acts.

## 1. Approve or edit preferences

Read `project-planning/PREFERENCES_DRAFT.md` and `config/preferences.example.yaml`.
Reply with the exact line below only when the draft is acceptable:

```text
PREFERENCES APPROVED
```

If changes are needed, list them and the draft will be regenerated.

## 2. Approve Stage F -> PART 4

Part 4 includes live-source proof and the five-job end-to-end proof. It is blocked until
preferences are approved and the owner explicitly allows a live run.

## 3. Real company import (G4)

`import-companies` is implemented and read-only by default. Do not run it against the
authoritative master until the owner approves the output and understands that:

- the workbook is hashed before and after;
- nothing is written to the workbook;
- the master path is `D:\code\plans\PLACEMENT\job\Master_Job_Tracker_final.xlsx`.

## 4. Live discovery spike (A-029)

Live HTTP is implemented but not exercised. The owner must approve a specific allowlist
of public sources and a request cap before any real request is made.

## 5. Blocked items

`project-planning/BLOCKED.md` lists A-029, A-030..A-033, A-034, real A-048 labelling,
Batch 3 cleanup, and PART 4. The task board and BLOCKED file disagree about A-030..A-034;
the build treats them as pure fixture classifiers, which is the conservative choice.

## 6. Repository state

There are no commits. The branch is `rebuild`. Staging and commits require explicit
owner approval; no `git add .` or `git add -A` was used.
