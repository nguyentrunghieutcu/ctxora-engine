"""TTL cache for immutable retrieval selections."""

from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from pathlib import Path


class RetrievalCache:
    def __init__(self, ttl: int = 600):
        self.ttl = ttl
        self.cache: dict[str, tuple[list, float]] = {}

    @staticmethod
    def path_fingerprint(path: str) -> str:
        """Fingerprint a requested source path so changed files cannot hit cache."""
        source = Path(path)
        digest = hashlib.sha256()

        if not source.exists():
            return "missing"

        files = [source] if source.is_file() else sorted(
            candidate for candidate in source.rglob("*") if candidate.is_file()
        )
        for file_path in files:
            stat = file_path.stat()
            digest.update(str(file_path.resolve()).encode())
            digest.update(f"{stat.st_mtime_ns}:{stat.st_size}".encode())
        return digest.hexdigest()

    def _hash(
        self,
        query: str,
        paths: list[str],
        options: dict | None = None,
    ) -> str:
        payload = {
            "query": query,
            "paths": sorted((path, self.path_fingerprint(path)) for path in paths),
            "options": options or {},
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(encoded.encode()).hexdigest()

    def get(
        self,
        query: str,
        paths: list[str],
        options: dict | None = None,
    ) -> list | None:
        key = self._hash(query, paths, options)
        entry = self.cache.get(key)
        if entry is None:
            return None

        data, timestamp = entry
        if time.time() - timestamp >= self.ttl:
            del self.cache[key]
            return None
        return deepcopy(data)

    def set(
        self,
        query: str,
        paths: list[str],
        chunks: list,
        options: dict | None = None,
    ) -> None:
        self.cache[self._hash(query, paths, options)] = (deepcopy(chunks), time.time())

    def invalidate_all(self) -> None:
        self.cache.clear()
