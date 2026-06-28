# aiClaudia RAG corpus (for ai2tcs)

Portuguese copy is intentional (Brazilian public + tone).

## Layout

| File | Role |
|------|------|
| `instrucoes-llm.md` | **Request-time** behavior (ai2tcs `behavior_instruction_path`) — not vector RAG |
| `01_world_and_satire.md` | World boundaries (optional ingest if RAG re-enabled) |
| `02_voice_and_politics.md` | Short ingest summary; full rules in `instrucoes-llm.md` |
| `04_metaphors_and_lexicon.md` | Recurring metaphors (optional ingest) |
| `06_examples.md` | Anti-exemplos — what NOT to copy |
| `docs_03_prompt_system.md` | Human docs only (not auto-ingested) |
| `docs_05_personas.md` | Human persona guide (rndbase handles live modes) |

## ai2tcs (portal — llm.webplace.cc)

Projeto: `aiclaudia` (`LLM_PROJECT_ID`). Creative profile with **`rag_mode: disabled`** — persona via client `system_prompt` + rndbase; world via `instrucoes-llm.md`.

1. Seed: `cd ~/Documents/projects/ai2tcs/llm_api && DATABASE_URL=postgresql://llmapi:llmapi_dev@localhost:5437/llmapi python3 scripts/seed_aiclaudia.py`
2. Ingest (only if re-enabling vector RAG later): `./rag/ingest_llm.sh`
3. Eval: `python3 scripts/eval_rag.py --project aiclaudia` (from `llm_api/`)

Default model alias in client env: **`smart`** (gemma3:12b); greetings route to `fast`.
