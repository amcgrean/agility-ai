import json
import logging
import os
import re
import sqlite3
import uuid
from base64 import urlsafe_b64decode
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from providers import OpenAIProvider, ProviderAnswer

load_dotenv(os.getenv("AGILITY_ENV_FILE"))

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("AGILITY_DATA_DIR", str(BASE))).expanduser()
UI_DIR = Path(os.getenv("AGILITY_UI_DIR", str(BASE / "ui"))).expanduser()
INDEX_FILE = DATA_DIR / "agility.index"
META_FILE = DATA_DIR / "agility_meta.jsonl"
DB_FILE = DATA_DIR / "agility_ai.db"
CACHE_DB_FILE = Path(os.getenv("CACHE_DB_FILE", str(DATA_DIR / "agility_cache.db"))).expanduser()
LEGACY_CONVERSATIONS_FILE = DATA_DIR / "conversations.json"

RETRIEVAL_TOP_K_CANDIDATES = int(os.getenv("RETRIEVAL_TOP_K_CANDIDATES", os.getenv("TOP_K", "10")))
FINAL_TOP_K = int(os.getenv("FINAL_TOP_K", "4"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "9000"))
MIN_RERANK_SCORE = float(os.getenv("MIN_RERANK_SCORE", "0.1"))
MAX_RECENT_MESSAGES = int(os.getenv("MAX_RECENT_MESSAGES", "6"))
CONVERSATION_SUMMARY_TRIGGER_MESSAGES = int(os.getenv("CONVERSATION_SUMMARY_TRIGGER_MESSAGES", "12"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "700"))
REQUEST_CACHE_TTL_SECONDS = int(os.getenv("REQUEST_CACHE_TTL_SECONDS", "300"))
ENABLE_DEBUG_MODE = os.getenv("ENABLE_DEBUG_MODE", "false").lower() == "true"
ENABLE_HYBRID_RETRIEVAL_HINT = os.getenv("ENABLE_HYBRID_RETRIEVAL_HINT", "true").lower() == "true"


def parse_identity_list(env_name: str) -> set[str]:
    raw = os.getenv(env_name, "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


EXPERT_USER_IDENTITIES = parse_identity_list("EXPERT_USER_IDENTITIES")
STAFF_USER_IDENTITIES = parse_identity_list("STAFF_USER_IDENTITIES")
CORRECTION_CUE_PREFIXES = (
    "correct answer",
    "actually",
    "no,",
    "no ",
    "it should be",
    "it is",
    "the answer is",
    "real answer",
    "what it should say",
)

logger = logging.getLogger("agility_ai")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

provider = OpenAIProvider()

index = faiss.read_index(str(INDEX_FILE))

meta = []
with open(META_FILE, "r", encoding="utf-8") as f:
    for line in f:
        meta.append(json.loads(line))

app = FastAPI()

if (UI_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=UI_DIR / "assets"), name="ui-assets")


class AskRequest(BaseModel):
    question: str
    conversationId: str | None = None


class ConversationCreateRequest(BaseModel):
    title: str | None = None


class ConversationUpdateRequest(BaseModel):
    title: str


class MessageCreateRequest(BaseModel):
    conversationId: str
    id: str
    role: str
    content: str
    createdAt: str


class EngagementEventCreateRequest(BaseModel):
    eventType: str
    conversationId: str | None = None
    messageId: str | None = None
    label: str | None = None
    metadata: dict | None = None


class CorrectionFeedbackCreateRequest(BaseModel):
    conversationId: str
    messageId: str
    correctedAnswer: str
    notes: str | None = None


class TrainingConsentUpdateRequest(BaseModel):
    enabled: bool


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_cache_db() -> sqlite3.Connection:
    conn = sqlite3.connect(CACHE_DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                owner_identity TEXT NOT NULL DEFAULT 'local',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
            ON messages(conversation_id, created_at);

            CREATE TABLE IF NOT EXISTS engagement_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_identity TEXT NOT NULL DEFAULT 'local',
                conversation_id TEXT,
                message_id TEXT,
                label TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_engagement_created
            ON engagement_events(created_at);

            CREATE TABLE IF NOT EXISTS user_preferences (
                user_identity TEXT PRIMARY KEY,
                training_consent INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ask_analytics (
                id TEXT PRIMARY KEY,
                user_identity TEXT NOT NULL DEFAULT 'local',
                conversation_id TEXT,
                question TEXT NOT NULL,
                normalized_question TEXT NOT NULL,
                cache_hit INTEGER NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                estimated_cost_usd REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ask_analytics_created
            ON ask_analytics(created_at);

            CREATE INDEX IF NOT EXISTS idx_ask_analytics_user_created
            ON ask_analytics(user_identity, created_at);

            CREATE INDEX IF NOT EXISTS idx_ask_analytics_question
            ON ask_analytics(normalized_question);
            """
        )
        ensure_column(conn, "conversations", "owner_identity", "TEXT NOT NULL DEFAULT 'local'")
        ensure_column(conn, "conversations", "training_consent", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "conversations", "memory_summary", "TEXT")
        ensure_column(conn, "engagement_events", "user_identity", "TEXT NOT NULL DEFAULT 'local'")
        ensure_column(conn, "ask_analytics", "conversation_id", "TEXT")


def init_cache_db() -> None:
    with get_cache_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ask_cache (
                key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ask_cache_expires_at
            ON ask_cache(expires_at);
            """
        )


def estimate_cost(usage: dict) -> float:
    # conservative estimate for gpt-5-mini; overridable by env
    input_cost_per_million = float(os.getenv("INPUT_COST_PER_MILLION", "0.25"))
    output_cost_per_million = float(os.getenv("OUTPUT_COST_PER_MILLION", "2.0"))
    input_tokens = usage.get("input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    return (input_tokens / 1_000_000) * input_cost_per_million + (output_tokens / 1_000_000) * output_cost_per_million


def normalize_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question.strip().lower())
    return normalized[:500]


def jaccard_similarity(a: str, b: str) -> float:
    tokens_a = set(re.findall(r"\w+", a.lower()))
    tokens_b = set(re.findall(r"\w+", b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def select_contexts(question: str, indices: np.ndarray, distances: np.ndarray) -> list[dict]:
    selected: list[dict] = []

    for raw_idx, distance in zip(indices[0], distances[0]):
        idx = int(raw_idx)
        if idx < 0 or idx >= len(meta):
            continue
        ctx = dict(meta[idx])
        text = (ctx.get("text") or "").strip()
        if not text:
            continue

        keyword_overlap = jaccard_similarity(question, text)
        rerank_score = float(distance) + (0.20 * keyword_overlap if ENABLE_HYBRID_RETRIEVAL_HINT else 0.0)
        if rerank_score < MIN_RERANK_SCORE:
            continue

        duplicate = any(
            jaccard_similarity(text, existing.get("text", "")) > 0.88
            or (
                ctx.get("url")
                and existing.get("url")
                and ctx.get("url") == existing.get("url")
                and abs(int(ctx.get("chunk_id", 0)) - int(existing.get("chunk_id", 0))) <= 1
            )
            for existing in selected
        )
        if duplicate:
            continue

        ctx["retrieval_score"] = rerank_score
        ctx.setdefault("source_type", "website_docs")
        selected.append(ctx)

    selected.sort(key=lambda item: item.get("retrieval_score", 0.0), reverse=True)

    constrained: list[dict] = []
    total_chars = 0
    for ctx in selected[: FINAL_TOP_K * 2]:
        chunk_chars = len(ctx.get("text", ""))
        if constrained and total_chars + chunk_chars > MAX_CONTEXT_CHARS:
            break
        constrained.append(ctx)
        total_chars += chunk_chars
        if len(constrained) >= FINAL_TOP_K:
            break

    return constrained


def get_conversation_context(conversation_id: str, user_identity: str) -> tuple[list[dict], str | None]:
    with get_db() as conn:
        messages = conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()
        row = conn.execute(
            "SELECT memory_summary FROM conversations WHERE id = ? AND owner_identity = ?",
            (conversation_id, user_identity),
        ).fetchone()

    recent_messages = [
        {"role": row["role"], "content": row["content"], "createdAt": row["created_at"]}
        for row in messages[-MAX_RECENT_MESSAGES:]
    ]
    memory_summary = row["memory_summary"] if row else None

    if len(messages) >= CONVERSATION_SUMMARY_TRIGGER_MESSAGES:
        try:
            recomputed_summary = provider.summarize_messages(
                [{"role": row["role"], "content": row["content"]} for row in messages],
                previous_summary=memory_summary,
            )
            with get_db() as conn:
                conn.execute(
                    "UPDATE conversations SET memory_summary = ? WHERE id = ? AND owner_identity = ?",
                    (recomputed_summary, conversation_id, user_identity),
                )
            memory_summary = recomputed_summary
        except Exception as exc:
            logger.warning("Failed to summarize conversation %s: %s", conversation_id, exc)

    return recent_messages, memory_summary


def cleanup_expired_cache() -> None:
    now_ts = datetime.utcnow().timestamp()
    with get_cache_db() as conn:
        conn.execute("DELETE FROM ask_cache WHERE expires_at <= ?", (now_ts,))


def get_cached_answer(cache_key: str) -> dict | None:
    now_ts = datetime.utcnow().timestamp()
    with get_cache_db() as conn:
        row = conn.execute(
            "SELECT payload_json, expires_at FROM ask_cache WHERE key = ?",
            (cache_key,),
        ).fetchone()

    if row is None:
        return None

    if row["expires_at"] <= now_ts:
        with get_cache_db() as conn:
            conn.execute("DELETE FROM ask_cache WHERE key = ?", (cache_key,))
        return None

    try:
        return json.loads(row["payload_json"])
    except json.JSONDecodeError:
        return None


def put_cached_answer(cache_key: str, payload: dict) -> None:
    now_ts = datetime.utcnow().timestamp()
    expires_at = now_ts + REQUEST_CACHE_TTL_SECONDS
    with get_cache_db() as conn:
        conn.execute(
            """
            INSERT INTO ask_cache (key, payload_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                payload_json = excluded.payload_json,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (cache_key, json.dumps(payload), now_ts, expires_at),
        )


def decode_access_jwt_email(jwt_token: str) -> str | None:
    try:
        parts = jwt_token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = urlsafe_b64decode(payload + padding).decode("utf-8")
        return json.loads(decoded).get("email")
    except Exception:
        return None


def resolve_user_identity(request: Request) -> str:
    direct_header = request.headers.get("x-user-email") or request.headers.get("cf-access-authenticated-user-email")
    if direct_header:
        return direct_header.strip().lower()

    access_jwt = request.headers.get("cf-access-jwt-assertion")
    if access_jwt:
        email = decode_access_jwt_email(access_jwt)
        if email:
            return email.strip().lower()

    return "local"


def migrate_legacy_conversations() -> None:
    if not LEGACY_CONVERSATIONS_FILE.exists():
        return

    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS count FROM conversations").fetchone()["count"]
        if existing:
            return

        with open(LEGACY_CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            conversations = json.load(f)

        for conversation in conversations:
            conn.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation["id"],
                    conversation.get("title", "New conversation"),
                    conversation.get("createdAt", now_iso()),
                    conversation.get("updatedAt", now_iso()),
                ),
            )

            for message in conversation.get("messages", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO messages (id, conversation_id, role, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        message["id"],
                        conversation["id"],
                        message["role"],
                        message["content"],
                        message.get("createdAt", now_iso()),
                    ),
                )

    LEGACY_CONVERSATIONS_FILE.rename(LEGACY_CONVERSATIONS_FILE.with_suffix(".json.migrated"))


def serialize_conversation(row: sqlite3.Row, messages: list[dict]) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "trainingConsent": bool(row["training_consent"]),
        "messages": messages,
    }


def list_conversations_with_messages(user_identity: str) -> list[dict]:
    with get_db() as conn:
        conversations = conn.execute(
            """
            SELECT id, title, owner_identity, training_consent, created_at, updated_at
            FROM conversations
            WHERE owner_identity = ?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (user_identity,),
        ).fetchall()

        messages = conn.execute(
            """
            SELECT id, conversation_id, role, content, created_at
            FROM messages
            WHERE conversation_id IN (
                SELECT id FROM conversations WHERE owner_identity = ?
            )
            ORDER BY created_at ASC
            """,
            (user_identity,),
        ).fetchall()

    messages_by_conversation: dict[str, list[dict]] = {}
    for message in messages:
        messages_by_conversation.setdefault(message["conversation_id"], []).append(
            {
                "id": message["id"],
                "role": message["role"],
                "content": message["content"],
                "createdAt": message["created_at"],
            }
        )

    return [
        serialize_conversation(row, messages_by_conversation.get(row["id"], []))
        for row in conversations
    ]


def get_conversation_for_user(conversation_id: str, user_identity: str) -> dict | None:
    for conversation in list_conversations_with_messages(user_identity):
        if conversation["id"] == conversation_id:
            return conversation
    return None


def ensure_conversation(conversation_id: str, user_identity: str, title: str = "New conversation") -> None:
    timestamp = now_iso()
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO conversations (id, title, owner_identity, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, title, user_identity, timestamp, timestamp),
        )


def require_conversation_access(conversation_id: str, user_identity: str) -> None:
    with get_db() as conn:
        conversation = conn.execute(
            "SELECT owner_identity FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation["owner_identity"] != user_identity:
        raise HTTPException(status_code=403, detail="Conversation does not belong to this user")


def maybe_generate_conversation_title(conversation_id: str, user_identity: str, question: str) -> str | None:
    with get_db() as conn:
        conversation = conn.execute(
            "SELECT title FROM conversations WHERE id = ? AND owner_identity = ?",
            (conversation_id, user_identity),
        ).fetchone()
        user_message_count = conn.execute(
            "SELECT COUNT(*) AS count FROM messages WHERE conversation_id = ? AND role = 'user'",
            (conversation_id,),
        ).fetchone()["count"]

    if conversation is None or conversation["title"] != "New conversation" or user_message_count != 1:
        return None

    try:
        generated_title = provider.generate_conversation_title(question)
    except Exception:
        generated_title = question.strip()[:80]

    generated_title = generated_title.strip() or "New conversation"

    with get_db() as conn:
        conn.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ? AND owner_identity = ?
            """,
            (generated_title, now_iso(), conversation_id, user_identity),
        )

    return generated_title


def ui_index_response():
    index_file = UI_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return HTMLResponse(
        """
<html>
<head>
<title>Agility Assistant</title>
</head>
<body style="font-family:Arial;max-width:900px;margin:40px auto;">
<h2>Agility Documentation Assistant</h2>
<p>UI bundle not found. Build the frontend and point <code>AGILITY_UI_DIR</code> at the output directory.</p>
</body>
</html>
"""
    )


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")


def redact_pii(text: str) -> str:
    redacted = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
    return redacted


def safe_parse_metadata(metadata_json: str | None) -> dict:
    if not metadata_json:
        return {}
    try:
        parsed = json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def check_export_token(request: Request) -> None:
    expected = os.getenv("ADMIN_EXPORT_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Training export token not configured")

    header = request.headers.get("authorization", "")
    token = header.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid export token")


def check_admin_token(request: Request) -> None:
    check_export_token(request)


def stable_identity_hash(identity: str) -> str:
    salt = os.getenv("TRAINING_EXPORT_SALT", "agility-training")
    return sha256(f"{salt}:{identity}".encode("utf-8")).hexdigest()


def get_user_trust_profile(identity: str) -> dict:
    normalized = (identity or "").strip().lower()
    if normalized in EXPERT_USER_IDENTITIES:
        return {"tier": "expert", "weight": 3.0}
    if normalized in STAFF_USER_IDENTITIES:
        return {"tier": "staff", "weight": 2.0}
    return {"tier": "default", "weight": 1.0}


def get_user_training_consent(user_identity: str) -> bool:
    with get_db() as conn:
        preference_row = conn.execute(
            """
            SELECT training_consent
            FROM user_preferences
            WHERE user_identity = ?
            """,
            (user_identity,),
        ).fetchone()
        if preference_row is not None:
            return bool(preference_row["training_consent"])

        conversation_row = conn.execute(
            """
            SELECT MAX(training_consent) AS enabled
            FROM conversations
            WHERE owner_identity = ?
            """,
            (user_identity,),
        ).fetchone()
        return bool(conversation_row["enabled"]) if conversation_row and conversation_row["enabled"] is not None else False


def record_ask_analytics(
    *,
    user_identity: str,
    conversation_id: str | None,
    question: str,
    usage: dict,
    estimated_cost: float,
    cache_hit: bool,
) -> None:
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO ask_analytics (
                id,
                user_identity,
                conversation_id,
                question,
                normalized_question,
                cache_hit,
                input_tokens,
                output_tokens,
                estimated_cost_usd,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                user_identity,
                conversation_id,
                question,
                normalize_question(question),
                1 if cache_hit else 0,
                input_tokens,
                output_tokens,
                estimated_cost,
                now_iso(),
            ),
        )


def summarize_feedback() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) AS count
            FROM engagement_events
            GROUP BY event_type
            ORDER BY count DESC, event_type ASC
            """
        ).fetchall()

    return [{"eventType": row["event_type"], "count": row["count"]} for row in rows]


def analytics_created_at_local_sql(column_name: str = "created_at") -> str:
    return f"datetime(replace(replace({column_name}, 'T', ' '), 'Z', ''), 'localtime')"


def looks_like_correction(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    if len(normalized) < 24:
        return False
    if any(normalized.startswith(prefix) for prefix in CORRECTION_CUE_PREFIXES):
        return True
    return "wrong" in normalized or "should have" in normalized or "not " in normalized


def collect_follow_up_correction_text(messages: list[sqlite3.Row], assistant_index: int) -> str | None:
    correction_parts: list[str] = []
    for message in messages[assistant_index + 1 :]:
        if message["role"] == "assistant":
            break
        if message["role"] != "user":
            continue
        content = (message["content"] or "").strip()
        if content:
            correction_parts.append(content)
    if not correction_parts:
        return None
    return "\n\n".join(correction_parts)


def find_latest_user_question(messages: list[sqlite3.Row], assistant_index: int) -> str | None:
    for message in reversed(messages[:assistant_index]):
        if message["role"] != "user":
            continue
        content = (message["content"] or "").strip()
        if content:
            return content
    return None


def build_correction_record(
    *,
    event_id: str,
    conversation_id: str,
    user_identity: str,
    conversation_created_at: str,
    event_created_at: str,
    assistant_message: sqlite3.Row,
    question: str,
    corrected_answer: str,
    capture_mode: str,
    source_event_type: str,
    notes: str = "",
) -> dict:
    trust_profile = get_user_trust_profile(user_identity)
    record = {
        "event_id": event_id,
        "conversation_id": conversation_id,
        "user_hash": stable_identity_hash(user_identity),
        "conversation_created_at": conversation_created_at,
        "event_created_at": event_created_at,
        "assistant_message_id": assistant_message["id"],
        "question": redact_pii(question),
        "bad_answer": redact_pii(assistant_message["content"]),
        "corrected_answer": redact_pii(corrected_answer),
        "capture_mode": capture_mode,
        "source_event_type": source_event_type,
        "trust_tier": trust_profile["tier"],
        "confidence_weight": trust_profile["weight"],
    }
    cleaned_notes = notes.strip()
    if cleaned_notes:
        record["notes"] = redact_pii(cleaned_notes)
    return record


def build_correction_export_records() -> list[dict]:
    with get_db() as conn:
        feedback_rows = conn.execute(
            """
            SELECT
                e.id AS event_id,
                e.event_type,
                e.user_identity,
                e.conversation_id,
                e.message_id,
                e.metadata_json,
                e.created_at AS event_created_at,
                c.created_at AS conversation_created_at
            FROM engagement_events e
            JOIN conversations c ON c.id = e.conversation_id
            WHERE c.training_consent = 1
              AND e.event_type IN ('response_thumbed_down', 'response_correction_submitted')
            ORDER BY e.created_at ASC
            """
        ).fetchall()

        trusted_rows = conn.execute(
            """
            SELECT
                c.id AS conversation_id,
                c.owner_identity,
                c.created_at AS conversation_created_at,
                c.updated_at AS conversation_updated_at
            FROM conversations c
            WHERE c.training_consent = 1
            ORDER BY c.created_at ASC
            """
        ).fetchall()

        messages_by_conversation: dict[str, list[sqlite3.Row]] = {}
        for row in feedback_rows:
            conversation_id = row["conversation_id"]
            if not conversation_id or conversation_id in messages_by_conversation:
                continue
            messages_by_conversation[conversation_id] = conn.execute(
                """
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()
        for row in trusted_rows:
            conversation_id = row["conversation_id"]
            if conversation_id in messages_by_conversation:
                continue
            messages_by_conversation[conversation_id] = conn.execute(
                """
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()

    records: list[dict] = []
    explicit_by_message_id = {
        row["message_id"]
        for row in feedback_rows
        if row["event_type"] == "response_correction_submitted" and row["message_id"]
    }
    covered_message_ids = set(explicit_by_message_id)

    for row in feedback_rows:
        message_id = row["message_id"]
        conversation_id = row["conversation_id"]
        if not message_id or not conversation_id:
            continue

        messages = messages_by_conversation.get(conversation_id, [])
        assistant_index = next((idx for idx, message in enumerate(messages) if message["id"] == message_id), None)
        if assistant_index is None:
            continue

        assistant_message = messages[assistant_index]
        if assistant_message["role"] != "assistant":
            continue

        metadata = safe_parse_metadata(row["metadata_json"])
        corrected_answer = (
            metadata.get("correctedAnswer")
            or metadata.get("correctAnswer")
            or metadata.get("expertCorrection")
            or metadata.get("replacementAnswer")
        )
        capture_mode = "explicit_feedback"

        if row["event_type"] != "response_correction_submitted" and message_id in explicit_by_message_id:
            continue
        if row["event_type"] != "response_correction_submitted" and not corrected_answer:
            corrected_answer = collect_follow_up_correction_text(messages, assistant_index)
            capture_mode = "derived_from_follow_up"

        corrected_answer = (corrected_answer or "").strip()
        if not corrected_answer:
            continue

        question = find_latest_user_question(messages, assistant_index)
        if not question:
            continue

        records.append(
            build_correction_record(
                event_id=row["event_id"],
                conversation_id=conversation_id,
                user_identity=row["user_identity"],
                conversation_created_at=row["conversation_created_at"],
                event_created_at=row["event_created_at"],
                assistant_message=assistant_message,
                question=question,
                corrected_answer=corrected_answer,
                capture_mode=capture_mode,
                source_event_type=row["event_type"],
                notes=metadata.get("notes") or "",
            )
        )
        covered_message_ids.add(message_id)

    for row in trusted_rows:
        conversation_id = row["conversation_id"]
        trust_profile = get_user_trust_profile(row["owner_identity"])
        if trust_profile["tier"] == "default":
            continue

        messages = messages_by_conversation.get(conversation_id, [])
        for index, message in enumerate(messages):
            if message["role"] != "assistant" or message["id"] in covered_message_ids:
                continue

            follow_up = messages[index + 1] if index + 1 < len(messages) else None
            if follow_up is None or follow_up["role"] != "user":
                continue

            corrected_answer = (follow_up["content"] or "").strip()
            if not looks_like_correction(corrected_answer):
                continue

            question = find_latest_user_question(messages, index)
            if not question:
                continue

            records.append(
                build_correction_record(
                    event_id=f"trusted-follow-up:{follow_up['id']}",
                    conversation_id=conversation_id,
                    user_identity=row["owner_identity"],
                    conversation_created_at=row["conversation_created_at"],
                    event_created_at=follow_up["created_at"],
                    assistant_message=message,
                    question=question,
                    corrected_answer=corrected_answer,
                    capture_mode="trusted_user_follow_up",
                    source_event_type="trusted_user_follow_up",
                )
            )
            covered_message_ids.add(message["id"])

    return records


init_db()
init_cache_db()
cleanup_expired_cache()
migrate_legacy_conversations()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/conversations")
def list_conversations(request: Request):
    user_identity = resolve_user_identity(request)
    return list_conversations_with_messages(user_identity)


@app.get("/users/me")
def get_current_user(request: Request):
    user_identity = resolve_user_identity(request)
    return {
        "identity": user_identity,
        "trainingConsent": get_user_training_consent(user_identity),
    }


@app.get("/users/me/training-consent")
def get_training_consent(request: Request):
    user_identity = resolve_user_identity(request)
    return {"enabled": get_user_training_consent(user_identity)}


@app.patch("/users/me/training-consent")
def set_training_consent(req: TrainingConsentUpdateRequest, request: Request):
    user_identity = resolve_user_identity(request)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (user_identity, training_consent, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_identity) DO UPDATE SET
                training_consent = excluded.training_consent,
                updated_at = excluded.updated_at
            """,
            (user_identity, 1 if req.enabled else 0, now_iso()),
        )
        conn.execute(
            """
            UPDATE conversations
            SET training_consent = ?, updated_at = ?
            WHERE owner_identity = ?
            """,
            (1 if req.enabled else 0, now_iso(), user_identity),
        )

    return {"enabled": req.enabled}


@app.post("/conversations")
def create_conversation(req: ConversationCreateRequest, request: Request):
    conversation_id = str(uuid.uuid4())
    timestamp = now_iso()
    user_identity = resolve_user_identity(request)

    with get_db() as conn:
        default_consent = get_user_training_consent(user_identity)
        conn.execute(
            """
            INSERT INTO conversations (id, title, owner_identity, training_consent, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, req.title or "New conversation", user_identity, 1 if default_consent else 0, timestamp, timestamp),
        )

    return get_conversation_for_user(conversation_id, user_identity)


@app.patch("/conversations/{conversation_id}")
def update_conversation(conversation_id: str, req: ConversationUpdateRequest, request: Request):
    user_identity = resolve_user_identity(request)
    with get_db() as conn:
        result = conn.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ? AND owner_identity = ?
            """,
            (req.title, now_iso(), conversation_id, user_identity),
        )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return get_conversation_for_user(conversation_id, user_identity)


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request):
    user_identity = resolve_user_identity(request)
    require_conversation_access(conversation_id, user_identity)
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id = ? AND owner_identity = ?", (conversation_id, user_identity))
    return {"ok": True}


@app.post("/messages")
def append_message(req: MessageCreateRequest, request: Request):
    user_identity = resolve_user_identity(request)
    ensure_conversation(req.conversationId, user_identity)
    require_conversation_access(req.conversationId, user_identity)

    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO messages (id, conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (req.id, req.conversationId, req.role, req.content, req.createdAt),
        )
        conn.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ? AND owner_identity = ?
            """,
            (now_iso(), req.conversationId, user_identity),
        )

    conversation_title = None
    if req.role == "user":
        conversation_title = maybe_generate_conversation_title(req.conversationId, user_identity, req.content)

    return {
        "id": req.id,
        "role": req.role,
        "content": req.content,
        "createdAt": req.createdAt,
        "conversationTitle": conversation_title,
    }


@app.get("/admin/training-export")
def export_training_dataset(request: Request):
    check_export_token(request)

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                c.id AS conversation_id,
                c.owner_identity,
                c.created_at AS conversation_created_at,
                m.id AS message_id,
                m.role,
                m.content,
                m.created_at AS message_created_at
            FROM conversations c
            JOIN messages m ON m.conversation_id = c.id
            WHERE c.training_consent = 1
            ORDER BY c.created_at ASC, m.created_at ASC
            """
        ).fetchall()

    records = []
    for row in rows:
        records.append(
            {
                "conversation_id": row["conversation_id"],
                "user_hash": stable_identity_hash(row["owner_identity"]),
                "conversation_created_at": row["conversation_created_at"],
                "message_id": row["message_id"],
                "role": row["role"],
                "content": redact_pii(row["content"]),
                "message_created_at": row["message_created_at"],
            }
        )

    correction_records = build_correction_export_records()

    return {
        "count": len(records),
        "records": records,
        "correctionCount": len(correction_records),
        "corrections": correction_records,
    }


@app.get("/admin/metrics")
def get_admin_metrics(request: Request):
    check_admin_token(request)
    created_at_local = analytics_created_at_local_sql()

    with get_db() as conn:
        overview_row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_questions,
                COALESCE(SUM(estimated_cost_usd), 0) AS total_spend,
                COALESCE(SUM(CASE WHEN {created_at_local} >= datetime('now', 'localtime', 'start of day') THEN estimated_cost_usd ELSE 0 END), 0) AS spend_today,
                COALESCE(SUM(CASE WHEN {created_at_local} >= datetime('now', 'localtime', 'start of month') THEN estimated_cost_usd ELSE 0 END), 0) AS spend_month,
                COALESCE(SUM(CASE WHEN {created_at_local} >= datetime('now', 'localtime', 'start of year') THEN estimated_cost_usd ELSE 0 END), 0) AS spend_year,
                COALESCE(SUM(CASE WHEN {created_at_local} >= datetime('now', 'localtime', '-29 day') THEN 1 ELSE 0 END), 0) AS questions_30d,
                COALESCE(SUM(CASE WHEN {created_at_local} >= datetime('now', 'localtime', 'start of day') THEN 1 ELSE 0 END), 0) AS questions_today,
                COALESCE(SUM(CASE WHEN {created_at_local} >= datetime('now', 'localtime', '-29 day') AND cache_hit = 1 THEN 1 ELSE 0 END), 0) AS cache_hits_30d,
                COUNT(DISTINCT CASE WHEN {created_at_local} >= datetime('now', 'localtime', '-29 day') THEN user_identity END) AS active_users_30d,
                COALESCE(SUM(input_tokens), 0) AS input_tokens_total,
                COALESCE(SUM(output_tokens), 0) AS output_tokens_total
            FROM ask_analytics
            """
        ).fetchone()

        top_question_rows = conn.execute(
            """
            SELECT
                normalized_question,
                MIN(question) AS example_question,
                COUNT(*) AS ask_count,
                COUNT(DISTINCT user_identity) AS user_count,
                MAX(created_at) AS last_asked_at
            FROM ask_analytics
            WHERE normalized_question != ''
            GROUP BY normalized_question
            ORDER BY ask_count DESC, last_asked_at DESC
            LIMIT 12
            """
        ).fetchall()

        top_user_rows = conn.execute(
            """
            SELECT
                user_identity,
                COUNT(*) AS question_count,
                COALESCE(SUM(estimated_cost_usd), 0) AS total_cost_usd,
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                MAX(created_at) AS last_asked_at
            FROM ask_analytics
            GROUP BY user_identity
            ORDER BY total_cost_usd DESC, question_count DESC, user_identity ASC
            LIMIT 20
            """
        ).fetchall()

        usage_day_rows = conn.execute(
            f"""
            SELECT
                date({created_at_local}) AS day,
                COUNT(*) AS question_count,
                COALESCE(SUM(estimated_cost_usd), 0) AS total_cost_usd,
                COALESCE(SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END), 0) AS cache_hits
            FROM ask_analytics
            WHERE {created_at_local} >= datetime('now', 'localtime', '-29 day')
            GROUP BY date({created_at_local})
            ORDER BY day ASC
            """
        ).fetchall()

        recent_feedback_rows = conn.execute(
            """
            SELECT
                event_type,
                user_identity,
                label,
                created_at
            FROM engagement_events
            ORDER BY created_at DESC
            LIMIT 20
            """
        ).fetchall()

    questions_30d = int(overview_row["questions_30d"] or 0)
    cache_hits_30d = int(overview_row["cache_hits_30d"] or 0)

    return {
        "generatedAt": now_iso(),
        "overview": {
            "totalQuestions": int(overview_row["total_questions"] or 0),
            "questionsToday": int(overview_row["questions_today"] or 0),
            "questions30d": questions_30d,
            "activeUsers30d": int(overview_row["active_users_30d"] or 0),
            "cacheHitRate30d": (cache_hits_30d / questions_30d) if questions_30d else 0.0,
            "inputTokensTotal": int(overview_row["input_tokens_total"] or 0),
            "outputTokensTotal": int(overview_row["output_tokens_total"] or 0),
            "spendToday": float(overview_row["spend_today"] or 0.0),
            "spendMonth": float(overview_row["spend_month"] or 0.0),
            "spendYear": float(overview_row["spend_year"] or 0.0),
            "totalSpend": float(overview_row["total_spend"] or 0.0),
        },
        "topQuestions": [
            {
                "question": row["example_question"],
                "count": int(row["ask_count"] or 0),
                "users": int(row["user_count"] or 0),
                "lastAskedAt": row["last_asked_at"],
            }
            for row in top_question_rows
        ],
        "topUsers": [
            {
                "userIdentity": row["user_identity"],
                "questionCount": int(row["question_count"] or 0),
                "totalCostUsd": float(row["total_cost_usd"] or 0.0),
                "inputTokens": int(row["input_tokens"] or 0),
                "outputTokens": int(row["output_tokens"] or 0),
                "lastAskedAt": row["last_asked_at"],
            }
            for row in top_user_rows
        ],
        "usageByDay": [
            {
                "day": row["day"],
                "questionCount": int(row["question_count"] or 0),
                "totalCostUsd": float(row["total_cost_usd"] or 0.0),
                "cacheHits": int(row["cache_hits"] or 0),
            }
            for row in usage_day_rows
        ],
        "feedbackSummary": summarize_feedback(),
        "recentFeedback": [
            {
                "eventType": row["event_type"],
                "userIdentity": row["user_identity"],
                "label": row["label"],
                "createdAt": row["created_at"],
            }
            for row in recent_feedback_rows
        ],
    }


@app.post("/engagement")
def create_engagement_event(req: EngagementEventCreateRequest, request: Request):
    event_id = str(uuid.uuid4())
    created_at = now_iso()
    user_identity = resolve_user_identity(request)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO engagement_events (
                id, event_type, user_identity, conversation_id, message_id, label, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                req.eventType,
                user_identity,
                req.conversationId,
                req.messageId,
                req.label,
                json.dumps(req.metadata or {}),
                created_at,
            ),
        )

    return {"ok": True, "id": event_id, "createdAt": created_at}


@app.post("/feedback/corrections")
def create_correction_feedback(req: CorrectionFeedbackCreateRequest, request: Request):
    user_identity = resolve_user_identity(request)
    require_conversation_access(req.conversationId, user_identity)

    corrected_answer = req.correctedAnswer.strip()
    if not corrected_answer:
        raise HTTPException(status_code=400, detail="Corrected answer is required")

    message_id = req.messageId.strip()
    with get_db() as conn:
        message_row = conn.execute(
            """
            SELECT id, role
            FROM messages
            WHERE id = ? AND conversation_id = ?
            """,
            (message_id, req.conversationId),
        ).fetchone()

        if message_row is None:
            raise HTTPException(status_code=404, detail="Message not found")
        if message_row["role"] != "assistant":
            raise HTTPException(status_code=400, detail="Corrections can only target assistant messages")

        event_id = str(uuid.uuid4())
        created_at = now_iso()
        conn.execute(
            """
            INSERT INTO engagement_events (
                id, event_type, user_identity, conversation_id, message_id, label, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                "response_correction_submitted",
                user_identity,
                req.conversationId,
                message_id,
                "expert_correction",
                json.dumps(
                    {
                        "correctedAnswer": corrected_answer,
                        "notes": (req.notes or "").strip(),
                        "source": "expert_feedback",
                    }
                ),
                created_at,
            ),
        )

    return {"ok": True, "id": event_id, "createdAt": created_at}


@app.get("/", response_class=HTMLResponse)
def home():
    return ui_index_response()


@app.post("/ask")
def ask(req: AskRequest, request: Request):
    user_identity = resolve_user_identity(request)
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    cache_scope = req.conversationId or "global"
    cache_key = sha256(f"{user_identity}:{cache_scope}:{question.lower()}".encode("utf-8")).hexdigest()
    cached = get_cached_answer(cache_key)
    if cached:
        record_ask_analytics(
            user_identity=user_identity,
            conversation_id=req.conversationId,
            question=question,
            usage=cached.get("usage", {}) if isinstance(cached, dict) else {},
            estimated_cost=float(cached.get("estimatedCostUsd", 0.0)) if isinstance(cached, dict) else 0.0,
            cache_hit=True,
        )
        return cached

    emb = provider.embedding(question)
    q = np.array([emb]).astype("float32")
    faiss.normalize_L2(q)

    distances, indices = index.search(q, RETRIEVAL_TOP_K_CANDIDATES)
    contexts = select_contexts(question, indices, distances)

    recent_messages: list[dict] = []
    memory_summary: str | None = None
    if req.conversationId:
        require_conversation_access(req.conversationId, user_identity)
        recent_messages, memory_summary = get_conversation_context(req.conversationId, user_identity)

    answer_result: ProviderAnswer = provider.answer(
        question,
        contexts,
        recent_messages=recent_messages,
        memory_summary=memory_summary,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    usage = answer_result.usage if isinstance(answer_result.usage, dict) else {}
    estimated_cost = estimate_cost(usage)
    logger.info(
        "ask conversation=%s contexts=%d in_tokens=%s out_tokens=%s est_cost=%.6f",
        req.conversationId,
        len(contexts),
        usage.get("input_tokens", "?"),
        usage.get("output_tokens", "?"),
        estimated_cost,
    )

    payload = {
        "answer": answer_result.text,
        "usage": usage,
        "estimatedCostUsd": estimated_cost,
    }

    if ENABLE_DEBUG_MODE:
        payload["debug"] = {
            "retrievalTopKCandidates": RETRIEVAL_TOP_K_CANDIDATES,
            "finalTopK": FINAL_TOP_K,
            "selectedContexts": [
                {
                    "url": ctx.get("url"),
                    "chunk_id": ctx.get("chunk_id"),
                    "source_type": ctx.get("source_type", "website_docs"),
                    "retrieval_score": ctx.get("retrieval_score"),
                    "preview": (ctx.get("text", "")[:220] + "...") if len(ctx.get("text", "")) > 220 else ctx.get("text", ""),
                }
                for ctx in contexts
            ],
            "recentMessagesIncluded": len(recent_messages),
            "hasMemorySummary": bool(memory_summary),
        }

    record_ask_analytics(
        user_identity=user_identity,
        conversation_id=req.conversationId,
        question=question,
        usage=usage,
        estimated_cost=estimated_cost,
        cache_hit=False,
    )
    put_cached_answer(cache_key, payload)
    return payload


@app.get("/{full_path:path}")
def frontend_routes(full_path: str):
    candidate = (UI_DIR / full_path).resolve()

    try:
        candidate.relative_to(UI_DIR.resolve())
    except ValueError:
        return ui_index_response()

    if candidate.is_file():
        return FileResponse(candidate)

    return ui_index_response()
