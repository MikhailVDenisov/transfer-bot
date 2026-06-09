#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${DB_PATH:-$ROOT_DIR/transfer_bot.db}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/sqlite}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/transfer_bot_${STAMP}.db"
SQLITE3_BIN="${SQLITE3_BIN:-}"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
  echo "Ошибка: база данных не найдена: $DB_PATH" >&2
  exit 1
fi

if [ -z "$SQLITE3_BIN" ]; then
  if command -v sqlite3 >/dev/null 2>&1; then
    SQLITE3_BIN="$(command -v sqlite3)"
  elif [ -x "/usr/bin/sqlite3" ]; then
    SQLITE3_BIN="/usr/bin/sqlite3"
  else
    echo "Ошибка: sqlite3 не найден. Установите sqlite3 или передайте SQLITE3_BIN=/path/to/sqlite3" >&2
    exit 1
  fi
fi

# Консистентный бэкап SQLite даже при работающем приложении.
"$SQLITE3_BIN" "$DB_PATH" ".backup '$BACKUP_FILE'"

# Проверка целостности резервной копии.
if ! "$SQLITE3_BIN" "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "^ok$"; then
  echo "Ошибка: проверка целостности бэкапа не пройдена: $BACKUP_FILE" >&2
  rm -f "$BACKUP_FILE"
  exit 1
fi

gzip -f "$BACKUP_FILE"

# Ротация старых бэкапов.
find "$BACKUP_DIR" -type f -name "transfer_bot_*.db.gz" -mtime +"$KEEP_DAYS" -delete

echo "Бэкап создан: ${BACKUP_FILE}.gz"
