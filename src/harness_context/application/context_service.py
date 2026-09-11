from __future__ import annotations

import time

from harness_context.adapters.ecc import EccMemoryReader
from harness_context.api.v2 import ContextPackageV2, PrepareContextRequest
from harness_context.engine import ContextEngine
from harness_context.infrastructure.compact.handoff import ConversationHandoffStore
from harness_context.infrastructure.memory.episodic import MemoryStore
from harness_context.schemas import HarnessError
from harness_context.skills import SkillRouter


class ContextService:
    def __init__(self, engine: ContextEngine, memory: MemoryStore, handoffs: ConversationHandoffStore, ecc: EccMemoryReader | None = None, skill_router: SkillRouter | None = None):
        self.engine = engine
        self.memory = memory
        self.handoffs = handoffs
        self.ecc = ecc
        self.skill_router = skill_router

    def prepare(self, request: PrepareContextRequest) -> ContextPackageV2:
        if request.deadline_ms <= 0:
            raise HarnessError("invalid_deadline", "deadline_ms must be positive")
        started = time.perf_counter()
        preferred = "" if request.preferred_strategy == "auto" else request.preferred_strategy
        with self.engine.snapshot_pin(request.workspace_id) as pin:
            if request.freshness == "current" and not self.engine.snapshot_is_current(request.workspace_id, pin.state):
                raise HarnessError("stale_snapshot", "active snapshot is stale; refresh_workspace is required")
            prepared = self.engine.prepare_context(request.workspace_id, request.query, request.available_input_tokens, preferred, pin)
        evidence = prepared["retrieval"]
        memory = self.memory.search(request.query, top_k=4, workspace_id=request.workspace_id) if request.include_memory else []
        handoff = None
        if request.include_handoff:
            if not request.handoff_id:
                raise HarnessError("missing_handoff_id", "handoff_id is required when include_handoff is true")
            handoff = self.handoffs.restore(request.handoff_id, request.workspace_id)
            if handoff is None:
                raise HarnessError("handoff_not_found", "handoff was not found in this workspace")
        external_context, ecc_diagnostics = [], []
        if request.include_ecc:
            if self.ecc is None or not self.ecc.installation.available:
                raise HarnessError("ecc_not_available", "ECC adapter is not enabled or no local ECC vault was detected")
            ecc_result = self.ecc.search(request.query, limit=4)
            external_context, ecc_diagnostics = ecc_result["entries"], ecc_result["diagnostics"]
        skill_diagnostics = {"enabled": self.skill_router is not None}
        if self.skill_router is not None:
            try:
                routed = self.skill_router.route(request.workspace_id, request.query, top_k=3, include_instructions=False, token_budget=0)
                skill_diagnostics.update({"route_id": routed["route_id"], "profile": routed["profile"], "recommendations": routed["recommendations"], "feedback_policy": routed["feedback_policy"]})
            except ValueError as error:
                skill_diagnostics.update({"recommendations": [], "routing_error": str(error)})
        elapsed_ms = (time.perf_counter() - started) * 1000
        if elapsed_ms > request.deadline_ms:
            raise HarnessError("deadline_exceeded", "context preparation exceeded deadline_ms")
        diagnostics = {"coverage": evidence.get("coverage", "not_applicable") if evidence else "not_applicable", "freshness": request.freshness, "untrusted_content": True, "latency_ms": round(elapsed_ms, 3), "ecc": {"enabled": self.ecc is not None, "diagnostics": ecc_diagnostics}, "skills": skill_diagnostics}
        return ContextPackageV2(api_version="2.0", workspace_id=request.workspace_id, snapshot_id=prepared["snapshot_id"], snapshot_version=prepared["snapshot_version"], plan=prepared["plan"], stable_context=prepared["bundle"], evidence=evidence, memory=memory, handoff=handoff, external_context=external_context, diagnostics=diagnostics)

    def prepare_values(self, **values) -> dict:
        return self.prepare(PrepareContextRequest(**values)).to_dict()
