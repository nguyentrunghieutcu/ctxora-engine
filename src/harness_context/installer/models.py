from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Mutation:
    operation: str
    path: str
    before: Any
    after: Any


@dataclass(frozen=True)
class MutationPlan:
    profile: str
    config_path: str
    mutations: tuple[Mutation, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
