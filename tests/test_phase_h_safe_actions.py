from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from harness_context.interfaces.console import ConsoleServer
from harness_context.runtime import HarnessRuntime


class SafeActionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "README.md").write_text("# safe actions\n", "utf-8")
        self.runtime = HarnessRuntime.for_workspace(str(self.root))
        self.runtime.startup()
        self.operations = self.runtime.container.operations
        self.workspace_id = self.runtime.config.workspace_id

    def tearDown(self):
        self.temporary.cleanup()

    def test_action_plan_is_deterministic_and_required_before_execute(self):
        first = self.operations.plan_action(self.workspace_id, "purge_expired_handoffs", {})
        second = self.operations.plan_action(self.workspace_id, "purge_expired_handoffs", {})
        self.assertEqual(first.digest, second.digest)
        with self.assertRaisesRegex(ValueError, "confirmation"):
            self.operations.execute_action(self.workspace_id, first.digest, confirmed=False)
        with self.assertRaisesRegex(ValueError, "unknown or expired"):
            self.operations.execute_action(self.workspace_id, "0" * 64, confirmed=True)

    def test_stale_plan_and_arbitrary_action_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported action"):
            self.operations.plan_action(self.workspace_id, "shell", {"command": "rm -rf /"})
        with patch("harness_context.application.operator_actions.time.time", return_value=100):
            plan = self.operations.plan_action(self.workspace_id, "refresh", {})
        with (
            patch("harness_context.application.operator_actions.time.time", return_value=1_000),
            self.assertRaisesRegex(ValueError, "unknown or expired"),
        ):
            self.operations.execute_action(self.workspace_id, plan.digest, confirmed=True)

    def test_execute_uses_the_stored_plan_not_a_mutated_response(self):
        plan = self.operations.plan_action(self.workspace_id, "invalidate", {"target": "bundles"})
        digest = plan.digest
        plan.parameters["target"] = "all"
        receipt = self.operations.execute_action(self.workspace_id, digest, confirmed=True)
        self.assertEqual("bundles", receipt.details["invalidated"])

    def test_diagnostics_export_rejects_external_and_traversal_paths(self):
        for name in ("../secret.json", "/tmp/secret.json", "nested/../../secret.json"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "export"):
                self.operations.plan_action(
                    self.workspace_id,
                    "diagnostics_export",
                    {"name": name},
                )

    def test_install_preview_calls_catalog_without_mutating_target(self):
        target = self.root / ".agents" / "skills"
        plan = self.operations.plan_action(
            self.workspace_id,
            "install_preview",
            {"target": "custom", "output": ".agents/skills", "profile": "minimal"},
        )
        receipt = self.operations.execute_action(self.workspace_id, plan.digest, confirmed=True)
        self.assertEqual("ctxora.action-receipt.v1", receipt.schema_version)
        self.assertEqual("previewed", receipt.status)
        self.assertFalse(target.exists())
        self.assertGreater(receipt.details["operation_count"], 0)
        self.assertNotIn(str(self.root), json.dumps(receipt.to_dict()))

    def test_action_audit_event_is_redacted(self):
        plan = self.operations.plan_action(self.workspace_id, "refresh", {})
        receipt = self.operations.execute_action(self.workspace_id, plan.digest, confirmed=True)
        events = self.operations.events_page(limit=200)["items"]
        audit = [event for event in events if event["event"] == "operator_action"][-1]
        self.assertEqual(receipt.receipt_id, audit["receipt_id"])
        self.assertEqual(plan.digest, audit["plan_digest"])
        encoded = json.dumps(audit)
        self.assertNotIn(str(self.root), encoded)
        self.assertFalse({"path", "query", "source", "parameters"} & audit.keys())

    def test_repair_and_diagnostics_export_stay_workspace_scoped(self):
        invalidate = self.operations.plan_action(self.workspace_id, "invalidate", {"target": "index"})
        self.operations.execute_action(self.workspace_id, invalidate.digest, confirmed=True)
        self.assertEqual(0, self.runtime.health_report()["index"]["files"])
        repair = self.operations.plan_action(self.workspace_id, "repair_index", {})
        repaired = self.operations.execute_action(self.workspace_id, repair.digest, confirmed=True)
        self.assertEqual("completed", repaired.status)
        self.assertGreater(repaired.details["files"], 0)
        export = self.operations.plan_action(
            self.workspace_id,
            "diagnostics_export",
            {"name": "phase-8/diagnostics.json"},
        )
        exported = self.operations.execute_action(self.workspace_id, export.digest, confirmed=True)
        path = self.root / ".ctxora" / "exports" / "phase-8" / "diagnostics.json"
        self.assertTrue(path.is_file())
        self.assertEqual("exports/phase-8/diagnostics.json", exported.details["name"])
        self.assertNotIn(str(self.root), path.read_text("utf-8"))


class SafeActionConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "README.md").write_text("# console actions\n", "utf-8")
        self.runtime = HarnessRuntime.for_workspace(str(self.root))
        self.console = ConsoleServer(self.runtime)
        self.console.start()

    def tearDown(self):
        self.console.shutdown()
        self.temporary.cleanup()

    def request(self, path: str, payload: dict, token: str | None = None):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-CTXORA-CSRF"] = token
        request = Request(
            f"{self.console.url.rstrip('/')}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read())

    def test_console_requires_csrf_and_explicit_confirmation(self):
        with urlopen(f"{self.console.url.rstrip('/')}/api/actions", timeout=5) as response:
            capabilities = json.loads(response.read())
        token = capabilities["csrf_token"]
        self.assertIn("refresh", capabilities["actions"])
        with self.assertRaises(HTTPError) as missing:
            self.request("/api/actions/plan", {"action": "refresh", "parameters": {}})
        self.assertEqual(403, missing.exception.code)
        with self.assertRaises(HTTPError) as wrong:
            self.request("/api/actions/plan", {"action": "refresh", "parameters": {}}, "wrong")
        self.assertEqual(403, wrong.exception.code)
        plan = self.request(
            "/api/actions/plan",
            {"action": "purge_expired_handoffs", "parameters": {}},
            token,
        )
        with self.assertRaises(HTTPError) as unconfirmed:
            self.request(
                "/api/actions/execute",
                {"plan_digest": plan["digest"], "confirm": False},
                token,
            )
        self.assertEqual(400, unconfirmed.exception.code)
        receipt = self.request(
            "/api/actions/execute",
            {"plan_digest": plan["digest"], "confirm": True},
            token,
        )
        self.assertEqual("ctxora.action-receipt.v1", receipt["schema_version"])


if __name__ == "__main__":
    unittest.main()
