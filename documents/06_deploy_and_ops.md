# Deploy e operações — aiClaudia

## Produção

| Item | Valor |
|------|--------|
| Domínio | aiclaudia.com.br, www.aiclaudia.com.br |
| Servidor | BikeAnjoVM (Oracle, 136.248.79.126) — SSH: `BikeAnjoVM` |
| Path no servidor | `/home/opc/033_aiClaudia` (rsync; sem git no host) |
| Frontend (nginx container) | host `:8082` → nginx nativo `:443` |
| API (Flask container) | host `:5001` → proxy `/api/*` |
| PostgreSQL | container `aiclaudia_db`, host `:5434` (local dev) |

Nginx nativo no BikeAnjoVM usa fragmento separado `/etc/nginx/conf.d/aiclaudia.conf` (não misturar com deploy BikeAnjo). SSL Let's Encrypt; Cloudflare Proxied.

## Deploy a partir do mini62

1. Copiar `deploy/env.prod.example` → `deploy/env.prod` (não commitado).
2. Preencher `DB_PASSWORD`, chaves de IA ou trio ITCS (`LLM_API_URL`, `LLM_API_TOKEN`, `LLM_PROJECT_ID`).
3. Definir `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_REMOTE_PATH` (default `/home/opc/033_aiClaudia`).

```bash
./start_aiclaudia.sh deploy
```

O script: rsync do repo (exclui `.git`, envs locais) → escreve `deploy/config.env` no servidor → copia `aiclaudia.nginx.conf` → `nginx -t && reload` → `./start_aiclaudia.sh` remoto (docker compose up).

## Local

```bash
cp deploy/env.prod.example deploy/config.env   # ou env.prod
# preencher DB_PASSWORD e IA
./start_aiclaudia.sh
```

URLs locais: frontend `http://localhost:8082`, API `http://localhost:5001`, Postgres `localhost:5434`.

## LLM (ai2tcs)

Com `LLM_API_URL` + `LLM_API_TOKEN` + `LLM_PROJECT_ID` definidos, a API usa só ITCS `/ask` (Gemini/ChatGPT ficam fallback ou bloqueados).

Corpus RAG para ingest: pasta `rag/` (ver `rag/README.md`). Projeto sugerido: `aiclaudia`.

## Health checks

```bash
curl -sI https://aiclaudia.com.br
curl -s https://aiclaudia.com.br/api/health
ssh BikeAnjoVM 'docker ps --filter name=aiclaudia; systemctl is-active nginx'
```

## Notas

- Build corre no host de deploy (mini62); BikeAnjoVM só corre containers.
- `aiclaudia_db` parado em prod não impede respostas se a API não depender do Postgres naquele momento; para sessões/histórico o DB deve estar Up.
- Certificado SSL expira periodicamente — renovar com certbot no BikeAnjoVM.
