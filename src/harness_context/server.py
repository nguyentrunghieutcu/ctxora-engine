import sys

from harness_context.interfaces.mcp import legacy_server as _implementation

sys.modules[__name__] = _implementation
