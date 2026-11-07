# job-agent planning pack

This directory contains the planning, audit, cleanup, architecture, roadmap, task, and approval documents for the `job-agent` repository.

They were created during **A-000 (read-only inventory)** on **2026-11-06**. They are not approved until the owner gives **G1** approval. Until then, treat the current prototype as frozen.

## Reading order

1. `PROJECT_STATUS.md` - current maturity, blockers, and the next task.
2. `CURRENT_PROJECT_AUDIT.md` - what exists, what is broken, and the claim-by-claim verification table.
3. `FILE_CLEANUP_MANIFEST.md` - every file classified, dependents, risks, and archive batches.
4. `TARGET_ARCHITECTURE.md` - the intended pipeline, module contracts, schema, scoring, and dedupe design.
5. `MASTER_DEVELOPMENT_ROADMAP.md` - phases 0-6, dependencies, acceptance, and exit gates.
6. `AGENT_TASK_BOARD.md` - task IDs A-000 through A-060, status, dependencies, acceptance, evidence.
7. `HUMAN_TASK_CHECKLIST.md` - owner tasks H-01 through H-17 and shared rules S-01 through S-10.
8. `PROJECT_EXECUTION_RULES.md` - safety restrictions, dry-run policy, network policy, and gates G1-G6.

## How to use these documents

- Do **one task per session**. Stop after the required report and wait for approval.
- Update only the relevant row(s) in `AGENT_TASK_BOARD.md` and the owner-facing items in `HUMAN_TASK_CHECKLIST.md`.
- Record evidence next to every completed task: commands, exit status, test result, and file references. Do not record company records, contact details, personal data, or secrets.
- The audit uses counts only. It deliberately does not reproduce company names, contact rows, resume text, or profile/answers contents.
- No planning document is permission to modify the master workbook, the resume, `profile.yaml`, `answers.yaml`, or `.env`.
- When a document conflicts with source code or the workbook, the source code/workbook wins. Re-verify before acting.

## Scope decisions already made by the owner

- **Telegram notifications are removed by owner decision.** They are marked `REMOVED` in this planning pack. Do not add Telegram back without a new written decision.
- **The primary interface is a local dashboard**, moved from Phase 6 to Phase 5 as tasks **A-057 through A-060**.
- **Application submission remains human-only.** The dashboard and CLI may update the local database only.
- **Optional email or desktop notifications are deferred.** They are not part of the current scope.

## Status and priority legends

Claim status:

- `VERIFIED` - reproduced from source, filesystem, or workbook evidence.
- `CONTRADICTED` - the prior statement is not true in the current repository state.
- `UNVERIFIED` - not testable without approval, network, live data, or contents that must not be read.
- `PARTIAL` - some parts hold and some do not; the detail is stated.

Task status:

- `DONE` - completed with evidence in this session.
- `TODO` - approved for later work but not started.
- `BLOCKED` - waiting for an owner decision, approval, or prior task.
- `REMOVED` - removed from scope by owner decision.

Priority:

- `P0` - safety, data-loss, or correctness blocker.
- `P1` - required for a trustworthy pipeline.
- `P2` - quality, performance, or maintainability.
- `P3` - polish or documentation.

## Privacy rule

These documents must never contain:

- personal names, email addresses, phone numbers, or postal addresses
- resume contents or the resume filename
- API keys, tokens, passwords, cookies, or `.env` values
- individual company records, recruiter records, or contact rows
- workbook cell contents other than headers and aggregate counts

If a future update needs to reference a sensitive file, use a redacted label such as `<resume-pdf>` or `<private-config>` and record only its hash and existence.
