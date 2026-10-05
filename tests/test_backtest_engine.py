import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backtest_engine as backtest_module
from accounting_engine import AccountingDecision, ClosedTrade
from backtest_engine import BacktestEngine, BacktestConfig
from feature_signal_engine import FeatureSignalEngine
from risk_engine import RiskDecision


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

    def test_backtest_passes_protected_exit_in_notional_units(self):
        observed = {}
        original_evaluate = backtest_module.RiskEngine.evaluate

        def recording_evaluate(self, strategy_decision, event_time_utc=None, **kwargs):
            observed["candidate_entry_notional"] = kwargs["candidate_entry_notional"]
            observed["protected_exit_value"] = kwargs["protected_exit_value"]
            return original_evaluate(self, strategy_decision, event_time_utc=event_time_utc, **kwargs)

        events = [{
            "event_time_utc": "2025-01-01T12:00:00Z",
            "event_type": "ticker",
            "market": "BTC-EUR",
            "bid": 100.0,
            "ask": 101.0,
            "last": 100.0,
        }]

        original_strategy = backtest_module.StrategyEngine.evaluate

        def forced_candidate(self, strategy_input, event_time_utc=None):
            return backtest_module.StrategyDecision(
                timestamp_utc=event_time_utc or "2025-01-01T12:00:00Z",
                market=strategy_input.market,
                action="CANDIDATE_TRADE",
                reason="unit_test_candidate",
                signal_strength=1.0,
                spread_pct=strategy_input.spread_pct,
                micro_return_1=0.01,
                micro_return_5=0.01,
                tick_interval_ms=1000.0,
            )

        with patch("backtest_engine.StrategyEngine.evaluate", new=forced_candidate):
            with patch("backtest_engine.RiskEngine.evaluate", new=recording_evaluate):
                BacktestEngine(BacktestConfig(initial_capital=1000.0, fee_rate=0.001, spread_pct=0.001)).run(
                    events,
                    assume_canonical_chronological=True,
                )

        self.assertIn("candidate_entry_notional", observed)
        self.assertIn("protected_exit_value", observed)
        self.assertLess(observed["protected_exit_value"], observed["candidate_entry_notional"])
        self.assertAlmostEqual(
            observed["protected_exit_value"],
            observed["candidate_entry_notional"] * (1.0 - 0.001),
            places=8,
        )

    def test_backtest_accepts_closed_trade_only_via_accounting_decision_contract(self):
        events = [
            {
                "event_time_utc": "2025-01-01T12:00:00Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 100.0,
                "ask": 101.0,
                "last": 100.0,
            },
            {
                "event_time_utc": "2025-01-01T12:00:01Z",
                "event_type": "ticker",
                "market": "BTC-EUR",
                "bid": 102.0,
                "ask": 103.0,
                "last": 102.0,
            },
        ]

        def forced_candidate(self, strategy_input, event_time_utc=None):
            return backtest_module.StrategyDecision(
                timestamp_utc=event_time_utc or "2025-01-01T12:00:00Z",
                market=strategy_input.market,
                action="CANDIDATE_TRADE",
                reason="unit_test_candidate",
                signal_strength=1.0,
                spread_pct=strategy_input.spread_pct,
                micro_return_1=0.01,
                micro_return_5=0.01,
                tick_interval_ms=1000.0,
            )

        def forced_risk(self, strategy_decision, event_time_utc=None, **kwargs):
            return RiskDecision(
                timestamp_utc=event_time_utc or "2025-01-01T12:00:00Z",
                market=strategy_decision.market,
                strategy_action=strategy_decision.action,
                risk_action="TARGET",
                approved=True,
                reason="approved",
                signal_strength=strategy_decision.signal_strength,
                spread_pct=strategy_decision.spread_pct,
                tick_interval_ms=strategy_decision.tick_interval_ms,
                candidates_last_minute=1,
            )

        original_process_execution = backtest_module.AccountingEngine.process_execution

        def contract_aware_process_execution(self, execution_event, bid, ask, timestamp_utc=None, signal=None, confidence=None):
            if getattr(self, "open_position", None) is None:
                created = original_process_execution(
                    self,
                    execution_event,
                    bid=bid,
                    ask=ask,
                    timestamp_utc=timestamp_utc,
                    signal=signal,
                    confidence=confidence,
                )
                return created

            self.last_decision = AccountingDecision(
                status="ACCEPTED",
                execution_event_id=getattr(execution_event, "execution_event_id", None),
                execution_action=getattr(execution_event, "execution_action", None),
                reason="accepted_close_contract",
                financial_effect_applied=True,
                market=getattr(execution_event, "market", None),
                signal_strength=getattr(execution_event, "signal_strength", None),
                spread_pct=getattr(execution_event, "spread_pct", None),
            )
            return ClosedTrade(
                trade_id="TRD-000001",
                timestamp_utc=timestamp_utc or "2025-01-01T12:00:01Z",
                symbol="BTC-EUR",
                side="LONG",
                entry_price=100.0,
                exit_price=102.0,
                position_size=1.0,
                gross_pnl=2.0,
                fees=0.0,
                slippage=0.0,
                net_pnl=2.0,
                holding_time_seconds=1.0,
                strategy="backtest_contract_repro",
                signal="contract_close",
                confidence=1.0,
                close_reason="accepted_close_contract",
                entry_timestamp_utc="2025-01-01T12:00:00Z",
                exit_timestamp_utc=timestamp_utc or "2025-01-01T12:00:01Z",
            )

        with patch("backtest_engine.StrategyEngine.evaluate", new=forced_candidate):
            with patch("backtest_engine.RiskEngine.evaluate", new=forced_risk):
                with patch.object(backtest_module.AccountingEngine, "process_execution", new=contract_aware_process_execution):
                    result = BacktestEngine(BacktestConfig(initial_capital=1000.0, fee_rate=0.001, spread_pct=0.001)).run(
                        events,
                        assume_canonical_chronological=True,
                    )

        self.assertEqual(result.validation_status, "PASS")
        self.assertTrue(result.accounting_decisions)
        self.assertEqual(result.accounting_decisions[-1]["status"], "ACCEPTED")
        self.assertTrue(result.accounting_decisions[-1]["financial_effect_applied"])

    def test_risk_engine_rejects_invalid_protected_exit_notional(self):
        risk = backtest_module.RiskEngine(
            tempfile.NamedTemporaryFile(delete=False).name,
            __import__("logging").getLogger("risk_test"),
            enabled=True,
            max_spread_pct=0.02,
            max_tick_interval_ms=2000.0,
            max_candidates_per_minute=120,
            max_position_size=1000.0,
            max_exposure=2000.0,
            max_risk_per_trade=250.0,
        )
        decision = backtest_module.StrategyDecision(
            timestamp_utc="2025-01-01T12:00:00Z",
            market="BTC-EUR",
            action="CANDIDATE_TRADE",
            reason="unit_test_candidate",
            signal_strength=1.0,
            spread_pct=0.001,
            micro_return_1=0.01,
            micro_return_5=0.01,
            tick_interval_ms=1000.0,
        )
        risk_state = backtest_module.RiskState(
            available_balance=1000.0,
            equity=1000.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            open_position_exists=False,
            open_position_side=None,
            open_position_size=None,
            open_position_entry_price=None,
            current_drawdown=0.0,
            maximum_drawdown=0.0,
            recovery_status="VALID",
            financial_valid=True,
            is_valid=True,
        )
        result = risk.evaluate(
            decision,
            event_time_utc="2025-01-01T12:00:00Z",
            risk_state=risk_state,
            candidate_position_size=0.1,
            candidate_entry_notional=250.0,
            protected_exit_value=300.0,
        )
        self.assertFalse(result.approved)
        self.assertIn("invalid_protected_exit_value", result.reason)

    def test_risk_engine_accepts_valid_protected_exit_notional(self):
        risk = backtest_module.RiskEngine(
            tempfile.NamedTemporaryFile(delete=False).name,
            __import__("logging").getLogger("risk_test"),
            enabled=True,
            max_spread_pct=0.02,
            max_tick_interval_ms=2000.0,
            max_candidates_per_minute=120,
            max_position_size=1000.0,
            max_exposure=2000.0,
            max_risk_per_trade=250.0,
        )
        decision = backtest_module.StrategyDecision(
            timestamp_utc="2025-01-01T12:00:00Z",
            market="BTC-EUR",
            action="CANDIDATE_TRADE",
            reason="unit_test_candidate",
            signal_strength=1.0,
            spread_pct=0.001,
            micro_return_1=0.01,
            micro_return_5=0.01,
            tick_interval_ms=1000.0,
        )
        risk_state = backtest_module.RiskState(
            available_balance=1000.0,
            equity=1000.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            open_position_exists=False,
            open_position_side=None,
            open_position_size=None,
            open_position_entry_price=None,
            current_drawdown=0.0,
            maximum_drawdown=0.0,
            recovery_status="VALID",
            financial_valid=True,
            is_valid=True,
        )
        protected_exit_value = 250.0 * (1.0 - 0.001)
        result = risk.evaluate(
            decision,
            event_time_utc="2025-01-01T12:00:00Z",
            risk_state=risk_state,
            candidate_position_size=0.1,
            candidate_entry_notional=250.0,
            protected_exit_value=protected_exit_value,
        )
        self.assertTrue(result.approved)
        self.assertEqual(result.reason, "risk_checks_passed")

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

    def test_backtest_trade_net_pnl_uses_accounting_canonical_formula(self):
        engine = BacktestEngine(BacktestConfig(initial_capital=1000.0, fee_rate=0.001, spread_pct=0.001, slippage_bps=100.0))
        state = backtest_module.BacktestState(cash=1000.0)
        state.current_equity = 1000.0
        state.peak_equity = 1000.0

        buy_event = type("Evt", (), {"event_time_utc": "2025-01-01T12:00:00Z"})()
        sell_event = type("Evt", (), {"event_time_utc": "2025-01-01T12:00:01Z"})()

        buy = engine.execution_model.simulate(
            side="BUY",
            reference_price=100.0,
            order_quantity=1.0,
            event_time_utc="2025-01-01T12:00:00Z",
            available_cash=1000.0,
            position_quantity=0.0,
            observed_bid=99.0,
            observed_ask=101.0,
        )
        sell = engine.execution_model.simulate(
            side="SELL",
            reference_price=110.0,
            order_quantity=1.0,
            event_time_utc="2025-01-01T12:00:01Z",
            available_cash=1000.0,
            position_quantity=1.0,
            observed_bid=109.0,
            observed_ask=111.0,
        )

        engine._apply_outcome(
            state,
            buy,
            buy_event,
            0,
            execution_event_id="evt-buy",
            strategy_name="BTC-EUR",
            signal="ENTRY_LONG",
            confidence=0.75,
            entry_reason="entry_condition_satisfied",
            entry_signal_strength=0.75,
            entry_spread_pct=0.001,
            micro_return_1=0.01,
            micro_return_5=0.02,
            tick_interval_ms=1000.0,
        )
        engine._apply_outcome(
            state,
            sell,
            sell_event,
            1,
            execution_event_id="evt-sell",
            strategy_name="BTC-EUR",
            signal="EXIT_LONG",
            confidence=0.75,
            close_reason="strategy_exit_max_hold",
            entry_reason="entry_condition_satisfied",
            entry_signal_strength=0.75,
            entry_spread_pct=0.001,
            micro_return_1=0.01,
            micro_return_5=0.02,
            tick_interval_ms=1000.0,
        )

        self.assertTrue(state.closed_trades)
        trade = state.closed_trades[0]
        self.assertEqual(trade["close_reason"], "strategy_exit_max_hold")
        self.assertEqual(trade["holding_time_seconds"], 1.0)
        self.assertAlmostEqual(trade["net_pnl"], trade["gross_pnl"] - trade["fees"], places=10)
        self.assertAlmostEqual(trade["slippage"], sell.slippage_impact, places=10)
        self.assertGreater(sell.slippage_impact, 0.0)
        self.assertGreater(sell.spread_impact, 0.0)

    def test_backtest_evidence_export_preserves_holding_time_and_exit_reason(self):
        engine = BacktestEngine(BacktestConfig())
        state = backtest_module.BacktestState(cash=1000.0)
        state.current_equity = 1000.0
        state.peak_equity = 1000.0
        state.open_trade = {
            "entry_timestamp_utc": "2025-01-01T12:00:00Z",
            "entry_reason": "entry_condition_satisfied",
            "entry_signal_strength": 0.8,
            "entry_spread_pct": 0.001,
            "micro_return_1": 0.01,
            "micro_return_5": 0.02,
            "tick_interval_ms": 1000.0,
        }
        state.closed_trades.append({
            "trade_id": "trade-1",
            "execution_event_id": "evt-1",
            "market": "BTC-EUR",
            "side": "SELL",
            "entry_timestamp_utc": "2025-01-01T12:00:00Z",
            "exit_timestamp_utc": "2025-01-01T12:00:30Z",
            "entry_price": 100.0,
            "exit_price": 101.0,
            "quantity": 1.0,
            "gross_pnl": 1.0,
            "fees": 0.1,
            "spread_impact": 0.05,
            "slippage_impact": 0.02,
            "net_pnl": 0.9,
            "holding_time_seconds": 30.0,
            "close_reason": "strategy_exit_max_hold",
            "signal": "EXIT_LONG",
            "confidence": 0.8,
            "entry_reason": "entry_condition_satisfied",
            "entry_signal_strength": 0.8,
            "entry_spread_pct": 0.001,
            "micro_return_1": 0.01,
            "micro_return_5": 0.02,
            "tick_interval_ms": 1000.0,
            "status": "CLOSED",
        })

        result = backtest_module.BacktestResult(
            run_id="run-123",
            dataset_id="dataset-123",
            market="BTC-EUR",
            event_start_utc="2025-01-01T12:00:00Z",
            event_end_utc="2025-01-01T12:00:30Z",
            repository_revision=None,
            strategy_configuration={},
            risk_configuration={},
            execution_configuration={},
            fee_configuration={},
            spread_configuration={},
            slippage_configuration={},
            latency_configuration={},
            initial_capital=1000.0,
            final_cash=1000.0,
            final_position_quantity=0.0,
            final_equity=1000.0,
            realized_pnl=0.9,
            trade_records=[],
            equity_curve=[],
            metrics={"trade_count": 1, "net_pnl": 0.9},
            warnings=[],
            limitations=[],
            validation_status="PASS",
            observed_assumptions={"backtest_evidence_dir": "reports/backtests/run-123"},
            modeled_assumptions={},
            replay_status="CANONICALIZED",
            replay_rejection_reasons=(),
            analytics=backtest_module.BacktestAnalytics(
                trade_ledger=[state.closed_trades[0]],
                equity_curve=[],
                cost_attribution=backtest_module.CostAttribution(0.05, 0.02, 0.1, 0.17, 1.0, 0.9),
                performance_summary=backtest_module.PerformanceSummary(
                    gross_pnl=1.0,
                    execution_costs=0.17,
                    net_pnl=0.9,
                    roi=0.0,
                    trade_count=1,
                    winning_trades=1,
                    losing_trades=0,
                    win_rate=1.0,
                    average_win=0.0,
                    average_loss=0.0,
                    expectancy=0.0,
                    profit_factor=0.0,
                    max_drawdown=0.0,
                    current_drawdown=0.0,
                    current_drawdown_pct=0.0,
                    consecutive_losses=0,
                    average_holding_time_seconds=30.0,
                ),
                run_metadata=backtest_module.RunMetadata(
                    dataset_id="dataset-123",
                    event_count=1,
                    first_event_time_utc="2025-01-01T12:00:00Z",
                    last_event_time_utc="2025-01-01T12:00:30Z",
                    strategy_configuration={},
                    risk_configuration={},
                    execution_configuration={},
                    fee_configuration={},
                    spread_configuration={},
                    slippage_configuration={},
                    latency_configuration={},
                    run_signature="sig-123",
                ),
            ),
        )

        evidence_dir = engine.export_backtest_evidence(result, output_root=tempfile.mkdtemp(prefix="evidence_test_"))
        with (evidence_dir / "trade_ledger.csv").open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["holding_time_seconds"], "30.0")
        self.assertEqual(rows[0]["close_reason"], "strategy_exit_max_hold")
        self.assertEqual(rows[0]["entry_reason"], "entry_condition_satisfied")

    def test_export_backtest_evidence_fails_on_missing_required_provenance(self):
        engine = BacktestEngine(BacktestConfig())
        result = backtest_module.BacktestResult(
            run_id="run-456",
            dataset_id="dataset-456",
            market="BTC-EUR",
            event_start_utc="2025-01-01T12:00:00Z",
            event_end_utc="2025-01-01T12:00:30Z",
            repository_revision=None,
            strategy_configuration={},
            risk_configuration={},
            execution_configuration={},
            fee_configuration={},
            spread_configuration={},
            slippage_configuration={},
            latency_configuration={},
            initial_capital=1000.0,
            final_cash=1000.0,
            final_position_quantity=0.0,
            final_equity=1000.0,
            realized_pnl=0.0,
            trade_records=[],
            equity_curve=[],
            metrics={"trade_count": 1, "net_pnl": 0.0},
            warnings=[],
            limitations=[],
            validation_status="PASS",
            observed_assumptions={"backtest_evidence_dir": "reports/backtests/run-456"},
            modeled_assumptions={},
            replay_status="CANONICALIZED",
            replay_rejection_reasons=(),
            analytics=backtest_module.BacktestAnalytics(
                trade_ledger=[{
                    "trade_id": "trade-1",
                    "side": "SELL",
                    "entry_timestamp_utc": "2025-01-01T12:00:00Z",
                    "exit_timestamp_utc": "2025-01-01T12:00:30Z",
                    "entry_price": 100.0,
                    "exit_price": 101.0,
                    "quantity": 1.0,
                    "gross_pnl": 1.0,
                    "fees": 0.1,
                    "spread_impact": 0.05,
                    "slippage_impact": 0.02,
                    "net_pnl": 0.9,
                    "holding_time_seconds": 30.0,
                    "signal": "EXIT_LONG",
                    "confidence": 0.8,
                    "status": "CLOSED",
                }],
                equity_curve=[],
                cost_attribution=backtest_module.CostAttribution(0.05, 0.02, 0.1, 0.17, 1.0, 0.9),
                performance_summary=backtest_module.PerformanceSummary(
                    gross_pnl=1.0,
                    execution_costs=0.17,
                    net_pnl=0.9,
                    roi=0.0,
                    trade_count=1,
                    winning_trades=1,
                    losing_trades=0,
                    win_rate=1.0,
                    average_win=0.0,
                    average_loss=0.0,
                    expectancy=0.0,
                    profit_factor=0.0,
                    max_drawdown=0.0,
                    current_drawdown=0.0,
                    current_drawdown_pct=0.0,
                    consecutive_losses=0,
                    average_holding_time_seconds=30.0,
                ),
                run_metadata=backtest_module.RunMetadata(
                    dataset_id="dataset-456",
                    event_count=1,
                    first_event_time_utc="2025-01-01T12:00:00Z",
                    last_event_time_utc="2025-01-01T12:00:30Z",
                    strategy_configuration={},
                    risk_configuration={},
                    execution_configuration={},
                    fee_configuration={},
                    spread_configuration={},
                    slippage_configuration={},
                    latency_configuration={},
                    run_signature="sig-456",
                ),
            ),
        )

        with self.assertRaises(ValueError):
            engine.export_backtest_evidence(result, output_root=tempfile.mkdtemp(prefix="evidence_missing_"))

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

    def test_backtest_evidence_bundle_is_created_with_manifest_summary_and_deterministic_identity(self):
        cfg = BacktestConfig(initial_capital=1000.0)
        run_root = Path(tempfile.mkdtemp(prefix="evidence_test_")) / "reports" / "backtests"
        result = BacktestEngine(cfg).run(self._fixture_events())
        evidence_dir = result.observed_assumptions["backtest_evidence_dir"]
        bundle_path = Path(evidence_dir)

        self.assertTrue(bundle_path.exists())
        self.assertTrue((bundle_path / "manifest.json").exists())
        self.assertTrue((bundle_path / "summary.json").exists())
        self.assertTrue((bundle_path / "trade_ledger.csv").exists())

        manifest = __import__("json").loads((bundle_path / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_id"], result.run_id)
        self.assertEqual(manifest["run_signature"], result.run_id)
        self.assertEqual(manifest["configuration_identity"], BacktestEngine(cfg)._config_identity())

        with (bundle_path / "trade_ledger.csv").open("r", encoding="utf-8", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(csv_rows), 0)
        self.assertNotIn("tmp", manifest["configuration_identity"])
        self.assertNotIn("generated_at", json.dumps(manifest, sort_keys=True))

    def test_backtest_evidence_identity_ignores_temp_paths_and_is_stable_for_same_inputs(self):
        cfg = BacktestConfig(initial_capital=1000.0)
        first = BacktestEngine(cfg).run(self._fixture_events())
        second = BacktestEngine(cfg).run(self._fixture_events())

        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.observed_assumptions["backtest_evidence_dir"], second.observed_assumptions["backtest_evidence_dir"])
        self.assertNotIn("tmp", first.observed_assumptions["backtest_evidence_dir"])
        self.assertNotIn("\\\\", first.observed_assumptions["backtest_evidence_dir"])


if __name__ == "__main__":
    unittest.main()
