import ast
import tempfile
import unittest
from pathlib import Path

from harness_context.domain.chunking import bounded_windows
from harness_context.engine import ContextEngine
from harness_context.infrastructure.parsing import LocalParserDispatcher
from harness_context.infrastructure.scanning import ChangeSet

ROOT = Path(__file__).parents[1]


class PhaseCDomainTests(unittest.TestCase):
    def test_domain_has_no_transport_dependencies(self):
        forbidden = ("harness_context.cli", "harness_context.mcp", "harness_context.application")
        for path in (ROOT / "src" / "harness_context" / "domain").glob("*.py"):
            tree = ast.parse(path.read_text("utf-8"))
            imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
            self.assertFalse([name for name in imports if name.startswith(forbidden)], path)

    def test_change_sets_preserve_files_outside_partial_refresh_scope(self):
        previous = {"/repo/a.py": "old", "/repo/b.py": "same"}
        changes = ChangeSet.calculate(previous, {"/repo/a.py": "new"}, [Path("/repo/a.py")])
        self.assertEqual({"/repo/a.py": "new", "/repo/b.py": "same"}, changes.current)
        self.assertEqual({"/repo/a.py"}, changes.changed)

    def test_fallback_windows_are_bounded_and_overlap(self):
        windows = list(bounded_windows([str(i) for i in range(300)]))
        self.assertEqual((1, 160), windows[0][:2])
        self.assertEqual((141, 300), windows[1][:2])

    def test_parser_chunk_ids_are_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("def useful():\n    return 1\n", encoding="utf-8")
            parser = LocalParserDispatcher()
            self.assertEqual([item.chunk_id for item in parser.parse("w", path)], [item.chunk_id for item in parser.parse("w", path)])

    def test_context_engine_remains_public_compatibility_facade(self):
        self.assertEqual("ContextEngine", ContextEngine.__name__)
        self.assertNotIn("retrieve_context", ContextEngine.__dict__)
