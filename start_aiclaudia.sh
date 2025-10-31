#!/bin/bash

# ☁️👜 aiClaudia - Startup Script
# Inicia todos os serviços e executa testes

set -e  # Parar em caso de erro

echo "🚀 Iniciando ☁️👜 aiClaudia..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verificar se estamos no diretório correto
if [ ! -f "deploy/033_aiclaudia_dComposer.yml" ]; then
    error "Execute este script a partir do diretório raiz do projeto!"
    exit 1
fi

# Carregar variáveis de ambiente
log "📋 Carregando variáveis de ambiente..."
if [ -f "deploy/config.env" ]; then
    export $(grep -v '^#' deploy/config.env | xargs)
    success "Variáveis carregadas de deploy/config.env"
else
    error "Arquivo deploy/config.env não encontrado!"
    exit 1
fi

# Verificar variáveis obrigatórias
log "🔍 Verificando variáveis obrigatórias..."
required_vars=("DB_PASSWORD" "GEMINI_API_KEY" "CHATGPT_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        error "Variável $var não está definida!"
        exit 1
    fi
done
success "Todas as variáveis obrigatórias estão definidas"

# Parar containers existentes
log "🛑 Parando containers existentes..."
cd deploy
docker-compose -f 033_aiclaudia_dComposer.yml down 2>/dev/null || true

# Construir e iniciar containers
log "🔨 Construindo e iniciando containers..."
docker-compose -f 033_aiclaudia_dComposer.yml up --build -d

# Aguardar serviços ficarem prontos
log "⏳ Aguardando serviços ficarem prontos..."
sleep 10

# Testes de conectividade
log "🧪 Executando testes de conectividade..."

# Teste 1: Nginx (Frontend)
log "Testando Nginx (porta 8082)..."
if curl -s -f http://localhost:8082 > /dev/null; then
    success "✅ Nginx está respondendo"
else
    error "❌ Nginx não está respondendo"
    exit 1
fi

# Teste 2: API Flask
log "Testando API Flask (porta 5001)..."
if curl -s -f http://localhost:5001/api/health > /dev/null; then
    success "✅ API Flask está respondendo"
else
    error "❌ API Flask não está respondendo"
    exit 1
fi

# Teste 3: Database
log "Testando PostgreSQL..."
if docker exec aiclaudia_db pg_isready -U aiclaudia -d aiclaudia > /dev/null 2>&1; then
    success "✅ PostgreSQL está respondendo"
else
    error "❌ PostgreSQL não está respondendo"
    exit 1
fi

# Teste 4: API Endpoint
log "Testando endpoint /api/process-message..."
response=$(curl -s -X POST http://localhost:5001/api/process-message \
    -H "Content-Type: application/json" \
    -d '{"user_message": "teste"}' 2>/dev/null)

if echo "$response" | grep -q "success\|error"; then
    success "✅ Endpoint /api/process-message está funcionando"
else
    error "❌ Endpoint /api/process-message não está funcionando"
    echo "Resposta: $response"
    exit 1
fi

# Teste 5: API Endpoint /msgs
log "Testando endpoint /api/msgs..."
response=$(curl -s http://localhost:5001/api/msgs 2>/dev/null)

if echo "$response" | grep -q "success\|messages"; then
    success "✅ Endpoint /api/msgs está funcionando"
else
    warning "⚠️ Endpoint /api/msgs não está funcionando"
    echo "Resposta: $response"
fi

# Teste 6: Frontend carregando recursos
log "Testando carregamento de recursos do frontend..."
if curl -s -f http://localhost:8082/front/style.css > /dev/null; then
    success "✅ CSS está sendo servido"
else
    warning "⚠️ CSS não está sendo servido"
fi

if curl -s -f http://localhost:8082/front/main.js > /dev/null; then
    success "✅ JavaScript está sendo servido"
else
    warning "⚠️ JavaScript não está sendo servido"
fi

# Status final
log "📊 Status dos containers:"
docker-compose -f 033_aiclaudia_dComposer.yml ps

echo ""
success "🎉 ☁️👜 aiClaudia está rodando!"
echo ""
echo "🌐 Frontend: http://localhost:8082"
echo "🔌 API: http://localhost:5001"
echo "🗄️ Database: localhost:5434"
echo ""
echo "📝 Comandos úteis:"
echo "  docker-compose -f deploy/033_aiclaudia_dComposer.yml logs -f    # Ver logs"
echo "  docker-compose -f deploy/033_aiclaudia_dComposer.yml down       # Parar"
echo "  docker-compose -f deploy/033_aiclaudia_dComposer.yml restart    # Reiniciar"
echo ""
