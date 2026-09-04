from __future__ import annotations

from harness_context.adapters.ecc.provenance import ecc_provenance

_TYPE_MAP = {
    "handoff": "episodic",
    "lesson": "procedural",
    "runbook": "procedural",
    "context": "semantic",
    "decision": "semantic",
    "fact": "semantic",
    "note": "semantic",
    "preference": "semantic",
}


def map_ecc_memory(memory: dict, source_path) -> dict:
    """Map ECC context into Harness's provider-neutral read-only memory shape."""
    return {
        "workspace_id": "external:ecc",
        "type": _TYPE_MAP[memory["kind"]],
        "key": memory["id"],
        "value": memory["body"],
        "title": memory["title"],
        "tags": ",".join(memory["tags"]),
        "scope": memory["scope"],
        "source": f"ecc:{memory['sourceHarness']}",
        "confidence": 0.5,
        "status": memory["status"],
        "links": list(memory["links"]),
        "provenance": ecc_provenance(memory, source_path),
    }
