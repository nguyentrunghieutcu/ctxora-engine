from harness_context.interfaces.mcp.tool_handlers import (
    register_context_tools,
    register_ecc_tools,
    register_handoff_tools,
    register_memory_tools,
    register_skill_tools,
    register_workspace_tools,
)


def register_tools(mcp, container, default_workspace_id: str) -> None:
    register_workspace_tools(mcp, container, default_workspace_id)
    register_context_tools(mcp, container, default_workspace_id)
    register_memory_tools(mcp, container)
    register_handoff_tools(mcp, container)
    register_ecc_tools(mcp, container)
    register_skill_tools(mcp, container)
