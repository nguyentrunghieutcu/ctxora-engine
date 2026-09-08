from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness_context.api.v2 import (
    ContextPackageV2,
    ErrorResponse,
    PrepareContextRequest,
    export_json_schemas,
    map_exception,
    validate_response,
)
from harness_context.api.v2.models import ContextPackageV2 as LegacyContextPackageV2
from harness_context.api.v2.models import PrepareContextRequest as LegacyPrepareContextRequest
from harness_context.schemas import HarnessError


class ApiV2ContractTests(unittest.TestCase):
    def test_legacy_imports_and_serialized_context_shape_are_preserved(self):
        self.assertIs(LegacyPrepareContextRequest, PrepareContextRequest)
        self.assertIs(LegacyContextPackageV2, ContextPackageV2)
        request = PrepareContextRequest("workspace", "query", 100)
        self.assertEqual(request.preferred_strategy, "auto")
        package = ContextPackageV2("2.0", "workspace", "snapshot", 1, {}, None, None)
        self.assertEqual(list(package.to_dict()), [
            "api_version", "workspace_id", "snapshot_id", "snapshot_version", "plan",
            "stable_context", "evidence", "memory", "handoff", "external_context", "diagnostics",
        ])

    def test_exported_schemas_are_complete_and_deterministic(self):
        checked_in = Path(__file__).parents[1] / "schemas" / "mcp-v2"
        with tempfile.TemporaryDirectory() as directory:
            generated = export_json_schemas(directory)
            self.assertEqual(len(generated), 43)
            self.assertEqual(
                {path.name: path.read_text("utf-8") for path in generated},
                {path.name: path.read_text("utf-8") for path in checked_in.glob("*.json")},
            )
            for path in generated:
                self.assertEqual(json.loads(path.read_text("utf-8"))["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_runtime_response_validation_rejects_contract_drift(self):
        response = ContextPackageV2("2.0", "workspace", "snapshot", 1, {}, None, None).to_dict()
        self.assertIs(validate_response("prepare_context", response), response)
        response.pop("snapshot_id")
        with self.assertRaisesRegex(ValueError, "snapshot_id is required"):
            validate_response("prepare_context", response)

    def test_typed_errors_serialize_and_map_existing_harness_errors(self):
        response = map_exception(HarnessError("stale_snapshot", "refresh required"))
        self.assertIsInstance(response, ErrorResponse)
        self.assertEqual(response.to_dict(), {
            "error": {"code": "stale_snapshot", "message": "refresh required", "retryable": False, "details": {}},
            "api_version": "2.0",
        })


if __name__ == "__main__":
    unittest.main()
