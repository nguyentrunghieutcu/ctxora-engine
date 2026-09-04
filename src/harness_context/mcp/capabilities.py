from harness_context.branding import MCP_SERVER_NAME

SERVER_NAME = MCP_SERVER_NAME

TOOL_NAMES = frozenset({
    "register_workspace", "refresh_workspace", "plan_context", "retrieve_context",
    "prepare_context", "context_stats", "invalidate_context", "memory_save",
    "memory_search", "memory_delete", "memory_list", "handoff_conversation",
    "restore_conversation_handoff", "list_conversation_handoffs",
    "delete_conversation_handoff", "purge_expired_handoffs", "ecc_status", "ecc_search",
})
