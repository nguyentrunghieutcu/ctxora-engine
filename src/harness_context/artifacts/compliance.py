from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from harness_context.artifacts.catalog import CANONICAL_ROOT, canonical_artifact_drift

SCHEMA_VERSION = "https://json-schema.org/draft/2020-12/schema"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PERSONAL_PATH = re.compile(r"(?:/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\Users\\[^\\\s]+)")
REFERENCE = re.compile(r"\bctxora-[a-z0-9-]+\b")


def _object(properties: dict[str, Any], required: tuple[str, ...]) -> dict[str, Any]:
    return {
        "$schema": SCHEMA_VERSION,
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


S = {"type": "string"}
STRING_ARRAY = {"type": "array", "items": S}
SCHEMAS = {
    "harness-registry": _object({"version": {"type": "integer"}, "targets": {"type": "array"}}, ("version", "targets")),
    "artifact-manifest": _object({"schema_version": S, "canonical_root": S, "projections": {"type": "object"}, "artifact_count": {"type": "integer"}, "artifacts": {"type": "array"}}, ("schema_version", "canonical_root", "projections", "artifact_count", "artifacts")),
    "install-request": _object({"profile": S, "targets": STRING_ARRAY, "artifacts": STRING_ARRAY, "force": {"type": "boolean"}, "prune": {"type": "boolean"}}, ("profile", "targets", "artifacts")),
    "install-plan": _object({"target": S, "profile": S, "destination": S, "operations": {"type": "array"}, "conflicts": STRING_ARRAY, "skipped": {"type": "array"}, "metadata": {"type": "array"}, "digest": S}, ("target", "profile", "destination", "operations", "digest")),
    "install-receipt": _object({"schema_version": S, "plan_digest": S, "target": S, "profile": S, "destination": S, "installed_hashes": {"type": "array"}, "previous_ownership": {"type": "array"}, "verified": {"type": "boolean"}, "metadata": {"type": "object"}}, ("schema_version", "plan_digest", "target", "profile", "destination", "installed_hashes")),
    "agent-definition": _object({"name": S, "description": S, "body": S}, ("name", "description", "body")),
    "command-definition": _object({"description": S, "argument-hint": S, "body": S}, ("description", "body")),
}


def _identifier(value: str, label: str) -> None:
    if not IDENTIFIER.fullmatch(value) or unicodedata.normalize("NFC", value) != value:
        raise ValueError(f"invalid {label}: {value!r}")


def _portable_path(value: str, label: str) -> None:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or value.startswith("~"):
        raise ValueError(f"{label} must be a portable relative path")
    if PERSONAL_PATH.search(value) or unicodedata.normalize("NFC", value) != value:
        raise ValueError(f"{label} contains a personal or unsafe path")


def _portable_text(value: str, label: str) -> None:
    if unicodedata.normalize("NFC", value) != value or PERSONAL_PATH.search(value):
        raise ValueError(f"{label} contains non-portable text")
    if any(unicodedata.category(character) == "Cc" and character not in "\n\r\t" for character in value):
        raise ValueError(f"{label} contains control characters")


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text("utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"{path.name} requires frontmatter")
    header, body = text[4:].split("\n---\n", 1)
    values = {}
    for line in header.splitlines():
        if ":" not in line:
            raise ValueError(f"invalid frontmatter in {path.name}")
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    values["body"] = body.strip()
    return values


def validate_harness_manifest(data: dict[str, Any]) -> None:
    if data.get("version") != 1 or not isinstance(data.get("targets"), list):
        raise ValueError("unsupported harness registry schema")
    seen = set()
    for target in data["targets"]:
        identifier = str(target.get("id", ""))
        _identifier(identifier, "target id")
        aliases = [str(value) for value in target.get("aliases", [])]
        capabilities = set(target.get("capabilities", []))
        if identifier in seen or any(alias in seen for alias in aliases):
            raise ValueError("duplicate harness target id or alias")
        for alias in aliases:
            _identifier(alias, "target alias")
        seen.update((identifier, *aliases))
        for kind, destination in target.get("artifacts", {}).items():
            if kind not in capabilities:
                raise ValueError(f"target {identifier} maps undeclared capability {kind}")
            _portable_path(str(destination), f"target {identifier} artifact root")


def validate_artifact_manifest(data: dict[str, Any], harnesses: dict[str, Any]) -> None:
    targets = {target["id"]: set(target["capabilities"]) for target in harnesses["targets"]}
    artifacts = data.get("artifacts", [])
    if data.get("schema_version") != "ctxora.artifacts.v1" or data.get("artifact_count") != len(artifacts):
        raise ValueError("invalid artifact manifest header")
    known_ids = {str(item.get("id", "")) for item in artifacts}
    if len(known_ids) != len(artifacts):
        raise ValueError("duplicate artifact id")
    dependencies = {}
    for artifact in artifacts:
        identifier = str(artifact.get("id", ""))
        _identifier(identifier, "artifact id")
        kind = str(artifact.get("kind", ""))
        if artifact.get("capability") != kind:
            raise ValueError(f"artifact {identifier} capability does not match kind")
        _portable_path(str(artifact.get("source", "")), f"artifact {identifier} source")
        if not SHA256.fullmatch(str(artifact.get("content_hash", ""))):
            raise ValueError(f"artifact {identifier} has invalid content hash")
        provenance = artifact.get("provenance", {})
        if not all(provenance.get(key) for key in ("origin", "source", "license")):
            raise ValueError(f"artifact {identifier} has incomplete provenance")
        if provenance.get("origin") != "ctxora" and not (
            re.fullmatch(r"[0-9a-f]{40}", str(provenance.get("commit", "")))
            and SHA256.fullmatch(str(provenance.get("source_hash", "")))
        ):
            raise ValueError(f"derived artifact {identifier} requires commit and source hash")
        for target in artifact.get("targets", []):
            if target not in targets or kind not in targets[target]:
                raise ValueError(f"artifact {identifier} is incompatible with target {target}")
        dependencies[identifier] = tuple(artifact.get("dependencies", []))
        if any(dependency not in known_ids for dependency in dependencies[identifier]):
            raise ValueError(f"artifact {identifier} has an unknown dependency")
    visiting, visited = set(), set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise ValueError("artifact dependency cycle")
        if identifier in visited:
            return
        visiting.add(identifier)
        for dependency in dependencies[identifier]:
            visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in dependencies:
        visit(identifier)


def validate_definition(path: Path, kind: str, known_references: set[str]) -> None:
    values = _frontmatter(path)
    _portable_text(path.read_text("utf-8"), path.name)
    if not values.get("description") or not values.get("body"):
        raise ValueError(f"{path.name} requires description and body")
    if kind == "agents":
        _identifier(values.get("name", ""), "agent name")
        if values["name"] != path.stem or "model" in values or "tools" in values:
            raise ValueError(f"agent {path.name} is not host-neutral")
    references = set(REFERENCE.findall(values["body"]))
    unknown = references - known_references
    if unknown:
        raise ValueError(f"{path.name} has unknown references: {sorted(unknown)}")


def validate_repository_compliance(repository: str | Path) -> tuple[str, ...]:
    root = Path(repository).resolve()
    issues = list(canonical_artifact_drift(root))
    harnesses = json.loads((CANONICAL_ROOT.parent / "manifests" / "harnesses.json").read_text("utf-8"))
    artifacts = json.loads((CANONICAL_ROOT.parent / "manifests" / "artifacts.json").read_text("utf-8"))
    try:
        validate_harness_manifest(harnesses)
        validate_artifact_manifest(artifacts, harnesses)
        known = {item["id"] for item in artifacts["artifacts"]}
        for kind in ("agents", "commands"):
            for path in sorted((CANONICAL_ROOT / kind).glob("*.md")):
                validate_definition(path, kind, known)
    except (KeyError, TypeError, ValueError) as error:
        issues.append(str(error))
    return tuple(issues)


def export_artifact_schemas(directory: str | Path) -> tuple[Path, ...]:
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, schema in sorted(SCHEMAS.items()):
        path = destination / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", "utf-8")
        paths.append(path)
    return tuple(paths)
