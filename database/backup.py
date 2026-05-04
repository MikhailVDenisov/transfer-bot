"""
Утилита для создания резервных копий SQLite базы данных.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence

from config.settings import DB_PATH


def build_backup_path(
    db_path: Path, backup_dir: Path, timestamp: datetime | None = None
) -> Path:
    """Строит путь до файла резервной копии."""
    snapshot_time = timestamp or datetime.now()
    file_name = f"{db_path.stem}_{snapshot_time.strftime('%Y%m%d_%H%M%S')}.db"
    return backup_dir / file_name


def cleanup_old_backups(backup_dir: Path, prefix: str, keep: int) -> list[Path]:
    """Удаляет старые резервные копии, оставляя только keep последних файлов."""
    if keep < 1:
        return []

    backups = sorted(backup_dir.glob(f"{prefix}_*.db"))
    outdated_backups = backups[:-keep]

    for backup_path in outdated_backups:
        backup_path.unlink()

    return outdated_backups


def backup_database(
    db_path: str = DB_PATH,
    backup_dir: str = "backups",
    keep: int | None = None,
    timestamp: datetime | None = None,
) -> Path:
    """Создает резервную копию SQLite базы данных."""
    source_path = Path(db_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"База данных не найдена: {source_path}")

    target_dir = Path(backup_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = build_backup_path(source_path, target_dir, timestamp=timestamp)

    with NamedTemporaryFile(
        dir=target_dir,
        prefix=f"{source_path.stem}_",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        with (
            sqlite3.connect(source_path) as source_connection,
            sqlite3.connect(temp_path) as backup_connection,
        ):
            source_connection.backup(backup_connection)

        temp_path.replace(target_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    if keep is not None:
        cleanup_old_backups(target_dir, source_path.stem, keep)

    return target_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Создает резервную копию SQLite базы данных transfer-bot."
    )
    parser.add_argument(
        "--db-path",
        default=DB_PATH,
        help="Путь до SQLite базы данных. По умолчанию берется DB_PATH из .env.",
    )
    parser.add_argument(
        "--backup-dir",
        default="backups",
        help="Папка, в которую будут складываться резервные копии.",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=None,
        help="Сколько последних бэкапов хранить. Если не указано, старые файлы не удаляются.",
    )
    args = parser.parse_args(argv)

    if args.keep is not None and args.keep < 1:
        parser.error("--keep должен быть больше 0")

    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа для CLI."""
    args = parse_args(argv)
    backup_path = backup_database(
        db_path=args.db_path,
        backup_dir=args.backup_dir,
        keep=args.keep,
    )
    print(f"Бэкап создан: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
