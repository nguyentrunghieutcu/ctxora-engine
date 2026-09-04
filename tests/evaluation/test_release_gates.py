from __future__ import annotations

import unittest

from evaluation.gates import STRATEGIES, percentile, run_release_gates
from evaluation.metrics import ndcg_at_k


class EvaluationGateTests(unittest.TestCase):
    def test_percentile_is_deterministic_for_small_ci_samples(self):
        self.assertEqual(percentile([5.0, 1.0, 3.0, 2.0, 4.0], 0.95), 4.0)

    def test_ndcg_is_bounded_when_path_and_symbol_match_multiple_chunks(self):
        results = [
            {"path": "/tmp/auth.py", "symbol": "refresh_token"},
            {"path": "/tmp/auth.py", "symbol": "authenticate_request"},
        ]
        self.assertEqual(ndcg_at_k(results, {"auth.py"}, {"refresh_token"}, 5), 1.0)

    def test_release_quality_gate(self):
        report = run_release_gates()
        self.assertTrue(report["passed"], report)
        self.assertEqual(set(report["strategies"]), set(STRATEGIES))
        self.assertTrue(all(report["fixture_coverage"].values()))
        self.assertTrue(all(report["freshness"].values()))
