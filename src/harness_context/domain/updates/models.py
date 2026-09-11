from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class UpdateCheck:
    current_version: str
    latest_version: str
    update_available: bool
    checked_at: float
    cached: bool = False
    schema_version: str = field(default="ctxora.update-check.v1", init=False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UpdatePlan:
    current_version: str
    target_version: str
    package: str
    scope: str
    mcp_profiles: tuple[str, ...]
    skill_installs: tuple[tuple[str, str], ...]
    manual_skill_targets: tuple[str, ...]
    created_at: float
    expires_at: float
    schema_version: str = field(default="ctxora.update-plan.v1", init=False)

    @property
    def digest(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "package": self.package,
            "scope": self.scope,
            "mcp_profiles": self.mcp_profiles,
            "skill_installs": self.skill_installs,
            "manual_skill_targets": self.manual_skill_targets,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "digest": self.digest}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> UpdatePlan:
        return cls(
            current_version=str(payload["current_version"]),
            target_version=str(payload["target_version"]),
            package=str(payload["package"]),
            scope=str(payload["scope"]),
            mcp_profiles=tuple(payload.get("mcp_profiles", ())),
            skill_installs=tuple(tuple(item) for item in payload.get("skill_installs", ())),
            manual_skill_targets=tuple(payload.get("manual_skill_targets", ())),
            created_at=float(payload["created_at"]),
            expires_at=float(payload["expires_at"]),
        )


@dataclass(frozen=True)
class UpdateReceipt:
    current_version: str
    target_version: str
    status: str
    plan_digest: str
    details: dict[str, Any] = field(default_factory=dict)
    schema_version: str = field(default="ctxora.update-receipt.v1", init=False)
    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
