from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from compact.handoff import ConversationHandoffStore
from harness_context.bootstrap import build_container
from harness_context.cli.app import build_parser
from harness_context.engine import ContextEngine
from harness_context.mcp.server import create_mcp_server
from harness_context.runtime import HarnessRuntime
from harness_context.schemas import HarnessError
from memory.episodic import MemoryStore, MemoryType


class ContextEngineTests(unittest.TestCase):
    def test_workspace_isolation_and_unauthorized_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "second"
            outside = root / "outside.py"
            first.mkdir()
            second.mkdir()
            (first / "auth.py").write_text("def refresh_token():\n    return 'first'\n", encoding="utf-8")
            (second / "billing.py").write_text("def charge_card():\n    return 'second'\n", encoding="utf-8")
            outside.write_text("def secret(): pass\n", encoding="utf-8")
            engine = ContextEngine()
            engine.register_workspace("a", [str(first)])
            engine.register_workspace("b", [str(second)])
            engine.refresh_workspace("a")
            engine.refresh_workspace("b")
            result = engine.retrieve_context("b", "refresh_token")
            self.assertEqual(result["items"], [])
            with self.assertRaises(HarnessError):
                engine.refresh_workspace("a", [str(outside)])

    def test_ignores_secrets_and_binary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("TOKEN=secret", encoding="utf-8")
            (root / "image.bin").write_bytes(b"\x00secret")
            (root / "README.md").write_text("# Tiếng Việt\nTài liệu xác thực", encoding="utf-8")
            engine = ContextEngine()
            engine.register_workspace("w", [str(root)])
            report = engine.refresh_workspace("w")
            self.assertEqual(report["files"], 1)
            self.assertTrue(engine.retrieve_context("w", "xác thực")["items"])

    def test_respects_framework_generated_directory_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".gitignore").write_text("/.dart_tool/\n/ios/Pods/\n/build/\n", encoding="utf-8")
            (root / "lib.dart").write_text("String rotateToken() => 'dart';\n", encoding="utf-8")
            generated = {
                ".dart_tool/package_config.json": "dart generated",
                "ios/Pods/Manifest.lock": "pods generated",
                "build/app.bin": "build generated",
                "node_modules/package/index.js": "node generated",
            }
            for relative, content in generated.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            engine = ContextEngine()
            engine.register_workspace("w", [str(root)])
            report = engine.refresh_workspace("w")

            self.assertEqual(report["files"], 2)
            indexed_paths = {item.path for item in engine.states["w"].items}
            self.assertIn(str((root / "lib.dart").resolve()), indexed_paths)
            self.assertNotIn(str((root / ".dart_tool/package_config.json").resolve()), indexed_paths)
            self.assertNotIn(str((root / "ios/Pods/Manifest.lock").resolve()), indexed_paths)

    def test_bundle_is_deterministic_and_planner_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Stable core\nRules", encoding="utf-8")
            engine = ContextEngine()
            engine.register_workspace("w", [str(root)])
            engine.refresh_workspace("w")
            first = engine.prepare_bundle("w")["bundle_id"]
            second = engine.prepare_bundle("w")["bundle_id"]
            self.assertEqual(first, second)
            plan = engine.plan_context("w", "anything", 10, "cag")
            self.assertEqual(plan["strategy"], "cag")

    def test_failed_refresh_keeps_the_last_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "service.py"
            source.write_text("def stable():\n    return 1\n", encoding="utf-8")
            engine = ContextEngine()
            engine.register_workspace("w", [str(root)])
            first = engine.refresh_workspace("w")
            source.write_text("def changed():\n    return 2\n", encoding="utf-8")
            original = engine._chunk_file
            engine._chunk_file = lambda *_: (_ for _ in ()).throw(RuntimeError("parser failed"))
            with self.assertRaises(RuntimeError):
                engine.refresh_workspace("w")
            engine._chunk_file = original
            self.assertEqual(engine.stats("w")["snapshot_id"], first["snapshot_id"])
            self.assertEqual(engine.stats("w")["status"], "ready")

    def test_incremental_refresh_does_not_drop_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.py"
            second = root / "second.py"
            first.write_text("def first():\n    return 1\n", encoding="utf-8")
            second.write_text("def second():\n    return 2\n", encoding="utf-8")
            engine = ContextEngine()
            engine.register_workspace("w", [str(root)])
            engine.refresh_workspace("w")
            first.write_text("def first_changed():\n    return 3\n", encoding="utf-8")
            engine.refresh_workspace("w", [str(first)])
            paths = {item.path for item in engine.states["w"].items}
            self.assertIn(str(first.resolve()), paths)
            self.assertIn(str(second.resolve()), paths)

    def test_warm_runtime_recovers_the_promoted_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Runtime\nSnapshot recovery", encoding="utf-8")
            first = HarnessRuntime.for_workspace(str(root))
            cold = first.startup()
            second = HarnessRuntime.for_workspace(str(root))
            warm = second.startup()
            self.assertFalse(cold["warm_start"])
            self.assertTrue(warm["warm_start"])
            self.assertEqual(cold["snapshot_id"], warm["snapshot_id"])

    def test_cli_and_mcp_expose_the_canonical_contract(self):
        parser = build_parser()
        self.assertEqual(parser.parse_args(["run"]).command, "run")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Contract", encoding="utf-8")
            container = build_container(root)
            workspace_id = next(iter(container.engine.states))
            container.refresh.execute(workspace_id)
            mcp = create_mcp_server(container, workspace_id)
            expected = {
                "register_workspace", "refresh_workspace", "plan_context",
                "retrieve_context", "prepare_context", "context_stats",
                "invalidate_context",
                "memory_save", "memory_search", "handoff_conversation",
                "restore_conversation_handoff",
                "ecc_status", "ecc_search",
            }
            self.assertTrue(expected.issubset(mcp._tool_manager._tools))


class LifecycleTests(unittest.TestCase):
    def test_memory_scope_and_handoff_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(str(Path(directory) / "memory.sqlite3"))
            memory.save(MemoryType.SEMANTIC, "private", "workspace one rule", "", workspace_id="one")
            self.assertEqual(memory.search("workspace one rule", workspace_id="two"), [])
            self.assertEqual(memory.search("workspace one rule", workspace_id="one")[0]["workspace_id"], "one")
            handoffs = ConversationHandoffStore(str(Path(directory) / "handoffs.sqlite3"))
            payload = '[{"role":"user","content":"long history"}]'
            saved = handoffs.prepare(payload, threshold_tokens=1, workspace_id="one", retention_seconds=1)
            self.assertIsNone(handoffs.restore(saved["handoff_id"], workspace_id="two"))
            self.assertTrue(handoffs.delete(saved["handoff_id"], workspace_id="one"))
