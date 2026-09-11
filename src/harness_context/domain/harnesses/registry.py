from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_context.domain.harnesses.models import Capability, HarnessTarget


class HarnessRegistry:
    def __init__(self, targets: tuple[HarnessTarget, ...]):
        self._targets = {target.id: target for target in targets}
        self._aliases = {
            alias: target.id
            for target in targets
            for alias in (target.id, *target.aliases)
        }
        if len(self._aliases) != sum(1 + len(target.aliases) for target in targets):
            raise ValueError("duplicate harness target id or alias")

    @classmethod
    def load(cls, path: str | Path) -> HarnessRegistry:
        data = json.loads(Path(path).read_text("utf-8"))
        if data.get("version") != 1 or not isinstance(data.get("targets"), list):
            raise ValueError("unsupported harness registry manifest")
        return cls(tuple(cls._parse_target(item) for item in data["targets"]))

    @staticmethod
    def _parse_target(item: dict[str, Any]) -> HarnessTarget:
        required = {"id", "display_name", "adapter", "capabilities", "artifacts"}
        missing = required - item.keys()
        if missing:
            raise ValueError(f"harness target is missing fields: {sorted(missing)}")
        identifier = str(item["id"])
        aliases = tuple(str(alias) for alias in item.get("aliases", []))
        capabilities = frozenset(Capability(value) for value in item["capabilities"])
        mcp = item.get("mcp") or {}
        config_format = mcp.get("config_format")
        default_config = Path(mcp["default_config"]) if mcp.get("default_config") else None
        artifacts = tuple(sorted((str(key), str(value)) for key, value in item["artifacts"].items()))
        if not identifier or any(not alias for alias in aliases):
            raise ValueError("harness target identifiers must be non-empty")
        if Capability.MCP in capabilities and (config_format not in {"json", "toml"} or default_config is None):
            raise ValueError(f"MCP target {identifier} requires config metadata")
        for kind in artifacts:
            Capability(kind[0])
        return HarnessTarget(
            id=identifier,
            display_name=str(item["display_name"]),
            adapter_id=str(item["adapter"]),
            aliases=aliases,
            capabilities=capabilities,
            config_format=config_format,
            default_config=default_config,
            artifact_roots=artifacts,
        )

    def get(self, name: str) -> HarnessTarget:
        try:
            return self._targets[self._aliases[name]]
        except KeyError as error:
            raise ValueError(f"unknown harness target: {name}") from error

    def targets(self, capability: Capability | str | None = None) -> tuple[HarnessTarget, ...]:
        values = tuple(self._targets.values())
        if capability is None:
            return values
        expected = Capability(capability)
        return tuple(target for target in values if target.supports(expected))


DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "artifacts" / "manifests" / "harnesses.json"
REGISTRY = HarnessRegistry.load(DEFAULT_MANIFEST)

