from __future__ import annotations

import threading
import time

from mcp.server.fastmcp import FastMCP

from harness_context.mcp.capabilities import SERVER_NAME
from harness_context.mcp.middleware import RequestMiddleware
from harness_context.mcp.tools import register_tools
from harness_context.observability import LocalMetrics, StructuredEventSink


class ServerLifecycle:
    def __init__(self):
        self._condition = threading.Condition()
        self._ready = False
        self._draining = False
        self._active_requests = 0

    def mark_ready(self) -> None:
        with self._condition:
            self._ready = True

    def begin_request(self) -> bool:
        with self._condition:
            if not self._ready or self._draining:
                return False
            self._active_requests += 1
            return True

    def end_request(self) -> None:
        with self._condition:
            self._active_requests = max(0, self._active_requests - 1)
            self._condition.notify_all()

    def drain(self, timeout: float = 10.0) -> bool:
        deadline = time.monotonic() + timeout
        with self._condition:
            self._draining = True
            while self._active_requests and time.monotonic() < deadline:
                self._condition.wait(max(0, deadline - time.monotonic()))
            return self._active_requests == 0

    def status(self) -> dict[str, object]:
        with self._condition:
            return {"ready": self._ready and not self._draining,
                    "draining": self._draining, "active_requests": self._active_requests}


def create_mcp_server(container, default_workspace_id: str, lifecycle=None,
                      events=None, metrics=None) -> FastMCP:
    server = FastMCP(SERVER_NAME)
    register_tools(server, container, default_workspace_id)
    lifecycle = lifecycle or ServerLifecycle()
    events = events or StructuredEventSink(container.snapshots.state_dir / "events.jsonl")
    metrics = metrics or LocalMetrics()
    middleware = RequestMiddleware(lifecycle, events, metrics)
    target = getattr(server, "middleware", None)
    if target is None:
        target = getattr(getattr(server, "_mcp_server", None), "middleware", None)
    if target is not None:
        target.append(middleware)
    else:
        for tool in server._tool_manager._tools.values():
            tool.fn = middleware.wrap(tool.name, tool.fn)
    lifecycle.mark_ready()
    server.ctxora_lifecycle = lifecycle
    server.ctxora_metrics = metrics
    server.harness_lifecycle = lifecycle
    server.harness_metrics = metrics
    return server
