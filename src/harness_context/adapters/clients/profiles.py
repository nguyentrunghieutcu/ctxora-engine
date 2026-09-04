from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness_context.branding import MCP_SERVER_KEY


@dataclass(frozen=True)
class ClientProfile:
    name: str
    config_format: str
    default_config: Path
    server_key: str = MCP_SERVER_KEY


PROFILES = {
    "codex": ClientProfile("codex", "toml", Path("~/.codex/config.toml")),
    "claude-code": ClientProfile("claude-code", "json", Path("~/.claude.json")),
    "cursor": ClientProfile("cursor", "json", Path("~/.cursor/mcp.json")),
    "generic-mcp": ClientProfile("generic-mcp", "json", Path("~/.config/mcp/servers.json")),
}


def get_profile(name: str) -> ClientProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unknown client profile: {name}") from exc
