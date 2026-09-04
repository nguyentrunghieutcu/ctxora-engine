from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from harness_context.schemas import ContextItem


class FileScanner(Protocol):
    def scan(self, workspace_id: str, requested: Sequence[str]) -> list[Path]: ...


class ChunkParser(Protocol):
    def parse(self, workspace_id: str, path: Path) -> list[ContextItem]: ...


class SearchIndex(Protocol):
    def rebuild(self, items: Sequence[ContextItem]) -> None: ...
    def scores(self, query: str, items: Sequence[ContextItem]) -> list[float]: ...


class DependencyGraph(Protocol):
    def build(self, items: Sequence[ContextItem]) -> dict[str, set[str]]: ...
