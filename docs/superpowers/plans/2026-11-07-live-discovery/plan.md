# Implementation Plan: Bounded LIVE Job Discovery

**Date**: 2026-11-07 | **Spec**: `docs/superpowers/specs/2026-11-07-live-discovery-design.md`

## Summary

Add a separate `python -m job_agent discover-live` workflow for owner-approved public GET discovery. It validates preferences and caps before network access, selects only Tier 1/2 company sources, enforces robots/rate/retry/redirect/request-budget policy, feeds genuine responses through the existing pipeline, and records LIVE jobs without changing fixture behavior or enabling application submission.

## Technical Context

**Language/Version**: Python; the project doctor expects Python 3.11-3.13.
**Primary Dependencies**: Existing `requests`, `PyYAML`, `beautifulsoup4`, and `responses` test dependency. No dependency installation is planned.
**Storage**: Existing SQLite real database and isolated `data/fixture_job_agent.sqlite3`; LIVE writes use the configured real database only.
**Testing**: `pytest`, `responses` for offline HTTP policy tests, and existing CLI/fixture/apply-refusal regression tests.
**Target Platform**: Windows local CLI, using `.\.venv\Scripts\python.exe`.
**Performance Goals**: At most 25 companies in the initial pass, at most one additional batch of 25, and 300 actual HTTP requests total across both passes; at least one second between requests to a host.
**Constraints**: Public GET only; robots and source terms respected; no login, cookies, application submission, portal sourcing, fixture-to-real writes, or preference changes. Never lower the configured `thresholds.manual_apply_min`.

## Constitution Check

No separate `constitution.md` exists. Per owner direction, `project-planning/PROJECT_EXECUTION_RULES.md` is the governing constitution for this plan. The owner-approved feature-specific authorization permits the bounded public GET stage; it does not authorize submission or broader live mode.

| Principle | Result | Plan alignment |
|---|---|---|
| Human-only application submission | PASS | The command and apply-link checks issue GET requests only; existing apply refusal remains untouched. |
| No restricted portal scraping, login, CAPTCHA, or recruiter contact | PASS | Only Tier 1/2 company career/ATS sources are candidates; portal registry rows are excluded. |
| `dry_run` remains true and live requests require explicit approval/caps | PASS | Dedicated command requires valid preferences and `--network-ok`, with hard caps validated before requests. |
| Live source requests honor terms, robots, rate limits, retries, and 403/429 stops | PASS | Terms are reviewed before source use; robots, host pacing, bounded retry, skip rules, and a global ledger are tested. |
| Privacy and fixture/live separation | PASS | No protected candidate data is read or changed; fixture DB path is refused for LIVE writes; outputs avoid cookies and response dumps. |
| Existing pipeline behavior is preserved | PASS | Fixture path keeps its current default behavior; LIVE passes the configured manual score floor without changing weights, gates, or quotas. |

## Applied Guidelines

No repository `skills/guidelines/` directory or matching framework-migration pattern was found. Existing project execution rules and the current adapter/pipeline contracts govern implementation.

## Implementation Steps

### Phase 1: Foundational safety

#### Step 1.1: Count and constrain every HTTP request
- **Requirements**: REQ-002
- **Design inputs**: Approved LIVE discovery design; `job_agent/http_client.py`
- **Description**: Refactor `HttpClient` so each real GET attempt is counted before sending, including retry and redirect hops. Enforce HTTP(S)-only URLs, timeout, at most one retry, truthful User-Agent, cookie isolation, host pacing, and the shared hard cap. Disable automatic redirects and validate each hop before a separately counted GET.

#### Step 1.2: Enforce robots and per-host refusal policy
- **Requirements**: REQ-002, REQ-003
- **Design inputs**: Approved LIVE discovery design; `project-planning/PROJECT_EXECUTION_RULES.md`
- **Description**: Add robots retrieval/cache and path authorization to the HTTP flow. Treat robots 404 as no published policy and other failures as fail-closed. Count robots requests, record disallowed paths, allow only same-host redirects, honor `Retry-After`, and stop a host after its second 403/429 response. Emit a path-only request ledger.

#### Step 1.3: Add separate CLI gates and hard limits
- **Requirements**: REQ-001
- **Design inputs**: Approved LIVE discovery design; `job_agent/cli.py`, `job_agent/config.py`
- **Description**: Add a separate `discover-live` command with `--preferences`, `--network-ok`, `--max-companies` (default 25), `--max-requests` (default 300), and `--dry-report`. Validate preference schema, the configured `manual_apply_min` range, and numeric caps before opening a network client. Refuse missing approval, invalid preferences/caps, and attempts to use the fixture DB for LIVE writes. Print parsed preference key names, including `experience.ceiling_years` and `locations`, and report that `work_modes` has no preference-schema support and is not filtered. Preserve `run` and all submit/apply refusal behavior.

### Phase 2: Source selection and parsing

#### Step 2.1: Select eligible company sources
- **Requirements**: REQ-004
- **Design inputs**: Approved LIVE discovery design; `job_agent/db/repository.py`, `job_agent/companies/resolver.py`, project execution rules
- **Description**: Query only real-database Tier 1/2 companies; prioritize supported ATS URLs; exclude owner portal-registry URLs and unsupported sources. Review each candidate source's terms before use, count any terms-page GET in the request budget, and skip/report sources whose terms prohibit access or cannot be verified.

#### Step 2.2: Bound careers-page resolution
- **Requirements**: REQ-004
- **Design inputs**: Approved LIVE discovery design; `job_agent/companies/resolver.py`, `job_agent/sources/registry.py`
- **Description**: Keep `job_agent/companies/resolver.py` pure. Use the existing stored openings/careers URLs and resolver patterns; implement network page scanning in `job_agent/live_discovery.py`. Inspect links one hop deep and consider supported ATS links only. Probe a slug only when company-name fuzzy matching justifies it. Never guess arbitrary endpoints or follow portal links.

#### Step 2.3: Verify adapters against actual response samples
- **Requirements**: REQ-005
- **Design inputs**: Approved LIVE discovery design; `job_agent/sources/*.py`, `job_agent/models.py`
- **Description**: Parse only responses supported by the selected adapter. Add an adapter-specific first-job consistency check against raw response fields. Print field names only; report `VERIFIED-ON-1-SAMPLE` with company name only when comparison succeeds, otherwise `UNVERIFIED` with a concise reason.

### Phase 3: Persistence and existing pipeline

#### Step 3.1: Back up safely and label LIVE records
- **Requirements**: REQ-006
- **Design inputs**: Approved LIVE discovery design; `job_agent/db/backup.py`, `job_agent/db/repository.py`, `job_agent/pipeline/run.py`
- **Description**: Extend backup behavior with an opt-out from pruning, thread that option through `Database.connect()`, and use it for LIVE execution so existing backups are never removed. Add optional batch-origin propagation through `run_pipeline`; LIVE batches set `origin='LIVE'`, while fixture defaults remain unchanged.

#### Step 3.2: Run the pipeline with the configured floor
- **Requirements**: REQ-006, REQ-007
- **Design inputs**: Approved LIVE discovery design; `job_agent/pipeline/run.py`, `job_agent/pipeline/score.py`, `job_agent/config.py`
- **Description**: Back up before any real DB mutation, upsert LIVE sources/jobs, and reuse normalization, validation, classification, hard filters, scoring, dedupe, and quota. The current pipeline does not apply the configured score threshold; add an optional LIVE-only score floor sourced from `preferences.thresholds.manual_apply_min`, reject below-floor jobs before persistence/queueing, and keep the default fixture pipeline behavior unchanged. For `--dry-report`, run the same pipeline against a disposable copy so the configured DB is not mutated.

#### Step 3.3: Verify apply links with counted GETs only
- **Requirements**: REQ-008
- **Design inputs**: Approved LIVE discovery design; `job_agent/http_client.py`, `job_agent/pipeline/run.py`
- **Description**: After queue selection, check only the top five apply URLs through the same safe client and request budget. Report status or a clear not-checked reason if robots, host refusal, or budget prevents the check. Never invoke submission code.

### Phase 4: Offline verification and authorized run

#### Step 4.1: Add FIXTURE regression coverage
- **Requirements**: REQ-009
- **Design inputs**: Approved LIVE discovery design; `tests/unit/test_http_client.py`, `tests/unit/test_cli_safety.py`
- **Description**: Use `responses` for no-network tests covering both CLI refusals, caps, GET-only behavior, actual request accounting, retry and pacing, robots, redirects, cookie isolation, host skips, terms/source selection, adapter verification, origin labels, fixture/live separation, dry-report, backup ordering, score floor, apply checks, and one widening pass under one shared cap. Retain all existing fixture and apply-refusal assertions.

#### Step 4.2: Document the command and save evidence
- **Requirements**: REQ-010
- **Design inputs**: Approved LIVE discovery design; `README.md`
- **Description**: Document the separate command, safety gates, caps, fixture/live distinction, and no-submit behavior. Write `project-planning/evidence/LIVE_request_ledger.txt` and a run summary containing funnel, terms/robots/host skips, adapter status, actual jobs, and apply-URL status codes without cookies or full response dumps.

#### Step 4.3: Validate and execute the owner-authorized run
- **Requirements**: REQ-010, REQ-011
- **Design inputs**: Approved LIVE discovery design; generated FIXTURE test results
- **Description**: Run `.\.venv\Scripts\python.exe -m pytest -q` and `.\run_selfcheck.bat` before network access. Then execute one initial pass with `--network-ok --max-companies 25 --max-requests 300`. If fewer than five jobs survive and budget remains, allow exactly one more batch of up to 25 not-yet-attempted companies, sharing the same counter and cap. Stop at 300, never lower the score floor, and report fewer results honestly.

## Project Structure

```text
job_agent/
  cli.py                         # discover-live CLI gates and dispatch
  http_client.py                 # counted GET, pacing, robots, redirect policy
  live_discovery.py              # selection, crawl, verification, report
  companies/resolver.py          # pure URL/source resolution
  db/backup.py                   # preserve backups for LIVE invocation
  db/repository.py               # configure connection backup pruning
  pipeline/run.py                # LIVE origin and optional score floor
tests/unit/
  test_http_client.py            # offline HTTP policy tests
  test_cli_safety.py             # command refusal/regression tests
  test_live_discovery.py         # source, pipeline, ledger, widening tests
README.md                        # command and safety documentation
project-planning/evidence/
  LIVE_request_ledger.txt        # path-only actual request ledger
  LIVE_discovery_summary.txt     # run funnel and verification evidence
```

## Testing Strategy

- **appType**: Local Python CLI with SQLite persistence.
- **Critical user journeys**:
  1. Missing `--network-ok` or invalid preferences exits before the first HTTP request.
  2. Robots-disallowed, cross-host redirect, unsupported scheme, and repeated 403/429 cases are refused and recorded.
  3. Eligible company responses parse and pass the existing classification, hard filters, configured manual score floor, dedupe, and quota.
  4. LIVE records stay in the real DB with `origin='LIVE'`; fixture runs remain on the fixture DB.
  5. Top apply URLs are checked by GET only and consume the same request cap.
- **primaryValidationStack**: `.venv` Python, `pytest`, `responses`, existing project selfcheck.
- **fallbackMatrix**:
  - `infra-tier`: SQLite temporary databases and fixtures; no containers required.
  - `browser-tier`: Not applicable; CLI-only change.
- **Environment requirements**: Existing venv and project dependencies; live execution requires owner preferences and explicit `--network-ok`. Tests do not require network.
- **knownGaps**: An endpoint/adapter with no supported response contract remains UNVERIFIED; inaccessible terms or robots policy causes a source skip; fewer than five eligible jobs is an honest valid outcome.
- **Test data strategy**: Temporary SQLite DBs and response fixtures; never use fixture rows in the configured real DB.
- **Acceptance criteria**: All safety and pipeline tests pass offline; exact caps are asserted by request count; one optional widening pass shares the initial cap; no submit path is reachable.
- **Validation review expectations**: Confirm no network was used by tests, no request exceeded policy, LIVE/fixture labels are accurate, all queued jobs meet the configured score floor, and the real run produced only evidence-backed results.

## Complexity Tracking

No constitution violations are planned. The additional optional score-floor parameter preserves current fixture behavior while enforcing the already-configured minimum for LIVE jobs.

## Requirement Mapping

| REQ ID | Description | Plan Items | Implementation Evidence |
|--------|-------------|------------|------------------------|
| REQ-001 | Separate command, preferences/flag gates, caps, dry-report | 1.3 | `job_agent/cli.py`, `job_agent/live_discovery.py`, `tests/unit/test_cli_safety.py` |
| REQ-002 | Bounded GET-only client and global actual-request counter | 1.1, 1.2 | `job_agent/http_client.py`, `tests/unit/test_http_client.py` |
| REQ-003 | Robots, redirects, host blocking, path-only ledger | 1.2 | `job_agent/http_client.py`, `job_agent/live_discovery.py`, `tests/unit/test_http_client.py` |
| REQ-004 | Tier 1/2 source selection and bounded resolution | 2.1, 2.2 | `job_agent/live_discovery.py`, `job_agent/companies/resolver.py`, `tests/unit/test_live_discovery.py` |
| REQ-005 | Honest per-adapter sample verification | 2.3 | `job_agent/live_discovery.py`, `job_agent/sources/*.py`, `tests/unit/test_live_discovery.py` |
| REQ-006 | Backup, LIVE origin, fixture isolation, dry-report | 3.1, 3.2 | `job_agent/db/backup.py`, `job_agent/pipeline/run.py`, `job_agent/live_discovery.py` |
| REQ-007 | Existing gates, scorer, dedupe, quota, score floor | 3.2 | `job_agent/pipeline/run.py`, `tests/unit/test_live_discovery.py` |
| REQ-008 | Counted apply-link GETs and no submission | 3.3 | `job_agent/live_discovery.py`, `job_agent/http_client.py`, `tests/unit/test_cli_safety.py` |
| REQ-009 | Offline FIXTURE regression coverage | 4.1 | `tests/unit/test_http_client.py`, `tests/unit/test_cli_safety.py`, `tests/unit/test_live_discovery.py` |
| REQ-010 | Evidence, funnel, adapter and result reporting | 4.2, 4.3 | `project-planning/evidence/LIVE_request_ledger.txt`, `project-planning/evidence/LIVE_discovery_summary.txt` |
| REQ-011 | At most one extra batch under the original request cap | 4.1, 4.3 | `job_agent/live_discovery.py`, `tests/unit/test_live_discovery.py` |

## Task Breakdown

### Phase 1: Foundational safety

- [ ] T001 [Plan:1.1] Add `responses` FIXTURE tests in `tests/unit/test_http_client.py` for per-attempt request accounting, timeout, one retry, User-Agent, cookie isolation, GET-only behavior, and host pacing.
- [ ] T002 [Plan:1.1] Implement counted HTTP(S) GET attempts, explicit timeout, maximum one retry, cookie clearing, host pacing, hard cap enforcement, and disabled automatic redirects in `job_agent/http_client.py`.
- [ ] T003 [Plan:1.2] Add offline tests in `tests/unit/test_http_client.py` for robots allow/deny/404/failure, counted robots requests, same-host redirect handling, path-only ledger entries, and second-403/429 host skipping.
- [ ] T004 [Plan:1.2] Implement robots caching/enforcement, `Retry-After` handling, per-host refusal state, redirect validation, and request-ledger recording in `job_agent/http_client.py`.
- [ ] T005 [Plan:1.3] Add CLI tests in `tests/unit/test_cli_safety.py` proving invalid/missing preferences, missing `--network-ok`, invalid caps, and fixture DB write attempts fail before any HTTP request; assert output identifies parsed keys and reports unsupported work-mode preference filtering.
- [ ] T006 [Plan:1.3] Add `discover-live` parser options, score-floor validation, parsed-key/work-mode diagnostic, and early preference/cap/path gates in `job_agent/cli.py`, without changing `run`, `--live`, or apply-refusal behavior.

### Phase 2: Source selection and parsing

- [ ] T007 [Plan:2.1] Add FIXTURE cases in `tests/unit/test_live_discovery.py` for Tier 1/2-only selection, ATS-first ordering, portal exclusion, and terms-result handling.
- [ ] T008 [Plan:2.1] Implement real-DB candidate selection and terms eligibility in `job_agent/live_discovery.py`; count terms-page requests and skip/report prohibited or unverifiable source terms.
- [ ] T009 [Plan:2.2] Implement stored-URL resolution, one-hop same-page link scanning, supported ATS URL selection, and fuzzy-name-gated slug probes in `job_agent/live_discovery.py`, keeping `job_agent/companies/resolver.py` free of network I/O.
- [ ] T010 [Plan:2.3] Implement first-job adapter/response consistency checks and per-adapter verification reporting in `job_agent/live_discovery.py`; test supported payloads in `tests/unit/test_live_discovery.py`.

### Phase 3: Persistence and existing pipeline

- [ ] T011 [Plan:3.1] Add tests proving LIVE backup creation does not prune existing backups and batch `origin` is retained without changing fixture defaults in `tests/unit/test_live_discovery.py`.
- [ ] T012 [Plan:3.1] Add non-pruning backup support in `job_agent/db/backup.py` and `job_agent/db/repository.py`, plus optional batch-origin propagation in `job_agent/pipeline/run.py`.
- [ ] T013 [Plan:3.2] Implement source/job batching, backup-before-write ordering, disposable-database `--dry-report`, LIVE origin, and configured `manual_apply_min` enforcement in `job_agent/live_discovery.py` and `job_agent/pipeline/run.py`.
- [ ] T014 [Plan:3.3] Implement top-five apply-URL GET checks through the shared client, including status/not-checked reasons, in `job_agent/live_discovery.py`.

### Phase 4: Offline verification and authorized run

- [ ] T015 [Plan:4.1,4.3] Add FIXTURE integration tests for real/fixture DB separation, dry-report no-write behavior, score-floor preservation, apply checks, and one widening batch sharing the original request budget in `tests/unit/test_live_discovery.py`.
- [ ] T016 [Plan:4.2] Document `discover-live` gates and limits in `README.md`; write the path-only request ledger and sanitized funnel/job/adapter summary under `project-planning/evidence/`.
- [ ] T017 [Plan:4.3] Run `.\.venv\Scripts\python.exe -m pytest -q`, commit only explicit LIVE-discovery code/test/docs paths (never preference files), then run `.\run_selfcheck.bat`; only if required checks pass, execute the owner-authorized first LIVE pass and at most one widening batch, saving actual outputs to evidence.
