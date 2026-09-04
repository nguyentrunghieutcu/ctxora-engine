from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness_context.branding import (
    BRAND_NAME,
    CLI_NAME,
    DESCRIPTION,
    DISTRIBUTION_NAME,
    FREE_PLAN_NAME,
    MCP_SERVER_NAME,
    PAID_PLAN_NAME,
    PAID_PLAN_STATUS,
    PRODUCT_NAME,
    TAGLINE,
)
from harness_context.cli.app import build_parser
from harness_context.mcp.capabilities import SERVER_NAME
from harness_context.paths import workspace_state_dir


class BrandingTests(unittest.TestCase):
    def test_public_brand_contract(self):
        self.assertEqual(BRAND_NAME, "CTXORA")
        self.assertEqual(PRODUCT_NAME, "CTXORA Engine")
        self.assertEqual(MCP_SERVER_NAME, "CTXORA MCP")
        self.assertEqual(CLI_NAME, "ctxora")
        self.assertEqual(DISTRIBUTION_NAME, "ctxora-engine")
        self.assertEqual(FREE_PLAN_NAME, "CTXORA Free")
        self.assertEqual(PAID_PLAN_NAME, "CTXORA Pro")
        self.assertEqual(PAID_PLAN_STATUS, "waitlist")
        self.assertEqual(TAGLINE, "Index once. Ground every agent.")
        self.assertEqual(DESCRIPTION, "Local-first context engine for coding agents.")
        self.assertEqual(build_parser().prog, "ctxora")
        self.assertEqual(SERVER_NAME, "CTXORA MCP")

    def test_legacy_workspace_state_remains_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.assertEqual(workspace_state_dir(root), root / ".ctxora" / "state")
            legacy = root / ".harness" / "state"
            legacy.mkdir(parents=True)
            self.assertEqual(workspace_state_dir(root), legacy)
            preferred = root / ".ctxora" / "state"
            preferred.mkdir(parents=True)
            self.assertEqual(workspace_state_dir(root), preferred)


if __name__ == "__main__":
    unittest.main()
