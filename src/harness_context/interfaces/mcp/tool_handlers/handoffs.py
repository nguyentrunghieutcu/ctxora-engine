def register_handoff_tools(mcp, container) -> None:
    @mcp.tool()
    def handoff_conversation(workspace_id: str, messages_json: str, threshold_tokens: int = 30_000, label: str = "", retention_seconds: int = 604_800, consent: bool = False) -> dict:
        return container.handoff.prepare(workspace_id, messages_json, threshold_tokens, label, retention_seconds, consent)

    @mcp.tool()
    def restore_conversation_handoff(workspace_id: str, handoff_id: str) -> dict:
        return container.handoff.restore(workspace_id, handoff_id)

    @mcp.tool()
    def list_conversation_handoffs(workspace_id: str, limit: int = 30) -> list[dict]:
        return container.handoff.list(workspace_id, limit)

    @mcp.tool()
    def delete_conversation_handoff(workspace_id: str, handoff_id: str) -> dict:
        return container.handoff.delete(workspace_id, handoff_id)

    @mcp.tool()
    def purge_expired_handoffs() -> dict:
        return container.handoff.purge()
