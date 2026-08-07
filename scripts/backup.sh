#!/usr/bin/env bash
# Back up everything that cannot be rebuilt: the database and the photographs.
#
#   ./scripts/backup.sh            → writes into ./data/backups
#   BACKUP_DIR=/mnt/x ./scripts/backup.sh
#
# Restore is documented in docs/HANDOFF.md.

set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./data/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
COMPOSE="docker compose"

PG_USER="${POSTGRES_USER:-portfolio}"
PG_DB="${POSTGRES_DB:-portfolio}"

mkdir -p "$BACKUP_DIR"

echo "→ dumping database"
$COMPOSE exec -T db pg_dump -U "$PG_USER" -d "$PG_DB" --clean --if-exists \
  | gzip > "$BACKUP_DIR/db-$STAMP.sql.gz"

echo "→ archiving media"
# Follows MEDIA_HOST_DIR, which on a server points outside the checkout. The
# archive always unpacks to a directory called `media`, whatever it is called
# on disk, so the restore in docs/HANDOFF.md §5 does not depend on the layout.
MEDIA_DIR="${MEDIA_HOST_DIR:-./data/media}"
if [ -d "$MEDIA_DIR" ]; then
  tar -czf "$BACKUP_DIR/media-$STAMP.tar.gz" \
    -C "$(dirname "$MEDIA_DIR")" --transform 's,^[^/]*,media,' "$(basename "$MEDIA_DIR")"
else
  echo "  (no $MEDIA_DIR yet — skipped)"
fi

echo "→ pruning backups older than 30 days"
find "$BACKUP_DIR" -name 'db-*.sql.gz' -mtime +30 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name 'media-*.tar.gz' -mtime +30 -delete 2>/dev/null || true

echo
echo "Done:"
ls -lh "$BACKUP_DIR" | tail -n +2
