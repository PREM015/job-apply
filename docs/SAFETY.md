# Safety model

The system is dry-run only. There is no code path that submits an application, sends
email, creates an account, solves a CAPTCHA, or bypasses a login.

## Enforced at startup

- `job_agent.config.load_config` rejects `dry_run` values other than literal `true`.
- `job_agent.config.load_config` rejects a dashboard host other than `127.0.0.1`.
- `job_agent.cli.main` rejects `--live` with exit code 2.
- `main.py` rejects `--live` with exit code 2, refuses `JobAgent(dry_run=False)`, and
  disables the legacy `run()` flow so it cannot open a workbook or network connection.
- `job_agent.dashboard.app.assert_local_host` rejects non-loopback binding.

## Enforced in the pipeline

- Only public ATS JSON, public JSON-LD, and public sitemap parsing exist.
- 401/403 responses are terminal `blocked` results and are never retried.
- 429 responses honour `Retry-After` once and stop.
- Per-host request caps and a global request cap are enforced by `HttpClient`.
- Soft skills, salary, and other unverifiable claims never add score; only keyword
  evidence from the posting text does.
- Applied URLs/fingerprints and suppressed companies are excluded from the queue.

## Human-only actions

- Reviewing the daily queue.
- Marking a job `interested`, `applied`, `skipped`, or `archived`.
- Logging an application in `applications`.
- Approving preferences and any future live mode.

## Never allowed

- `dry_run: false`
- `--live`
- Automatic form filling or submission
- Playwright/browser automation
- Recruiter email or LinkedIn/Naukri scraping
- Writing the authoritative master workbook
