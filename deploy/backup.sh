#!/usr/bin/env bash
# Daily PostgreSQL backup. Keeps the last 14 days. Runs as the "turkiye" user (peer authentication).
set -euo pipefail

DIR=/var/backups/turkiye-discover
mkdir -p "$DIR"
FILE="$DIR/turkiye_discover-$(date +%Y%m%d-%H%M%S).sql.gz"
pg_dump turkiye_discover | gzip > "$FILE"
find "$DIR" -name 'turkiye_discover-*.sql.gz' -mtime +14 -delete
echo "Backup written: $FILE"
