import json
import os
import sqlite3
import uuid
from base64 import urlsafe_b64decode
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from providers import OpenAIProvider

load_dotenv()

BASE = Path(__file__).resolve().parent
INDEX_FILE = BASE / "agility.index"
META_FILE = BASE / "agility_meta.jsonl"
UI_DIR = BASE / "ui"
DB_FILE = BASE / "agility_ai.db"
LEGACY_CONVERSATIONS_FILE = BASE / "conversations.json"

TOP_K = int(os.getenv("TOP_K", "6"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

client = OpenAI()
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


def now_iso() -> str:
    return __import__("datetime").datetime.utcnow().isoformat() + "Z"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
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
            """
        )
        ensure_column(conn, "conversations", "owner_identity", "TEXT NOT NULL DEFAULT 'local'")
        ensure_column(conn, "engagement_events", "user_identity", "TEXT NOT NULL DEFAULT 'local'")


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
        "messages": messages,
    }


def list_conversations_with_messages(user_identity: str) -> list[dict]:
    with get_db() as conn:
        conversations = conn.execute(
            """
            SELECT id, title, owner_identity, created_at, updated_at
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
<p>UI bundle not found. Build the frontend into <code>/home/amcgrean/agility-ai/ui</code>.</p>
</body>
</html>
"""
    )


init_db()
migrate_legacy_conversations()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/conversations")
def list_conversations(request: Request):
    user_identity = resolve_user_identity(request)
    return list_conversations_with_messages(user_identity)


@app.post("/conversations")
def create_conversation(req: ConversationCreateRequest, request: Request):
    conversation_id = str(uuid.uuid4())
    timestamp = now_iso()
    user_identity = resolve_user_identity(request)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO conversations (id, title, owner_identity, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, req.title or "New conversation", user_identity, timestamp, timestamp),
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


@app.get("/", response_class=HTMLResponse)
def home():
    return ui_index_response()


@app.post("/ask")
def ask(req: AskRequest):
    emb = client.embeddings.create(model=EMBED_MODEL, input=req.question).data[0].embedding

    q = np.array([emb]).astype("float32")
    faiss.normalize_L2(q)

    _distances, indices = index.search(q, TOP_K)

    contexts = []
    for idx in indices[0]:
        if idx >= 0:
            contexts.append(meta[idx])

    answer = provider.answer(req.question, contexts)

    return {"answer": answer}


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
