#!/bin/bash

# aiClaudia - Start (local) ou Deploy (via SSH para itcsVM2)
# Uso:
#   ./start_aiclaudia.sh           # inicia local (deploy/config.env ou deploy/env.prod)
#   ./start_aiclaudia.sh deploy   # deploy remoto: sync, config, nginx, ingest RAG, start no servidor
#   ./start_aiclaudia.sh refresh-chips  # seed + gera chips a partir de RSS/notícias

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "deploy/033_aiclaudia_dComposer.yml" ]; then
    error "Execute este script a partir do diretório raiz do projeto!"
fi

# Carrega env: preferência config.env (local), senão env.prod (deploy/local)
load_env() {
    local f
    if [ -f "deploy/config.env" ]; then f="deploy/config.env"
    elif [ -f "deploy/env.prod" ]; then f="deploy/env.prod"
    else return 1; fi
    set -a
    while IFS= read -r line; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        export "$line"
    done < "$f"
    set +a
    return 0
}

# Variáveis obrigatórias para subir a aplicação
check_required_env() {
    if [ -z "${DB_PASSWORD}" ]; then
        error "Variável DB_PASSWORD não está definida (deploy/config.env ou deploy/env.prod)."
    fi
    if [ -n "${LLM_API_URL:-}" ] && [ -n "${LLM_API_TOKEN:-}" ] && [ -n "${LLM_PROJECT_ID:-}" ]; then
        success "LLM ITCS configurado (LLM_API_URL + LLM_API_TOKEN + LLM_PROJECT_ID); Claudia fala só pela tua LLM (llm.webplace.cc), sem Gemini/ChatGPT."
        return 0
    fi
    for var in GEMINI_API_KEY CHATGPT_API_KEY; do
        if [ -z "${!var}" ]; then
            error "Variável $var não está definida. Ou defina ITCS (LLM_API_URL, LLM_API_TOKEN, LLM_PROJECT_ID) ou as chaves comerciais."
        fi
    done
}

# ---------- Suggestion chips (RSS + LLM) ----------
bootstrap_suggestion_chips() {
    log "Suggestion chips (schema + seed)..."
    if docker exec \
        -e DB_HOST=database -e DB_PORT=5432 \
        -e DB_NAME="${DB_NAME:-aiclaudia}" -e DB_USER="${DB_USER:-aiclaudia}" \
        -e DB_PASSWORD="${DB_PASSWORD}" \
        aiclaudia_api python3 /app/deploy/seed_suggestion_chips.py 2>/dev/null; then
        success "Suggestion chips seed OK."
    else
        warning "Suggestion chips seed falhou (endpoint usa fallback)."
    fi
}

do_refresh_chips() {
    log "Modo REFRESH-CHIPS: RSS + LLM + pool..."
    if ! load_env; then
        error "Nenhum de: deploy/config.env ou deploy/env.prod encontrado."
    fi
    check_required_env
    export DB_HOST="${DB_HOST:-localhost}"
    export DB_PORT="${DB_PORT:-5434}"
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx aiclaudia_api; then
        warning "Stack não está up; subindo containers primeiro..."
        do_start
    fi
    bash scripts/refresh_suggestion_chips.sh
    success "refresh-chips concluído."
}

# ---------- RAG ingest (LLM pessoal) ----------
# Atualiza o corpus rag/ no portal (llm.webplace.cc). Não-fatal: um problema de RAG
# não deve abortar o deploy/start da app.
ingest_rag() {
    if [ -z "${LLM_API_URL:-}" ] || [ -z "${LLM_API_TOKEN:-}" ] || [ -z "${LLM_PROJECT_ID:-}" ]; then
        warning "RAG ingest pulado: defina LLM_API_URL + LLM_API_TOKEN + LLM_PROJECT_ID."
        return 0
    fi
    log "Atualizando RAG no portal (${LLM_API_URL}, projeto ${LLM_PROJECT_ID})..."
    if LLM_API_URL="$LLM_API_URL" LLM_API_TOKEN="$LLM_API_TOKEN" LLM_PROJECT_ID="$LLM_PROJECT_ID" \
        bash rag/ingest_llm.sh "${RAG_INGEST_MODE:-sync}"; then
        success "RAG ingerido/atualizado no portal."
    else
        warning "RAG ingest falhou (segue o fluxo; verifique o portal/token)."
    fi
}

# ---------- Modo DEPLOY (via SSH) ----------
do_deploy() {
    log "Modo DEPLOY: enviando projeto e configurando servidor..."
    if [ ! -f "deploy/env.prod" ]; then
        error "deploy/env.prod não encontrado. Use deploy/env.prod.example como base."
    fi
    set -a
    while IFS= read -r line; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        export "$line"
    done < deploy/env.prod
    set +a

    for var in DEPLOY_HOST DEPLOY_USER DEPLOY_REMOTE_PATH; do
        if [ -z "${!var}" ]; then
            error "Em env.prod defina: $var"
        fi
    done

    SSH_TARGET="${DEPLOY_USER}@${DEPLOY_HOST}"
    SSH_OPTS="-o StrictHostKeyChecking=accept-new"
    [ -n "${DEPLOY_JUMP}" ] && SSH_OPTS="${SSH_OPTS} -J ${DEPLOY_JUMP}"
    [ -n "${DEPLOY_SSH_KEY}" ] && SSH_OPTS="${SSH_OPTS} -i ${DEPLOY_SSH_KEY}"
    RSYNC_SSH="ssh ${SSH_OPTS}"

    log "Rsync para ${SSH_TARGET}:${DEPLOY_REMOTE_PATH}"
    rsync -avz --delete \
        -e "$RSYNC_SSH" \
        --exclude '.git' \
        --exclude 'deploy/config.env' \
        --exclude 'deploy/env.prod' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.env' \
        --exclude '.env.*' \
        --exclude '*.log' \
        ./ "${SSH_TARGET}:${DEPLOY_REMOTE_PATH}/" || error "Rsync falhou."

    log "Escrevendo config.env no servidor (apenas variáveis da app)..."
    ssh $SSH_OPTS "$SSH_TARGET" "mkdir -p ${DEPLOY_REMOTE_PATH}/deploy"
    {
        echo "DB_NAME=${DB_NAME:-aiclaudia}"
        echo "DB_USER=${DB_USER:-aiclaudia}"
        echo "DB_PASSWORD=${DB_PASSWORD}"
        echo "GEMINI_API_KEY=${GEMINI_API_KEY}"
        echo "GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.0-flash}"
        echo "CHATGPT_API_KEY=${CHATGPT_API_KEY}"
        echo "LLM_API_URL=${LLM_API_URL:-}"
        echo "LLM_API_TOKEN=${LLM_API_TOKEN:-}"
        echo "LLM_PROJECT_ID=${LLM_PROJECT_ID:-}"
        echo "LLM_MODEL_ALIAS=${LLM_MODEL_ALIAS:-smart}"
        echo "LLM_DISABLE_COMMERCIAL=${LLM_DISABLE_COMMERCIAL:-1}"
        echo "LLM_ASK_TIMEOUT_SECONDS=${LLM_ASK_TIMEOUT_SECONDS:-120}"
        echo "LLM_ASK_POLL_INTERVAL=${LLM_ASK_POLL_INTERVAL:-0.8}"
        echo "NGINX_HOST=${NGINX_HOST:-www.aiclaudia.com.br}"
        echo "FLASK_DEBUG=${FLASK_DEBUG:-False}"
        echo "API_PORT=${API_PORT:-5000}"
    } | ssh $SSH_OPTS "$SSH_TARGET" "cat > ${DEPLOY_REMOTE_PATH}/deploy/config.env"
    success "config.env escrito no servidor."

    log "Instalando nginx fragment (aiclaudia.conf, separado do BikeAnjo)..."
    scp $SSH_OPTS deploy/aiclaudia.nginx.conf "${SSH_TARGET}:/tmp/aiclaudia.conf"
    ssh $SSH_OPTS "$SSH_TARGET" "sudo mv /tmp/aiclaudia.conf /etc/nginx/conf.d/aiclaudia.conf && sudo chown root:root /etc/nginx/conf.d/aiclaudia.conf && sudo chmod 644 /etc/nginx/conf.d/aiclaudia.conf && (sudo restorecon /etc/nginx/conf.d/aiclaudia.conf 2>/dev/null || sudo chcon -t httpd_config_t /etc/nginx/conf.d/aiclaudia.conf 2>/dev/null) && sudo nginx -t && sudo systemctl reload nginx" || warning "Nginx reload falhou (confira /etc/nginx/conf.d/aiclaudia.conf no servidor)."
    success "Nginx atualizado (arquivo aiclaudia.conf não é alterado pelo deploy BikeAnjo)."

    # RAG ingest is explicit: ./start_aiclaudia.sh ingest (rag_mode disabled for aiclaudia).

    log "Iniciando aiClaudia no servidor..."
    ssh $SSH_OPTS "$SSH_TARGET" "cd ${DEPLOY_REMOTE_PATH} && ./start_aiclaudia.sh" || error "Falha ao rodar start no servidor."
    log "Atualizando suggestion chips no servidor (RSS + LLM)..."
    ssh $SSH_OPTS "$SSH_TARGET" "cd ${DEPLOY_REMOTE_PATH} && ./start_aiclaudia.sh refresh-chips" || warning "refresh-chips no servidor falhou (chips seed/fallback)."
    success "Deploy concluído."
}

# ---------- Modo LOCAL (start) ----------
do_start() {
    echo "Iniciando aiClaudia (local)..."
    log "Carregando variáveis de ambiente..."
    if ! load_env; then
        error "Nenhum de: deploy/config.env ou deploy/env.prod encontrado."
    fi
    check_required_env
    success "Variáveis carregadas."
    export API_HOST_PORT="${API_HOST_PORT:-5001}"

    log "Parando containers existentes..."
    (cd deploy && (docker compose -f 033_aiclaudia_dComposer.yml down 2>/dev/null || docker-compose -f 033_aiclaudia_dComposer.yml down 2>/dev/null)) || true

    log "Construindo e iniciando containers..."
    (cd deploy && (docker compose -f 033_aiclaudia_dComposer.yml up --build -d || docker-compose -f 033_aiclaudia_dComposer.yml up --build -d))

    log "Aguardando serviços..."
    sleep 10

    log "Testes de conectividade..."
    if ! curl -s -f http://localhost:8082 > /dev/null; then
        error "Nginx (8082) não está respondendo."
    fi
    success "Nginx OK."
    if ! curl -s -f "http://localhost:${API_HOST_PORT}/api/health" > /dev/null; then
        error "API (${API_HOST_PORT}) não está respondendo."
    fi
    success "API OK."
    if ! docker exec aiclaudia_db pg_isready -U aiclaudia -d aiclaudia > /dev/null 2>&1; then
        error "PostgreSQL não está respondendo."
    fi
    success "PostgreSQL OK."

    log "Carregando prompts rndbase (personas)..."
    if docker exec aiclaudia_api python3 /app/deploy/load_rndbase.py; then
        success "rndbase carregado."
    else
        warning "load_rndbase falhou (personas podem estar vazias)."
    fi

    bootstrap_suggestion_chips

    if ! curl -s -f "http://localhost:${API_HOST_PORT}/api/suggestions" > /dev/null; then
        warning "GET /api/suggestions não respondeu (frontend usa fallback)."
    else
        success "GET /api/suggestions OK."
    fi

    response=$(curl -s -X POST "http://localhost:${API_HOST_PORT}/api/process-message" -H "Content-Type: application/json" -d '{"user_message": "teste"}' 2>/dev/null)
    if ! echo "$response" | grep -q "success\|error"; then
        warning "Endpoint /api/process-message inesperado: $response"
    else
        success "Endpoint /api/process-message OK."
    fi

    (cd deploy && (docker compose -f 033_aiclaudia_dComposer.yml ps || docker-compose -f 033_aiclaudia_dComposer.yml ps))
    echo ""
    success "aiClaudia está rodando (local)."
    echo "  Frontend: http://localhost:8082"
    echo "  API:      http://localhost:${API_HOST_PORT}"
    echo "  DB:       localhost:5434"
}

# ---------- Main ----------
case "${1:-}" in
    deploy) do_deploy ;;
    refresh-chips) do_refresh_chips ;;
    ingest)
        # Só atualiza o RAG no portal (sem subir containers). Ex.: ./start_aiclaudia.sh ingest
        if ! load_env; then
            error "Nenhum de: deploy/config.env ou deploy/env.prod encontrado."
        fi
        ingest_rag
        ;;
    *) do_start ;;
esac
