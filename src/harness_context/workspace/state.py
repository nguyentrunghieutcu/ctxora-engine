from enum import Enum


class WorkspaceStatus(str, Enum):
    REGISTERED = "registered"
    INDEXING = "indexing"
    READY = "ready"


_TRANSITIONS = {
    WorkspaceStatus.REGISTERED: {WorkspaceStatus.INDEXING},
    WorkspaceStatus.INDEXING: {WorkspaceStatus.READY},
    WorkspaceStatus.READY: {WorkspaceStatus.INDEXING, WorkspaceStatus.REGISTERED},
}


def transition_workspace_status(current: str | WorkspaceStatus, target: str | WorkspaceStatus) -> WorkspaceStatus:
    current_status = WorkspaceStatus(current)
    target_status = WorkspaceStatus(target)
    if target_status not in _TRANSITIONS[current_status]:
        raise ValueError(f"invalid workspace transition: {current_status.value} -> {target_status.value}")
    return target_status


def validate_ready_snapshot(snapshot: dict) -> None:
    required = {"workspace_id", "snapshot_id", "snapshot_version", "status", "fingerprints", "items"}
    missing = required - snapshot.keys()
    if missing:
        raise ValueError(f"snapshot is missing required fields: {sorted(missing)}")
    if snapshot["status"] != WorkspaceStatus.READY:
        raise ValueError("only ready snapshots may be promoted")
    if not snapshot["snapshot_id"] or int(snapshot["snapshot_version"]) < 1:
        raise ValueError("snapshot identity is invalid")
    if any(item.get("workspace_id") != snapshot["workspace_id"] for item in snapshot["items"]):
        raise ValueError("snapshot contains items from another workspace")
