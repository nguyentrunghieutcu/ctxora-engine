"""Persistent, locally ranked memory tiers for the MCP harness."""

from __future__ import annotations

import math
import os
import re
import sqlite3
import time
from collections import Counter
from enum import Enum

from retrieval.embeddings import EmbeddingEngine

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class MemoryType(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryStore:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, db_path: str | None = None):
        self.db_path = (
            db_path
            or os.environ.get("CTXORA_MEMORY_DB")
            or os.environ.get("MCP_HARNESS_MEMORY_DB")
            or os.path.expanduser("~/.ctxora/memory.sqlite3")
        )
        if self.db_path != ":memory:":
            directory = os.path.dirname(os.path.abspath(self.db_path))
            os.makedirs(directory, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, timeout=5)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL DEFAULT 'legacy_global',
                type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                scope TEXT NOT NULL DEFAULT 'workspace',
                source TEXT NOT NULL DEFAULT 'user',
                confidence REAL NOT NULL DEFAULT 1.0,
                created_by TEXT NOT NULL DEFAULT 'user',
                expires_at REAL,
                supersedes TEXT NOT NULL DEFAULT '',
                content_hash TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_access REAL NOT NULL,
                hits INTEGER NOT NULL DEFAULT 0,
                UNIQUE(workspace_id, type, key)
            )
        """)
        if self._table_exists("memories"):
            self._conn.execute("""
                INSERT OR IGNORE INTO memories_v2 (
                    workspace_id, type, key, value, tags, created_at,
                    updated_at, last_access, hits
                )
                SELECT 'legacy_global', type, key, value, tags, created_at,
                       updated_at, last_access, hits
                FROM memories
            """)
        self._conn.commit()

    def _table_exists(self, name: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone() is not None

    @staticmethod
    def _document(row: sqlite3.Row) -> str:
        return f"{row['key']} {row['tags']} {row['value']}"

    @staticmethod
    def _lexical_score(query: str, document: str) -> float:
        query_counts = Counter(_TOKEN_RE.findall(query.lower()))
        document_counts = Counter(_TOKEN_RE.findall(document.lower()))
        if not query_counts or not document_counts:
            return 0.0
        numerator = sum(
            query_counts[token] * document_counts[token]
            for token in query_counts.keys() & document_counts.keys()
        )
        query_norm = math.sqrt(sum(count * count for count in query_counts.values()))
        document_norm = math.sqrt(
            sum(count * count for count in document_counts.values())
        )
        return numerator / (query_norm * document_norm)

    @staticmethod
    def _semantic_scores(query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        engine = EmbeddingEngine()
        vectors = engine.rebuild(documents)
        query_vector = engine.embed_text(query)
        return [
            max(0.0, sum(value * query_value for value, query_value in zip(vector, query_vector)))
            for vector in vectors
        ]

    @staticmethod
    def _entry(row: sqlite3.Row) -> dict:
        return {
            "workspace_id": row["workspace_id"],
            "type": row["type"],
            "key": row["key"],
            "value": row["value"],
            "tags": row["tags"],
            "time": row["created_at"],
            "scope": row["scope"],
            "source": row["source"],
            "confidence": row["confidence"],
            "expires_at": row["expires_at"],
            "content_hash": row["content_hash"],
        }

    def search(
        self,
        query: str,
        mtype: MemoryType | None = None,
        top_k: int = 5,
        min_sim: float = 0.12,
        workspace_id: str = "legacy_global",
    ) -> list[dict]:
        if top_k <= 0:
            return []
        sql = "SELECT * FROM memories_v2 WHERE (workspace_id = ? OR scope = 'global') AND (expires_at IS NULL OR expires_at > ?)"
        params: tuple = (workspace_id, time.time())
        if mtype is not None:
            sql += " AND type = ?"
            params += (mtype.value,)
        rows = self._conn.execute(sql, params).fetchall()
        documents = [self._document(row) for row in rows]
        semantic_scores = self._semantic_scores(query, documents)
        ranked = []
        for row, document, semantic_score in zip(rows, documents, semantic_scores):
            score = 0.8 * self._lexical_score(query, document) + 0.2 * semantic_score
            if score >= min_sim:
                ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = ranked[:top_k]
        if selected:
            now = time.time()
            self._conn.executemany(
                "UPDATE memories_v2 SET hits = hits + 1, last_access = ? WHERE id = ?",
                [(now, row["id"]) for _, row in selected],
            )
            self._conn.commit()
        return [self._entry(row) for _, row in selected]

    def save(self, mtype: MemoryType, key: str, value: str, tags: str, workspace_id: str = "legacy_global", scope: str = "workspace", source: str = "user", confidence: float = 1.0, created_by: str = "user", expires_at: float | None = None, supersedes: str = "") -> dict:
        now = time.time()
        import hashlib
        content_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
        self._conn.execute("""
            INSERT INTO memories_v2 (workspace_id, type, key, value, tags, scope, source, confidence, created_by, expires_at, supersedes, content_hash, created_at, updated_at, last_access)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id, type, key) DO UPDATE SET
                value = excluded.value,
                tags = excluded.tags,
                scope = excluded.scope,
                source = excluded.source,
                confidence = excluded.confidence,
                expires_at = excluded.expires_at,
                supersedes = excluded.supersedes,
                content_hash = excluded.content_hash,
                updated_at = excluded.updated_at,
                last_access = excluded.last_access
        """, (workspace_id, mtype.value, key, value, tags, scope, source, confidence, created_by, expires_at, supersedes, content_hash, now, now, now))
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM memories_v2 WHERE workspace_id = ? AND type = ? AND key = ?",
            (workspace_id, mtype.value, key),
        ).fetchone()
        return self._entry(row)

    def delete(self, mtype: MemoryType, key: str, workspace_id: str = "legacy_global") -> bool:
        cursor = self._conn.execute(
            "DELETE FROM memories_v2 WHERE workspace_id = ? AND type = ? AND key = ?", (workspace_id, mtype.value, key)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def list_keys(self, mtype: MemoryType | None = None, limit: int = 30, workspace_id: str = "legacy_global") -> list[str]:
        sql = "SELECT key FROM memories_v2 WHERE workspace_id = ?"
        params: tuple = (workspace_id,)
        if mtype is not None:
            sql += " AND type = ?"
            params += (mtype.value,)
        sql += " ORDER BY last_access DESC LIMIT ?"
        return [row["key"] for row in self._conn.execute(sql, (*params, limit))]

    def evict_lru(self, keep_top: int) -> int:
        keep_top = max(keep_top, 0)
        before = self._conn.execute("SELECT COUNT(*) FROM memories_v2").fetchone()[0]
        self._conn.execute("""
            DELETE FROM memories_v2
            WHERE id NOT IN (
                SELECT id FROM memories_v2 ORDER BY last_access DESC, id DESC LIMIT ?
            )
        """, (keep_top,))
        self._conn.commit()
        return before - self._conn.execute("SELECT COUNT(*) FROM memories_v2").fetchone()[0]

    def stats(self) -> dict:
        summary = {"total": 0}
        rows = self._conn.execute("""
            SELECT type, COUNT(*) AS count, COALESCE(SUM(hits), 0) AS hits,
                   COALESCE(SUM((LENGTH(key) + LENGTH(value) + LENGTH(tags)) / 4), 0) AS tokens
            FROM memories_v2 GROUP BY type
        """).fetchall()
        for row in rows:
            summary[row["type"]] = {
                "count": row["count"],
                "tokens": row["tokens"],
                "hits": row["hits"],
            }
            summary["total"] += row["count"]
        return summary


class EpisodicMemory:
    def __init__(self, store): self.store = store

    def save(self, key, value, tags):
        return self.store.save(MemoryType.EPISODIC, key, value, tags)


class SemanticMemory:
    def __init__(self, store): self.store = store

    def save(self, key, value, tags):
        return self.store.save(MemoryType.SEMANTIC, key, value, tags)


class ProceduralMemory:
    def __init__(self, store): self.store = store

    def save(self, key, value, tags):
        return self.store.save(MemoryType.PROCEDURAL, key, value, tags)
