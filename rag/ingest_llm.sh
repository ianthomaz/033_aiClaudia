#!/usr/bin/env bash
# Ingere o corpus RAG da Claudia no portal LLM pessoal (ai2tcs / itcs-webplace).
#
# Pré-requisitos:
#   - O projeto (LLM_PROJECT_ID, default 'aiclaudia') já existe no portal (POST /projects no dashboard).
#   - Os .md de rag/ estão acessíveis ao llm_server (via 'sources' do projeto) OU envia-se cada
#     ficheiro por /ingest/upload (multipart) — ver mais abaixo.
#
# Uso:
#   LLM_API_URL=https://llm.webplace.cc \
#   LLM_API_TOKEN=xxxxx \
#   LLM_PROJECT_ID=aiclaudia \
#   ./rag/ingest_llm.sh                 # dispara /ingest incremental do projeto
#
#   ./rag/ingest_llm.sh upload          # envia cada rag/*.md via /ingest/upload (multipart)
#
set -euo pipefail

BASE="${LLM_API_URL:-https://llm.webplace.cc}"
BASE="${BASE%/}"
TOKEN="${LLM_API_TOKEN:?defina LLM_API_TOKEN (Bearer do projeto)}"
PROJECT="${LLM_PROJECT_ID:-aiclaudia}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-ingest}"

if [ "$MODE" = "upload" ]; then
  # Envia cada ficheiro markdown para a library do projeto.
  for f in "$HERE"/0*_*.md; do
    echo "→ upload $(basename "$f")"
    curl -sS -X POST "${BASE}/ingest/upload" \
      -H "Authorization: Bearer ${TOKEN}" \
      -F "project_id=${PROJECT}" \
      -F "library_slug=${PROJECT}" \
      -F "subpath=rag/" \
      -F "file=@${f};type=text/markdown"
    echo
  done
  echo "✅ uploads enviados; correr depois: $0 (modo ingest) para indexar."
  exit 0
fi

# Dispara ingest incremental do projeto (usa as 'sources' configuradas no projeto).
echo "→ POST /ingest project_id=${PROJECT} em ${BASE}"
curl -sS -X POST "${BASE}/ingest" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"${PROJECT}\",\"incremental\":true,\"name\":\"aiclaudia-rag\"}"
echo
echo "✅ ingest disparado. Confirmar no dashboard do portal (/dashboard/projects/${PROJECT})."
