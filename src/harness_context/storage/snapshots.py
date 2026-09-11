from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path

from harness_context.paths import workspace_state_dir
from harness_context.storage.migrations import MIGRATIONS
from harness_context.workspace import file_lock, validate_ready_snapshot

SCHEMA_VERSION = 2


class SnapshotStore:
    def __init__(self, workspace_root: str | Path):
        self.state_dir = workspace_state_dir(workspace_root)
        self.snapshots_dir = self.state_dir / "snapshots"
        self.candidates_dir = self.state_dir / "candidates"
        self.active_path = self.state_dir / "active.json"
        self.previous_path = self.state_dir / "active.previous.json"
        self.schema_path = self.state_dir / "schema.json"
        self.lock_path = self.state_dir / "state.lock"

    @staticmethod
    def _atomic_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def prepare(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with file_lock(self.lock_path):
            version = json.loads(self.schema_path.read_text("utf-8")).get("version", 0) if self.schema_path.exists() else 0
            if version > SCHEMA_VERSION:
                raise RuntimeError(f"snapshot schema {version} is newer than supported {SCHEMA_VERSION}")
            for migration in MIGRATIONS:
                if migration.version > version:
                    try:
                        migration.apply(self.state_dir)
                    except Exception:
                        if migration.rollback is not None:
                            migration.rollback(self.state_dir)
                        raise
                    self._atomic_json(self.schema_path, {"version": migration.version})
                    version = migration.version
            for temporary in self.state_dir.rglob("*.tmp"):
                temporary.unlink(missing_ok=True)
            self._recover_active()

    def _recover_active(self) -> None:
        if not self.active_path.exists() and self.previous_path.exists():
            os.replace(self.previous_path, self.active_path)
        if self.active_path.exists():
            try:
                active = json.loads(self.active_path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                active = {}
            if not (self.snapshots_dir / f"{active.get('snapshot_id', '')}.json").exists() and self.previous_path.exists():
                os.replace(self.previous_path, self.active_path)

    def create_candidate(self, snapshot: dict) -> str:
        validate_ready_snapshot(snapshot)
        candidate_id = self.begin_candidate(snapshot["workspace_id"])
        self.validate_candidate(candidate_id, snapshot)
        return candidate_id

    def begin_candidate(self, workspace_id: str) -> str:
        self.prepare()
        candidate_id = uuid.uuid4().hex
        self._atomic_json(self.candidates_dir / f"{candidate_id}.json", {
            "candidate_id": candidate_id, "workspace_id": workspace_id,
            "status": "building", "created_at": time.time(),
        })
        return candidate_id

    def validate_candidate(self, candidate_id: str, snapshot: dict) -> None:
        validate_ready_snapshot(snapshot)
        record_path = self.candidates_dir / f"{candidate_id}.json"
        record = json.loads(record_path.read_text("utf-8"))
        if record["workspace_id"] != snapshot["workspace_id"]:
            raise ValueError("candidate workspace does not match snapshot")
        record.update(status="validated", snapshot=snapshot, validated_at=time.time())
        self._atomic_json(record_path, record)

    def fail_candidate(self, candidate_id: str, error: Exception) -> None:
        record_path = self.candidates_dir / f"{candidate_id}.json"
        if not record_path.exists():
            return
        record = json.loads(record_path.read_text("utf-8"))
        record.update(status="failed", failed_at=time.time(), error=str(error))
        self._atomic_json(record_path, record)

    def promote_candidate(self, candidate_id: str) -> None:
        with file_lock(self.lock_path):
            record_path = self.candidates_dir / f"{candidate_id}.json"
            record = json.loads(record_path.read_text("utf-8"))
            if record.get("status") != "validated":
                raise ValueError("only validated candidates may be promoted")
            snapshot = record["snapshot"]
            validate_ready_snapshot(snapshot)
            snapshot_path = self.snapshots_dir / f"{snapshot['snapshot_id']}.json"
            if not snapshot_path.exists():
                self._atomic_json(snapshot_path, snapshot)
            if self.active_path.exists():
                self._atomic_json(self.previous_path, json.loads(self.active_path.read_text("utf-8")))
            self._atomic_json(self.active_path, {
                "workspace_id": snapshot["workspace_id"], "snapshot_id": snapshot["snapshot_id"],
                "snapshot_version": snapshot["snapshot_version"],
            })
            record["status"] = "promoted"
            self._atomic_json(record_path, record)
            retained = sorted(self.snapshots_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
            for expired in retained[3:]:
                expired.unlink(missing_ok=True)

    def promote(self, snapshot: dict) -> None:
        self.promote_candidate(self.create_candidate(snapshot))

    def rollback(self) -> None:
        with file_lock(self.lock_path):
            if not self.previous_path.exists():
                raise RuntimeError("no previous active snapshot")
            current = json.loads(self.active_path.read_text("utf-8")) if self.active_path.exists() else None
            previous = json.loads(self.previous_path.read_text("utf-8"))
            self._atomic_json(self.active_path, previous)
            if current:
                self._atomic_json(self.previous_path, current)

    def clear_active(self, workspace_id: str) -> None:
        with file_lock(self.lock_path):
            if self.active_path.exists():
                active = json.loads(self.active_path.read_text("utf-8"))
                if active.get("workspace_id") != workspace_id:
                    raise ValueError("active snapshot belongs to another workspace")
            self.active_path.unlink(missing_ok=True)
            self.previous_path.unlink(missing_ok=True)

    def load_active(self, workspace_id: str) -> dict | None:
        self.prepare()
        with file_lock(self.lock_path):
            if not self.active_path.exists():
                return None
            active = json.loads(self.active_path.read_text("utf-8"))
            if active.get("workspace_id") != workspace_id:
                return None
            path = self.snapshots_dir / f"{active['snapshot_id']}.json"
            return json.loads(path.read_text("utf-8")) if path.exists() else None
