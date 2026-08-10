#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Použitie: $0 ZALOHA.dump NOVA_DATABAZA --confirm CREATE:NOVA_DATABAZA" >&2
}

if [[ $# -ne 4 || "$3" != "--confirm" ]]; then
  usage
  exit 2
fi

backup_file=$1
target_database=$2
confirmation=$4

compose=(docker compose)
if [[ -n "${CARLO_COMPOSE_ENV_FILE:-}" ]]; then
  compose+=(--env-file "$CARLO_COMPOSE_ENV_FILE")
fi
if [[ -n "${CARLO_COMPOSE_FILE:-}" ]]; then
  compose+=(-f "$CARLO_COMPOSE_FILE")
fi

if [[ ! -f "$backup_file" || ! -s "$backup_file" ]]; then
  echo "Záloha neexistuje alebo je prázdna: $backup_file" >&2
  exit 2
fi
if [[ ! "$target_database" =~ ^[a-zA-Z][a-zA-Z0-9_]{0,62}$ ]]; then
  echo "Názov cieľovej databázy nie je bezpečný PostgreSQL identifikátor." >&2
  exit 2
fi
if [[ "$target_database" == "postgres" || "$target_database" == "template0" || "$target_database" == "template1" ]]; then
  echo "Systémová PostgreSQL databáza nemôže byť cieľom obnovy." >&2
  exit 2
fi
if [[ "$confirmation" != "CREATE:$target_database" ]]; then
  echo "Potvrdenie sa nezhoduje s cieľom: očakáva sa CREATE:$target_database" >&2
  exit 2
fi

existing=$("${compose[@]}" exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname = '\''$1'\''"' \
  sh "$target_database")
if [[ "$existing" == "1" ]]; then
  echo "Cieľová databáza už existuje; skript ju z bezpečnostných dôvodov neprepíše." >&2
  exit 1
fi

"${compose[@]}" exec -T db sh -c \
  'createdb -U "$POSTGRES_USER" "$1"' sh "$target_database"

restore_ok=false
cleanup_failed_restore() {
  if [[ "$restore_ok" != true ]]; then
    "${compose[@]}" exec -T db sh -c \
      'dropdb -U "$POSTGRES_USER" --if-exists "$1"' sh "$target_database" >/dev/null 2>&1 || true
  fi
}
trap cleanup_failed_restore EXIT

"${compose[@]}" exec -T db sh -c \
  'exec pg_restore -U "$POSTGRES_USER" -d "$1" --no-owner --no-acl --exit-on-error' \
  sh "$target_database" <"$backup_file"

table_count=$("${compose[@]}" exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$1" -Atqc "SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\''"' \
  sh "$target_database")
alembic_version=$("${compose[@]}" exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$1" -Atqc "SELECT version_num FROM alembic_version"' \
  sh "$target_database")

if [[ ! "$table_count" =~ ^[1-9][0-9]*$ || -z "$alembic_version" ]]; then
  echo "Obnovená databáza neprešla základnou integritnou kontrolou." >&2
  exit 1
fi

restore_ok=true
echo "Obnova do novej databázy $target_database bola úspešná."
echo "Počet public tabuliek: $table_count"
echo "Alembic verzia: $alembic_version"
