from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness_context.branding import MCP_SERVER_KEY
from harness_context.domain.harnesses import REGISTRY, Capability


@dataclass(frozen=True)
class ClientProfile:
    name: str
    config_format: str
    default_config: Path
    server_key: str = MCP_SERVER_KEY


PROFILES = {
    target.id: ClientProfile(target.id, target.config_format or "", target.default_config or Path())
    for target in REGISTRY.targets(Capability.MCP)
}


def get_profile(name: str) -> ClientProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        available = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown client profile: {name}. Available profiles: {available}") from exc
