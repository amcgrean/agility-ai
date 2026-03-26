Follow-up implementation prompt for the `agility-ai` repo.

Current repo/workspace:
- Repo path: `C:\Users\indha\python\agility ai`
- Active backend work branch already pushed to GitHub:
  - branch: `codex/ingestion-runtime-deploy`
  - commit: `e9577b7b3f881cb7fb052c997cfcaa0e0bece54e`
  - PR URL: `https://github.com/amcgrean/agility-ai/pull/new/codex/ingestion-runtime-deploy`
- There are unrelated local frontend changes in `src/` that should not be reverted or mixed into backend work unless explicitly requested.

Recent Updates & Achievements:
- **App Rebranded to Beisser AI**: Fully renamed from "Agility AI" to "Beisser AI" across all UI, backend, and LLM persona.
- **PWA Implementation**: Added a custom logo, `manifest.json`, and `sw.js`. Optimized for mobile using `h-dvh`.
- **Independent Scrolling Fix**: Applied `min-h-0` to the flex hierarchy in `ChatPage.jsx` to allow the message list to scroll independently of the sticky sidebar and input.
- **Codex Mobile Patch Merge**: Integrated "sticky chat input" and other mobile-first CSS tweaks.
- **Deployment**: Synced to GitHub `main` and fully deployed to the Raspberry Pi.

What I Learned (Technical Notes):
- **Flexbox Scrolling**: Use `min-h-0` on flex items that should scroll with `overflow-y-auto`.
- **PWA Layout**: `h-dvh` prevents mobile browser chrome from jumping or hiding the app UI.
- **Pi Sync**: If the Pi git state is "dirty", use `git reset --hard origin/main` to allow clean pulling.

Future Handover Tasks:
- **OCR Improvements**: 3 mobile-app PDFs still fail to extract text via standard PyMuPDF. Monitor Tesseract status or try a cloud OCR if needed.
- **PWA Enhancements**: Improve offline capabilities in `sw.js`.
- **UI Tweaks**: Fine-tune the "Beisser AI" persona tone based on user feedback.

What is already done:
- A document ingestion pipeline now exists under `pi_backend/scripts/`:
  - `ingest_agility_docs.py`
  - `build_doc_index.py`
  - `refresh_agility_docs.py`
  - `doc_ingest_utils.py`
  - `doc_ingest_extract.py`
  - `doc_ingest_chunk.py`
  - `agility_mcp_server.py`
- The pipeline handles:
  - HTML portal articles
  - HTML training/video wrapper pages
  - PDFs
  - DOCX guides
- Metadata now includes:
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
- The backend `server.py` now supports:
  - safer retrieval artifact loading
  - `GET /admin/retrieval-status`
  - `POST /admin/reindex`
- The MCP server can search and filter by:
  - `corpus_name`
  - `content_domain`
  - `access_scope`
  - `source_type`
  - `portal_section`

Live deployment status:
- The Raspberry Pi is already updated with:
  - the new `agility.index`
  - the new `agility_meta.jsonl`
  - the new backend code from `codex/ingestion-runtime-deploy`
- Pi service:
  - service name: `agility-ai`
  - live data dir: `/home/amcgrean/agility-ai-data`
  - checkout dir: `/home/amcgrean/agility-ai`
  - env file: `/home/amcgrean/agility-ai-local/.env`
- Verified on Pi:
  - `/health` returns `retrievalReady: true`
  - `/admin/retrieval-status` returns `2319` chunks
  - `/ask` answers correctly from the new hosted Agility corpus

Latest ingestion baseline:
- Output folder:
  - `pi_backend/ingest_output/wedge_scrape_v5`
- Current counts:
  - `254` processed sources
  - `1039` normalized records
  - `2319` chunks
  - `7` remaining errors

Remaining unresolved ingestion errors:
1. `Mobile Apps/Agility Mobile Proof of Delivery POD.pdf`
2. `Mobile Apps/Agility Sales - POD notifications on SO.pdf`
3. `Mobile Apps/Agility Sales - View Delivery pics from SO.pdf`
   - Current result: still `No extractable PDF text found`
   - Tried:
     - machine-readable PDF extraction
     - `pytesseract` hook
     - `rapidocr-onnxruntime` fallback
   - Windows Tesseract installer did not complete in this environment
2. Missing/unopenable password-policy PDFs referenced by the scrape corpus:
   - `site/downloads/ar27482-password-policy-prohibition-of-compromised-passwords-2127d305.pdf`
   - `site/downloads/ar27482-password-policy-prohibition-of-compromised-passwords-pdf-2127d305.html`
   - `site/downloads/ar27485-hosted-password-policy-qa-ar2007-how-to-change-or-update-user-passwords--59f8a691.html`
   - `site/downloads/ar27485-hosted-password-policy-qa-ar2007-how-to-change-or-update-user-passwords--59f8a691.pdf`

Important implementation notes:
- Do not revert unrelated user changes in `src/`.
- Generated artifacts are now ignored in `.gitignore`:
  - `pi_backend/agility.index`
  - `pi_backend/agility_meta.jsonl`
  - `pi_backend/agility_ai.db`
  - `pi_backend/agility_cache.db*`
  - `pi_backend/ingest_output/`
- If deploying code to Pi again, remember the Pi venv needed:
  - `python-multipart`
- If using the admin reindex endpoint on Pi, validate dependencies in `/home/amcgrean/agility-ai-local/.venv`.

Recommended next objective:
- Start the next corpus as a separate ingest batch, likely internal docs.
- Keep corpora separate by output folder and `corpus_name`, but searchable together at runtime.

Suggested next task:
1. Ingest internal docs into a new corpus, for example:
   - `pi_backend/ingest_output/internal_docs_v1`
   - `--corpus-name internal_docs_v1`
2. Rebuild the combined retrieval index.
3. Verify retrieval filtering for `access_scope` before broader internal rollout.
4. Optionally improve the stubborn OCR case for the 3 mobile-app PDFs if those documents are important.

If asked whether the live chatbot is already using the new scrape corpus, the answer is yes.
