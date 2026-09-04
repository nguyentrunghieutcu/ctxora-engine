#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from harness_context.storage.snapshots import SnapshotStore

parser = argparse.ArgumentParser(description="Apply Harness state migrations.")
parser.add_argument("workspace", type=Path)
args = parser.parse_args()
store = SnapshotStore(args.workspace.resolve())
store.prepare()
print(store.state_dir)
