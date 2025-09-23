# Estrutura Técnica - aiClaudia

## Arquitetura Geral

O projeto utiliza uma arquitetura de microserviços containerizados com Docker Compose, separando frontend, API e banco de dados.

## Estrutura de Pastas

```
aiclaudia/
├── deploy/                 # Configurações e backend
│   ├── 033_aiclaudia_dComposer.yml
│   ├── Dockerfile
│   ├── config.env
│   ├── init.sql
│   ├── api_server.py
│   ├── simple_prompt_selector.py
│   ├── load_rndbase.py
│   └── rndbase_prompts.json
├── front/                  # Frontend
│   ├── style.css
│   └── main.js
├── img/                    # Assets
│   └── favicon_iclaudia.png
├── tokens/                 # Chaves de API
│   └── geminiKey.txt
├── documents/              # Documentação
├── index.html              # Página principal
├── start_iclaudia.sh       # Script de inicialização
└── stop_iclaudia.sh        # Script de parada
```

## Componentes Principais

### Frontend (Nginx)
- **Porta**: 8081
- **Tecnologia**: HTML, CSS, JavaScript, Bootstrap 5, Material Icons
- **Funcionalidades**: Interface de consulta, rate limiting frontend, modal de respostas

### API (Flask)
- **Porta**: 5000
- **Tecnologia**: Python, Flask, Flask-CORS
- **Endpoints**:
  - `POST /api/process-message` - Processa mensagens do usuário
  - `GET /api/msgs` - Lista mensagens do banco
  - `POST /api/log-block` - Registra bloqueios de rate limit
  - `GET /api/health` - Health check

### Banco de Dados (PostgreSQL)
- **Porta**: 5433
- **Tabelas**:
  - `requests` - Registro de consultas
  - `rndbase` - Prompts surrealistas
  - `rate_limits` - Controle de rate limiting
  - `ai_helpers` - Configuração das APIs
  - `logs` - Logs do sistema

## Sistema de Prompts

### Premissas do Sistema
- **Persona**: aiClaudia, mulher com visão humanitária e inclusiva
- **Limite de caracteres**: 24-300 caracteres por resposta
- **Dosimetria**: Evita repetir o último prompt usado
- **Rate limiting**: 3 requests/3min (frontend), 10 requests/5min (backend)
- **Fallback**: Gemini como principal, ChatGPT como backup

### Categorias de Prompts
- Nuvem preguiçosa, discurso heroico, haicai sistema
- Assistente cansada, sermão épico, profecia mística
- Slogan publicitário, herói cansado, carta poética
- Motivacional absurdo, aiClaudia consciente, guardiã das nuvens
- Auditório absurdo, diário secreto, entidade dissimulada
- Revista editorial, horóscopo, dicas, moda, cartas
- Tigresa oráculo, gata rainha, gata bugada, gata memes, felina psicanalista

## Integração com APIs

### Gemini API
- **Modelo**: gemini-2.0-flash
- **Uso**: Principal para geração de respostas
- **Configuração**: Via variável de ambiente

### ChatGPT API
- **Modelo**: gpt-3.5-turbo
- **Uso**: Fallback quando Gemini falha
- **Configuração**: Via variável de ambiente

## Rate Limiting

### Frontend
- **Método**: localStorage
- **Limite**: 3 requests em 3 minutos
- **Mensagem**: "Tô cansada, tem nuvem no céu hoje não, volta daqui 5min!"

### Backend
- **Método**: PostgreSQL
- **Limite**: 10 requests em 5 minutos
- **Tabela**: rate_limits

## Exposição Pública

### Cloudflare Tunnel
- **Domínio**: aiclaudia.com.br, www.aiclaudia.com.br
- **Rotas**:
  - `/api/*` → API Flask (porta 5000)
  - `/*` → Frontend Nginx (porta 8081)

## Scripts de Gerenciamento

### start_iclaudia.sh
- Carrega variáveis de ambiente
- Para containers existentes
- Constrói e inicia containers
- Executa testes de conectividade
- Valida todos os endpoints

### stop_iclaudia.sh
- Para e remove containers
- Remove volumes e redes
- Limpeza completa do ambiente
