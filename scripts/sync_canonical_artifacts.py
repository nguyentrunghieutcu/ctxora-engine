#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from harness_context.artifacts import canonical_artifact_drift, sync_canonical_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize packaged canonical artifacts with compatibility projections."
    )
    parser.add_argument("--check", action="store_true", help="Fail when projections or manifest drift")
    args = parser.parse_args()
    if not args.check:
        sync_canonical_artifacts(ROOT)
    issues = canonical_artifact_drift(ROOT)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    print("canonical artifacts are synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
