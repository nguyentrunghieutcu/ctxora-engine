from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class ChangeSet:
    current: dict[str, str]
    changed: set[str]
    removed: set[str]

    @classmethod
    def calculate(cls, previous: Mapping[str, str], discovered: Mapping[str, str], scopes: Sequence[Path] = ()) -> ChangeSet:
        if not scopes:
            current = dict(discovered)
            return cls(current, {p for p, value in current.items() if previous.get(p) != value}, set(previous) - set(current))
        scoped_old = {p for p in previous if any(Path(p) == scope or scope in Path(p).parents for scope in scopes)}
        current = {p: value for p, value in previous.items() if p not in scoped_old}
        current.update(discovered)
        return cls(current, {p for p, value in discovered.items() if previous.get(p) != value}, scoped_old - set(discovered))


class LocalManifest:
    @staticmethod
    def snapshot_id(version: int, fingerprints: Mapping[str, str]) -> str:
        manifest = [(path, fingerprints[path]) for path in sorted(fingerprints)]
        return hashlib.sha256(json.dumps([version, manifest]).encode()).hexdigest()


class LocalScanner:
    def __init__(self, registry) -> None:
        self.registry = registry

    def scan(self, workspace_id: str, requested: Sequence[str]) -> list[Path]:
        return self.registry.files(workspace_id, list(requested))

    @staticmethod
    def fingerprints(files: Sequence[Path]) -> dict[str, str]:
        return {str(path): fingerprint(path) for path in files}
