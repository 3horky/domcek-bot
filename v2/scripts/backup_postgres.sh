#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Použitie: $0 VYSTUPNY_ADRESAR" >&2
}

if [[ $# -ne 1 || -z "${1:-}" ]]; then
  usage
  exit 2
fi

backup_dir=$1
mkdir -p -- "$backup_dir"
backup_dir=$(cd -- "$backup_dir" && pwd -P)
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
database_dump="$backup_dir/carlo-postgres-$timestamp.dump"
media_archive="$backup_dir/carlo-media-$timestamp.tar.gz"
manifest="$backup_dir/carlo-backup-$timestamp.sha256"

umask 077
compose=(docker compose)
if [[ -n "${CARLO_COMPOSE_ENV_FILE:-}" ]]; then
  compose+=(--env-file "$CARLO_COMPOSE_ENV_FILE")
fi
if [[ -n "${CARLO_COMPOSE_FILE:-}" ]]; then
  compose+=(-f "$CARLO_COMPOSE_FILE")
fi

"${compose[@]}" exec -T db sh -c \
  'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --compress=9 --no-owner --no-acl' \
  >"$database_dump"

if [[ ! -s "$database_dump" ]]; then
  echo "Databázová záloha je prázdna." >&2
  exit 1
fi

"${compose[@]}" exec -T api sh -c \
  'if [ -d /var/lib/domcek/media ]; then exec tar -C /var/lib/domcek -czf - media; else exec tar -czf - --files-from /dev/null; fi' \
  >"$media_archive"

(
  cd -- "$backup_dir"
  sha256sum "$(basename -- "$database_dump")" "$(basename -- "$media_archive")" \
    >"$(basename -- "$manifest")"
)

echo "Databáza: $database_dump"
echo "Médiá: $media_archive"
echo "Kontrolné súčty: $manifest"
