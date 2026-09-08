from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from harness_context.cli.app import main
from harness_context.skills import SkillCatalog


class SkillCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = SkillCatalog()

    def test_pinned_catalog_and_full_profile_cover_all_ecc_skills(self):
        self.assertEqual(286, len(self.catalog.skills))
        self.assertEqual(286, len(self.catalog.select("full").skills))
        self.assertEqual("e04ea0b9cc8248686edf5ac751cadff550e162b8", self.catalog.commit)
        self.assertTrue(all((self.catalog.source_root / skill / "SKILL.md").is_file() for skill in self.catalog.skills))
        self.assertTrue(all((self.catalog.source_root / skill / "LICENSE.ecc").is_file() for skill in self.catalog.skills))

    def test_profile_can_be_customized_by_module_and_skill(self):
        base = self.catalog.select("developer")
        custom = self.catalog.select(
            "developer",
            add_modules=("security",),
            remove_skills=("security-scan",),
        )
        self.assertGreater(len(custom.skills), len(base.skills))
        self.assertIn("security", custom.modules)
        self.assertNotIn("security-scan", custom.skills)

    def test_install_preserves_modified_skill_without_force(self):
        selection = self.catalog.select(
            "minimal",
            remove_modules=("workflow-quality",),
            add_skills=("api-design",),
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            first = self.catalog.install(workspace, ".agents/skills", selection)
            self.assertEqual([], first["conflicts"])
            installed = workspace / ".agents" / "skills" / "api-design" / "SKILL.md"
            installed.write_text("user edit", "utf-8")
            conflict = self.catalog.install(workspace, ".agents/skills", selection)
            self.assertEqual(["api-design"], conflict["conflicts"])
            self.assertEqual("user edit", installed.read_text("utf-8"))
            forced = self.catalog.install(workspace, ".agents/skills", selection, force=True)
            self.assertEqual([], forced["conflicts"])
            self.assertNotEqual("user edit", installed.read_text("utf-8"))

    def test_prune_only_removes_unchanged_owned_skills(self):
        first = self.catalog.select(
            "minimal",
            remove_modules=("workflow-quality",),
            add_skills=("api-design",),
        )
        second = self.catalog.select(
            "minimal",
            remove_modules=("workflow-quality",),
            add_skills=("python-patterns",),
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self.catalog.install(workspace, ".agents/skills", first)
            result = self.catalog.install(workspace, ".agents/skills", second, prune=True)
            self.assertEqual([], result["conflicts"])
            self.assertFalse((workspace / ".agents" / "skills" / "api-design").exists())
            self.assertTrue((workspace / ".agents" / "skills" / "python-patterns" / "SKILL.md").is_file())

    def test_one_workspace_can_manage_separate_host_outputs(self):
        selection = self.catalog.select(
            "minimal",
            remove_modules=("workflow-quality",),
            add_skills=("api-design",),
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self.catalog.install(workspace, ".agents/skills", selection)
            self.catalog.install(workspace, ".claude/skills", selection)
            manifests = list((workspace / ".ctxora" / "installer").glob("ecc-skills-*.json"))
            self.assertEqual(2, len(manifests))
            self.assertTrue((workspace / ".agents" / "skills" / "api-design").is_dir())
            self.assertTrue((workspace / ".claude" / "skills" / "api-design").is_dir())

    def test_install_target_registry_maps_hosts_without_duplicate_codex_directory(self):
        outputs = dict(self.catalog.install_outputs(("all",)))
        self.assertEqual(".agents/skills", outputs["codex"])
        self.assertEqual(".claude/skills", outputs["claude"])
        self.assertEqual(".cursor/skills", outputs["cursor"])
        self.assertEqual(".gemini/skills", outputs["gemini"])
        self.assertEqual(".opencode/skills", outputs["opencode"])
        self.assertNotIn(".codex/skills", outputs.values())

    def test_custom_output_and_named_targets_are_mutually_exclusive(self):
        with self.assertRaisesRegex(ValueError, "either --output or --target"):
            self.catalog.install_outputs(("claude",), ".custom/skills")

    def test_cli_profiles_reports_machine_readable_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                status = main(["skills", "profiles", "--workspace", directory])
            payload = json.loads(output.getvalue())
            self.assertEqual(0, status)
            self.assertEqual(286, payload["skill_count"])
            full = next(item for item in payload["profiles"] if item["name"] == "full")
            self.assertEqual(286, full["skill_count"])


if __name__ == "__main__":
    unittest.main()
