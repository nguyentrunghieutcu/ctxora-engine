"""Backward-compatible facade for the local context engine."""

from harness_context.infrastructure.local_engine import LocalContextEngine, WorkspaceState


class ContextEngine(LocalContextEngine):
    """Preserve the historic public type while delegating to local infrastructure."""


__all__ = ["ContextEngine", "WorkspaceState"]
