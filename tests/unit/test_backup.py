"""
Тесты для резервного копирования базы данных.
"""

import sqlite3
from datetime import datetime, timedelta

import pytest

from database.backup import backup_database


def create_test_database(db_path):
    """Создает простую SQLite базу данных для теста."""
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE test_records (id INTEGER PRIMARY KEY, value TEXT)"
        )
        connection.execute(
            "INSERT INTO test_records (value) VALUES (?)", ("backup-check",)
        )
        connection.commit()


class TestDatabaseBackup:
    """Тесты для backup_database."""

    def test_backup_database_creates_copy(self, tmp_path):
        """Создает резервную копию с теми же данными, что и оригинал."""
        db_path = tmp_path / "transfer-bot.db"
        backup_dir = tmp_path / "backups"
        create_test_database(db_path)

        backup_path = backup_database(
            db_path=str(db_path),
            backup_dir=str(backup_dir),
            timestamp=datetime(2026, 5, 4, 12, 0, 0),
        )

        assert backup_path.exists()
        assert backup_path.parent == backup_dir.resolve()

        with sqlite3.connect(backup_path) as connection:
            stored_value = connection.execute(
                "SELECT value FROM test_records"
            ).fetchone()

        assert stored_value == ("backup-check",)

    def test_backup_database_keeps_only_latest_files(self, tmp_path):
        """Удаляет старые бэкапы, если включено ограничение keep."""
        db_path = tmp_path / "transfer-bot.db"
        backup_dir = tmp_path / "backups"
        create_test_database(db_path)

        start_time = datetime(2026, 5, 4, 12, 0, 0)
        for offset in range(3):
            backup_database(
                db_path=str(db_path),
                backup_dir=str(backup_dir),
                keep=2,
                timestamp=start_time + timedelta(minutes=offset),
            )

        backup_names = sorted(path.name for path in backup_dir.glob("*.db"))

        assert backup_names == [
            "transfer-bot_20260504_120100.db",
            "transfer-bot_20260504_120200.db",
        ]

    def test_backup_database_raises_for_missing_source(self, tmp_path):
        """Падает с понятной ошибкой, если исходная база не существует."""
        missing_db_path = tmp_path / "missing.db"

        with pytest.raises(FileNotFoundError, match="База данных не найдена"):
            backup_database(db_path=str(missing_db_path))
