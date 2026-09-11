from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ArtifactKind(str, Enum):
    SKILL = "skills"
    AGENT = "agents"
    COMMAND = "commands"
    RULE = "rules"


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: ArtifactKind
    source: str
    compatible_targets: tuple[str, ...] = ()
    provenance: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ArtifactProfile:
    id: str
    artifacts: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class InstallOperation:
    operation: str
    artifact_id: str
    source_path: str
    destination_path: str
    before_hash: str | None = None
    after_hash: str | None = None


@dataclass(frozen=True)
class InstallPlan:
    target: str
    profile: str
    destination: str
    operations: tuple[InstallOperation, ...]
    conflicts: tuple[str, ...] = ()
    skipped: tuple[tuple[str, str], ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    @property
    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "digest": self.digest}


@dataclass(frozen=True)
class InstallReceipt:
    schema_version: str
    plan_digest: str
    target: str
    profile: str
    destination: str
    installed_hashes: tuple[tuple[str, str], ...]
    previous_ownership: tuple[tuple[str, str], ...] = ()
    verified: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

