from __future__ import annotations

import fnmatch
from pathlib import Path

from harness_context.schemas import HarnessError
from harness_context.security import contains_secret
from harness_context.workspace.policy import WorkspacePolicy

DEFAULT_DENY = (
    ".git", ".hg", ".svn", ".ctxora", ".harness", ".ecc", "node_modules", "vendor", ".venv", "venv",
    "dist", "build", "__pycache__", ".env", ".env.*", "*.pem", "*.key", "id_rsa", "id_ed25519",
    "*.sqlite", "*.sqlite3", "*.db", "*.egg-info",
)


class WorkspaceRegistry:
    def __init__(self) -> None:
        self._policies: dict[str, WorkspacePolicy] = {}

    def register(self, workspace_id: str, roots: list[str], **limits: int) -> WorkspacePolicy:
        if not workspace_id.strip():
            raise HarnessError("invalid_workspace", "workspace_id is required")
        canonical = tuple(sorted({str(Path(root).expanduser().resolve(strict=True)) for root in roots}))
        if not canonical:
            raise HarnessError("invalid_workspace", "at least one existing root is required")
        policy = WorkspacePolicy(roots=canonical, **limits)
        self._policies[workspace_id] = policy
        return policy

    def get(self, workspace_id: str) -> WorkspacePolicy:
        try:
            return self._policies[workspace_id]
        except KeyError as error:
            raise HarnessError("unknown_workspace", f"workspace not registered: {workspace_id}") from error

    def authorize(self, workspace_id: str, paths: list[str]) -> list[Path]:
        policy = self.get(workspace_id)
        authorized = []
        for raw in paths:
            unresolved = Path(raw).expanduser()
            if unresolved.is_symlink():
                raise HarnessError("symlink_path", f"symlink paths are not allowed: {unresolved.name}")
            path = unresolved.resolve(strict=False)
            if not any(path == Path(root) or Path(root) in path.parents for root in policy.roots):
                raise HarnessError("unauthorized_path", f"path is outside workspace roots: {path.name}")
            authorized.append(path)
        return authorized

    @staticmethod
    def _patterns(root: Path) -> list[str]:
        patterns = list(DEFAULT_DENY)
        for name in (".gitignore", ".ctxoraignore", ".harnessignore"):
            ignore = root / name
            if ignore.is_file():
                patterns.extend(line.strip().lstrip("/") for line in ignore.read_text("utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#") and not line.startswith("!"))
        return patterns

    def files(self, workspace_id: str, paths: list[str]) -> list[Path]:
        policy = self.get(workspace_id)
        selected, total = [], 0
        for source in self.authorize(workspace_id, paths):
            if not source.exists():
                continue
            base = source if source.is_dir() else source.parent
            patterns = self._patterns(base)
            candidates = [source] if source.is_file() else source.rglob("*")
            for path in candidates:
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(base).as_posix()
                if any(fnmatch.fnmatch(relative, pattern) or any(fnmatch.fnmatch(part, pattern) for part in path.parts) for pattern in patterns):
                    continue
                size = path.stat().st_size
                if size > policy.max_file_bytes:
                    continue
                content = path.read_bytes()
                if b"\x00" in content[:4096] or contains_secret(content):
                    continue
                total += size
                if total > policy.max_total_bytes or len(selected) >= policy.max_files:
                    raise HarnessError("workspace_limit", "workspace indexing limits exceeded")
                selected.append(path)
        return sorted(set(selected))
