#!/bin/bash
# Nightly SQLite backup script
# Usage: ./scripts/backup.sh /path/to/vibe-electrician/data/db.sqlite3 /path/to/backups

DB_PATH="${1:-./data/db.sqlite3}"
BACKUP_DIR="${2:-./backups}"

mkdir -p "$BACKUP_DIR"
cp "$DB_PATH" "$BACKUP_DIR/db-$(date +%Y%m%d).sqlite3"
find "$BACKUP_DIR" -name "db-*.sqlite3" -mtime +30 -delete
echo "Backup saved to $BACKUP_DIR/db-$(date +%Y%m%d).sqlite3"
