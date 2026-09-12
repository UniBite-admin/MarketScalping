import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from accounting_engine import AccountingDecision
from execution_engine import ExecutionEngine, _build_execution_event_id
from feature_signal_engine import FeatureSignalEngine, StrategyInput
import market_data_engine as market_data_module
from market_data_engine import MarketDataEngine, TickerState
from position_manager import PositionManager
from risk_engine import RiskDecision, RiskEngine
from strategy_engine import StrategyDecision, StrategyEngine


class DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None

    def debug(self, *args, **kwargs):
        return None


def _event_object(**attrs):
    return type("EventObject", (), attrs)()


class RecordingFeatureSignalEngine:
    def __init__(self, *args, **kwargs):
        self.received_event_times = []
        self.latest_strategy_input = None

    def update(self, ticker_state, event_time_utc: str | None = None):
        self.received_event_times.append(event_time_utc)
        timestamp_utc = event_time_utc or datetime.now(timezone.utc).isoformat()
        self.latest_strategy_input = StrategyInput(
            timestamp_utc=timestamp_utc,
            market=ticker_state.market,
            bid=ticker_state.bid,
            ask=ticker_state.ask,
            last=ticker_state.last,
            spread_abs=ticker_state.spread,
            spread_pct=ticker_state.spread_percentage,
            mid_price=ticker_state.mid_price,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )

    def get_latest_strategy_input(self):
        return self.latest_strategy_input


class RecordingStrategyEngine:
    def __init__(self, *args, **kwargs):
        self.received_event_times = []

    def evaluate(self, strategy_input, event_time_utc: str | None = None):
        self.received_event_times.append(event_time_utc)
        timestamp_utc = event_time_utc or strategy_input.timestamp_utc
        return StrategyDecision(
            timestamp_utc=timestamp_utc,
            market=strategy_input.market,
            action="CANDIDATE_TRADE",
            reason="momentum_positive_and_spread_acceptable",
            signal_strength=0.01,
            spread_pct=strategy_input.spread_pct,
            micro_return_1=strategy_input.micro_return_1,
            micro_return_5=strategy_input.micro_return_5,
            tick_interval_ms=strategy_input.tick_interval_ms,
        )


class RecordingRiskEngine:
    def __init__(self, *args, **kwargs):
        self.received_event_times = []

    def evaluate(self, strategy_decision, event_time_utc: str | None = None):
        self.received_event_times.append(event_time_utc)
        timestamp_utc = event_time_utc or strategy_decision.timestamp_utc
        return RiskDecision(
            timestamp_utc=timestamp_utc,
            market=strategy_decision.market,
            strategy_action=strategy_decision.action,
            risk_action="APPROVED_SIMULATION",
            approved=True,
            reason="risk_checks_passed",
            signal_strength=strategy_decision.signal_strength,
            spread_pct=strategy_decision.spread_pct,
            tick_interval_ms=strategy_decision.tick_interval_ms,
            candidates_last_minute=0,
        )


class RecordingExecutionEngine:
    def __init__(self, *args, **kwargs):
        self.received_event_times = []

    def process(self, risk_decision, event_time_utc: str | None = None):
        self.received_event_times.append(event_time_utc)
        timestamp_utc = event_time_utc or risk_decision.timestamp_utc
        return _event_object(
            execution_event_id=f"EXEC-{timestamp_utc}",
            timestamp_utc=timestamp_utc,
            market=risk_decision.market,
            strategy_action=risk_decision.strategy_action,
            risk_action=risk_decision.risk_action,
            execution_action="SIMULATED_ORDER_PREPARED",
            reason="risk_approved_dry_run_only",
            signal_strength=risk_decision.signal_strength,
            spread_pct=risk_decision.spread_pct,
        )


class RecordingPositionManager:
    def __init__(self, *args, **kwargs):
        self.received_event_times = []

    def process_accounting_decision(self, accounting_decision, event_time_utc: str | None = None):
        self.received_event_times.append(event_time_utc)
        timestamp_utc = event_time_utc or datetime.now(timezone.utc).isoformat()
        return _event_object(
            timestamp_utc=timestamp_utc,
            market=getattr(accounting_decision, "market", "BTC-EUR"),
            position_id="SIMPOS-000001",
            lifecycle_action="OPENED",
            status="OPEN",
            hold_events=0,
        )

    def process(self, execution_event, event_time_utc: str | None = None):
        raise RuntimeError("PositionManager raw ExecutionEvent path is disabled; use process_accounting_decision() only.")


class RecordingAccountingEngine:
    def __init__(self, *args, **kwargs):
        self.received_event_times = []
        self.last_decision = AccountingDecision(
            status="ACCEPTED",
            execution_event_id="recording-accounting-decision",
            execution_action="SIMULATED_ORDER_PREPARED",
            reason="recording_accounting_engine_accepts",
            financial_effect_applied=True,
            market="BTC-EUR",
            signal_strength=0.01,
            spread_pct=0.001,
        )

    def process_execution(self, execution_event, bid, ask, timestamp_utc=None, signal=None, confidence=None):
        self.received_event_times.append(timestamp_utc)
        self.last_decision = AccountingDecision(
            status="ACCEPTED",
            execution_event_id=getattr(execution_event, "execution_event_id", "recording-accounting-decision"),
            execution_action=getattr(execution_event, "execution_action", "SIMULATED_ORDER_PREPARED"),
            reason=getattr(execution_event, "reason", "recording_accounting_engine_accepts"),
            financial_effect_applied=True,
            market=getattr(execution_event, "market", "BTC-EUR"),
            signal_strength=getattr(execution_event, "signal_strength", 0.01),
            spread_pct=getattr(execution_event, "spread_pct", 0.001),
        )
        return None


class SafetyAndAccountingAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.logger = DummyLogger()

    def tearDown(self):
        self.tmp.cleanup()

    def _file(self, name: str) -> str:
        return str(self.tmp_path / name)

    def _candidate_decision(self, tick_interval_ms: float = 10.0, spread_pct: float = 0.001, signal_strength: float = 0.01):
        return StrategyDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            action="CANDIDATE_TRADE",
            reason="test_candidate",
            signal_strength=signal_strength,
            spread_pct=spread_pct,
            micro_return_1=0.01,
            micro_return_5=0.01,
            tick_interval_ms=tick_interval_ms,
        )

    def _no_trade_decision(self):
        return StrategyDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            action="NO_TRADE",
            reason="test_no_trade",
            signal_strength=0.0,
            spread_pct=0.001,
            micro_return_1=0.0,
            micro_return_5=0.0,
            tick_interval_ms=10.0,
        )

    def _valid_ticker_state(self):
        return TickerState(market="BTC-EUR", bid=100.0, ask=101.0, last=100.5)

    def _accepted_accounting_decision(
        self,
        execution_event_id: str = "audit-accepted-execution-id",
        execution_action: str = "SIMULATED_ORDER_PREPARED",
        reason: str = "accounting_accepted",
        market: str = "BTC-EUR",
        signal_strength: float = 0.01,
        spread_pct: float = 0.001,
    ):
        return AccountingDecision(
            status="ACCEPTED",
            execution_event_id=execution_event_id,
            execution_action=execution_action,
            reason=reason,
            financial_effect_applied=True,
            market=market,
            signal_strength=signal_strength,
            spread_pct=spread_pct,
        )

    def _market_data_engine_with_recording_pipeline(self) -> MarketDataEngine:
        patches = [
            patch.object(market_data_module, "configure_logging", return_value=self.logger),
            patch.object(market_data_module, "FeatureSignalEngine", RecordingFeatureSignalEngine),
            patch.object(market_data_module, "StrategyEngine", RecordingStrategyEngine),
            patch.object(market_data_module, "RiskEngine", RecordingRiskEngine),
            patch.object(market_data_module, "ExecutionEngine", RecordingExecutionEngine),
            patch.object(market_data_module, "PositionManager", RecordingPositionManager),
            patch.object(market_data_module, "AccountingEngine", RecordingAccountingEngine),
        ]

        for started_patch in patches:
            started_patch.start()
            self.addCleanup(started_patch.stop)

        return MarketDataEngine(
            market="BTC-EUR",
            debug=False,
            feature_output_path=self._file("features.csv"),
            strategy_output_path=self._file("strategy.csv"),
            risk_output_path=self._file("risk.csv"),
            execution_output_path=self._file("execution.csv"),
            position_output_path=self._file("positions.csv"),
            accounting_trade_ledger_path=self._file("trade_ledger.csv"),
            accounting_account_state_path=self._file("account_state.csv"),
            accounting_open_position_state_path=self._file("open_position_state.json"),
        )

    def _risk_decision(
        self,
        timestamp_utc: str = "2026-09-06T00:00:00+00:00",
        market: str = "BTC-EUR",
        strategy_action: str = "CANDIDATE_TRADE",
        risk_action: str = "APPROVED_SIMULATION",
        approved: bool = True,
        reason: str = "risk_checks_passed",
        signal_strength: float = 0.01,
        spread_pct: float = 0.001,
        tick_interval_ms: float | None = 10.0,
        candidates_last_minute: int = 0,
    ) -> RiskDecision:
        return RiskDecision(
            timestamp_utc=timestamp_utc,
            market=market,
            strategy_action=strategy_action,
            risk_action=risk_action,
            approved=approved,
            reason=reason,
            signal_strength=signal_strength,
            spread_pct=spread_pct,
            tick_interval_ms=tick_interval_ms,
            candidates_last_minute=candidates_last_minute,
        )

    def test_feature_engine_blocks_strategy_input_until_core_fields_present(self):
        engine = FeatureSignalEngine(output_path=self._file("features.csv"), logger=self.logger)

        invalid_state = TickerState(market="BTC-EUR", bid=100.0, ask=101.0, last=None)
        engine.update(invalid_state)
        self.assertIsNone(engine.get_latest_strategy_input())

        valid_state = TickerState(market="BTC-EUR", bid=100.0, ask=101.0, last=100.5)
        engine.update(valid_state)
        self.assertIsNotNone(engine.get_latest_strategy_input())

    def test_feature_event_time_identical_inputs_have_identical_timing(self):
        t = "2026-01-01T00:00:00+00:00"

        engine_one = FeatureSignalEngine(output_path=self._file("features_one.csv"), logger=self.logger)
        engine_two = FeatureSignalEngine(output_path=self._file("features_two.csv"), logger=self.logger)

        engine_one.update(self._valid_ticker_state(), event_time_utc=t)
        engine_two.update(self._valid_ticker_state(), event_time_utc=t)

        snap_one = engine_one.get_latest_valid_snapshot()
        snap_two = engine_two.get_latest_valid_snapshot()

        self.assertIsNotNone(snap_one)
        self.assertIsNotNone(snap_two)
        self.assertEqual(snap_one.timestamp_utc, snap_two.timestamp_utc)
        self.assertEqual(snap_one.tick_interval_ms, snap_two.tick_interval_ms)

    def test_feature_event_time_known_interval_sets_expected_tick_interval_ms(self):
        engine = FeatureSignalEngine(output_path=self._file("features.csv"), logger=self.logger)

        engine.update(self._valid_ticker_state(), event_time_utc="2026-01-01T00:00:00+00:00")
        engine.update(self._valid_ticker_state(), event_time_utc="2026-01-01T00:00:01.500000+00:00")

        snap = engine.get_latest_valid_snapshot()
        self.assertIsNotNone(snap)
        self.assertAlmostEqual(snap.tick_interval_ms, 1500.0, places=6)

    def test_feature_event_time_override_uses_historical_not_machine_clock(self):
        engine = FeatureSignalEngine(output_path=self._file("features.csv"), logger=self.logger)

        historical_time = "2001-09-09T01:46:40+00:00"
        engine.update(self._valid_ticker_state(), event_time_utc=historical_time)
        snap = engine.get_latest_valid_snapshot()

        self.assertIsNotNone(snap)
        self.assertEqual(snap.timestamp_utc, historical_time)

        now = datetime.now(timezone.utc)
        snap_dt = datetime.fromisoformat(snap.timestamp_utc.replace("Z", "+00:00"))
        self.assertGreater((now - snap_dt).total_seconds(), 60)

    def test_feature_event_time_malformed_explicit_timestamp_is_invalid_without_fallback(self):
        engine = FeatureSignalEngine(output_path=self._file("features.csv"), logger=self.logger)

        engine.update(self._valid_ticker_state(), event_time_utc="not-a-timestamp")
        self.assertIsNone(engine.get_latest_valid_snapshot())

        with open(self._file("features.csv"), "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["timestamp_utc"], "not-a-timestamp")
        self.assertEqual(row["is_valid"], "False")
        self.assertIn("invalid_event_time_utc", row["validation_errors"])

    def test_feature_engine_live_default_behavior_still_works_without_event_time(self):
        engine = FeatureSignalEngine(output_path=self._file("features.csv"), logger=self.logger)
        engine.update(self._valid_ticker_state())

        snap = engine.get_latest_valid_snapshot()
        self.assertIsNotNone(snap)
        self.assertIsNotNone(datetime.fromisoformat(snap.timestamp_utc.replace("Z", "+00:00")))

    def test_strategy_blocks_stale_ticks(self):
        engine = StrategyEngine(
            output_path=self._file("strategy.csv"),
            logger=self.logger,
            max_spread_pct=0.02,
            max_tick_interval_ms=1000.0,
            min_momentum_return=0.0,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=100.0,
            ask=101.0,
            last=100.5,
            spread_abs=1.0,
            spread_pct=0.01,
            mid_price=100.5,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=5000.0,
        )

        decision = engine.evaluate(strategy_input)
        self.assertEqual(decision.action, "NO_TRADE")
        self.assertIn("stale_tick_interval", decision.reason)

    def test_strategy_uses_historical_event_timestamp(self):
        engine = StrategyEngine(
            output_path=self._file("strategy.csv"),
            logger=self.logger,
            max_spread_pct=0.02,
            max_tick_interval_ms=1000.0,
            min_momentum_return=0.0,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=100.0,
            ask=101.0,
            last=100.5,
            spread_abs=1.0,
            spread_pct=0.01,
            mid_price=100.5,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )

        decision = engine.evaluate(strategy_input, event_time_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(decision.timestamp_utc, "2026-01-01T00:00:00+00:00")

    def test_strategy_same_input_same_historical_timestamp_is_deterministic(self):
        engine = StrategyEngine(
            output_path=self._file("strategy.csv"),
            logger=self.logger,
            max_spread_pct=0.02,
            max_tick_interval_ms=1000.0,
            min_momentum_return=0.0,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=100.0,
            ask=101.0,
            last=100.5,
            spread_abs=1.0,
            spread_pct=0.01,
            mid_price=100.5,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )

        first = engine.evaluate(strategy_input, event_time_utc="2026-01-01T00:00:00+00:00")
        second = engine.evaluate(strategy_input, event_time_utc="2026-01-01T00:00:00+00:00")

        self.assertEqual(first.timestamp_utc, second.timestamp_utc)
        self.assertEqual(first.action, second.action)
        self.assertEqual(first.reason, second.reason)
        self.assertAlmostEqual(first.signal_strength, second.signal_strength, places=12)

    def test_strategy_historical_timestamp_overrides_wall_clock(self):
        engine = StrategyEngine(
            output_path=self._file("strategy.csv"),
            logger=self.logger,
            max_spread_pct=0.02,
            max_tick_interval_ms=1000.0,
            min_momentum_return=0.0,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=100.0,
            ask=101.0,
            last=100.5,
            spread_abs=1.0,
            spread_pct=0.01,
            mid_price=100.5,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )

        decision = engine.evaluate(strategy_input, event_time_utc="2001-09-09T01:46:40+00:00")
        self.assertEqual(decision.timestamp_utc, "2001-09-09T01:46:40+00:00")
        decision_dt = datetime.fromisoformat(decision.timestamp_utc.replace("Z", "+00:00"))
        self.assertGreater((datetime.now(timezone.utc) - decision_dt).total_seconds(), 60)

    def test_strategy_malformed_explicit_timestamp_no_fallback(self):
        engine = StrategyEngine(
            output_path=self._file("strategy.csv"),
            logger=self.logger,
            max_spread_pct=0.02,
            max_tick_interval_ms=1000.0,
            min_momentum_return=0.0,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=100.0,
            ask=101.0,
            last=100.5,
            spread_abs=1.0,
            spread_pct=0.01,
            mid_price=100.5,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )

        decision = engine.evaluate(strategy_input, event_time_utc="not-a-timestamp")
        self.assertEqual(decision.timestamp_utc, "not-a-timestamp")
        self.assertEqual(decision.action, "NO_TRADE")
        self.assertEqual(decision.reason, "invalid_event_time_utc")

    def test_strategy_naive_timestamp_rejected_no_fallback(self):
        engine = StrategyEngine(
            output_path=self._file("strategy.csv"),
            logger=self.logger,
            max_spread_pct=0.02,
            max_tick_interval_ms=1000.0,
            min_momentum_return=0.0,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=100.0,
            ask=101.0,
            last=100.5,
            spread_abs=1.0,
            spread_pct=0.01,
            mid_price=100.5,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )

        decision = engine.evaluate(strategy_input, event_time_utc="2026-01-01T00:00:00")
        self.assertEqual(decision.timestamp_utc, "2026-01-01T00:00:00")
        self.assertEqual(decision.action, "NO_TRADE")
        self.assertEqual(decision.reason, "invalid_event_time_utc")

    def test_strategy_live_default_behavior_still_works_without_event_time(self):
        engine = StrategyEngine(
            output_path=self._file("strategy.csv"),
            logger=self.logger,
            max_spread_pct=0.02,
            max_tick_interval_ms=1000.0,
            min_momentum_return=0.0,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=100.0,
            ask=101.0,
            last=100.5,
            spread_abs=1.0,
            spread_pct=0.01,
            mid_price=100.5,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )

        decision = engine.evaluate(strategy_input)
        self.assertIsNotNone(datetime.fromisoformat(decision.timestamp_utc.replace("Z", "+00:00")))

    def test_strategy_decision_logic_unchanged_with_explicit_valid_time(self):
        engine = StrategyEngine(
            output_path=self._file("strategy.csv"),
            logger=self.logger,
            max_spread_pct=0.02,
            max_tick_interval_ms=1000.0,
            min_momentum_return=0.0,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=100.0,
            ask=101.0,
            last=100.5,
            spread_abs=1.0,
            spread_pct=0.01,
            mid_price=100.5,
            micro_return_1=0.01,
            micro_return_5=0.01,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )

        decision = engine.evaluate(strategy_input, event_time_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(decision.action, "CANDIDATE_TRADE")
        self.assertEqual(decision.reason, "momentum_positive_and_spread_acceptable")

    def test_risk_engine_emergency_stop_overrides_candidate(self):
        engine = RiskEngine(
            output_path=self._file("risk.csv"),
            logger=self.logger,
            enabled=True,
            emergency_stop=True,
        )

        decision = engine.evaluate(self._candidate_decision())
        self.assertFalse(decision.approved)
        self.assertEqual(decision.risk_action, "BLOCKED")
        self.assertIn("emergency_stop", decision.reason)

    def test_risk_engine_blocks_missing_tick_interval(self):
        engine = RiskEngine(output_path=self._file("risk.csv"), logger=self.logger, enabled=True)

        decision = engine.evaluate(self._candidate_decision(tick_interval_ms=None))
        self.assertFalse(decision.approved)
        self.assertEqual(decision.risk_action, "BLOCKED")
        self.assertIn("tick_interval_above_risk_limit", decision.reason)

    def test_risk_engine_rate_limit_can_reject_strategy_candidate(self):
        engine = RiskEngine(
            output_path=self._file("risk.csv"),
            logger=self.logger,
            enabled=True,
            max_candidates_per_minute=1,
        )

        first = engine.evaluate(self._candidate_decision())
        second = engine.evaluate(self._candidate_decision())

        self.assertTrue(first.approved)
        self.assertFalse(second.approved)
        self.assertIn("candidate_rate_limit", second.reason)

    def test_risk_event_time_same_input_produces_same_timestamp(self):
        engine = RiskEngine(output_path=self._file("risk.csv"), logger=self.logger, enabled=True)
        decision = self._candidate_decision()

        first = engine.evaluate(decision, event_time_utc="2026-01-01T00:00:00+00:00")
        second = engine.evaluate(decision, event_time_utc="2026-01-01T00:00:00+00:00")

        self.assertEqual(first.timestamp_utc, "2026-01-01T00:00:00+00:00")
        self.assertEqual(second.timestamp_utc, "2026-01-01T00:00:00+00:00")

    def test_risk_historical_window_uses_event_time_not_machine_clock(self):
        engine = RiskEngine(
            output_path=self._file("risk.csv"),
            logger=self.logger,
            enabled=True,
            max_candidates_per_minute=1,
        )

        first = engine.evaluate(self._candidate_decision(), event_time_utc="2026-01-01T00:00:00+00:00")
        second = engine.evaluate(self._candidate_decision(), event_time_utc="2026-01-01T00:00:30+00:00")

        self.assertTrue(first.approved)
        self.assertFalse(second.approved)
        self.assertIn("candidate_rate_limit", second.reason)

    def test_risk_candidate_older_than_60_seconds_is_outside_window(self):
        engine = RiskEngine(
            output_path=self._file("risk.csv"),
            logger=self.logger,
            enabled=True,
            max_candidates_per_minute=1,
        )

        first = engine.evaluate(self._candidate_decision(), event_time_utc="2026-01-01T00:00:00+00:00")
        second = engine.evaluate(self._candidate_decision(), event_time_utc="2026-01-01T00:01:01+00:00")

        self.assertTrue(first.approved)
        self.assertTrue(second.approved)

    def test_risk_candidate_within_60_seconds_is_rate_limited(self):
        engine = RiskEngine(
            output_path=self._file("risk.csv"),
            logger=self.logger,
            enabled=True,
            max_candidates_per_minute=1,
        )

        first = engine.evaluate(self._candidate_decision(), event_time_utc="2026-01-01T00:00:00+00:00")
        second = engine.evaluate(self._candidate_decision(), event_time_utc="2026-01-01T00:00:59+00:00")

        self.assertTrue(first.approved)
        self.assertFalse(second.approved)
        self.assertIn("candidate_rate_limit", second.reason)

    def test_risk_historical_event_time_overrides_wall_clock(self):
        engine = RiskEngine(output_path=self._file("risk.csv"), logger=self.logger, enabled=True)
        decision = engine.evaluate(self._candidate_decision(), event_time_utc="2001-09-09T01:46:40+00:00")

        self.assertEqual(decision.timestamp_utc, "2001-09-09T01:46:40+00:00")
        decision_dt = datetime.fromisoformat(decision.timestamp_utc.replace("Z", "+00:00"))
        self.assertGreater((datetime.now(timezone.utc) - decision_dt).total_seconds(), 60)

    def test_risk_malformed_explicit_event_time_is_blocked_without_fallback(self):
        engine = RiskEngine(output_path=self._file("risk.csv"), logger=self.logger, enabled=True)
        decision = engine.evaluate(self._candidate_decision(), event_time_utc="not-a-timestamp")

        self.assertFalse(decision.approved)
        self.assertEqual(decision.risk_action, "BLOCKED")
        self.assertEqual(decision.reason, "invalid_event_time_utc")
        self.assertEqual(decision.timestamp_utc, "not-a-timestamp")

    def test_risk_live_default_behavior_still_works_without_event_time(self):
        engine = RiskEngine(output_path=self._file("risk.csv"), logger=self.logger, enabled=True)
        decision = engine.evaluate(self._candidate_decision())

        self.assertIsNotNone(datetime.fromisoformat(decision.timestamp_utc.replace("Z", "+00:00")))

    def test_execution_engine_uses_risk_override(self):
        engine = ExecutionEngine(output_path=self._file("execution.csv"), logger=self.logger, enabled=True)

        blocked = RiskDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            strategy_action="CANDIDATE_TRADE",
            risk_action="BLOCKED",
            approved=False,
            reason="risk_block",
            signal_strength=0.0,
            spread_pct=0.01,
            tick_interval_ms=1.0,
            candidates_last_minute=0,
        )
        approved = RiskDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            strategy_action="CANDIDATE_TRADE",
            risk_action="APPROVED_SIMULATION",
            approved=True,
            reason="risk_ok",
            signal_strength=0.0,
            spread_pct=0.01,
            tick_interval_ms=1.0,
            candidates_last_minute=0,
        )

        blocked_event = engine.process(blocked)
        approved_event = engine.process(approved)

        self.assertEqual(blocked_event.execution_action, "SKIPPED")
        self.assertEqual(approved_event.execution_action, "SIMULATED_ORDER_PREPARED")

    def test_execution_event_uses_explicit_historical_timestamp(self):
        engine = ExecutionEngine(output_path=self._file("execution.csv"), logger=self.logger, enabled=True)
        approved = self._risk_decision(approved=True, risk_action="APPROVED_SIMULATION", reason="risk_checks_passed")

        event = engine.process(approved, event_time_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(event.timestamp_utc, "2026-01-01T00:00:00+00:00")

    def test_execution_event_same_input_same_historical_timestamp_deterministic(self):
        engine = ExecutionEngine(output_path=self._file("execution.csv"), logger=self.logger, enabled=True)
        approved = self._risk_decision(approved=True, risk_action="APPROVED_SIMULATION", reason="risk_checks_passed")

        first = engine.process(approved, event_time_utc="2026-01-01T00:00:00+00:00")
        second = engine.process(approved, event_time_utc="2026-01-01T00:00:00+00:00")

        self.assertEqual(first.timestamp_utc, second.timestamp_utc)
        self.assertEqual(first.execution_action, second.execution_action)
        self.assertEqual(first.reason, second.reason)
        self.assertEqual(first.execution_event_id, second.execution_event_id)

    def test_execution_event_historical_timestamp_overrides_wall_clock(self):
        engine = ExecutionEngine(output_path=self._file("execution.csv"), logger=self.logger, enabled=True)
        approved = self._risk_decision(approved=True, risk_action="APPROVED_SIMULATION", reason="risk_checks_passed")

        event = engine.process(approved, event_time_utc="2001-09-09T01:46:40+00:00")
        self.assertEqual(event.timestamp_utc, "2001-09-09T01:46:40+00:00")

        event_dt = datetime.fromisoformat(event.timestamp_utc.replace("Z", "+00:00"))
        self.assertGreater((datetime.now(timezone.utc) - event_dt).total_seconds(), 60)

    def test_execution_event_malformed_explicit_timestamp_no_fallback(self):
        engine = ExecutionEngine(output_path=self._file("execution.csv"), logger=self.logger, enabled=True)
        approved = self._risk_decision(approved=True, risk_action="APPROVED_SIMULATION", reason="risk_checks_passed")

        event = engine.process(approved, event_time_utc="not-a-timestamp")

        self.assertEqual(event.timestamp_utc, "not-a-timestamp")
        self.assertEqual(event.execution_action, "NO_ACTION")
        self.assertEqual(event.reason, "invalid_event_time_utc")

    def test_execution_engine_live_default_behavior_still_works_without_event_time(self):
        engine = ExecutionEngine(output_path=self._file("execution.csv"), logger=self.logger, enabled=True)
        approved = self._risk_decision(approved=True, risk_action="APPROVED_SIMULATION", reason="risk_checks_passed")

        event = engine.process(approved)
        self.assertIsNotNone(datetime.fromisoformat(event.timestamp_utc.replace("Z", "+00:00")))

    def test_execution_event_id_contract_unchanged_with_explicit_event_time(self):
        engine = ExecutionEngine(output_path=self._file("execution.csv"), logger=self.logger, enabled=True)
        decision = self._risk_decision(approved=True, risk_action="APPROVED_SIMULATION", reason="risk_checks_passed")
        expected_event_id = _build_execution_event_id(decision)

        event = engine.process(decision, event_time_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(event.execution_event_id, expected_event_id)

    def test_execution_event_id_identical_inputs_produce_same_id(self):
        first = self._risk_decision()
        second = self._risk_decision()

        first_id = _build_execution_event_id(first)
        second_id = _build_execution_event_id(second)

        self.assertEqual(first_id, second_id)

    def test_execution_event_id_meaningful_change_produces_different_id(self):
        baseline = self._risk_decision()
        changed = self._risk_decision(reason="risk_checks_passed_with_override")

        baseline_id = _build_execution_event_id(baseline)
        changed_id = _build_execution_event_id(changed)

        self.assertNotEqual(baseline_id, changed_id)

    def test_execution_event_id_is_deterministic_across_repeated_calls(self):
        decision = self._risk_decision(signal_strength=0.123456789)

        ids = [_build_execution_event_id(decision) for _ in range(10)]

        self.assertEqual(len(set(ids)), 1)

    def test_execution_event_id_is_stable_string_for_persistence(self):
        decision = self._risk_decision()
        event_id = _build_execution_event_id(decision)

        self.assertIsInstance(event_id, str)
        self.assertTrue(len(event_id) > 0)
        self.assertEqual(event_id, event_id.strip())

        engine = ExecutionEngine(output_path=self._file("execution.csv"), logger=self.logger, enabled=True)
        event = engine.process(decision)
        self.assertEqual(event.execution_event_id, event_id)

    def test_position_manager_opens_and_closes_by_hold_event_limit(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        open_decision = self._accepted_accounting_decision(execution_event_id="open-decision")
        hold_decision = self._accepted_accounting_decision(execution_event_id="hold-decision")
        close_decision = self._accepted_accounting_decision(execution_event_id="close-decision")

        opened = manager.process_accounting_decision(open_decision)
        held = manager.process_accounting_decision(hold_decision)
        closed = manager.process_accounting_decision(close_decision)

        self.assertEqual(opened.lifecycle_action, "OPENED")
        self.assertEqual(held.lifecycle_action, "HOLD")
        self.assertEqual(closed.lifecycle_action, "CLOSED")

    def test_position_open_uses_historical_event_timestamp(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        opened = manager.process_accounting_decision(
            self._accepted_accounting_decision(execution_event_id="open-historical"),
            event_time_utc="2026-01-01T00:00:00+00:00",
        )

        self.assertIsNotNone(opened)
        self.assertEqual(opened.timestamp_utc, "2026-01-01T00:00:00+00:00")
        self.assertEqual(opened.entry_time_utc, "2026-01-01T00:00:00+00:00")

    def test_position_close_uses_historical_event_timestamp(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=1,
        )

        manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="close-open"), event_time_utc="2026-01-01T00:00:00+00:00")
        closed = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="close-close"), event_time_utc="2026-01-01T00:00:10+00:00")

        self.assertIsNotNone(closed)
        self.assertEqual(closed.timestamp_utc, "2026-01-01T00:00:10+00:00")
        self.assertEqual(closed.close_time_utc, "2026-01-01T00:00:10+00:00")
        self.assertEqual(closed.entry_time_utc, "2026-01-01T00:00:00+00:00")

    def test_position_same_input_same_historical_timestamp_deterministic(self):
        first_manager = PositionManager(
            output_path=self._file("positions_one.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )
        second_manager = PositionManager(
            output_path=self._file("positions_two.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        first_open = first_manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="deterministic-one"), event_time_utc="2026-01-01T00:00:00+00:00")
        second_open = second_manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="deterministic-two"), event_time_utc="2026-01-01T00:00:00+00:00")

        self.assertEqual(first_open.timestamp_utc, second_open.timestamp_utc)
        self.assertEqual(first_open.lifecycle_action, second_open.lifecycle_action)
        self.assertEqual(first_open.status, second_open.status)

    def test_position_historical_time_overrides_wall_clock(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        opened = manager.process_accounting_decision(
            self._accepted_accounting_decision(execution_event_id="historical-time"),
            event_time_utc="2001-09-09T01:46:40+00:00",
        )

        self.assertIsNotNone(opened)
        self.assertEqual(opened.timestamp_utc, "2001-09-09T01:46:40+00:00")
        opened_dt = datetime.fromisoformat(opened.timestamp_utc.replace("Z", "+00:00"))
        self.assertGreater((datetime.now(timezone.utc) - opened_dt).total_seconds(), 60)

    def test_position_malformed_explicit_timestamp_does_not_fallback(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        result = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="bad-timestamp"), event_time_utc="not-a-timestamp")
        self.assertIsNone(result)
        self.assertIsNone(manager._active_position)

        with open(self._file("positions.csv"), "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 0)

    def test_position_live_default_behavior_still_works_without_event_time(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        opened = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="live-default"))
        self.assertIsNotNone(opened)
        self.assertIsNotNone(datetime.fromisoformat(opened.timestamp_utc.replace("Z", "+00:00")))

    def test_position_max_hold_events_behavior_unchanged_with_historical_time(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        opened = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="hold-open"), event_time_utc="2026-01-01T00:00:00+00:00")
        held = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="hold-mid"), event_time_utc="2026-01-01T00:00:01+00:00")
        closed = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="hold-close"), event_time_utc="2026-01-01T00:00:02+00:00")

        self.assertEqual(opened.lifecycle_action, "OPENED")
        self.assertEqual(held.lifecycle_action, "HOLD")
        self.assertEqual(closed.lifecycle_action, "CLOSED")

    def test_position_non_fill_events_do_not_mutate_with_historical_time(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=5,
        )

        opened = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="non-fill-open"), event_time_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(opened.lifecycle_action, "OPENED")

        skipped = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="non-fill-skipped", execution_action="SKIPPED"), event_time_utc="2026-01-01T00:00:01+00:00")
        no_action = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="non-fill-no-action", execution_action="NO_ACTION"), event_time_utc="2026-01-01T00:00:02+00:00")
        failed = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="non-fill-failed", execution_action="FAILED"), event_time_utc="2026-01-01T00:00:03+00:00")

        self.assertIsNone(skipped)
        self.assertIsNone(no_action)
        self.assertIsNone(failed)
        self.assertIsNotNone(manager._active_position)

    def test_position_hold_should_not_advance_on_skipped_execution(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=5,
        )

        opened = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="skip-open"))
        self.assertEqual(opened.lifecycle_action, "OPENED")

        result = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="skip-later", execution_action="SKIPPED"))

        self.assertIsNone(result)

    def test_position_hold_should_not_advance_on_no_action_execution(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=5,
        )

        opened = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="no-action-open"))
        self.assertEqual(opened.lifecycle_action, "OPENED")

        result = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="no-action-later", execution_action="NO_ACTION"))
        self.assertIsNone(result)

    def test_position_hold_should_not_advance_on_risk_rejection(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=5,
        )

        opened = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="risk-open"))
        self.assertEqual(opened.lifecycle_action, "OPENED")

        rejected = AccountingDecision(
            status="REJECTED",
            execution_event_id="risk-rejected",
            execution_action="SIMULATED_ORDER_PREPARED",
            reason="risk_rejected",
            financial_effect_applied=False,
            market="BTC-EUR",
            signal_strength=0.01,
            spread_pct=0.001,
        )
        result = manager.process_accounting_decision(rejected)
        self.assertIsNone(result)

    def test_position_hold_should_not_advance_on_failed_execution(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=5,
        )

        opened = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="failed-open"))
        self.assertEqual(opened.lifecycle_action, "OPENED")

        failed = AccountingDecision(
            status="FAILED",
            execution_event_id="failed-later",
            execution_action="SIMULATED_ORDER_PREPARED",
            reason="execution_failed",
            financial_effect_applied=False,
            market="BTC-EUR",
            signal_strength=0.01,
            spread_pct=0.001,
        )
        result = manager.process_accounting_decision(failed)
        self.assertIsNone(result)

    def test_closed_position_not_mutated_by_later_non_fill_events(self):
        manager = PositionManager(
            output_path=self._file("positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=1,
        )

        opened = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="closed-open"))
        closed = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="closed-close"))

        self.assertEqual(opened.lifecycle_action, "OPENED")
        self.assertEqual(closed.lifecycle_action, "CLOSED")
        self.assertIsNone(manager._active_position)

        skipped_after_close = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="after-close-skipped", execution_action="SKIPPED"))
        no_action_after_close = manager.process_accounting_decision(self._accepted_accounting_decision(execution_event_id="after-close-no-action", execution_action="NO_ACTION"))
        rejected_after_close = manager.process_accounting_decision(AccountingDecision(status="REJECTED", execution_event_id="after-close-rejected", execution_action="SIMULATED_ORDER_PREPARED", reason="rejected", financial_effect_applied=False, market="BTC-EUR", signal_strength=0.01, spread_pct=0.001))
        failed_after_close = manager.process_accounting_decision(AccountingDecision(status="FAILED", execution_event_id="after-close-failed", execution_action="SIMULATED_ORDER_PREPARED", reason="failed", financial_effect_applied=False, market="BTC-EUR", signal_strength=0.01, spread_pct=0.001))

        self.assertIsNone(skipped_after_close)
        self.assertIsNone(no_action_after_close)
        self.assertIsNone(rejected_after_close)
        self.assertIsNone(failed_after_close)
        self.assertIsNone(manager._active_position)

    def test_market_data_pipeline_uses_same_historical_timestamp_end_to_end(self):
        engine = self._market_data_engine_with_recording_pipeline()
        payload = {
            "event": "ticker",
            "market": "BTC-EUR",
            "bestBid": 100.0,
            "bestAsk": 101.0,
            "lastPrice": 100.5,
            "timestamp": "2025-01-01T12:00:00Z",
        }

        engine.handle_control_message(payload)

        canonical = "2025-01-01T12:00:00+00:00"
        self.assertEqual(engine.feature_engine.received_event_times, [canonical])
        self.assertEqual(engine.strategy_engine.received_event_times, [canonical])
        self.assertEqual(engine.risk_engine.received_event_times, [canonical])
        self.assertEqual(engine.execution_engine.received_event_times, [canonical])
        self.assertEqual(engine.position_manager.received_event_times, [canonical])
        self.assertEqual(engine.accounting_engine.received_event_times, [canonical])

    def test_market_data_pipeline_reuses_live_timestamp_when_no_explicit_timestamp_is_supplied(self):
        engine = self._market_data_engine_with_recording_pipeline()
        payload = {
            "event": "trade",
            "market": "BTC-EUR",
            "price": 100.5,
        }

        engine.handle_control_message(payload)

        self.assertEqual(len(engine.feature_engine.received_event_times), 1)
        canonical = engine.feature_engine.received_event_times[0]
        self.assertIsNotNone(datetime.fromisoformat(canonical.replace("Z", "+00:00")))
        self.assertEqual(engine.strategy_engine.received_event_times, [canonical])
        self.assertEqual(engine.risk_engine.received_event_times, [canonical])
        self.assertEqual(engine.execution_engine.received_event_times, [canonical])
        self.assertEqual(engine.position_manager.received_event_times, [canonical])
        self.assertEqual(engine.accounting_engine.received_event_times, [canonical])

    def test_market_data_pipeline_rejects_invalid_explicit_timestamp_without_wall_clock_fallback(self):
        engine = self._market_data_engine_with_recording_pipeline()
        payload = {
            "event": "ticker",
            "market": "BTC-EUR",
            "bestBid": 100.0,
            "bestAsk": 101.0,
            "lastPrice": 100.5,
        }

        engine.handle_control_message(payload, event_time_utc="2025-01-01T12:00:00")

        self.assertEqual(engine.feature_engine.received_event_times, [])
        self.assertEqual(engine.strategy_engine.received_event_times, [])
        self.assertEqual(engine.risk_engine.received_event_times, [])
        self.assertEqual(engine.execution_engine.received_event_times, [])
        self.assertEqual(engine.position_manager.received_event_times, [])
        self.assertEqual(engine.accounting_engine.received_event_times, [])
        self.assertIn("invalid", engine.last_error.lower())

    def test_recovery_lifecycle_valid_state_reaches_ready(self):
        engine = MarketDataEngine(
            feature_output_path=self._file("features.csv"),
            strategy_output_path=self._file("strategy.csv"),
            risk_output_path=self._file("risk.csv"),
            execution_output_path=self._file("execution.csv"),
            position_output_path=self._file("positions.csv"),
            accounting_trade_ledger_path=self._file("trade_ledger.csv"),
            accounting_account_state_path=self._file("account_state.csv"),
            accounting_open_position_state_path=self._file("open_position_state.json"),
        )

        self.assertEqual(engine.recovery_status, "READY")

    def test_recovery_lifecycle_is_deterministic_and_idempotent(self):
        engine = MarketDataEngine(
            feature_output_path=self._file("features.csv"),
            strategy_output_path=self._file("strategy.csv"),
            risk_output_path=self._file("risk.csv"),
            execution_output_path=self._file("execution.csv"),
            position_output_path=self._file("positions.csv"),
            accounting_trade_ledger_path=self._file("trade_ledger.csv"),
            accounting_account_state_path=self._file("account_state.csv"),
            accounting_open_position_state_path=self._file("open_position_state.json"),
        )

        first = engine.run_startup_recovery()
        second = engine.run_startup_recovery()

        self.assertEqual(first, "READY")
        self.assertEqual(second, "READY")
        self.assertEqual(engine.recovery_status, "READY")

    def test_blocked_accounting_state_blocks_market_processing(self):
        checkpoint_path = self.tmp_path / "blocked_open_state.json"
        checkpoint_path.write_text('{"version": 1, "timestamp_utc": "2026-09-06T00:00:00+00:00", "processed_successful_execution_ids": [123], "account_state": {"starting_balance": 1000.0, "available_balance": 800.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0, "equity": 800.0, "cumulative_fees": 0.0, "cumulative_slippage": 0.0, "peak_equity": 1000.0, "current_drawdown": 0.0, "maximum_drawdown": 0.0}, "counters": {"trade_counter": 1, "order_counter": 1, "fill_counter": 1}, "last_mark_price": 100.0, "open_position": null}', encoding="utf-8")

        engine = MarketDataEngine(
            feature_output_path=self._file("features.csv"),
            strategy_output_path=self._file("strategy.csv"),
            risk_output_path=self._file("risk.csv"),
            execution_output_path=self._file("execution.csv"),
            position_output_path=self._file("positions.csv"),
            accounting_trade_ledger_path=self._file("trade_ledger.csv"),
            accounting_account_state_path=self._file("account_state.csv"),
            accounting_open_position_state_path=str(checkpoint_path),
        )

        self.assertEqual(engine.recovery_status, "BLOCKED_ON_DIVERGENCE")
        payload = {"event": "ticker", "market": "BTC-EUR", "bestBid": 100.0, "bestAsk": 101.0, "lastPrice": 100.5}

        with patch.object(engine, "update_features") as mock_features, patch.object(engine, "update_strategy") as mock_strategy, patch.object(engine, "update_risk") as mock_risk, patch.object(engine, "update_execution") as mock_execution:
            engine.handle_control_message(payload)

        mock_features.assert_not_called()
        mock_strategy.assert_not_called()
        mock_risk.assert_not_called()
        mock_execution.assert_not_called()


class ExecutionEventFactory:
    @staticmethod
    def approved():
        return type("ExecutionEventObj", (), {
            "timestamp_utc": "2026-09-06T00:00:00+00:00",
            "market": "BTC-EUR",
            "strategy_action": "CANDIDATE_TRADE",
            "risk_action": "APPROVED_SIMULATION",
            "execution_action": "SIMULATED_ORDER_PREPARED",
            "reason": "risk_approved_dry_run_only",
            "signal_strength": 0.01,
            "spread_pct": 0.001,
        })()

    @staticmethod
    def skipped():
        return type("ExecutionEventObj", (), {
            "timestamp_utc": "2026-09-06T00:00:00+00:00",
            "market": "BTC-EUR",
            "strategy_action": "NO_TRADE",
            "risk_action": "NO_ACTION",
            "execution_action": "SKIPPED",
            "reason": "no_strategy_candidate",
            "signal_strength": 0.0,
            "spread_pct": 0.001,
        })()

    @staticmethod
    def no_action():
        return type("ExecutionEventObj", (), {
            "timestamp_utc": "2026-09-06T00:00:00+00:00",
            "market": "BTC-EUR",
            "strategy_action": "NO_TRADE",
            "risk_action": "NO_ACTION",
            "execution_action": "NO_ACTION",
            "reason": "risk_engine_disabled",
            "signal_strength": 0.0,
            "spread_pct": 0.001,
        })()

    @staticmethod
    def risk_rejected():
        return type("ExecutionEventObj", (), {
            "timestamp_utc": "2026-09-06T00:00:00+00:00",
            "market": "BTC-EUR",
            "strategy_action": "CANDIDATE_TRADE",
            "risk_action": "BLOCKED",
            "execution_action": "SKIPPED",
            "reason": "spread_above_risk_limit",
            "signal_strength": 0.0,
            "spread_pct": 0.5,
        })()

    @staticmethod
    def failed():
        return type("ExecutionEventObj", (), {
            "timestamp_utc": "2026-09-06T00:00:00+00:00",
            "market": "BTC-EUR",
            "strategy_action": "CANDIDATE_TRADE",
            "risk_action": "APPROVED_SIMULATION",
            "execution_action": "FAILED",
            "reason": "simulated_order_failed",
            "signal_strength": 0.01,
            "spread_pct": 0.001,
        })()


if __name__ == "__main__":
    unittest.main()
