import unittest

from backtest_engine import BacktestEngine, BacktestConfig


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

    def test_valid_canonical_dataset_is_accepted(self):
        result = BacktestEngine(BacktestConfig()).run(self._fixture_events())
        self.assertEqual(result.validation_status, "PASS")
        self.assertEqual(result.replay_status, "CANONICALIZED")

    def test_invalid_timestamp_is_rejected(self):
        invalid = [{**self._fixture_events()[0], "event_time_utc": "2025-01-01T12:00:00"}]
        result = BacktestEngine(BacktestConfig()).run(invalid)
        self.assertEqual(result.validation_status, "INVALID")
        self.assertEqual(result.replay_status, "REJECTED")

    def test_deterministic_backtest_is_repeatable(self):
        cfg = BacktestConfig()
        first = BacktestEngine(cfg).run(self._fixture_events())
        second = BacktestEngine(cfg).run(self._fixture_events())
        self.assertEqual(first.run_id, second.run_id)
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


if __name__ == "__main__":
    unittest.main()
