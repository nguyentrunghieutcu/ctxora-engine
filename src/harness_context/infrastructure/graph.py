from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from harness_context.schemas import ContextItem


class LocalGraphBuilder:
    def build(self, items: Sequence[ContextItem]) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = defaultdict(set); by_symbol = {item.symbol: item.chunk_id for item in items if item.symbol}; by_path = {item.path: item.chunk_id for item in items if item.type == "module"}
        for item in items:
            if Path(item.path).suffix != ".py": continue
            try: tree = ast.parse(item.content)
            except SyntaxError: continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
                    if name in by_symbol and by_symbol[name] != item.chunk_id: graph[item.chunk_id].add(by_symbol[name])
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for path, target in by_path.items():
                            if Path(path).stem == alias.name.split(".")[-1]: graph[item.chunk_id].add(target)
        return graph
