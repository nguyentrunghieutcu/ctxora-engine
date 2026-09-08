from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKILL_INSTALL_TARGETS = {
    "codex": ".agents/skills",
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "gemini": ".gemini/skills",
    "opencode": ".opencode/skills",
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
            raise ValueError(f"unknown skills profile: {profile}")
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
    ) -> dict[str, Any]:
        root = Path(workspace).expanduser().resolve(strict=True)
        destination = Path(output).expanduser()
        if not destination.is_absolute():
            destination = root / destination
        self._reject_symlinks(destination)
        destination = destination.resolve()
        output_key = hashlib.sha256(str(destination).encode("utf-8")).hexdigest()[:12]
        manifest_path = root / ".ctxora" / "installer" / f"ecc-skills-{output_key}.json"
        self._reject_symlinks(manifest_path)
        previous = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
        previous_hashes = previous.get("hashes", {}) if previous.get("output") == str(destination) else {}
        for skill in (*selection.skills, *previous_hashes):
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", skill):
                raise ValueError(f"unsafe skill id: {skill}")
        source_hashes = {skill: self._directory_hash(self.source_root / skill) for skill in selection.skills}
        conflicts: list[str] = []
        operations: list[dict[str, str]] = []
        for skill, source_hash in source_hashes.items():
            target = destination / skill
            self._reject_symlinks(target)
            if not target.exists():
                operations.append({"operation": "add", "skill": skill})
                continue
            target_hash = self._directory_hash(target)
            if target_hash == source_hash:
                operations.append({"operation": "keep", "skill": skill})
            elif force or previous_hashes.get(skill) == target_hash:
                operations.append({"operation": "replace", "skill": skill})
            else:
                conflicts.append(skill)
        if prune:
            for skill, installed_hash in previous_hashes.items():
                if skill in source_hashes:
                    continue
                target = destination / skill
                self._reject_symlinks(target)
                if not target.exists():
                    continue
                if self._directory_hash(target) == installed_hash:
                    operations.append({"operation": "remove", "skill": skill})
                else:
                    conflicts.append(skill)
        result = {
            "profile": selection.profile,
            "output": str(destination),
            "skill_count": len(selection.skills),
            "operations": operations,
            "conflicts": sorted(set(conflicts)),
        }
        if dry_run or conflicts:
            return result
        destination.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        hashes = dict(previous_hashes) if not prune else {}
        hashes.update(source_hashes)
        manifest = json.dumps({
            "catalog_commit": self.commit,
            "output": str(destination),
            "profile": selection.profile,
            "modules": list(selection.modules),
            "skills": list(selection.skills),
            "hashes": hashes,
        }, ensure_ascii=False, indent=2) + "\n"
        lock_path = manifest_path.with_suffix(".lock")
        try:
            lock = lock_path.open("x")
        except FileExistsError as error:
            raise ValueError("skill installation is locked; check for an active or interrupted installer") from error
        with lock:
            try:
                current = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
                if current != previous:
                    raise ValueError("skill installation changed; preview again")
                with tempfile.TemporaryDirectory(prefix=".ctxora-ecc-", dir=destination) as staging:
                    staging_root = Path(staging)
                    changed = []
                    try:
                        for operation in operations:
                            skill = operation["skill"]
                            target = destination / skill
                            if operation["operation"] == "keep":
                                continue
                            staged = staging_root / (skill + ".new")
                            if operation["operation"] != "remove":
                                shutil.copytree(self.source_root / skill, staged)
                            backup = staging_root / (skill + ".old")
                            if target.exists():
                                target.rename(backup)
                            changed.append((target, backup))
                            if staged.exists():
                                staged.rename(target)
                        pending = manifest_path.with_suffix(".pending")
                        self._reject_symlinks(pending)
                        pending.write_text(manifest, "utf-8")
                        pending.replace(manifest_path)
                    except Exception:
                        for target, backup in reversed(changed):
                            if target.exists():
                                shutil.rmtree(target)
                            if backup.exists():
                                backup.rename(target)
                        raise
            finally:
                lock_path.unlink()
        return result

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
