from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from harness_context.application.container import ApplicationContainer
from harness_context.bootstrap import build_container, workspace_identity
from harness_context.interfaces.mcp.lifecycle import ServerLifecycle
from harness_context.paths import legacy_workspace_data_dir, workspace_data_dir


@dataclass(frozen=True)
class RuntimeConfig:
    workspace: Path
    workspace_id: str
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8765
    startup_policy: str = "block_until_ready"
    watch: bool = False
    ecc_enabled: bool = False
    ecc_allow_user_scope: bool = False


class HarnessRuntime:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.container: ApplicationContainer | None = None
        self.lifecycle = ServerLifecycle()

    @classmethod
    def for_workspace(
        cls, workspace: str, transport: str | None = None,
        host: str | None = None, port: int | None = None, watch: bool | None = None,
        ecc_enabled: bool | None = None, ecc_allow_user_scope: bool | None = None,
    ) -> HarnessRuntime:
        root = Path(workspace).expanduser().resolve(strict=True)
        values = {"transport": "stdio", "host": "127.0.0.1", "port": 8765, "startup_policy": "block_until_ready", "watch": False, "ecc_enabled": False, "ecc_allow_user_scope": False}
        for path in (
            Path.home() / ".config" / "harness" / "config.toml",
            Path.home() / ".config" / "ctxora" / "config.toml",
            legacy_workspace_data_dir(root) / "config.toml",
            workspace_data_dir(root) / "config.toml",
        ):
            if path.exists():
                loaded = tomllib.loads(path.read_text("utf-8"))
                unknown = set(loaded) - set(values)
                if unknown:
                    raise ValueError(f"unknown runtime config keys: {sorted(unknown)}")
                values.update(loaded)
        def environment_value(name: str) -> str | None:
            return os.environ.get(f"CTXORA_{name}") or os.environ.get(f"HARNESS_{name}")

        environment = {
            "transport": environment_value("TRANSPORT"),
            "host": environment_value("HOST"),
            "port": environment_value("PORT"),
            "ecc_enabled": environment_value("ECC_ENABLED"),
            "ecc_allow_user_scope": environment_value("ECC_ALLOW_USER_SCOPE"),
        }
        values.update({key: value for key, value in environment.items() if value not in {None, ""}})
        overrides = {"transport": transport, "host": host, "port": port, "watch": watch, "ecc_enabled": ecc_enabled, "ecc_allow_user_scope": ecc_allow_user_scope}
        values.update({key: value for key, value in overrides.items() if value is not None})
        def boolean(value) -> bool:
            return value.casefold() in {"1", "true", "yes", "on"} if isinstance(value, str) else bool(value)
        user_scope = boolean(values["ecc_allow_user_scope"])
        return cls(RuntimeConfig(
            root, workspace_identity(root), str(values["transport"]), str(values["host"]),
            int(values["port"]), str(values["startup_policy"]), boolean(values["watch"]),
            boolean(values["ecc_enabled"]) or user_scope, user_scope,
        ))

    def startup(self) -> dict:
        self.container = build_container(
            self.config.workspace, self.config.workspace_id,
            ecc_enabled=self.config.ecc_enabled,
            ecc_allow_user_scope=self.config.ecc_allow_user_scope,
        )
        warm = self.container.retrieval.snapshot_is_current(self.config.workspace_id)
        if not warm:
            refresh = self.container.refresh.execute(self.config.workspace_id)
        else:
            refresh = self.container.retrieval.stats(self.config.workspace_id)
        self.lifecycle.mark_ready()
        return {"warm_start": warm, **refresh}

    def health_report(self) -> dict[str, object]:
        lifecycle = self.lifecycle.status()
        if self.container is None:
            return {
                "schema_version": "ctxora.operator-snapshot.v1",
                "status": "not_ready",
                "ready": False,
                "runtime": lifecycle,
                "workspace": {"workspace_id": self.config.workspace_id, "root_count": 1},
                "snapshot": {},
                "index": {},
                "retrieval": {},
                "memory": {},
                "handoffs": {"count": 0, "recent": []},
                "skills": {},
                "installer": {"receipt_count": 0, "receipts": []},
                "metrics": {},
                "events": {
                    "items": [],
                    "cursor": "0",
                    "next_cursor": "0",
                    "has_more": False,
                },
            }
        lifecycle.update({
            "transport": self.config.transport,
            "host": self.config.host,
            "port": self.config.port,
        })
        return self.container.operations.snapshot(
            self.config.workspace_id, lifecycle
        ).to_dict()

    def drain(self, timeout: float = 10.0) -> bool:
        return self.lifecycle.drain(timeout)

    def run(self) -> None:
        if self.container is None:
            self.startup()
        from harness_context.interfaces.mcp.server import create_mcp_server
        from harness_context.watcher import WorkspaceWatcher
        server = create_mcp_server(self.container, self.config.workspace_id, self.lifecycle)
        watcher = WorkspaceWatcher(self.container.retrieval, self.container.refresh, self.config.workspace_id) if self.config.watch else None
        if watcher:
            watcher.start()
        try:
            if self.config.transport == "streamable-http":
                server.settings.host = self.config.host
                server.settings.port = self.config.port
                server.run(transport="streamable-http")
                return
            server.run(transport="stdio")
        finally:
            self.drain()
            if watcher:
                watcher.stop()
