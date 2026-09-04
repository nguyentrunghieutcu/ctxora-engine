from __future__ import annotations

import re

_PATTERNS = (
    re.compile(rb"\bsk-[A-Za-z0-9_-]{16,}\b", re.IGNORECASE),
    re.compile(rb"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"),
    re.compile(rb"\b(?:gh[pors]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})\b"),
    re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)


def contains_secret(content: bytes) -> bool:
    return any(pattern.search(content) for pattern in _PATTERNS)
