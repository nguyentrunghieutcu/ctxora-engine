from __future__ import annotations

import ast
import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

REQUIRED_PATHS = (
    "CHANGELOG.md", "SUPPORT.md", "docs/ARCHITECTURE.md", "docs/OPERATIONS.md",
    "docs/PRICING.md",
    "examples/basic_usage.py", "examples/mcp-config.json", "migrations/manifest.json",
    "migrations/README.md", "schemas/README.md", "scripts/install.sh",
    "scripts/migrate_state.py", "scripts/uninstall.sh", "src/harness_context/server.py",
)
LEGACY_IMPLEMENTATION_DIRS = ("harness_context", "chunking", "compact", "context", "memory", "retrieval", "evaluation")
PAID_DEPENDENCIES = {
    "stripe", "launchdarkly", "ctxora_cloud", "ctxora_control_plane",
    "harness_cloud", "harness_control_plane",
}


def audit(root: Path) -> list[str]:
    failures: list[str] = []
    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            failures.append(f"missing required artifact: {relative}")
    for directory in LEGACY_IMPLEMENTATION_DIRS:
        if (root / directory).is_dir():
            failures.append(f"legacy production package remains at repository root: {directory}/")
    config = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))
    package_dir = config.get("tool", {}).get("setuptools", {}).get("package-dir", {})
    if package_dir.get("") != "src":
        failures.append("setuptools package-dir must map the package root to src")
    dependencies = {item.split("[", 1)[0].split("<", 1)[0].split(">", 1)[0].split("=", 1)[0].strip().lower() for item in config["project"].get("dependencies", [])}
    for dependency in sorted(dependencies & PAID_DEPENDENCIES):
        failures.append(f"paid control-plane dependency is forbidden: {dependency}")
    for source in sorted((root / "src").rglob("*.py")):
        tree = ast.parse(source.read_text("utf-8"), filename=str(source))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        for dependency in sorted(imported & PAID_DEPENDENCIES):
            failures.append(f"paid control-plane import in {source.relative_to(root)}: {dependency}")
    shim = (root / "server.py").read_text("utf-8")
    if shim.count("\n") > 20 or "harness_context import server" not in shim:
        failures.append("server.py must remain a tiny compatibility shim")
    return failures


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    failures = audit(root)
    print(json.dumps({"status": "failed" if failures else "ok", "failures": failures}, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
