from __future__ import annotations

import json
import unittest
from pathlib import Path

from harness_context.artifacts import build_artifact_manifest, canonical_artifact_drift

ROOT = Path(__file__).parents[2]


class CanonicalArtifactPackagingTests(unittest.TestCase):
    def test_manifest_and_compatibility_projections_are_synchronized(self):
        self.assertEqual((), canonical_artifact_drift(ROOT))

    def test_manifest_declares_portable_targets_and_complete_role_set(self):
        manifest = build_artifact_manifest()
        artifacts = {(item["kind"], item["id"]): item for item in manifest["artifacts"]}
        self.assertEqual(19, manifest["artifact_count"])
        self.assertEqual(
            {
                "ctxora-context-engineer",
                "ctxora-maintainer",
                "ctxora-planner",
                "ctxora-researcher",
                "ctxora-reviewer",
            },
            {artifact_id for kind, artifact_id in artifacts if kind == "agents"},
        )
        self.assertEqual(
            ["codex", "claude-code"],
            artifacts[("agents", "ctxora-planner")]["targets"],
        )
        self.assertEqual(
            ["claude-code"],
            artifacts[("commands", "plan")]["targets"],
        )
        self.assertEqual(
            ["codex", "claude-code", "cursor", "gemini", "opencode"],
            artifacts[("skills", "ctxora-navigation")]["targets"],
        )
        self.assertTrue(
            all(item["provenance"]["license"] == "MIT" for item in artifacts.values())
        )

    def test_package_and_plugin_declarations_keep_canonical_and_projection_paths(self):
        package = json.loads((ROOT / "package.json").read_text("utf-8"))
        self.assertIn("src/harness_context/artifacts", package["files"])
        for projection in ("agents", "commands", "skills"):
            self.assertIn(projection, package["files"])
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text("utf-8"))
        self.assertEqual(["./commands/"], plugin["commands"])
        self.assertEqual(["./agents/"], plugin["agents"])


if __name__ == "__main__":
    unittest.main()
