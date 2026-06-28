# Deploy e operações — aiClaudia

## Produção

| Item | Valor |
|------|--------|
| Domínio | aiclaudia.com.br, www.aiclaudia.com.br |
| Servidor | itcsVM2 (Oracle, 136.248.79.126) — SSH: `itcsVM2` |
| Path no servidor | `/home/opc/033_aiClaudia` (rsync; sem git no host) |
| Frontend (nginx container) | host `:8082` → nginx nativo `:443` |
| API (Flask container) | host `:5001` → proxy `/api/*` |
| PostgreSQL | container `aiclaudia_db`, host `:5434` (local dev) |

Nginx nativo no itcsVM2 usa fragmento separado `/etc/nginx/conf.d/aiclaudia.conf` (não misturar com deploy BikeAnjo). SSL Let's Encrypt; Cloudflare Proxied.

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

## LLM (ai2tcs — llm.webplace.cc)

Claudia fala **só** pela LLM pessoal: `LLM_API_URL=https://llm.webplace.cc`, `LLM_API_TOKEN`, `LLM_PROJECT_ID=aiclaudia`. Com o trio definido a API usa só ITCS `/ask`; `LLM_DISABLE_COMMERCIAL=1` bloqueia Gemini/ChatGPT mesmo sem token. Fluxo: `POST /ask` → poll `GET /status/{job_id}` → `GET /result/{job_id}` (Bearer).

Health do portal: `curl -s https://llm.webplace.cc/health`.

Corpus opcional: pasta `rag/` (ver `rag/README.md`). Projeto ai2tcs: `prompt_profile: creative`, `rag_mode: disabled`, `behavior_instruction_path: instrucoes-llm.md`.

## Calibração Claudia

| Item | Valor recomendado |
|------|-------------------|
| `LLM_MODEL_ALIAS` | `smart` (default); saudações curtas usam `fast` no código |
| `rag_mode` (ai2tcs DB) | `disabled` |
| Seed | `python3 llm_api/scripts/seed_aiclaudia.py` |
| Eval | `python3 llm_api/scripts/eval_rag.py --project aiclaudia` |
| Ingest vector | Só se reativar RAG: `./start_aiclaudia.sh ingest` |

Checklist após mudanças de prompt/RAG:

1. Re-seed ai2tcs e confirmar `rag_mode: disabled` no dashboard ou via SQL.
2. Reiniciar stack local: `./start_aiclaudia.sh`
3. Eval verde no projeto `aiclaudia`.
4. Smoke: resposta sem meta-texto (`Voz aiClaudia`, `Com base no contexto`).

## Health checks

```bash
curl -sI https://aiclaudia.com.br
curl -s https://aiclaudia.com.br/api/health
ssh itcsVM2 'docker ps --filter name=aiclaudia; systemctl is-active nginx'
```

## Footer — link webplace + tracking `origin`

Rodapé do site aponta para `https://webplace.cc/?origin=aiclaudia`. Cliques disparam `outbound_click` no GA4 do aiClaudia (`G-0SSHXB16EN`).

No webplace.cc, `analytics.js` lê `?origin=` e envia evento `inbound_origin` + `campaign_source` no GA4 (`G-SJMKHC5H5C`). Fonte: repo `ianthomaz/webplace_mainSite` → pasta `webplace_Apex/`.

**GA4 Admin (webplace, one-time):** Admin → Custom definitions → Create custom dimension → Scope: Event → Parameter name: `origin`. Sem isso o parâmetro chega nos eventos mas demora a aparecer nos relatórios (~24h).

Após deploy de `analytics.js`, purgar cache Cloudflare do arquivo `/analytics.js` se a CDN servir versão antiga.

## Suggestion chips (notícias + cron)

Pool de perguntas nos chips do chat. Feeds em [`deploy/news_feeds.json`](../deploy/news_feeds.json) (internacional, política, moda, artes, esporte, dança, teatro, música, ciência, sociedade).

| Comando | Efeito |
|---------|--------|
| `./start_aiclaudia.sh` | Sobe stack + seed se pool pequeno |
| `./start_aiclaudia.sh refresh-chips` | 2× LLM (5+5 chips) + local fill se faltar + desativa chips >3 meses (soft) |
| `GET /api/suggestions` | 4 chips aleatórios ativos (mix de tópicos) |

Cron no Mac (2x/semana, segunda e quinta 6h):

```cron
0 6 * * 1,4 cd /Users/ianthomaz/Documents/projects/033_aiClaudia && ./scripts/refresh_suggestion_chips.sh >> /tmp/aiclaudia-chips.log 2>&1
```

Chips com mais de 3 meses ficam `is_active = FALSE` (nunca deletados). Editar feeds: `deploy/news_feeds.json` sem mudar código.

## Notas

- Build corre no host de deploy (mini62); itcsVM2 só corre containers.
- `aiclaudia_db` parado em prod não impede respostas se a API não depender do Postgres naquele momento; para sessões/histórico o DB deve estar Up.
- Certificado SSL expira periodicamente — renovar com certbot no itcsVM2.
