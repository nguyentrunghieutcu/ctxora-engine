"""Persistent, locally ranked memory tiers for the MCP harness."""

from __future__ import annotations

from collections import Counter
from enum import Enum
import math
import os
import re
import sqlite3
import time

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
        self.db_path = db_path or os.environ.get(
            "MCP_HARNESS_MEMORY_DB",
            os.path.expanduser("~/.mcp-harness/memory.sqlite3"),
        )
        if self.db_path != ":memory:":
            directory = os.path.dirname(os.path.abspath(self.db_path))
            os.makedirs(directory, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_access REAL NOT NULL,
                hits INTEGER NOT NULL DEFAULT 0,
                UNIQUE(type, key)
            )
        """)
        self._conn.commit()

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
            "type": row["type"],
            "key": row["key"],
            "value": row["value"],
            "tags": row["tags"],
            "time": row["created_at"],
        }

    def search(
        self,
        query: str,
        mtype: MemoryType | None = None,
        top_k: int = 5,
        min_sim: float = 0.12,
    ) -> list[dict]:
        if top_k <= 0:
            return []
        sql = "SELECT * FROM memories"
        params: tuple = ()
        if mtype is not None:
            sql += " WHERE type = ?"
            params = (mtype.value,)
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
                "UPDATE memories SET hits = hits + 1, last_access = ? WHERE id = ?",
                [(now, row["id"]) for _, row in selected],
            )
            self._conn.commit()
        return [self._entry(row) for _, row in selected]

    def save(self, mtype: MemoryType, key: str, value: str, tags: str) -> dict:
        now = time.time()
        self._conn.execute("""
            INSERT INTO memories (type, key, value, tags, created_at, updated_at, last_access)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(type, key) DO UPDATE SET
                value = excluded.value,
                tags = excluded.tags,
                updated_at = excluded.updated_at,
                last_access = excluded.last_access
        """, (mtype.value, key, value, tags, now, now, now))
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM memories WHERE type = ? AND key = ?",
            (mtype.value, key),
        ).fetchone()
        return self._entry(row)

    def delete(self, mtype: MemoryType, key: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM memories WHERE type = ? AND key = ?", (mtype.value, key)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def list_keys(self, mtype: MemoryType | None = None, limit: int = 30) -> list[str]:
        sql = "SELECT key FROM memories"
        params: tuple = ()
        if mtype is not None:
            sql += " WHERE type = ?"
            params = (mtype.value,)
        sql += " ORDER BY last_access DESC LIMIT ?"
        return [row["key"] for row in self._conn.execute(sql, (*params, limit))]

    def evict_lru(self, keep_top: int) -> int:
        keep_top = max(keep_top, 0)
        before = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        self._conn.execute("""
            DELETE FROM memories
            WHERE id NOT IN (
                SELECT id FROM memories ORDER BY last_access DESC, id DESC LIMIT ?
            )
        """, (keep_top,))
        self._conn.commit()
        return before - self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    def stats(self) -> dict:
        summary = {"total": 0}
        rows = self._conn.execute("""
            SELECT type, COUNT(*) AS count, COALESCE(SUM(hits), 0) AS hits,
                   COALESCE(SUM((LENGTH(key) + LENGTH(value) + LENGTH(tags)) / 4), 0) AS tokens
            FROM memories GROUP BY type
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
