import unittest

from paper_backtest_comparator import compare_paper_to_backtest


class Step10_2PaperBacktestComparisonTests(unittest.TestCase):
    def _paper_result(self):
        return {
            "final_equity": 1015.0,
            "realized_pnl": 15.0,
            "metrics": {"net_pnl": 15.0, "win_rate": 0.5},
            "observed_assumptions": {
                "event_count": 120,
                "first_event_time_utc": "2026-01-01T00:00:00Z",
                "last_event_time_utc": "2026-01-01T00:30:00Z",
            },
            "latency_configuration": {"latency_ticks": 2},
            "spread_configuration": {"spread_pct": 0.002},
            "fee_configuration": {"fee_rate": 0.001},
            "slippage_configuration": {"slippage_bps": 15},
            "partial_fill_ratio": 0.8,
            "rejected_executions": 2,
            "strategy_decisions": [{"action": "CANDIDATE_TRADE"}, {"action": "NO_TRADE"}],
            "risk_decisions": [{"approved": True}, {"approved": False}],
            "execution_events": [{"execution_action": "SIMULATED_ORDER_PREPARED"}, {"execution_action": "SKIPPED"}],
            "accounting_decisions": [{"status": "ACCEPTED"}, {"status": "REJECTED"}],
        }

    def _backtest_result(self):
        return {
            "final_equity": 1035.0,
            "realized_pnl": 35.0,
            "metrics": {"net_pnl": 35.0, "win_rate": 0.6},
            "observed_assumptions": {
                "event_count": 100,
                "first_event_time_utc": "2026-01-01T00:00:00Z",
                "last_event_time_utc": "2026-01-01T00:25:00Z",
            },
            "latency_configuration": {"latency_ticks": 0},
            "spread_configuration": {"spread_pct": 0.001},
            "fee_configuration": {"fee_rate": 0.001},
            "slippage_configuration": {"slippage_bps": 10},
            "partial_fill_ratio": 1.0,
            "rejected_executions": 0,
            "strategy_decisions": [{"action": "CANDIDATE_TRADE"}],
            "risk_decisions": [{"approved": True}],
            "execution_events": [{"execution_action": "SIMULATED_ORDER_PREPARED"}],
            "accounting_decisions": [{"status": "ACCEPTED"}],
        }

    def test_comparison_explains_material_differences(self):
        comparison = compare_paper_to_backtest(self._paper_result(), self._backtest_result())

        self.assertEqual(comparison.authority_boundary, "read_only_evidence")
        self.assertTrue(comparison.deterministic)
        self.assertIn("market_data", [issue["category"] for issue in comparison.discrepancy_analysis])
        self.assertIn("latency", [issue["category"] for issue in comparison.discrepancy_analysis])
        self.assertIn("spread", [issue["category"] for issue in comparison.discrepancy_analysis])
        self.assertEqual(comparison.summary_status, "PASS")
        self.assertFalse(comparison.unexplained_divergence)

    def test_unexplained_divergence_blocks_validation(self):
        paper = self._paper_result()
        backtest = self._backtest_result()
        paper["final_equity"] = 1500.0
        backtest["final_equity"] = 1000.0
        paper["observed_assumptions"]["event_count"] = 10
        backtest["observed_assumptions"]["event_count"] = 10

        comparison = compare_paper_to_backtest(paper, backtest)

        self.assertEqual(comparison.summary_status, "FAIL")
        self.assertTrue(comparison.unexplained_divergence)

    def test_result_keeps_paper_and_backtest_artifacts_separate(self):
        comparison = compare_paper_to_backtest(self._paper_result(), self._backtest_result())
        self.assertIn("paper_result", comparison.as_dict())
        self.assertIn("backtest_result", comparison.as_dict())
        self.assertIsNot(comparison.paper_result, comparison.backtest_result)
        self.assertTrue(comparison.data_quality_controls["paper_and_backtest_result_separate"])


if __name__ == "__main__":
    unittest.main()
