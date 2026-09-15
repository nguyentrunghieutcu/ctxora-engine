from harness_context.interfaces.mcp.tool_handlers.workspace_ids import resolve_workspace_id


def register_memory_tools(mcp, container, default_workspace_id: str) -> None:
    @mcp.tool()
    def memory_save(workspace_id: str, key: str, value: str, mtype: str = "semantic", tags: str = "", scope: str = "workspace", source: str = "user", confidence: float = 1.0, expires_at: float | None = None) -> dict:
        return container.memories.save(resolve_workspace_id(workspace_id, default_workspace_id), key, value, mtype, tags, scope, source, confidence, expires_at)

    @mcp.tool()
    def memory_search(workspace_id: str, query: str, mtype: str = "", top_k: int = 5, min_sim: float = 0.12) -> list[dict]:
        return container.memories.search(resolve_workspace_id(workspace_id, default_workspace_id), query, mtype, top_k, min_sim)

    @mcp.tool()
    def memory_delete(workspace_id: str, key: str, mtype: str = "semantic") -> dict:
        return container.memories.delete(resolve_workspace_id(workspace_id, default_workspace_id), key, mtype)

    @mcp.tool()
    def memory_list(workspace_id: str, mtype: str = "", limit: int = 30) -> list[str]:
        return container.memories.list(resolve_workspace_id(workspace_id, default_workspace_id), mtype, limit)
