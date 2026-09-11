from harness_context.adapters.harnesses.base import HarnessAdapter
from harness_context.domain.harnesses import REGISTRY


def get_harness_adapter(name: str) -> HarnessAdapter:
    return HarnessAdapter(REGISTRY.get(name))

