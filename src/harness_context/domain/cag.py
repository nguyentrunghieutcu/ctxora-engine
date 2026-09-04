from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence

from harness_context.domain.planning import ContextPlanner
from harness_context.schemas import ContextItem


class CAGStore:
    def build(self, workspace_id: str, items: Sequence[ContextItem], version: int, ttl_seconds: int) -> dict:
        stable = [item for item in items if ContextPlanner.is_stable(item)]
        sources = [{"path": item.path, "content_hash": item.content_hash, "start_line": item.start_line, "end_line": item.end_line} for item in sorted(stable, key=lambda item: (item.path, item.start_line))]
        bundle_id = "sha256:" + hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
        now = time.time()
        return {"bundle_id": bundle_id, "workspace_id": workspace_id, "version": version, "bundle_type": "project_core", "model_family": "provider-neutral", "token_count": sum(item.tokens for item in stable), "created_at": now, "expires_at": now + ttl_seconds, "sources": sources, "items": [item.to_dict() for item in stable]}
