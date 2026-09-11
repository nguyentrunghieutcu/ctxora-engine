from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path

from harness_context.domain import (
    CAGStore,
    ContextPlanner,
    CoveragePolicy,
    GraphExpander,
    RankFusion,
    Selector,
)
from harness_context.infrastructure.chunking.treesitter_chunker import count_tokens
from harness_context.infrastructure.graph import LocalGraphBuilder
from harness_context.infrastructure.indexes import (
    LocalLexicalIndex,
    LocalPathIndex,
    LocalSemanticIndex,
    LocalSymbolIndex,
)
from harness_context.infrastructure.parsing import LocalParserDispatcher
from harness_context.infrastructure.retrieval.embeddings import EmbeddingEngine
from harness_context.infrastructure.scanning import (
    ChangeSet,
    LocalManifest,
    LocalScanner,
    fingerprint,
)
from harness_context.schemas import ContextItem, HarnessError
from harness_context.storage.pins import SnapshotPin
from harness_context.tokenize import tokens
from harness_context.workspace import (
    WorkspaceRegistry,
    transition_workspace_status,
    validate_ready_snapshot,
)


@dataclass
class WorkspaceState:
    items: list[ContextItem] = field(default_factory=list)
    fingerprints: dict[str, str] = field(default_factory=dict)
    embedder: EmbeddingEngine = field(default_factory=EmbeddingEngine)
    vectors: list[list[float]] = field(default_factory=list)
    graph: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    bundles: dict[str, dict] = field(default_factory=dict)
    refreshed_at: float = 0.0
    last_retrieval_ms: float = 0.0
    last_coverage: str = "unknown"
    snapshot_id: str = ""
    snapshot_version: int = 0
    status: str = "registered"


class LocalContextEngine:
    def __init__(self) -> None:
        self.registry = WorkspaceRegistry()
        self.states: dict[str, WorkspaceState] = {}
        self._refresh_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.parser = LocalParserDispatcher()
        self.planner = ContextPlanner()
        self.rank_fusion = RankFusion()
        self.graph_expander = GraphExpander()
        self.selector = Selector()
        self.coverage_policy = CoveragePolicy()
        self.cag_store = CAGStore()
        self.graph_builder = LocalGraphBuilder()

    def register_workspace(self, workspace_id: str, roots: list[str], **limits: int) -> dict:
        policy = self.registry.register(workspace_id, roots, **limits)
        self.states.setdefault(workspace_id, WorkspaceState())
        return {"workspace_id": workspace_id, "roots": list(policy.roots), "policy": asdict(policy)}

    @staticmethod
    def _fingerprint(path: Path) -> str:
        return fingerprint(path)

    @staticmethod
    def _item(workspace_id: str, path: Path, kind: str, symbol: str, start: int, end: int, content: str) -> ContextItem:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        identity = f"{workspace_id}\0{path}\0{kind}\0{symbol}\0{start}\0{end}\0{digest}"
        return ContextItem(
            chunk_id=hashlib.sha256(identity.encode()).hexdigest(), workspace_id=workspace_id,
            path=str(path), start_line=start, end_line=end, type=kind, symbol=symbol,
            content=content, tokens=count_tokens(content), content_hash=digest,
        )

    def _chunk_file(self, workspace_id: str, path: Path) -> list[ContextItem]:
        return self.parser.parse(workspace_id, path)

    def refresh_workspace(self, workspace_id: str, paths: list[str] | None = None) -> dict:
        candidate, result = self.build_workspace_snapshot(workspace_id, paths)
        self.activate_snapshot(workspace_id, candidate)
        return result

    def build_workspace_snapshot(self, workspace_id: str, paths: list[str] | None = None) -> tuple[WorkspaceState, dict]:
        with self._refresh_locks[workspace_id]:
            policy = self.registry.get(workspace_id)
            requested = paths or list(policy.roots)
            scanner = LocalScanner(self.registry)
            files = scanner.scan(workspace_id, requested)
            active = self.states.setdefault(workspace_id, WorkspaceState())
            discovered = scanner.fingerprints(files)
            scopes = [Path(path).expanduser().resolve(strict=False) for path in paths] if paths else []
            changes = ChangeSet.calculate(active.fingerprints, discovered, scopes)
            current, changed, removed = changes.current, changes.changed, changes.removed
            candidate = WorkspaceState(
                items=[item for item in active.items if item.path not in changed | removed],
                fingerprints=current,
                bundles=dict(active.bundles),
                snapshot_version=active.snapshot_version + 1,
                status=transition_workspace_status(active.status, "indexing"),
            )
            for path in sorted(changed):
                candidate.items.extend(self._chunk_file(workspace_id, Path(path)))
            candidate.vectors = candidate.embedder.rebuild([item.content for item in candidate.items])
            self._build_graph(candidate)
            candidate.snapshot_id = LocalManifest.snapshot_id(candidate.snapshot_version, current)
            candidate.refreshed_at = time.time()
            candidate.status = transition_workspace_status(candidate.status, "ready")
            snapshot = self.export_state(workspace_id, candidate)
            validate_ready_snapshot(snapshot)
            return candidate, {
                "workspace_id": workspace_id, "snapshot_id": candidate.snapshot_id,
                "snapshot_version": candidate.snapshot_version, "status": candidate.status,
                "files": len(files), "chunks": len(candidate.items),
                "changed_files": len(changed), "removed_files": len(removed),
            }

    def activate_snapshot(self, workspace_id: str, candidate: WorkspaceState) -> None:
        self.states[workspace_id] = candidate

    def pin_snapshot(self, workspace_id: str) -> SnapshotPin:
        state = self.states.get(workspace_id)
        if state is None or not state.snapshot_id:
            raise HarnessError("workspace_not_ready", f"workspace has no active snapshot: {workspace_id}")
        return SnapshotPin(workspace_id, state.snapshot_id, state.snapshot_version, state)

    @contextmanager
    def snapshot_pin(self, workspace_id: str):
        yield self.pin_snapshot(workspace_id)

    def export_snapshot(self, workspace_id: str) -> dict:
        return self.export_state(workspace_id, self.states[workspace_id])

    def export_state(self, workspace_id: str, state: WorkspaceState) -> dict:
        return {
            "workspace_id": workspace_id, "snapshot_id": state.snapshot_id,
            "snapshot_version": state.snapshot_version, "status": state.status,
            "fingerprints": state.fingerprints, "items": [item.to_dict() for item in state.items],
            "bundles": state.bundles, "refreshed_at": state.refreshed_at,
        }

    def load_snapshot(self, snapshot: dict) -> None:
        workspace_id = snapshot["workspace_id"]
        state = WorkspaceState(
            items=[ContextItem(**item) for item in snapshot.get("items", [])],
            fingerprints=dict(snapshot.get("fingerprints", {})),
            bundles=dict(snapshot.get("bundles", {})),
            refreshed_at=float(snapshot.get("refreshed_at", 0)),
            snapshot_id=snapshot.get("snapshot_id", ""),
            snapshot_version=int(snapshot.get("snapshot_version", 0)),
            status=snapshot.get("status", "ready"),
        )
        state.vectors = state.embedder.rebuild([item.content for item in state.items])
        self._build_graph(state)
        self.states[workspace_id] = state

    def snapshot_is_current(self, workspace_id: str, _state: WorkspaceState | None = None) -> bool:
        state = _state or self.states.get(workspace_id)
        if state is None or not state.snapshot_id:
            return False
        policy = self.registry.get(workspace_id)
        files = self.registry.files(workspace_id, list(policy.roots))
        current = {str(path): self._fingerprint(path) for path in files}
        return current == state.fingerprints

    @staticmethod
    def _build_graph(state: WorkspaceState) -> None:
        state.graph = LocalGraphBuilder().build(state.items)

    @staticmethod
    def _rank(query: str, state: WorkspaceState, top_n: int) -> list[ContextItem]:
        if not state.items:
            return []
        semantic_index = LocalSemanticIndex(state.embedder); semantic_index.vectors = state.vectors
        indexes = [semantic_index, LocalLexicalIndex(), LocalSymbolIndex(), LocalPathIndex()]
        semantic_scores, lexical, symbol, path_scores = [index.scores(query, state.items) for index in indexes]
        pools = [semantic_scores, lexical, symbol, path_scores]
        weights = [1.0, 1.2, 1.5, 1.1]
        results = []
        for index, score in RankFusion().fuse(pools, weights, top_n):
            item = ContextItem(**state.items[index].to_dict())
            item.score = score
            item.signals = {"semantic": semantic_scores[index], "lexical": lexical[index], "symbol": symbol[index], "path": path_scores[index]}
            results.append(item)
        return results

    @staticmethod
    def _excerpt(item: ContextItem, query: str, max_lines: int = 80) -> ContextItem:
        lines = item.content.splitlines()
        query_tokens = set(tokens(query))
        matches = [index for index, line in enumerate(lines) if query_tokens & set(tokens(line))]
        if not matches or len(lines) <= max_lines:
            return item
        center = matches[0]
        start = max(0, center - max_lines // 3)
        item.content = "\n".join(lines[start:start + max_lines])
        item.start_line += start
        item.end_line = item.start_line + len(item.content.splitlines()) - 1
        item.tokens = count_tokens(item.content)
        return item

    def retrieve_context(self, workspace_id: str, query: str, top_k: int = 12, graph_expand: bool = True, token_budget: int = 4000, _state: WorkspaceState | None = None) -> dict:
        started = time.perf_counter()
        state = _state or self.states.get(workspace_id)
        if state is None:
            raise HarnessError("unknown_workspace", f"workspace not registered: {workspace_id}")
        ranked = self._rank(query, state, max(top_k * 4, 40))
        selected = ranked[:top_k]
        if graph_expand:
            selected = self.graph_expander.expand(selected, state.items, state.graph)
        excerpts = [self._excerpt(ContextItem(**item.to_dict()), query) for item in selected]
        chosen, used = self.selector.select(excerpts, token_budget)
        output = [item.to_dict() for item in chosen]
        confidence = min(1.0, sum(item.get("score", 0.0) for item in output) * 10)
        coverage, missing = self.coverage_policy.assess(query, output)
        state.last_retrieval_ms = (time.perf_counter() - started) * 1000
        state.last_coverage = coverage
        return {"workspace_id": workspace_id, "query_fingerprint": hashlib.sha256(query.encode()).hexdigest()[:16], "items": output, "token_count": used, "coverage": coverage, "confidence": confidence, "missing_signals": missing, "recommended_action": "expand_search" if missing else "answer_from_evidence", "latency_ms": round(state.last_retrieval_ms, 3), "untrusted_content": True}

    def long_context(self, workspace_id: str, token_budget: int, _state: WorkspaceState | None = None) -> dict:
        state = _state or self.states[workspace_id]
        items, used = [], 0
        for item in sorted(state.items, key=lambda item: (item.path, item.start_line)):
            if used + item.tokens > token_budget:
                continue
            used += item.tokens
            items.append(item.to_dict())
        coverage = "sufficient" if len(items) == len(state.items) else "partial"
        return {"workspace_id": workspace_id, "items": items, "token_count": used, "coverage": coverage, "authorized_corpus_only": True, "untrusted_content": True}

    def plan_context(self, workspace_id: str, query: str, available_input_tokens: int, strategy_override: str = "", _state: WorkspaceState | None = None) -> dict:
        state = _state or self.states.get(workspace_id)
        if state is None:
            raise HarnessError("unknown_workspace", f"workspace not registered: {workspace_id}")
        return self.planner.plan(workspace_id, query, available_input_tokens, state.items, strategy_override)

    def prepare_bundle(self, workspace_id: str, ttl_seconds: int = 604800, _state: WorkspaceState | None = None, _record: bool = False) -> dict:
        state = _state or self.states[workspace_id]
        version = len(state.bundles) + 1
        manifest = self.cag_store.build(workspace_id, state.items, version, ttl_seconds)
        bundle_id = manifest["bundle_id"]
        manifest["version"] = len(state.bundles) + (bundle_id not in state.bundles)
        if _record:
            state.bundles[bundle_id] = manifest
        return manifest

    def prepare_context(self, workspace_id: str, query: str, available_input_tokens: int, strategy_override: str = "", pin: SnapshotPin | None = None) -> dict:
        pin = pin or self.pin_snapshot(workspace_id)
        state = pin.state
        plan = self.plan_context(workspace_id, query, available_input_tokens, strategy_override, state)
        result = {"snapshot_id": pin.snapshot_id, "snapshot_version": pin.snapshot_version, "plan": plan, "bundle": None, "retrieval": None}
        if plan["strategy"] in {"cag", "hybrid_cag_rag"}:
            result["bundle"] = self.prepare_bundle(workspace_id, _state=state)
        if plan["strategy"] == "long_context":
            result["retrieval"] = self.long_context(workspace_id, available_input_tokens, state)
        elif plan["strategy"] != "cag":
            result["retrieval"] = self.retrieve_context(workspace_id, query, graph_expand=plan["graph_expand"], token_budget=plan["rag_budget_tokens"], _state=state)
        return result

    def stats(self, workspace_id: str) -> dict:
        state = self.states[workspace_id]
        return {"workspace_id": workspace_id, "status": state.status, "snapshot_id": state.snapshot_id, "snapshot_version": state.snapshot_version, "files": len(state.fingerprints), "chunks": len(state.items), "tokens": sum(item.tokens for item in state.items), "graph_edges": sum(map(len, state.graph.values())), "bundles": len(state.bundles), "refreshed_at": state.refreshed_at, "last_retrieval_ms": state.last_retrieval_ms, "last_coverage": state.last_coverage}

    def invalidate(self, workspace_id: str, target: str = "all") -> dict:
        active = self.states[workspace_id]
        state = deepcopy(active)
        if target in {"all", "index"}:
            state.items.clear(); state.fingerprints.clear(); state.vectors.clear(); state.graph.clear()
            state.status = transition_workspace_status(state.status, "registered")
        if target in {"all", "bundles"}:
            state.bundles.clear()
        state.snapshot_version += 1
        state.snapshot_id = hashlib.sha256(
            f"{active.snapshot_id}:{target}:{state.snapshot_version}".encode()
        ).hexdigest()
        self.states[workspace_id] = state
        return {"workspace_id": workspace_id, "invalidated": target, "snapshot_id": state.snapshot_id, "snapshot_version": state.snapshot_version, "status": state.status}
