from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from harness_context.cli.app import main
from harness_context.mcp.capabilities import TOOL_NAMES
from harness_context.mcp.server import create_mcp_server
from harness_context.runtime import HarnessRuntime


class CliEndToEndTests(unittest.TestCase):
    def test_install_generates_only_selected_target_and_preserves_existing_instructions(self):
        targets = {
            "codex": "AGENTS.md",
            "claude-code": "CLAUDE.md",
            "cursor": ".cursor/rules/ctxora.mdc",
            "generic-mcp": "AGENTS.md",
        }
        for profile, relative in targets.items():
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                config = root / ("client.toml" if profile == "codex" else "client.json")
                arguments = ("install", "--workspace", str(root), "--profile", profile,
                             "--client-config", str(config), "--generate-instructions")
                preview = self.run_cli(*arguments, "--dry-run")
                self.assertEqual(preview["instructions"]["output"], str((root / relative).resolve()))
                self.assertFalse(config.exists(), "preview must not install MCP configuration")
                self.assertFalse((root / ".ctxora").exists(), "preview must not initialize indexing")
                self.assertFalse((root / relative).exists())
                self.run_cli(*arguments)
                content = (root / relative).read_text("utf-8")
                for tool in ("prepare_context", "memory_search", "refresh_workspace", "handoff_conversation", "security"):
                    self.assertIn(tool, content, "every target needs the shared context policy")
                for other in set(targets.values()) - {relative}:
                    self.assertFalse((root / other).exists(), "install must not fan out to other agents")
                if profile == "cursor":
                    self.assertTrue(content.startswith("---\n"))
                (root / relative).write_text("User-owned instructions\n", "utf-8")
                config_before = config.read_bytes()
                with redirect_stderr(StringIO()):
                    self.assertNotEqual(main(list(arguments)), 0)
                self.assertEqual((root / relative).read_text("utf-8"), "User-owned instructions\n")
                self.assertEqual(config.read_bytes(), config_before)

    def test_generate_agents_target_and_output_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_cli("generate-agents-md", "--workspace", str(root), "--target", "claude-code")
            self.assertEqual(result["output"], str((root / "CLAUDE.md").resolve()))
            custom = root / "custom.md"
            self.run_cli("generate-agents-md", "--workspace", str(root), "--target", "copilot", "--output", str(custom))
            self.assertIn("GitHub Copilot", custom.read_text("utf-8"))
            self.assertFalse((root / "AGENTS.md").exists())

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

    def test_framework_agnostic_full_flow_reaches_mcp_ready(self):
        projects = {
            "python": ("pyproject.toml", "[project]\nname = 'sample'\n", "src/app.py", "FRAMEWORK_PYTHON = True\n"),
            "typescript": ("package.json", '{"scripts":{"test":"node --test"}}\n', "src/app.ts", "export const FRAMEWORK_TYPESCRIPT = true;\n"),
            "flutter": ("pubspec.yaml", "name: sample\n", "lib/app.dart", "const FRAMEWORK_FLUTTER = true;\n"),
            "go": ("go.mod", "module example.com/sample\n", "main.go", "package main\nconst FRAMEWORK_GO = true\n"),
            "rust": ("Cargo.toml", "[package]\nname = 'sample'\nversion = '0.1.0'\n", "src/lib.rs", "pub const FRAMEWORK_RUST: bool = true;\n"),
            "java": ("pom.xml", "<project></project>\n", "src/Main.java", "class Main { static final boolean FRAMEWORK_JAVA = true; }\n"),
            "kotlin": ("build.gradle.kts", "plugins { kotlin(\"jvm\") version \"2.0.0\" }\n", "src/Main.kt", "const val FRAMEWORK_KOTLIN = true\n"),
            "swift": ("Package.swift", "// swift-tools-version: 5.9\n", "Sources/App.swift", "let FRAMEWORK_SWIFT = true\n"),
            "php": ("composer.json", '{"name":"example/sample"}\n', "src/App.php", "<?php const FRAMEWORK_PHP = true;\n"),
            "ruby": ("Gemfile", "source 'https://rubygems.org'\n", "lib/app.rb", "FRAMEWORK_RUBY = true\n"),
        }
        for framework, (manifest, manifest_content, source, source_content) in projects.items():
            with self.subTest(framework=framework), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest_path = root / manifest
                source_path = root / source
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_path.write_text(manifest_content, encoding="utf-8")
                source_path.write_text(source_content, encoding="utf-8")

                self.run_cli("setup", "--workspace", str(root))
                registered = self.run_cli("register", "--workspace", str(root))
                indexed = self.run_cli("index", "--workspace", str(root))
                queried = self.run_cli("query", "--workspace", str(root), f"FRAMEWORK_{framework.upper()}")
                health = self.run_cli("doctor", "--workspace", str(root))

                self.assertEqual(registered["status"], "registered")
                self.assertEqual(indexed["status"], "ready")
                self.assertTrue(queried["evidence"]["items"])
                self.assertTrue(health["ready"])

                runtime = HarnessRuntime.for_workspace(str(root), transport="stdio")
                startup = runtime.startup()
                server = create_mcp_server(runtime.container, runtime.config.workspace_id, runtime.lifecycle)
                self.assertTrue(startup["warm_start"])
                self.assertEqual(TOOL_NAMES, frozenset(server._tool_manager._tools))
