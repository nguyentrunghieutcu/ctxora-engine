from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import webbrowser
from dataclasses import asdict
from pathlib import Path

from harness_context.adapters.clients import PROFILES
from harness_context.api.v2 import PrepareContextRequest
from harness_context.application.update_service import UpdateService
from harness_context.branding import CLI_NAME, PAID_PLAN_NAME, PAID_PLAN_STATUS
from harness_context.free_tools import (
    compact_context,
    compact_route,
    context_score,
    explain_context,
    instruction_document,
    repository_map,
    write_instruction,
)
from harness_context.installer import ClientInstaller
from harness_context.interfaces.cli.exit_codes import error_report, exit_code_for
from harness_context.interfaces.console import ConsoleServer
from harness_context.paths import workspace_data_dir, workspace_data_dirs, workspace_runtime_dir
from harness_context.runtime import HarnessRuntime
from harness_context.skills import SkillCatalog, SkillRouter
from harness_context.version import __version__
from harness_context.workspace.identity import workspace_identity

INSTRUCTION_TARGETS = {
    "codex": ("AGENTS.md", "AGENTS.md"),
    "claude-code": ("CLAUDE.md", "Claude Code"),
    "cursor": (".cursor/rules/ctxora.mdc", "Cursor"),
    "generic-mcp": ("AGENTS.md", "AGENTS.md"),
    "copilot": (".github/copilot-instructions.md", "GitHub Copilot"),
}


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
        "status", "stop", "doctor", "dashboard", "repair", "register", "export",
        "uninstall", "ci",
    ):
        command = commands.add_parser(name)
        command.add_argument("--workspace", default=".")
        if name == "dashboard":
            command.add_argument("--host", choices=("127.0.0.1", "localhost", "::1"))
            command.add_argument("--port", type=int)
            command.add_argument("--ecc", action="store_true", default=None)
            command.add_argument("--ecc-user-scope", action="store_true", default=None)
            command.add_argument("--open", action="store_true", dest="open_browser")
            command.set_defaults(transport=None, allow_external=False, watch=None)
        else:
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
        if name == "query":
            command.add_argument("--compact", action="store_true", help="Filter output to evidence.items (path + line + code) and omit diagnostics.skills")
        if name in {"generate-agents-md", "generate-copilot-instructions", "generate-cursor-rules"}:
            command.add_argument("--output")
            command.add_argument("--force", action="store_true")
        if name == "generate-agents-md":
            command.add_argument("--target", choices=tuple(INSTRUCTION_TARGETS), default="codex")
        if name == "install":
            command.add_argument("--generate-instructions", action="store_true")
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
    skill_command = commands.add_parser("skills")
    skill_command.add_argument("--workspace", default=".")
    skill_actions = skill_command.add_subparsers(dest="skills_action", required=True)
    profile_action = skill_actions.add_parser("profiles")
    profile_action.add_argument("--workspace", default=argparse.SUPPRESS)
    module_action = skill_actions.add_parser("modules")
    module_action.add_argument("--workspace", default=argparse.SUPPRESS)
    list_skills = skill_actions.add_parser("list")
    list_skills.add_argument("--workspace", default=argparse.SUPPRESS)
    list_skills.add_argument("--profile")
    list_skills.add_argument("--module")
    route_skills = skill_actions.add_parser("route")
    route_skills.add_argument("task")
    route_skills.add_argument("--workspace", default=argparse.SUPPRESS)
    route_skills.add_argument("--profile", default="")
    route_skills.add_argument("--top-k", type=int, default=5)
    route_skills.add_argument("--token-budget", type=int, default=6_000)
    route_skills.add_argument("--no-instructions", action="store_true")
    route_skills.add_argument("--compact", action="store_true", help="Compact output format for minimal token consumption")
    feedback = skill_actions.add_parser("feedback")
    feedback.add_argument("route_id")
    feedback.add_argument("--workspace", default=argparse.SUPPRESS)
    feedback.add_argument("--outcome", choices=("success", "failure", "rejected", "corrected"), required=True)
    feedback.add_argument("--skill", action="append", default=[])
    feedback.add_argument("--correction-skill", default="")
    learning = skill_actions.add_parser("learning")
    learning.add_argument("--workspace", default=argparse.SUPPRESS)
    learning.add_argument("--limit", type=int, default=20)
    for action in ("preview", "install"):
        action_parser = skill_actions.add_parser(action)
        action_parser.add_argument("--workspace", default=argparse.SUPPRESS)
        action_parser.add_argument("--profile", default="developer")
        action_parser.add_argument("--add-module", action="append", default=[])
        action_parser.add_argument("--remove-module", action="append", default=[])
        action_parser.add_argument("--add-skill", action="append", default=[])
        action_parser.add_argument("--remove-skill", action="append", default=[])
        action_parser.add_argument("--output", default="")
        action_parser.add_argument("--delivery", choices=("shared", "materialized"), default="shared")
        action_parser.add_argument(
            "--target",
            action="append",
            choices=("codex", "claude", "cursor", "gemini", "opencode", "all"),
            default=[],
        )
        action_parser.add_argument("--force", action="store_true")
        action_parser.add_argument("--prune", action="store_true")
        if action == "install":
            action_parser.add_argument("--dry-run", action="store_true")
    update_command = commands.add_parser("update")
    update_actions = update_command.add_subparsers(dest="update_action", required=True)
    update_check = update_actions.add_parser("check")
    update_check.add_argument("--workspace", default=".")
    update_check.add_argument("--force", action="store_true")
    update_plan = update_actions.add_parser("plan")
    update_plan.add_argument("--workspace", default=".")
    update_apply = update_actions.add_parser("apply")
    update_apply.add_argument("plan_digest")
    update_apply.add_argument("--workspace", default=".")
    update_apply.add_argument("--yes", action="store_true", dest="confirmed")
    return parser


def _main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.workspace).expanduser().resolve(strict=True)
    if args.command == "update":
        updates = UpdateService(root, __version__)
        if args.update_action == "check":
            _print(updates.check(force=args.force).to_dict())
        elif args.update_action == "plan":
            _print(updates.plan().to_dict())
        else:
            _print(updates.apply(args.plan_digest, confirmed=args.confirmed).to_dict())
        return 0
    if args.command == "skills":
        catalog = SkillCatalog()
        if args.skills_action in {"route", "feedback", "learning"}:
            router = SkillRouter(root, workspace_identity(root), catalog)
            workspace_id = workspace_identity(root)
            if args.skills_action == "route":
                is_compact = getattr(args, "compact", False)
                top_k = 2 if is_compact and args.top_k == 5 else args.top_k
                include_instructions = False if is_compact else not args.no_instructions
                routed = router.route(
                    workspace_id,
                    args.task,
                    args.profile,
                    top_k,
                    include_instructions,
                    args.token_budget,
                )
                _print(compact_route(routed) if is_compact else routed)
            elif args.skills_action == "feedback":
                _print(router.feedback(
                    workspace_id,
                    args.route_id,
                    args.outcome,
                    args.skill,
                    args.correction_skill,
                ))
            else:
                _print(router.learning_status(workspace_id, args.limit))
            return 0
        if args.skills_action == "modules":
            _print({"modules": catalog.modules})
            return 0
        if args.skills_action == "profiles":
            profiles = []
            for name, profile in catalog.profiles.items():
                selection = catalog.select(name)
                profiles.append({
                    "name": name,
                    "description": profile["description"],
                    "modules": list(selection.modules),
                    "skill_count": len(selection.skills),
                })
            _print({"catalog_commit": catalog.commit, "skill_count": len(catalog.skills), "profiles": profiles})
            return 0
        if args.skills_action == "list":
            if args.profile and args.module:
                raise ValueError("use either --profile or --module, not both")
            if args.profile:
                selection = catalog.select(args.profile)
                _print(selection.to_dict())
            elif args.module:
                if args.module not in catalog.modules:
                    raise ValueError(f"unknown skills module: {args.module}")
                _print({"module": args.module, **catalog.modules[args.module]})
            else:
                _print({"skill_count": len(catalog.skills), "skills": sorted(catalog.skills)})
            return 0
        selection = catalog.select(
            args.profile,
            tuple(args.add_module),
            tuple(args.remove_module),
            tuple(args.add_skill),
            tuple(args.remove_skill),
        )
        dry_run = args.skills_action == "preview" or args.dry_run
        if args.output and args.delivery != "materialized":
            raise ValueError("--output requires --delivery materialized")
        installs = []
        conflicts = []
        plans = []
        for target, output in catalog.install_outputs(tuple(args.target), args.output):
            plan = catalog.plan_install(
                root, output, selection, force=args.force, prune=args.prune, target=target,
                delivery=args.delivery,
            )
            plans.append(plan)
            installed = catalog._legacy_plan_result(plan, len(selection.skills))
            installed["target"] = target
            installs.append(installed)
            conflicts.extend(f"{target}:{skill}" for skill in installed["conflicts"])
        if not dry_run and not conflicts:
            catalog.apply_install_plans(root, tuple(plans), selection)
        result = {
            "status": "conflict" if conflicts else ("planned" if dry_run else "installed"),
            "selection": selection.to_dict(),
            "delivery": args.delivery,
            "catalog_source": str(catalog.source_root),
            "requires_mcp": args.delivery == "shared",
            "activation": "Use prepare_context for recommendations; route_skills returns instructions on demand.",
            "installs": installs,
            "conflicts": conflicts,
        }
        if not dry_run and not conflicts:
            result["profile_config"] = str(root / ".ctxora" / "skills-profile.json")
        _print(result)
        return 2 if conflicts else 0
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
        instruction = None
        if args.generate_instructions:
            relative, target = INSTRUCTION_TARGETS[args.profile]
            output = root / relative
            if output.exists():
                raise FileExistsError(f"refusing to overwrite existing instructions: {output}")
            instruction = {"target": target, "output": str(output)}
            if not args.dry_run:
                runtime = _runtime(args)
                runtime.startup()
                snapshot = runtime.container.engine.export_snapshot(runtime.config.workspace_id)
                content = instruction_document(snapshot, root, target)
        plan = ClientInstaller(root).install(args.profile, args.client_config, args.dry_run)
        if instruction and not args.dry_run:
            write_instruction(output, content)
        result = {"status": "planned" if args.dry_run else "installed", "plan": plan.to_dict()}
        if instruction:
            result["instructions"] = instruction
        _print(result)
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
    if args.command == "dashboard":
        console = ConsoleServer(runtime, args.host or "127.0.0.1", args.port or 0)
        info = console.start()
        _print(info)
        if args.open_browser:
            webbrowser.open(str(info["url"]))
        try:
            console.wait()
        finally:
            console.shutdown()
        return 0
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
        if args.command == "explain":
            _print(explain_context(args.query, package, root))
        elif getattr(args, "compact", False):
            _print(compact_context(package, root))
        else:
            _print(package)
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
        if args.command == "generate-agents-md":
            relative, target = INSTRUCTION_TARGETS[args.target]
            default_output = root / relative
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
    except KeyboardInterrupt:
        return 130
    except Exception as error:  # noqa: BLE001 - CLI boundary maps all failures to stable exits.
        print(json.dumps(error_report(error), sort_keys=True), file=sys.stderr)
        return int(exit_code_for(error))


if __name__ == "__main__":
    raise SystemExit(main())
