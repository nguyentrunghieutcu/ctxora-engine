from __future__ import annotations

import threading

from harness_context.application.protocols import RefreshCommands, RetrievalQueries


class WorkspaceWatcher:
    """Treat filesystem events as hints and confirm freshness by content hash."""

    def __init__(self, retrieval: RetrievalQueries, refresh: RefreshCommands, workspace_id: str, interval: float = 1.0):
        self.retrieval = retrieval
        self.refresh = refresh
        self.workspace_id = workspace_id
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="harness-watcher", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=max(2.0, self.interval * 2))

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            if not self.retrieval.snapshot_is_current(self.workspace_id):
                try:
                    self.refresh.execute(self.workspace_id)
                except Exception:
                    continue
