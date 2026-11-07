"""Forward-only SQLite migrations."""
from __future__ import annotations

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS companies (
            master_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            tier TEXT,
            careers_url TEXT,
            openings_url TEXT,
            ats_type TEXT,
            ats_identifier TEXT,
            resolution_status TEXT NOT NULL DEFAULT 'unresolved',
            last_resolved_at TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS sources (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_master_id INTEGER NOT NULL REFERENCES companies(master_id) ON DELETE CASCADE,
            source_type TEXT NOT NULL,
            url TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run_at TEXT,
            last_status TEXT,
            etag TEXT,
            last_modified TEXT,
            fail_count INTEGER NOT NULL DEFAULT 0,
            request_cap INTEGER NOT NULL DEFAULT 5,
            UNIQUE (company_master_id, url)
        );

        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER REFERENCES sources(source_id) ON DELETE SET NULL,
            company_master_id INTEGER REFERENCES companies(master_id) ON DELETE SET NULL,
            source_job_id TEXT,
            canonical_url TEXT NOT NULL,
            apply_url TEXT,
            title TEXT NOT NULL,
            company_name TEXT NOT NULL,
            location_raw TEXT,
            city TEXT,
            region TEXT,
            country TEXT,
            work_mode TEXT NOT NULL DEFAULT 'unknown',
            employment_type TEXT NOT NULL DEFAULT 'unknown',
            experience_level TEXT NOT NULL DEFAULT 'unknown',
            is_internship INTEGER NOT NULL DEFAULT 0,
            is_software INTEGER NOT NULL DEFAULT 0,
            software_evidence TEXT NOT NULL DEFAULT '[]',
            skills_required TEXT NOT NULL DEFAULT '[]',
            skills_preferred TEXT NOT NULL DEFAULT '[]',
            description_text TEXT NOT NULL DEFAULT '',
            posted_at TEXT,
            discovered_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            score_total INTEGER NOT NULL DEFAULT 0,
            score_breakdown TEXT NOT NULL DEFAULT '{}',
            dedupe_key TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (canonical_url),
            UNIQUE (dedupe_key),
            UNIQUE (fingerprint)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_identity
            ON jobs(source_id, source_job_id)
            WHERE source_job_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            applied_at TEXT,
            notes TEXT NOT NULL DEFAULT '',
            proof_path TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            mode TEXT NOT NULL DEFAULT 'dry',
            source_count INTEGER NOT NULL DEFAULT 0,
            fetched_count INTEGER NOT NULL DEFAULT 0,
            normalized_count INTEGER NOT NULL DEFAULT 0,
            rejected_count INTEGER NOT NULL DEFAULT 0,
            duplicate_count INTEGER NOT NULL DEFAULT 0,
            queued_count INTEGER NOT NULL DEFAULT 0,
            errors_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS queue (
            queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL REFERENCES daily_runs(run_id) ON DELETE CASCADE,
            job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
            rank INTEGER NOT NULL,
            score INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'queued',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (run_id, job_id)
        );

        CREATE TABLE IF NOT EXISTS queue_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER NOT NULL REFERENCES queue(queue_id) ON DELETE CASCADE,
            old_state TEXT,
            new_state TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT 'owner',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS suppressions (
            suppression_id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            value TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE (kind, value)
        );

        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS global_targets (
            target_id INTEGER PRIMARY KEY,
            company TEXT NOT NULL,
            tier TEXT,
            careers_url TEXT,
            status TEXT,
            matched_master_id INTEGER REFERENCES companies(master_id) ON DELETE SET NULL,
            source TEXT
        );
        """,
    ),
    (
        3,
        """
        ALTER TABLE companies ADD COLUMN origin TEXT NOT NULL DEFAULT 'master';
        ALTER TABLE companies ADD COLUMN region TEXT NOT NULL DEFAULT 'unknown';
        ALTER TABLE companies ADD COLUMN owner_group TEXT;
        ALTER TABLE companies ADD COLUMN needs_review INTEGER NOT NULL DEFAULT 0;

        CREATE TABLE IF NOT EXISTS company_career_candidates (
            candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_master_id INTEGER NOT NULL REFERENCES companies(master_id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            url_verified INTEGER NOT NULL DEFAULT 0,
            origin TEXT NOT NULL,
            UNIQUE (company_master_id, url, origin)
        );

        CREATE TABLE IF NOT EXISTS registry_platforms (
            platform_id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            url_verified INTEGER NOT NULL DEFAULT 0,
            handling_class TEXT NOT NULL,
            feed_url TEXT,
            terms_url TEXT,
            approved INTEGER NOT NULL DEFAULT 0,
            owner_has_account INTEGER NOT NULL DEFAULT 0,
            alerts_set INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS platform_tags (
            platform_id INTEGER NOT NULL REFERENCES registry_platforms(platform_id) ON DELETE CASCADE,
            section TEXT NOT NULL,
            owner_group TEXT,
            PRIMARY KEY (platform_id, section, owner_group)
        );

        CREATE TABLE IF NOT EXISTS saved_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE,
            keyword_group TEXT NOT NULL,
            keyword TEXT NOT NULL,
            portal_key TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            checked INTEGER NOT NULL DEFAULT 0
        );
        """,
    ),
    (
        4,
        """
        ALTER TABLE jobs ADD COLUMN origin TEXT NOT NULL DEFAULT 'discovery';
        """,
    ),
    (
        5,
        """
        CREATE INDEX IF NOT EXISTS idx_platform_tags_lookup
            ON platform_tags(platform_id, section);
        """,
    ),
    (
        # Version 5 may already be recorded by databases that ran its earlier
        # implementation, so version 6 repeats the non-destructive index step.
        6,
        """
        CREATE INDEX IF NOT EXISTS idx_platform_tags_lookup
            ON platform_tags(platform_id, section);
        """,
    ),
]
