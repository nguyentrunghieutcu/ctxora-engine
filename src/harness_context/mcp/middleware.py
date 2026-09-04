from __future__ import annotations

import time
import uuid
from functools import wraps


class RequestMiddleware:
    def __init__(self, lifecycle, events, metrics):
        self.lifecycle = lifecycle
        self.events = events
        self.metrics = metrics

    async def __call__(self, context, call_next):
        request_id = uuid.uuid4().hex
        method = str(getattr(context, "method", "unknown"))
        started = time.monotonic()
        if not self.lifecycle.begin_request():
            self._complete(request_id, method, "rejected", started)
            raise RuntimeError("server is draining")
        try:
            result = await call_next(context)
        except Exception:
            self._complete(request_id, method, "error", started)
            raise
        else:
            self._complete(request_id, method, "ok", started)
            return result
        finally:
            self.lifecycle.end_request()

    def wrap(self, method: str, function):
        @wraps(function)
        def tracked(*args, **kwargs):
            request_id = uuid.uuid4().hex
            started = time.monotonic()
            if not self.lifecycle.begin_request():
                self._complete(request_id, method, "rejected", started)
                raise RuntimeError("server is draining")
            try:
                result = function(*args, **kwargs)
            except Exception:
                self._complete(request_id, method, "error", started)
                raise
            else:
                self._complete(request_id, method, "ok", started)
                return result
            finally:
                self.lifecycle.end_request()

        return tracked

    def _complete(self, request_id: str, method: str, outcome: str, started: float) -> None:
        duration = int((time.monotonic() - started) * 1000)
        self.metrics.record_request(outcome, duration)
        self.events.emit("request.completed", request_id=request_id, method=method,
                         outcome=outcome, duration_ms=duration)
