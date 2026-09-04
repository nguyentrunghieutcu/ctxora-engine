from harness_context.engine import ContextEngine
from harness_context.storage import SnapshotStore


class RefreshService:
    def __init__(self, engine: ContextEngine, snapshots: SnapshotStore):
        self.engine, self.snapshots = engine, snapshots

    def execute(self, workspace_id: str, paths: list[str] | None = None) -> dict:
        candidate_id = self.snapshots.begin_candidate(workspace_id)
        try:
            candidate, result = self.engine.build_workspace_snapshot(workspace_id, paths)
            self.engine.prepare_bundle(workspace_id, _state=candidate, _record=True)
            self.snapshots.validate_candidate(candidate_id, self.engine.export_state(workspace_id, candidate))
            self.snapshots.promote_candidate(candidate_id)
            self.engine.activate_snapshot(workspace_id, candidate)
            return result
        except Exception as error:
            self.snapshots.fail_candidate(candidate_id, error)
            raise

    def invalidate(self, workspace_id: str, target: str) -> dict:
        result = self.engine.invalidate(workspace_id, target)
        self.snapshots.promote(self.engine.export_snapshot(workspace_id))
        return result
