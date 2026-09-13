import tempfile
import unittest
from pathlib import Path

from accounting_engine import AccountingEngine
from feature_signal_engine import StrategyInput
from risk_engine import RiskDecision, RiskEngine
from strategy_engine import StrategyDecision


class DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class ExecutionEventObj:
    def __init__(
        self,
        action: str,
        reason: str = "risk_approved_dry_run_only",
        execution_event_id: str | None = None,
        market: str = "BTC-EUR",
        signal_strength: float = 0.0,
        spread_pct: float = 0.0,
    ):
        self.execution_action = action
        self.reason = reason
        self.market = market
        self.execution_event_id = execution_event_id
        self.signal_strength = signal_strength
        self.spread_pct = spread_pct


class RiskStateContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.logger = DummyLogger()

    def tearDown(self):
        self.tmp.cleanup()

    def _engine(self, starting_balance=10000.0, fee_rate=0.0, slippage_bps=0.0, order_notional_eur=1000.0):
        return AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(self.tmp_path / "open_position_state.json"),
            logger=self.logger,
            enabled=True,
            strategy_name="baseline",
            starting_balance=starting_balance,
            order_notional_eur=order_notional_eur,
            fee_rate=fee_rate,
            slippage_bps=slippage_bps,
        )

    def _open_position(self, engine, ask=100.0, bid=99.0, timestamp_utc="2026-09-06T00:00:00+00:00"):
        engine.process_execution(
            execution_event=ExecutionEventObj(
                "SIMULATED_ORDER_PREPARED",
                reason="entry_signal",
                execution_event_id="evt-open-1",
                market="BTC-EUR",
                signal_strength=0.8,
                spread_pct=0.01,
            ),
            bid=bid,
            ask=ask,
            timestamp_utc=timestamp_utc,
            signal="entry_signal",
            confidence=0.5,
        )

    def test_risk_state_can_be_constructed_from_accounting_state(self):
        engine = self._engine()
        self._open_position(engine, ask=100.0, bid=99.0)
        engine.update_mark_to_market(bid=105.0, ask=106.0, timestamp_utc="2026-09-06T00:00:05+00:00")

        state = engine.build_risk_state()

        self.assertIsNotNone(state)
        self.assertTrue(state.is_valid)
        self.assertEqual(state.recovery_status, "VALID")
        self.assertEqual(state.available_balance, engine.available_balance)
        self.assertEqual(state.equity, engine.equity)
        self.assertEqual(state.realized_pnl, engine.realized_pnl)
        self.assertEqual(state.unrealized_pnl, engine.unrealized_pnl)
        self.assertTrue(state.open_position_exists)
        self.assertEqual(state.open_position_side, engine.open_position.side)
        self.assertEqual(state.open_position_size, engine.open_position.position_size)
        self.assertEqual(state.open_position_entry_price, engine.open_position.entry_price)
        self.assertEqual(state.current_drawdown, engine.current_drawdown)
        self.assertEqual(state.maximum_drawdown, engine.maximum_drawdown)

    def test_invalid_accounting_state_cannot_produce_valid_risk_state(self):
        engine = self._engine()
        engine.recovery_status = "BLOCKED_ON_DIVERGENCE"

        state = engine.build_risk_state()

        self.assertIsNotNone(state)
        self.assertFalse(state.is_valid)
        self.assertEqual(state.recovery_status, "BLOCKED_ON_DIVERGENCE")
        self.assertFalse(state.financial_valid)

    def test_recovery_blocked_state_cannot_produce_valid_risk_state(self):
        engine = self._engine()
        engine.recovery_status = "BLOCKED_ON_DIVERGENCE"

        state = RiskState.from_accounting(engine)

        self.assertIsNotNone(state)
        self.assertFalse(state.is_valid)
        self.assertIn("BLOCKED", state.recovery_status)

    def test_risk_state_creation_does_not_mutate_accounting_state(self):
        engine = self._engine()
        self._open_position(engine, ask=100.0, bid=99.0)
        before = {
            "available_balance": engine.available_balance,
            "equity": engine.equity,
            "realized_pnl": engine.realized_pnl,
            "unrealized_pnl": engine.unrealized_pnl,
            "current_drawdown": engine.current_drawdown,
            "maximum_drawdown": engine.maximum_drawdown,
            "recovery_status": engine.recovery_status,
        }

        snapshot = engine.build_risk_state()

        self.assertEqual(snapshot.available_balance, before["available_balance"])
        self.assertEqual(snapshot.equity, before["equity"])
        self.assertEqual(snapshot.realized_pnl, before["realized_pnl"])
        self.assertEqual(snapshot.unrealized_pnl, before["unrealized_pnl"])
        self.assertEqual(snapshot.current_drawdown, before["current_drawdown"])
        self.assertEqual(snapshot.maximum_drawdown, before["maximum_drawdown"])
        self.assertEqual(engine.available_balance, before["available_balance"])
        self.assertEqual(engine.equity, before["equity"])
        self.assertEqual(engine.recovery_status, before["recovery_status"])

    def test_risk_engine_behavior_remains_intact_for_valid_candidates(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            emergency_stop=False,
            max_spread_pct=0.02,
            max_tick_interval_ms=2000.0,
            min_signal_strength=-1.0,
            max_candidates_per_minute=120,
        )

        strategy_input = StrategyInput(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            bid=101.0,
            ask=102.0,
            last=101.5,
            spread_abs=1.0,
            spread_pct=0.0099,
            mid_price=101.5,
            micro_return_1=0.02,
            micro_return_5=0.02,
            spread_change_1=0.0,
            spread_change_5=0.0,
            tick_interval_ms=10.0,
        )
        strategy_decision = StrategyDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            action="CANDIDATE_TRADE",
            reason="momentum_positive_and_spread_acceptable",
            signal_strength=0.9,
            spread_pct=0.0099,
            micro_return_1=0.02,
            micro_return_5=0.02,
            tick_interval_ms=10.0,
        )

        decision = engine.evaluate(strategy_decision, event_time_utc="2026-09-06T00:00:00+00:00")

        self.assertTrue(decision.approved)
        self.assertEqual(decision.risk_action, "APPROVED_SIMULATION")
        self.assertEqual(decision.reason, "risk_checks_passed")

    def test_risk_state_has_one_coherent_financial_view(self):
        engine = self._engine()
        self._open_position(engine, ask=100.0, bid=99.0)
        engine.update_mark_to_market(bid=105.0, ask=106.0, timestamp_utc="2026-09-06T00:00:05+00:00")

        state = engine.build_risk_state()

        self.assertTrue(state.open_position_exists)
        self.assertEqual(state.open_position_side, "LONG")
        self.assertGreater(state.open_position_size, 0.0)
        self.assertGreater(state.open_position_entry_price, 0.0)
        self.assertEqual(state.available_balance, engine.available_balance)
        self.assertEqual(state.equity, engine.equity)
        self.assertEqual(state.realized_pnl, engine.realized_pnl)
        self.assertAlmostEqual(state.unrealized_pnl, engine.unrealized_pnl)
        self.assertTrue(state.financial_valid)
        self.assertTrue(state.is_valid)

    def test_missing_or_invalid_risk_state_blocks_candidate_trade(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=1.0,
            max_exposure=1000.0,
        )
        strategy_decision = StrategyDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            action="CANDIDATE_TRADE",
            reason="momentum_positive_and_spread_acceptable",
            signal_strength=0.9,
            spread_pct=0.0099,
            micro_return_1=0.02,
            micro_return_5=0.02,
            tick_interval_ms=10.0,
        )

        invalid_state = RiskState(
            available_balance=0.0,
            equity=0.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            open_position_exists=False,
            open_position_side=None,
            open_position_size=None,
            open_position_entry_price=None,
            current_drawdown=0.0,
            maximum_drawdown=0.0,
            recovery_status="BLOCKED_ON_DIVERGENCE",
            financial_valid=False,
            is_valid=False,
        )
        blocked = engine.evaluate(
            strategy_decision,
            event_time_utc="2026-09-06T00:00:01+00:00",
            risk_state=invalid_state,
            candidate_position_size=0.1,
        )
        self.assertFalse(blocked.approved)
        self.assertIn("invalid_risk_state", blocked.reason)


class RiskPositionExposureLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.logger = DummyLogger()

    def tearDown(self):
        self.tmp.cleanup()

    def _candidate(self, *, signal_strength=0.9, spread_pct=0.01):
        return StrategyDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            action="CANDIDATE_TRADE",
            reason="momentum_positive_and_spread_acceptable",
            signal_strength=signal_strength,
            spread_pct=spread_pct,
            micro_return_1=0.02,
            micro_return_5=0.02,
            tick_interval_ms=10.0,
        )

    def _risk_state(self, *, open_position_exists=False, open_position_size=0.0, entry_price=100.0, recovery_status="VALID", financial_valid=True):
        return RiskState(
            available_balance=1000.0,
            equity=1000.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            open_position_exists=open_position_exists,
            open_position_side="LONG" if open_position_exists else None,
            open_position_size=open_position_size if open_position_exists else None,
            open_position_entry_price=entry_price if open_position_exists else None,
            current_drawdown=0.0,
            maximum_drawdown=0.0,
            recovery_status=recovery_status,
            financial_valid=financial_valid,
            is_valid=financial_valid and recovery_status == "VALID",
        )

    def test_candidate_within_max_position_size_allowed(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=0.75,
            max_exposure=1000.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.5,
        )

        self.assertTrue(decision.approved)
        self.assertEqual(decision.reason, "risk_checks_passed")

    def test_candidate_exceeding_max_position_size_denied(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=0.5,
            max_exposure=1000.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.75,
        )

        self.assertFalse(decision.approved)
        self.assertIn("max_position_size", decision.reason)

    def test_candidate_within_max_exposure_allowed(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=1.0,
            max_exposure=40.0,
        )
        risk_state = self._risk_state(open_position_exists=True, open_position_size=0.2, entry_price=100.0)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.1,
        )

        self.assertTrue(decision.approved)
        self.assertNotIn("max_exposure", decision.reason)

    def test_candidate_exceeding_max_exposure_denied(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=1.0,
            max_exposure=20.0,
        )
        risk_state = self._risk_state(open_position_exists=True, open_position_size=0.2, entry_price=100.0)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.3,
        )

        self.assertFalse(decision.approved)
        self.assertIn("max_exposure", decision.reason)

    def test_reducing_candidate_not_blocked_by_position_limit(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=0.25,
            max_exposure=5000.0,
        )
        risk_state = self._risk_state(open_position_exists=True, open_position_size=0.3, entry_price=100.0)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=-0.2,
        )

        self.assertTrue(decision.approved)

    def test_invalid_risk_state_is_denied(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=0.5,
            max_exposure=5000.0,
        )
        risk_state = self._risk_state(recovery_status="BLOCKED_ON_DIVERGENCE", financial_valid=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.2,
        )

        self.assertFalse(decision.approved)
        self.assertIn("invalid_risk_state", decision.reason)

    def test_invalid_limit_configuration_fails_closed(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=0.0,
            max_exposure=5000.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.1,
        )

        self.assertFalse(decision.approved)
        self.assertIn("invalid_limit_configuration", decision.reason)

    def test_risk_engine_does_not_mutate_accounting_state(self):
        engine = AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(self.tmp_path / "open_position_state.json"),
            logger=self.logger,
            enabled=True,
            strategy_name="baseline",
            starting_balance=1000.0,
            order_notional_eur=10.0,
            fee_rate=0.0,
            slippage_bps=0.0,
        )
        engine.open_position = type("Position", (), {"side": "LONG", "position_size": 0.3, "entry_price": 100.0})()
        risk_state = RiskState.from_accounting(engine)

        risk_gate = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_position_size=0.25,
            max_exposure=2500.0,
        )

        before_size = engine.open_position.position_size
        before_entry = engine.open_position.entry_price
        decision = risk_gate.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.1,
        )

        self.assertFalse(decision.approved)
        self.assertEqual(engine.open_position.position_size, before_size)
        self.assertEqual(engine.open_position.entry_price, before_entry)

    def test_risk_per_trade_allows_valid_below_max(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=25.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=20.0,
            protected_exit_value=5.0,
        )

        self.assertTrue(decision.approved)
        self.assertEqual(decision.reason, "risk_checks_passed")

    def test_risk_per_trade_allows_equal_max(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=25.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=30.0,
            protected_exit_value=5.0,
        )

        self.assertTrue(decision.approved)

    def test_risk_per_trade_denies_above_max(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=25.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=40.0,
            protected_exit_value=5.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("max_risk_per_trade", decision.reason)

    def test_risk_per_trade_denies_missing_protected_exit(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=25.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=20.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("missing_protected_exit_value", decision.reason)

    def test_risk_per_trade_denies_invalid_protected_exit_boundary(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=25.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=20.0,
            protected_exit_value=30.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("invalid_protected_exit_value", decision.reason)

    def test_risk_per_trade_denies_invalid_notional(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=25.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=-10.0,
            protected_exit_value=5.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("invalid_candidate_entry_notional", decision.reason)

    def test_risk_per_trade_denies_invalid_max_risk_configuration(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=0.0,
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=10.0,
            protected_exit_value=5.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("invalid_max_risk_per_trade", decision.reason)

    def test_risk_per_trade_denies_non_finite_max_risk_configuration(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=float("nan"),
        )
        risk_state = self._risk_state(open_position_exists=False)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=10.0,
            protected_exit_value=5.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("invalid_max_risk_per_trade", decision.reason)

    def test_risk_per_trade_reducing_position_is_allowed(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_risk_per_trade=25.0,
        )
        risk_state = self._risk_state(open_position_exists=True, open_position_size=0.5, entry_price=100.0)

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_entry_notional=10.0,
            protected_exit_value=8.0,
        )

        self.assertTrue(decision.approved)


class LossControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.logger = DummyLogger()

    def tearDown(self):
        self.tmp.cleanup()

    def _engine(self, **kwargs):
        return AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(self.tmp_path / "open_position_state.json"),
            logger=self.logger,
            enabled=True,
            strategy_name="baseline",
            starting_balance=10000.0,
            order_notional_eur=1000.0,
            fee_rate=0.0,
            slippage_bps=0.0,
            **kwargs,
        )

    def _candidate(self):
        return StrategyDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            action="CANDIDATE_TRADE",
            reason="momentum_positive_and_spread_acceptable",
            signal_strength=0.9,
            spread_pct=0.0099,
            micro_return_1=0.02,
            micro_return_5=0.02,
            tick_interval_ms=10.0,
        )

    def test_loss_controls_are_tracked_from_accounting_state(self):
        engine = self._engine()

        engine.process_execution(
            execution_event=ExecutionEventObj(
                "SIMULATED_ORDER_PREPARED",
                reason="entry_signal",
                execution_event_id="evt-open-1",
                market="BTC-EUR",
                signal_strength=0.8,
                spread_pct=0.01,
            ),
            bid=100.0,
            ask=100.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
            signal="entry_signal",
            confidence=0.5,
        )
        engine.process_execution(
            execution_event=ExecutionEventObj(
                "SIMULATED_ORDER_PREPARED",
                reason="exit_signal",
                execution_event_id="evt-close-1",
                market="BTC-EUR",
                signal_strength=0.8,
                spread_pct=0.01,
            ),
            bid=90.0,
            ask=100.0,
            timestamp_utc="2026-09-06T00:00:05+00:00",
            signal="exit_signal",
            confidence=0.5,
        )

        self.assertEqual(engine.daily_loss, 100.0)
        self.assertEqual(engine.consecutive_losses, 1)
        self.assertEqual(engine.daily_loss_reference_utc, "2026-09-06T00:00:05+00:00")

    def test_risk_engine_blocks_when_daily_loss_limit_is_reached(self):
        risk_gate = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_daily_loss=25.0,
        )
        risk_state = RiskState(
            available_balance=1000.0,
            equity=1000.0,
            realized_pnl=-25.0,
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
            daily_loss=25.0,
            daily_loss_reference_utc="2026-09-06T00:00:00+00:00",
            consecutive_losses=0,
        )

        decision = risk_gate.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:17+00:00",
        )

        self.assertFalse(decision.approved)
        self.assertIn("max_daily_loss", decision.reason)

    def test_risk_engine_blocks_when_consecutive_losses_limit_is_reached(self):
        risk_gate = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            max_consecutive_losses=2,
        )
        risk_state = RiskState(
            available_balance=1000.0,
            equity=1000.0,
            realized_pnl=-25.0,
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
            daily_loss=25.0,
            daily_loss_reference_utc="2026-09-06T00:00:00+00:00",
            consecutive_losses=2,
        )

        decision = risk_gate.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:17+00:00",
        )

        self.assertFalse(decision.approved)
        self.assertIn("max_consecutive_losses", decision.reason)

    def test_loss_state_survives_runtime_checkpoint_restore(self):
        engine = self._engine()
        engine.daily_loss = 35.0
        engine.daily_loss_reference_utc = "2026-09-06T00:00:00+00:00"
        engine.consecutive_losses = 3
        engine._persist_runtime_state()

        restored = AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(self.tmp_path / "open_position_state.json"),
            logger=self.logger,
            enabled=True,
            strategy_name="baseline",
            starting_balance=10000.0,
            order_notional_eur=1000.0,
            fee_rate=0.0,
            slippage_bps=0.0,
        )

        self.assertEqual(restored.daily_loss, 35.0)
        self.assertEqual(restored.daily_loss_reference_utc, "2026-09-06T00:00:00+00:00")
        self.assertEqual(restored.consecutive_losses, 3)


class RiskValidationStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.logger = DummyLogger()

    def tearDown(self):
        self.tmp.cleanup()

    def _candidate(self, *, signal_strength=0.9, spread_pct=0.0099, tick_interval_ms=10.0):
        return StrategyDecision(
            timestamp_utc="2026-09-06T00:00:00+00:00",
            market="BTC-EUR",
            action="CANDIDATE_TRADE",
            reason="momentum_positive_and_spread_acceptable",
            signal_strength=signal_strength,
            spread_pct=spread_pct,
            micro_return_1=0.02,
            micro_return_5=0.02,
            tick_interval_ms=tick_interval_ms,
        )

    def _valid_risk_state(self, *, recovery_status="VALID", financial_valid=True):
        return RiskState(
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
            recovery_status=recovery_status,
            financial_valid=financial_valid,
            is_valid=financial_valid and recovery_status == "VALID",
            daily_loss=10.0,
            daily_loss_reference_utc="2026-09-06T00:00:00+00:00",
            consecutive_losses=1,
        )

    def test_complete_gate_accepts_valid_state_with_all_controls_passing(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            emergency_stop=False,
            max_spread_pct=0.02,
            max_tick_interval_ms=2000.0,
            min_signal_strength=-1.0,
            max_candidates_per_minute=120,
            max_position_size=1.0,
            max_exposure=1000.0,
            max_risk_per_trade=20.0,
            max_daily_loss=25.0,
            max_consecutive_losses=3,
        )
        risk_state = self._valid_risk_state()

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.2,
            candidate_entry_notional=15.0,
            protected_exit_value=5.0,
        )

        self.assertTrue(decision.approved)
        self.assertEqual(decision.reason, "risk_checks_passed")

    def test_complete_gate_denies_when_any_mandatory_control_fails(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            emergency_stop=True,
            max_spread_pct=0.02,
            max_tick_interval_ms=2000.0,
            min_signal_strength=-1.0,
            max_candidates_per_minute=120,
            max_position_size=1.0,
            max_exposure=1000.0,
            max_risk_per_trade=20.0,
            max_daily_loss=25.0,
            max_consecutive_losses=3,
        )
        risk_state = self._valid_risk_state()

        decision = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.2,
            candidate_entry_notional=15.0,
            protected_exit_value=5.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("emergency_stop", decision.reason)

    def test_complete_gate_is_deterministic_for_identical_inputs(self):
        engine = RiskEngine(
            output_path=str(self.tmp_path / "risk.csv"),
            logger=self.logger,
            enabled=True,
            emergency_stop=False,
            max_spread_pct=0.02,
            max_tick_interval_ms=2000.0,
            min_signal_strength=-1.0,
            max_candidates_per_minute=120,
            max_position_size=1.0,
            max_exposure=1000.0,
            max_risk_per_trade=20.0,
            max_daily_loss=25.0,
            max_consecutive_losses=3,
        )
        risk_state = self._valid_risk_state()

        first = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.2,
            candidate_entry_notional=15.0,
            protected_exit_value=5.0,
        )
        second = engine.evaluate(
            self._candidate(),
            risk_state=risk_state,
            event_time_utc="2026-09-06T00:00:00+00:00",
            candidate_position_size=0.2,
            candidate_entry_notional=15.0,
            protected_exit_value=5.0,
        )

        self.assertEqual(first.approved, second.approved)
        self.assertEqual(first.reason, second.reason)


# ensure the name exists for imports that expect it
from risk_engine import RiskState
