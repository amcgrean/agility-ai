# Pi Backend

These files mirror the backend currently deployed on the Raspberry Pi alongside the React UI.

Contents:
- `server.py`: FastAPI app, chat persistence, engagement logging, per-user conversation scoping, and training-consent/export endpoints
- `providers.py`: OpenAI-backed answer formatting and auto-title generation
- `cleanup_non_user_conversations.py`: one-off cleanup script used to remove legacy local/test chat data

The frontend lives in `src/` and is built with Vite. The Pi serves the built static frontend from `ui/` using the backend above.

## Training data readiness

`server.py` now supports:
- per-user training consent APIs (`GET/PATCH /users/me/training-consent`)
- token-protected export endpoint (`GET /admin/training-export`) that only includes consented conversations
- basic PII redaction in exported content (emails/phone numbers)
- stable user hashing in exports using `TRAINING_EXPORT_SALT`

Set `ADMIN_EXPORT_TOKEN` in the backend environment to enable export access.


## Retrieval and cost optimization (new)

### What changed
- Two-stage retrieval: fetches a larger candidate pool from FAISS (`RETRIEVAL_TOP_K_CANDIDATES`) and then locally reranks/deduplicates to send only the best chunks (`FINAL_TOP_K`).
- Near-duplicate chunk suppression in a single answer context.
- Context-size guardrail with `MAX_CONTEXT_CHARS` to cap prompt bloat.
- Conversation-aware context building in `/ask` via `conversationId`:
  - includes only recent turns (`MAX_RECENT_MESSAGES`)
  - uses rolling summary memory (`memory_summary` column) for older turns
- Persistent SQLite answer cache DB (`agility_cache.db` by default) for repeated requests (`REQUEST_CACHE_TTL_SECONDS`) so cache survives backend restarts.
- Token usage + estimated cost returned by backend and logged for each `/ask` call.
- Debug mode (`ENABLE_DEBUG_MODE=true`) exposes selected chunks and retrieval scores in `/ask` response.

### New environment variables
- `OPENAI_API_KEY` (required)
- `CHAT_MODEL` (default: `gpt-5-mini`)
- `EMBED_MODEL` (default: `text-embedding-3-small`)
- `RETRIEVAL_TOP_K_CANDIDATES` (default: `10`)
- `FINAL_TOP_K` (default: `4`)
- `MAX_CONTEXT_CHARS` (default: `9000`)
- `MIN_RERANK_SCORE` (default: `0.1`)
- `MAX_RECENT_MESSAGES` (default: `6`)
- `CONVERSATION_SUMMARY_TRIGGER_MESSAGES` (default: `12`)
- `MAX_OUTPUT_TOKENS` (default: `700`)
- `REQUEST_CACHE_TTL_SECONDS` (default: `300`)
- `CACHE_DB_FILE` (default: `pi_backend/agility_cache.db`)
- `ENABLE_DEBUG_MODE` (`true`/`false`, default: `false`)
- `ENABLE_HYBRID_RETRIEVAL_HINT` (`true`/`false`, default: `true`)
- `OPENAI_REASONING_EFFORT` (`minimal` recommended for retrieval-heavy GPT-5 answers on Pi)
- `OPENAI_TEXT_VERBOSITY` (`low`/`medium`/`high`, default: `medium`)
- `INPUT_COST_PER_MILLION` (default: `0.25`)
- `OUTPUT_COST_PER_MILLION` (default: `2.0`)
- `ADMIN_EXPORT_TOKEN` (required only if using `/admin/training-export`)
- `TRAINING_EXPORT_SALT` (recommended if using exports)
- `EXPERT_USER_IDENTITIES` (comma-separated identities whose corrective follow-ups should be treated as higher-confidence feedback)
- `STAFF_USER_IDENTITIES` (comma-separated identities for medium-confidence trusted follow-up corrections)

### Migration notes
No destructive migration is required. On startup, the backend safely adds a nullable `memory_summary` column to `conversations` if missing. A separate cache SQLite DB is created automatically for request caching.

Do not replace the Pi `.env` wholesale from the template. Merge new keys into the existing file so current secrets like `OPENAI_API_KEY` are preserved.

## Git-backed Pi deployment

For a durable production setup, keep the Raspberry Pi app as a normal Git checkout and move machine-local state outside the repo:

- code checkout: `/home/amcgrean/agility-ai`
- env file: `/etc/agility-ai/agility.env`
- persistent app data: `/home/amcgrean/agility-ai-data`
- Pi-only helper scripts and virtualenv: `/home/amcgrean/agility-ai-local`

`server.py` supports these path overrides:

- `AGILITY_ENV_FILE` for the env file to load
- `AGILITY_DATA_DIR` for `agility_ai.db`, `agility_cache.db`, `agility.index`, and `agility_meta.jsonl`
- `AGILITY_UI_DIR` for the built frontend directory

Suggested systemd wiring:

- `WorkingDirectory=/home/amcgrean/agility-ai/pi_backend`
- `EnvironmentFile=/etc/agility-ai/agility.env`
- `Environment=AGILITY_DATA_DIR=/home/amcgrean/agility-ai-data`
- `Environment=AGILITY_UI_DIR=/home/amcgrean/agility-ai/dist`

That layout lets the Pi track `origin/main` cleanly while preserving secrets, indexes, and local utility scripts across deploys.

### Recommended defaults for Raspberry Pi 5
- Candidate retrieval: `RETRIEVAL_TOP_K_CANDIDATES=10`
- Final chunks sent to LLM: `FINAL_TOP_K=4`
- Max context size: `MAX_CONTEXT_CHARS=9000`
- Cache strategy: `REQUEST_CACHE_TTL_SECONDS=300`
- Follow-up memory: `MAX_RECENT_MESSAGES=6`, `CONVERSATION_SUMMARY_TRIGGER_MESSAGES=12`
