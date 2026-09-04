from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from typing import Any


class ProviderFormatter:
    def format(self, payload: Any) -> dict[str, Any]:
        if hasattr(payload, "to_dict"):
            payload = payload.to_dict()
        elif is_dataclass(payload):
            payload = asdict(payload)
        if not isinstance(payload, dict):
            raise TypeError("provider payload must be a mapping or dataclass")
        return deepcopy(payload)


class CodexFormatter(ProviderFormatter):
    pass


class ClaudeCodeFormatter(ProviderFormatter):
    pass


class CursorFormatter(ProviderFormatter):
    pass


class GenericMcpFormatter(ProviderFormatter):
    pass


FORMATTERS = {
    "codex": CodexFormatter,
    "claude-code": ClaudeCodeFormatter,
    "cursor": CursorFormatter,
    "generic-mcp": GenericMcpFormatter,
}


def get_formatter(name: str) -> ProviderFormatter:
    try:
        return FORMATTERS[name]()
    except KeyError as exc:
        raise ValueError(f"unknown provider formatter: {name}") from exc
