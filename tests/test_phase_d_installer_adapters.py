from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from harness_context.adapters.clients import PROFILES, get_formatter
from harness_context.installer import ClientInstaller


class PhaseDInstallerAdapterTests(unittest.TestCase):
    def test_profiles_build_deterministic_dry_run_plans(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            installer = ClientInstaller(workspace)
            for name, profile in PROFILES.items():
                config = Path(directory) / f"{name}.{'toml' if profile.config_format == 'toml' else 'json'}"
                first = installer.install(name, config, dry_run=True).to_dict()
                second = installer.install(name, config, dry_run=True).to_dict()
                self.assertEqual(first, second, "dry-run plans are stable inputs to review and automation")
                self.assertFalse(config.exists(), "dry-run must not mutate client configuration")

    def test_json_install_uninstall_round_trip_preserves_unrelated_configuration_and_data(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            data = workspace / ".ctxora" / "state" / "index.bin"
            data.parent.mkdir(parents=True)
            data.write_bytes(b"index")
            config = Path(directory) / "client.json"
            original = {"theme": "dark", "mcpServers": {"existing": {"command": "keep"}}}
            config.write_text(json.dumps(original), "utf-8")
            installer = ClientInstaller(workspace)

            installer.install("cursor", config)
            self.assertTrue(config.with_suffix(".json.ctxora.bak").exists(), "client changes require an atomic recovery point")
            manifest = json.loads(installer.ownership_path.read_text("utf-8"))
            self.assertIn("cursor", manifest, "uninstall may remove only installer-owned configuration")
            installer.uninstall("cursor", config)

            self.assertEqual(original, json.loads(config.read_text("utf-8")), "adoption and removal must not alter unrelated client settings")
            self.assertEqual(b"index", data.read_bytes(), "uninstall preserves customer indexes unless deletion is explicit")

    def test_uninstall_restores_replaced_server_and_delete_data_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            config = Path(directory) / "client.json"
            previous = {"command": "custom", "args": ["serve"]}
            config.write_text(json.dumps({"mcpServers": {"ctxora": previous}}), "utf-8")
            installer = ClientInstaller(workspace)
            installer.install("claude-code", config)
            installer.uninstall("claude-code", config)
            self.assertEqual(previous, json.loads(config.read_text("utf-8"))["mcpServers"]["ctxora"])

            installer.install("claude-code", config)
            installer.uninstall("claude-code", config, delete_data=True)
            self.assertFalse((workspace / ".ctxora").exists())

    def test_codex_toml_round_trip_preserves_unrelated_text(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            config = Path(directory) / "config.toml"
            unrelated = 'model = "gpt-5"\n[features]\nweb = true\n'
            config.write_text(unrelated, "utf-8")
            installer = ClientInstaller(workspace)
            installer.install("codex", config)
            installer.uninstall("codex", config)
            self.assertEqual(unrelated, config.read_text("utf-8"))

    def test_provider_formatters_preserve_warnings_and_provenance_exactly(self):
        payload = {
            "warnings": [{"code": "partial", "message": "kept exactly", "details": [1, None]}],
            "evidence": {"items": [{"content": "x", "provenance": {"source": "workspace", "line": 7}}]},
        }
        for name in PROFILES:
            original = deepcopy(payload)
            formatted = get_formatter(name).format(payload)
            self.assertEqual(original["warnings"], formatted["warnings"])
            self.assertEqual(original["evidence"]["items"][0]["provenance"], formatted["evidence"]["items"][0]["provenance"])
            self.assertIsNot(payload, formatted)

    def test_uninstall_does_not_remove_a_user_modified_owned_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            config = Path(directory) / "client.json"
            installer = ClientInstaller(workspace)
            installer.install("generic-mcp", config)
            content = json.loads(config.read_text("utf-8"))
            content["mcpServers"]["ctxora"]["command"] = "user-command"
            config.write_text(json.dumps(content), "utf-8")
            plan = installer.uninstall("generic-mcp", config)
            self.assertEqual("conflict", plan.mutations[0].operation)
            self.assertEqual("user-command", json.loads(config.read_text("utf-8"))["mcpServers"]["ctxora"]["command"])
            self.assertTrue(installer.ownership_path.exists())


if __name__ == "__main__":
    unittest.main()
