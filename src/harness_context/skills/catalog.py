from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_context.domain.artifacts import InstallOperation, InstallPlan
from harness_context.domain.harnesses import REGISTRY, Capability
from harness_context.paths import workspace_installer_dir

SKILL_TARGET_NAMES = ("codex", "claude", "cursor", "gemini", "opencode")
SKILL_INSTALL_TARGETS = {
    name: REGISTRY.get(name).artifact_root(Capability.SKILLS.value)
    for name in SKILL_TARGET_NAMES
}


@dataclass(frozen=True)
class SkillSelection:
    profile: str
    modules: tuple[str, ...]
    skills: tuple[str, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "modules": list(self.modules),
            "skill_count": len(self.skills),
            "skills": list(self.skills),
            "added": list(self.added),
            "removed": list(self.removed),
        }


class SkillCatalog:
    def __init__(self, manifest_path: str | Path | None = None):
        path = Path(manifest_path) if manifest_path else Path(__file__).with_name("ecc_catalog.json")
        data = json.loads(path.read_text("utf-8"))
        self.version = data["version"]
        self.source = data["source"]
        self.commit = data["commit"]
        self.skills: dict[str, dict[str, Any]] = data["skills"]
        self.modules: dict[str, dict[str, Any]] = data["modules"]
        self.profiles: dict[str, dict[str, Any]] = data["profiles"]

    def select(
        self,
        profile: str = "developer",
        add_modules: tuple[str, ...] = (),
        remove_modules: tuple[str, ...] = (),
        add_skills: tuple[str, ...] = (),
        remove_skills: tuple[str, ...] = (),
    ) -> SkillSelection:
        if profile not in self.profiles:
            available = ", ".join(sorted(self.profiles))
            raise ValueError(f"unknown skills profile: {profile}. Available profiles: {available}")
        modules = list(self.profiles[profile]["modules"])
        for module in add_modules:
            self._require_module(module)
            if module not in modules:
                modules.append(module)
        for module in remove_modules:
            self._require_module(module)
            modules = [item for item in modules if item != module]
        selected: set[str] = set()
        for module in modules:
            selected.update(self.modules[module]["skills"])
        for skill in add_skills:
            self._require_skill(skill)
            selected.add(skill)
        for skill in remove_skills:
            self._require_skill(skill)
            selected.discard(skill)
        base = set(self._profile_skills(profile))
        return SkillSelection(
            profile,
            tuple(modules),
            tuple(sorted(selected)),
            tuple(sorted(selected - base)),
            tuple(sorted(base - selected)),
        )

    def write_selection(self, workspace: str | Path, selection: SkillSelection) -> Path:
        root = Path(workspace).expanduser().resolve(strict=True)
        target = root / ".ctxora" / "skills-profile.json"
        self._reject_symlinks(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "catalog_version": self.version,
            "catalog_commit": self.commit,
            "profile": selection.profile,
            "modules": list(selection.modules),
            "skills": list(selection.skills),
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
        return target

    @property
    def source_root(self) -> Path:
        return Path(__file__).with_name("ecc")

    @staticmethod
    def install_outputs(targets: tuple[str, ...], output: str = "") -> tuple[tuple[str, str], ...]:
        if output and targets:
            raise ValueError("use either --output or --target, not both")
        if output:
            return (("custom", output),)
        selected = list(targets or ("codex",))
        if "all" in selected:
            selected = list(SKILL_INSTALL_TARGETS)
        unknown = sorted(set(selected) - set(SKILL_INSTALL_TARGETS))
        if unknown:
            raise ValueError(f"unknown skill install target: {unknown[0]}")
        return tuple((name, SKILL_INSTALL_TARGETS[name]) for name in dict.fromkeys(selected))

    def install(
        self,
        workspace: str | Path,
        output: str | Path,
        selection: SkillSelection,
        *,
        force: bool = False,
        prune: bool = False,
        dry_run: bool = False,
        target: str = "custom",
    ) -> dict[str, Any]:
        plan = self.plan_install(
            workspace, output, selection, force=force, prune=prune, target=target
        )
        result = self._legacy_plan_result(plan, len(selection.skills))
        if dry_run or plan.conflicts:
            return result
        self.apply_install(workspace, plan, selection)
        return result

    def plan_install(
        self,
        workspace: str | Path,
        output: str | Path,
        selection: SkillSelection,
        *,
        force: bool = False,
        prune: bool = False,
        target: str = "custom",
        delivery: str = "materialized",
    ) -> InstallPlan:
        if delivery not in {"shared", "materialized"}:
            raise ValueError("unknown skill delivery mode")
        if delivery == "shared" and force:
            raise ValueError("shared migration never overwrites customized skills; omit --force")
        root = Path(workspace).expanduser().resolve(strict=True)
        destination = Path(output).expanduser()
        if not destination.is_absolute():
            destination = root / destination
        self._reject_symlinks(destination)
        destination = destination.resolve()
        output_key = hashlib.sha256(str(destination).encode("utf-8")).hexdigest()[:12]
        manifest_path = workspace_installer_dir(root) / f"ecc-skills-{output_key}.json"
        self._reject_symlinks(manifest_path)
        previous = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
        previous_hashes = previous.get("hashes", {}) if previous.get("output") == str(destination) else {}
        for skill in (*selection.skills, *previous_hashes):
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", skill):
                raise ValueError(f"unsafe skill id: {skill}")
        source_hashes = {
            skill: self._directory_hash(self.source_root / skill)
            for skill in selection.skills
        } if delivery == "materialized" else {}
        conflicts: list[str] = []
        operations: list[InstallOperation] = []
        if delivery == "shared" and previous_hashes and not prune:
            conflicts.append("legacy materialized skills remain; preview with --prune to migrate")
        for skill, source_hash in source_hashes.items():
            target_path = destination / skill
            self._reject_symlinks(target_path)
            if not target_path.exists():
                operations.append(InstallOperation(
                    "add", skill, str(self.source_root / skill), str(target_path), after_hash=source_hash
                ))
                continue
            target_hash = self._directory_hash(target_path)
            if target_hash == source_hash:
                operations.append(InstallOperation(
                    "keep", skill, str(self.source_root / skill), str(target_path),
                    before_hash=target_hash, after_hash=source_hash,
                ))
            elif force or previous_hashes.get(skill) == target_hash:
                operations.append(InstallOperation(
                    "replace", skill, str(self.source_root / skill), str(target_path),
                    before_hash=target_hash, after_hash=source_hash,
                ))
            else:
                conflicts.append(skill)
        if prune:
            for skill, installed_hash in previous_hashes.items():
                if skill in source_hashes:
                    continue
                target_path = destination / skill
                self._reject_symlinks(target_path)
                if not target_path.exists():
                    continue
                target_hash = self._directory_hash(target_path)
                if target_hash == installed_hash:
                    operations.append(InstallOperation(
                        "remove", skill, "", str(target_path), before_hash=target_hash
                    ))
                else:
                    conflicts.append(skill)
        metadata = (
            ("catalog_commit", self.commit),
            ("manifest_path", str(manifest_path)),
            ("modules", json.dumps(selection.modules, separators=(",", ":"))),
            ("previous_manifest_hash", self._json_hash(previous)),
            ("prune", "true" if prune else "false"),
            ("delivery", delivery),
        )
        return InstallPlan(
            target=target,
            profile=selection.profile,
            destination=str(destination),
            operations=tuple(operations),
            conflicts=tuple(sorted(set(conflicts))),
            metadata=metadata,
        )

    def apply_install(
        self,
        workspace: str | Path,
        plan: InstallPlan,
        selection: SkillSelection,
    ) -> None:
        self.apply_install_plans(workspace, (plan,), selection)

    def apply_install_plans(
        self,
        workspace: str | Path,
        plans: tuple[InstallPlan, ...],
        selection: SkillSelection,
    ) -> None:
        root = Path(workspace).expanduser().resolve(strict=True)
        if len({plan.destination for plan in plans}) != len(plans):
            raise ValueError("install plans must target distinct destinations")
        prepared = [self._prepare_apply(root, plan, selection) for plan in plans]
        profile_path = root / ".ctxora" / "skills-profile.json"
        self._reject_symlinks(profile_path)
        lock_paths = sorted({item[1].with_suffix(".lock") for item in prepared} | {
            workspace_installer_dir(root) / "skills-profile.lock",
        })
        locks = []
        try:
            for lock_path in lock_paths:
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    locks.append(lock_path.open("x"))
                except FileExistsError as error:
                    raise ValueError(
                        "skill installation is locked; check for an active or interrupted installer"
                    ) from error
            prepared = [self._prepare_apply(root, plan, selection) for plan in plans]
            self._apply_prepared(prepared, root, selection)
        finally:
            for lock in reversed(locks):
                lock.close()
                Path(lock.name).unlink(missing_ok=True)

    def _prepare_apply(
        self,
        root: Path,
        plan: InstallPlan,
        selection: SkillSelection,
    ) -> tuple[InstallPlan, Path, dict[str, Any], str]:
        destination = Path(plan.destination)
        self._reject_symlinks(destination)
        metadata = dict(plan.metadata)
        manifest_path = Path(metadata["manifest_path"])
        self._reject_symlinks(manifest_path)
        if plan.conflicts:
            raise ValueError("cannot apply a skill plan with conflicts")
        if plan.profile != selection.profile or metadata.get("catalog_commit") != self.commit:
            raise ValueError("install plan does not match the selected catalog profile")
        if manifest_path.parent != workspace_installer_dir(root):
            raise ValueError("install plan manifest is outside the workspace installer directory")
        previous = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
        if self._json_hash(previous) != metadata.get("previous_manifest_hash"):
            raise ValueError("skill installation changed; preview again")
        for operation in plan.operations:
            target_path = Path(operation.destination_path)
            self._reject_symlinks(target_path)
            current_hash = self._directory_hash(target_path) if target_path.exists() else None
            if current_hash != operation.before_hash:
                raise ValueError(f"skill installation changed for {operation.artifact_id}; preview again")
            if operation.operation != "remove":
                source_hash = self._directory_hash(Path(operation.source_path))
                if source_hash != operation.after_hash:
                    raise ValueError(f"source skill changed for {operation.artifact_id}; preview again")
        hashes = dict(previous.get("hashes", {}))
        if metadata.get("prune") == "true":
            hashes = {}
        for operation in plan.operations:
            if operation.operation == "remove":
                hashes.pop(operation.artifact_id, None)
            elif operation.after_hash:
                hashes[operation.artifact_id] = operation.after_hash
        manifest = json.dumps({
            "schema_version": "ctxora.install.receipt.v1",
            "plan_digest": plan.digest,
            "target": plan.target,
            "delivery": metadata.get("delivery", "materialized"),
            "verified": True,
            "catalog_commit": self.commit,
            "output": str(destination),
            "profile": selection.profile,
            "modules": list(selection.modules),
            "skills": list(selection.skills),
            "hashes": hashes,
        }, ensure_ascii=False, indent=2) + "\n"
        return plan, manifest_path, previous, manifest

    def _apply_prepared(
        self,
        prepared: list[tuple[InstallPlan, Path, dict[str, Any], str]],
        root: Path,
        selection: SkillSelection,
    ) -> None:
        changed: list[tuple[Path, Path]] = []
        manifest_backups: list[tuple[Path, bytes | None]] = []
        created_destinations: list[Path] = []
        with ExitStack() as stack:
            staged_plans = []
            for plan, manifest_path, previous, manifest in prepared:
                destination = Path(plan.destination)
                shared = dict(plan.metadata).get("delivery") == "shared"
                if not shared and not destination.exists():
                    destination.mkdir(parents=True)
                    created_destinations.append(destination)
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                staging_root = Path(stack.enter_context(
                    tempfile.TemporaryDirectory(
                        prefix=".ctxora-ecc-", dir=manifest_path.parent if shared else destination
                    )
                ))
                staged = {}
                for operation in plan.operations:
                    if operation.operation in {"keep", "remove"}:
                        continue
                    staged_path = staging_root / (operation.artifact_id + ".new")
                    shutil.copytree(operation.source_path, staged_path)
                    staged[operation.artifact_id] = staged_path
                staged_plans.append((plan, manifest_path, previous, manifest, staging_root, staged))
            profile_path = root / ".ctxora" / "skills-profile.json"
            manifest_backups.append(
                (profile_path, profile_path.read_bytes() if profile_path.exists() else None)
            )
            try:
                for plan, manifest_path, previous, manifest, staging_root, staged in staged_plans:
                    current = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
                    if current != previous:
                        raise ValueError("skill installation changed; preview again")
                    for operation in plan.operations:
                        if operation.operation == "keep":
                            continue
                        target_path = Path(operation.destination_path)
                        backup = staging_root / (operation.artifact_id + ".old")
                        if target_path.exists():
                            target_path.rename(backup)
                        changed.append((target_path, backup))
                        staged_path = staged.get(operation.artifact_id)
                        if staged_path is not None:
                            staged_path.rename(target_path)
                    previous_bytes = manifest_path.read_bytes() if manifest_path.exists() else None
                    manifest_backups.append((manifest_path, previous_bytes))
                    self._write_manifest(manifest_path, manifest)
                self.write_selection(root, selection)
            except Exception:
                for target_path, backup in reversed(changed):
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    if backup.exists():
                        backup.rename(target_path)
                for manifest_path, previous_bytes in reversed(manifest_backups):
                    if previous_bytes is None:
                        manifest_path.unlink(missing_ok=True)
                    else:
                        manifest_path.write_bytes(previous_bytes)
                for destination in reversed(created_destinations):
                    try:
                        destination.rmdir()
                    except OSError:
                        pass
                raise

    def _write_manifest(self, manifest_path: Path, content: str) -> None:
        pending = manifest_path.with_suffix(".pending")
        self._reject_symlinks(pending)
        pending.write_text(content, "utf-8")
        pending.replace(manifest_path)

    @staticmethod
    def _legacy_plan_result(plan: InstallPlan, skill_count: int) -> dict[str, Any]:
        return {
            "profile": plan.profile,
            "output": plan.destination,
            "skill_count": skill_count,
            "operations": [
                {"operation": operation.operation, "skill": operation.artifact_id}
                for operation in plan.operations
            ],
            "conflicts": list(plan.conflicts),
            "plan_digest": plan.digest,
        }

    @staticmethod
    def _json_hash(value: Any) -> str:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _reject_symlinks(path: Path) -> None:
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError(f"refusing symlink in skill installation path: {path}")

    @staticmethod
    def _directory_hash(path: Path) -> str:
        if not path.is_dir():
            raise ValueError(f"skill directory is missing: {path.name}")
        digest = hashlib.sha256()
        if path.is_symlink() or any(item.is_symlink() for item in path.rglob("*")):
            raise ValueError(f"refusing symlink inside skill: {path.name}")
        for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(file_path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()

    def _profile_skills(self, profile: str) -> set[str]:
        if profile not in self.profiles:
            available = ", ".join(sorted(self.profiles))
            raise ValueError(f"unknown skills profile: {profile}. Available profiles: {available}")
        selected: set[str] = set()
        for module in self.profiles[profile]["modules"]:
            selected.update(self.modules[module]["skills"])
        return selected

    def _require_module(self, module: str) -> None:
        if module not in self.modules:
            raise ValueError(f"unknown skills module: {module}")

    def _require_skill(self, skill: str) -> None:
        if skill not in self.skills:
            raise ValueError(f"unknown ECC skill: {skill}")
