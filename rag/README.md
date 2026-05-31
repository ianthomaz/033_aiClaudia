# aiClaudia RAG corpus (for ai2tcs)

Markdown sources for **ingest** into the ITCS LLM API (`project_id` e.g. `aiclaudia`). Portuguese copy is intentional (Brazilian public + tone).

## Layout

| File | Role |
|------|------|
| `01_world_and_satire.md` | What this experiment is, boundaries, humour |
| `02_voice_and_politics.md` | Political/social voice, inclusive language |
| `03_prompt_system.md` | Random category instructions + sessions (no code) |
| `04_metaphors_and_lexicon.md` | Recurring metaphors (cloud, backup, “Cláudia”) |

## ai2tcs

1. Point the project `sources` at this `rag/` directory (or a copy on the llm_server).
2. Run `POST /ingest` (or your usual ingest pipeline).
3. Set `rag_mode` for the project per ai2tcs docs when you want retrieval on every `/ask`.

The Flask app still sends a **short** `system_prompt` prefix + `question`; retrieved chunks add depth. Keep `rndbase_prompts.json` for the random “genre” line.
