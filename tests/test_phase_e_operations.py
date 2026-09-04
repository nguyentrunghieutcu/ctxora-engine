from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from harness_context.cli.exit_codes import ExitCode, exit_code_for
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
            self.assertFalse({"path", "query", "source", "workspace"} & report.keys())

    def test_exit_codes_are_deterministic(self):
        self.assertEqual(ExitCode.CONFIGURATION, exit_code_for(ValueError("bad")))
        self.assertEqual(ExitCode.TEMPORARY_FAILURE, exit_code_for(TimeoutError()))
        self.assertEqual(ExitCode.INTERNAL_ERROR, exit_code_for(RuntimeError()))


if __name__ == "__main__":
    unittest.main()
