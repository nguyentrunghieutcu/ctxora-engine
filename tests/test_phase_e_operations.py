from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from harness_context.cli.app import main
from harness_context.cli.exit_codes import ExitCode, exit_code_for
from harness_context.domain.operations import ActionReceipt
from harness_context.mcp.lifecycle import ServerLifecycle
from harness_context.mcp.middleware import RequestMiddleware
from harness_context.observability import LocalMetrics, StructuredEventSink
from harness_context.runtime import HarnessRuntime


async def _result(value):
    return value


class PhaseEOperationsTests(unittest.TestCase):
    def test_events_and_metrics_cannot_capture_customer_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            events = StructuredEventSink(path)
            metrics = LocalMetrics()
            lifecycle = ServerLifecycle()
            lifecycle.mark_ready()
            middleware = RequestMiddleware(lifecycle, events, metrics)
            context = type("Context", (), {"method": "tools/call"})()
            self.assertEqual("ok", asyncio.run(middleware(context, lambda _: _result("ok"))))
            payload = json.loads(path.read_text("utf-8"))
            self.assertFalse({"query", "path", "source"} & payload.keys())
            self.assertEqual(1, metrics.snapshot()["requests_ok"])
            with self.assertRaises(ValueError):
                events.emit("unsafe", query="secret")

    def test_readiness_and_drain_reject_new_work(self):
        lifecycle = ServerLifecycle()
        self.assertFalse(lifecycle.begin_request())
        lifecycle.mark_ready()
        self.assertTrue(lifecycle.begin_request())
        lifecycle.end_request()
        self.assertTrue(lifecycle.drain(0))
        self.assertFalse(lifecycle.begin_request())

    def test_health_report_is_machine_readable_and_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# health", "utf-8")
            runtime = HarnessRuntime.for_workspace(str(root))
            runtime.startup()
            report = runtime.health_report()
            self.assertTrue(report["ready"])
            self.assertFalse({"path", "query", "source"} & report.keys())
            self.assertNotIn(str(root), json.dumps(report))

    def test_operator_snapshot_has_stable_sections_and_runtime_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# snapshot", "utf-8")
            runtime = HarnessRuntime.for_workspace(str(root))
            runtime.startup()
            report = runtime.health_report()
            self.assertEqual(
                {
                    "schema_version",
                    "status",
                    "ready",
                    "runtime",
                    "workspace",
                    "snapshot",
                    "index",
                    "retrieval",
                    "memory",
                    "handoffs",
                    "skills",
                    "installer",
                    "metrics",
                    "events",
                },
                set(report),
            )
            self.assertEqual(
                report,
                runtime.container.operations.snapshot(
                    runtime.config.workspace_id,
                    report["runtime"],
                ).to_dict(),
            )

    def test_operator_snapshot_redacts_handoff_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# redaction", "utf-8")
            runtime = HarnessRuntime.for_workspace(str(root))
            runtime.startup()
            runtime.container.handoff.prepare(
                runtime.config.workspace_id,
                '[{"role":"user","content":"customer-secret-query"}]',
                threshold_tokens=1,
                label="customer-secret-label",
                consent=True,
            )
            encoded = json.dumps(runtime.health_report())
            self.assertNotIn("customer-secret-query", encoded)
            self.assertNotIn("customer-secret-label", encoded)
            self.assertNotIn(str(root), encoded)

    def test_operator_snapshot_summarizes_legacy_mcp_ownership_without_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# ownership", "utf-8")
            runtime = HarnessRuntime.for_workspace(str(root))
            runtime.startup()
            installer = root / ".ctxora" / "installer"
            installer.mkdir(parents=True, exist_ok=True)
            (installer / "ownership.json").write_text(
                json.dumps(
                    {
                        "codex": {
                            "config_path": "/customer/private/config.toml",
                            "installed": "secret config body",
                        }
                    }
                ),
                "utf-8",
            )
            report = runtime.health_report()
            self.assertEqual("codex", report["installer"]["receipts"][0]["target"])
            self.assertEqual("mcp", report["installer"]["receipts"][0]["profile"])
            self.assertNotIn("/customer/private", json.dumps(report))
            self.assertNotIn("secret config body", json.dumps(report))

    def test_event_cursor_is_stable_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            events = StructuredEventSink(Path(directory) / "events.jsonl")
            for index in range(205):
                events.emit("request", request_id=str(index), outcome="ok")
            first = events.query(limit=2)
            second = events.query(first["next_cursor"], limit=2)
            bounded = events.query(limit=1_000)
            self.assertEqual(["0", "1"], [item["request_id"] for item in first["items"]])
            self.assertEqual(["2", "3"], [item["request_id"] for item in second["items"]])
            self.assertEqual("2", second["cursor"])
            self.assertEqual(200, len(bounded["items"]))
            self.assertTrue(bounded["has_more"])
            with self.assertRaises(ValueError):
                events.query("not-a-cursor")

    def test_action_receipt_has_explicit_versioned_serialization(self):
        payload = ActionReceipt("refresh", "planned", "sha256:abc").to_dict()
        self.assertEqual("ctxora.action-receipt.v1", payload["schema_version"])
        self.assertEqual("refresh", payload["action"])
        self.assertTrue(payload["receipt_id"])

    def test_exit_codes_are_deterministic(self):
        self.assertEqual(ExitCode.CONFIGURATION, exit_code_for(ValueError("bad")))
        self.assertEqual(ExitCode.TEMPORARY_FAILURE, exit_code_for(TimeoutError()))
        self.assertEqual(ExitCode.INTERNAL_ERROR, exit_code_for(RuntimeError()))

    def test_cli_interrupt_stops_without_error_traceback(self):
        errors = StringIO()
        with patch("harness_context.cli.app._main", side_effect=KeyboardInterrupt()), redirect_stderr(errors):
            self.assertEqual(130, main([]))
        self.assertEqual("", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
