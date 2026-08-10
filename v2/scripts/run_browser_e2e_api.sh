#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
project_dir=$(cd -- "$script_dir/.." && pwd -P)
host_python="$project_dir/backend/.venv/bin/python"
action=${1:-serve}

if [[ "$action" != "serve" && "$action" != "cleanup" ]]; then
  echo "Použitie: $0 [serve|cleanup]" >&2
  exit 2
fi

if [[ -x "$host_python" ]]; then
  cd -- "$project_dir/backend"
  if [[ "$action" == "cleanup" ]]; then
    exec "$host_python" scripts/run_browser_e2e_api.py --cleanup
  fi
  exec "$host_python" scripts/run_browser_e2e_api.py
fi

cd -- "$project_dir"
if [[ "$action" == "cleanup" ]]; then
  while IFS= read -r e2e_container; do
    if [[ -n "$e2e_container" ]]; then
      docker stop "$e2e_container" >/dev/null
    fi
  done < <(
    docker ps -q \
      --filter label=com.docker.compose.project=v2 \
      --filter label=com.docker.compose.service=api \
      --filter label=com.docker.compose.oneoff=True \
      --filter publish=4180
  )
  exec docker compose run --rm --no-deps \
    -e TEST_DATABASE_URL=postgresql+asyncpg://domcek:domcek-local-only@db:5432/domcek_test \
    api python scripts/run_browser_e2e_api.py --cleanup
fi
exec docker compose run --rm --no-deps \
  -p 127.0.0.1:4180:4180 \
  -e CARLO_E2E_API_HOST=0.0.0.0 \
  -e TEST_DATABASE_URL=postgresql+asyncpg://domcek:domcek-local-only@db:5432/domcek_test \
  api python scripts/run_browser_e2e_api.py
