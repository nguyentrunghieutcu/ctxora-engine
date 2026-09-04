from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContextDiagnostics:
    coverage: str = "not_applicable"
    freshness: str = "current"
    untrusted_content: bool = True
    latency_ms: float = 0.0
    ecc: dict[str, Any] = field(default_factory=dict)
