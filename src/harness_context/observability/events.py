from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import ClassVar


class StructuredEventSink:
    _FIELDS: ClassVar = {"request_id", "method", "outcome", "duration_ms"}

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def emit(self, event: str, **fields: object) -> dict[str, object]:
        unknown = set(fields) - self._FIELDS
        if unknown:
            raise ValueError(f"unsupported event fields: {sorted(unknown)}")
        payload = {"event": event, "timestamp": round(time.time(), 3), **fields}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        return payload
