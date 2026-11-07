"""Read-only company workbook importer."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import openpyxl

from ..db.repository import Database

HEADER_ALIASES = {
    "master_id": ("Master ID", "master_id"),
    "name": ("Company Name", "Company", "name"),
    "tier": ("Priority Tier (Best Available)", "Tier", "tier"),
    "careers_url": ("Official Careers Page", "Careers URL", "careers_url"),
    "openings_url": ("Current Openings URL", "Openings URL", "openings_url"),
    "ats_type": ("ATS Type", "ats_type"),
    "ats_identifier": ("ATS Identifier", "ats_identifier"),
    "notes": ("Notes", "notes"),
}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_master_id(value: Any) -> int:
    text = str(value).strip()
    match = re.fullmatch(r"(?:JT-)?0*(\d+)", text, re.I)
    if not match:
        raise ValueError(f"invalid master id: {text}")
    return int(match.group(1))


def _map_headers(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for field, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in headers:
                mapping[field] = headers.index(alias)
                break
    return mapping


def read_companies(workbook_path: str | Path, sheet: str = "Companies") -> dict[str, Any]:
    path = Path(workbook_path)
    before = _hash_file(path)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet not in workbook.sheetnames:
            raise ValueError(f"missing sheet: {sheet}")
        worksheet = workbook[sheet]
        rows = worksheet.iter_rows(values_only=True)
        try:
            headers = [str(cell).strip() if cell is not None else "" for cell in next(rows)]
        except StopIteration:
            raise ValueError("empty Companies sheet")
        mapping = _map_headers(headers)
        missing = [key for key in ("master_id", "name") if key not in mapping]
        if missing:
            raise ValueError(f"missing required headers: {', '.join(missing)}")
        companies = []
        errors = []
        for row_number, values in enumerate(rows, start=2):
            if not any(value not in (None, "") for value in values):
                continue
            record = {}
            for field, index in mapping.items():
                record[field] = values[index] if index < len(values) else None
            if record.get("master_id") in (None, ""):
                errors.append({"row": row_number, "error": "missing_master_id"})
                continue
            if not record.get("name"):
                errors.append({"row": row_number, "error": "missing_name"})
                continue
            companies.append(record)
    finally:
        workbook.close()
    after = _hash_file(path)
    return {"companies": companies, "errors": errors, "hash_before": before,
            "hash_after": after, "hash_unchanged": before == after, "headers": headers}


def read_global_targets(workbook_path: str | Path,
                        sheet: str = "Global Product Targets") -> dict[str, Any]:
    path = Path(workbook_path)
    before = _hash_file(path)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    targets: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    columns: dict[str, int] = {}
    headers: list[str] = []
    try:
        if sheet not in workbook.sheetnames:
            return {"global_targets": targets, "errors": errors, "columns": columns,
                    "hash_before": before, "hash_after": before, "hash_unchanged": True,
                    "sheet_present": False}
        worksheet = workbook[sheet]
        rows = worksheet.iter_rows(values_only=True)
        try:
            headers = [str(cell).strip() if cell is not None else "" for cell in next(rows)]
        except StopIteration:
            raise ValueError("empty Global Product Targets sheet")
        required = {"target_id": "#", "company": "Company", "tier": "Tier",
                    "careers_url": "Careers Page", "status": "Status",
                    "matched_master_id": "Matched Master ID (Companies)", "source": "Source"}
        for field, header in required.items():
            if header not in headers:
                raise ValueError(f"missing required header in {sheet}: {header}")
            columns[field] = headers.index(header) + 1
        for row_number, values in enumerate(rows, start=2):
            if not any(value not in (None, "") for value in values):
                continue
            record = {field: values[index - 1] if index - 1 < len(values) else None
                      for field, index in columns.items()}
            if record.get("target_id") in (None, ""):
                errors.append({"row": row_number, "error": "missing_target_id"})
                continue
            if not record.get("company"):
                errors.append({"row": row_number, "error": "missing_company"})
                continue
            matched = record.get("matched_master_id")
            if matched not in (None, ""):
                try:
                    record["matched_master_id"] = _to_master_id(matched)
                except (TypeError, ValueError):
                    errors.append({"row": row_number, "error": "invalid_matched_master_id"})
                    record["matched_master_id"] = None
            targets.append(record)
    finally:
        workbook.close()
    after = _hash_file(path)
    return {"global_targets": targets, "errors": errors, "columns": columns,
            "hash_before": before, "hash_after": after, "hash_unchanged": before == after,
            "sheet_present": True}


def import_companies(db: Database, workbook_path: str | Path, sheet: str = "Companies",
                     target_sheet: str = "Global Product Targets",
                     commit: bool = False) -> dict[str, Any]:
    report = read_companies(workbook_path, sheet)
    if not report["hash_unchanged"]:
        raise RuntimeError("workbook hash changed during read-only import")
    targets = read_global_targets(workbook_path, target_sheet)
    if not targets["hash_unchanged"]:
        raise RuntimeError("workbook hash changed during read-only global target import")
    report["global_targets"] = targets["global_targets"]
    report["global_target_errors"] = targets["errors"]
    report["global_target_columns"] = targets["columns"]
    report["global_target_sheet_present"] = targets["sheet_present"]
    if commit:
        for company in report["companies"]:
            db.upsert_company({
                "master_id": _to_master_id(company["master_id"]),
                "name": str(company.get("name", "")),
                "tier": company.get("tier"),
                "careers_url": company.get("careers_url"),
                "openings_url": company.get("openings_url"),
                "ats_type": company.get("ats_type") or "unknown",
                "ats_identifier": company.get("ats_identifier"),
                "resolution_status": "unresolved",
                "last_resolved_at": None,
                "notes": company.get("notes"),
            })
        for target in report["global_targets"]:
            db.upsert_global_target({
                "target_id": int(target["target_id"]),
                "company": str(target.get("company", "")),
                "tier": target.get("tier"),
                "careers_url": target.get("careers_url"),
                "status": target.get("status"),
                "matched_master_id": target.get("matched_master_id"),
                "source": target.get("source"),
            })
    return report


def data_quality_report(companies: list[dict[str, Any]]) -> dict[str, Any]:
    tiers: dict[str, int] = {}
    missing_id = 0
    missing_url = 0
    ats_counts: dict[str, int] = {}
    names: set[str] = set()
    duplicates = 0
    for company in companies:
        tier = str(company.get("tier") or "unknown")
        tiers[tier] = tiers.get(tier, 0) + 1
        if not company.get("master_id"):
            missing_id += 1
        if not (company.get("careers_url") or company.get("openings_url")):
            missing_url += 1
        ats = str(company.get("ats_type") or "unknown").lower()
        ats_counts[ats] = ats_counts.get(ats, 0) + 1
        name = str(company.get("name", "")).strip().lower()
        if name in names:
            duplicates += 1
        names.add(name)
    return {"total": len(companies), "tiers": tiers, "missing_id": missing_id,
            "missing_url": missing_url, "ats_counts": ats_counts, "duplicate_names": duplicates}
