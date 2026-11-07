# Canonical schema

The runtime source of truth is SQLite. Excel is an import/export format, never the
master store. The authoritative workbook stays read-only and is never written by code.

## Tables

| Table | Purpose | Key columns |
|---|---|---|
| `companies` | normalized company directory | `master_id` (PK), `name`, `tier`, `careers_url`, `openings_url`, `ats_type`, `resolution_status` |
| `sources` | one fetch target per company | `source_id` (PK), `company_master_id` (FK), `source_type`, `url`, `enabled`, `fail_count` |
| `jobs` | normalized postings | `job_id` (PK), `source_id`, `company_master_id`, `canonical_url`, `dedupe_key`, `fingerprint` |
| `applications` | human-owned application log | `application_id` (PK), `job_id`, `status`, `applied_at`, `notes` |
| `daily_runs` | run ledger | `run_id` (PK), counts, `errors_json` |
| `queue` | ranked daily queue | `queue_id` (PK), `run_id`, `job_id`, `rank`, `score`, `state` |
| `queue_events` | append-only queue audit | `event_id`, `queue_id`, `old_state`, `new_state`, `actor` |
| `suppressions` | company/URL exclusions | `kind`, `value`, `reason` |
| `schema_migrations` | applied migration versions | `version` (PK), `applied_at` |

## Invariants

- `jobs.canonical_url`, `jobs.dedupe_key`, and `jobs.fingerprint` are unique.
- `(sources.company_master_id, sources.url)` is unique.
- `(queue.run_id, queue.job_id)` is unique.
- `applications.status` is owner-managed; automatic submission is not supported.
- Deletes are blocked by `ON DELETE CASCADE` only for derived child rows; source data is
  archived, never silently removed.
- Queue transitions always append a `queue_events` row.

## Job lifecycle

`discovered -> active -> queued -> reviewed -> interested/applied/skipped -> archived`

The pipeline only writes `discovered`, `active`, and `queued`. Human actions move the
remaining states through the dashboard or tracking API.

## Import/export rules

- Company import reads the workbook with `read_only=True`, hashes before and after,
  and refuses if the hash changed.
- Export always writes a new file inside `exports_dir`, refuses to overwrite unless
  `force=True`, and refuses any filename matching the master workbook.
- Exports contain `Daily Queue`, `All Jobs`, `Applications`, `Companies`, `Runs`, and
  `Rejected` sheets.
