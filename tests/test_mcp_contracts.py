import tempfile
import unittest
from pathlib import Path

from harness_context.api.v2 import ErrorCode
from harness_context.application.container import ApplicationContainer
from harness_context.bootstrap import build_container
from harness_context.mcp.capabilities import SERVER_NAME, TOOL_NAMES
from harness_context.mcp.errors import error_payload
from harness_context.mcp.lifecycle import create_mcp_server as lifecycle_factory
from harness_context.mcp.server import create_mcp_server as legacy_factory


class McpContractTests(unittest.TestCase):
    def test_legacy_factory_and_exact_tool_inventory_are_preserved(self):
        self.assertIs(lifecycle_factory, legacy_factory)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# MCP contract", "utf-8")
            container = build_container(root)
            server = legacy_factory(container, next(iter(container.engine.states)))
        self.assertEqual(SERVER_NAME, server.name)
        self.assertEqual(TOOL_NAMES, frozenset(server._tool_manager._tools))

    def test_transport_container_exposes_application_services(self):
        fields = ApplicationContainer.__dataclass_fields__
        self.assertTrue({
            "workspace", "retrieval", "memories", "handoff", "ecc_queries", "skill_router",
            "events", "metrics", "operations",
        }.issubset(fields))

    def test_typed_error_mapping_is_available_at_mcp_boundary(self):
        payload = error_payload(ValueError("bad request"))
        self.assertEqual("2.0", payload["api_version"])
        self.assertEqual(ErrorCode.INVALID_REQUEST.value, payload["error"]["code"])
