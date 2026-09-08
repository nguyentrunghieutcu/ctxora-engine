from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OBJECT = {"type": "object", "additionalProperties": True}
ARRAY_OBJECT = {"type": "array", "items": OBJECT}
ARRAY_STRING = {"type": "array", "items": {"type": "string"}}
SCHEMA_VERSION = "https://json-schema.org/draft/2020-12/schema"


def _object(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "$schema": SCHEMA_VERSION,
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = list(required)
    return schema


S = {"type": "string"}
I = {"type": "integer"}
N = {"type": "number"}
B = {"type": "boolean"}
NULLABLE_S = {"type": ["string", "null"]}
NULLABLE_N = {"type": ["number", "null"]}

REQUEST_SCHEMAS: dict[str, dict[str, Any]] = {
    "register_workspace": _object({"workspace_id": S, "roots": ARRAY_STRING, "initial_refresh": B}, ("workspace_id", "roots")),
    "refresh_workspace": _object({"workspace_id": S, "paths": {"type": ["array", "null"], "items": S}}),
    "plan_context": _object({"workspace_id": S, "query": S, "available_input_tokens": I, "strategy_override": S}, ("workspace_id", "query", "available_input_tokens")),
    "retrieve_context": _object({"workspace_id": S, "query": S, "top_k": I, "graph_expand": B, "token_budget": I}, ("workspace_id", "query")),
    "prepare_context": _object({"workspace_id": S, "query": S, "available_input_tokens": I, "preferred_strategy": S, "include_memory": B, "include_handoff": B, "handoff_id": S, "include_ecc": B, "freshness": S, "deadline_ms": I}, ("workspace_id", "query", "available_input_tokens")),
    "context_stats": _object({"workspace_id": S}),
    "invalidate_context": _object({"workspace_id": S, "target": S}, ("workspace_id", "target")),
    "memory_save": _object({"workspace_id": S, "key": S, "value": S, "mtype": S, "tags": S, "scope": S, "source": S, "confidence": N, "expires_at": NULLABLE_N}, ("workspace_id", "key", "value")),
    "memory_search": _object({"workspace_id": S, "query": S, "mtype": S, "top_k": I, "min_sim": N}, ("workspace_id", "query")),
    "memory_delete": _object({"workspace_id": S, "key": S, "mtype": S}, ("workspace_id", "key")),
    "memory_list": _object({"workspace_id": S, "mtype": S, "limit": I}, ("workspace_id",)),
    "handoff_conversation": _object({"workspace_id": S, "messages_json": S, "threshold_tokens": I, "label": S, "retention_seconds": I, "consent": B}, ("workspace_id", "messages_json")),
    "restore_conversation_handoff": _object({"workspace_id": S, "handoff_id": S}, ("workspace_id", "handoff_id")),
    "list_conversation_handoffs": _object({"workspace_id": S, "limit": I}, ("workspace_id",)),
    "delete_conversation_handoff": _object({"workspace_id": S, "handoff_id": S}, ("workspace_id", "handoff_id")),
    "purge_expired_handoffs": _object({}),
    "ecc_status": _object({}),
    "ecc_search": _object({"query": S, "limit": I}, ("query",)),
    "route_skills": _object({
        "workspace_id": S, "task": S, "profile": S, "top_k": I,
        "include_instructions": B, "token_budget": I,
    }, ("workspace_id", "task")),
    "skill_feedback": _object({
        "workspace_id": S, "route_id": S, "outcome": S,
        "skills": {"type": ["array", "null"], "items": S}, "correction_skill": S,
    }, ("workspace_id", "route_id", "outcome")),
    "skill_learning_status": _object({"workspace_id": S, "limit": I}, ("workspace_id",)),
}

RESPONSE_SCHEMAS = {name: {"$schema": SCHEMA_VERSION, **OBJECT} for name in REQUEST_SCHEMAS}
RESPONSE_SCHEMAS.update({
    "memory_search": {"$schema": SCHEMA_VERSION, **ARRAY_OBJECT},
    "memory_list": {"$schema": SCHEMA_VERSION, **ARRAY_STRING},
    "list_conversation_handoffs": {"$schema": SCHEMA_VERSION, **ARRAY_OBJECT},
    "prepare_context": _object({
        "api_version": S, "workspace_id": S, "snapshot_id": S, "snapshot_version": I,
        "plan": OBJECT, "stable_context": {"type": ["object", "null"]},
        "evidence": {"type": ["object", "null"]}, "memory": ARRAY_OBJECT,
        "handoff": {"type": ["object", "null"]}, "external_context": ARRAY_OBJECT,
        "diagnostics": OBJECT,
    }, ("api_version", "workspace_id", "snapshot_id", "snapshot_version", "plan", "stable_context", "evidence", "memory", "handoff", "external_context", "diagnostics")),
})

ERROR_SCHEMA = _object({
    "api_version": S,
    "error": _object({"code": S, "message": S, "retryable": B, "details": OBJECT}, ("code", "message", "retryable", "details")),
}, ("api_version", "error"))


def _matches_type(value: Any, expected: str) -> bool:
    return {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str), "integer": isinstance(value, int) and not isinstance(value, bool), "number": isinstance(value, (int, float)) and not isinstance(value, bool), "boolean": isinstance(value, bool), "null": value is None}[expected]


def validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected = schema.get("type")
    expected_types = expected if isinstance(expected, list) else [expected]
    if expected and not any(_matches_type(value, item) for item in expected_types):
        raise TypeError(f"{path} must be {expected}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError(f"{path}.{key} is required")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise ValueError(f"{path} contains unknown properties: {sorted(unknown)}")
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            validate_schema(item, schema["items"], f"{path}[{index}]")


def validate_response(contract: str, value: Any) -> Any:
    try:
        schema = RESPONSE_SCHEMAS[contract]
    except KeyError as error:
        raise KeyError(f"unknown MCP v2 response contract: {contract}") from error
    validate_schema(value, schema)
    return value


def export_json_schemas(directory: str | Path) -> list[Path]:
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    documents = {f"{name}.request.schema.json": schema for name, schema in REQUEST_SCHEMAS.items()}
    documents.update({f"{name}.response.schema.json": schema for name, schema in RESPONSE_SCHEMAS.items()})
    documents["error.response.schema.json"] = ERROR_SCHEMA
    written = []
    for filename, schema in sorted(documents.items()):
        path = destination / filename
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written
