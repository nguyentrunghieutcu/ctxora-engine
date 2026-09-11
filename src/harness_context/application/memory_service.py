from harness_context.infrastructure.memory.episodic import MemoryType


class MemoryService:
    def __init__(self, store): self.store = store
    def save(self, workspace_id, key, value, mtype="semantic", tags="", scope="workspace", source="user", confidence=1.0, expires_at=None): return self.store.save(MemoryType(mtype), key, value, tags, workspace_id=workspace_id, scope=scope, source=source, confidence=confidence, expires_at=expires_at)
    def search(self, workspace_id, query, mtype="", top_k=5, min_sim=0.12): return self.store.search(query, MemoryType(mtype) if mtype else None, top_k, min_sim, workspace_id)
    def delete(self, workspace_id, key, mtype="semantic"): return {"deleted": self.store.delete(MemoryType(mtype), key, workspace_id)}
    def list(self, workspace_id, mtype="", limit=30): return self.store.list_keys(MemoryType(mtype) if mtype else None, limit, workspace_id)
