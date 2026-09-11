from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness_context.adapters.harnesses import get_harness_adapter
from harness_context.domain.artifacts import ArtifactKind, InstallOperation, InstallPlan
from harness_context.domain.harnesses import REGISTRY, Capability, HarnessRegistry


class HarnessRegistryTests(unittest.TestCase):
    def test_registry_preserves_current_public_layouts(self):
        fixtures = Path(__file__).parent / "fixtures" / "harnesses" / "current-layouts.json"
        expected = json.loads(fixtures.read_text("utf-8"))
        for name, layout in expected.items():
            target = REGISTRY.get(name)
            self.assertEqual(layout.get("canonical_id", name), target.id)
            self.assertEqual(layout["skill_root"], target.artifact_root("skills"))
            config = str(target.default_config) if target.default_config else None
            self.assertEqual(layout["config"], config)

    def test_profiles_select_content_without_implying_targets(self):
        from harness_context.skills import SkillCatalog

        catalog = SkillCatalog()
        selection = catalog.select("developer")
        self.assertEqual(("codex", ".agents/skills"), catalog.install_outputs(())[0])
        self.assertNotIn("target", selection.to_dict())

    def test_adapter_exposes_only_declared_artifact_roots(self):
        self.assertEqual(".codex/agents", get_harness_adapter("codex").destination(ArtifactKind.AGENT))
        with self.assertRaisesRegex(ValueError, "does not support commands"):
            get_harness_adapter("codex").destination(ArtifactKind.COMMAND)

    def test_fake_harness_is_data_driven(self):
        manifest = {
            "version": 1,
            "targets": [{
                "id": "fake", "display_name": "Fake", "adapter": "fake", "aliases": [],
                "capabilities": ["skills"], "mcp": None,
                "artifacts": {"skills": ".fake/skills"},
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "harnesses.json"
            path.write_text(json.dumps(manifest), "utf-8")
            registry = HarnessRegistry.load(path)
        self.assertEqual(".fake/skills", registry.get("fake").artifact_root("skills"))

    def test_install_plan_digest_is_stable_and_content_addressed(self):
        operation = InstallOperation("add", "one", "/source", "/target", after_hash="abc")
        first = InstallPlan("codex", "developer", "/target", (operation,))
        second = InstallPlan("codex", "developer", "/target", (operation,))
        changed = InstallPlan("codex", "developer", "/other", (operation,))
        self.assertEqual(first.digest, second.digest)
        self.assertNotEqual(first.digest, changed.digest)

    def test_mcp_registry_matches_client_profiles(self):
        from harness_context.adapters.clients import PROFILES

        self.assertEqual(
            {target.id for target in REGISTRY.targets(Capability.MCP)},
            set(PROFILES),
        )

    def test_adapters_match_golden_rendered_artifact_roots(self):
        fixture = Path(__file__).parent / "fixtures" / "harnesses" / "rendered-artifacts.json"
        expected = json.loads(fixture.read_text("utf-8"))
        for target_id, roots in expected.items():
            adapter = get_harness_adapter(target_id)
            self.assertEqual(dict(adapter.target.artifact_roots), roots)


if __name__ == "__main__":
    unittest.main()
