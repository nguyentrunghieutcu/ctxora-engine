from __future__ import annotations

import json
from urllib.request import Request, urlopen


class NpmReleaseRegistry:
    def __init__(self, package: str = "ctxora", timeout: float = 5.0):
        self.package = package
        self.timeout = timeout

    def latest(self) -> str:
        request = Request(
            f"https://registry.npmjs.org/{self.package}/latest",
            headers={"Accept": "application/json", "User-Agent": "ctxora-update-check"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read(65_537))
        version = payload.get("version") if isinstance(payload, dict) else None
        if not isinstance(version, str):
            raise TypeError("npm registry returned no release version")
        return version
