from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from harness_context.adapters.clients import PROFILES
from harness_context.api.v2 import PrepareContextRequest
from harness_context.branding import CLI_NAME, PAID_PLAN_NAME, PAID_PLAN_STATUS
from harness_context.cli.exit_codes import error_report, exit_code_for
from harness_context.free_tools import (
    context_score,
    explain_context,
    instruction_document,
    repository_map,
    write_instruction,
)
from harness_context.installer import ClientInstaller
from harness_context.paths import workspace_data_dir, workspace_data_dirs, workspace_runtime_dir
from harness_context.runtime import HarnessRuntime


def _runtime(args) -> HarnessRuntime:
    if args.host and args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_external:
        raise SystemExit("external HTTP binding requires --allow-external")
    return HarnessRuntime.for_workspace(
        args.workspace, args.transport, args.host, args.port, args.watch,
        args.ecc, args.ecc_user_scope,
    )


def _print(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _pid_path(workspace: str) -> Path:
    return workspace_runtime_dir(workspace) / "run.pid"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=CLI_NAME)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in (
        "setup", "install", "profile", "run", "start", "index", "query", "explain",
        "context-score", "repo-map", "generate-agents-md",
        "generate-copilot-instructions", "generate-cursor-rules", "pro", "inspect",
        "status", "stop", "doctor", "repair", "register", "export", "uninstall", "ci",
    ):
        command = commands.add_parser(name)
        command.add_argument("--workspace", default=".")
        command.add_argument("--transport", choices=("stdio", "streamable-http"))
        command.add_argument("--host")
        command.add_argument("--port", type=int)
        command.add_argument("--allow-external", action="store_true")
        command.add_argument("--watch", action="store_true", default=None)
        command.add_argument("--ecc", action="store_true", default=None)
        command.add_argument("--ecc-user-scope", action="store_true", default=None)
        if name in {"query", "explain"}:
            command.add_argument("query")
            command.add_argument("--tokens", type=int, default=8_000)
        if name in {"generate-agents-md", "generate-copilot-instructions", "generate-cursor-rules"}:
            command.add_argument("--output")
            command.add_argument("--force", action="store_true")
        if name == "inspect":
            command.add_argument("target", choices=("workspace", "snapshot", "bundle", "ecc"), default="workspace", nargs="?")
        if name == "index":
            command.add_argument("--incremental", action="store_true")
        if name == "ci":
            command.add_argument("--base", default="origin/main")
            command.add_argument("--head", default="HEAD")
        if name == "export":
            command.add_argument("--output", required=True)
        if name in {"install", "uninstall"}:
            command.add_argument("--profile", choices=tuple(PROFILES))
            command.add_argument("--client-config")
            command.add_argument("--dry-run", action="store_true")
        if name == "uninstall":
            command.add_argument("--delete-data", action="store_true")
    return parser


def _main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.workspace).expanduser().resolve(strict=True)
    if args.command == "setup":
        config = workspace_data_dir(root) / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        if not config.exists():
            config.write_text('transport = "stdio"\nstartup_policy = "block_until_ready"\nwatch = false\necc_enabled = false\necc_allow_user_scope = false\n', "utf-8")
        _print({"status": "configured", "config": str(config)})
        return 0
    if args.command == "profile":
        _print({"profiles": [asdict(profile) | {"default_config": str(profile.default_config)} for profile in PROFILES.values()]})
        return 0
    if args.command == "pro":
        _print({
            "plan": PAID_PLAN_NAME,
            "status": PAID_PLAN_STATUS,
            "features": ["managed automation", "private workflows", "team context"],
        })
        return 0
    if args.command == "install":
        if not args.profile:
            raise SystemExit("install requires --profile")
        plan = ClientInstaller(root).install(args.profile, args.client_config, args.dry_run)
        _print({"status": "planned" if args.dry_run else "installed", "plan": plan.to_dict()})
        return 0
    if args.command == "register":
        runtime = _runtime(args)
        _print({"workspace_id": runtime.config.workspace_id, "root": str(root), "status": "registered"})
        return 0
    if args.command == "uninstall":
        if args.profile:
            plan = ClientInstaller(root).uninstall(args.profile, args.client_config, args.dry_run, args.delete_data)
            _print({"status": "planned" if args.dry_run else "uninstalled", "plan": plan.to_dict(), "data_deleted": args.delete_data})
            return 0
        if args.delete_data:
            for owned in workspace_data_dirs(root):
                shutil.rmtree(owned, ignore_errors=True)
        _print({"status": "uninstalled", "data_deleted": args.delete_data})
        return 0
    if args.command == "start":
        if args.host and args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_external:
            raise SystemExit("external HTTP binding requires --allow-external")
        pid_path = _pid_path(str(root))
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        log = (pid_path.parent / "runtime.log").open("a", encoding="utf-8")
        command = [
            sys.executable, "-m", "harness_context.cli.app", "run",
            "--workspace", str(root), "--transport", "streamable-http",
            "--host", args.host or "127.0.0.1", "--port", str(args.port or 8765),
            "--watch",
        ]
        if args.ecc:
            command.append("--ecc")
        if args.ecc_user_scope:
            command.append("--ecc-user-scope")
        process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
        pid_path.write_text(str(process.pid), "utf-8")
        _print({"status": "started", "pid": process.pid})
        return 0
    if args.command in {"status", "stop"}:
        pid_path = _pid_path(str(root))
        pid = int(pid_path.read_text("utf-8")) if pid_path.exists() else 0
        running = False
        if pid:
            try:
                os.kill(pid, 0)
                running = True
            except OSError:
                pass
        if args.command == "stop" and running:
            os.kill(pid, signal.SIGTERM)
            pid_path.unlink(missing_ok=True)
            running = False
        _print({"status": "running" if running else "stopped", "pid": pid or None})
        return 0
    runtime = _runtime(args)
    startup = runtime.startup()
    if args.command == "run":
        runtime.run()
        return 0
    if args.command == "index":
        _print(startup)
        return 0
    if args.command == "repair":
        repaired = runtime.container.refresh.execute(runtime.config.workspace_id)
        _print({"status": "repaired", "workspace": str(root), "runtime": repaired})
        return 0
    if args.command == "doctor":
        _print(runtime.health_report())
        return 0
    if args.command == "ci":
        changed = subprocess.run(
            ["git", "diff", "--name-only", args.base, args.head],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        paths = [str(root / path) for path in changed]
        result = runtime.container.refresh.execute(runtime.config.workspace_id, paths) if paths else startup
        _print({"status": "ok", "changed_files": changed, "refresh": result})
        return 0
    assert runtime.container is not None
    if args.command in {"query", "explain"}:
        request = PrepareContextRequest(runtime.config.workspace_id, args.query, args.tokens)
        package = runtime.container.context.prepare(request).to_dict()
        _print(package if args.command == "query" else explain_context(args.query, package, root))
        return 0
    snapshot = runtime.container.engine.export_snapshot(runtime.config.workspace_id)
    if args.command == "context-score":
        _print(context_score(snapshot, root))
        return 0
    if args.command == "repo-map":
        _print(repository_map(snapshot, root))
        return 0
    generators = {
        "generate-agents-md": (root / "AGENTS.md", "AGENTS.md"),
        "generate-copilot-instructions": (root / ".github" / "copilot-instructions.md", "GitHub Copilot"),
        "generate-cursor-rules": (root / ".cursor" / "rules" / "ctxora.mdc", "Cursor"),
    }
    if args.command in generators:
        default_output, target = generators[args.command]
        output = Path(args.output).expanduser().resolve() if args.output else default_output
        write_instruction(output, instruction_document(snapshot, root, target), args.force)
        _print({"status": "generated", "target": target, "output": str(output), "snapshot_id": snapshot["snapshot_id"]})
        return 0
    stats = runtime.container.engine.stats(runtime.config.workspace_id)
    if args.command == "export":
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(runtime.container.engine.export_snapshot(runtime.config.workspace_id), ensure_ascii=False, indent=2), "utf-8")
        _print({"status": "exported", "output": str(output), "snapshot_id": stats["snapshot_id"]})
        return 0
    if args.target == "bundle":
        _print(runtime.container.engine.prepare_bundle(runtime.config.workspace_id))
    elif args.target == "ecc":
        _print(runtime.container.ecc.status() if runtime.container.ecc else {"available": False, "enabled": False, "read_only": True})
    else:
        _print(stats)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except SystemExit:
        raise
    except Exception as error:  # noqa: BLE001 - CLI boundary maps all failures to stable exits.
        print(json.dumps(error_report(error), sort_keys=True), file=sys.stderr)
        return int(exit_code_for(error))


if __name__ == "__main__":
    raise SystemExit(main())
