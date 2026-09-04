import threading
from collections import Counter


class LocalMetrics:
    def __init__(self):
        self._values: Counter[str] = Counter()
        self._lock = threading.Lock()

    def record_request(self, outcome: str, duration_ms: int) -> None:
        if outcome not in {"ok", "error", "rejected"}:
            raise ValueError("unsupported request outcome")
        with self._lock:
            self._values["requests_total"] += 1
            self._values[f"requests_{outcome}"] += 1
            self._values["request_duration_ms_total"] += max(0, int(duration_ms))

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(sorted(self._values.items()))
