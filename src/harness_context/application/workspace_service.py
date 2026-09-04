from pathlib import Path


class WorkspaceService:
    def __init__(self, engine, refresh, default_workspace_id):
        self.engine, self.refresh, self.default_workspace_id = engine, refresh, default_workspace_id

    def register(self, workspace_id, roots, initial_refresh=False):
        if workspace_id != self.default_workspace_id:
            raise ValueError("one runtime serves exactly one workspace")
        policy = self.engine.registry.get(self.default_workspace_id)
        requested = tuple(sorted(str(Path(root).resolve()) for root in roots))
        if requested != policy.roots:
            raise ValueError("workspace roots cannot change after runtime startup")
        result = {"workspace_id": workspace_id, "roots": list(policy.roots), "status": self.engine.stats(workspace_id)["status"]}
        if initial_refresh:
            result["refresh"] = self.refresh.execute(workspace_id)
        return result
