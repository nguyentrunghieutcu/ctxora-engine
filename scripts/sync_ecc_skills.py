#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

SKILL_PATH = re.compile(r"^skills/([^/]+)$")


def skill_metadata(path: Path) -> dict[str, str]:
    text = (path / "SKILL.md").read_text("utf-8")
    frontmatter = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""

    def field(name: str, fallback: str = "") -> str:
        match = re.search(rf"^{name}:\s*(.+)$", frontmatter, re.MULTILINE)
        return match.group(1).strip().strip('"\'') if match else fallback

    section = re.search(
        r"(?ims)^##\s+(?:when to use|when to activate|triggers?)\s*$\n(.*?)(?=^##\s|\Z)",
        text,
    )
    routing_text = " ".join(filter(None, [
        path.name.replace("-", " "),
        field("name", path.name).replace("-", " "),
        field("description"),
        section.group(1)[:3_000] if section else "",
    ]))
    return {
        "path": f"ecc/{path.name}",
        "name": field("name", path.name),
        "description": field("description"),
        "routing_text": routing_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync the pinned ECC skill catalog into CTXORA.")
    parser.add_argument("source", type=Path, help="Path to an ECC checkout or extracted archive")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--synced-at", required=True)
    parser.add_argument("--destination", type=Path, default=Path("src/harness_context/skills/ecc"))
    parser.add_argument("--expected-count", type=int, default=286)
    args = parser.parse_args()

    source = args.source.resolve(strict=True)
    skills_root = source / "skills"
    modules_data = json.loads((source / "manifests" / "install-modules.json").read_text("utf-8"))
    profiles_data = json.loads((source / "manifests" / "install-profiles.json").read_text("utf-8"))
    skill_names = sorted(path.name for path in skills_root.iterdir() if (path / "SKILL.md").is_file())
    if len(skill_names) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} ECC skills, found {len(skill_names)}")
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        raise ValueError("commit must be the full pinned Git SHA")
    if any(path.is_symlink() for path in skills_root.rglob("*")):
        raise ValueError("ECC source must not contain symlinks")

    modules: dict[str, dict] = {}
    covered: set[str] = set()
    for module in modules_data["modules"]:
        names = []
        for raw_path in module.get("paths", []):
            match = SKILL_PATH.fullmatch(raw_path)
            if match and match.group(1) in skill_names:
                names.append(match.group(1))
        if names:
            modules[module["id"]] = {
                "description": module["description"],
                "skills": sorted(set(names)),
            }
            covered.update(names)
    missing = sorted(set(skill_names) - covered)
    if missing:
        modules["uncategorized"] = {
            "description": "ECC skills not assigned to an install module in the pinned manifest.",
            "skills": missing,
        }

    profiles = {}
    for profile_id, profile in profiles_data["profiles"].items():
        selected_modules = [module for module in profile["modules"] if module in modules]
        if profile_id == "full" and "uncategorized" in modules:
            selected_modules.append("uncategorized")
        profiles[profile_id] = {
            "description": f"{profile['description']} Skills only; no hooks, agents, commands, or runtime setup.",
            "modules": selected_modules,
            "excluded_modules": [module for module in profile["modules"] if module not in modules],
        }

    destination = args.destination.resolve()
    full = set()
    for module in profiles["full"]["modules"]:
        full.update(modules[module]["skills"])
    if full != set(skill_names):
        raise ValueError("full profile does not resolve to the complete catalog")
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("destination must not overlap the ECC source")
    if destination.exists() and not (destination.parent / "ecc_catalog.json").is_file():
        raise ValueError("refusing to replace an unmanaged destination")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        skills_root,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    for name in skill_names:
        license_path = destination / name / "LICENSE.ecc"
        if license_path.exists():
            raise ValueError("upstream LICENSE.ecc conflicts with the attribution file")
        shutil.copy2(source / "LICENSE", license_path)
    catalog_path = destination.parent / "ecc_catalog.json"
    catalog_path.write_text(json.dumps({
        "version": 1,
        "source": "https://github.com/affaan-m/ECC",
        "commit": args.commit,
        "synced_at": args.synced_at,
        "skills": {name: skill_metadata(skills_root / name) for name in skill_names},
        "modules": modules,
        "profiles": profiles,
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "utf-8")
    shutil.copy2(source / "LICENSE", Path("docs/third-party/ECC-LICENSE"))

    print(json.dumps({"skills": len(skill_names), "modules": len(modules), "profiles": len(profiles)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
