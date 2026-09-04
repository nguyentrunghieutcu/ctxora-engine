from __future__ import annotations

import json
import re
from pathlib import Path

from harness_context.adapters.ecc.detection import EccInstallation
from harness_context.adapters.ecc.mapping import map_ecc_memory
from harness_context.tokenize import tokens

_FIELDS = {
    "schema": "schema", "id": "id", "title": "title", "kind": "kind",
    "scope": "scope", "trust": "trust", "status": "status",
    "source_harness": "sourceHarness", "target_harnesses": "targetHarnesses",
    "tags": "tags", "links": "links", "created_at": "createdAt",
    "updated_at": "updatedAt",
}
_KINDS = {"context", "decision", "fact", "handoff", "lesson", "note", "preference", "runbook"}
_SCOPES = {"project", "team", "user"}
_STATUSES = {"active", "rejected", "superseded"}
_ID = re.compile(r"^mem_[a-z0-9][a-z0-9_-]{2,127}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
_SECRETS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b", re.IGNORECASE),
    re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pors]_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)


def _has_unsafe_characters(value: str, allow_whitespace: bool = False) -> bool:
    for character in value:
        code = ord(character)
        if allow_whitespace and character in "\t\n\r":
            continue
        if code <= 0x1F or 0x7F <= code <= 0x9F or 0x202A <= code <= 0x202E or 0x2066 <= code <= 0x2069:
            return True
    return False


class EccMemoryReader:
    """Bounded, read-only reader for ECC's ecc.memory.v1 Markdown vault."""

    def __init__(self, installation: EccInstallation, target_harness: str = "ctxora"):
        self.installation = installation
        self.target_harness = target_harness
        self.target_harnesses = {target_harness, "harness-context"}

    def status(self) -> dict:
        roots = [root for root in (self.installation.project_memory_root, self.installation.user_memory_root) if root]
        return {
            "available": self.installation.available,
            "read_only": True,
            "project_memory_root": str(self.installation.project_memory_root) if self.installation.project_memory_root else None,
            "user_memory_root": str(self.installation.user_memory_root) if self.installation.user_memory_root else None,
            "roots": len(roots),
        }

    @staticmethod
    def _parse(path: Path) -> dict:
        if path.is_symlink() or path.stat().st_size > 128 * 1024:
            raise ValueError("ECC memory file is unsafe or oversized")
        source = path.read_text("utf-8")
        if not source.startswith("---\n"):
            raise ValueError("ECC memory document must start with frontmatter")
        frontmatter, separator, body = source[4:].partition("\n---\n")
        if not separator:
            raise ValueError("ECC memory document has no closing frontmatter")
        parsed = {}
        for line in frontmatter.splitlines():
            key, marker, value = line.partition(":")
            if not marker or key not in _FIELDS or _FIELDS[key] in parsed:
                raise ValueError("invalid ECC memory frontmatter")
            parsed[_FIELDS[key]] = json.loads(value.strip())
        required = set(_FIELDS.values())
        if set(parsed) != required:
            raise ValueError("incomplete ECC memory frontmatter")
        parsed["body"] = body.strip()
        if parsed["schema"] != "ecc.memory.v1" or not _ID.fullmatch(parsed["id"]):
            raise ValueError("unsupported ECC memory schema or id")
        if not isinstance(parsed["title"], str) or not parsed["title"].strip() or len(parsed["title"]) > 200:
            raise ValueError("invalid ECC memory title")
        if _has_unsafe_characters(parsed["title"]):
            raise ValueError("unsafe ECC memory title")
        if parsed["kind"] not in _KINDS or parsed["scope"] not in _SCOPES:
            raise ValueError("unsupported ECC memory kind or scope")
        if parsed["trust"] != "unreviewed" or parsed["status"] not in _STATUSES:
            raise ValueError("unsupported ECC memory trust or status")
        if not _SLUG.fullmatch(parsed["sourceHarness"]):
            raise ValueError("invalid ECC source harness")
        if not _TIMESTAMP.fullmatch(parsed["createdAt"]) or not _TIMESTAMP.fullmatch(parsed["updatedAt"]):
            raise ValueError("invalid ECC timestamp")
        if not parsed["body"] or len(parsed["body"].encode("utf-8")) > 64 * 1024:
            raise ValueError("invalid ECC memory body")
        if _has_unsafe_characters(parsed["body"], allow_whitespace=True):
            raise ValueError("unsafe ECC memory body")
        if any(pattern.search(parsed["body"]) for pattern in _SECRETS):
            raise ValueError("ECC memory contains a secret-like value")
        for field in ("targetHarnesses", "tags"):
            if not isinstance(parsed[field], list) or not all(isinstance(value, str) and _SLUG.fullmatch(value) for value in parsed[field]):
                raise ValueError(f"invalid ECC {field}")
            if len(parsed[field]) != len(set(parsed[field])):
                raise ValueError(f"duplicate ECC {field}")
        if not parsed["targetHarnesses"] or len(parsed["targetHarnesses"]) > 32 or len(parsed["tags"]) > 32:
            raise ValueError("invalid ECC target or tag count")
        if not isinstance(parsed["links"], list) or not all(_ID.fullmatch(value) for value in parsed["links"]):
            raise ValueError("invalid ECC links")
        if len(parsed["links"]) > 64:
            raise ValueError("too many ECC links")
        if len(parsed["links"]) != len(set(parsed["links"])):
            raise ValueError("duplicate ECC links")
        return parsed

    def read(self) -> tuple[list[dict], list[dict]]:
        entries, diagnostics = [], []
        roots = [root for root in (self.installation.project_memory_root, self.installation.user_memory_root) if root]
        for root in roots:
            for path in sorted(root.rglob("*.md"))[:1_000]:
                try:
                    memory = self._parse(path)
                    is_user_root = root == self.installation.user_memory_root
                    allowed_scopes = {"user"} if is_user_root else {"project", "team"}
                    if memory["scope"] not in allowed_scopes:
                        raise ValueError("ECC memory scope does not match its vault location")
                    if memory["status"] != "active":
                        continue
                    if not self.target_harnesses.intersection(memory["targetHarnesses"]) and "all" not in memory["targetHarnesses"]:
                        continue
                    entries.append(map_ecc_memory(memory, path))
                except (OSError, UnicodeError, ValueError) as error:
                    diagnostics.append({"path": str(path), "error": str(error)})
        counts = {}
        for entry in entries:
            counts[entry["key"]] = counts.get(entry["key"], 0) + 1
        duplicates = {key for key, count in counts.items() if count > 1}
        if duplicates:
            entries = [entry for entry in entries if entry["key"] not in duplicates]
            diagnostics.extend({"memory_id": key, "error": "duplicate ECC memory id"} for key in sorted(duplicates))
        return entries, diagnostics[:100]

    def search(self, query: str, limit: int = 4) -> dict:
        entries, diagnostics = self.read()
        query_tokens = set(tokens(query))
        ranked = []
        for entry in entries:
            document = set(tokens(f"{entry['title']} {entry['tags']} {entry['value']}"))
            score = len(query_tokens & document) / max(len(query_tokens), 1)
            if not query_tokens or score > 0:
                ranked.append((score, entry))
        ranked.sort(key=lambda item: (-item[0], item[1]["key"]))
        return {
            "entries": [{**entry, "score": score} for score, entry in ranked[:max(0, limit)]],
            "diagnostics": diagnostics,
            "read_only": True,
        }
