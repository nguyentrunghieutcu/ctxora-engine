from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkspacePolicy:
    roots: tuple[str, ...]
    max_files: int = 10_000
    max_file_bytes: int = 2_000_000
    max_total_bytes: int = 200_000_000


@dataclass
class ContextItem:
    chunk_id: str
    workspace_id: str
    path: str
    start_line: int
    end_line: int
    type: str
    symbol: str
    content: str
    tokens: int
    content_hash: str
    score: float = 0.0
    signals: dict[str, float] = field(default_factory=dict)
    provenance: str = "workspace"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HarnessError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
