from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness_context.adapters.ecc import EccMemoryReader, detect_ecc
from harness_context.api.v2 import PrepareContextRequest
from harness_context.bootstrap import build_container


def memory_document(
    memory_id: str = "mem_auth_decision",
    *,
    status: str = "active",
    targets: list[str] | None = None,
    body: str = "Rotate refresh tokens after every successful exchange.",
) -> str:
    fields = {
        "schema": "ecc.memory.v1", "id": memory_id,
        "title": "Authentication decision", "kind": "decision",
        "scope": "project", "trust": "unreviewed", "status": status,
        "source_harness": "claude-code",
        "target_harnesses": targets or ["all"], "tags": ["auth", "security"],
        "links": [], "created_at": "2026-09-01T10:00:00.000Z",
        "updated_at": "2026-09-03T10:00:00.000Z",
    }
    frontmatter = "\n".join(f"{key}: {json.dumps(value)}" for key, value in fields.items())
    return f"---\n{frontmatter}\n---\n{body}\n"


class EccAdapterTests(unittest.TestCase):
    def test_detects_project_vault_without_enabling_user_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / ".ecc" / "memory"
            vault.mkdir(parents=True)
            installation = detect_ecc(root, allow_user_scope=False, environment={})
            self.assertEqual(installation.project_memory_root, vault.resolve())
            self.assertIsNone(installation.user_memory_root)

    def test_user_vault_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            user = Path(directory) / "user-memory"
            root.mkdir()
            user.mkdir()
            environment = {"ECC_MEMORY_USER_ROOT": str(user)}
            disabled = detect_ecc(root, allow_user_scope=False, environment=environment)
            enabled = detect_ecc(root, allow_user_scope=True, environment=environment)
            self.assertIsNone(disabled.user_memory_root)
            self.assertEqual(enabled.user_memory_root, user.resolve())

    def test_reads_active_targeted_memory_without_modifying_ecc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / ".ecc" / "memory"
            vault.mkdir(parents=True)
            source = vault / "auth.md"
            content = memory_document(targets=["ctxora"])
            source.write_text(content, encoding="utf-8")
            reader = EccMemoryReader(detect_ecc(root, environment={}))
            result = reader.search("refresh token")
            self.assertEqual(result["entries"][0]["key"], "mem_auth_decision")
            self.assertTrue(result["entries"][0]["provenance"]["read_only"])
            self.assertEqual(source.read_text("utf-8"), content)

    def test_reads_legacy_harness_target_during_rebrand(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / ".ecc" / "memory"
            vault.mkdir(parents=True)
            (vault / "legacy.md").write_text(memory_document(targets=["harness-context"]), "utf-8")
            result = EccMemoryReader(detect_ecc(root, environment={})).search("refresh token")
            self.assertEqual(result["entries"][0]["key"], "mem_auth_decision")

    def test_filters_rejected_wrong_target_and_secret_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / ".ecc" / "memory"
            vault.mkdir(parents=True)
            (vault / "rejected.md").write_text(memory_document("mem_rejected", status="rejected"), "utf-8")
            (vault / "other.md").write_text(memory_document("mem_other_target", targets=["cursor"]), "utf-8")
            (vault / "secret.md").write_text(memory_document("mem_secret_note", body="token sk-abcdefghijklmnopqrstuvwxyz"), "utf-8")
            result = EccMemoryReader(detect_ecc(root, environment={})).search("")
            self.assertEqual(result["entries"], [])
            self.assertEqual(len(result["diagnostics"]), 1)

    def test_context_package_includes_ecc_only_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Project\nAuthentication", "utf-8")
            vault = root / ".ecc" / "memory"
            vault.mkdir(parents=True)
            (vault / "auth.md").write_text(memory_document(), "utf-8")
            container = build_container(root, ecc_enabled=True)
            workspace_id = next(iter(container.engine.states))
            container.refresh.execute(workspace_id)
            package = container.context.prepare(PrepareContextRequest(
                workspace_id, "refresh token", 2_000, include_ecc=True,
            ))
            self.assertEqual(package.external_context[0]["key"], "mem_auth_decision")
            indexed_paths = {item.path for item in container.engine.states[workspace_id].items}
            self.assertNotIn(str((vault / "auth.md").resolve()), indexed_paths)
