import sqlite3
from pathlib import Path


DB_FILE = Path("/home/amcgrean/agility-ai/agility_ai.db")
BACKUP_FILE = Path("/home/amcgrean/agility-ai/agility_ai.db.pre-user-cleanup-2026-03-17.bak")
REMOVE_IDENTITIES = ("local", "alice@example.com", "bob@example.com")


def main() -> None:
    BACKUP_FILE.write_bytes(DB_FILE.read_bytes())

    conn = sqlite3.connect(DB_FILE)
    with conn:
        placeholders = ", ".join("?" for _ in REMOVE_IDENTITIES)
        conversation_ids = [
            row[0]
            for row in conn.execute(
                f"SELECT id FROM conversations WHERE owner_identity IN ({placeholders})",
                REMOVE_IDENTITIES,
            ).fetchall()
        ]

        if conversation_ids:
            id_placeholders = ", ".join("?" for _ in conversation_ids)
            conn.execute(
                f"DELETE FROM messages WHERE conversation_id IN ({id_placeholders})",
                conversation_ids,
            )

        conn.execute(
            f"DELETE FROM conversations WHERE owner_identity IN ({placeholders})",
            REMOVE_IDENTITIES,
        )
        conn.execute(
            f"DELETE FROM engagement_events WHERE user_identity IN ({placeholders})",
            REMOVE_IDENTITIES,
        )

    conn.close()
    print("cleanup-complete")


if __name__ == "__main__":
    main()
