from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from chunking.treesitter_chunker import count_tokens
from harness_context.domain.chunking import bounded_windows, stable_chunk_id
from harness_context.schemas import ContextItem


class LocalParserDispatcher:
    @staticmethod
    def _item(workspace_id: str, path: Path, kind: str, symbol: str, start: int, end: int, content: str) -> ContextItem:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return ContextItem(chunk_id=stable_chunk_id(workspace_id, path, kind, symbol, start, end, digest), workspace_id=workspace_id, path=str(path), start_line=start, end_line=end, type=kind, symbol=symbol, content=content, tokens=count_tokens(content), content_hash=digest)

    def parse(self, workspace_id: str, path: Path) -> list[ContextItem]:
        text = path.read_text("utf-8"); lines = text.splitlines()
        if path.suffix == ".py":
            try: tree = ast.parse(text)
            except SyntaxError: tree = None
            if tree is not None:
                imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
                prefix_end = max((node.end_lineno or node.lineno for node in imports), default=0); prefix = "\n".join(lines[:prefix_end]); chunks = []
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]); end = node.end_lineno or start; body = "\n".join(lines[start - 1:end]); content = f"{prefix}\n\n{body}" if prefix else body
                        chunks.append(self._item(workspace_id, path, "class" if isinstance(node, ast.ClassDef) else "function", node.name, start, end, content))
                module_lines = [line for index, line in enumerate(lines, 1) if index <= prefix_end or not any(item.start_line <= index <= item.end_line for item in chunks)]
                module = "\n".join(module_lines).strip()
                if module: chunks.insert(0, self._item(workspace_id, path, "module", path.stem, 1, len(lines), module))
                return chunks
        if path.suffix.lower() in {".md", ".markdown"}:
            starts = [index for index, line in enumerate(lines) if line.startswith("#")]
            if starts:
                starts.append(len(lines)); return [self._item(workspace_id, path, "section", lines[start].lstrip("# ") or "section", start + 1, starts[pos + 1], "\n".join(lines[start:starts[pos + 1]])) for pos, start in enumerate(starts[:-1])]
        return [self._item(workspace_id, path, "file", path.name, start, end, content) for start, end, content in bounded_windows(lines)]
