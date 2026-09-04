from __future__ import annotations

from pathlib import Path

from harness_context.branding import LEGACY_WORKSPACE_DIR_NAME, WORKSPACE_DIR_NAME


def workspace_data_dir(workspace: str | Path) -> Path:
    return Path(workspace).resolve() / WORKSPACE_DIR_NAME


def legacy_workspace_data_dir(workspace: str | Path) -> Path:
    return Path(workspace).resolve() / LEGACY_WORKSPACE_DIR_NAME


def workspace_state_dir(workspace: str | Path) -> Path:
    preferred = workspace_data_dir(workspace) / "state"
    legacy = legacy_workspace_data_dir(workspace) / "state"
    return preferred if preferred.exists() or not legacy.exists() else legacy


def workspace_runtime_dir(workspace: str | Path) -> Path:
    preferred = workspace_data_dir(workspace)
    legacy = legacy_workspace_data_dir(workspace)
    return preferred if (preferred / "run.pid").exists() or not (legacy / "run.pid").exists() else legacy


def workspace_installer_dir(workspace: str | Path) -> Path:
    preferred = workspace_data_dir(workspace) / "installer"
    legacy = legacy_workspace_data_dir(workspace) / "installer"
    return preferred if preferred.exists() or not legacy.exists() else legacy


def workspace_data_dirs(workspace: str | Path) -> tuple[Path, Path]:
    return workspace_data_dir(workspace), legacy_workspace_data_dir(workspace)
