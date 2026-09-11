from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Capability(str, Enum):
    MCP = "mcp"
    SKILLS = "skills"
    AGENTS = "agents"
    COMMANDS = "commands"
    RULES = "rules"
    HOOKS = "hooks"


@dataclass(frozen=True)
class HarnessTarget:
    id: str
    display_name: str
    adapter_id: str
    aliases: tuple[str, ...] = ()
    capabilities: frozenset[Capability] = frozenset()
    config_format: str | None = None
    default_config: Path | None = None
    artifact_roots: tuple[tuple[str, str], ...] = ()

    def supports(self, capability: Capability | str) -> bool:
        return Capability(capability) in self.capabilities

    def artifact_root(self, kind: str) -> str | None:
        return dict(self.artifact_roots).get(kind)

