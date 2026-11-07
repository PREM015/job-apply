# Project execution rules

These rules apply to every session. They are stricter than convenience: if a task conflicts with them, stop and report the conflict.

## 1. Product boundary

The system discovers, filters, ranks, deduplicates, and tracks fresher and internship jobs. **Application submission is always human-assisted.** The system may prepare links, packets, and notes; it must not submit an application, contact a recruiter, create an account, or accept terms on the owner's behalf.

## 2. Absolute prohibitions

The agent must NOT:

- submit an application or click a final submit control on any form
- email, message, or otherwise contact recruiters or companies
- create accounts, accept terms, bypass CAPTCHA/login/2FA, or evade rate limits
- scrape LinkedIn, Indeed, Glassdoor, Naukri, or any other restricted portal; never request portal passwords
- invent candidate information, answers, job data, companies, URLs, or evidence; unknown stays `unknown`
- modify the resume PDF, the authoritative company workbook, `.env`, `profile.yaml`, or `answers.yaml`
- print, log, commit, or paste credentials, PII, company records, or contact rows
- set `dry_run: false` or enable a live submission path
- delete anything permanently; move it to `archive/legacy_<YYYYMMDD>/` only after approval
- install or update dependencies without approval
- make network calls unless the task explicitly names an approved live spike

## 3. Dry-run policy

- `dry_run` must remain `true` in every environment and in every task.
- A `--live` flag must exit non-zero with a clear message. It must not be possible to reach a submission code path by configuration.
- Dry-run means: no applications, no outbound contact to companies or recruiters, no portal scraping. It may write the local SQLite database, local exports, and local logs.
- The dashboard may update the database only. It must never submit, message, or fetch a job portal.
- Any future live spike is read-only discovery against approved public sources, with explicit approval and request caps.

## 4. Read-only assets

The following are read-only inputs unless a future task explicitly says otherwise and the owner approves:

- the authoritative company workbook (path to be confirmed by H-01)
- the resume PDF
- `profile.yaml` and `answers.yaml`
- `.env`
- `requirements.txt` pins during an audit task

The workbook must be opened read-only, hashed before and after, and never written by the dashboard or by any task that is not an explicitly approved import/export task.

## 5. Network policy

- No network calls in planning, audit, test-fixture, cleanup, or dashboard tasks.
- Approved live spikes must:
  - identify the agent with a truthful User-Agent
  - honor `robots.txt`
  - honor `Retry-After`
  - rate-limit per host (start at about 1 request/second)
  - respect a stated total request cap
  - stop on repeated 403/429 responses and record the source as failed/skipped
  - never bypass a block or use a proxy rotation service
- A failed fetch must never close, delete, or overwrite existing jobs.
- Check each source's terms of use before enabling it and summarize them for the owner.

## 6. Privacy and data handling

- Do not read `profile.yaml` or `answers.yaml` contents for planning. Use existence and hashes only.
- Do not read the resume PDF. Use existence and hash only.
- Do not print workbook cell values for company, contact, or application rows. Use aggregate counts and header names only.
- Redact sensitive paths in reports as `<resume-pdf>`, `<private-config>`, or `<authoritative-workbook>` when the filename itself would reveal personal data.
- Logs must use a redaction filter for emails, phone numbers, tokens, API-key-like strings, and absolute user paths.

## 7. Change and cleanup policy

- Every move must be logged in `archive/MOVE_LOG.md` with source, destination, reason, and SHA-256.
- Before moving code, re-run the import graph and paste the dependents. If a live module still depends on the file, do not move it.
- Batch 1 is cache hygiene only. Batch 2 is prototype retirement. Batch 3 is owner-named items only. See `FILE_CLEANUP_MANIFEST.md`.
- Never merge placeholder or `example.com` rows into real data.
- Never touch the master workbook, resume, profile/answers, or `.env` during cleanup.

## 8. Testing rules

- Write tests before changing classifiers, the scorer, or dedupe.
- Label every result `FIXTURE` or `LIVE`.
- A fixture pass does not prove a live source works.
- Match keywords on word boundaries, never raw substrings.
- Isolate adapter failures. A failed adapter returns a failed result and does not raise into the run.
- The dashboard test suite must include a mocked-network assertion that no outbound HTTP request is made by any page or action.

## 9. Approval gates

| Gate | Owner decision | Unblocks |
|---|---|---|
| **G1** | Approve this planning pack and the target architecture | Phase 1 tasks A-001, A-002, A-005 |
| **G2** | Approve cleanup batches and specific archive moves | A-003 and any move/archive action |
| **G3** | Approve named dependency installs only | A-004 and later test/runtime work |
| **G4** | Approve the first read-only import of the authoritative workbook | A-012 |
| **G5** | Approve a named live spike, source, stage, or mailbox | A-029, A-030 through A-034, scale stages |
| **G6** | Approve Phase 6 advanced features after the readiness review | Any Phase 6 implementation |

G1 is not permission to install packages, move files, read private data, or make network calls. Each gate is separate.

## 10. Scope changes approved by the owner

- **Telegram is removed from scope.** Mark related tasks, human checklist items, env vars, and code as `REMOVED by owner decision`. Do not add Telegram back without a new written decision.
- **The local dashboard replaces Telegram** as the primary interface. It is moved from Phase 6 into Phase 5 as A-057 through A-060.
- **Optional email or desktop notifications are deferred.** They are not approved for implementation.
- Dashboard rules:
  - bind to `127.0.0.1` only; refuse `0.0.0.0`
  - read SQLite through the repository layer only
  - never open or write the master workbook
  - buttons update the database only; no submission or external automation
  - never display secrets, `profile.yaml`, `answers.yaml`, or resume contents
  - no network calls to job portals
  - "Run discovery now" is not allowed without a separate approval

## 11. Required end-of-session report

Every session must end with:

1. Task IDs completed
2. Files created, changed, or moved
3. Commands run and actual output
4. Tests added and results (`FIXTURE` vs `LIVE`)
5. SHA-256 before/after of the workbook, resume, and config files (must be unchanged unless the task says otherwise)
6. Known gaps and anything `NOT EXECUTED`
7. Questions or approvals needed from the owner

Then stop and wait. Do not continue into the next prompt.
