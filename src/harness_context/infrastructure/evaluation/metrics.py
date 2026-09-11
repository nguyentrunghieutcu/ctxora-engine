from __future__ import annotations

"""Small provider-neutral retrieval quality metrics for golden fixtures."""

import math


def recall_at_k(results: list[dict], expected_paths: set[str], expected_symbols: set[str], k: int) -> float:
    selected = results[:k]
    found_paths = {item["path"].rsplit("/", 1)[-1] for item in selected}
    found_symbols = {item.get("symbol", "") for item in selected}
    signals = []
    if expected_paths:
        signals.append(bool(found_paths & expected_paths))
    if expected_symbols:
        signals.append(bool(found_symbols & expected_symbols))
    return sum(signals) / len(signals) if signals else 1.0


def coverage_score(result: dict) -> float:
    if result.get("coverage") == "sufficient":
        return 1.0
    if result.get("coverage") == "partial":
        return 0.5
    return 0.0

def reciprocal_rank(results: list[dict], expected_paths: set[str], expected_symbols: set[str]) -> float:
    for rank, item in enumerate(results, 1):
        if item["path"].rsplit("/", 1)[-1] in expected_paths or item.get("symbol", "") in expected_symbols:
            return 1.0 / rank
    return 0.0

def ndcg_at_k(results: list[dict], expected_paths: set[str], expected_symbols: set[str], k: int) -> float:
    relevance = [
        int(item["path"].rsplit("/", 1)[-1] in expected_paths or item.get("symbol", "") in expected_symbols)
        for item in results[:k]
    ]
    dcg = sum(value / math.log2(rank + 1) for rank, value in enumerate(relevance, 1))
    relevant_count = sum(relevance)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, relevant_count + 1))
    return dcg / ideal if ideal else 1.0
