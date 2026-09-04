from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import server
from chunking.treesitter_chunker import Chunk
from compact.handoff import ConversationHandoffStore
from memory.episodic import MemoryStore, MemoryType
from retrieval.cache import RetrievalCache
from retrieval.embeddings import EmbeddingEngine


class EmbeddingEngineTests(unittest.TestCase):
    def test_rebuild_keeps_index_vectors_on_the_current_basis(self):
        engine = EmbeddingEngine()
        initial = [
            "auth login session cookie",
            "database migration schema index",
            "flutter widget layout color",
        ]
        engine.rebuild(initial)
        all_texts = initial + [
            "http retry timeout backoff",
            "vector search cosine ranking",
            "unittest fixture monkeypatch",
        ]

        rebuilt_vectors = np.asarray(engine.rebuild(all_texts))
        self.assertTrue(
            np.allclose(rebuilt_vectors[:len(initial)], engine._transform(initial))
        )

        before_query = engine._transform(initial)
        engine.embed_text("retrieve the auth session")
        self.assertTrue(np.allclose(before_query, engine._transform(initial)))


class RetrievalCacheTests(unittest.TestCase):
    def test_cache_invalidates_on_source_change_and_returns_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("initial source", encoding="utf-8")
            cache = RetrievalCache(ttl=60)
            chunk = Chunk(
                id="chunk-1", path=str(source), type="file", symbol="module",
                content="original", summary="", tokens=1,
            )
            options = {"rerank_top_k": 12}
            cache.set("query", [str(source)], [chunk], options)

            cached = cache.get("query", [str(source)], options)
            self.assertIsNotNone(cached)
            cached[0].content = "mutated by presentation"
            self.assertEqual(
                cache.get("query", [str(source)], options)[0].content, "original"
            )

            source.write_text("changed source with a different size", encoding="utf-8")
            self.assertIsNone(cache.get("query", [str(source)], options))


class ConversationHandoffTests(unittest.TestCase):
    def test_compaction_tool_is_not_registered(self):
        self.assertFalse(hasattr(server, "compact_conversation"))

    def test_handoff_preserves_raw_history_only_after_the_threshold(self):
        messages_json = json.dumps([
            {"role": "system", "content": "Keep the original format."},
            {"role": "user", "content": "Explain the release plan in detail."},
            {"role": "assistant", "content": "Here is the complete plan."},
        ], ensure_ascii=False)
        with tempfile.TemporaryDirectory() as directory:
            store = ConversationHandoffStore(str(Path(directory) / "handoffs.sqlite3"))
            continue_result = store.prepare(messages_json, threshold_tokens=10_000)
            self.assertEqual(continue_result["action"], "continue")

            handoff_result = store.prepare(messages_json, threshold_tokens=1, label="release")
            self.assertEqual(handoff_result["action"], "handoff")
            self.assertTrue(handoff_result["preserved_without_compaction"])
            restored = store.restore(handoff_result["handoff_id"])
            self.assertEqual(restored["messages_json"], messages_json)
            self.assertEqual(restored["provider"], "openai")


class MemoryStoreTests(unittest.TestCase):
    def test_memory_persists_and_filters_by_ranked_relevance(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "memory.sqlite3")
            first_store = MemoryStore(db_path)
            first_store.save(
                MemoryType.SEMANTIC,
                "auth-refresh-policy",
                "Refresh token rotation prevents token replay after login.",
                "auth,security",
            )
            first_store.save(
                MemoryType.SEMANTIC,
                "ui-color-scale",
                "Use neutral colors for dashboard controls.",
                "ui,design",
            )

            second_store = MemoryStore(db_path)
            matches = second_store.search(
                "refresh token rotation", mtype=MemoryType.SEMANTIC,
                min_sim=0.2,
            )
            self.assertEqual([match["key"] for match in matches], ["auth-refresh-policy"])
            self.assertEqual(
                second_store.search("unrelated gardening question", min_sim=0.95), []
            )
            stats = second_store.stats()
            self.assertEqual(stats["total"], 2)
            self.assertGreaterEqual(stats["semantic"]["hits"], 1)


class IndexRefreshTests(unittest.TestCase):
    def setUp(self):
        server._all_chunks.clear()
        server._indexed_paths.clear()
        server._indexed_fingerprints.clear()
        server.vec_store.clear()
        server.bm25.build([])
        server.graph.build([])
        server.cache.invalidate_all()

    def tearDown(self):
        self.setUp()

    def test_refresh_replaces_chunks_instead_of_accumulating_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "context.txt"
            source.write_text("first revision", encoding="utf-8")
            server._ensure_indexed([str(source)])
            self.assertEqual(len(server._all_chunks), 1)

            source.write_text("second revision with changed content", encoding="utf-8")
            server._ensure_indexed([str(source)])
            self.assertEqual(len(server._all_chunks), 1)
            self.assertIn("second revision", server._all_chunks[0].content)

            server._ensure_indexed([str(source)], force_reindex=True)
            self.assertEqual(len(server._all_chunks), 1)

    def test_project_default_prompt_cap_is_four_thousand_tokens(self):
        self.assertEqual(server.DEFAULT_MAX_PROMPT_TOKENS, 4_000)
        self.assertFalse(server.DEFAULT_INCLUDE_REPORT)
