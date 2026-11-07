# LIVE Job Discovery Design

## Status

The owner approved this design in chat. Implementation and any network access remain gated on review of this document and an implementation plan.

## Goal

Add an explicit, bounded LIVE discovery command that retrieves public job listings from Tier 1/2 company career pages or supported ATS feeds, runs the existing job-processing pipeline, and reports genuine results without submitting applications.

## Non-goals

- No application submission, login, account creation, CAPTCHA handling, email, or other write action.
- No source discovery from LinkedIn, Naukri, Indeed, Glassdoor, or owner portal-registry entries.
- No changes to fixture command behavior or the permanent LIVE-apply refusal.
- No preference-value, weight, threshold, or quota changes; no score-floor relaxation or result padding.
- No staging or committing either owner preference file.

## Safety invariants

1. `discover-live` is a separate CLI command. It proceeds only when `load_preferences` accepts the requested preferences file and `--network-ok` is present.
2. The company cap defaults to 25 and cannot exceed 25. The request cap defaults to 300 and cannot exceed 300. Invalid caps fail before any request.
3. Network access is GET-only. Every actual request, including robots checks, a retry, a redirect hop, and apply-URL verification, consumes the same global budget.
4. Fixture jobs are confined to `data/fixture_job_agent.sqlite3`. LIVE discovery reads companies and writes jobs only in the configured real database.
5. Before any LIVE database mutation, create a database backup without pruning existing backups.
6. Jobs written by this command carry `origin='LIVE'`. No LIVE request or result is presented as FIXTURE, and fixture data is never copied into the real database.
7. All discovered jobs pass through the existing normalization, validation, classification, hard gates, scoring, dedupe, and quota behavior. A job that fails a gate or score floor is not queued.
8. No application is submitted. The final apply-URL check is a counted GET only.

## Components and flow

### CLI

Add `discover-live` with `--preferences`, `--network-ok`, `--max-companies` (default 25), `--max-requests` (default 300), and `--dry-report`. Preference validation and cap validation happen before constructing a network client. Missing or invalid preferences and a missing network flag produce explicit safety refusals.

`--dry-report` may perform the requested bounded GET discovery and produce a report, but it does not back up or mutate the job database. Normal execution backs up the real database before writing.

### Company selection and source resolution

Read only Tier 1/2 company rows from the real database. Sort known supported ATS sources ahead of other companies, then use the stored openings/careers URL and the existing resolver. If a company page must be scanned, fetch that page and inspect links only one hop deep. A bounded slug probe is permitted only when the company name sufficiently fuzzy-matches a known ATS identifier; otherwise do not guess a URL.

A page-discovered link may point to a supported ATS host and be fetched as a new, policy-checked URL. Redirects are stricter: follow only redirects to the same host, which is a safe subset of same-registrable-domain redirects and avoids an inaccurate public-suffix guess. Unsupported, ambiguous, or portal URLs are skipped and reported.

### HTTP policy

The shared `HttpClient` enforces HTTPS/HTTP-only URLs, GET-only requests, explicit timeout, an honest project User-Agent, at most one retry, one-second minimum spacing per host, and a single hard request counter. Requests disable automatic redirects; each allowed redirect is validated and fetched as a separate counted GET. Do not send or retain cookies, credentials, or login state.

Fetch and cache each host's `robots.txt` before accessing a path. A robots 404 means no published rules; other robots failures fail closed. Disallowed paths are recorded and skipped. After a host returns a second 403 or 429 response, skip that host for the remainder of the run. The ledger records host, URL path (not query values), status, and request number for every actual request.

### Parsing and pipeline

Use the adapter selected by the resolver only when the response matches that adapter's expected payload. Inspect the first parsed job for field-level consistency against the source response; print field names only, not a full response or job dump. Report each adapter as `VERIFIED-ON-1-SAMPLE` with company name only when the check passes; otherwise report `UNVERIFIED` and the reason.

Pass batches through the existing pipeline. Add only the minimal batch metadata wiring required to preserve `origin='LIVE'`; do not change normalization, gate, score, dedupe, or quota rules. Report counts for attempted companies, resolution method, fetched jobs, rejection reasons, duplicates, and queue. Check apply URLs for queued top results with counted GETs and report status codes.

### Evidence

Write the path-only request ledger to `project-planning/evidence/LIVE_request_ledger.txt`. Save the run summary and raw command output under evidence without storing credentials or response cookies. The chat summary lists at most five actual jobs, the request count, host/robots skips, funnel, adapter status, validation results, recent commits, and any failed or unexecuted work.

## Testing

All automated network-policy tests use `responses`; tests make no real network calls. Cover:

- Both CLI refusals (missing `--network-ok`; invalid/missing preferences) without any HTTP request.
- Hard caps, global accounting, host pacing, one retry, GET-only behavior, URL scheme checks, timeout, cookie isolation, redirect rejection, robots allow/deny/failure behavior, and repeated 403/429 host skipping.
- Company-tier selection and exclusion of owner portal URLs; bounded resolver behavior and slug-probe conditions.
- Adapter parsing and field verification using representative FIXTURE responses.
- LIVE-origin propagation, fixture/real database separation, dry-report no-write behavior, backup-before-write ordering, and counted apply-URL checks.
- Existing fixture and apply-refusal tests remain unchanged in behavior.

## Acceptance criteria

1. The command refuses before network access unless preferences validate and `--network-ok` is supplied.
2. No run can exceed 25 companies or 300 actual GET requests, including robots, retries, redirects, and apply checks.
3. The only job sources are Tier 1/2 company careers/ATS URLs resolved under the constraints above.
4. LIVE records are labeled `LIVE`; fixture data never enters the real database.
5. Existing pipeline gates, score floor, dedupe, and quota are preserved.
6. The request ledger, per-adapter verification results, funnel, and actual top results are reproducible from the run evidence.
7. Automated tests run offline and pass; LIVE APPLY remains impossible.

## Known limitations

The current resolver defaults unknown careers URLs to JSON-LD, and the repository's adapters do not establish that every stored careers URL is a supported feed endpoint. Discovery must therefore report unresolved/unsupported sources rather than claim coverage or invent API endpoints. Adapters are verified only for a real response sample encountered during the authorized run; all others remain unverified.
