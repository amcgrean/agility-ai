# Beisser AI — Next Agent Handoff

**See `CLAUDE.md` for full project reference (auto-loaded by Claude Code).**

---

## Current State (as of 2026-03-26)

### GitHub
- Repo: `https://github.com/amcgrean/agility-ai`
- Branch: `main`
- Latest commit: `41d9703` — Auto-authenticate admin page for expert users

### Live Pi
- Service: `agility-ai` — **active and healthy**
- `GET /health` → `{ retrievalReady: true, chunkCount: 2319 }`
- Reporting mode live and tested
- Admin page auto-loads for `amcgrean@beisserlumber.com` without a token

---

## What Was Built This Session

### Reporting Expert Mode
- New `/reporting` route and `ReportingPage.jsx` — AgilitySQL schema specialist
- Blue-themed UI with SQL-focused prompt cards
- Backend loads `pi_backend/ingest_output/agility_reporting_v1/chunks.jsonl` (14 chunks) at startup into `reporting_meta`
- Mode is passed through the entire stack: frontend → `api.js` → `useChat.js` → `POST /ask` → `providers.py`
- Separate prompt in `providers.py` with AgilitySQL join rules and alias conventions

### Learning Feedback Loop
- `get_relevant_corrections(question)` queries past corrections (Jaccard similarity > 0.2) and injects them into the LLM prompt as "Previous corrections"
- Corrections stored in `engagement_events` table via `POST /feedback/corrections`

### Performance & Quality Fixes
- Prompt starters cached in-memory (60s TTL) — was running 3 SQL queries on every `/ask`
- Memory summary now refreshes every 6 messages after the first 12 (was only at multiples of 12)
- `top_retrieval_score` now tracked in `ask_analytics` table
- Cache key includes `mode` to prevent default/reporting answers bleeding into each other
- All 14 reporting chunks sent to LLM (was arbitrarily capped at 8)

### UI Fixes
- Auto-scroll to bottom on new messages (both ChatPage and ReportingPage)
- Suggestion/follow-up clicks now fire immediately instead of populating draft
- Follow-up questions now phrased as user questions ("How do I..."), not assistant offers ("Would you like me to...")
- Sidebar navigation links (General Chat / Reporting Expert)

### Admin Auth
- Expert users (`EXPERT_USER_IDENTITIES`) bypass the Bearer token check on all `/admin/*` endpoints
- AdminPage auto-detects expert users via `/users/me` and loads dashboard automatically

### Service Worker
- Bumped to `beisser-ai-v2` with `skipWaiting()` + `activate` cache cleanup
- Future deploys: bump version string in `public/sw.js`

---

## Unresolved / Next Steps

1. **Internal Docs Corpus** — Not yet ingested. Ingest into `pi_backend/ingest_output/internal_docs_v1` with `--corpus-name internal_docs_v1`. At runtime, load alongside existing corpora.

2. **OCR for 3 Mobile App PDFs** — Still failing. Try Azure Document Intelligence or AWS Textract. Files are image-only scans with no text layer.

3. **Training Export → Fine-tuning** — The export endpoint works (`GET /admin/training-export`), but there's no automated pipeline from export → fine-tuned model. This is the next step to make the learning loop complete.

4. **Bundle splitting** — Vite warns about 944KB JS. Fine on LAN. If the app goes public, add dynamic imports for `AdminPage` and `ReportingPage`.

5. **Reporting KB growth** — As more schema rules are added to the reporting skill, consider building a FAISS index for the reporting corpus instead of loading all chunks raw. Currently 14 chunks is fine.
