from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import ClassVar


class StructuredEventSink:
    _FIELDS: ClassVar = {
        "request_id", "method", "outcome", "duration_ms",
        "action", "status", "receipt_id", "plan_digest",
    }

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

    def query(self, cursor: str = "", limit: int = 50) -> dict[str, object]:
        try:
            offset = int(cursor or 0)
        except (TypeError, ValueError) as error:
            raise ValueError("event cursor must be a non-negative integer") from error
        if offset < 0:
            raise ValueError("event cursor must be a non-negative integer")
        lines = self.path.read_text("utf-8").splitlines() if self.path.exists() else []
        end = min(len(lines), offset + max(0, min(int(limit), 200)))
        items = [json.loads(line) for line in lines[offset:end]]
        return {
            "items": items,
            "cursor": str(offset),
            "next_cursor": str(end),
            "has_more": end < len(lines),
        }
