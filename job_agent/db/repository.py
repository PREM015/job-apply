"""SQLite repository. All SQL lives here (and in migrations.py)."""
from __future__ import annotations

import json
import sqlite3
from itertools import count
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .backup import backup_database
from .migrations import MIGRATIONS

_SAVEPOINTS = count()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Database:
    def __init__(self, path: str | Path = "data/job_agent.sqlite3", backup_keep: int = 14):
        self.path = Path(path)
        self.backup_keep = backup_keep
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists() and self.path.stat().st_size > 0
        if existed and self.connection is None:
            backup_database(self.path, self.path.parent / "backups", keep=self.backup_keep)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        return self.connection

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        assert self.connection is not None, "connect() first"
        nested = self.connection.in_transaction
        savepoint = f"job_agent_sp_{next(_SAVEPOINTS)}"
        try:
            if nested:
                self.connection.execute(f"SAVEPOINT {savepoint}")
            else:
                self.connection.execute("BEGIN")
            yield self.connection
            if nested:
                self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            else:
                self.connection.commit()
        except Exception:
            if nested:
                self.connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            else:
                self.connection.rollback()
            raise

    def migrate(self) -> list[int]:
        assert self.connection is not None, "connect() first"
        applied: list[int] = []
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        existing = {row[0] for row in self.connection.execute("SELECT version FROM schema_migrations")}
        for version, sql in MIGRATIONS:
            if version in existing:
                continue
            with self.transaction() as conn:
                conn.executescript(sql)
                conn.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (version, now_iso()))
            applied.append(version)
        return applied

    # ------------------------------------------------------------------ companies
    def upsert_company(self, company: dict[str, Any]) -> int:
        assert self.connection is not None
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO companies(master_id, name, tier, careers_url, openings_url, ats_type,
                    ats_identifier, resolution_status, last_resolved_at, notes, origin, region,
                    owner_group, needs_review)
                VALUES (:master_id, :name, :tier, :careers_url, :openings_url, :ats_type,
                    :ats_identifier, :resolution_status, :last_resolved_at, :notes, :origin,
                    :region, :owner_group, :needs_review)
                ON CONFLICT(master_id) DO UPDATE SET
                    name=excluded.name, tier=excluded.tier, careers_url=excluded.careers_url,
                    openings_url=excluded.openings_url, ats_type=excluded.ats_type,
                    ats_identifier=excluded.ats_identifier, resolution_status=excluded.resolution_status,
                    last_resolved_at=excluded.last_resolved_at, notes=excluded.notes,
                    origin=excluded.origin, region=excluded.region, owner_group=excluded.owner_group,
                    needs_review=excluded.needs_review
                """,
                {
                    "master_id": company["master_id"],
                    "name": company["name"],
                    "tier": company.get("tier"),
                    "careers_url": company.get("careers_url"),
                    "openings_url": company.get("openings_url"),
                    "ats_type": company.get("ats_type"),
                    "ats_identifier": company.get("ats_identifier"),
                    "resolution_status": company.get("resolution_status", "unresolved"),
                    "last_resolved_at": company.get("last_resolved_at"),
                    "notes": company.get("notes"),
                    "origin": company.get("origin", "master"),
                    "region": company.get("region", "unknown"),
                    "owner_group": company.get("owner_group"),
                    "needs_review": int(company.get("needs_review", False)),
                },
            )
        return int(company["master_id"])

    def add_company_career_candidate(self, company_master_id: int, url: str,
                                     origin: str = "owner_list") -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO company_career_candidates(
                    company_master_id, url, url_verified, origin
                ) VALUES (?, ?, 0, ?)
                """,
                (company_master_id, url, origin),
            )

    def get_company(self, master_id: int) -> dict[str, Any] | None:
        assert self.connection is not None
        row = self.connection.execute("SELECT * FROM companies WHERE master_id=?", (master_id,)).fetchone()
        return dict(row) if row else None

    def list_companies(self) -> list[dict[str, Any]]:
        assert self.connection is not None
        return [dict(r) for r in self.connection.execute("SELECT * FROM companies ORDER BY master_id")]

    def count_companies(self) -> int:
        assert self.connection is not None
        return int(self.connection.execute("SELECT COUNT(*) FROM companies").fetchone()[0])

    # ------------------------------------------------------------- global targets
    def upsert_global_target(self, target: dict[str, Any]) -> int:
        assert self.connection is not None
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO global_targets(target_id, company, tier, careers_url, status,
                    matched_master_id, source)
                VALUES (:target_id, :company, :tier, :careers_url, :status,
                    :matched_master_id, :source)
                ON CONFLICT(target_id) DO UPDATE SET
                    company=excluded.company, tier=excluded.tier, careers_url=excluded.careers_url,
                    status=excluded.status, matched_master_id=excluded.matched_master_id,
                    source=excluded.source
                """,
                {
                    "target_id": target["target_id"],
                    "company": target["company"],
                    "tier": target.get("tier"),
                    "careers_url": target.get("careers_url"),
                    "status": target.get("status"),
                    "matched_master_id": target.get("matched_master_id"),
                    "source": target.get("source"),
                },
            )
        return int(target["target_id"])

    def list_global_targets(self) -> list[dict[str, Any]]:
        assert self.connection is not None
        return [dict(r) for r in self.connection.execute(
            "SELECT * FROM global_targets ORDER BY target_id")]

    def count_global_targets(self) -> int:
        assert self.connection is not None
        return int(self.connection.execute("SELECT COUNT(*) FROM global_targets").fetchone()[0])

    def upsert_registry_platform(self, platform: dict[str, Any]) -> int:
        assert self.connection is not None
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO registry_platforms(
                    normalized_key, name, url, url_verified, handling_class, feed_url, terms_url,
                    approved, owner_has_account, alerts_set, notes
                ) VALUES (
                    :normalized_key, :name, :url, 0, :handling_class, :feed_url, :terms_url,
                    :approved, :owner_has_account, :alerts_set, :notes
                )
                ON CONFLICT(normalized_key) DO UPDATE SET
                    name=excluded.name, url=excluded.url,
                    url_verified=0,
                    handling_class=excluded.handling_class,
                    feed_url=excluded.feed_url, terms_url=excluded.terms_url,
                    approved=excluded.approved
                """,
                {
                    **platform,
                    "feed_url": platform.get("feed_url"),
                    "terms_url": platform.get("terms_url"),
                    "approved": int(platform.get("approved", False)),
                    "owner_has_account": int(platform.get("owner_has_account", False)),
                    "alerts_set": int(platform.get("alerts_set", False)),
                    "notes": platform.get("notes", ""),
                },
            )
            row = conn.execute(
                "SELECT platform_id FROM registry_platforms WHERE normalized_key=?",
                (platform["normalized_key"],),
            ).fetchone()
            platform_id = int(row[0])
            conn.execute(
                "INSERT OR IGNORE INTO platform_tags(platform_id, section, owner_group) VALUES (?, ?, ?)",
                (platform_id, platform["section"], platform.get("owner_group")),
            )
        return platform_id

    def list_registry_platforms(self) -> list[dict[str, Any]]:
        assert self.connection is not None
        rows = self.connection.execute(
            """
            SELECT p.*, GROUP_CONCAT(DISTINCT t.section) AS sections,
                   GROUP_CONCAT(DISTINCT t.owner_group) AS owner_groups
            FROM registry_platforms p
            LEFT JOIN platform_tags t ON t.platform_id=p.platform_id
            GROUP BY p.platform_id ORDER BY p.name COLLATE NOCASE
            """
        )
        return [dict(row) for row in rows]

    def update_registry_platform(self, platform_id: int, *, owner_has_account: bool | None = None,
                                 alerts_set: bool | None = None) -> None:
        assert self.connection is not None
        fields = []
        values: list[Any] = []
        if owner_has_account is not None:
            fields.append("owner_has_account=?")
            values.append(int(owner_has_account))
        if alerts_set is not None:
            fields.append("alerts_set=?")
            values.append(int(alerts_set))
        if not fields:
            return
        values.append(platform_id)
        with self.transaction() as conn:
            cursor = conn.execute(
                f"UPDATE registry_platforms SET {', '.join(fields)} WHERE platform_id=?",
                values,
            )
            if cursor.rowcount != 1:
                raise ValueError(f"unknown registry platform: {platform_id}")

    def upsert_saved_alert(self, label: str, keyword_group: str, keyword: str,
                           portal_key: str | None = None, enabled: bool = True) -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO saved_alerts(label, keyword_group, keyword, portal_key, enabled)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(label) DO UPDATE SET
                    keyword_group=excluded.keyword_group, keyword=excluded.keyword,
                    portal_key=excluded.portal_key, enabled=excluded.enabled
                """,
                (label, keyword_group, keyword, portal_key, int(enabled)),
            )

    def list_saved_alerts(self) -> list[dict[str, Any]]:
        assert self.connection is not None
        return [dict(row) for row in self.connection.execute(
            "SELECT * FROM saved_alerts ORDER BY keyword_group, label"
        )]

    def set_saved_alert_checked(self, alert_id: int, checked: bool) -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            cursor = conn.execute(
                "UPDATE saved_alerts SET checked=? WHERE alert_id=?",
                (int(checked), alert_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"unknown saved alert: {alert_id}")

    # -------------------------------------------------------------------- sources
    def add_source(self, source: dict[str, Any]) -> int:
        assert self.connection is not None
        with self.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO sources(company_master_id, source_type, url, enabled, request_cap)
                VALUES (:company_master_id, :source_type, :url, :enabled, :request_cap)
                ON CONFLICT(company_master_id, url) DO UPDATE SET
                    source_type=excluded.source_type, enabled=excluded.enabled,
                    request_cap=excluded.request_cap
                """,
                {
                    "company_master_id": source["company_master_id"],
                    "source_type": source["source_type"],
                    "url": source["url"],
                    "enabled": int(source.get("enabled", True)),
                    "request_cap": int(source.get("request_cap", 5)),
                },
            )
            if cur.lastrowid:
                return int(cur.lastrowid)
            row = conn.execute(
                "SELECT source_id FROM sources WHERE company_master_id=? AND url=?",
                (source["company_master_id"], source["url"]),
            ).fetchone()
            return int(row[0])

    def list_sources(self) -> list[dict[str, Any]]:
        assert self.connection is not None
        return [dict(r) for r in self.connection.execute("SELECT * FROM sources ORDER BY source_id")]

    def update_source_health(self, source_id: int, status: str, ok: bool) -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            if ok:
                conn.execute(
                    "UPDATE sources SET last_run_at=?, last_status=?, fail_count=0 WHERE source_id=?",
                    (now_iso(), status, source_id),
                )
            else:
                conn.execute(
                    "UPDATE sources SET last_run_at=?, last_status=?, fail_count=fail_count+1 WHERE source_id=?",
                    (now_iso(), status, source_id),
                )

    # ----------------------------------------------------------------------- jobs
    def _find_job(self, conn: sqlite3.Connection, job: dict[str, Any]) -> sqlite3.Row | None:
        if job.get("source_id") is not None and job.get("source_job_id"):
            row = conn.execute(
                "SELECT * FROM jobs WHERE source_id=? AND source_job_id=?",
                (job["source_id"], job["source_job_id"]),
            ).fetchone()
            if row:
                return row
        row = conn.execute("SELECT * FROM jobs WHERE canonical_url=?", (job["canonical_url"],)).fetchone()
        if row:
            return row
        row = conn.execute("SELECT * FROM jobs WHERE dedupe_key=?", (job["dedupe_key"],)).fetchone()
        if row:
            return row
        return conn.execute("SELECT * FROM jobs WHERE fingerprint=?", (job["fingerprint"],)).fetchone()

    def upsert_job(self, job: dict[str, Any]) -> tuple[int, bool]:
        assert self.connection is not None
        stamp = now_iso()
        with self.transaction() as conn:
            existing = self._find_job(conn, job)
            if existing:
                conn.execute(
                    """
                    UPDATE jobs SET last_seen_at=?, score_total=?, score_breakdown=?, is_active=1,
                        experience_level=?, is_software=?, software_evidence=?, skills_required=?,
                        skills_preferred=?, work_mode=?, country=?, updated_at=?
                    WHERE job_id=?
                    """,
                    (
                        stamp,
                        int(job.get("score_total", 0)),
                        json.dumps(job.get("score_breakdown", {}), sort_keys=True),
                        job.get("experience_level", "unknown"),
                        int(job.get("is_software", 0)),
                        json.dumps(job.get("software_evidence", [])),
                        json.dumps(job.get("skills_required", [])),
                        json.dumps(job.get("skills_preferred", [])),
                        job.get("work_mode", "unknown"),
                        job.get("country", "unknown"),
                        stamp,
                        int(existing["job_id"]),
                    ),
                )
                return int(existing["job_id"]), False
            cur = conn.execute(
                """
                INSERT INTO jobs(source_id, company_master_id, source_job_id, canonical_url, apply_url,
                    title, company_name, location_raw, city, region, country, work_mode, employment_type,
                    experience_level, is_internship, is_software, software_evidence, skills_required,
                    skills_preferred, description_text, posted_at, discovered_at, last_seen_at, status, origin,
                    score_total, score_breakdown, dedupe_key, fingerprint, is_active, created_at, updated_at)
                VALUES (:source_id, :company_master_id, :source_job_id, :canonical_url, :apply_url,
                    :title, :company_name, :location_raw, :city, :region, :country, :work_mode, :employment_type,
                    :experience_level, :is_internship, :is_software, :software_evidence, :skills_required,
                    :skills_preferred, :description_text, :posted_at, :discovered_at, :last_seen_at, :status, :origin,
                    :score_total, :score_breakdown, :dedupe_key, :fingerprint, 1, :created_at, :updated_at)
                """,
                {
                    "source_id": job.get("source_id"),
                    "company_master_id": job.get("company_master_id"),
                    "source_job_id": job.get("source_job_id"),
                    "canonical_url": job["canonical_url"],
                    "apply_url": job.get("apply_url"),
                    "title": job["title"],
                    "company_name": job["company_name"],
                    "location_raw": job.get("location_raw", ""),
                    "city": job.get("city", ""),
                    "region": job.get("region", ""),
                    "country": job.get("country", "unknown"),
                    "work_mode": job.get("work_mode", "unknown"),
                    "employment_type": job.get("employment_type", "unknown"),
                    "experience_level": job.get("experience_level", "unknown"),
                    "is_internship": int(job.get("is_internship", 0)),
                    "is_software": int(job.get("is_software", 0)),
                    "software_evidence": json.dumps(job.get("software_evidence", [])),
                    "skills_required": json.dumps(job.get("skills_required", [])),
                    "skills_preferred": json.dumps(job.get("skills_preferred", [])),
                    "description_text": job.get("description_text", ""),
                    "posted_at": job.get("posted_at"),
                    "discovered_at": job.get("discovered_at", stamp),
                    "last_seen_at": stamp,
                    "status": job.get("status", "active"),
                    "origin": job.get("origin", "discovery"),
                    "score_total": int(job.get("score_total", 0)),
                    "score_breakdown": json.dumps(job.get("score_breakdown", {}), sort_keys=True),
                    "dedupe_key": job["dedupe_key"],
                    "fingerprint": job["fingerprint"],
                    "created_at": stamp,
                    "updated_at": stamp,
                },
            )
            return int(cur.lastrowid), True

    def find_job_by_source(self, source_id: int, source_job_id: str) -> dict[str, Any] | None:
        assert self.connection is not None
        row = self.connection.execute(
            "SELECT * FROM jobs WHERE source_id=? AND source_job_id=?", (source_id, source_job_id)
        ).fetchone()
        return dict(row) if row else None

    def find_job_by_url(self, url: str) -> dict[str, Any] | None:
        assert self.connection is not None
        row = self.connection.execute("SELECT * FROM jobs WHERE canonical_url=?", (url,)).fetchone()
        return dict(row) if row else None

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        assert self.connection is not None
        row = self.connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def list_jobs(self, active_only: bool = False) -> list[dict[str, Any]]:
        assert self.connection is not None
        sql = "SELECT * FROM jobs"
        if active_only:
            sql += " WHERE is_active=1"
        sql += " ORDER BY job_id"
        return [dict(r) for r in self.connection.execute(sql)]

    def set_job_status(self, job_id: int, status: str) -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            conn.execute("UPDATE jobs SET status=?, is_active=?, updated_at=? WHERE job_id=?",
                         (status, 0 if status in {"closed", "expired"} else 1, now_iso(), job_id))

    # ----------------------------------------------------------------------- runs
    def create_run(self) -> int:
        assert self.connection is not None
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO daily_runs(started_at, mode) VALUES (?, 'dry')", (now_iso(),)
            )
            return int(cur.lastrowid)

    def finish_run(self, run_id: int, counters: dict[str, int], errors: list[str]) -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE daily_runs SET finished_at=?, source_count=?, fetched_count=?, normalized_count=?,
                    rejected_count=?, duplicate_count=?, queued_count=?, errors_json=? WHERE run_id=?
                """,
                (
                    now_iso(), counters.get("source_count", 0), counters.get("fetched_count", 0),
                    counters.get("normalized_count", 0), counters.get("rejected_count", 0),
                    counters.get("duplicate_count", 0), counters.get("queued_count", 0),
                    json.dumps(errors), run_id,
                ),
            )

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        assert self.connection is not None
        row = self.connection.execute("SELECT * FROM daily_runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def list_runs(self) -> list[dict[str, Any]]:
        assert self.connection is not None
        return [dict(r) for r in self.connection.execute("SELECT * FROM daily_runs ORDER BY run_id DESC")]

    # ---------------------------------------------------------------------- queue
    def enqueue(self, run_id: int, job_id: int, rank: int, score: int, reason: str) -> int:
        assert self.connection is not None
        stamp = now_iso()
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO queue(run_id, job_id, rank, score, reason, state, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'queued', ?, ?)",
                (run_id, job_id, rank, score, reason, stamp, stamp),
            )
            conn.execute(
                "INSERT INTO queue_events(queue_id, old_state, new_state, actor, note, created_at) "
                "VALUES (?, NULL, 'queued', 'system', 'daily selection', ?)",
                (cur.lastrowid, stamp),
            )
            return int(cur.lastrowid)

    def list_queue(self, run_id: int | None = None) -> list[dict[str, Any]]:
        assert self.connection is not None
        if run_id is None:
            sql = """SELECT q.*, j.title, j.company_name, j.canonical_url, j.score_breakdown,
                            j.experience_level, j.work_mode, j.is_software
                     FROM queue q JOIN jobs j ON j.job_id=q.job_id ORDER BY q.run_id DESC, q.rank"""
            return [dict(r) for r in self.connection.execute(sql)]
        sql = """SELECT q.*, j.title, j.company_name, j.canonical_url, j.score_breakdown,
                        j.experience_level, j.work_mode, j.is_software
                 FROM queue q JOIN jobs j ON j.job_id=q.job_id WHERE q.run_id=? ORDER BY q.rank"""
        return [dict(r) for r in self.connection.execute(sql, (run_id,))]

    def update_queue_state(self, queue_id: int, new_state: str, actor: str = "owner", note: str = "") -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            row = conn.execute("SELECT state FROM queue WHERE queue_id=?", (queue_id,)).fetchone()
            if not row:
                raise KeyError(f"queue item not found: {queue_id}")
            old = row[0]
            stamp = now_iso()
            conn.execute("UPDATE queue SET state=?, updated_at=? WHERE queue_id=?", (new_state, stamp, queue_id))
            conn.execute(
                "INSERT INTO queue_events(queue_id, old_state, new_state, actor, note, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (queue_id, old, new_state, actor, note, stamp),
            )

    def list_queue_events(self, queue_id: int) -> list[dict[str, Any]]:
        assert self.connection is not None
        return [dict(r) for r in self.connection.execute(
            "SELECT * FROM queue_events WHERE queue_id=? ORDER BY event_id", (queue_id,)
        )]

    # --------------------------------------------------------------- applications
    def create_application(self, job_id: int, status: str, applied_at: str | None = None,
                           notes: str = "", proof_path: str | None = None) -> int:
        assert self.connection is not None
        stamp = now_iso()
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO applications(job_id, status, applied_at, notes, proof_path, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (job_id, status, applied_at, notes, proof_path, stamp, stamp),
            )
            return int(cur.lastrowid)

    def update_application(self, application_id: int, status: str, notes: str | None = None) -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            if notes is None:
                conn.execute("UPDATE applications SET status=?, updated_at=? WHERE application_id=?",
                             (status, now_iso(), application_id))
            else:
                conn.execute("UPDATE applications SET status=?, notes=?, updated_at=? WHERE application_id=?",
                             (status, notes, now_iso(), application_id))

    def list_applications(self) -> list[dict[str, Any]]:
        assert self.connection is not None
        sql = """SELECT a.*, j.title, j.company_name, j.canonical_url
                 FROM applications a JOIN jobs j ON j.job_id=a.job_id ORDER BY a.application_id"""
        return [dict(r) for r in self.connection.execute(sql)]

    # ---------------------------------------------------------------- suppression
    def suppress(self, kind: str, value: str, reason: str = "") -> None:
        assert self.connection is not None
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO suppressions(kind, value, reason, created_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(kind, value) DO UPDATE SET reason=excluded.reason",
                (kind, value, reason, now_iso()),
            )

    def is_suppressed(self, kind: str, value: str) -> bool:
        assert self.connection is not None
        row = self.connection.execute(
            "SELECT 1 FROM suppressions WHERE kind=? AND value=?", (kind, value)
        ).fetchone()
        return row is not None

    def list_suppressions(self) -> list[dict[str, Any]]:
        assert self.connection is not None
        return [dict(r) for r in self.connection.execute("SELECT * FROM suppressions ORDER BY suppression_id")]

    def applied_keys(self) -> set[str]:
        assert self.connection is not None
        keys: set[str] = set()
        rows = self.connection.execute(
            """SELECT j.canonical_url, j.fingerprint, j.source_job_id
               FROM applications a JOIN jobs j ON j.job_id=a.job_id
               WHERE a.status IN ('applied', 'Applied', 'interview', 'offer')"""
        )
        for row in rows:
            for value in row:
                if value:
                    keys.add(str(value))
        return keys

    # --------------------------------------------------------------------- counts
    def counts(self) -> dict[str, int]:
        assert self.connection is not None
        tables = ["companies", "sources", "jobs", "applications", "daily_runs", "queue", "suppressions"]
        return {table: int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
