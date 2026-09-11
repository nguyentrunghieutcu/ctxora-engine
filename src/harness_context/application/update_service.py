from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from harness_context.adapters.releases import NpmReleaseRegistry
from harness_context.domain.updates import UpdateCheck, UpdatePlan, UpdateReceipt
from harness_context.paths import workspace_data_dir, workspace_installer_dir
from harness_context.skills import SkillCatalog


class ReleaseRegistry(Protocol):
    def latest(self) -> str: ...


Runner = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str]]
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class UpdateService:
    def __init__(
        self,
        workspace: str | Path,
        current_version: str,
        *,
        registry: ReleaseRegistry | None = None,
        runner: Runner | None = None,
        clock: Callable[[], float] = time.time,
        cache_ttl_seconds: int = 86_400,
        plan_ttl_seconds: int = 900,
        events=None,
    ):
        self.workspace = Path(workspace).expanduser().resolve(strict=True)
        self.current_version = self._validate_version(current_version)
        self.registry = registry or NpmReleaseRegistry()
        self.runner = runner or self._run
        self.clock = clock
        self.cache_ttl_seconds = max(0, int(cache_ttl_seconds))
        self.plan_ttl_seconds = max(1, int(plan_ttl_seconds))
        self.events = events
        self.state_dir = workspace_data_dir(self.workspace) / "updates"

    def check(self, *, force: bool = False) -> UpdateCheck:
        now = self.clock()
        cache_path = self.state_dir / "check.json"
        if not force and cache_path.is_file():
            payload = self._read_json(cache_path)
            if (
                payload.get("current_version") == self.current_version
                and now - float(payload.get("checked_at", 0)) <= self.cache_ttl_seconds
            ):
                return UpdateCheck(
                    self.current_version,
                    self._validate_version(str(payload["latest_version"])),
                    bool(payload["update_available"]),
                    float(payload["checked_at"]),
                    cached=True,
                )
        latest = self._validate_version(self.registry.latest())
        result = UpdateCheck(
            self.current_version,
            latest,
            self._version_tuple(latest) > self._version_tuple(self.current_version),
            now,
        )
        self._write_json(cache_path, result.to_dict())
        self._emit("checked", "")
        return result

    def plan(self) -> UpdatePlan:
        check = self.check(force=True)
        if not check.update_available:
            raise ValueError("no newer CTXORA release is available")
        now = self.clock()
        skill_installs, manual_skill_targets = self._owned_skill_state()
        plan = UpdatePlan(
            current_version=self.current_version,
            target_version=check.latest_version,
            package="ctxora",
            scope="npm-global",
            mcp_profiles=self._owned_mcp_profiles(),
            skill_installs=skill_installs,
            manual_skill_targets=manual_skill_targets,
            created_at=now,
            expires_at=now + self.plan_ttl_seconds,
        )
        self._write_json(self.state_dir / "plans" / f"{plan.digest}.json", plan.to_dict())
        self._emit("planned", plan.digest)
        return plan

    def apply(self, plan_digest: str, *, confirmed: bool) -> UpdateReceipt:
        if not confirmed:
            raise ValueError("explicit confirmation is required")
        if not re.fullmatch(r"[0-9a-f]{64}", plan_digest):
            raise ValueError("update plan digest must be 64 lowercase hexadecimal characters")
        plan_path = self.state_dir / "plans" / f"{plan_digest}.json"
        if not plan_path.is_file():
            raise ValueError("update plan is unknown or expired; create a new plan")
        plan = UpdatePlan.from_dict(self._read_json(plan_path))
        if plan.digest != plan_digest or plan.expires_at < self.clock():
            plan_path.unlink(missing_ok=True)
            raise ValueError("update plan is unknown or expired; create a new plan")
        plan_path.unlink(missing_ok=True)
        try:
            self._require_success(self._install_command(plan.target_version), "package installation")
            if self._installed_global_version() != plan.target_version:
                raise RuntimeError("update verification failed")
            self._reapply_owned(plan)
        except Exception as error:
            self._rollback(plan)
            receipt = self._receipt(plan, "rolled_back", {"reason": type(error).__name__})
            self._save_receipt(receipt)
            self._emit("rolled_back", plan.digest, receipt.receipt_id)
            raise RuntimeError("update verification failed; previous version restored") from error
        receipt = self._receipt(plan, "verified", {
            "mcp_profiles_reapplied": len(plan.mcp_profiles),
            "skill_targets_reapplied": len(plan.skill_installs),
            "restart_required": True,
            "manual_skill_targets": list(plan.manual_skill_targets),
        })
        self._save_receipt(receipt)
        self._emit("verified", plan.digest, receipt.receipt_id)
        return receipt

    def _reapply_owned(self, plan: UpdatePlan) -> None:
        for profile in plan.mcp_profiles:
            self._require_success(
                ("ctxora", "install", "--workspace", str(self.workspace), "--profile", profile),
                f"MCP profile {profile}",
            )
        for target, profile in plan.skill_installs:
            self._require_success(
                (
                    "ctxora", "skills", "install", "--workspace", str(self.workspace),
                    "--profile", profile, "--target", target, "--prune",
                ),
                f"skill target {target}",
            )

    def _rollback(self, plan: UpdatePlan) -> None:
        self.runner(self._install_command(plan.current_version))
        for profile in plan.mcp_profiles:
            self.runner(("ctxora", "install", "--workspace", str(self.workspace), "--profile", profile))
        for target, profile in plan.skill_installs:
            self.runner((
                "ctxora", "skills", "install", "--workspace", str(self.workspace),
                "--profile", profile, "--target", target, "--prune",
            ))

    def _owned_mcp_profiles(self) -> tuple[str, ...]:
        path = workspace_installer_dir(self.workspace) / "ownership.json"
        if not path.is_file():
            return ()
        payload = self._read_json(path)
        return tuple(sorted(key for key, value in payload.items() if isinstance(value, dict)))

    def _owned_skill_state(self) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
        installs = set()
        manual = set()
        catalog = SkillCatalog()
        directory = workspace_installer_dir(self.workspace)
        for path in directory.glob("ecc-skills-*.json") if directory.is_dir() else ():
            payload = self._read_json(path)
            target, profile = payload.get("target"), payload.get("profile")
            if target in {"codex", "claude", "cursor", "gemini", "opencode"} and isinstance(profile, str):
                selection = catalog.select(profile)
                if (
                    payload.get("modules") == list(selection.modules)
                    and payload.get("skills") == list(selection.skills)
                ):
                    installs.add((target, profile))
                else:
                    manual.add(target)
        return tuple(sorted(installs)), tuple(sorted(manual))

    def _emit(self, status: str, plan_digest: str, receipt_id: str = "") -> None:
        if self.events is not None:
            self.events.emit(
                "operator_action",
                action="update",
                status=status,
                plan_digest=plan_digest,
                receipt_id=receipt_id,
            )

    def _installed_global_version(self) -> str:
        result = self.runner(("npm", "list", "--global", "ctxora", "--depth=0", "--json"))
        self._require_result(result, "package verification")
        try:
            version = json.loads(result.stdout)["dependencies"]["ctxora"]["version"]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("update verification returned an invalid version") from error
        return self._validate_version(str(version))

    def _require_success(self, command: tuple[str, ...], label: str) -> None:
        self._require_result(self.runner(command), label)

    @staticmethod
    def _require_result(result: subprocess.CompletedProcess[str], label: str) -> None:
        if result.returncode != 0:
            raise RuntimeError(f"{label} failed")

    @staticmethod
    def _install_command(version: str) -> tuple[str, ...]:
        return ("npm", "install", "--global", f"ctxora@{version}", "--ignore-scripts")

    def _receipt(self, plan: UpdatePlan, status: str, details: dict) -> UpdateReceipt:
        return UpdateReceipt(
            current_version=plan.current_version,
            target_version=plan.target_version,
            status=status,
            plan_digest=plan.digest,
            details=details,
        )

    def _save_receipt(self, receipt: UpdateReceipt) -> None:
        self._write_json(
            self.state_dir / "receipts" / f"{receipt.receipt_id}.json",
            receipt.to_dict(),
        )

    @staticmethod
    def _run(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)

    @staticmethod
    def _validate_version(version: str) -> str:
        if not _SEMVER.fullmatch(version):
            raise ValueError(f"invalid release version: {version}")
        return version

    @staticmethod
    def _version_tuple(version: str) -> tuple[int, int, int]:
        return tuple(int(part) for part in version.split("."))

    @staticmethod
    def _read_json(path: Path) -> dict:
        payload = json.loads(path.read_text("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError(f"invalid update state: {path.name}")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            temporary = Path(handle.name)
        os.replace(temporary, path)
