"""Minimal provider-neutral local API example."""
from pathlib import Path

from harness_context.api.v2 import PrepareContextRequest
from harness_context.bootstrap import build_container

workspace = Path.cwd().resolve()
container = build_container([str(workspace)])
workspace_id = next(iter(container.engine.states))
container.refresh.execute(workspace_id)
result = container.context.prepare(
    PrepareContextRequest(workspace_id, "Where is startup configured?", 2000)
)
print(result.to_dict())
