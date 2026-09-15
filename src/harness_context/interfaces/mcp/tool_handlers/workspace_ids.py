from pathlib import Path

from harness_context.workspace.identity import workspace_identity


def resolve_workspace_id(value: str, default_workspace_id: str) -> str:
    if value == default_workspace_id:
        return value
    candidate = Path(value).expanduser()
    if candidate.is_dir() and workspace_identity(candidate) == default_workspace_id:
        return default_workspace_id
    return value
