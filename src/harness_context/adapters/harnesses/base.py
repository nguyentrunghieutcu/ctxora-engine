from __future__ import annotations

from dataclasses import dataclass

from harness_context.domain.artifacts import ArtifactKind
from harness_context.domain.harnesses import HarnessTarget


@dataclass(frozen=True)
class HarnessAdapter:
    target: HarnessTarget

    def destination(self, kind: ArtifactKind | str) -> str:
        value = kind.value if isinstance(kind, ArtifactKind) else str(kind)
        destination = self.target.artifact_root(value)
        if destination is None:
            raise ValueError(f"target {self.target.id} does not support {value}")
        return destination

