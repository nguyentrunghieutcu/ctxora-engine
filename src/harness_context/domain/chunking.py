from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path


def stable_chunk_id(workspace_id: str, path: Path, kind: str, symbol: str, start: int, end: int, content_hash: str) -> str:
    identity = f"{workspace_id}\0{path}\0{kind}\0{symbol}\0{start}\0{end}\0{content_hash}"
    return hashlib.sha256(identity.encode()).hexdigest()


def bounded_windows(lines: list[str], window: int = 160, overlap: int = 20) -> Iterator[tuple[int, int, str]]:
    if window <= 0 or overlap < 0 or overlap >= window:
        raise ValueError("window must be positive and overlap smaller than window")
    for offset in range(0, max(1, len(lines)), window - overlap):
        yield offset + 1, min(offset + window, len(lines)), "\n".join(lines[offset:offset + window])
