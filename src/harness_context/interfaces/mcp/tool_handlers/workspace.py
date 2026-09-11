def register_workspace_tools(mcp, container, default_workspace_id: str) -> None:
    @mcp.tool()
    def register_workspace(workspace_id: str, roots: list[str], initial_refresh: bool = False) -> dict:
        return container.workspace.register(workspace_id, roots, initial_refresh)

    @mcp.tool()
    def refresh_workspace(workspace_id: str = default_workspace_id, paths: list[str] | None = None) -> dict:
        return container.refresh.execute(workspace_id, paths)

    @mcp.tool()
    def invalidate_context(workspace_id: str, target: str) -> dict:
        return container.refresh.invalidate(workspace_id, target)
