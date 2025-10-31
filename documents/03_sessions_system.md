# 🎭 Sistema de Sessões - aiClaudia

## 📋 O que foi implementado

### ✅ Features Completas:

1. **Sessões Persistentes**
   - Cada usuário recebe um `session_id` único (UUID)
   - Sessão armazenada no `localStorage` do navegador
   - Sessão persiste entre recarregamentos da página

2. **Personalidade Fixa por Sessão**
   - Ao entrar, sistema escolhe 1 das 26 personalidades
   - Claudia mantém ESSA personalidade durante toda a sessão
   - Não muda aleatoriamente entre mensagens

3. **Contexto de Conversa**
   - Sistema mantém histórico das últimas 5 mensagens
   - AI recebe contexto das últimas 3 mensagens no prompt
   - Permite respostas mais contextualizadas e coerentes

4. **Rastreamento no Banco**
   - Tabela `sessions`: gerencia sessões ativas
   - Tabela `requests`: vincula mensagens à sessão
   - Possibilita analytics por sessão

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (localStorage)                                    │
│  - Armazena session_id                                      │
│  - Envia session_id em cada request                         │
│  - Recebe e atualiza session_id                             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  API (/api/process-message)                                 │
│  - Recebe: user_message + session_id                        │
│  - Retorna: response + session_id + is_new_session          │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (simple_prompt_selector.py)                        │
│                                                             │
│  1. get_session_prompt()                                    │
│     - Se session_id existe → busca personalidade da sessão  │
│     - Se não existe → cria nova sessão com prompt aleatório │
│                                                             │
│  2. add_message_to_history()                                │
│     - Adiciona user + assistant ao histórico JSON           │
│     - Mantém apenas últimas 5 mensagens                     │
│                                                             │
│  3. Prompt enviado à IA:                                    │
│     PREMISSA + PERSONALIDADE + CONTEXTO + USER_MESSAGE      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  DATABASE (PostgreSQL)                                      │
│                                                             │
│  sessions                     requests                      │
│  - session_id (PK)            - request_id (PK)             │
│  - user_ip                    - session_id (FK)             │
│  - current_personality        - user_ip                     │
│  - message_history (JSONB)    - original_msg                │
│  - created_at                 - ai_response                 │
│  - last_activity              - prompt_category             │
│  - is_active                  - platform_used               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Fluxo de Uso

### Primeiro Acesso:
```
1. Usuário entra no site
2. Frontend: session_id = null
3. Usuário envia mensagem
4. Backend:
   - Não encontra sessão
   - Cria nova sessão
   - Escolhe personalidade aleatória (ex: "gata_oraculo")
   - Gera UUID: "abc-123-def-456"
   - Retorna resposta + session_id + is_new_session=true
5. Frontend salva "abc-123-def-456" no localStorage
6. Console.log: "✨ Nova sessão criada: abc-123-def-456"
7. Console.log: "🎭 Personalidade: gata_oraculo"
```

### Segunda Mensagem (mesma sessão):
```
1. Usuário envia nova mensagem
2. Frontend envia session_id="abc-123-def-456"
3. Backend:
   - Encontra sessão
   - Usa mesma personalidade: "gata_oraculo"
   - Adiciona contexto da mensagem anterior
   - Prompt = PREMISSA + gata_oraculo + "Contexto: User: oi | You: miau"
4. AI responde mantendo personalidade
5. Backend salva mensagem no histórico
6. Retorna resposta + session_id + is_new_session=false
```

### Reset de Sessão:
```
1. Usuário abre console do navegador (F12)
2. Digite: resetSession()
3. localStorage limpo
4. Próxima mensagem = nova sessão + nova personalidade
```

---

## 📁 Arquivos Modificados

### Backend:
- `deploy/init.sql` - Adicionada tabela `sessions` e coluna `session_id` em requests
- `deploy/simple_prompt_selector.py` - Funções de gerenciamento de sessão
- `deploy/api_server.py` - Endpoint `/api/process-message` com suporte a sessions

### Frontend:
- `front/main.js` - Gerenciamento de session_id no localStorage

### Novos Arquivos:
- `deploy/migrate_add_sessions.sql` - Script de migração para bancos existentes

---

## 🚀 Como Testar

### Para Bancos Novos:
```bash
# O init.sql já contém a tabela sessions
./start_aiclaudia.sh
```

### Para Bancos Existentes:
```bash
# 1. Parar containers
./stop_aiclaudia.sh

# 2. Executar migração
docker exec -i aiclaudia_db psql -U aiclaudia -d aiclaudia < deploy/migrate_add_sessions.sql

# 3. Rebuild e restart
docker-compose -f deploy/033_aiclaudia_dComposer.yml up --build -d
```

### Testando no Navegador:
```javascript
// 1. Abrir console (F12)
// 2. Verificar session_id atual:
localStorage.getItem('aiclaudia_session_id')

// 3. Resetar sessão:
resetSession()

// 4. Enviar mensagens e observar console:
// ✨ Nova sessão criada: abc-123...
// 🎭 Personalidade: gata_rainha
```

---

## 🔍 Consultas SQL Úteis

### Ver todas as sessões ativas:
```sql
SELECT session_id, user_ip, current_personality,
       created_at, last_activity
FROM sessions
WHERE is_active = TRUE
ORDER BY last_activity DESC;
```

### Ver histórico de uma sessão específica:
```sql
SELECT * FROM requests
WHERE session_id = 'abc-123-def-456'
ORDER BY date_time_request;
```

### Ver personalidades mais usadas:
```sql
SELECT current_personality, COUNT(*) as sessions_count
FROM sessions
GROUP BY current_personality
ORDER BY sessions_count DESC;
```

### Ver mensagens de uma sessão com contexto:
```sql
SELECT
    s.current_personality,
    s.message_history,
    COUNT(r.request_id) as total_messages
FROM sessions s
LEFT JOIN requests r ON s.session_id = r.session_id
WHERE s.session_id = 'abc-123-def-456'
GROUP BY s.session_id, s.current_personality, s.message_history;
```

---

## 📊 Características Técnicas

### Contexto de Mensagens:
- **Armazenamento**: JSONB no PostgreSQL
- **Formato**:
```json
[
  {
    "user": "oi claudia",
    "assistant": "miau! sou a gata-oráculo",
    "timestamp": "2025-10-30T10:30:00"
  },
  {
    "user": "como você está?",
    "assistant": "contemplando o infinito felino",
    "timestamp": "2025-10-30T10:31:00"
  }
]
```
- **Limite**: Últimas 5 mensagens armazenadas
- **Uso no Prompt**: Últimas 3 mensagens enviadas à IA

### Performance:
- Índices criados:
  - `idx_sessions_user_ip` - Busca por IP
  - `idx_sessions_last_activity` - Cleanup de sessões antigas
  - `idx_requests_session_id` - Join requests ↔ sessions

---

## 🎯 Benefícios

1. **Experiência do Usuário**
   - Conversas mais coerentes
   - Claudia "lembra" do contexto
   - Personalidade consistente

2. **Analytics**
   - Rastrear sessões completas
   - Entender jornada do usuário
   - Métricas: duração média de sessão, mensagens por sessão

3. **Escalabilidade**
   - Preparado para multi-usuário
   - Fácil adicionar autenticação futura
   - Sistema modular

---

## 🔮 Próximos Passos (NÃO implementados ainda)

### Ideias para o Futuro:

1. **Mudança Dinâmica de Personalidade**
   - Claudia muda após 10 mensagens
   - Ou muda baseado em trigger (ex: usuário fala "quero falar com a gata rainha")
   - Sistema de "humor" que evolui

2. **Botão Visual de Reset**
   - "Começar nova conversa" na interface
   - Confirmação: "Quer mesmo mudar de personalidade?"

3. **Dashboard de Sessão**
   - Mostrar personalidade atual
   - Histórico visual das mensagens
   - Botão para exportar conversa

4. **Expiração de Sessões**
   - Auto-cleanup de sessões inativas (>24h)
   - Cronjob ou trigger no backend

5. **Sessões Autenticadas**
   - Login Google → sessões permanentes
   - Usuário pode revisar conversas antigas
   - Histórico ilimitado para usuários logados

---

## 🐛 Troubleshooting

### Sessão não persiste:
- Verificar se localStorage está habilitado no navegador
- Verificar console para erros
- Tentar `resetSession()` e começar nova conversa

### Personalidade mudando aleatoriamente:
- Verificar se session_id está sendo enviado: `localStorage.getItem('aiclaudia_session_id')`
- Verificar logs do backend para erros
- Checar se tabela sessions foi criada: `SELECT * FROM sessions;`

### Contexto não funciona:
- Verificar coluna `message_history` na tabela sessions
- Deve ser JSONB, não TEXT
- Verificar função `add_message_to_history()` nos logs

---

**Implementado por**: Claude Code
**Data**: 2025-10-30
**Status**: ✅ Completo e funcional
