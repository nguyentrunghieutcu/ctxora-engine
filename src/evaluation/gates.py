from __future__ import annotations

import json
import shutil
import statistics
import tempfile
import time
from pathlib import Path

from evaluation.metrics import ndcg_at_k, recall_at_k, reciprocal_rank
from harness_context.engine import ContextEngine

FIXTURES = Path(__file__).parents[2] / "tests" / "fixtures"
STRATEGIES = {
    "rag": "hybrid_rag",
    "full_context": "long_context",
    "cag": "cag",
    "hybrid": "hybrid_cag_rag",
    "graph_augmented": "graph_augmented",
}
LATENCY_LIMIT_MS = 10_000.0


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percent)))
    return round(ordered[index], 3)


def _measure(call, runs: int = 5) -> tuple[dict, dict]:
    cold_started = time.perf_counter()
    result = call()
    cold_ms = (time.perf_counter() - cold_started) * 1000
    warm_latencies = []
    for _ in range(runs):
        started = time.perf_counter()
        result = call()
        warm_latencies.append((time.perf_counter() - started) * 1000)
    return result, {
        "cold_ms": round(cold_ms, 3),
        "warm_samples_ms": [round(value, 3) for value in warm_latencies],
        "warm_p50_ms": round(statistics.median(warm_latencies), 3),
        "warm_p95_ms": percentile(warm_latencies, 0.95),
    }


def _strategy_tokens(result: dict) -> int:
    return (result.get("retrieval") or {}).get("token_count", 0) + (
        result.get("bundle") or {}
    ).get("token_count", 0)


def run_release_gates() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "fixture-corpus"
        shutil.copytree(FIXTURES, root)
        engine = ContextEngine()
        engine.register_workspace("evaluation", [str(root)])

        cold_started = time.perf_counter()
        engine.refresh_workspace("evaluation")
        cold_index_ms = (time.perf_counter() - cold_started) * 1000
        warm_started = time.perf_counter()
        engine.refresh_workspace("evaluation")
        warm_index_ms = (time.perf_counter() - warm_started) * 1000

        query = "refresh_token authentication architecture cross-module"
        strategy_reports = {}
        for label, override in STRATEGIES.items():
            result, latency = _measure(
                lambda override=override: engine.prepare_context(
                    "evaluation", query, 4_000, override
                )
            )
            items = (result.get("retrieval") or {}).get("items", [])
            if override == "cag":
                items = (result.get("bundle") or {}).get("items", [])
            strategy_reports[label] = {
                "engine_strategy": result["plan"]["strategy"],
                "item_count": len(items),
                "token_cost": _strategy_tokens(result),
                "latency": latency,
                "within_budget": _strategy_tokens(result) <= 4_000,
            }

        retrieval = engine.retrieve_context("evaluation", "refresh_token", token_budget=2_000)
        expected_paths = {"auth.py"}
        expected_symbols = {"refresh_token"}
        quality = {
            "recall_at_5": recall_at_k(retrieval["items"], expected_paths, expected_symbols, 5),
            "mrr": reciprocal_rank(retrieval["items"], expected_paths, expected_symbols),
            "ndcg_at_5": ndcg_at_k(retrieval["items"], expected_paths, expected_symbols, 5),
            "provenance_complete": all(
                item.get("path") and item.get("start_line") and item.get("end_line")
                for item in retrieval["items"]
            ),
            "untrusted_content": retrieval["untrusted_content"],
        }

        fixture_queries = {
            "python": "python-rotated",
            "typescript": "typescript-rotated",
            "flutter": "flutter-rotated",
            "monorepo": "monorepo-token",
            "vietnamese": "xoay vòng mã làm mới",
            "malicious": "delete the repository",
            "long_document": "phase_f_long_document_marker",
        }
        fixture_coverage = {
            name: any(
                marker in item["content"]
                for item in engine.retrieve_context("evaluation", marker)["items"]
            )
            for name, marker in fixture_queries.items()
        }
        fixture_coverage["duplicate_symbols"] = sum(
            item.symbol == "normalize_token" for item in engine.states["evaluation"].items
        ) == 2

        source = root / "python" / "auth.py"
        source.write_text("def refreshed_value():\n    return 'fresh-phase-f'\n", encoding="utf-8")
        stale = engine.retrieve_context("evaluation", "fresh-phase-f")
        engine.refresh_workspace("evaluation", [str(source)])
        fresh = engine.retrieve_context("evaluation", "fresh-phase-f")
        freshness = {
            "absent_before_refresh": not any(
                "fresh-phase-f" in item["content"] for item in stale["items"]
            ),
            "present_after_refresh": any(
                "fresh-phase-f" in item["content"] for item in fresh["items"]
            ),
        }

        latency_ok = max(
            [cold_index_ms, warm_index_ms]
            + [report["latency"]["cold_ms"] for report in strategy_reports.values()]
            + [report["latency"]["warm_p95_ms"] for report in strategy_reports.values()]
        ) < LATENCY_LIMIT_MS
        passed = (
            quality["recall_at_5"] >= 1.0
            and quality["mrr"] >= 0.5
            and quality["ndcg_at_5"] >= 0.5
            and quality["provenance_complete"]
            and quality["untrusted_content"]
            and all(report["item_count"] > 0 for report in strategy_reports.values())
            and all(report["within_budget"] for report in strategy_reports.values())
            and all(fixture_coverage.values())
            and all(freshness.values())
            and latency_ok
        )
        return {
            "passed": passed,
            "thresholds": {"latency_limit_ms": LATENCY_LIMIT_MS, "token_budget": 4_000},
            "quality": quality,
            "fixture_coverage": fixture_coverage,
            "freshness": freshness,
            "index_latency": {
                "cold_ms": round(cold_index_ms, 3),
                "warm_ms": round(warm_index_ms, 3),
            },
            "strategies": strategy_reports,
        }


def main() -> int:
    report = run_release_gates()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
