from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Migration:
    version: int
    apply: object
    rollback: object | None = None


def _version_one(state_dir: Path) -> None:
    (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)


def _version_two(state_dir: Path) -> None:
    (state_dir / "candidates").mkdir(parents=True, exist_ok=True)


def _rollback_version_two(state_dir: Path) -> None:
    (state_dir / "candidates").rmdir()


MIGRATIONS = (Migration(1, _version_one), Migration(2, _version_two, _rollback_version_two))
