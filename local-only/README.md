# local-only

Not committed (see root `.gitignore`).

## Cursor chat transcripts

Run from repo root:

```bash
chmod +x local-only/copy_cursor_transcript.sh
./local-only/copy_cursor_transcript.sh
```

Copies `~/.cursor/projects/*/agent-transcripts/*.jsonl` into `local-only/cursor-transcripts/` with a slug prefix so names do not collide.

If a transcript contains API keys, **do not** commit this folder; keep it local or redact before sharing.
