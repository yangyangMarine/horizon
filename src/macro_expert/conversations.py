"""
conversations.py
Manages persistent conversations, message history, and conversation export.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.macro_expert.database import Database
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.conversations")

class ConversationManager:
    def __init__(self, db: Database):
        self.db = db

    def create_conversation(self, title: str = "新对话") -> str:
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        with self.db.session() as conn:
            conn.execute(
                "INSERT INTO conversations(conversation_id, title) VALUES (?, ?);",
                (conv_id, title)
            )
        return conv_id

    def list_conversations(self) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            cur = conn.execute(
                "SELECT conversation_id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC;"
            )
            return [dict(r) for r in cur.fetchall()]

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            cur = conn.execute(
                "SELECT conversation_id, title, created_at, updated_at FROM conversations WHERE conversation_id = ?;",
                (conversation_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_title(self, conversation_id: str, new_title: str) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?;",
                (new_title, conversation_id)
            )

    def delete_conversation(self, conversation_id: str) -> bool:
        with self.db.session() as conn:
            cur = conn.execute(
                "DELETE FROM conversations WHERE conversation_id = ?;",
                (conversation_id,)
            )
            return cur.rowcount > 0

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model_name: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        tokens_used: int = 0
    ) -> str:
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        citations_json = json.dumps(citations or [], ensure_ascii=False)
        with self.db.session() as conn:
            conn.execute(
                """
                INSERT INTO messages(message_id, conversation_id, role, content, model_name, citations_json, tokens_used)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (msg_id, conversation_id, role, content, model_name, citations_json, tokens_used)
            )
            conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?;",
                (conversation_id,)
            )
        return msg_id

    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            cur = conn.execute(
                """
                SELECT message_id, role, content, model_name, citations_json, tokens_used, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC;
                """,
                (conversation_id,)
            )
            results = []
            for r in cur.fetchall():
                d = dict(r)
                d["citations"] = json.loads(d.get("citations_json") or "[]")
                results.append(d)
            return results

    def export_conversation_markdown(self, conversation_id: str) -> str:
        conv = self.get_conversation(conversation_id)
        if not conv:
            return ""
        messages = self.get_messages(conversation_id)
        md = [f"# {conv['title']}\n", f"Conversation ID: `{conv['conversation_id']}`\n", f"Exported: {datetime.now(timezone.utc).isoformat()}\n\n---\n"]
        for msg in messages:
            role_display = "👤 **User**" if msg["role"] == "user" else "🤖 **Horizon Expert**"
            md.append(f"### {role_display} ({msg['created_at']})\n\n{msg['content']}\n")
            if msg.get("citations"):
                md.append("\n**来源证据 (Citations):**\n")
                for c in msg["citations"]:
                    cat = c.get("category", "")
                    title = c.get("title", "")
                    ts = f" [{c.get('timestamp')}]" if c.get("timestamp") else ""
                    quote = f" > \"{c.get('verbatim_quote')}\"" if c.get("verbatim_quote") else ""
                    md.append(f"- **[{cat}]** {title}{ts}\n{quote}\n")
            md.append("\n---\n")
        return "\n".join(md)
