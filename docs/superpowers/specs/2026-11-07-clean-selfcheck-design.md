# Clean, document, and selfcheck design

## Purpose and constraints

Deliver the requested final cleanup as a reproducible, offline-only workflow:
an owner can run one selfcheck command, fixture demonstration data is reset
without touching the LIVE database, and the repository's root and operating
documentation are clear. Never create `config/preferences.yaml`, contact a
network, start PART 4, or modify/move/stage protected owner files or the
Python installer.

The current checkout is on `rebuild` at `20feda9`. At design time the worktree
already contains a modified `config/preferences.draft.yaml` and three
untracked root files containing pager/Git output. They must be inspected and
handled only under the approved cleanup rules; do not silently discard or
overwrite them.

## Approaches considered

1. **Recommended: bounded, evidence-led cleanup.** Add the selfcheck and
   fixture reset behavior, update only the requested docs, and archive
   candidates only after the prescribed reference search is empty. Keep
   protected and Batch 3 items untouched.
2. **Documentation and selfcheck only.** Lowest cleanup risk, but leaves
   generated root artifacts and the fixture database reset requirement
   unresolved.
3. **Broad cleanup.** Archive all apparent legacy and planning material.
   Rejected because several older files may still be referenced and the
   owner explicitly reserves Batch 3 decisions.

## Components and behavior

- `tools/selfcheck.ps1` performs each requested check from live command
  results, prints `CHECK | RESULT | DETAIL`, and returns nonzero on FAIL.
  Checks cover venv Python 3.11-3.13, full pytest count, clean Git status,
  forbidden tracked paths, each of the five protected hashes, every archive
  log hash, unknown root names, the requested Telegram/notify patterns, LIVE
  schema version/company/job counts and fixture DB separation, disabled LIVE
  mode, preferences-file presence, and the preferences-gated run lock.
  Protected-hash checks print each filename and SAME/CHANGED. The unknown-root
  check is WARN, not FAIL. The preferences-file check is informational.
  Test, archive-hash, Python, database, safety, and tracked-file checks must
  not make network requests. Outputs are saved under
  `project-planning/evidence/FINAL_*.txt`.
- `run_selfcheck.bat` launches that PowerShell script from the repository
  root and propagates its exit code.
- The fixture reset path must be explicitly restricted to
  `data/fixture_job_agent.sqlite3`, retain a recoverable copy of the prior
  fixture DB, migrate/reset to schema version 6, and never open or write
  `data/job_agent.sqlite3`. `run_fixture_demo.bat` labels all sample data
  FIXTURE. Tests verify the current migration version, reset behavior, and
  LIVE DB isolation.
- `README.md`, `docs/FOLDER_GUIDE.md`, and `project-planning/OWNER_TODO.md`
  are updated to the requested sections, root-file allowlist, owner-only
  actions, and PART 4 gate. README begins with the exact WARNING text from the
  request, then covers product scope, setup, daily commands, manual
  application flow, owner approval steps, folder map, troubleshooting, and
  honest FIXTURE/LIVE status. The folder guide lists the allowed root entries.
  Apply the owner-supplied draft defaults only to
  `config/preferences.draft.yaml`: experience cap 2, Bihar, and hybrid. The
  approved preferences file remains absent.
- Cleanup first records the complete root inventory and classifies every
  item. A candidate is archived only when the exact reference scan across
  `job_agent/`, `tests/`, `config/`, `tools/`, and root `*.bat` finds no use.
  The four named planning specs, `RUN_LOG.md`, `PREFERENCES_DRAFT.md`, and
  `evidence/` remain. Other planning candidates use the same reference check.
  Batch 3 items, caches, `.venv`, `.git`, protected files, and uncertain
  items stay in place. Each actual move is preceded/followed by SHA-256
  verification and logged by appending to `archive/MOVE_LOG.md`.

## Evidence and validation

Before any move, save the inventory/reference-search output. After changes,
run the full FIXTURE test suite; if cleanup causes a failure, restore that
file from the archive and document it as KEEP. Compare every existing and new
MOVE_LOG entry with its current archived-file hash. Run selfcheck before each
commit and once after the final commit. The pre-commit clean-tree check is
expected to report the staged work; the required final selfcheck must report
a clean tree. Never stage via `git add .` or `git add -A`; stage only reviewed
paths. Do not push.

## Scope exclusions

No LIVE discovery, adapter verification, application submission, PART 4
execution, preference approval, network access, permanent deletion, or changes
to protected files. Batch 3 disposition remains with the owner.
