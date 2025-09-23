#!/bin/bash

# ☁️👜 aiClaudia - Stop Script
# Para todos os serviços

set -e

echo "🛑 Parando ☁️👜 aiClaudia..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Verificar se estamos no diretório correto
if [ ! -f "deploy/033_aiclaudia_dComposer.yml" ]; then
    echo -e "${RED}[ERROR]${NC} Execute este script a partir do diretório raiz do projeto!"
    exit 1
fi

# Parar containers
log "Parando containers..."
cd deploy
docker compose -f 033_aiclaudia_dComposer.yml down

success "☁️👜 aiClaudia parado com sucesso!"
