import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from harness_context.bootstrap import build_container
from harness_context.engine import ContextEngine
from harness_context.storage.migrations import Migration
from harness_context.storage.snapshots import SCHEMA_VERSION, SnapshotStore
from harness_context.workspace import transition_workspace_status
from retrieval.embeddings import EmbeddingEngine


class PhaseBWorkspaceStorageTests(unittest.TestCase):
    def test_context_request_uses_one_explicit_snapshot_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "service.py"
            source.write_text("def old_value():\n    return 'old'\n", encoding="utf-8")
            engine = ContextEngine()
            engine.register_workspace("w", [str(root)])
            first = engine.refresh_workspace("w")
            original_plan = engine.plan_context

            def refresh_during_plan(*args, **kwargs):
                source.write_text("def new_value():\n    return 'new'\n", encoding="utf-8")
                engine.refresh_workspace("w")
                return original_plan(*args, **kwargs)

            with patch.object(engine, "plan_context", side_effect=refresh_during_plan):
                prepared = engine.prepare_context("w", "old_value", 500)

            self.assertEqual(first["snapshot_id"], prepared["snapshot_id"])
            contents = "\n".join(item["content"] for item in prepared["retrieval"]["items"])
            self.assertIn("old_value", contents)
            self.assertNotIn("new_value", contents)

    def test_invalid_candidate_and_provider_failure_keep_active_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "service.py"
            source.write_text("def stable():\n    return 1\n", encoding="utf-8")
            container = build_container(root, "w")
            first = container.refresh.execute("w")
            active_before = json.loads(container.snapshots.active_path.read_text("utf-8"))
            with self.assertRaises(ValueError):
                container.snapshots.create_candidate({"workspace_id": "w"})
            self.assertEqual(active_before, json.loads(container.snapshots.active_path.read_text("utf-8")))

            source.write_text("def changed():\n    return 2\n", encoding="utf-8")
            with patch.object(EmbeddingEngine, "rebuild", side_effect=RuntimeError("provider unavailable")):
                with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
                    container.refresh.execute("w")
            self.assertEqual(first["snapshot_id"], container.engine.stats("w")["snapshot_id"])
            self.assertEqual(active_before, json.loads(container.snapshots.active_path.read_text("utf-8")))
            records = [json.loads(path.read_text("utf-8")) for path in container.snapshots.candidates_dir.glob("*.json")]
            failed = [record for record in records if record["status"] == "failed"]
            self.assertEqual(1, len(failed))
            self.assertIn("provider unavailable", failed[0]["error"])

    def test_versioned_migration_failure_recovers_and_rollback_swaps_active(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SnapshotStore(root)
            store.state_dir.mkdir(parents=True)
            store.schema_path.write_text('{"version": 1}', encoding="utf-8")
            marker = store.state_dir / "partial-migration"

            def apply_failure(_: Path) -> None:
                marker.write_text("partial", encoding="utf-8")
                raise RuntimeError("migration failed")

            failure = Migration(2, apply_failure, lambda _: marker.unlink())
            with patch("harness_context.storage.snapshots.MIGRATIONS", (failure,)):
                with self.assertRaisesRegex(RuntimeError, "migration failed"):
                    store.prepare()
            self.assertEqual(1, json.loads(store.schema_path.read_text("utf-8"))["version"])
            self.assertFalse(store.candidates_dir.exists())
            self.assertFalse(marker.exists())

            store.prepare()
            self.assertEqual(SCHEMA_VERSION, json.loads(store.schema_path.read_text("utf-8"))["version"])
            for version in (1, 2):
                snapshot = {"workspace_id": "w", "snapshot_id": f"s{version}", "snapshot_version": version,
                            "status": "ready", "fingerprints": {}, "items": [], "bundles": {}, "refreshed_at": 0}
                store.promote(snapshot)
            store.rollback()
            self.assertEqual("s1", store.load_active("w")["snapshot_id"])
            store.active_path.write_text("{broken", encoding="utf-8")
            store.prepare()
            self.assertEqual("s2", store.load_active("w")["snapshot_id"])

    def test_workspace_state_machine_rejects_invalid_promotion_path(self):
        self.assertEqual("indexing", transition_workspace_status("registered", "indexing"))
        self.assertEqual("ready", transition_workspace_status("indexing", "ready"))
        with self.assertRaisesRegex(ValueError, "registered -> ready"):
            transition_workspace_status("registered", "ready")

    def test_concurrent_readers_and_writer_never_return_mixed_snapshot_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "value.py"
            source.write_text("VALUE = 0\n", encoding="utf-8")
            container = build_container(root, "w")
            initial = container.refresh.execute("w")
            failures = []
            expected = {initial["snapshot_id"]: "VALUE = 0"}
            observed = []
            result_lock = threading.Lock()

            def reader():
                try:
                    for _ in range(40):
                        result = container.retrieval.retrieve("w", "VALUE", token_budget=500)
                        self.assertTrue(result["snapshot_id"])
                        self.assertGreaterEqual(result["snapshot_version"], 1)
                        content = "\n".join(item["content"] for item in result["items"])
                        with result_lock:
                            observed.append((result["snapshot_id"], content))
                except Exception as error:
                    failures.append(error)

            def writer():
                try:
                    for value in range(1, 12):
                        source.write_text(f"VALUE = {value}\n", encoding="utf-8")
                        result = container.refresh.execute("w")
                        with result_lock:
                            expected[result["snapshot_id"]] = f"VALUE = {value}"
                except Exception as error:
                    failures.append(error)

            threads = [threading.Thread(target=reader) for _ in range(5)] + [threading.Thread(target=writer)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual([], failures)
            for snapshot_id, content in observed:
                self.assertIn(expected[snapshot_id], content)


if __name__ == "__main__":
    unittest.main()
