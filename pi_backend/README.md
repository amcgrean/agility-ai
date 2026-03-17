# Pi Backend

These files mirror the backend currently deployed on the Raspberry Pi alongside the React UI.

Contents:
- `server.py`: FastAPI app, chat persistence, engagement logging, and per-user conversation scoping
- `providers.py`: OpenAI-backed answer formatting and auto-title generation
- `cleanup_non_user_conversations.py`: one-off cleanup script used to remove legacy local/test chat data

The frontend lives in `src/` and is built with Vite. The Pi serves the built static frontend from `ui/` using the backend above.
