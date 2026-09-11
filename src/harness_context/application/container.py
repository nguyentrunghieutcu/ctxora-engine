from __future__ import annotations

from dataclasses import dataclass

from harness_context.adapters.ecc import EccMemoryReader
from harness_context.application.ecc_service import EccService
from harness_context.application.handoff_service import HandoffService
from harness_context.application.memory_service import MemoryService
from harness_context.application.operator_service import OperatorService
from harness_context.application.retrieval_service import RetrievalService
from harness_context.application.services import ContextService, RefreshService
from harness_context.application.update_service import UpdateService
from harness_context.application.workspace_service import WorkspaceService
from harness_context.engine import ContextEngine
from harness_context.infrastructure.compact.handoff import ConversationHandoffStore
from harness_context.infrastructure.memory.episodic import MemoryStore
from harness_context.observability import LocalMetrics, StructuredEventSink
from harness_context.skills import SkillRouter
from harness_context.storage import SnapshotStore


@dataclass(frozen=True)
class ApplicationContainer:
    engine: ContextEngine
    snapshots: SnapshotStore
    refresh: RefreshService
    context: ContextService
    memory: MemoryStore
    handoffs: ConversationHandoffStore
    ecc: EccMemoryReader | None
    workspace: WorkspaceService
    retrieval: RetrievalService
    memories: MemoryService
    handoff: HandoffService
    ecc_queries: EccService
    skill_router: SkillRouter
    events: StructuredEventSink
    metrics: LocalMetrics
    operations: OperatorService
    updates: UpdateService
