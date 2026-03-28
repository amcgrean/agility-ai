# Handoff to Claude: Agility AI SQL Reporting Module Deployment

**Date:** March 26, 2026
**Project Location (Local):** `c:\Users\indha\python\agility ai`
**Remote Host:** `agility-ai-remote` (User: `amcgrean`)

## 1. Objective Completed
We successfully designed and developed a new **"Reporting Expert"** module for the Agility AI codebase. This module gives the AI specialized context (from `agility-reporting` markdown rules) regarding the AgilitySQL schema to help users construct accurate SQL queries based on verified business joins (e.g., joining on `so_id` instead of `prrowid`).

## 2. Current State
*   **Locally:** The code is 100% finished and functioning correctly.
*   **Remotely:** The deployment to the remote Raspberry Pi has been repeatedly interrupted by severe network instability (SSH connection drops). 

## 3. Files Modified/Created (Local)
The following files include the new feature logic and need to be pushed to the production server:

**Frontend (React/Vite):**
*   `src/pages/ReportingPage.jsx` (NEW)
*   `src/components/Sidebar.jsx` (Added navigation links)
*   `src/App.jsx` (Added `/reporting` route)
*   `src/hooks/useChat.js` (Added support for passing `mode` in requests)
*   `src/services/api.js` (Added support for `mode` parameter)

**Backend (FastAPI/Python):**
*   `pi_backend/server.py` (Loads reporting chunks into memory, adds `mode` to `/ask` endpoint)
*   `pi_backend/providers.py` (Adds specialized "Reporting" prompt behavior)

**Data / Knowledge Base:**
*   `pi_backend/ingest_output/agility_reporting_v1/chunks.jsonl` (The ingested skill rules)
*   `pi_backend/ingest_output/agility_reporting_v1/agility.index` (FAISS index generated locally)
*   `pi_backend/ingest_output/agility_reporting_v1/agility_meta.jsonl`

## 4. The Unstable Connection Deployment Strategy
Because the connection drops if we try to transfer files individually or run long remote build processes, we devised the following strategy that **Claude needs to execute**:

1.  **Local Build:** Run `npm run build` locally in `c:\Users\indha\python\agility ai` to compile the Vite application into the `dist/` (or `ui/`) directory.
2.  **Local Packaging:** Create a single archive file (e.g., `deploy.zip` or `deploy.tar.gz`). It should contain:
    *   The compiled frontend build folder.
    *   `pi_backend/server.py`
    *   `pi_backend/providers.py`
    *   The entire `pi_backend/ingest_output/agility_reporting_v1/` directory.
3.  **Single File Transfer:** Use `scp` to copy `deploy.zip` to `agility-ai-remote`. If the connection drops, you only have to retry this single file transfer.
4.  **Remote Extraction & Restart:** 
    *   SSH into `agility-ai-remote`.
    *   Extract the contents over the existing production directory (likely `/home/amcgrean/agility-ai-local` or `/home/amcgrean/agility-ai`).
    *   Restart the backend service (you can find it by searching `ps aux | grep uvicorn` or `gunicorn` and killing it, or using systemctl if a service is defined).

## 5. Next Steps for Claude
1. Review this document.
2. Ensure you have the user run the `npm run build` process locally (and stream the output back so they know it isn't frozen).
3. Zip the required files.
4. Deploy using the strategy above.
