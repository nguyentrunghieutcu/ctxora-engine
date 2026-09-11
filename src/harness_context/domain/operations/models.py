from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class OperatorSnapshot:
    schema_version: str
    status: str
    ready: bool
    runtime: dict[str, Any]
    workspace: dict[str, Any]
    snapshot: dict[str, Any]
    index: dict[str, Any]
    retrieval: dict[str, Any]
    memory: dict[str, Any]
    handoffs: dict[str, Any]
    skills: dict[str, Any]
    installer: dict[str, Any]
    metrics: dict[str, Any]
    events: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionPlan:
    action: str
    workspace_id: str
    parameters: dict[str, Any]
    summary: dict[str, Any]
    created_at: float
    expires_at: float
    schema_version: str = field(default="ctxora.action-plan.v1", init=False)

    @property
    def digest(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "action": self.action,
            "workspace_id": self.workspace_id,
            "parameters": self.parameters,
            "summary": self.summary,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "digest": self.digest}


@dataclass(frozen=True)
class ActionReceipt:
    action: str
    status: str
    plan_digest: str
    details: dict[str, Any] = field(default_factory=dict)
    schema_version: str = field(default="ctxora.action-receipt.v1", init=False)
    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
