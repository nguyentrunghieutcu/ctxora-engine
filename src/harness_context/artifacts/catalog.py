from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from harness_context.domain.harnesses import REGISTRY

ARTIFACT_KINDS = ("agents", "commands", "skills")
CANONICAL_ROOT = Path(__file__).with_name("canonical")
MANIFEST_PATH = Path(__file__).with_name("manifests") / "artifacts.json"


def _files(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_hash(path: Path) -> str:
    digest = hashlib.sha256()
    files = _files(path) if path.is_dir() else {path.name: path}
    for relative, file_path in files.items():
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _artifact_paths(kind: str) -> tuple[Path, ...]:
    root = CANONICAL_ROOT / kind
    if kind == "skills":
        return tuple(sorted(path for path in root.iterdir() if (path / "SKILL.md").is_file()))
    return tuple(sorted(root.glob("*.md")))


def build_artifact_manifest() -> dict[str, Any]:
    artifacts = []
    for kind in ARTIFACT_KINDS:
        targets = [target.id for target in REGISTRY.targets(kind)]
        for path in _artifact_paths(kind):
            artifact_id = path.name if path.is_dir() else path.stem
            artifact_root = path if path.is_dir() else path.parent
            artifact_files = _files(path) if path.is_dir() else {path.name: path}
            artifacts.append(
                {
                    "id": artifact_id,
                    "kind": kind,
                    "source": path.relative_to(CANONICAL_ROOT).as_posix(),
                    "capability": kind,
                    "targets": targets,
                    "dependencies": [],
                    "content_hash": _artifact_hash(path),
                    "files": [
                        {
                            "path": file_path.relative_to(artifact_root).as_posix(),
                            "sha256": _sha256(file_path),
                        }
                        for file_path in artifact_files.values()
                    ],
                    "provenance": {
                        "origin": "ctxora",
                        "source": "ctxora-engine",
                        "license": "MIT",
                    },
                }
            )
    return {
        "schema_version": "ctxora.artifacts.v1",
        "canonical_root": "src/harness_context/artifacts/canonical",
        "projections": {kind: kind for kind in ARTIFACT_KINDS},
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def canonical_artifact_drift(repository: str | Path) -> tuple[str, ...]:
    root = Path(repository).resolve()
    issues = []
    expected_manifest = build_artifact_manifest()
    if not MANIFEST_PATH.is_file():
        issues.append("missing canonical artifact manifest")
    else:
        actual_manifest = json.loads(MANIFEST_PATH.read_text("utf-8"))
        if actual_manifest != expected_manifest:
            issues.append("canonical artifact manifest is stale")
    for kind in ARTIFACT_KINDS:
        canonical = _files(CANONICAL_ROOT / kind)
        projection = _files(root / kind)
        for relative in sorted(canonical.keys() - projection.keys()):
            issues.append(f"missing {kind} projection: {relative}")
        for relative in sorted(projection.keys() - canonical.keys()):
            issues.append(f"unexpected {kind} projection: {relative}")
        for relative in sorted(canonical.keys() & projection.keys()):
            if _sha256(canonical[relative]) != _sha256(projection[relative]):
                issues.append(f"out-of-sync {kind} projection: {relative}")
    return tuple(issues)


def sync_canonical_artifacts(repository: str | Path) -> None:
    root = Path(repository).resolve()
    if not (root / "pyproject.toml").is_file() or not (root / "package.json").is_file():
        raise ValueError("repository must contain pyproject.toml and package.json")
    for kind in ARTIFACT_KINDS:
        source_root = CANONICAL_ROOT / kind
        destination_root = root / kind
        if source_root.is_symlink() or destination_root.is_symlink():
            raise ValueError(f"artifact roots must not be symlinks: {kind}")
        source_files = _files(source_root)
        destination_files = _files(destination_root)
        for relative in sorted(destination_files.keys() - source_files.keys()):
            destination_files[relative].unlink()
        for relative, source in source_files.items():
            destination = destination_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        for directory in sorted(destination_root.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
    payload = json.dumps(build_artifact_manifest(), ensure_ascii=False, indent=2) + "\n"
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(".tmp")
    temporary.write_text(payload, "utf-8")
    temporary.replace(MANIFEST_PATH)
