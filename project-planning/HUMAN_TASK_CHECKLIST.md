# Human task checklist

These are the owner actions that unblock the agent. The agent must not perform them on the owner's behalf.

Use this checklist with `PROJECT_EXECUTION_RULES.md` and `AGENT_TASK_BOARD.md`.

## 1. How to respond

Use a short, explicit phrase. Do not paste secrets, profile contents, answers, resume text, or company/contact rows.

| Decision | Required phrase |
|---|---|
| Approve the planning pack and target design | `G1 APPROVED` |
| Confirm the authoritative workbook | `H-01 CONFIRMED: <path>` |
| Confirm Telegram removal | `TELEGRAM REMOVED: confirmed` |
| Confirm dashboard move to Phase 5 | `DASHBOARD PHASE 5: confirmed` |
| Approve cleanup batch | `G2 APPROVED: <batch and item list>` |
| Approve named dependencies | `G3 APPROVED: <package list>` |
| Approve first read-only import | `G4 APPROVED: read-only company import` |
| Approve a live spike | `G5 APPROVED: <source> <stage> <request cap>` |
| Approve Phase 6 | `G6 APPROVED: <feature>` |

A general "looks good" is not a gate approval. If a decision is unclear, the agent must ask again.

## 2. Owner tasks H-01 through H-17

| ID | Task | Why it matters | What the owner does | Blocks | Done when |
|---|---|---|---|---|---|
| **H-01** | Confirm the authoritative workbook | The resolver currently picks the 2-row starter; two workbooks share a name | Confirm the exact path of the 693-company parent workbook, or name a different file. Confirm it is the source of truth and stays read-only. | A-010, A-012, Phase 1 | `H-01 CONFIRMED: <path>` |
| **H-02** | Approve the planning pack and target architecture | The agent must not build on an unapproved design | Read `README.md`, `TARGET_ARCHITECTURE.md`, `MASTER_DEVELOPMENT_ROADMAP.md`, and `PROJECT_EXECUTION_RULES.md`. Approve or request edits. | A-002 and all later work | `G1 APPROVED` or a written edit list |
| **H-03** | Confirm scope decisions | Prevent Telegram or auto-apply from returning | Confirm Telegram is removed, the dashboard is Phase 5, and optional notifications are deferred. | A-002, A-053, A-057 | `TELEGRAM REMOVED: confirmed` and `DASHBOARD PHASE 5: confirmed` |
| **H-04** | Review scoring, quotas, and filters | The weights in the pack are proposals, not approved values | Review the proposed weights, tier caps, daily quota, experience ceiling (default 2 years), locations, and work modes. Approve or edit. | A-036, A-039, A-042 | Written weights and caps, or `G1 APPROVED` with the defaults |
| **H-05** | Confirm private config exists and is current | The pipeline must not guess or read private contents in planning | Confirm `profile.yaml` and `answers.yaml` exist and are current. Do not paste contents. | A-006, Phase 3 | Written confirmation only |
| **H-06** | Confirm resume policy | The resume is private and must never be uploaded by the system | Confirm the resume path and that it stays outside Git. Confirm the system will not upload or submit it. | A-002, A-054 | Written confirmation |
| **H-07** | Approve cleanup batches | Moves and archives need explicit approval | Review `FILE_CLEANUP_MANIFEST.md`. Approve Batch 1 and/or Batch 2 by name. Batch 3 requires naming each item. | A-003, A-013 | `G2 APPROVED: <batch/items>` |
| **H-08** | Approve dependencies and Python version | Python 3.15 is installed; several packages are missing or mismatched | Approve the target Python version and the exact package list after the agent proposes it. | A-004, A-014, A-057 | `G3 APPROVED: <package list>` |
| **H-09** | Approve the first read-only company import | The workbook is an input; the import must not write it | Approve the import after reviewing the header validation and data-quality report. | A-012 | `G4 APPROVED: read-only company import` |
| **H-10** | Approve a live spike | Fixture tests do not prove a live source works | Approve one source, one stage, and a request cap. Review the terms summary and results. | A-029 and any live work | `G5 APPROVED: <source> <stage> <cap>` |
| **H-11** | Confirm ATS/source overrides | Some companies need a manual source mapping | Name any known ATS board, tenant, or careers URL that the resolver should prefer. Do not paste credentials. | A-025, Phase 2 | Written override list or "no overrides" |
| **H-12** | Confirm locations, work modes, and eligibility | The scorer must not guess country eligibility | Confirm target cities/countries, remote/hybrid/onsite preferences, and the experience ceiling. | A-034, A-036 | Written preferences |
| **H-13** | Review sample rankings | A score is only useful if the owner agrees with the ordering | Review a small fixture queue with score breakdowns. Mark roles as relevant or not. | A-042, Phase 3 exit | Written calibration notes |
| **H-14** | Confirm application statuses and proof policy | The application log is human-owned | Confirm the status set (`interested`, `applied`, `skipped`, `rejected`, `archived`) and whether proof paths are optional. | A-043, A-044 | Written status policy |
| **H-15** | Approve the local dashboard | The dashboard must not become a remote or automation surface | Confirm local-only `127.0.0.1`, DB-only writes, no workbook access, no network calls, and no apply/discovery buttons. Approve dashboard dependencies separately. | A-057 - A-060 | `DASHBOARD PHASE 5: confirmed` and `G3 APPROVED: <dashboard packages>` |
| **H-16** | Review the runbook and scheduled dry run | The system must run without prompts and without live actions | Review the operator runbook, launchers, logs, and one offline scheduled run. | A-054, A-056, Phase 4 exit | Written approval or corrections |
| **H-17** | Final readiness review and Phase 6 decision | Advanced features must not reintroduce unsafe behavior | Review the readiness evidence. Decide whether to stop or approve named Phase 6 features. | Phase 6 | `G6 APPROVED: <feature>` or "stop at Phase 5" |

## 3. Shared rules S-01 through S-10

| ID | Rule | Applies to |
|---|---|---|
| **S-01** | One task per session. End with the required report and stop. | Owner and agent |
| **S-02** | `dry_run` is always true. No application submission, recruiter contact, account creation, CAPTCHA/login bypass, or restricted-portal scraping. | Agent |
| **S-03** | Never modify the authoritative workbook, resume, `profile.yaml`, `answers.yaml`, or `.env`. | Agent |
| **S-04** | No PII, company records, contact rows, resume text, or secrets in docs, logs, tests, or reports. Use counts and redacted labels. | Owner and agent |
| **S-05** | Match keywords on word boundaries. Unknown stays unknown. Non-software roles are rejected before scoring. | Agent |
| **S-06** | No Telegram. No LinkedIn/Indeed/Glassdoor/Naukri scraping. No stealth, proxy rotation, or rate-limit evasion. | Owner and agent |
| **S-07** | Offline fixture tests first. Label every live result `LIVE` and every fixture result `FIXTURE`. | Agent |
| **S-08** | Record SHA-256 before and after any task touching the workbook, resume, or config. The hash must match unless the task explicitly changes that file. | Agent |
| **S-09** | Move files to `archive/legacy_<date>/` with a move log. No permanent deletion without a separate explicit approval. | Owner and agent |
| **S-10** | No package install, update, or network call without the named gate. Report anything not executed. | Owner and agent |

## 4. First approval packet

To unblock Phase 1, the owner only needs to send:

```text
G1 APPROVED
H-01 CONFIRMED: <authoritative workbook path>
TELEGRAM REMOVED: confirmed
DASHBOARD PHASE 5: confirmed
```

Optional at the same time:

```text
G2 APPROVED: Batch 1 cache hygiene
G3 APPROVED: <dependency list>
```

Do not approve Batch 2, the first import, a live spike, or Phase 6 until the agent presents the evidence for that gate.

## 5. What the owner should not do

- Do not paste `.env` values, API keys, profile answers, or resume text into chat.
- Do not ask the agent to "just run it live" without a named G5 approval and caps.
- Do not approve a package install by naming a package the agent has not listed with a version.
- Do not approve a cleanup batch by saying "clean up everything".
- Do not ask for auto-apply, auto-message, or Telegram.
- Do not share the authoritative workbook path in a public issue or commit.

## 6. Current pending decisions

| Decision | Status | Blocks |
|---|---|---|
| A-002 execution | **Approved and complete** | No longer blocking |
| G1 planning approval | Pending for later phases; A-002 scope only was approved | A-005, A-006, and later implementation |
| H-01 authoritative workbook | **Confirmed** | No longer blocking |
| Telegram removal confirmation | **Confirmed** | No longer blocking |
| Dashboard Phase 5 confirmation | **Confirmed** | No longer blocking |
| G2 Batch 1 cleanup | **Approved and complete** | Batch 2 needs new approval |
| G3 dependency list | Pending | A-004, A-014 |
| G4 first import | Pending | A-012 |
| G5 live spike | Not requested yet | A-029 |
| G6 Phase 6 | Not requested yet | Phase 6 |
