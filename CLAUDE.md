# Beisser AI — Claude Agent Notes

This file is read automatically by Claude Code at the start of every session.

---

## Agility Docs MCP (Local Knowledge Search)

An MCP server is wired into this project at `.claude/settings.json`. It gives Claude Code searchable access to all 2319 Agility documentation chunks (254 source documents) directly from the local `pi_backend/agility_meta.jsonl` file — no Pi connection needed.

**Available MCP tools:**
| Tool | What it does |
|------|-------------|
| `search_docs` | Keyword search across all Agility doc chunks. Supports filtering by `corpus_name`, `content_domain`, `portal_section`, `source_type`. |
| `get_doc_chunk` | Fetch full text of a specific chunk by its URI. |
| `list_doc_chunks` | Browse all chunks of a document sequentially by `doc_id`. |
| `corpus_stats` | See chunk counts, domains, portal sections, source types covered. |

**When to use it:** When a user asks something about Agility features, security, reports, GL/AR/AP setup, or any DMSI-specific process — search here before relying on general knowledge. Prefer `search_docs` with a specific keyword phrase.

**Corpus coverage:** product docs, training docs, internal docs (DMSI Guides, System Admins portal, Warehouse portal, Uncategorized). Does NOT include the 14-chunk Reporting Skill corpus (those are loaded separately in `server.py`).

**Limitation:** Uses token-overlap scoring (not vector search). Miss rate is higher on semantic queries — try alternate keyword phrasings if the first search is empty.

---

## Project Overview

**Beisser AI** is an internal RAG (Retrieval-Augmented Generation) chatbot for Beisser Lumber, built on a Raspberry Pi. It answers questions from the DMSI Agility documentation corpus and supports a specialized SQL Reporting Expert mode.

- **Live URL**: `agility.beisser.cloud`
- **GitHub**: `https://github.com/amcgrean/agility-ai` (branch: `main`)
- **Local path**: `C:\Users\indha\python\agility ai`
- **Stack**: React/Vite frontend + FastAPI/Python backend + FAISS vector search + SQLite + OpenAI

---

## Pi Deployment

### Connection
- SSH alias: `agility-ai-remote` (user: `amcgrean`) — pre-configured, just works
- Checkout dir: `/home/amcgrean/agility-ai`
- Data dir: `DATA_DIR` defaults to `/home/amcgrean/agility-ai/pi_backend` (no `AGILITY_DATA_DIR` env set)
- Env file: `/home/amcgrean/agility-ai-local/.env`
- Venv: `/home/amcgrean/agility-ai-local/.venv`
- Service: `agility-ai` (systemd, runs uvicorn on port 8000)

### Standard Deploy Process
**Always follow this exact sequence — do NOT `git pull` on the Pi (dirty state issues):**

```bash
# 1. Build frontend locally
npm run build

# 2. Package (dist/ → pi_backend/ui/, plus backend files)
python -c "
import zipfile
from pathlib import Path
base, out = Path('.'), Path('deploy.zip')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in (base / 'dist').rglob('*'):
        if f.is_file():
            zf.write(f, 'pi_backend/ui/' + str(f.relative_to(base/'dist')).replace(chr(92),'/'))
    for rel in ['pi_backend/server.py', 'pi_backend/providers.py',
                'pi_backend/ingest_output/agility_reporting_v1/chunks.jsonl']:
        zf.write(base / rel, rel)
"

# 3. SCP single file (stable even on flaky connections)
scp deploy.zip agility-ai-remote:/home/amcgrean/deploy.zip

# 4. Extract (wipe old assets first to avoid stale files)
ssh agility-ai-remote "rm -rf /home/amcgrean/agility-ai/pi_backend/ui/assets && cd /home/amcgrean/agility-ai && unzip -o /home/amcgrean/deploy.zip && rm /home/amcgrean/deploy.zip"

# 5. Restart
ssh agility-ai-remote "sudo systemctl restart agility-ai && sleep 3 && systemctl is-active agility-ai"

# 6. Verify
ssh agility-ai-remote "curl -s http://localhost:8000/health"
```

### After deploy, always push to GitHub too:
```bash
git add <files> && git commit -m "..." && git push origin main
```

---

## Architecture

### Backend (`pi_backend/`)
| File | Purpose |
|------|---------|
| `server.py` | FastAPI app — all endpoints, SQLite DB, FAISS retrieval, caching, analytics |
| `providers.py` | OpenAI wrapper — prompt building, LLM calls, corrections injection |
| `scripts/build_doc_index.py` | Builds FAISS index + `agility_meta.jsonl` from a chunks JSONL |
| `scripts/ingest_reporting_skill.py` | Ingests the reporting skill markdown files into chunks |

### Frontend (`src/`)
| File | Purpose |
|------|---------|
| `pages/ChatPage.jsx` | Main general chat UI |
| `pages/ReportingPage.jsx` | Reporting Expert mode (AgilitySQL schema specialist) |
| `pages/AdminPage.jsx` | Usage/cost dashboard (auto-loads for expert users) |
| `components/Sidebar.jsx` | Nav (General Chat / Reporting Expert) + conversation list |
| `hooks/useChat.js` | All conversation state, sendMessage, memory |
| `services/api.js` | All API calls to FastAPI backend |

### Key Endpoints
| Endpoint | Auth | Notes |
|----------|------|-------|
| `POST /ask` | none | Main Q&A. Accepts `mode: "default"\|"reporting"` |
| `GET /health` | none | Returns `retrievalReady`, `chunkCount` |
| `GET /admin/metrics` | expert user OR Bearer token | Dashboard data |
| `GET /admin/retrieval-status` | expert user OR Bearer token | Chunk counts |
| `POST /admin/reindex` | expert user OR Bearer token | Rebuild index |
| `GET /admin/training-export` | Bearer token only | Full training dataset |

---

## Knowledge Bases

### Main Corpus (Agility Docs)
- **Source**: Wedge scrape of DMSI Agility portal
- **Location on Pi**: `pi_backend/agility.index` + `pi_backend/agility_meta.jsonl`
- **Latest baseline**: `pi_backend/ingest_output/wedge_scrape_v5` (2319 chunks, 254 sources)
- **Ingestion script**: `pi_backend/scripts/refresh_agility_docs.py`

### Reporting Skill Corpus
- **Source**: Internal markdown files at `C:\Users\indha\OneDrive - Beisser Lumber\ai\skills\agility-reporting\`
- **Location**: `pi_backend/ingest_output/agility_reporting_v1/chunks.jsonl` (14 chunks, loaded directly — no FAISS)
- **Ingestion script**: `pi_backend/scripts/ingest_reporting_skill.py`
- **Loaded by**: `server.py` startup reads chunks directly into `reporting_meta` list

---

## Learning / Feedback Loop

The system actively learns from corrections:

1. Users submit corrections via thumbs-down or the correction UI
2. Corrections stored in `engagement_events` table (`event_type = 'response_correction_submitted'`)
3. On each `/ask` call, `get_relevant_corrections(question)` queries past corrections with word-overlap similarity (Jaccard > 0.2) and injects them into the LLM prompt
4. Training data can be exported via `GET /admin/training-export` (requires Bearer token)

**Trust tiers** (set in `.env`):
- `EXPERT_USER_IDENTITIES=amcgrean@beisserlumber.com` → tier: expert, weight: 3.0, bypasses admin token
- `STAFF_USER_IDENTITIES=` → tier: staff, weight: 2.0
- Everyone else → tier: default, weight: 1.0

---

## Memory System

- Rolling 6-message window (`MAX_RECENT_MESSAGES=6`) passed to every LLM call
- Summary refreshes every 6 messages after the first 12 (`SUMMARY_REFRESH_INTERVAL = 12 // 2`)
- Summary stored in `conversations.memory_summary` (SQLite)
- Prompt starters cached in-memory per user with 60s TTL (`PROMPT_STARTERS_CACHE_TTL`)

---

## Service Worker

- Cache name: `beisser-ai-v2`
- Uses `skipWaiting()` + `clients.claim()` — new versions take over immediately
- `activate` event deletes old caches automatically
- **On future deploys**: bump `CACHE_NAME` in `public/sw.js` (e.g., `v3`, `v4`) to force all users to get fresh assets

---

## Important Gotchas

- **Never `git pull` on the Pi** — the working directory is intentionally kept clean via SCP deploys. The Pi's `pi_backend/` has live data files (`agility.index`, `agility_ai.db`) that aren't in git.
- **Generated artifacts are gitignored**: `pi_backend/agility.index`, `pi_backend/agility_meta.jsonl`, `pi_backend/agility_ai.db`, `pi_backend/agility_cache.db`, `pi_backend/ingest_output/`
- **The Pi venv** needs `python-multipart` installed if you ever rebuild it
- **Admin auth**: Expert users in `EXPERT_USER_IDENTITIES` bypass the Bearer token check. The token (`ADMIN_EXPORT_TOKEN`) is in the env file on the Pi.
- **Reporting chunks have no `url` field** — `providers.py` uses `ctx.get('url') or ctx.get('source_file')` fallback. Don't regress this.
- **Cache key includes mode**: `{user_identity}:{conversation_id}:{mode}:{question}` — reporting and default answers won't collide.

---

## Unresolved Items

### OCR — 3 Mobile App PDFs
Still failing text extraction:
- `Mobile Apps/Agility Mobile Proof of Delivery POD.pdf`
- `Mobile Apps/Agility Sales - POD notifications on SO.pdf`
- `Mobile Apps/Agility Sales - View Delivery pics from SO.pdf`

Tried: PyMuPDF, pytesseract, rapidocr-onnxruntime. All fail. Likely scanned images with no text layer. **Next step**: try Azure Document Intelligence or AWS Textract (cloud OCR), or manually extract and add as markdown.

### Internal Docs Corpus
Not yet ingested. Suggested approach:
- Output folder: `pi_backend/ingest_output/internal_docs_v1`
- Use `--corpus-name internal_docs_v1` when building
- At runtime, the server can load multiple corpora — see how `reporting_meta` is loaded alongside `meta` in `server.py`

### Prompt Starters Cache Invalidation
The in-memory `_prompt_starters_cache` dict is per-process and never evicted except by TTL. On a Pi restart it resets, which is fine. But if two users ask in rapid succession, the second user gets a 60s-old snapshot. For now this is acceptable.

### Bundle Size
Vite warns about a 944KB JS bundle. Not a problem on LAN, but if the app ever goes public-facing, add dynamic imports for `AdminPage` and `ReportingPage`.

### Training Export → Active Retraining
Corrections are captured and exportable, but the loop from export → fine-tuned model → redeployment is not automated. The export JSON is the raw material; the actual fine-tuning step is manual/future work.

---

## Environment Variables (Pi — `/home/amcgrean/agility-ai-local/.env`)

Key vars (secrets redacted):
```
CHAT_MODEL=gpt-5-mini
EMBED_MODEL=text-embedding-3-small
TOP_K=6
RETRIEVAL_TOP_K_CANDIDATES=10
FINAL_TOP_K=4
MAX_CONTEXT_CHARS=9000
MAX_RECENT_MESSAGES=6
CONVERSATION_SUMMARY_TRIGGER_MESSAGES=12
REQUEST_CACHE_TTL_SECONDS=300
EXPERT_USER_IDENTITIES=amcgrean@beisserlumber.com
OPENAI_REASONING_EFFORT=minimal
OPENAI_TEXT_VERBOSITY=medium
ENABLE_DEBUG_MODE=false
```
