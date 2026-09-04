#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from harness_context.topology import audit

failures = audit(ROOT)
for failure in failures:
    print(f"ERROR: {failure}")
raise SystemExit(1 if failures else 0)
