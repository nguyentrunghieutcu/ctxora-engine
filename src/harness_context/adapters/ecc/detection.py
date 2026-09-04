from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EccInstallation:
    project_memory_root: Path | None
    user_memory_root: Path | None
    allow_user_scope: bool

    @property
    def available(self) -> bool:
        return self.project_memory_root is not None or self.user_memory_root is not None


def _existing_directory(path: str | Path) -> Path | None:
    candidate = Path(path).expanduser()
    if candidate.is_symlink() or not candidate.is_dir():
        return None
    return candidate.resolve()


def detect_ecc(
    workspace_root: str | Path,
    *,
    allow_user_scope: bool = False,
    environment: dict[str, str] | None = None,
) -> EccInstallation:
    """Detect existing ECC memory vaults without installing or cloning ECC."""
    env = environment if environment is not None else os.environ
    workspace = Path(workspace_root).expanduser().resolve(strict=True)
    project_override = env.get("ECC_MEMORY_PROJECT_ROOT")
    user_override = env.get("ECC_MEMORY_USER_ROOT")
    project_root = _existing_directory(project_override or workspace / ".ecc" / "memory")
    user_root = None
    if allow_user_scope:
        user_root = _existing_directory(user_override or Path.home() / ".ecc" / "memory")
    return EccInstallation(project_root, user_root, allow_user_scope)
