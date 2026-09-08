from __future__ import annotations

from pathlib import Path

from compact.handoff import ConversationHandoffStore
from harness_context.adapters.ecc import EccMemoryReader, detect_ecc
from harness_context.application.container import ApplicationContainer
from harness_context.application.ecc_service import EccService
from harness_context.application.handoff_service import HandoffService
from harness_context.application.memory_service import MemoryService
from harness_context.application.retrieval_service import RetrievalService
from harness_context.application.services import ContextService, RefreshService
from harness_context.application.workspace_service import WorkspaceService
from harness_context.engine import ContextEngine
from harness_context.paths import workspace_state_dir
from harness_context.skills import SkillRouter
from harness_context.storage import SnapshotStore
from harness_context.workspace.identity import workspace_identity
from memory.episodic import MemoryStore


def build_container(root: str | Path, workspace_id: str = "", *, ecc_enabled: bool = False, ecc_allow_user_scope: bool = False) -> ApplicationContainer:
    canonical = Path(root).expanduser().resolve(strict=True)
    identity = workspace_id or workspace_identity(canonical)
    engine = ContextEngine()
    engine.register_workspace(identity, [str(canonical)])
    snapshots = SnapshotStore(canonical)
    snapshots.prepare()
    active = snapshots.load_active(identity)
    if active:
        engine.load_snapshot(active)
    data_dir = workspace_state_dir(canonical)
    memory = MemoryStore(str(data_dir / "memory.sqlite3"))
    handoffs = ConversationHandoffStore(str(data_dir / "handoffs.sqlite3"))
    ecc = EccMemoryReader(detect_ecc(canonical, allow_user_scope=ecc_allow_user_scope)) if ecc_enabled else None
    skill_router = SkillRouter(canonical, identity)
    refresh = RefreshService(engine, snapshots)
    return ApplicationContainer(
        engine=engine, snapshots=snapshots,
        refresh=refresh,
        context=ContextService(engine, memory, handoffs, ecc, skill_router),
        memory=memory, handoffs=handoffs,
        ecc=ecc,
        workspace=WorkspaceService(engine, refresh, identity),
        retrieval=RetrievalService(engine, ecc),
        memories=MemoryService(memory),
        handoff=HandoffService(handoffs),
        ecc_queries=EccService(ecc),
        skill_router=skill_router,
    )
