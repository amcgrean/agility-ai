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
