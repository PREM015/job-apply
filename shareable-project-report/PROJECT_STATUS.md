# Job Application Automation Agent — Status Summary

**Audit date:** 2026-11-06
**Scope:** Current `job-agent` source, configuration, workbook structure, dependencies, and bounded read-only checks.
**Privacy:** Sanitized. No identities, credentials, local paths, resume data, or company/contact records.

---

## Executive summary

The project is an **early-stage local Python prototype** for daily job discovery and application preparation. It has a working Excel I/O layer, a generic career-page scraper, a scoring module, and notification helpers.

It is **not a working end-to-end job agent**:

- Discovery cannot record real jobs because three referenced helper functions do not exist.
- The decision stage raises a `NameError` for any job that reaches it.
- Skill matching scores the configured skill list instead of the job text, so a non-software job scored 85/100.
- Application submission is simulated; the real Playwright scaffold is never imported and never submits.
- ATS integrations, Apollo/contact discovery, resume routing, approval workflow, and persistent state are absent.

**Overall status:** pre-alpha, not production-ready.

---

## Status scorecard

| Area | Status | Comment |
|---|---|---|
| Excel integration | **Implemented** | Backup, load, save, sheet creation, append, daily log |
| Notifications | **Implemented** | Telegram/SMTP; not config-gated |
| Watch-list building | **Partial** | Reads Excel; rich workbook shadowed by local stub |
| Career-page crawling | **Partial** | Generic static HTML only; relative links lost |
| ATS detection | **Partial** | Sniffing only in unwired `apply.py` |
| Discovery-to-decision pipeline | **Broken** | Missing helpers; undefined symbol in decision |
| Skill matching / scoring | **Incorrect** | Config-list scoring; inflated scores |
| Excel deduplication | **Partial** | Read logic exists; key/recency helpers missing |
| Application preparation | **Partial** | Name/email/phone only; no resume upload |
| Application submission | **Not implemented** | Simulated success and fake proof files |
| ATS integrations (Greenhouse, Lever, Ashby, Workable, SmartRecruiters) | **Not implemented** | Strings only; no API clients |
| Workday / other ATS | **Not implemented** | No support |
| Apollo organization / jobs / people | **Not implemented** | Environment key exists but is unused |
| Email / phone enrichment | **Not implemented** | Contact columns exist; no population code |
| Queue / crash recovery | **Not implemented** | `pending_updates.json` referenced but never written |
| Tests | **Not implemented** | No tests; `pytest` missing |
| Logging / redaction | **Not implemented** | `logs/` empty; print-only errors |
| Privacy hardening | **Weak** | PII/workbook files not fully ignored by Git |

---

## What is implemented

1. **Excel I/O (`excel_io.py`)**
   - Backup before write and retention cleanup.
   - Safe load/save wrappers.
   - Creation of `Job Openings` and `Daily Run Log`.
   - Watch-list read from `Companies`.
   - Append/update helpers and applied-URL collection.

2. **Notifications (`notify.py`)**
   - Telegram digest and manual-action alert.
   - SMTP email support.
   - Environment-driven configuration.

3. **Pipeline scaffolding (`main.py`)**
   - Lock file, config/profile/answer loading, stage structure, stats.
   - Dry-run/live flag handling.
   - Excel logging of each run.

4. **Generic HTTP discovery (`discover.py`)**
   - Requests with timeout, retries, and robots checking.
   - Absolute-link extraction from static HTML.
   - Company-name presence check.

5. **Utility scripts**
   - Workbook creation/reset helpers (dev-only; destructive and hard-coded).

---

## What is partially implemented

1. **Career-page crawling** — static HTML only; no JavaScript rendering, pagination, or ATS feeds. Relative links are resolved against a placeholder domain and then discarded.
2. **Fresher/experience filtering** — regex-based; module exists but the decision path crashes.
3. **Skill matching and scoring** — present, but scores the configuration, not the posting; calibration is invalid.
4. **Deduplication** — comparison logic exists, but the job-key and recency helpers are missing.
5. **Application preparation** — fills name/email/phone only; no resume, select fields, EEO, or custom questions.
6. **ATS detection** — string sniffing in an unwired module.
7. **Locking** — a lock file is created, but stale locks and Excel locks are not handled.
8. **CLI modes** — `--discover-only` and `--report` are accepted but ignored.
9. **Scheduling scripts** — always dry-run; Windows script waits for input.

---

## Current blockers (P0/P1)

| Blocker | Evidence | Impact |
|---|---|---|
| Missing `compute_job_key`, `is_duplicate_job`, `is_posted_recent` | `main.py` calls them; `discover.py` does not define them; verified at runtime | Every candidate raises `AttributeError`; no jobs recorded |
| Undefined symbol in `match.decide_action()` | `match._experience_filter` is not defined; verified `NameError` | No decision can be returned |
| Scoring ignores job text | A non-software job scored 85/100 in a bounded test | Auto-apply threshold is meaningless |
| Simulated application in `main.py` | Writes a text file with `.png` extension and marks rows applied | Fabricates applications and proof; unsafe in live mode |
| `apply.py` never submits | `fill_and_submit()` always returns `False`; not imported by `main.py` | No real application capability |
| Global targets mapped from wrong columns | Code uses 1/3/4; sheet schema uses 14/8/10 | Invalid careers URLs; target discovery fails |
| Tracker resolution | Local minimal workbook preferred; hard-coded fallback path | Wrong workbook, portability and privacy risk |
| No ATS adapters | Only string allowlists/detection | Discovery coverage is accidental and shallow |
| No tests or logging | No test files; `logs/` empty | No regression safety or diagnosis |
| PII not fully ignored | `.gitignore` omits profile, answers, resume, tracker | Risk of leaking personal/confidential data |

---

## Top 10 next tasks

1. **Implement the three missing discovery helpers** and add unit tests for job keys, URL normalization, deduplication, and missing dates.
2. **Fix `decide_action()`** to call the local eligibility function; remove dead code and return structured decisions.
3. **Rewrite skill matching** to inspect job title/description; calibrate scores with fixtures, including negative and senior roles.
4. **Remove the simulated applier** and hard-disable live mode until a real, approval-gated submission path exists.
5. **Fix Global Product Targets mapping** (correct columns and hyperlink targets) and skip blank rows.
6. **Make the tracker path explicit** and portable; remove the hard-coded fallback and eliminate the local-stub shadowing.
7. **Harden privacy**: ignore profile/answers/resume/workbook files, add redaction, and audit logs/proofs for secrets.
8. **Update dependencies and runtime**: use a supported Python version, prune unused packages, add `pytest`, and verify installs.
9. **Build reliable discovery**: add ATS resolution and public feed adapters with schema validation, recency filters, caching, and rate limits.
10. **Add a real test suite and CI** covering parsers, scoring, deduplication, Excel writes, and offline ATS fixtures.

Deferred until the pipeline is stable: Apollo/contact enrichment, resume routing, real form submission, approval UX, and production scheduling.

---

## Verification snapshot

| Check | Result |
|---|---|
| Module syntax | 9/9 parse; four `SyntaxWarning`s in two path-based utility scripts |
| Core dependencies | 6 present |
| Optional dependencies | `playwright`, `Pillow`, `schedule`, `python-dateutil`, `rich`, `pytest` missing |
| Project workbook | 5 sheets; 2 sample company rows; empty `Job Openings`; 3 dry-run log rows |
| Historical backup | 2 placeholder `example.com` jobs — not real postings |
| Rich workbook in parent directory | 19 sheets; 693 companies; 526 career URLs; 4 ATS-like URLs; 50 global targets |
| Discovery helpers | All three absent |
| Relative URL extraction | 0 jobs returned |
| Absolute URL extraction | 1 job returned |
| Decision function | `NameError` |
| Scoring calibration | Non-software job scored 85/100 |
| Full pipeline | **NOT EXECUTED** (read-only audit; would modify files) |
| Live ATS/application tests | **NOT EXECUTED** (no adapters; module unwired) |

**Real-world success claims:** none. No real job posting or application submission was verified.

---

## Privacy scan status

The two report files were written with:

- No personal names, email addresses, phone numbers, or postal addresses.
- No resume contents or employment history.
- No personal GitHub/LinkedIn/portfolio URLs.
- No local usernames or absolute directory paths.
- No API keys, tokens, passwords, cookies, or `.env` values.
- No database credentials or private endpoints.
- No individual company or recruiter records; aggregate counts only.
- No fabricated test results presented as real success.

A post-write scan for email/phone/secret/path patterns is part of the final validation step. Public ATS provider domain names and the reserved `example.com` placeholder are the only URL-like strings retained, and they are not personal or confidential.

---

## Bottom line

The strongest asset is the Excel workflow. The weakest is the discovery-to-submission chain. The correct next milestone is **one small, tested, real discovery path** for a handful of companies that produces valid postings and calibrated scores — before any work on contacts, resumes, or automated submission.
