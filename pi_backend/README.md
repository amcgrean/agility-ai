# Pi Backend

These files mirror the backend currently deployed on the Raspberry Pi alongside the React UI.

Contents:
- `server.py`: FastAPI app, chat persistence, engagement logging, per-user conversation scoping, and training-consent/export endpoints
- `providers.py`: OpenAI-backed answer formatting and auto-title generation
- `cleanup_non_user_conversations.py`: one-off cleanup script used to remove legacy local/test chat data
- `scripts/ingest_agility_docs.py`: normalizes local HTML, PDF, and DOCX sources into chunk-ready JSONL outputs

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

## Local doc ingestion

The repo now includes a production-leaning ingestion pipeline for mixed local source folders that contain:
- scraped HTML portal pages
- local PDFs
- local DOCX guides
- training/video wrapper pages exported from the portal

The pipeline is:

```text
raw docs -> extract machine-readable text -> normalize/clean -> detect sections where available
-> chunk into retrieval-ready units -> attach provenance metadata -> write JSONL outputs
-> embed cleaned chunks -> build/update FAISS index
```

Example command:

```bash
python pi_backend/scripts/ingest_agility_docs.py --source-dir "C:\Users\indha\OneDrive - Beisser Lumber\Agility\wedge scrape" --out-dir "C:\Users\indha\python\agility ai\pi_backend\ingest_output\wedge_scrape"
```

Outputs:
- `normalized_docs.jsonl`: cleaned document/page/section units with provenance
- `doc_chunks.jsonl`: retrieval chunks with stable IDs and citation metadata
- `mcp_resources.jsonl`: MCP-ready resource rows for the same chunks
- `ingestion_manifest.json`: per-file processing status, hashes, dedupe signals, and counts

Chunk metadata now includes:
- `chunk_id`
- `chunk_hash`
- `doc_id`
- `corpus_name`
- `source_title`
- `source_file`
- `source_path`
- `source_type`
- `source_format`
- `doc_type`
- `content_domain`
- `access_scope`
- `ocr_applied`
- `source_url`
- `deep_link`
- `section_title`
- `page_start`
- `page_end`
- `last_processed_at`

Design notes:
- raw source files are never modified
- machine-readable extraction is used first; OCR is only attempted when PDF text is nearly empty and OCR dependencies are installed
- PDFs preserve page boundaries
- HTML extraction prefers article detail content and falls back to training/video page layouts
- repeated PDF margin lines are stripped when they look like headers/footers
- standalone PDF page-number artifacts are stripped where practical
- chunking is section-aware where source structure is available, with page/paragraph fallback
- duplicate files are detected by file hash, and chunk-level duplicates are suppressed with `chunk_hash`
- every record is tagged with `corpus_name`, `content_domain`, and `access_scope` so future internal/product/building corpora can be filtered without redesigning the schema

Notes:
- `.html`, `.pdf`, and `.docx` are processed now.
- legacy `.doc`, `.dotx`, and `.pptx` files are skipped.
- image-only or missing PDFs are reported in `ingestion_manifest.json` for follow-up.
- re-runs can skip unchanged files with `--skip-unchanged`.

Current known limitations:
- OCR fallback requires `pytesseract`, `Pillow`, and a working `tesseract` binary on the machine
- some PDF text still contains source encoding artifacts
- deep links are best for HTML/training pages today; PDFs use `agility://...` resource URIs unless a source URL exists

## Build the retrieval index

Once `doc_chunks.jsonl` exists and `OPENAI_API_KEY` is available, build the backend retrieval files with:

```bash
python pi_backend/scripts/build_doc_index.py --chunks-file "C:\Users\indha\python\agility ai\pi_backend\ingest_output\wedge_scrape\doc_chunks.jsonl" --out-dir "C:\Users\indha\python\agility ai\pi_backend" --mcp-export-file "C:\Users\indha\python\agility ai\pi_backend\ingest_output\wedge_scrape\mcp_resources.jsonl"
```

Outputs:
- `agility.index`: FAISS cosine-similarity index
- `agility_meta.jsonl`: chunk metadata consumed by `server.py`, preserving the richer citation fields
- `mcp_resources.jsonl`: MCP-friendly resource export for the same chunks

## One-command refresh

If you set these env vars:
- `AGILITY_DOC_SOURCE_DIR`
- `AGILITY_DOC_OUTPUT_DIR`
- `AGILITY_DOC_CHUNKS_FILE` (optional if using the default output path)
- `AGILITY_MCP_EXPORT_FILE` (optional)

you can refresh the pipeline with:

```bash
python pi_backend/scripts/refresh_agility_docs.py
```

or skip unchanged files during repeat batch loads:

```bash
python pi_backend/scripts/refresh_agility_docs.py --skip-unchanged
```

Behavior:
- always reruns ingestion
- supports manifest-based change detection with `--skip-unchanged`
- builds the FAISS index only when both `faiss` and `OPENAI_API_KEY` are available
- safely stops after ingestion otherwise

## MCP server

The repo now includes a simple MCP server over the exported corpora:

```bash
python pi_backend/scripts/agility_mcp_server.py --transport stdio
```

It reads `AGILITY_MCP_EXPORT_FILE` when set, or falls back to `pi_backend/ingest_output/*/mcp_resources.jsonl`.

Current MCP capabilities:
- `search_docs`: keyword-weighted search across all exported corpora
- `get_doc_chunk`: fetch a specific `agility://docs/.../chunk/...` record
- `list_doc_chunks`: browse all chunk URIs for a document
- `corpus_stats`: inspect loaded corpus coverage
- resource reads for `agility://docs/{doc_id}/chunk/{chunk_id}`

This is designed so future internal, product, and building-doc corpora can be added just by generating more `mcp_resources.jsonl` files and pointing the server at them.

Search filters now support:
- `corpus_name`
- `content_domain`
- `access_scope`
- `source_type`
- `portal_section`

## Admin reindexing

The backend now supports admin-triggered retrieval refreshes:

- `GET /admin/retrieval-status`
- `POST /admin/reindex`

Both endpoints require the same bearer token used by `ADMIN_EXPORT_TOKEN`.

Example payload for `POST /admin/reindex`:

```json
{
  "sourceDir": "C:\\Users\\indha\\OneDrive - Beisser Lumber\\Agility\\wedge scrape",
  "outputDir": "C:\\Users\\indha\\python\\agility ai\\pi_backend\\ingest_output\\wedge_scrape_v4",
  "corpusName": "wedge_scrape",
  "skipUnchanged": true
}
```

Useful flags:
- `reloadOnly`: reload `agility.index` and `agility_meta.jsonl` without running ingestion
- `skipIndex`: rerun ingestion only
- `skipUnchanged`: avoid reprocessing files whose hash matches the previous manifest
