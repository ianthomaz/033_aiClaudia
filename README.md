# aiClaudia

Hub ITCS: manifest `itcsManifest.yaml` — contrato em 0MM_ITCS `docs/21_project_hub_contract.md`


Versão brasileira satírica do iCloud: a Claudia guarda tudo na nuvem e responde com humor surreal e poético.

Site público: **https://aiclaudia.com.br**

## O que é

- Interface simples (pergunta + resposta).
- Personalidade fixa por sessão (26 “modos” no `rndbase`).
- Rate limiting frontend e backend.
- IA **só** via LLM pessoal (ai2tcs/itcs em `llm.webplace.cc`, RAG em `rag/`); Gemini/ChatGPT desativados.

## Documentação

| Ficheiro | Conteúdo |
|----------|----------|
| `documents/01_structure.md` | Arquitetura, portas, API, prompts |
| `documents/02_roadmap.md` | Roadmap |
| `documents/03_sessions_system.md` | Sessões e contexto |
| `documents/06_deploy_and_ops.md` | Deploy prod (itcsVM2) e local |
| `rag/README.md` | Corpus para ingest ai2tcs |

## Quick start (local)

```bash
cp deploy/env.prod.example deploy/config.env
# editar DB_PASSWORD e chaves de IA
./start_aiclaudia.sh
# → http://localhost:8082
```

## Deploy produção

```bash
cp deploy/env.prod.example deploy/env.prod
# preencher env.prod (SSH + secrets)
./start_aiclaudia.sh deploy
```

Servidor: itcsVM2 (`/home/opc/033_aiClaudia`). Ver `documents/06_deploy_and_ops.md`.

## Repositório

GitHub: `ianthomaz/033_aiClaudia`

---

Criado por Fernando Falcon & Ian Thomaz — coworkingsolution.com
