#!/usr/bin/env bash
# Back up everything that cannot be rebuilt: the database and the photographs.
#
#   ./scripts/backup.sh            → writes into ./data/backups
#   BACKUP_DIR=/mnt/x ./scripts/backup.sh
#   BACKUP_DB_CONTAINER=portfolio-db-1 BACKUP_DIR=/mnt/x ./scripts/backup.sh
#
# The third form is for a host where the stack was not started from this
# checkout — the appliance runs it from Portainer, so there is no compose
# project to `exec` into. Everything else is identical, including the artefact
# names and layout that scripts/restore-check.sh parses.
#
# Restore is documented in docs/HANDOFF.md §5.

set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./data/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"

PG_USER="${POSTGRES_USER:-portfolio}"
PG_DB="${POSTGRES_DB:-portfolio}"

# Which way we reach the database, and the only thing that differs between a
# development checkout and the server. Unset — the default — is exactly what it
# has always been.
if [ -n "${BACKUP_DB_CONTAINER:-}" ]; then
  DB_EXEC=(docker exec -i "$BACKUP_DB_CONTAINER")
else
  DB_EXEC=(docker compose exec -T db)
fi

mkdir -p "$BACKUP_DIR"

echo "→ dumping database"
"${DB_EXEC[@]}" pg_dump -U "$PG_USER" -d "$PG_DB" --clean --if-exists \
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
