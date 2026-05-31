# aiClaudia RAG corpus (for ai2tcs)

Markdown sources for **ingest** into the ITCS LLM API (`project_id` e.g. `aiclaudia`). Portuguese copy is intentional (Brazilian public + tone).

## Layout

| File | Role |
|------|------|
| `01_world_and_satire.md` | What this experiment is, boundaries, humour |
| `02_voice_and_politics.md` | Political/social voice, inclusive language |
| `03_prompt_system.md` | Random category instructions + sessions (no code) |
| `04_metaphors_and_lexicon.md` | Recurring metaphors (cloud, backup, “Cláudia”) |
| `05_personas.md` | Voice guide for the 25 real `category` modes (aligned to `rndbase_prompts.json`) |
| `06_examples.md` | Few-shot Q→A per category (style/length anchors) |

## ai2tcs (portal pessoal — llm.webplace.cc)

Projeto: `aiclaudia` (`LLM_PROJECT_ID`). Endpoint: `https://llm.webplace.cc`.

1. Garantir que o projeto `aiclaudia` existe no portal (dashboard → novo projeto).
2. Apontar as `sources` do projeto para este `rag/` (cópia no llm_server) **ou** usar o helper em modo upload.
3. Ingerir o corpus:

   ```bash
   LLM_API_URL=https://llm.webplace.cc LLM_API_TOKEN=xxx LLM_PROJECT_ID=aiclaudia \
     ./rag/ingest_llm.sh            # /ingest incremental (usa as sources do projeto)
   # ou, se preferir enviar os ficheiros:
   ./rag/ingest_llm.sh upload       # /ingest/upload de cada rag/*.md, depois rodar o ingest
   ```

4. Definir `rag_mode` do projeto (per docs ai2tcs) para ter recuperação em cada `/ask`.

O Flask manda só um `system_prompt` **curto** + `question`; os trechos recuperados dão profundidade. `rndbase_prompts.json` continua a dar a linha de “género” aleatório.
