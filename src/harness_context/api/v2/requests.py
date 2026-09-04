from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrepareContextRequest:
    workspace_id: str
    query: str
    available_input_tokens: int
    preferred_strategy: str = "auto"
    include_memory: bool = True
    include_handoff: bool = False
    handoff_id: str = ""
    include_ecc: bool = False
    freshness: str = "current"
    deadline_ms: int = 5_000
