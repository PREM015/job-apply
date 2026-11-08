from __future__ import annotations

import sqlite3
from pathlib import Path

from job_agent.db.backup import backup_database
from job_agent.db.repository import Database


def _create_db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES ('preserve')")


def test_backup_can_preserve_existing_backups(tmp_path):
    database_path = tmp_path / "job_agent.sqlite3"
    backup_dir = tmp_path / "backups"
    database_path.touch()
    backup_dir.mkdir()
    old_backups = [
        backup_dir / "job_agent_20200101T000000Z.sqlite3",
        backup_dir / "job_agent_20200102T000000Z.sqlite3",
    ]
    for backup in old_backups:
        backup.write_bytes(b"existing backup")

    created = Path(backup_database(database_path, backup_dir, keep=1, prune=False))

    assert created.is_file()
    assert all(backup.is_file() for backup in old_backups)


def test_database_connection_can_disable_backup_pruning(tmp_path):
    database_path = tmp_path / "job_agent.sqlite3"
    backup_dir = tmp_path / "backups"
    _create_db(database_path)
    backup_dir.mkdir()
    old_backups = [
        backup_dir / "job_agent_20200101T000000Z.sqlite3",
        backup_dir / "job_agent_20200102T000000Z.sqlite3",
    ]
    for backup in old_backups:
        backup.write_bytes(b"existing backup")

    database = Database(database_path, backup_keep=1, prune_backups=False)
    database.connect()
    database.close()

    assert all(backup.is_file() for backup in old_backups)
