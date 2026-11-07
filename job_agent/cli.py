"""Non-interactive CLI. Live mode is impossible by construction."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .companies.importer import import_companies
from .config import load_config, load_overrides, load_preferences, load_sources
from .db.repository import Database
from .errors import JobAgentError, SafetyLockError
from .io.excel_exporter import export_workbook
from .logging_setup import setup_logging
from .pipeline.run import run_pipeline
from .report import daily_report


def _db(path: str, config: dict) -> Database:
    backup_keep = int(config.get("limits", {}).get("backup_keep", 14))
    return Database(path or config["database_path"], backup_keep=backup_keep)


def _load_fixture(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or "batches" not in data:
        raise ValueError("fixture must be a mapping with a batches list")
    return data


def cmd_run(args, config: dict) -> int:
    if not args.fixtures:
        raise SafetyLockError("offline fixture input is required; live discovery is not available")
    prefs = load_preferences(args.preferences)
    fixture = _load_fixture(args.fixtures)
    db = _db(args.db, config)
    db.connect()
    try:
        db.migrate()
        for company in fixture.get("companies", []):
            db.upsert_company(company)
        for source in fixture.get("sources", []):
            db.add_source(source)
        result = run_pipeline(db, prefs, fixture["batches"])
        print(json.dumps(result, indent=2, default=str))
        return 0
    finally:
        db.close()


def cmd_report(args, config: dict) -> int:
    db = _db(args.db, config)
    db.connect()
    try:
        db.migrate()
        print(json.dumps(daily_report(db, args.run_id), indent=2, default=str))
        return 0
    finally:
        db.close()


def cmd_import(args, config: dict) -> int:
    db = _db(args.db, config)
    db.connect()
    try:
        db.migrate()
        report = import_companies(db, args.workbook, sheet=args.sheet, commit=args.commit)
        print(json.dumps({"companies": len(report["companies"]), "errors": report["errors"],
                          "global_targets": len(report["global_targets"]),
                          "global_target_errors": report["global_target_errors"],
                          "global_target_columns": report["global_target_columns"],
                          "hash_before": report["hash_before"], "hash_after": report["hash_after"],
                          "hash_unchanged": report["hash_unchanged"]}, indent=2))
        return 0
    finally:
        db.close()


def cmd_export(args, config: dict) -> int:
    db = _db(args.db, config)
    db.connect()
    try:
        db.migrate()
        print(json.dumps(export_workbook(db, args.out, config["exports_dir"], force=args.force), indent=2))
        return 0
    finally:
        db.close()


def cmd_db_check(args, config: dict) -> int:
    db = _db(args.db, config)
    db.connect()
    try:
        applied = db.migrate()
        print(json.dumps({"database": str(db.path), "applied_migrations": applied,
                          "counts": db.counts()}, indent=2))
        return 0
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job_agent")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--db", default=None)
    parser.add_argument("--live", action="store_true", help="refused; included only to make refusal explicit")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the offline fixture pipeline")
    run.add_argument("--fixtures", required=False)
    run.add_argument("--preferences", default="config/preferences.yaml")
    run.set_defaults(func=cmd_run)

    report = sub.add_parser("report", help="print a daily report")
    report.add_argument("--run-id", type=int, default=None)
    report.set_defaults(func=cmd_report)

    imp = sub.add_parser("import-companies", help="read-only company import")
    imp.add_argument("--workbook", required=True)
    imp.add_argument("--sheet", default="Companies")
    imp.add_argument("--commit", action="store_true")
    imp.set_defaults(func=cmd_import)

    exp = sub.add_parser("export", help="export SQLite to a new workbook")
    exp.add_argument("--out", required=True)
    exp.add_argument("--force", action="store_true")
    exp.set_defaults(func=cmd_export)

    check = sub.add_parser("db-check", help="migrate and print counts")
    check.set_defaults(func=cmd_db_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.live:
            raise SafetyLockError("--live is not supported; dry-run only")
        config = load_config(args.config)
        setup_logging(config["logs_dir"])
        return int(args.func(args, config))
    except SafetyLockError as exc:
        print(f"SAFETY LOCK: {exc}", file=sys.stderr)
        return 2
    except (JobAgentError, FileNotFoundError, ValueError, PermissionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
