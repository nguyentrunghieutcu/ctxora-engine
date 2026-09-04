class RetrievalService:
    def __init__(self, engine, ecc=None):
        self.engine, self.ecc = engine, ecc

    def plan(self, workspace_id, query, available_input_tokens, strategy_override=""):
        with self.engine.snapshot_pin(workspace_id) as pin:
            return self.engine.plan_context(workspace_id, query, available_input_tokens, strategy_override, pin.state)

    def retrieve(self, workspace_id, query, top_k=12, graph_expand=True, token_budget=4_000):
        with self.engine.snapshot_pin(workspace_id) as pin:
            result = self.engine.retrieve_context(workspace_id, query, top_k, graph_expand, token_budget, pin.state)
            result["snapshot_id"] = pin.snapshot_id
            result["snapshot_version"] = pin.snapshot_version
            return result

    def stats(self, workspace_id):
        result = self.engine.stats(workspace_id)
        result["adapters"] = {"ecc": self.ecc.status() if self.ecc else {"enabled": False, "available": False, "read_only": True}}
        return result

    def snapshot_is_current(self, workspace_id):
        return self.engine.snapshot_is_current(workspace_id)
