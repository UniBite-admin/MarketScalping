import unittest
from types import SimpleNamespace

from baseline_benchmark import (
    BaselineBenchmarkConfig,
    build_baseline_comparison,
    compute_buy_and_hold_baseline,
    compute_no_trade_baseline,
)


class Step9_1BaselineTests(unittest.TestCase):
    def _fixture_events(self):
        return [
            {
                "event_time_utc": "2025-01-01T12:00:00Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 100.0,
                "ask": 101.0,
                "last": 100.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:01Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 101.0,
                "ask": 102.0,
                "last": 101.5,
            },
            {
                "event_time_utc": "2025-01-01T12:00:02Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 102.0,
                "ask": 103.0,
                "last": 102.5,
            },
        ]

    def test_deterministic_no_trade_baseline(self):
        config = BaselineBenchmarkConfig(initial_capital=1000.0, benchmark_type="NO_TRADE", dataset_id="dataset-001")
        baseline = compute_no_trade_baseline(self._fixture_events(), config=config)
        self.assertEqual(baseline.baseline_type, "NO_TRADE")
        self.assertEqual(baseline.final_equity, 1000.0)
        self.assertEqual(baseline.realized_pnl, 0.0)
        self.assertEqual(baseline.trade_count, 0)
        self.assertTrue(baseline.deterministic)

    def test_deterministic_buy_and_hold_baseline(self):
        config = BaselineBenchmarkConfig(initial_capital=1000.0, benchmark_type="BUY_AND_HOLD", dataset_id="dataset-001")
        baseline = compute_buy_and_hold_baseline(self._fixture_events(), config=config)
        self.assertEqual(baseline.baseline_type, "BUY_AND_HOLD")
        self.assertEqual(baseline.trade_count, 1)
        self.assertAlmostEqual(baseline.initial_capital, 1000.0)
        self.assertGreater(baseline.final_equity, 0.0)
        self.assertTrue(baseline.deterministic)

    def test_identical_dataset_window_treatment(self):
        events = self._fixture_events()
        config = BaselineBenchmarkConfig(initial_capital=1000.0, benchmark_type="BUY_AND_HOLD", dataset_id="dataset-001")
        first = compute_buy_and_hold_baseline(events, config=config)
        second = compute_buy_and_hold_baseline(events, config=config)
        self.assertEqual(first.dataset_id, second.dataset_id)
        self.assertEqual(first.evaluation_window, second.evaluation_window)
        self.assertEqual(first.benchmark_identity, second.benchmark_identity)

    def test_benchmark_freeze_and_config_identity(self):
        config = BaselineBenchmarkConfig(initial_capital=1000.0, benchmark_type="BUY_AND_HOLD", dataset_id="dataset-001")
        self.assertTrue(config.frozen)
        self.assertEqual(config.configuration_identity(), config.configuration_identity())
        self.assertIn("configuration_identity", config.as_dict())

    def test_comparison_result_is_generated(self):
        candidate = SimpleNamespace(
            final_equity=1100.0,
            realized_pnl=100.0,
            trade_count=1,
            drawdown=0.05,
            total_costs=10.0,
            dataset_id="dataset-001",
            status="PASS",
            strategy_configuration={"strategy": "candidate"},
        )
        events = self._fixture_events()
        config = BaselineBenchmarkConfig(initial_capital=1000.0, benchmark_type="BUY_AND_HOLD", dataset_id="dataset-001")
        comparison = build_baseline_comparison(candidate, events, config=config)
        self.assertEqual(comparison.status, "PASS")
        self.assertEqual(comparison.benchmark_config.benchmark_type, "BUY_AND_HOLD")
        self.assertIn("candidate_result", comparison.as_dict())
        self.assertEqual(comparison.authority_boundary, "read_only_evidence")

    def test_failed_baseline_comparison_is_recorded(self):
        candidate = SimpleNamespace(
            final_equity=900.0,
            realized_pnl=-100.0,
            trade_count=1,
            drawdown=0.10,
            total_costs=20.0,
            dataset_id="dataset-001",
            status="FAIL",
            strategy_configuration={"strategy": "candidate"},
        )
        events = self._fixture_events()
        config = BaselineBenchmarkConfig(initial_capital=1000.0, benchmark_type="BUY_AND_HOLD", dataset_id="dataset-001")
        comparison = build_baseline_comparison(candidate, events, config=config)
        self.assertEqual(comparison.status, "FAILED_BASELINE_COMPARISON")
        self.assertIn("FAILED_BASELINE_COMPARISON", comparison.status)

    def test_reproducibility_metadata_is_present(self):
        candidate = SimpleNamespace(
            final_equity=1050.0,
            realized_pnl=50.0,
            trade_count=1,
            drawdown=0.02,
            total_costs=5.0,
            dataset_id="dataset-001",
            status="PASS",
            strategy_configuration={"strategy": "candidate"},
        )
        events = self._fixture_events()
        config = BaselineBenchmarkConfig(initial_capital=1000.0, benchmark_type="BUY_AND_HOLD", dataset_id="dataset-001", repository_revision="rev-001")
        comparison = build_baseline_comparison(candidate, events, config=config)
        metadata = comparison.reproducibility_metadata
        self.assertEqual(metadata["starting_capital"], 1000.0)
        self.assertEqual(metadata["repository_revision"], "rev-001")
        self.assertIn("benchmark_configuration", metadata)
        self.assertEqual(metadata["source_of_truth"], "baseline_benchmark_evidence_only")

    def test_no_second_ledger_or_risk_authority_is_created(self):
        candidate = SimpleNamespace(
            final_equity=1100.0,
            realized_pnl=100.0,
            trade_count=1,
            drawdown=0.03,
            total_costs=5.0,
            dataset_id="dataset-001",
            status="PASS",
            strategy_configuration={"strategy": "candidate"},
        )
        comparison = build_baseline_comparison(candidate, self._fixture_events(), config=BaselineBenchmarkConfig(initial_capital=1000.0, dataset_id="dataset-001"))
        self.assertEqual(comparison.authority_boundary, "read_only_evidence")
        self.assertNotIn("ledger", comparison.reproducibility_metadata)
        self.assertNotIn("risk_engine", comparison.reproducibility_metadata)

    def test_no_lookahead_in_buy_and_hold_baseline(self):
        config = BaselineBenchmarkConfig(initial_capital=1000.0, benchmark_type="BUY_AND_HOLD", dataset_id="dataset-001")
        baseline = compute_buy_and_hold_baseline(self._fixture_events(), config=config)
        self.assertEqual(baseline.observed_assumptions["first_event_time_utc"], "2025-01-01T12:00:00Z")
        self.assertEqual(baseline.observed_assumptions["last_event_time_utc"], "2025-01-01T12:00:02Z")
        self.assertAlmostEqual(baseline.observed_assumptions["start_price"], 100.5)
        self.assertAlmostEqual(baseline.observed_assumptions["end_price"], 102.5)


if __name__ == "__main__":
    unittest.main()
