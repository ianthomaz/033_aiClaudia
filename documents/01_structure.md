# Estrutura técnica — aiClaudia

## Arquitetura

Docker Compose com três serviços: frontend (nginx estático), API Flask, PostgreSQL. Em produção, nginx **nativo** no itcsVM2 faz TLS e proxy para os containers.

## Estrutura de pastas

```
033_aiClaudia/
├── deploy/                 # Backend, compose, nginx fragment prod
│   ├── 033_aiclaudia_dComposer.yml
│   ├── api_server.py
│   ├── simple_prompt_selector.py
│   ├── rndbase_prompts.json
│   ├── aiclaudia.nginx.conf   # fragmento para /etc/nginx/conf.d/ no host
│   └── env.prod.example
├── front/                  # CSS, JS, Lottie
├── dashboard/              # Admin simples (HTML)
├── rag/                    # Corpus markdown para ingest ai2tcs
├── documents/              # Documentação do projeto
├── local-only/             # Utilitários locais (transcripts Cursor)
├── index.html
├── start_aiclaudia.sh      # local start | deploy remoto
└── stop_aiclaudia.sh
```

## Portas (local / prod host)

| Serviço | Local | Prod (itcsVM2 host) |
|---------|-------|-------------------------|
| Frontend nginx | 8082 | 8082 → nginx :443 |
| API Flask | 5001 | 5001 |
| PostgreSQL | 5434 | (interno compose) |

## API (Flask)

- `POST /api/process-message` — mensagem do usuário (+ session_id)
- `GET /api/msgs` — histórico
- `POST /api/log-block` — rate limit frontend
- `GET /api/health` — health check

## Banco (PostgreSQL)

Tabelas principais: `requests`, `rndbase`, `rate_limits`, `sessions`, `ai_helpers`, `logs`. Sessões: ver `documents/03_sessions_system.md`.

## Sistema de prompts

- **Premissa curta** em código (`simple_prompt_selector.py`).
- **Gênero aleatório** por sessão a partir de `rndbase_prompts.json` / tabela `rndbase`.
- **Contexto**: últimas mensagens da sessão (JSONB).
- **Mundo / valores**: `rag/instrucoes-llm.md` via ai2tcs `behavior_instruction_path` (request-time, não vector).
- **Vector RAG**: desligado (`rag_mode: disabled`); corpus em `rag/` só para ingest opcional futuro.

## Provedores de IA

1. **LLM pessoal — ITCS / ai2tcs** (única em produção): `LLM_API_URL=https://llm.webplace.cc`, `LLM_API_TOKEN`, `LLM_PROJECT_ID=aiclaudia`. Fluxo `POST /ask` → poll `GET /status/{job_id}` → `GET /result/{job_id}` (Bearer); `model` aceita `fast|smart|compact|reasoner`.
2. **Gemini / ChatGPT** — desativados (`LLM_DISABLE_COMMERCIAL=1`); o código mantém o caminho só como contingência manual (`force_platform`).

## Rate limiting

- Frontend: localStorage, 3 req / 3 min.
- Backend: PostgreSQL `rate_limits`, 10 req / 5 min.

## Exposição pública

- Domínio: aiclaudia.com.br (Cloudflare Proxied).
- Origem: itcsVM2, nginx nativo + containers.
- Deploy: `./start_aiclaudia.sh deploy` — detalhes em `documents/06_deploy_and_ops.md`.

## Scripts

- `start_aiclaudia.sh` — local ou `deploy` via SSH/rsync.
- `stop_aiclaudia.sh` — para containers locais.
