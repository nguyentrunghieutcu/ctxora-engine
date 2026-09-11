def register_context_tools(mcp, container, default_workspace_id: str) -> None:
    @mcp.tool()
    def plan_context(workspace_id: str, query: str, available_input_tokens: int, strategy_override: str = "") -> dict:
        return container.retrieval.plan(workspace_id, query, available_input_tokens, strategy_override)

    @mcp.tool()
    def retrieve_context(workspace_id: str, query: str, top_k: int = 12, graph_expand: bool = True, token_budget: int = 4_000) -> dict:
        return container.retrieval.retrieve(workspace_id, query, top_k, graph_expand, token_budget)

    @mcp.tool()
    def prepare_context(workspace_id: str, query: str, available_input_tokens: int, preferred_strategy: str = "auto", include_memory: bool = True, include_handoff: bool = False, handoff_id: str = "", include_ecc: bool = False, freshness: str = "current", deadline_ms: int = 5_000) -> dict:
        return container.context.prepare_values(workspace_id=workspace_id, query=query, available_input_tokens=available_input_tokens, preferred_strategy=preferred_strategy, include_memory=include_memory, include_handoff=include_handoff, handoff_id=handoff_id, include_ecc=include_ecc, freshness=freshness, deadline_ms=deadline_ms)

    @mcp.tool()
    def context_stats(workspace_id: str = default_workspace_id) -> dict:
        return container.retrieval.stats(workspace_id)
