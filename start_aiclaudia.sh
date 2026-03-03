#!/bin/bash

# aiClaudia - Start (local) ou Deploy (via SSH para BikeAnjoVM)
# Uso:
#   ./start_aiclaudia.sh           # inicia local (deploy/config.env ou deploy/env.prod)
#   ./start_aiclaudia.sh deploy   # deploy remoto: sync, config, nginx, start no servidor

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
    for var in DB_PASSWORD GEMINI_API_KEY CHATGPT_API_KEY; do
        if [ -z "${!var}" ]; then
            error "Variável $var não está definida (deploy/config.env ou deploy/env.prod)."
        fi
    done
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
        echo "NGINX_HOST=${NGINX_HOST:-www.aiclaudia.com.br}"
        echo "FLASK_DEBUG=${FLASK_DEBUG:-False}"
        echo "API_PORT=${API_PORT:-5000}"
    } | ssh $SSH_OPTS "$SSH_TARGET" "cat > ${DEPLOY_REMOTE_PATH}/deploy/config.env"
    success "config.env escrito no servidor."

    log "Instalando nginx fragment (aiclaudia.conf, separado do BikeAnjo)..."
    scp $SSH_OPTS deploy/aiclaudia.nginx.conf "${SSH_TARGET}:/tmp/aiclaudia.conf"
    ssh $SSH_OPTS "$SSH_TARGET" "sudo mv /tmp/aiclaudia.conf /etc/nginx/conf.d/aiclaudia.conf && sudo chown root:root /etc/nginx/conf.d/aiclaudia.conf && sudo chmod 644 /etc/nginx/conf.d/aiclaudia.conf && (sudo restorecon /etc/nginx/conf.d/aiclaudia.conf 2>/dev/null || sudo chcon -t httpd_config_t /etc/nginx/conf.d/aiclaudia.conf 2>/dev/null) && sudo nginx -t && sudo systemctl reload nginx" || warning "Nginx reload falhou (confira /etc/nginx/conf.d/aiclaudia.conf no servidor)."
    success "Nginx atualizado (arquivo aiclaudia.conf não é alterado pelo deploy BikeAnjo)."

    log "Iniciando aiClaudia no servidor..."
    ssh $SSH_OPTS "$SSH_TARGET" "cd ${DEPLOY_REMOTE_PATH} && ./start_aiclaudia.sh" || error "Falha ao rodar start no servidor."
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
    if ! curl -s -f http://localhost:5001/api/health > /dev/null; then
        error "API (5001) não está respondendo."
    fi
    success "API OK."
    if ! docker exec aiclaudia_db pg_isready -U aiclaudia -d aiclaudia > /dev/null 2>&1; then
        error "PostgreSQL não está respondendo."
    fi
    success "PostgreSQL OK."

    response=$(curl -s -X POST http://localhost:5001/api/process-message -H "Content-Type: application/json" -d '{"user_message": "teste"}' 2>/dev/null)
    if ! echo "$response" | grep -q "success\|error"; then
        warning "Endpoint /api/process-message inesperado: $response"
    else
        success "Endpoint /api/process-message OK."
    fi

    (cd deploy && (docker compose -f 033_aiclaudia_dComposer.yml ps || docker-compose -f 033_aiclaudia_dComposer.yml ps))
    echo ""
    success "aiClaudia está rodando (local)."
    echo "  Frontend: http://localhost:8082"
    echo "  API:      http://localhost:5001"
    echo "  DB:       localhost:5434"
}

# ---------- Main ----------
if [ "${1:-}" = "deploy" ]; then
    do_deploy
else
    do_start
fi
