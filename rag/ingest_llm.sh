#!/usr/bin/env bash
# Ingere/atualiza o corpus RAG da Claudia no portal LLM pessoal (ai2tcs / itcs-webplace).
# Endpoint default: https://llm.webplace.cc  (POST /ingest, POST /ingest/upload — Bearer).
#
# Variáveis (vêm do deploy/config.env ou env.prod):
#   LLM_API_URL   (default https://llm.webplace.cc)
#   LLM_API_TOKEN (obrigatório — Bearer global ou chave itcs_aiclaudia_…)
#   LLM_PROJECT_ID (default aiclaudia)
#
# No mini62, se ai2tcs estiver em 127.0.0.1:28471, usa local para ingest (mesmo índice que llm.webplace.cc).
# Forçar remoto: LLM_INGEST_FORCE_REMOTE=1
#
# Modos:
#   ./rag/ingest_llm.sh            # 'sync': upload de cada rag/*.md + dispara o index
#   ./rag/ingest_llm.sh upload     # só envia os ficheiros (/ingest/upload)
#   ./rag/ingest_llm.sh index      # só dispara /ingest
set -euo pipefail

BASE="${LLM_API_URL:-https://llm.webplace.cc}"; BASE="${BASE%/}"
TOKEN="${LLM_API_TOKEN:?defina LLM_API_TOKEN (Bearer do projeto)}"
PROJECT="${LLM_PROJECT_ID:-aiclaudia}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-sync}"

if [ "${LLM_INGEST_FORCE_REMOTE:-}" != "1" ] && curl -sf --max-time 3 "${BASE}/health" >/dev/null 2>&1; then
  : # LLM_API_URL already reachable
elif [ "${LLM_INGEST_FORCE_REMOTE:-}" != "1" ] && curl -sf --max-time 3 "http://127.0.0.1:28471/health" >/dev/null 2>&1; then
  echo "ℹ️  ai2tcs local (127.0.0.1:28471) — ingest directo no mini62"
  BASE="http://127.0.0.1:28471"
fi

_post() {
  local out code
  out="$(curl -sS -w $'\n%{http_code}' "$@")" || return 1
  code="${out##*$'\n'}"; out="${out%$'\n'*}"
  printf '%s\n' "$out"
  [ "$code" -lt 400 ] || { echo "  (HTTP $code)" >&2; return 1; }
}

do_upload() {
  local f rc=0
  for f in "$HERE"/0*_*.md; do
    [ -f "$f" ] || continue
    echo "→ upload $(basename "$f")"
    if ! _post -X POST "${BASE}/ingest/upload" \
      -H "Authorization: Bearer ${TOKEN}" \
      -F "project_id=${PROJECT}" \
      -F "subpath=rag/" \
      -F "file=@${f};type=text/markdown"; then
      rc=1
    fi
  done
  return "$rc"
}

do_index() {
  echo "→ POST /ingest project_id=${PROJECT} em ${BASE}"
  _post -X POST "${BASE}/ingest" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"project_id\":\"${PROJECT}\",\"incremental\":true,\"name\":\"aiclaudia-rag\"}"
}

case "$MODE" in
  upload) do_upload ;;
  index)  do_index ;;
  sync)   do_upload && do_index ;;
  *) echo "modo inválido: $MODE (use sync | upload | index)" >&2; exit 2 ;;
esac

echo "✅ ingest '${MODE}' concluído (projeto ${PROJECT}, base ${BASE}). Conferir no dashboard do portal."
