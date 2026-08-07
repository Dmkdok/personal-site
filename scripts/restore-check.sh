#!/usr/bin/env bash
# Rehearse a restore without touching the live database or the live media (T086).
#
#   ./scripts/restore-check.sh                       # newest pair in ./data/backups
#   ./scripts/restore-check.sh data/backups/db-20260807-030000.sql.gz \
#                             data/backups/media-20260807-030000.tar.gz
#
# Replays the dump into a scratch database beside the real one, unpacks the
# media archive into a temporary directory, and checks that every media path
# the restored rows point at is actually present in the archive. That last
# check is the point: a dump that replays cleanly still leaves a broken site if
# the two artefacts came from different runs.
#
# The scratch database is dropped at the end. Nothing here writes to the real
# database, and nothing writes into MEDIA_HOST_DIR.

set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./data/backups}"
PG_USER="${POSTGRES_USER:-portfolio}"
PG_DB="${POSTGRES_DB:-portfolio}"
SCRATCH_DB="${SCRATCH_DB:-${PG_DB}_restorecheck}"

DB_DUMP="${1:-$(ls -t "$BACKUP_DIR"/db-*.sql.gz 2>/dev/null | head -1)}"
MEDIA_TAR="${2:-$(ls -t "$BACKUP_DIR"/media-*.tar.gz 2>/dev/null | head -1)}"

if [ -z "${DB_DUMP:-}" ] || [ -z "${MEDIA_TAR:-}" ]; then
  echo "No backup artefacts found in $BACKUP_DIR. Run 'make backup' first." >&2
  exit 1
fi

echo "database dump : $DB_DUMP"
echo "media archive : $MEDIA_TAR"

# Same run? The stamps are in the filenames and must match, or rows will point
# at files the archive does not carry.
DB_STAMP="$(basename "$DB_DUMP" | sed 's/^db-//; s/\.sql\.gz$//')"
MEDIA_STAMP="$(basename "$MEDIA_TAR" | sed 's/^media-//; s/\.tar\.gz$//')"
if [ "$DB_STAMP" != "$MEDIA_STAMP" ]; then
  echo "! the two artefacts are from different runs ($DB_STAMP vs $MEDIA_STAMP)." >&2
  echo "  Continuing anyway — the file check below will show what that costs." >&2
fi

WORK="$(mktemp -d)"
cleanup() {
  rm -rf "$WORK"
  docker compose exec -T db psql -U "$PG_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $SCRATCH_DB;" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo
echo "→ replaying the dump into $SCRATCH_DB"
docker compose exec -T db psql -U "$PG_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS $SCRATCH_DB;" >/dev/null
docker compose exec -T db psql -U "$PG_USER" -d postgres \
  -c "CREATE DATABASE $SCRATCH_DB;" >/dev/null
gunzip -c "$DB_DUMP" | docker compose exec -T db psql -q -U "$PG_USER" -d "$SCRATCH_DB" >/dev/null

echo "→ rows restored"
docker compose exec -T db psql -U "$PG_USER" -d "$SCRATCH_DB" -t -A -F' ' -c \
  "select 'album', count(*) from album union all
   select 'photo', count(*) from photo union all
   select 'post', count(*) from post union all
   select 'project', count(*) from project union all
   select 'site_content', count(*) from site_content;" | sed 's/^/   /'

echo "→ unpacking the media archive"
tar -xzf "$MEDIA_TAR" -C "$WORK"
echo "   $(find "$WORK/media" -type f | wc -l) file(s)"

echo "→ checking every restored path against the archive"
MISSING=0
while IFS= read -r relative; do
  [ -z "$relative" ] && continue
  if [ ! -f "$WORK/media/derived/$relative" ] && [ ! -f "$WORK/media/originals/$relative" ]; then
    echo "   MISSING $relative"
    MISSING=$((MISSING + 1))
  fi
done < <(docker compose exec -T db psql -U "$PG_USER" -d "$SCRATCH_DB" -t -A -c \
  "select original_path from photo where original_path <> ''
   union select thumb_path from photo where thumb_path is not null
   union select medium_path from photo where medium_path is not null
   union select large_path from photo where large_path is not null
   union select cover_path from post where cover_path is not null
   union select cover_path from project where cover_path is not null;" | tr -d '\r')

echo
if [ "$MISSING" -eq 0 ]; then
  echo "Restore rehearsal PASSED — every path in the restored database is in the archive."
else
  echo "Restore rehearsal FAILED — $MISSING path(s) have no file." >&2
  exit 1
fi
