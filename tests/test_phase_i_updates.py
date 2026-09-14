from __future__ import annotations

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness_context.application.update_service import UpdateService
from harness_context.interfaces.cli.app import build_parser
from harness_context.runtime import HarnessRuntime
from harness_context.version import __version__


class FakeRegistry:
    def __init__(self, latest: str):
        self.version = latest
        self.calls = 0

    def latest(self) -> str:
        self.calls += 1
        return self.version


class FakeRunner:
    def __init__(self, verified_version: str = "6.5.0"):
        self.verified_version = verified_version
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[:3] == ("npm", "list", "--global"):
            stdout = json.dumps({"dependencies": {"ctxora": {"version": self.verified_version}}})
            return subprocess.CompletedProcess(command, 0, stdout, "")
        return subprocess.CompletedProcess(command, 0, "", "")


class UpdateServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "README.md").write_text("# updater\n", "utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_check_is_cached_and_reports_available_release(self):
        registry = FakeRegistry("6.5.0")
        service = UpdateService(self.root, "6.4.0", registry=registry, clock=lambda: 100)
        first = service.check()
        second = service.check()
        self.assertTrue(first.update_available)
        self.assertEqual("6.5.0", first.latest_version)
        self.assertFalse(first.cached)
        self.assertTrue(second.cached)
        self.assertEqual(1, registry.calls)

    def test_plan_is_deterministic_durable_and_requires_confirmation(self):
        service = UpdateService(self.root, "6.4.0", registry=FakeRegistry("6.5.0"), clock=lambda: 100)
        first = service.plan()
        second = service.plan()
        self.assertEqual(first.digest, second.digest)
        self.assertEqual((), first.manual_skill_targets)
        self.assertTrue((self.root / ".ctxora" / "updates" / "plans" / f"{first.digest}.json").is_file())
        with self.assertRaisesRegex(ValueError, "confirmation"):
            service.apply(first.digest, confirmed=False)
        with self.assertRaisesRegex(ValueError, "unknown or expired"):
            service.apply("0" * 64, confirmed=True)
        with self.assertRaisesRegex(ValueError, "digest"):
            service.apply("../../outside", confirmed=True)

    def test_apply_uses_only_fixed_npm_commands_and_writes_receipt(self):
        runner = FakeRunner()
        service = UpdateService(
            self.root, "6.4.0", registry=FakeRegistry("6.5.0"), runner=runner, clock=lambda: 100
        )
        plan = service.plan()
        receipt = service.apply(plan.digest, confirmed=True)
        self.assertEqual("ctxora.update-receipt.v1", receipt.schema_version)
        self.assertEqual("verified", receipt.status)
        self.assertEqual(("npm", "install", "--global", "ctxora@6.5.0", "--ignore-scripts"), runner.commands[0])
        self.assertEqual(("npm", "list", "--global", "ctxora", "--depth=0", "--json"), runner.commands[1])
        receipt_path = self.root / ".ctxora" / "updates" / "receipts" / f"{receipt.receipt_id}.json"
        self.assertTrue(receipt_path.is_file())
        self.assertNotIn(str(self.root), receipt_path.read_text("utf-8"))

    def test_failed_verification_rolls_back_to_previous_version(self):
        runner = FakeRunner(verified_version="6.4.0")
        service = UpdateService(
            self.root, "6.4.0", registry=FakeRegistry("6.5.0"), runner=runner, clock=lambda: 100
        )
        plan = service.plan()
        with self.assertRaisesRegex(RuntimeError, "verification"):
            service.apply(plan.digest, confirmed=True)
        self.assertIn(
            ("npm", "install", "--global", "ctxora@6.4.0", "--ignore-scripts"),
            runner.commands,
        )

    def test_invalid_or_non_newer_versions_are_rejected(self):
        for latest in ("latest", "6.4.0", "6.3.9"):
            with self.subTest(latest=latest):
                service = UpdateService(self.root, "6.4.0", registry=FakeRegistry(latest))
                with self.assertRaises(ValueError):
                    service.plan()

    def test_release_version_and_update_cli_contract(self):
        self.assertEqual("6.5.3", __version__)
        check = build_parser().parse_args(["update", "check", "--workspace", ".", "--force"])
        apply = build_parser().parse_args(["update", "apply", "abc", "--workspace", ".", "--yes"])
        self.assertEqual("check", check.update_action)
        self.assertTrue(check.force)
        self.assertEqual("apply", apply.update_action)
        self.assertTrue(apply.confirmed)

    def test_all_release_version_markers_are_synchronized(self):
        repository = Path(__file__).parents[1]
        package = json.loads((repository / "package.json").read_text("utf-8"))
        lock = json.loads((repository / "package-lock.json").read_text("utf-8"))
        pyproject = (repository / "pyproject.toml").read_text("utf-8")
        launcher = (repository / "bin" / "ctxora.mjs").read_text("utf-8")
        self.assertEqual("6.5.3", package["version"])
        self.assertEqual("6.5.3", lock["version"])
        self.assertRegex(pyproject, re.compile(r'^version = "6\.5\.3"$', re.MULTILINE))
        self.assertIn('const PACKAGE_VERSION = "6.5.3"', launcher)

    def test_console_action_creates_durable_update_plan_without_applying(self):
        runtime = HarnessRuntime.for_workspace(str(self.root))
        runtime.startup()
        runtime.container.updates.registry = FakeRegistry("6.6.0")
        outer = runtime.container.operations.plan_action(runtime.config.workspace_id, "update_plan", {})
        receipt = runtime.container.operations.execute_action(
            runtime.config.workspace_id, outer.digest, confirmed=True
        )
        digest = receipt.details["update_plan_digest"]
        self.assertEqual("planned", receipt.status)
        self.assertTrue((self.root / ".ctxora" / "updates" / "plans" / f"{digest}.json").is_file())


if __name__ == "__main__":
    unittest.main()
