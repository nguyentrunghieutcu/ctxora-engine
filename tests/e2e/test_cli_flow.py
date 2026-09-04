from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from harness_context.cli.app import main


class CliEndToEndTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> dict:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(list(arguments)), 0)
        return json.loads(output.getvalue())

    def test_setup_index_query_refresh_export_uninstall(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "service.py"
            source.write_text("def current_value(): return 'one'\n", encoding="utf-8")
            self.run_cli("setup", "--workspace", str(root))
            first = self.run_cli("index", "--workspace", str(root))
            query = self.run_cli("query", "--workspace", str(root), "current_value")
            self.assertEqual(query["snapshot_id"], first["snapshot_id"])
            source.write_text("def current_value(): return 'two'\n", encoding="utf-8")
            second = self.run_cli("index", "--workspace", str(root), "--incremental")
            self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
            exported = root / "snapshot.json"
            self.run_cli("export", "--workspace", str(root), "--output", str(exported))
            self.assertEqual(json.loads(exported.read_text("utf-8"))["snapshot_id"], second["snapshot_id"])
            self.run_cli("uninstall", "--workspace", str(root))
            self.assertTrue((root / ".ctxora").exists(), "uninstall preserves user data by default")
            deleted = self.run_cli("uninstall", "--workspace", str(root), "--delete-data")
            self.assertTrue(deleted["data_deleted"])
            self.assertFalse((root / ".ctxora").exists())

    def test_free_onboarding_tools_and_pro_waitlist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\nname = 'sample'\n", "utf-8")
            (root / "service.py").write_text("def authenticate(): return True\n", "utf-8")
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_service.py").write_text("def test_authenticate(): assert True\n", "utf-8")

            pro = self.run_cli("pro", "--workspace", str(root))
            self.assertEqual(pro["status"], "waitlist")
            self.assertEqual(pro["features"], ["managed automation", "private workflows", "team context"])
            self.assertFalse((root / ".ctxora").exists(), "waitlist status must not initialize paid or local state")

            score = self.run_cli("context-score", "--workspace", str(root))
            self.assertGreaterEqual(score["score"], 55)
            repo_map = self.run_cli("repo-map", "--workspace", str(root))
            self.assertIn("service.py", repo_map["files"])
            explanation = self.run_cli("explain", "--workspace", str(root), "authenticate")
            self.assertEqual(explanation["question"], "authenticate")
            self.assertTrue(explanation["relevant_files"])

            agents = self.run_cli("generate-agents-md", "--workspace", str(root))
            copilot = self.run_cli("generate-copilot-instructions", "--workspace", str(root))
            cursor = self.run_cli("generate-cursor-rules", "--workspace", str(root))
            for result in (agents, copilot, cursor):
                self.assertEqual(result["status"], "generated")
                self.assertTrue(Path(result["output"]).exists())
