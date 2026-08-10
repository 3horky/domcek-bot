#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || -z "${1:-}" ]]; then
  echo "Použitie: $0 PRODUKCNY_ZALOHOVY_ADRESAR" >&2
  exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
project_dir=$(cd -- "$script_dir/.." && pwd -P)
deploy_env=${CARLO_PRODUCTION_DEPLOY_ENV:-$project_dir/deploy/.env.deploy}

if [[ ! -f "$deploy_env" ]]; then
  echo "Chýba produkčný deployment env: $deploy_env" >&2
  exit 2
fi

export CARLO_COMPOSE_FILE="$project_dir/compose.production.yaml"
export CARLO_COMPOSE_ENV_FILE="$deploy_env"
backup_dir=$1
retention_days=${CARLO_BACKUP_RETENTION_DAYS:-35}
if [[ ! "$retention_days" =~ ^[1-9][0-9]{0,3}$ ]]; then
  echo "CARLO_BACKUP_RETENTION_DAYS musí byť kladný počet dní." >&2
  exit 2
fi

"$script_dir/backup_postgres.sh" "$backup_dir"
backup_dir=$(cd -- "$backup_dir" && pwd -P)
if [[ "$backup_dir" == "/" || "$backup_dir" == "$project_dir" ]]; then
  echo "Nebezpečný adresár pre retenčné čistenie: $backup_dir" >&2
  exit 2
fi
find "$backup_dir" -maxdepth 1 -type f \
  \( -name 'carlo-postgres-*.dump' -o -name 'carlo-media-*.tar.gz' -o -name 'carlo-backup-*.sha256' \) \
  -mtime "+$retention_days" -delete
