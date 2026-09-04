from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from harness_context.schemas import ContextItem


class RankFusion:
    def fuse(self, pools: Sequence[Sequence[float]], weights: Sequence[float], top_n: int) -> list[tuple[int, float]]:
        fused: dict[int, float] = defaultdict(float)
        for scores, weight in zip(pools, weights):
            for rank, index in enumerate(sorted(range(len(scores)), key=scores.__getitem__, reverse=True)[:top_n], 1):
                if scores[index] > 0:
                    fused[index] += weight / (60 + rank)
        return [(index, fused[index]) for index in sorted(fused, key=fused.get, reverse=True)[:top_n]]


class GraphExpander:
    def expand(self, selected: list[ContextItem], items: Sequence[ContextItem], graph: Mapping[str, set[str]]) -> list[ContextItem]:
        result = list(selected)
        ids = {item.chunk_id for item in result}
        by_id = {item.chunk_id: item for item in items}
        for item in list(result):
            for neighbor in sorted(graph.get(item.chunk_id, set())):
                if neighbor not in ids and neighbor in by_id:
                    result.append(by_id[neighbor]); ids.add(neighbor)
        return result


class Selector:
    def select(self, items: Sequence[ContextItem], token_budget: int) -> tuple[list[ContextItem], int]:
        output, used = [], 0
        for item in items:
            if used + item.tokens <= token_budget:
                output.append(item); used += item.tokens
        return output, used


class CoveragePolicy:
    def assess(self, query: str, items: Sequence[dict]) -> tuple[str, list[str]]:
        missing = []
        if not items: missing.append("No relevant source was retrieved")
        if not any(item["type"] in {"function", "class"} for item in items): missing.append("No implementation symbol was retrieved")
        if "test" in query.casefold() and not any("test" in item["path"].casefold() for item in items): missing.append("No tests were retrieved")
        return ("insufficient" if missing else "sufficient"), missing
