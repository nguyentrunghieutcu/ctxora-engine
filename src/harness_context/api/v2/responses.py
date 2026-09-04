from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContextPackageV2:
    api_version: str
    workspace_id: str
    snapshot_id: str
    snapshot_version: int
    plan: dict[str, Any]
    stable_context: dict[str, Any] | None
    evidence: dict[str, Any] | None
    memory: list[dict[str, Any]] = field(default_factory=list)
    handoff: dict[str, Any] | None = None
    external_context: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
