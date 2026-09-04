import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text("utf-8"), filename=str(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_mcp_transport_only_reaches_application_and_api_boundaries(self):
        forbidden = ("harness_context.engine", "harness_context.storage", "memory", "compact", "retrieval", "chunking")
        for path in (SRC / "harness_context" / "mcp").rglob("*.py"):
            leaks = sorted(module for module in imported_modules(path) if module.startswith(forbidden))
            self.assertEqual([], leaks, f"{path.name} bypasses application boundary: {leaks}")

    def test_watcher_depends_on_application_protocols_not_engine(self):
        modules = imported_modules(SRC / "harness_context" / "watcher" / "service.py")
        self.assertIn("harness_context.application.protocols", modules)
        self.assertNotIn("harness_context.engine", modules)

    def test_legacy_service_imports_remain_stable(self):
        from harness_context.application import ContextService as public_context
        from harness_context.application import RefreshService as public_refresh
        from harness_context.application.context_service import ContextService
        from harness_context.application.refresh_service import RefreshService
        from harness_context.application.services import ContextService as legacy_context
        from harness_context.application.services import RefreshService as legacy_refresh

        self.assertIs(ContextService, public_context)
        self.assertIs(ContextService, legacy_context)
        self.assertIs(RefreshService, public_refresh)
        self.assertIs(RefreshService, legacy_refresh)

    def test_domain_does_not_import_transports_or_application_services(self):
        forbidden = ("harness_context.cli", "harness_context.mcp", "harness_context.application")
        for path in (SRC / "harness_context" / "domain").rglob("*.py"):
            leaks = sorted(module for module in imported_modules(path) if module.startswith(forbidden))
            self.assertEqual([], leaks, f"{path.name} crosses into an outer layer: {leaks}")

    def test_engine_is_a_compatibility_facade(self):
        modules = imported_modules(SRC / "harness_context" / "engine.py")
        self.assertEqual({"harness_context.infrastructure.local_engine"}, modules)
