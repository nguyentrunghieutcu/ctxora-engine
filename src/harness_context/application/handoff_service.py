class HandoffService:
    def __init__(self, store): self.store = store
    def prepare(self, workspace_id, messages_json, threshold_tokens=30_000, label="", retention_seconds=604_800, consent=False): return self.store.prepare(messages_json, threshold_tokens, label, workspace_id, retention_seconds, consent)
    def restore(self, workspace_id, handoff_id):
        result = self.store.restore(handoff_id, workspace_id)
        if result is None:
            raise ValueError("handoff not found")
        return result
    def list(self, workspace_id, limit=30): return self.store.list(workspace_id, limit)
    def delete(self, workspace_id, handoff_id): return {"deleted": self.store.delete(handoff_id, workspace_id)}
    def purge(self): return {"purged": self.store.purge_expired()}
