from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from harness_context.schemas import ContextItem


class ContextPlanner:
    STABLE_FILES = {"AGENTS.md", "CLAUDE.md", "README.md", "pyproject.toml"}

    @classmethod
    def is_stable(cls, item: ContextItem) -> bool:
        return Path(item.path).name in cls.STABLE_FILES or "/docs/" in item.path

    def plan(self, workspace_id: str, query: str, available: int, items: Sequence[ContextItem], override: str = "") -> dict:
        corpus = sum(item.tokens for item in items)
        stable = sum(item.tokens for item in items if self.is_stable(item))
        repo_wide = any(word in query.casefold() for word in ("architecture", "kiến trúc", "repo", "toàn bộ", "cross-module"))
        if override:
            strategy, reason, confidence = override, "Caller override requested.", 1.0
        elif corpus <= available * 0.7:
            strategy, reason, confidence = "long_context", "Authorized corpus fits comfortably in the supplied budget.", 0.84
        elif stable and repo_wide:
            strategy, reason, confidence = "hybrid_cag_rag", "Reusable stable core plus fresh cross-file evidence is required.", 0.88
        elif repo_wide:
            strategy, reason, confidence = "graph_augmented", "Cross-module query benefits from parsed dependency expansion.", 0.78
        else:
            strategy, reason, confidence = "hybrid_rag", "Narrow task over a larger changing corpus.", 0.82
        return {"workspace_id": workspace_id, "strategy": strategy, "reason": reason, "confidence": confidence, "estimated_context_tokens": min(corpus, available), "rag_budget_tokens": min(5000, available), "graph_expand": strategy in {"hybrid_cag_rag", "graph_augmented"}, "alternatives": ["hybrid_rag"] if strategy != "hybrid_rag" else ["long_context"], "override_allowed": True}
