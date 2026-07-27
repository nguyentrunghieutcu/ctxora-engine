"""Persistent, no-compression conversation handoff records."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid

from chunking.treesitter_chunker import count_tokens

DEFAULT_HANDOFF_THRESHOLD_TOKENS = 30_000


def _detect_format(messages: list[dict]) -> str:
    """Detect provider message formats without importing the retired compactor."""
    if not messages:
        return "unknown"
    if any("parts" in message for message in messages):
        return "gemini"
    if any(isinstance(message.get("content"), list) for message in messages):
        return "anthropic"
    return "openai"


class ConversationHandoffStore:
    """Store original conversation payloads for a client-created fresh task."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.environ.get(
            "MCP_HARNESS_HANDOFF_DB",
            os.path.expanduser("~/.mcp-harness/handoffs.sqlite3"),
        )
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_handoffs (
                handoff_id TEXT PRIMARY KEY,
                source_hash TEXT NOT NULL UNIQUE,
                provider TEXT NOT NULL,
                messages_json TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            )
        """)
        self._conn.commit()

    @staticmethod
    def _parse_messages(messages_json: str) -> list[dict]:
        try:
            messages = json.loads(messages_json)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError("messages_json must be a JSON array") from error
        if not isinstance(messages, list) or not all(isinstance(item, dict) for item in messages):
            raise ValueError("messages_json must be a JSON array of message objects")
        return messages

    def prepare(
        self,
        messages_json: str,
        threshold_tokens: int = DEFAULT_HANDOFF_THRESHOLD_TOKENS,
        label: str = "",
    ) -> dict:
        """Return continue below threshold or persist an exact handoff payload."""
        messages = self._parse_messages(messages_json)
        token_count = count_tokens(messages_json)
        threshold_tokens = max(1, int(threshold_tokens))
        provider = _detect_format(messages)
        base = {
            "history_tokens": token_count,
            "threshold_tokens": threshold_tokens,
            "provider": provider,
            "message_count": len(messages),
        }
        if token_count < threshold_tokens:
            return {"action": "continue", **base}

        source_hash = hashlib.sha256(messages_json.encode("utf-8")).hexdigest()
        existing = self._conn.execute(
            "SELECT handoff_id, created_at FROM conversation_handoffs WHERE source_hash = ?",
            (source_hash,),
        ).fetchone()
        if existing is None:
            handoff_id = str(uuid.uuid4())
            created_at = time.time()
            self._conn.execute("""
                INSERT INTO conversation_handoffs (
                    handoff_id, source_hash, provider, messages_json,
                    token_count, label, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                handoff_id, source_hash, provider, messages_json,
                token_count, label, created_at,
            ))
            self._conn.commit()
        else:
            handoff_id = existing["handoff_id"]
            created_at = existing["created_at"]

        return {
            "action": "handoff",
            "handoff_id": handoff_id,
            "created_at": created_at,
            "preserved_without_compaction": True,
            "next_tool": "restore_conversation_handoff",
            **base,
        }

    def restore(self, handoff_id: str) -> dict | None:
        """Return the original, unmodified JSON payload for an explicit restore."""
        row = self._conn.execute(
            "SELECT * FROM conversation_handoffs WHERE handoff_id = ?", (handoff_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "handoff_id": row["handoff_id"],
            "provider": row["provider"],
            "history_tokens": row["token_count"],
            "label": row["label"],
            "created_at": row["created_at"],
            "messages_json": row["messages_json"],
        }
