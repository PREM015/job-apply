# ATS patterns (read-only research notes)

Source of truth: `archive/legacy_20261106/apply.py` (archived, never executed) and the
public ATS URL patterns used by the offline adapters. No submission path exists in the
new codebase. These notes are for parsing public job boards only.

## Supported URL families

| ATS | Public board pattern | New adapter | Live status |
|---|---|---|---|
| Greenhouse | `boards.greenhouse.io/<board>` / `job-boards.greenhouse.io/<board>` | `sources/greenhouse.py` | fixture-tested, live blocked |
| Lever | `jobs.lever.co/<board>` | `sources/lever.py` | fixture-tested, live blocked |
| Ashby | `jobs.ashbyhq.com/<board>` | `sources/ashby.py` | fixture-tested, live blocked |
| SmartRecruiters | `jobs.smartrecruiters.com/<board>` / `careers.smartrecruiters.com/<board>` | `sources/smartrecruiters.py` | fixture-tested, live blocked |
| Workable | `<tenant>.workable.com` | `sources/workable.py` | fixture-tested, live blocked |
| Keka | `<tenant>.keka.com/careers/` | `sources/keka_zoho.py` | fixture-tested, disabled |
| Zoho Recruit | `<tenant>.zohorecruit.com/jobs/Careers` | `sources/keka_zoho.py` | fixture-tested, disabled |
| JSON-LD | any public careers page with `application/ld+json` `JobPosting` | `sources/jsonld.py` | fixture-tested, live blocked |
| Sitemap | public `sitemap.xml` with job-like URLs | `sources/sitemap.py` | fixture-tested, live blocked |

## Legacy selectors (archived, not used)

The archived browser automation looked for apply buttons with selectors such as
`button:has-text("Apply")`, `a:has-text("Apply")`, `button:has-text("Apply for this job")`,
and `[data-qa="apply-button"]`. It also guessed fields from `input[name*="first"]`,
`input[type="email"]`, and `input[type="tel"]`.

These selectors are retained only as a warning about how brittle and unsafe automated
submission is. The new system does not load Playwright, does not open a browser, does not
fill forms, and does not submit anything.

## Classification rules

- `Company` career links are resolved to an ATS family by hostname pattern.
- A job URL is canonicalized (tracking parameters removed, fragment removed, host lowercased).
- JSON-LD is preferred when no ATS pattern matches.
- Sitemap URLs must contain `job`, `career`, `position`, `opening`, or `vacanc`.
- Keka and Zoho remain disabled in `config/sources.yaml` until a human approves research.

## Hard limits

- No login, CAPTCHA solving, account creation, recruiter email, or portal scraping.
- No live HTTP run until the owner explicitly approves it.
- HTTP client requests are bounded by timeout, retry count, per-host delay, and request cap.
- Any 401/403 is recorded as `blocked` and never retried.
- Any 429 honours `Retry-After` and then stops.
