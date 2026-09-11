"""
chunking/treesitter_chunker.py — AST-based code chunker
=========================================================
Uses tree-sitter to split files into function/class-level chunks.
Falls back to file-level chunking for unsupported languages.

Token counting:
  - tiktoken (cl100k_base) for accurate GPT/Codex token counts
  - Falls back to len//3.5 heuristic if tiktoken unavailable
"""

from __future__ import annotations

import ast
import hashlib
import os
from dataclasses import dataclass, field

# ── Token counting ────────────────────────────────────────────────────────────

try:
    import tiktoken as _tiktoken
    # cl100k_base covers: gpt-4, gpt-3.5-turbo, gpt-4o, codex-mini, o1/o3/o4
    # o200k_base covers: gpt-4o (newer), but cl100k_base is ≥95% accurate for both
    _ENCODER = _tiktoken.get_encoding("cl100k_base")
    _HAS_TIKTOKEN = True
except Exception:
    _HAS_TIKTOKEN = False
    _ENCODER = None  # type: ignore[assignment]


def count_tokens(text: str) -> int:
    """
    Count tokens in text.

    Uses tiktoken (cl100k_base) for OpenAI-compatible accuracy.
    Falls back to len/3.5 heuristic if tiktoken is unavailable.

    cl100k_base is accurate for:
      - GPT-4, GPT-4o, GPT-4.1, GPT-4.5, GPT-5.x
      - GPT-3.5-turbo
      - o1, o3, o4-mini
      - codex-mini-latest
      - Claude (close approximation, actual tokenizer differs ~5%)
      - Gemini (close approximation)
    """
    if not text:
        return 0
    if _HAS_TIKTOKEN and _ENCODER is not None:
        return len(_ENCODER.encode(text, disallowed_special=()))
    # Fallback: code typically has ratio 3.2–3.8 chars/token; use 3.5
    return max(1, int(len(text) / 3.5))


# ── Chunk dataclass ───────────────────────────────────────────────────────────

@dataclass
class Chunk:
    id: str
    path: str
    type: str
    symbol: str
    content: str
    summary: str
    tokens: int
    embedding: list[float] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    priority: int = 5
    workspace_id: str = "legacy_global"
    start_line: int = 1
    end_line: int = 1
    content_hash: str = ""

    @staticmethod
    def stable_id(path: str, kind: str, symbol: str, start_line: int, end_line: int, content: str) -> str:
        payload = f"{path}\0{kind}\0{symbol}\0{start_line}\0{end_line}\0{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── AST Chunker ───────────────────────────────────────────────────────────────

class ASTChunker:
    def __init__(self):
        try:
            import tree_sitter
            import tree_sitter_javascript
            import tree_sitter_python
            import tree_sitter_typescript
            self.ts = tree_sitter
            self.lang_py = tree_sitter.Language(tree_sitter_python.language())
            self.lang_js = tree_sitter.Language(
                tree_sitter_javascript.language())
            self.lang_ts = tree_sitter.Language(
                tree_sitter_typescript.language_typescript())
        except ImportError:
            self.ts = None

    def get_parser(self, ext: str):
        if not self.ts:
            return None
        parser = self.ts.Parser()
        if ext == ".py":
            parser.language = self.lang_py
        elif ext in [".js", ".jsx"]:
            parser.language = self.lang_js
        elif ext in [".ts", ".tsx"]:
            parser.language = self.lang_ts
        else:
            return None
        return parser

    def chunk_paths(self, paths: list[str]) -> list[Chunk]:
        chunks = []
        for path in paths:
            if not os.path.exists(path):
                continue
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        filepath = os.path.join(root, file)
                        chunks.extend(self._chunk_file(filepath))
            else:
                chunks.extend(self._chunk_file(path))
        return chunks

    def _chunk_file(self, filepath: str) -> list[Chunk]:
        chunks = []
        ext = os.path.splitext(filepath)[1]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []

        if ext == ".py":
            try:
                tree = ast.parse(content)
            except SyntaxError:
                tree = None
            if tree is not None:
                lines = content.splitlines()
                import_nodes = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
                import_end = max((node.end_lineno or node.lineno for node in import_nodes), default=0)
                import_context = "\n".join(lines[:import_end])
                python_chunks = []
                for node in tree.body:
                    if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    start_line = min([node.lineno] + [decorator.lineno for decorator in node.decorator_list])
                    end_line = node.end_lineno or start_line
                    body = "\n".join(lines[start_line - 1:end_line])
                    chunk_content = f"{import_context}\n\n{body}" if import_context else body
                    kind = "class_definition" if isinstance(node, ast.ClassDef) else "function_definition"
                    python_chunks.append(Chunk(
                        id=Chunk.stable_id(filepath, kind, node.name, start_line, end_line, chunk_content),
                        path=filepath, type=kind, symbol=node.name, content=chunk_content,
                        summary=f"{kind} {node.name}", tokens=count_tokens(chunk_content),
                        start_line=start_line, end_line=end_line,
                        content_hash=hashlib.sha256(chunk_content.encode("utf-8")).hexdigest(),
                    ))
                if python_chunks:
                    return python_chunks

        parser = self.get_parser(ext)
        if parser is None:
            # Fallback to file-level chunk
            return [
                Chunk(
                    id=Chunk.stable_id(filepath, "file", "module", 1, len(content.splitlines()), content),
                    path=filepath,
                    type="file",
                    symbol="module",
                    content=content,
                    summary="",
                    tokens=count_tokens(content),
                    start_line=1,
                    end_line=max(1, len(content.splitlines())),
                    content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                )
            ]

        tree = parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        content_bytes = bytes(content, "utf8")

        def traverse(node):
            if node.type in [
                "class_definition",
                "function_definition",
                "class_declaration",
                "function_declaration",
                "method_definition",
            ]:
                chunk_content = content_bytes[
                    node.start_byte:node.end_byte
                ].decode("utf-8")
                symbol_name = "unknown"
                for child in node.children:
                    if child.type == "identifier":
                        symbol_name = content_bytes[
                            child.start_byte:child.end_byte
                        ].decode("utf-8")
                        break

                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                chunks.append(Chunk(
                    id=Chunk.stable_id(filepath, node.type, symbol_name, start_line, end_line, chunk_content),
                    path=filepath,
                    type=node.type,
                    symbol=symbol_name,
                    content=chunk_content,
                    summary=f"{node.type} {symbol_name}",
                    tokens=count_tokens(chunk_content),
                    start_line=start_line,
                    end_line=end_line,
                    content_hash=hashlib.sha256(chunk_content.encode("utf-8")).hexdigest(),
                ))
            for child in node.children:
                traverse(child)

        traverse(root_node)

        # If no chunks extracted, add file as a module chunk
        if not chunks:
            chunks.append(Chunk(
                id=Chunk.stable_id(filepath, "module", "module", 1, len(content.splitlines()), content),
                path=filepath,
                type="module",
                symbol="module",
                content=content,
                summary="",
                tokens=count_tokens(content),
                start_line=1,
                end_line=max(1, len(content.splitlines())),
                content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            ))

        return chunks
