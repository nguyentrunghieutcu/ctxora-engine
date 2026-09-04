from __future__ import annotations

from pathlib import Path


def ecc_provenance(memory: dict, source_path: Path) -> dict:
    return {
        "adapter": "ecc",
        "schema": memory["schema"],
        "ecc_memory_id": memory["id"],
        "source_path": str(source_path),
        "source_harness": memory["sourceHarness"],
        "updated_at": memory["updatedAt"],
        "trust": memory["trust"],
        "read_only": True,
    }
