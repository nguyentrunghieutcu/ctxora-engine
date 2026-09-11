from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from harness_context.interfaces.cli.app import build_parser
from harness_context.interfaces.console import ConsoleServer
from harness_context.runtime import HarnessRuntime


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "README.md").write_text("# Console\nOffline operator UI", "utf-8")
        self.runtime = HarnessRuntime.for_workspace(str(self.root))
        self.console = ConsoleServer(self.runtime)
        self.console.start()

    def tearDown(self):
        self.console.shutdown()
        self.temporary.cleanup()

    def fetch(self, path: str) -> tuple[object, dict[str, str]]:
        with urlopen(f"{self.console.url.rstrip('/')}{path}", timeout=5) as response:
            body = response.read()
            headers = dict(response.headers.items())
        if headers["Content-Type"].startswith("application/json"):
            return json.loads(body), headers
        return body.decode("utf-8"), headers

    def test_offline_console_exposes_all_operator_views(self):
        page, headers = self.fetch("/")
        self.assertIn("text/html", headers["Content-Type"])
        self.assertNotIn("https://", page)
        for section in (
            "Overview",
            "Index Health",
            "Retrieval",
            "Memory / Handoffs",
            "Skills",
            "Install Targets",
            "Task Learning",
            "Safe Actions",
            "Events",
        ):
            self.assertIn(section, page)

    def test_snapshot_endpoint_matches_doctor_service(self):
        payload, _ = self.fetch("/api/snapshot")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "harness_context.interfaces.cli.app",
                "doctor",
                "--workspace",
                str(self.root),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(completed.stdout), payload)

    def test_event_api_and_sse_use_redacted_application_query(self):
        self.runtime.container.events.emit(
            "request",
            request_id="safe-id",
            method="prepare_context",
            outcome="ok",
            duration_ms=7,
        )
        payload, _ = self.fetch("/api/events?cursor=0&limit=1")
        self.assertEqual("safe-id", payload["items"][0]["request_id"])
        stream, headers = self.fetch("/events?cursor=0&limit=1")
        self.assertIn("text/event-stream", headers["Content-Type"])
        self.assertIn("event: events", stream)
        self.assertIn('"request_id":"safe-id"', stream)

    def test_console_has_no_mutation_routes(self):
        request = Request(
            f"{self.console.url.rstrip('/')}/api/snapshot",
            data=b"{}",
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(405, caught.exception.code)
        self.assertIn("read-only", caught.exception.read().decode("utf-8"))

    def test_shutdown_stops_listener_thread(self):
        self.assertTrue(self.console.running)
        self.console.shutdown()
        self.assertFalse(self.console.running)


class ConsoleConfigurationTests(unittest.TestCase):
    def test_non_loopback_bind_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = HarnessRuntime.for_workspace(directory)
            with self.assertRaisesRegex(ValueError, "loopback"):
                ConsoleServer(runtime, "0.0.0.0")

    def test_dashboard_cli_defaults_to_ephemeral_port(self):
        args = build_parser().parse_args(["dashboard", "--workspace", ".", "--open"])
        self.assertEqual("dashboard", args.command)
        self.assertIsNone(args.port)
        self.assertTrue(args.open_browser)


if __name__ == "__main__":
    unittest.main()
