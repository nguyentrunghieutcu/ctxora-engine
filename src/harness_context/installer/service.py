from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from harness_context.adapters.clients import ClientProfile, get_profile
from harness_context.branding import CLI_NAME
from harness_context.installer.models import Mutation, MutationPlan
from harness_context.paths import workspace_data_dirs, workspace_installer_dir


class ClientInstaller:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).expanduser().resolve()
        self.ownership_path = workspace_installer_dir(self.workspace) / "ownership.json"

    def plan(self, profile_name: str, config_path: str | Path | None = None, uninstall: bool = False) -> MutationPlan:
        profile = get_profile(profile_name)
        path = self._config_path(profile, config_path)
        current = self._read(profile, path)
        before = self._owned_value(profile, current)
        manifest = self._load_manifest().get(profile.name, {})
        after = manifest.get("previous") if uninstall else self._server_config()
        if uninstall and manifest and before != manifest.get("installed"):
            return MutationPlan(profile.name, str(path), (Mutation("conflict", self._mutation_path(profile), before, after),))
        operation = "remove" if uninstall and after is None else ("restore" if uninstall else ("replace" if before is not None else "add"))
        mutations = () if before == after else (Mutation(operation, self._mutation_path(profile), before, after),)
        return MutationPlan(profile.name, str(path), mutations)

    def install(self, profile_name: str, config_path: str | Path | None = None, dry_run: bool = False) -> MutationPlan:
        profile = get_profile(profile_name)
        path = self._config_path(profile, config_path)
        plan = self.plan(profile_name, path)
        if dry_run or not plan.mutations:
            return plan
        current = self._read(profile, path)
        updated = self._set_owned(profile, current, self._server_config())
        self._backup(path)
        self._write(profile, path, updated)
        manifest = self._load_manifest()
        manifest[profile.name] = {
            "config_path": str(path),
            "server_key": profile.server_key,
            "previous": self._owned_value(profile, current),
            "installed": self._owned_value(profile, updated),
        }
        self._write_json(self.ownership_path, manifest)
        return plan

    def uninstall(self, profile_name: str, config_path: str | Path | None = None, dry_run: bool = False, delete_data: bool = False) -> MutationPlan:
        profile = get_profile(profile_name)
        manifest = self._load_manifest()
        owned = manifest.get(profile.name, {})
        path = self._config_path(profile, config_path or owned.get("config_path"))
        plan = self.plan(profile_name, path, uninstall=True)
        conflict = any(mutation.operation == "conflict" for mutation in plan.mutations)
        if not dry_run and plan.mutations and not conflict:
            current = self._read(profile, path)
            self._backup(path)
            self._write(profile, path, self._set_owned(profile, current, owned.get("previous")))
        if not dry_run and not conflict:
            manifest.pop(profile.name, None)
            if manifest:
                self._write_json(self.ownership_path, manifest)
            else:
                self.ownership_path.unlink(missing_ok=True)
            if delete_data:
                for data_dir in workspace_data_dirs(self.workspace):
                    shutil.rmtree(data_dir, ignore_errors=True)
        return plan

    def _server_config(self) -> dict[str, Any]:
        command = os.environ.get("CTXORA_MCP_COMMAND", CLI_NAME)
        prefix = json.loads(os.environ.get("CTXORA_MCP_ARGS_PREFIX", "[]"))
        if not isinstance(prefix, list) or not all(isinstance(item, str) for item in prefix):
            raise ValueError("CTXORA_MCP_ARGS_PREFIX must be a JSON array of strings")
        return {
            "command": command,
            "args": [*prefix, "run", "--workspace", str(self.workspace), "--transport", "stdio"],
            "env": {"CTXORA_ALLOWED_ROOTS": str(self.workspace), "PYTHONUTF8": "1"},
        }

    @staticmethod
    def _mutation_path(profile: ClientProfile) -> str:
        return f"mcp_servers.{profile.server_key}" if profile.config_format == "toml" else f"mcpServers.{profile.server_key}"

    @staticmethod
    def _config_path(profile: ClientProfile, config_path: str | Path | None) -> Path:
        return Path(config_path or profile.default_config).expanduser().resolve()

    @staticmethod
    def _read(profile: ClientProfile, path: Path) -> Any:
        if not path.exists():
            return "" if profile.config_format == "toml" else {}
        text = path.read_text("utf-8")
        return text if profile.config_format == "toml" else json.loads(text or "{}")

    @staticmethod
    def _owned_value(profile: ClientProfile, current: Any) -> Any:
        if profile.config_format == "json":
            return current.get("mcpServers", {}).get(profile.server_key)
        match = re.search(ClientInstaller._toml_pattern(profile), current)
        return match.group(0).rstrip() if match else None

    def _set_owned(self, profile: ClientProfile, current: Any, value: Any) -> Any:
        if profile.config_format == "json":
            updated = json.loads(json.dumps(current))
            servers = updated.setdefault("mcpServers", {})
            if value is None:
                servers.pop(profile.server_key, None)
                if not servers:
                    updated.pop("mcpServers", None)
            else:
                servers[profile.server_key] = value
            return updated
        pattern = self._toml_pattern(profile)
        cleaned = re.sub(pattern, "", current).rstrip()
        if value is None:
            return cleaned + ("\n" if cleaned else "")
        if isinstance(value, str):
            return (cleaned + "\n\n" if cleaned else "") + value.rstrip() + "\n"
        block = [f"[mcp_servers.{profile.server_key}]", f'command = {json.dumps(value["command"])}', f'args = {json.dumps(value["args"])}', ""]
        block.append(f"[mcp_servers.{profile.server_key}.env]")
        block.extend(f"{key} = {json.dumps(item)}" for key, item in sorted(value["env"].items()))
        return (cleaned + "\n\n" if cleaned else "") + "\n".join(block) + "\n"

    @staticmethod
    def _toml_pattern(profile: ClientProfile) -> str:
        key = re.escape(profile.server_key)
        return rf"(?ms)^\[mcp_servers\.{key}\]\n.*?(?=^\[(?!mcp_servers\.{key}(?:\.|\]))|\Z)"

    def _load_manifest(self) -> dict[str, Any]:
        if not self.ownership_path.exists():
            return {}
        return json.loads(self.ownership_path.read_text("utf-8"))

    @staticmethod
    def _backup(path: Path) -> None:
        if not path.exists():
            return
        backup = path.with_suffix(path.suffix + ".ctxora.bak")
        backup.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=backup.parent, delete=False) as handle:
            handle.write(path.read_bytes())
            temporary = Path(handle.name)
        os.replace(temporary, backup)

    @staticmethod
    def _write(profile: ClientProfile, path: Path, value: Any) -> None:
        text = value if profile.config_format == "toml" else json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ClientInstaller._write_text(path, text)

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        ClientInstaller._write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(text)
            temporary = Path(handle.name)
        os.replace(temporary, path)
