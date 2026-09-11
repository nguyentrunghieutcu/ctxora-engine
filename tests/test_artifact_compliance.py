from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness_context.artifacts import (
    SCHEMAS,
    export_artifact_schemas,
    validate_artifact_manifest,
    validate_definition,
    validate_harness_manifest,
    validate_repository_compliance,
)

ROOT = Path(__file__).parents[1]
MANIFESTS = ROOT / "src" / "harness_context" / "artifacts" / "manifests"


class ArtifactComplianceTests(unittest.TestCase):
    def setUp(self):
        self.harnesses = json.loads((MANIFESTS / "harnesses.json").read_text("utf-8"))
        self.artifacts = json.loads((MANIFESTS / "artifacts.json").read_text("utf-8"))

    def test_repository_and_exported_schemas_are_synchronized(self):
        self.assertEqual((), validate_repository_compliance(ROOT))
        with tempfile.TemporaryDirectory() as directory:
            generated = export_artifact_schemas(directory)
            for path in generated:
                packaged = ROOT / "src" / "harness_context" / "artifacts" / "schemas" / path.name
                self.assertEqual(packaged.read_text("utf-8"), path.read_text("utf-8"))
        self.assertEqual(7, len(SCHEMAS))

    def test_rejects_unsafe_harness_paths_and_undeclared_capabilities(self):
        invalid = copy.deepcopy(self.harnesses)
        invalid["targets"][0]["artifacts"]["commands"] = "/Users/alice/.codex/commands"
        with self.assertRaisesRegex(ValueError, "undeclared capability"):
            validate_harness_manifest(invalid)

    def test_rejects_incompatible_targets_unknown_dependencies_and_cycles(self):
        invalid = copy.deepcopy(self.artifacts)
        invalid["artifacts"][0]["targets"] = ["cursor"]
        with self.assertRaisesRegex(ValueError, "incompatible"):
            validate_artifact_manifest(invalid, self.harnesses)
        invalid = copy.deepcopy(self.artifacts)
        invalid["artifacts"][0]["dependencies"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "unknown dependency"):
            validate_artifact_manifest(invalid, self.harnesses)
        invalid = copy.deepcopy(self.artifacts)
        first, second = invalid["artifacts"][:2]
        first["dependencies"] = [second["id"]]
        second["dependencies"] = [first["id"]]
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            validate_artifact_manifest(invalid, self.harnesses)

    def test_rejects_incomplete_derived_provenance(self):
        invalid = copy.deepcopy(self.artifacts)
        invalid["artifacts"][0]["provenance"]["origin"] = "ecc"
        with self.assertRaisesRegex(ValueError, "requires commit and source hash"):
            validate_artifact_manifest(invalid, self.harnesses)

    def test_rejects_host_specific_or_personal_agent_definitions(self):
        known = {item["id"] for item in self.artifacts["artifacts"]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ctxora-test.md"
            path.write_text(
                "---\nname: ctxora-test\ndescription: Test\nmodel: fixed\n---\n"
                "Read /Users/alice/private and use ctxora-navigation.\n",
                "utf-8",
            )
            with self.assertRaisesRegex(ValueError, "non-portable text"):
                validate_definition(path, "agents", known)


if __name__ == "__main__":
    unittest.main()
