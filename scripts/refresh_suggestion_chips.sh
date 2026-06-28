#!/usr/bin/env bash
# Refresh suggestion chips: migrate schema, seed if low, generate from RSS+LLM, soft-archive old.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f "deploy/config.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source deploy/config.env
  set +a
elif [ -f "deploy/env.prod" ]; then
  set -a
  # shellcheck disable=SC1091
  source deploy/env.prod
  set +a
else
  echo "Missing deploy/config.env or deploy/env.prod" >&2
  exit 1
fi

export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5434}"

run_python() {
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx aiclaudia_api; then
    docker exec \
      -e DB_HOST=database \
      -e DB_PORT=5432 \
      -e DB_NAME="${DB_NAME:-aiclaudia}" \
      -e DB_USER="${DB_USER:-aiclaudia}" \
      -e DB_PASSWORD="${DB_PASSWORD}" \
      -e LLM_API_URL="${LLM_API_URL:-}" \
      -e LLM_API_TOKEN="${LLM_API_TOKEN:-}" \
      -e LLM_PROJECT_ID="${LLM_PROJECT_ID:-aiclaudia}" \
      -e LLM_MODEL_ALIAS="${LLM_MODEL_ALIAS:-smart}" \
      aiclaudia_api python3 "/app/deploy/$1" "${@:2}"
  else
    cd deploy
    export DB_HOST="${DB_HOST:-localhost}"
    export DB_PORT="${DB_PORT:-5434}"
    python3 "$1" "${@:2}"
  fi
}

echo "→ ensure schema + seed"
run_python seed_suggestion_chips.py

echo "→ generate from news feeds + LLM"
if run_python generate_suggestion_chips.py; then
  echo "✅ refresh_suggestion_chips done"
else
  echo "⚠️  generation failed; pool may still have seed chips" >&2
  exit 1
fi
