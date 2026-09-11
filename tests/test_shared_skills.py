from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from harness_context.interfaces.cli.app import main
from harness_context.skills import SkillCatalog, SkillRouter
from harness_context.workspace.identity import workspace_identity


class SharedSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.catalog = SkillCatalog()
        self.selection = self.catalog.select(
            "minimal", remove_modules=("workflow-quality",), add_skills=("api-design",)
        )

    def run_cli(self, *args):
        output = StringIO()
        with redirect_stdout(output):
            status = main(["skills", *args, "--workspace", str(self.root)])
        return status, json.loads(output.getvalue())

    def plans(self, *, prune=False):
        return tuple(
            self.catalog.plan_install(
                self.root, output, self.selection, target=target, delivery="shared", prune=prune
            )
            for target, output in self.catalog.install_outputs(("all",))
        )

    def install_legacy(self):
        for target, output in self.catalog.install_outputs(("all",)):
            self.catalog.install(self.root, output, self.selection, target=target)

    def test_developer_all_uses_runtime_catalog_without_host_payloads(self):
        status, result = self.run_cli("install", "--target", "all")
        self.assertEqual(0, status)
        self.assertEqual("shared", result["delivery"])
        self.assertTrue(result["requires_mcp"])
        self.assertEqual(124, result["selection"]["skill_count"])
        for output in dict(self.catalog.install_outputs(("all",))).values():
            self.assertFalse((self.root / output).exists(), "routing must not create host catalogs")
        receipts = list((self.root / ".ctxora/installer").glob("ecc-skills-*.json"))
        self.assertEqual(5, len(receipts))
        for receipt in receipts:
            payload = json.loads(receipt.read_text())
            self.assertEqual("shared", payload["delivery"])
            self.assertEqual({}, payload["hashes"])
        router = SkillRouter(self.root, workspace_identity(self.root), self.catalog)
        routed = router.route(router.workspace_id, "API design REST endpoints", top_k=1)
        self.assertEqual(124, routed["candidate_count"])
        self.assertIn("instructions", routed["recommendations"][0])
        self.assertTrue(Path(routed["recommendations"][0]["path"]).is_file())

    def test_shared_preview_is_read_only_and_deterministic(self):
        first = self.run_cli("preview", "--target", "all")
        self.assertEqual(first, self.run_cli("preview", "--target", "all"))
        self.assertEqual([], list(self.root.iterdir()))

    def test_materialized_is_explicit_compatibility_opt_in(self):
        status, result = self.run_cli(
            "install", "--delivery", "materialized", "--profile", "minimal", "--target", "claude"
        )
        self.assertEqual(0, status)
        self.assertFalse(result["requires_mcp"])
        self.assertTrue(list((self.root / ".claude/skills").glob("*/SKILL.md")))

    def test_legacy_migration_requires_explicit_prune(self):
        self.install_legacy()
        plans = self.plans()
        self.assertTrue(all(plan.conflicts for plan in plans))
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.catalog.apply_install_plans(self.root, plans, self.selection)
        self.assertEqual(5, len(list(self.root.glob(".*/skills/api-design/SKILL.md"))))

    def test_migration_preserves_unowned_skills_and_is_idempotent(self):
        self.install_legacy()
        custom = self.root / ".claude/skills/my-skill/SKILL.md"
        custom.parent.mkdir()
        custom.write_text("user-owned")
        self.catalog.apply_install_plans(self.root, self.plans(prune=True), self.selection)
        self.assertEqual([], list(self.root.glob(".*/skills/api-design/SKILL.md")))
        self.assertEqual("user-owned", custom.read_text())
        repeated = self.plans(prune=True)
        self.assertTrue(all(not plan.operations and not plan.conflicts for plan in repeated))
        self.catalog.apply_install_plans(self.root, repeated, self.selection)

    def test_modified_owned_skill_blocks_entire_migration(self):
        self.install_legacy()
        modified = self.root / ".opencode/skills/api-design/SKILL.md"
        modified.write_text("customized")
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.catalog.apply_install_plans(self.root, self.plans(prune=True), self.selection)
        self.assertEqual(5, len(list(self.root.glob(".*/skills/api-design/SKILL.md"))))
        self.assertEqual("customized", modified.read_text())

    def test_source_and_profile_failure_restore_files_receipts_and_selection(self):
        self.install_legacy()
        before = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with (
            patch.object(self.catalog, "write_selection", side_effect=OSError("profile failure")),
            self.assertRaisesRegex(OSError, "profile failure"),
        ):
            self.catalog.apply_install_plans(self.root, self.plans(prune=True), self.selection)
        after = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_migration_rejects_stale_preview_and_symlinked_skills(self):
        self.install_legacy()
        plans = self.plans(prune=True)
        modified = self.root / ".claude/skills/api-design/SKILL.md"
        modified.write_text("changed after preview")
        with self.assertRaisesRegex(ValueError, "changed for"):
            self.catalog.apply_install_plans(self.root, plans, self.selection)
        modified.unlink()
        modified.symlink_to(self.catalog.source_root / "api-design/SKILL.md")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.plans(prune=True)

    def test_lock_failure_does_not_remove_another_installers_lock(self):
        lock = self.root / ".ctxora/installer/skills-profile.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("other installer")
        with self.assertRaisesRegex(ValueError, "locked"):
            self.catalog.apply_install_plans(self.root, self.plans(), self.selection)
        self.assertEqual("other installer", lock.read_text())

    def test_shared_mode_rejects_force_and_custom_output(self):
        with self.assertRaisesRegex(ValueError, "never overwrites"):
            self.catalog.plan_install(
                self.root, ".agents/skills", self.selection, delivery="shared", force=True
            )
        self.assertEqual(3, main([
            "skills", "install", "--workspace", str(self.root), "--output", "custom"
        ]))
