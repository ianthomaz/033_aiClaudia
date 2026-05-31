#!/usr/bin/env bash
# Copy Cursor agent transcripts into this repo (run on your Mac).
# Cursor may use different folder slugs when the workspace path changes.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DST="$ROOT/local-only/cursor-transcripts"
mkdir -p "$DST"

SLUGS=(
  "Users-ianthomaz-033-aiClaudia"
  "Users-ianthomaz-Documents-projects-033-aiClaudia"
  "Users-ianthomaz-documents-projects-033-aiClaudia"
)

for slug in "${SLUGS[@]}"; do
  SRC="${HOME}/.cursor/projects/${slug}/agent-transcripts"
  if [[ -d "$SRC" ]]; then
    echo "Found: $SRC"
    shopt -s nullglob
    for f in "$SRC"/*.jsonl; do
      base="$(basename "$f")"
      cp -v "$f" "$DST/${slug}__${base}"
    done
    shopt -u nullglob
  fi
done

# Fallback: project slug differs — only folders that look like this repo (not all Cursor projects)
while IFS= read -r -d '' parent; do
  SRC="$parent/agent-transcripts"
  if [[ ! -d "$SRC" ]]; then
    continue
  fi
  slug="$(basename "$parent")"
  echo "Found (search): $SRC"
  shopt -s nullglob
  for f in "$SRC"/*.jsonl; do
    base="$(basename "$f")"
    cp -v "$f" "$DST/${slug}__${base}"
  done
  shopt -u nullglob
done < <(find "${HOME}/.cursor/projects" -maxdepth 1 -mindepth 1 -type d \( -iname '*033*claudia*' -o -iname '*aiclaudia*' \) -print0 2>/dev/null || true)

echo "Output: $DST"
ls -la "$DST" || true
