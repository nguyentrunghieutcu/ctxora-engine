from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_context.application.operator_actions import OperatorActionService
from harness_context.domain.operations import OperatorSnapshot
from harness_context.paths import workspace_installer_dir


class OperatorService:
    def __init__(self, engine, retrieval, memory, handoffs, skills, events, metrics, refresh, updates):
        self.engine = engine
        self.retrieval = retrieval
        self.memory = memory
        self.handoffs = handoffs
        self.skills = skills
        self.events = events
        self.metrics = metrics
        self.actions = OperatorActionService(
            engine, refresh, handoffs, events, lambda workspace_id: self.snapshot(workspace_id), updates
        )

    def available_actions(self) -> tuple[str, ...]:
        return self.actions.available()

    def plan_action(self, workspace_id: str, action: str, parameters: dict[str, Any] | None = None):
        return self.actions.plan(workspace_id, action, parameters)

    def execute_action(self, workspace_id: str, plan_digest: str, *, confirmed: bool):
        return self.actions.execute(workspace_id, plan_digest, confirmed=confirmed)

    def snapshot(
        self,
        workspace_id: str,
        runtime: dict[str, Any] | None = None,
        event_cursor: str = "",
        event_limit: int = 20,
    ) -> OperatorSnapshot:
        runtime = dict(runtime or {})
        stats = self.retrieval.stats(workspace_id)
        policy = self.engine.registry.get(workspace_id)
        handoffs = self.handoffs.list(workspace_id, 5)
        installer = self._installer_summary(Path(policy.roots[0]))
        events = self.events_page(event_cursor, event_limit)
        ready = bool(runtime.get("ready", stats.get("status") == "ready"))
        return OperatorSnapshot(
            schema_version="ctxora.operator-snapshot.v1",
            status="ready" if ready else "not_ready",
            ready=ready,
            runtime=runtime,
            workspace={"workspace_id": workspace_id, "root_count": len(policy.roots)},
            snapshot={
                "snapshot_id": stats.get("snapshot_id", ""),
                "snapshot_version": stats.get("snapshot_version", 0),
                "status": stats.get("status", "unknown"),
                "refreshed_at": stats.get("refreshed_at", 0),
            },
            index={
                "files": stats.get("files", 0),
                "chunks": stats.get("chunks", 0),
                "tokens": stats.get("tokens", 0),
                "graph_edges": stats.get("graph_edges", 0),
                "bundles": stats.get("bundles", 0),
                "current": self.retrieval.snapshot_is_current(workspace_id),
            },
            retrieval={
                "last_retrieval_ms": stats.get("last_retrieval_ms", 0),
                "last_coverage": stats.get("last_coverage", {}),
                "adapters": stats.get("adapters", {}),
            },
            memory=self.memory.stats(),
            handoffs={
                "count": len(self.handoffs.list(workspace_id, 10_000)),
                "recent": [self._handoff_summary(handoff) for handoff in handoffs],
            },
            skills=self.skills.learning_status(workspace_id, 10),
            installer=installer,
            metrics=self.metrics.snapshot(),
            events=events,
        )

    def events_page(self, cursor: str = "", limit: int = 50) -> dict[str, object]:
        return self.events.query(cursor, limit)

    @staticmethod
    def _handoff_summary(handoff: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "handoff_id",
            "provider",
            "token_count",
            "history_tokens",
            "created_at",
            "expires_at",
        }
        return {key: handoff[key] for key in allowed if key in handoff}

    @staticmethod
    def _installer_summary(workspace: Path) -> dict[str, Any]:
        receipts = []
        directory = workspace_installer_dir(workspace)
        for path in sorted(directory.glob("*.json")) if directory.is_dir() else ():
            try:
                payload = json.loads(path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                receipts.append({"name": path.name, "status": "invalid"})
                continue
            if path.name == "ownership.json" and "schema_version" not in payload:
                receipts.extend(
                    {
                        "name": path.name,
                        "schema_version": "ctxora.mcp-ownership.v1",
                        "target": target,
                        "profile": "mcp",
                        "verified": bool(record.get("installed")),
                        "plan_digest": "",
                    }
                    for target, record in sorted(payload.items())
                    if isinstance(record, dict)
                )
                continue
            receipts.append(
                {
                    "name": path.name,
                    "schema_version": payload.get("schema_version", "legacy"),
                    "target": payload.get("target", ""),
                    "profile": payload.get("profile", ""),
                    "verified": bool(payload.get("verified", False)),
                    "plan_digest": payload.get("plan_digest", ""),
                }
            )
        return {"receipt_count": len(receipts), "receipts": receipts}
