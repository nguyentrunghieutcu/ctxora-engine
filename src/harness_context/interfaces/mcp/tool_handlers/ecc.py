def register_ecc_tools(mcp, container) -> None:
    @mcp.tool()
    def ecc_status() -> dict:
        return container.ecc_queries.status()

    @mcp.tool()
    def ecc_search(query: str, limit: int = 4) -> dict:
        return container.ecc_queries.search(query, limit)
