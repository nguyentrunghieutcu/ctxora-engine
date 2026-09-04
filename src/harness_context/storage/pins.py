from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SnapshotPin:
    workspace_id: str
    snapshot_id: str
    snapshot_version: int
    state: Any
