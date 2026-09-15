

from harness_context.interfaces.mcp.tool_handlers.workspace_ids import resolve_workspace_id


def register_skill_tools(mcp, container, default_workspace_id: str) -> None:
    @mcp.tool()
    def route_skills(
        workspace_id: str,
        task: str,
        profile: str = "",
        top_k: int = 5,
        include_instructions: bool = True,
        token_budget: int = 6_000,
    ) -> dict:
        return container.skill_router.route(
            resolve_workspace_id(workspace_id, default_workspace_id), task, profile, top_k, include_instructions, token_budget
        )

    @mcp.tool()
    def skill_feedback(
        workspace_id: str,
        route_id: str,
        outcome: str,
        skills: list[str] | None = None,
        correction_skill: str = "",
    ) -> dict:
        return container.skill_router.feedback(
            resolve_workspace_id(workspace_id, default_workspace_id), route_id, outcome, skills, correction_skill
        )

    @mcp.tool()
    def skill_learning_status(workspace_id: str, limit: int = 20) -> dict:
        return container.skill_router.learning_status(resolve_workspace_id(workspace_id, default_workspace_id), limit)
