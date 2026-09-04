from __future__ import annotations

import hashlib
from pathlib import Path


def workspace_identity(root: str | Path) -> str:
    canonical = str(Path(root).expanduser().resolve(strict=True))
    return "ws_" + hashlib.sha256(canonical.encode()).hexdigest()[:16]
