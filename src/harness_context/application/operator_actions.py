from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from harness_context.domain.operations import ActionPlan, ActionReceipt, OperatorSnapshot
from harness_context.paths import workspace_data_dir
from harness_context.skills.catalog import SKILL_TARGET_NAMES, SkillCatalog

SUPPORTED_ACTIONS = (
    "refresh",
    "invalidate",
    "purge_expired_handoffs",
    "repair_index",
    "diagnostics_export",
    "install_preview",
    "update_check",
    "update_plan",
)

class OperatorActionService:
    def __init__(
        self,
        engine,
        refresh,
        handoffs,
        events,
        snapshot: Callable[[str], OperatorSnapshot],
        updates,
        catalog: SkillCatalog | None = None,
        plan_ttl_seconds: int = 300,
    ):
        self.engine = engine
        self.refresh = refresh
        self.handoffs = handoffs
        self.events = events
        self.snapshot = snapshot
        self.updates = updates
        self.catalog = catalog or SkillCatalog()
        self.plan_ttl_seconds = max(1, int(plan_ttl_seconds))
        self._plans: dict[tuple[str, str], ActionPlan] = {}
        self._lock = threading.Lock()

    def available(self) -> tuple[str, ...]:
        return SUPPORTED_ACTIONS

    def plan(self, workspace_id: str, action: str, parameters: dict[str, Any] | None = None) -> ActionPlan:
        if action not in SUPPORTED_ACTIONS:
            raise ValueError(f"unsupported action: {action}")
        self.engine.registry.get(workspace_id)
        normalized = self._normalize(workspace_id, action, parameters or {})
        now = time.time()
        plan = ActionPlan(
            action=action,
            workspace_id=workspace_id,
            parameters=normalized,
            summary=self._summary(action, normalized),
            created_at=now,
            expires_at=now + self.plan_ttl_seconds,
        )
        with self._lock:
            self._plans[(workspace_id, plan.digest)] = deepcopy(plan)
        self.events.emit("operator_action", action=action, status="planned", plan_digest=plan.digest)
        return plan

    def execute(self, workspace_id: str, plan_digest: str, *, confirmed: bool) -> ActionReceipt:
        if not confirmed:
            raise ValueError("explicit confirmation is required")
        key = (workspace_id, str(plan_digest))
        with self._lock:
            plan = self._plans.pop(key, None)
        if plan is None or plan.expires_at < time.time():
            raise ValueError("action plan is unknown or expired; preview again")
        try:
            status, details = self._execute(plan)
        except Exception:
            self.events.emit("operator_action", action=plan.action, status="failed", plan_digest=plan.digest)
            raise
        receipt = ActionReceipt(plan.action, status, plan.digest, details)
        self.events.emit(
            "operator_action",
            action=plan.action,
            status=status,
            receipt_id=receipt.receipt_id,
            plan_digest=plan.digest,
        )
        return receipt

    def _execute(self, plan: ActionPlan) -> tuple[str, dict[str, Any]]:
        if plan.action == "refresh":
            return "completed", self._index_details(self.refresh.execute(plan.workspace_id))
        if plan.action == "repair_index":
            return "completed", self._index_details(self.refresh.repair(plan.workspace_id))
        if plan.action == "invalidate":
            result = self.refresh.invalidate(plan.workspace_id, plan.parameters["target"])
            return "completed", self._index_details(result)
        if plan.action == "purge_expired_handoffs":
            return "completed", {"purged": self.handoffs.purge_expired()}
        if plan.action == "diagnostics_export":
            return "completed", self._export_diagnostics(plan)
        if plan.action == "install_preview":
            return "previewed", self._install_preview(plan)
        if plan.action == "update_check":
            return "completed", self.updates.check(force=True).to_dict()
        if plan.action == "update_plan":
            update = self.updates.plan()
            return "planned", {
                "current_version": update.current_version,
                "target_version": update.target_version,
                "scope": update.scope,
                "mcp_profile_count": len(update.mcp_profiles),
                "skill_target_count": len(update.skill_installs),
                "manual_skill_targets": list(update.manual_skill_targets),
                "update_plan_digest": update.digest,
                "expires_at": update.expires_at,
            }
        raise ValueError(f"unsupported action: {plan.action}")

    def _normalize(self, workspace_id: str, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(parameters, dict):
            raise TypeError("action parameters must be an object")
        allowed = {
            "refresh": set(), "repair_index": set(), "purge_expired_handoffs": set(),
            "update_check": set(), "update_plan": set(),
            "invalidate": {"target"}, "diagnostics_export": {"name"},
            "install_preview": {
                "target", "output", "profile", "add_modules", "remove_modules",
                "add_skills", "remove_skills", "force", "prune",
            },
        }[action]
        unknown = set(parameters) - allowed
        if unknown:
            raise ValueError(f"unsupported action parameters: {sorted(unknown)}")
        if action == "invalidate":
            target = str(parameters.get("target", "all"))
            if target not in {"all", "index", "bundles"}:
                raise ValueError("invalidate target must be all, index, or bundles")
            return {"target": target}
        if action == "diagnostics_export":
            name = str(parameters.get("name", "ctxora-diagnostics.json"))
            self._export_path(workspace_id, name)
            return {"name": name}
        if action == "install_preview":
            return self._normalize_install(workspace_id, parameters)
        return {}

    def _normalize_install(self, workspace_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        target = str(parameters.get("target", "codex"))
        output = str(parameters.get("output", ""))
        if target == "custom":
            if not output:
                raise ValueError("custom install preview requires a workspace-relative output")
            root = self._workspace_root(workspace_id)
            path = Path(output)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("custom install preview output must stay inside the workspace")
            self.engine.registry.authorize(workspace_id, [str(root / path)])
        elif target not in SKILL_TARGET_NAMES:
            raise ValueError(f"unknown skill install target: {target}")
        elif output:
            raise ValueError("output is only supported for the custom install target")
        normalized: dict[str, Any] = {
            "target": target,
            "profile": str(parameters.get("profile", "developer")),
        }
        for key in ("force", "prune"):
            value = parameters.get(key, False)
            if not isinstance(value, bool):
                raise TypeError(f"{key} must be a boolean")
            normalized[key] = value
        if output:
            normalized["output"] = output
        for key in ("add_modules", "remove_modules", "add_skills", "remove_skills"):
            values = parameters.get(key, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise ValueError(f"{key} must be an array of names")
            if any(not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value) for value in values):
                raise ValueError(f"{key} contains an unsafe name")
            normalized[key] = sorted(set(values))
        return normalized

    @staticmethod
    def _summary(action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if action == "install_preview":
            return {"target": parameters["target"], "profile": parameters["profile"]}
        if action == "diagnostics_export":
            return {"export": parameters["name"]}
        if action == "invalidate":
            return {"target": parameters["target"]}
        return {"scope": "workspace"}

    def _export_diagnostics(self, plan: ActionPlan) -> dict[str, Any]:
        path = self._export_path(plan.workspace_id, plan.parameters["name"])
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.snapshot(plan.workspace_id).to_dict()
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(text)
            temporary = Path(handle.name)
        os.replace(temporary, path)
        data_root = workspace_data_dir(self._workspace_root(plan.workspace_id))
        return {
            "name": path.relative_to(data_root).as_posix(),
            "bytes": len(text.encode("utf-8")),
            "snapshot_id": payload.get("snapshot", {}).get("snapshot_id", ""),
        }

    def _install_preview(self, plan: ActionPlan) -> dict[str, Any]:
        parameters = plan.parameters
        selection = self.catalog.select(
            parameters["profile"],
            add_modules=tuple(parameters["add_modules"]),
            remove_modules=tuple(parameters["remove_modules"]),
            add_skills=tuple(parameters["add_skills"]),
            remove_skills=tuple(parameters["remove_skills"]),
        )
        if parameters["target"] == "custom":
            target, output = "custom", parameters["output"]
        else:
            target, output = self.catalog.install_outputs((parameters["target"],))[0]
        preview = self.catalog.plan_install(
            self._workspace_root(plan.workspace_id), output, selection,
            force=parameters["force"], prune=parameters["prune"], target=target,
        )
        counts: dict[str, int] = {}
        for operation in preview.operations:
            counts[operation.operation] = counts.get(operation.operation, 0) + 1
        return {
            "target": preview.target,
            "profile": preview.profile,
            "operation_count": len(preview.operations),
            "operations": counts,
            "conflicts": list(preview.conflicts),
            "skipped_count": len(preview.skipped),
            "install_plan_digest": preview.digest,
        }

    def _export_path(self, workspace_id: str, name: str) -> Path:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".json":
            raise ValueError("diagnostics export must be a relative .json path")
        exports = workspace_data_dir(self._workspace_root(workspace_id)) / "exports"
        path = (exports / relative).resolve()
        if exports.resolve() not in path.parents:
            raise ValueError("diagnostics export must stay inside the workspace export directory")
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent.exists()):
            raise ValueError("diagnostics export path cannot contain symlinks")
        return path

    def _workspace_root(self, workspace_id: str) -> Path:
        return Path(self.engine.registry.get(workspace_id).roots[0])

    @staticmethod
    def _index_details(result: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "status", "snapshot_id", "snapshot_version", "files", "chunks", "tokens",
            "graph_edges", "bundles", "invalidated", "refreshed_at",
        }
        return {key: result[key] for key in allowed if key in result}
