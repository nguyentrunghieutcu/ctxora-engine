def register_skill_tools(mcp, container) -> None:
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
            workspace_id, task, profile, top_k, include_instructions, token_budget
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
            workspace_id, route_id, outcome, skills, correction_skill
        )

    @mcp.tool()
    def skill_learning_status(workspace_id: str, limit: int = 20) -> dict:
        return container.skill_router.learning_status(workspace_id, limit)
