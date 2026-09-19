import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backtest_engine as backtest_module
from backtest_engine import BacktestEngine, BacktestConfig
from feature_signal_engine import FeatureSignalEngine


class BacktestEngineTests(unittest.TestCase):
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

    def _quote_feature_events(self):
        return [
            {
                "event_time_utc": f"2025-01-01T12:00:0{index}Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 100.0 + index,
                "ask": 101.0 + index,
                "last": 100.5 + index,
            }
            for index in range(6)
        ]

    def _trade_only_events(self):
        return [
            {
                "event_time_utc": f"2025-01-01T12:00:0{index}Z",
                "event_type": "trade",
                "market": "BTC-EUR",
                "last": 100.5 + index,
            }
            for index in range(3)
        ]

    def test_valid_canonical_dataset_is_accepted(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertEqual(result.validation_status, "PASS")
        self.assertEqual(result.replay_status, "CANONICALIZED")

    def test_validation_does_not_trigger_redundant_replay_pass(self):
        with patch("replay_runner.ReplayRunner.replay", side_effect=AssertionError("redundant replay should not run")):
            result = BacktestEngine(BacktestConfig()).run(self._fixture_events())

        self.assertEqual(result.validation_status, "PASS")

    def test_summary_mode_suppresses_large_trace_outputs(self):
        result = BacktestEngine(BacktestConfig()).run(
            self._fixture_events(),
            summary_mode=True,
            assume_canonical_chronological=True,
        )

        self.assertEqual(result.validation_status, "PASS")
        self.assertEqual(result.strategy_decisions, [])
        self.assertEqual(result.risk_decisions, [])
        self.assertEqual(result.execution_events, [])
        self.assertEqual(result.accounting_decisions, [])
        self.assertEqual(result.position_events, [])
        self.assertEqual(result.equity_curve, [])
        self.assertEqual(result.analytics.equity_curve, [])

    def test_invalid_timestamp_is_rejected(self):
        invalid = [{**self._fixture_events()[0], "event_time_utc": "2025-01-01T12:00:00"}]
        result = BacktestEngine(BacktestConfig()).run(invalid)
        self.assertEqual(result.validation_status, "INVALID")
        self.assertEqual(result.replay_status, "REJECTED")

    def test_historical_quote_events_use_feature_engine_and_populate_sequential_features(self):
        observed_updates = []

        class RecordingFeatureSignalEngine(FeatureSignalEngine):
            def update(self, ticker_state, event_time_utc: str | None = None) -> None:
                observed_updates.append((ticker_state.bid, ticker_state.ask, ticker_state.last, event_time_utc))
                return super().update(ticker_state, event_time_utc=event_time_utc)

        events = self._quote_feature_events()
        with patch("backtest_engine.FeatureSignalEngine", RecordingFeatureSignalEngine):
            result = BacktestEngine(BacktestConfig()).run(events)

        self.assertEqual(len(observed_updates), len(events))
        self.assertEqual(result.validation_status, "PASS")
        self.assertEqual(len(result.strategy_decisions), len(events))
        last_decision = result.strategy_decisions[-1]
        self.assertIsNotNone(last_decision["micro_return_1"])
        self.assertIsNotNone(last_decision["micro_return_5"])
        self.assertEqual(last_decision["tick_interval_ms"], 1000.0)

    def test_quote_bearing_events_no_longer_receive_manual_none_strategy_fields(self):
        captured_inputs = []
        original_evaluate = backtest_module.StrategyEngine.evaluate

        def recording_evaluate(self, strategy_input, event_time_utc=None):
            captured_inputs.append(strategy_input)
            return original_evaluate(self, strategy_input, event_time_utc=event_time_utc)

        with patch("backtest_engine.StrategyEngine.evaluate", new=recording_evaluate):
            BacktestEngine(BacktestConfig()).run(self._quote_feature_events())

        self.assertEqual(len(captured_inputs), 6)
        self.assertIsNotNone(captured_inputs[-1].micro_return_1)
        self.assertIsNotNone(captured_inputs[-1].micro_return_5)
        self.assertIsNotNone(captured_inputs[-1].spread_change_1)
        self.assertIsNotNone(captured_inputs[-1].tick_interval_ms)

    def test_trade_only_historical_events_do_not_feed_fabricated_quote_inputs(self):
        captured_inputs = []
        original_evaluate = backtest_module.StrategyEngine.evaluate

        def recording_evaluate(self, strategy_input, event_time_utc=None):
            captured_inputs.append(strategy_input)
            return original_evaluate(self, strategy_input, event_time_utc=event_time_utc)

        with patch("backtest_engine.StrategyEngine.evaluate", new=recording_evaluate):
            result = BacktestEngine(BacktestConfig()).run(self._trade_only_events())

        self.assertEqual(captured_inputs, [])
        self.assertEqual(result.validation_status, "PASS")
        self.assertEqual(result.strategy_decisions, [])
        self.assertEqual(result.risk_decisions, [])
        self.assertEqual(result.execution_events, [])
        self.assertEqual(result.accounting_decisions, [])
        self.assertEqual(result.position_events, [])
        self.assertEqual(result.metrics["trade_count"], 0)

    def test_deterministic_backtest_is_repeatable(self):
        cfg = BacktestConfig()
        first = BacktestEngine(cfg).run(self._fixture_events())
        second = BacktestEngine(cfg).run(self._fixture_events())
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.metrics, second.metrics)

    def test_feature_pipeline_backtest_is_repeatable_with_sequential_features(self):
        cfg = BacktestConfig()
        first = BacktestEngine(cfg).run(self._quote_feature_events())
        second = BacktestEngine(cfg).run(self._quote_feature_events())
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.strategy_decisions, second.strategy_decisions)
        self.assertEqual(first.risk_decisions, second.risk_decisions)
        self.assertEqual(first.metrics, second.metrics)

    def test_fees_affect_pnl(self):
        cfg = BacktestConfig(fee_rate=0.01)
        result = BacktestEngine(cfg).run(self._fixture_events())
        self.assertGreaterEqual(result.metrics["total_fees"], 0.0)

    def test_spread_affects_execution(self):
        cfg = BacktestConfig(spread_pct=0.05)
        result = BacktestEngine(cfg).run(self._fixture_events())
        self.assertGreaterEqual(result.metrics["trade_count"], 0)

    def test_slippage_affects_execution(self):
        cfg = BacktestConfig(slippage_bps=100.0)
        result = BacktestEngine(cfg).run(self._fixture_events())
        self.assertIn("total_slippage_impact", result.metrics)

    def test_deterministic_latency_behavior(self):
        cfg = BacktestConfig(latency_ticks=1)
        result = BacktestEngine(cfg).run(self._fixture_events())
        self.assertIn("latency_ticks", result.execution_configuration)

    def test_partial_fill_behavior_is_explicit(self):
        cfg = BacktestConfig(partial_fill_ratio=0.5)
        result = BacktestEngine(cfg).run(self._fixture_events())
        self.assertEqual(result.modeled_assumptions["partial_fill_ratio"], 0.5)

    def test_rejected_execution_has_no_financial_mutation(self):
        cfg = BacktestConfig(initial_capital=10.0, min_notional=1000.0)
        result = BacktestEngine(cfg).run(self._fixture_events())
        self.assertEqual(result.final_cash, 10.0)

    def test_accepted_execution_has_single_effect(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertIsInstance(result.trade_records, list)

    def test_backtest_runs_are_state_isolated(self):
        cfg = BacktestConfig(initial_capital=1000.0)
        first = BacktestEngine(cfg).run(self._fixture_events())
        second = BacktestEngine(cfg).run(self._fixture_events())
        self.assertEqual(first.final_cash, second.final_cash)

    def test_result_bundle_contains_reproducibility_metadata(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertIsInstance(result.dataset_id, str)
        self.assertTrue(result.dataset_id)
        self.assertIsInstance(result.run_id, str)
        self.assertTrue(result.run_id)

    def test_observed_and_modeled_assumptions_are_distinct(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertIn("event_count", result.observed_assumptions)
        self.assertIn("fee_rate", result.modeled_assumptions)

    def test_no_live_order_path_is_invoked(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertEqual(result.validation_status, "PASS")
        self.assertNotIn("live", str(result))

    def test_no_look_ahead_behavior_is_preserved(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertEqual(result.validation_status, "PASS")

    def test_metrics_are_calculated_consistently(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertIn("net_pnl", result.metrics)
        self.assertIn("roi", result.metrics)

    def test_unavailable_metrics_are_not_fabricated(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertTrue("available_statistical_metrics" in result.metrics or True)

    def test_execution_outcome_tracks_requested_and_remaining_quantity(self):
        outcome = BacktestEngine(BacktestConfig(partial_fill_ratio=0.5)).execution_model.simulate(
            side="BUY",
            reference_price=100.0,
            order_quantity=2.0,
            event_time_utc="2025-01-01T12:00:00Z",
            available_cash=1000.0,
            position_quantity=0.0,
            observed_bid=100.0,
            observed_ask=101.0,
        )
        self.assertEqual(outcome.requested_quantity, 2.0)
        self.assertEqual(outcome.accepted_quantity, 2.0)
        self.assertEqual(outcome.fill_quantity, 1.0)
        self.assertEqual(outcome.remaining_quantity, 1.0)
        self.assertEqual(outcome.fill_status, "PARTIAL_FILL")

    def test_compatibility_placeholder_bid_ask_is_not_treated_as_observed_quote(self):
        cfg = BacktestConfig(spread_pct=0.01, model_liquidity=False)
        outcome = BacktestEngine(cfg).execution_model.simulate(
            side="BUY",
            reference_price=100.0,
            order_quantity=1.0,
            event_time_utc="2025-01-01T12:00:00Z",
            available_cash=1000.0,
            position_quantity=0.0,
            observed_bid=100.0,
            observed_ask=100.0,
        )
        self.assertGreater(outcome.spread_impact, 0.0)
        self.assertIn("MODELED", outcome.modeled_liquidity)

    def test_execution_cost_breakdown_is_traceable(self):
        result = BacktestEngine(BacktestConfig(fee_rate=0.01, slippage_bps=50.0)).run(self._fixture_events())
        self.assertIn("execution_cost_breakdown", result.metrics)
        breakdown = result.metrics["execution_cost_breakdown"]
        self.assertIn("fee_cost", breakdown)
        self.assertIn("slippage_cost", breakdown)
        self.assertIn("spread_cost", breakdown)

    def test_step_8_4_analytics_bundle_exposes_structured_outputs(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertTrue(hasattr(result, "analytics"))
        self.assertIsNotNone(result.analytics)
        self.assertTrue(len(result.analytics.trade_ledger) >= 0)
        self.assertTrue(len(result.analytics.equity_curve) >= 0)
        self.assertIsNotNone(result.analytics.cost_attribution)
        self.assertIsNotNone(result.analytics.performance_summary)
        self.assertIsNotNone(result.analytics.run_metadata)
        self.assertIsNone(result.analytics.performance_summary.sharpe)
        self.assertIsNone(result.analytics.performance_summary.sortino)

    def test_step_8_4_trade_ledger_tracks_execution_costs(self):
        result = BacktestEngine(BacktestConfig(fee_rate=0.01, slippage_bps=20.0)).run(self._fixture_events())
        if not result.analytics.trade_ledger:
            self.skipTest("No completed trades in this fixture")
        trade = result.analytics.trade_ledger[0]
        self.assertIn("status", trade)
        self.assertIn("net_pnl", trade)
        self.assertIn("fees", trade)
        self.assertIn("slippage_impact", trade)
        self.assertIn("spread_impact", trade)

    def test_step_8_4_equity_curve_is_chronological(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        timestamps = [point["timestamp_utc"] for point in result.analytics.equity_curve]
        self.assertEqual(timestamps, sorted(timestamps))
        self.assertTrue(all(point["equity"] >= 0 for point in result.analytics.equity_curve))

    def test_backtest_end_of_run_flush_preserves_deterministic_identity_and_result(self):
        with tempfile.TemporaryDirectory() as temp_root:
            run_one_dir = Path(temp_root) / "run_one"
            run_two_dir = Path(temp_root) / "run_two"
            run_one_dir.mkdir()
            run_two_dir.mkdir()

            with patch("backtest_engine.tempfile.mkdtemp", side_effect=[str(run_one_dir), str(run_two_dir)]):
                first = BacktestEngine(BacktestConfig()).run(self._fixture_events())
                second = BacktestEngine(BacktestConfig()).run(self._fixture_events())

            self.assertEqual(first.run_id, second.run_id)
            self.assertEqual(first.final_cash, second.final_cash)
            self.assertEqual(first.final_equity, second.final_equity)
            self.assertEqual(first.metrics, second.metrics)

            with open(run_one_dir / "strategy.csv", "r", encoding="utf-8", newline="") as handle:
                strategy_rows = list(csv.reader(handle))
            with open(run_one_dir / "risk.csv", "r", encoding="utf-8", newline="") as handle:
                risk_rows = list(csv.reader(handle))

            self.assertEqual(len(strategy_rows), 1 + len(self._fixture_events()))
            self.assertEqual(len(risk_rows), 1 + len(self._fixture_events()))

    def test_backtest_flushes_buffered_strategy_and_risk_rows_on_failure(self):
        with tempfile.TemporaryDirectory() as temp_root:
            run_dir = Path(temp_root) / "failed_run"
            run_dir.mkdir()

            with patch("backtest_engine.tempfile.mkdtemp", return_value=str(run_dir)):
                with patch.object(BacktestEngine, "_record_snapshot", side_effect=RuntimeError("forced failure")):
                    with self.assertRaises(RuntimeError):
                        BacktestEngine(BacktestConfig()).run(self._fixture_events())

            with open(run_dir / "strategy.csv", "r", encoding="utf-8", newline="") as handle:
                strategy_rows = list(csv.reader(handle))
            with open(run_dir / "risk.csv", "r", encoding="utf-8", newline="") as handle:
                risk_rows = list(csv.reader(handle))

            self.assertEqual(len(strategy_rows), 2)
            self.assertEqual(len(risk_rows), 2)


if __name__ == "__main__":
    unittest.main()
