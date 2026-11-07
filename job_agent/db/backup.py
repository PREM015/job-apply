from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


def backup_database(database_path: str | Path, backup_dir: str | Path = "data/backups", keep: int = 14) -> str:
    source = Path(database_path)
    if not source.exists():
        raise FileNotFoundError(f"database does not exist: {source}")
    target_dir = Path(backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = target_dir / f"{source.stem}_{stamp}.sqlite3"
    shutil.copy2(source, target)
    backups = sorted(target_dir.glob(f"{source.stem}_*.sqlite3"))
    for old in backups[:-keep]:
        old.unlink()
    return str(target)


def restore_database(backup_path: str | Path, database_path: str | Path) -> str:
    source = Path(backup_path)
    target = Path(database_path)
    if not source.exists():
        raise FileNotFoundError(f"backup does not exist: {source}")
    if source.resolve() == target.resolve():
        raise ValueError("backup and database paths must differ")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(target)
