import csv
import tempfile
import unittest
from pathlib import Path

from accounting_engine import AccountingDecision, AccountingEngine
from market_data_engine import MarketDataEngine
from position_manager import PositionManager


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


class AccountingBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.logger = DummyLogger()
        self._event_seq = 0

    def tearDown(self):
        self.tmp.cleanup()

    def _engine(self, fee_rate=0.0, slippage_bps=0.0, starting_balance=10000.0, notional=1000.0):
        return AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(self.tmp_path / "open_position_state.json"),
            logger=self.logger,
            enabled=True,
            strategy_name="baseline",
            starting_balance=starting_balance,
            order_notional_eur=notional,
            fee_rate=fee_rate,
            slippage_bps=slippage_bps,
        )

    def _open(self, engine, ask=100.0, bid=99.0, ts="2026-09-06T00:00:00+00:00"):
        engine.process_execution(
            execution_event=ExecutionEventObj(
                "SIMULATED_ORDER_PREPARED",
                "entry_signal",
                execution_event_id=self._next_event_id("open"),
            ),
            bid=bid,
            ask=ask,
            timestamp_utc=ts,
            signal="entry_signal",
            confidence=0.5,
        )

    def _close(self, engine, bid=110.0, ask=111.0, ts="2026-09-06T00:01:00+00:00"):
        return engine.process_execution(
            execution_event=ExecutionEventObj(
                "SIMULATED_ORDER_PREPARED",
                "exit_signal",
                execution_event_id=self._next_event_id("close"),
            ),
            bid=bid,
            ask=ask,
            timestamp_utc=ts,
            signal="exit_signal",
            confidence=0.5,
        )

    def _next_event_id(self, prefix="evt"):
        self._event_seq += 1
        return f"{prefix}-{self._event_seq:04d}"

    def _ledger_rows(self):
        with (self.tmp_path / "trade_ledger.csv").open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _restart(self, fee_rate=0.0, slippage_bps=0.0, starting_balance=10000.0, notional=1000.0):
        return self._engine(
            fee_rate=fee_rate,
            slippage_bps=slippage_bps,
            starting_balance=starting_balance,
            notional=notional,
        )

    def test_profitable_trade_zero_fees_slippage(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0)
        trade = self._close(engine, bid=110.0)

        expected_size = 1000.0 / 100.0
        expected_gross = (110.0 - 100.0) * expected_size

        self.assertAlmostEqual(trade.position_size, expected_size, places=10)
        self.assertAlmostEqual(trade.gross_pnl, expected_gross, places=10)
        self.assertAlmostEqual(trade.fees, 0.0, places=10)
        self.assertAlmostEqual(trade.slippage, 0.0, places=10)
        self.assertAlmostEqual(trade.net_pnl, expected_gross, places=10)

    def test_losing_trade_zero_fees_slippage(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0)
        trade = self._close(engine, bid=90.0)

        expected_size = 1000.0 / 100.0
        expected_gross = (90.0 - 100.0) * expected_size

        self.assertAlmostEqual(trade.gross_pnl, expected_gross, places=10)
        self.assertAlmostEqual(trade.net_pnl, expected_gross, places=10)

    def test_profitable_trade_with_fees(self):
        engine = self._engine(fee_rate=0.001, slippage_bps=0.0)
        self._open(engine, ask=100.0)
        trade = self._close(engine, bid=110.0)

        size = 1000.0 / 100.0
        gross = (110.0 - 100.0) * size
        total_fees = (1000.0 * 0.001) + ((110.0 * size) * 0.001)
        expected_net = gross - total_fees

        self.assertAlmostEqual(trade.fees, total_fees, places=10)
        self.assertAlmostEqual(trade.net_pnl, expected_net, places=10)

    def test_losing_trade_with_fees(self):
        engine = self._engine(fee_rate=0.001, slippage_bps=0.0)
        self._open(engine, ask=100.0)
        trade = self._close(engine, bid=90.0)

        size = 1000.0 / 100.0
        gross = (90.0 - 100.0) * size
        total_fees = (1000.0 * 0.001) + ((90.0 * size) * 0.001)
        expected_net = gross - total_fees

        self.assertAlmostEqual(trade.fees, total_fees, places=10)
        self.assertAlmostEqual(trade.net_pnl, expected_net, places=10)

    def test_buy_uses_ask_and_sell_uses_bid(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=99.0)
        trade = self._close(engine, bid=101.0, ask=102.0)

        size = 1000.0 / 100.0
        expected_gross = (101.0 - 100.0) * size

        self.assertAlmostEqual(trade.entry_price, 100.0, places=10)
        self.assertAlmostEqual(trade.exit_price, 101.0, places=10)
        self.assertAlmostEqual(trade.gross_pnl, expected_gross, places=10)

    def test_slippage_affects_entry_exit_and_pnl(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=100.0)
        self._open(engine, ask=100.0)
        trade = self._close(engine, bid=110.0)

        entry_exec = 100.0 * 1.01
        size = 1000.0 / entry_exec
        exit_exec = 110.0 * 0.99
        expected_gross = (exit_exec - entry_exec) * size
        expected_slippage = ((entry_exec - 100.0) * size) + ((110.0 - exit_exec) * size)

        self.assertAlmostEqual(trade.entry_price, entry_exec, places=10)
        self.assertAlmostEqual(trade.exit_price, exit_exec, places=10)
        self.assertAlmostEqual(trade.gross_pnl, expected_gross, places=10)
        self.assertAlmostEqual(trade.slippage, expected_slippage, places=10)

    def test_slippage_is_attribution_not_second_ledger_deduction(self):
        engine = self._engine(fee_rate=0.001, slippage_bps=100.0)
        self._open(engine, ask=100.0)
        trade = self._close(engine, bid=110.0)

        entry_exec = 100.0 * 1.01
        exit_exec = 110.0 * 0.99
        size = 1000.0 / entry_exec
        expected_gross = (exit_exec - entry_exec) * size
        expected_fees = (entry_exec * size * 0.001) + (exit_exec * size * 0.001)
        expected_slippage = ((entry_exec - 100.0) * size) + ((110.0 - exit_exec) * size)

        self.assertAlmostEqual(trade.gross_pnl, expected_gross, places=10)
        self.assertAlmostEqual(trade.fees, expected_fees, places=10)
        self.assertAlmostEqual(trade.net_pnl, expected_gross - expected_fees, places=10)
        self.assertAlmostEqual(trade.slippage, expected_slippage, places=10)
        self.assertAlmostEqual(trade.gross_pnl - trade.fees, trade.net_pnl, places=10)

    def test_open_position_generates_unrealized_pnl(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)

        engine.update_mark_to_market(bid=105.0, ask=106.0, timestamp_utc="2026-09-06T00:00:30+00:00")

        size = 1000.0 / 100.0
        expected_unrealized = (105.0 - 100.0) * size
        expected_equity = (10000.0 - 1000.0) + (105.0 * size)

        self.assertAlmostEqual(engine.unrealized_pnl, expected_unrealized, places=10)
        self.assertAlmostEqual(engine.equity, expected_equity, places=10)

    def test_close_converts_unrealized_to_realized(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)
        engine.update_mark_to_market(bid=105.0, ask=106.0, timestamp_utc="2026-09-06T00:00:30+00:00")

        trade = self._close(engine, bid=110.0)

        self.assertAlmostEqual(engine.unrealized_pnl, 0.0, places=10)
        self.assertAlmostEqual(engine.realized_pnl, trade.net_pnl, places=10)

    def test_multiple_trades_update_balance_correctly(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)

        self._open(engine, ask=100.0)
        trade1 = self._close(engine, bid=110.0, ts="2026-09-06T00:01:00+00:00")

        self._open(engine, ask=100.0, ts="2026-09-06T00:02:00+00:00")
        trade2 = self._close(engine, bid=90.0, ts="2026-09-06T00:03:00+00:00")

        expected_available = 10000.0 + trade1.net_pnl + trade2.net_pnl
        self.assertAlmostEqual(engine.available_balance, expected_available, places=10)

    def test_drawdown_calculation_uses_equity(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)

        engine.update_mark_to_market(bid=80.0, ask=81.0, timestamp_utc="2026-09-06T00:00:20+00:00")

        size = 1000.0 / 100.0
        expected_equity = (10000.0 - 1000.0) + (size * 80.0)
        expected_drawdown = (10000.0 - expected_equity) / 10000.0

        self.assertAlmostEqual(engine.equity, expected_equity, places=10)
        self.assertAlmostEqual(engine.current_drawdown, expected_drawdown, places=10)
        self.assertAlmostEqual(engine.maximum_drawdown, expected_drawdown, places=10)

    def test_skipped_events_generate_no_pnl(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        before_available = engine.available_balance
        before_realized = engine.realized_pnl

        result = engine.process_execution(
            execution_event=ExecutionEventObj("SKIPPED", "no_strategy_candidate"),
            bid=100.0,
            ask=101.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
        )

        self.assertIsNone(result)
        self.assertAlmostEqual(engine.available_balance, before_available, places=10)
        self.assertAlmostEqual(engine.realized_pnl, before_realized, places=10)
        self.assertEqual(len(self._ledger_rows()), 0)

    def test_rejected_or_failed_events_generate_no_pnl(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        before_available = engine.available_balance
        before_realized = engine.realized_pnl

        rejected = engine.process_execution(
            execution_event=ExecutionEventObj("NO_ACTION", "risk_rejected"),
            bid=100.0,
            ask=101.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
        )
        failed = engine.process_execution(
            execution_event=ExecutionEventObj("FAILED", "simulated_order_failed"),
            bid=100.0,
            ask=101.0,
            timestamp_utc="2026-09-06T00:00:01+00:00",
        )

        self.assertIsNone(rejected)
        self.assertIsNone(failed)
        self.assertAlmostEqual(engine.available_balance, before_available, places=10)
        self.assertAlmostEqual(engine.realized_pnl, before_realized, places=10)
        self.assertEqual(len(self._ledger_rows()), 0)

    def test_order_fill_position_trade_lifecycle_consistency(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)

        self._open(engine, ask=100.0, bid=100.0, ts="2026-09-06T00:00:00+00:00")
        self.assertIsNotNone(engine.open_position)
        trade_id = engine.open_position.trade_id

        closed = self._close(engine, bid=101.0, ask=102.0, ts="2026-09-06T00:00:10+00:00")
        self.assertIsNone(engine.open_position)

        ledger_rows = self._ledger_rows()
        self.assertEqual(len(ledger_rows), 1)
        self.assertEqual(ledger_rows[0]["trade_id"], trade_id)
        self.assertEqual(closed.trade_id, trade_id)

    def test_restart_recovers_open_position_from_persisted_state(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0, ts="2026-09-06T00:00:00+00:00")

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)

        self.assertIsNotNone(recovered.open_position)
        self.assertEqual(recovered.open_position.trade_id, engine.open_position.trade_id)

    def test_restart_recovers_same_entry_price(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=15.0)
        self._open(engine, ask=100.0, bid=100.0, ts="2026-09-06T00:00:00+00:00")
        expected_entry = engine.open_position.entry_price

        recovered = self._restart(fee_rate=0.0, slippage_bps=15.0)
        self.assertAlmostEqual(recovered.open_position.entry_price, expected_entry, places=10)
        self.assertAlmostEqual(recovered.open_position.entry_execution_price, expected_entry, places=10)

    def test_restart_recovers_same_position_size(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=10.0)
        self._open(engine, ask=100.0, bid=100.0)
        expected_size = engine.open_position.position_size

        recovered = self._restart(fee_rate=0.0, slippage_bps=10.0)
        self.assertAlmostEqual(recovered.open_position.position_size, expected_size, places=10)

    def test_restart_preserves_available_balance(self):
        engine = self._engine(fee_rate=0.001, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)
        expected_available = engine.available_balance

        recovered = self._restart(fee_rate=0.001, slippage_bps=0.0)
        self.assertAlmostEqual(recovered.available_balance, expected_available, places=10)

    def test_restart_preserves_realized_pnl(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)

        self._open(engine, ask=100.0, bid=100.0, ts="2026-09-06T00:00:00+00:00")
        self._close(engine, bid=110.0, ask=111.0, ts="2026-09-06T00:01:00+00:00")
        self._open(engine, ask=105.0, bid=104.0, ts="2026-09-06T00:02:00+00:00")

        expected_realized = engine.realized_pnl
        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)
        self.assertAlmostEqual(recovered.realized_pnl, expected_realized, places=10)

    def test_mark_to_market_after_restart_updates_unrealized_correctly(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)
        recovered.update_mark_to_market(bid=103.0, ask=104.0, timestamp_utc="2026-09-06T00:00:10+00:00")

        size = 1000.0 / 100.0
        expected_unrealized = (103.0 - 100.0) * size
        self.assertAlmostEqual(recovered.unrealized_pnl, expected_unrealized, places=10)

    def test_equity_after_restart_matches_expected_value(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)
        recovered.update_mark_to_market(bid=103.0, ask=104.0, timestamp_utc="2026-09-06T00:00:10+00:00")

        size = 1000.0 / 100.0
        expected_equity = (10000.0 - 1000.0) + (103.0 * size)
        self.assertAlmostEqual(recovered.equity, expected_equity, places=10)

    def test_drawdown_continuity_is_preserved_after_restart(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)
        engine.update_mark_to_market(bid=80.0, ask=81.0, timestamp_utc="2026-09-06T00:00:10+00:00")
        expected_max_drawdown = engine.maximum_drawdown

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)
        self.assertAlmostEqual(recovered.maximum_drawdown, expected_max_drawdown, places=10)

        recovered.update_mark_to_market(bid=90.0, ask=91.0, timestamp_utc="2026-09-06T00:00:20+00:00")
        self.assertAlmostEqual(recovered.maximum_drawdown, expected_max_drawdown, places=10)

    def test_restart_does_not_create_duplicate_position(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)
        trade_id = engine.open_position.trade_id

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)

        self.assertIsNotNone(recovered.open_position)
        self.assertEqual(recovered.open_position.trade_id, trade_id)
        self.assertEqual(len(self._ledger_rows()), 0)

    def test_restart_does_not_create_duplicate_trade(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)
        rows_before = len(self._ledger_rows())

        _ = self._restart(fee_rate=0.0, slippage_bps=0.0)
        rows_after = len(self._ledger_rows())

        self.assertEqual(rows_before, 0)
        self.assertEqual(rows_after, 0)

    def test_skipped_after_restart_does_not_mutate_position(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)
        trade_id = engine.open_position.trade_id

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)
        recovered.process_execution(
            execution_event=ExecutionEventObj("SKIPPED", "no_strategy_candidate"),
            bid=100.0,
            ask=101.0,
            timestamp_utc="2026-09-06T00:00:10+00:00",
        )

        self.assertIsNotNone(recovered.open_position)
        self.assertEqual(recovered.open_position.trade_id, trade_id)

    def test_failed_and_rejected_after_restart_do_not_mutate_position(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0)
        trade_id = engine.open_position.trade_id

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)
        recovered.process_execution(
            execution_event=ExecutionEventObj("NO_ACTION", "risk_rejected"),
            bid=100.0,
            ask=101.0,
            timestamp_utc="2026-09-06T00:00:10+00:00",
        )
        recovered.process_execution(
            execution_event=ExecutionEventObj("FAILED", "simulated_order_failed"),
            bid=100.0,
            ask=101.0,
            timestamp_utc="2026-09-06T00:00:11+00:00",
        )

        self.assertIsNotNone(recovered.open_position)
        self.assertEqual(recovered.open_position.trade_id, trade_id)

    def test_successful_fill_after_restart_closes_recovered_position(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=100.0, ts="2026-09-06T00:00:00+00:00")
        trade_id = engine.open_position.trade_id

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)
        closed = recovered.process_execution(
            execution_event=ExecutionEventObj("SIMULATED_ORDER_PREPARED", "exit_signal"),
            bid=110.0,
            ask=111.0,
            timestamp_utc="2026-09-06T00:01:00+00:00",
            signal="exit_signal",
            confidence=0.5,
        )

        self.assertIsNotNone(closed)
        self.assertEqual(closed.trade_id, trade_id)
        self.assertIsNone(recovered.open_position)
        self.assertEqual(len(self._ledger_rows()), 1)

    def test_crash_recovery_open_mtm_close_final_realized_pnl_correct(self):
        engine = self._engine(fee_rate=0.001, slippage_bps=100.0)

        self._open(engine, ask=100.0, bid=99.0, ts="2026-09-06T00:00:00+00:00")
        recovered = self._restart(fee_rate=0.001, slippage_bps=100.0)

        recovered.update_mark_to_market(bid=105.0, ask=106.0, timestamp_utc="2026-09-06T00:00:10+00:00")

        entry_exec = 100.0 * 1.01
        size = 1000.0 / entry_exec
        expected_unrealized = (105.0 - entry_exec) * size
        self.assertAlmostEqual(recovered.unrealized_pnl, expected_unrealized, places=10)

        closed = recovered.process_execution(
            execution_event=ExecutionEventObj("SIMULATED_ORDER_PREPARED", "exit_signal"),
            bid=110.0,
            ask=111.0,
            timestamp_utc="2026-09-06T00:01:00+00:00",
            signal="exit_signal",
            confidence=0.5,
        )

        exit_exec = 110.0 * 0.99
        gross = (exit_exec - entry_exec) * size
        fees = (size * entry_exec * 0.001) + (size * exit_exec * 0.001)
        expected_net = gross - fees

        self.assertAlmostEqual(closed.net_pnl, expected_net, places=10)
        self.assertAlmostEqual(recovered.realized_pnl, expected_net, places=10)

    def test_first_successful_fill_is_processed(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)

        result = engine.process_execution(
            execution_event=ExecutionEventObj("SIMULATED_ORDER_PREPARED", "entry_signal", execution_event_id="FILL-123"),
            bid=100.0,
            ask=100.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
            signal="entry_signal",
            confidence=0.5,
        )

        self.assertIsNone(result)
        self.assertIsNotNone(engine.open_position)

    def test_same_successful_fill_replayed_immediately_is_ignored(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)

        event = ExecutionEventObj("SIMULATED_ORDER_PREPARED", "entry_signal", execution_event_id="FILL-123")
        engine.process_execution(event, bid=100.0, ask=100.0, timestamp_utc="2026-09-06T00:00:00+00:00")
        open_trade_id = engine.open_position.trade_id
        available_before = engine.available_balance

        engine.process_execution(event, bid=101.0, ask=101.0, timestamp_utc="2026-09-06T00:00:01+00:00")

        self.assertEqual(engine.open_position.trade_id, open_trade_id)
        self.assertAlmostEqual(engine.available_balance, available_before, places=10)
        self.assertEqual(len(self._ledger_rows()), 0)

    def test_valid_checkpoint_loads_successfully(self):
        checkpoint_path = self.tmp_path / "valid_open_position_state.json"
        valid_checkpoint = {
            "version": 1,
            "timestamp_utc": "2026-09-06T00:00:00+00:00",
            "processed_successful_execution_ids": ["FILL-001"],
            "account_state": {
                "starting_balance": 10000.0,
                "available_balance": 9000.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "equity": 10000.0,
                "cumulative_fees": 0.0,
                "cumulative_slippage": 0.0,
                "peak_equity": 10000.0,
                "current_drawdown": 0.0,
                "maximum_drawdown": 0.0,
            },
            "counters": {"trade_counter": 1, "order_counter": 2, "fill_counter": 2},
            "last_mark_price": 100.0,
            "open_position": {
                "trade_id": "TRD-000001",
                "symbol": "BTC-EUR",
                "side": "LONG",
                "entry_timestamp_utc": "2026-09-06T00:00:00+00:00",
                "entry_price": 100.0,
                "entry_execution_price": 100.0,
                "position_size": 10.0,
                "entry_fee": 0.0,
                "entry_slippage": 0.0,
                "strategy": "baseline",
                "signal": "entry_signal",
                "confidence": 0.5,
            },
        }
        checkpoint_path.write_text(__import__("json").dumps(valid_checkpoint), encoding="utf-8")

        engine = AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(checkpoint_path),
            logger=self.logger,
            enabled=True,
            starting_balance=10000.0,
        )

        self.assertEqual(engine.recovery_status, "VALID")
        self.assertEqual(engine._processed_successful_execution_ids, {"FILL-001"})
        self.assertIsNotNone(engine.open_position)
        self.assertEqual(engine.open_position.trade_id, "TRD-000001")
        self.assertAlmostEqual(engine.available_balance, 9000.0, places=10)

    def test_missing_checkpoint_fails_closed(self):
        checkpoint_path = self.tmp_path / "missing_checkpoint.json"
        if checkpoint_path.exists():
            checkpoint_path.unlink()

        trade_ledger = self.tmp_path / "trade_ledger.csv"
        trade_ledger.write_text("trade_id,timestamp_utc,symbol,side,entry_price,exit_price,position_size,gross_pnl,fees,slippage,net_pnl,holding_time_seconds,strategy,signal,confidence,close_reason,entry_timestamp_utc,exit_timestamp_utc\nTRD-000001,2026-09-06T00:00:00+00:00,BTC-EUR,LONG,100.0,110.0,10.0,100.0,0.0,0.0,100.0,60.0,baseline,momentum,0.5,close,2026-09-06T00:00:00+00:00,2026-09-06T00:01:00+00:00\n", encoding="utf-8")

        engine = AccountingEngine(
            trade_ledger_path=str(trade_ledger),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(checkpoint_path),
            logger=self.logger,
            enabled=True,
            starting_balance=10000.0,
        )

        self.assertEqual(engine.recovery_status, "BLOCKED_ON_DIVERGENCE")

    def test_corrupt_json_fails_closed(self):
        checkpoint_path = self.tmp_path / "corrupt_checkpoint.json"
        checkpoint_path.write_text('{"version": 1, "broken": ', encoding="utf-8")

        engine = AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(checkpoint_path),
            logger=self.logger,
            enabled=True,
            starting_balance=10000.0,
        )

        self.assertEqual(engine.recovery_status, "BLOCKED_ON_DIVERGENCE")

    def test_missing_processed_successful_execution_ids_fails_closed(self):
        checkpoint_path = self.tmp_path / "missing_execution_ids.json"
        checkpoint_path.write_text(
            __import__("json").dumps({
                "version": 1,
                "timestamp_utc": "2026-09-06T00:00:00+00:00",
                "account_state": {
                    "starting_balance": 10000.0,
                    "available_balance": 9000.0,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 0.0,
                    "equity": 9000.0,
                    "cumulative_fees": 0.0,
                    "cumulative_slippage": 0.0,
                    "peak_equity": 10000.0,
                    "current_drawdown": 0.0,
                    "maximum_drawdown": 0.0,
                },
                "counters": {"trade_counter": 1, "order_counter": 2, "fill_counter": 2},
                "last_mark_price": 100.0,
                "open_position": None,
            }),
            encoding="utf-8",
        )

        engine = AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(checkpoint_path),
            logger=self.logger,
            enabled=True,
            starting_balance=10000.0,
        )

        self.assertEqual(engine.recovery_status, "BLOCKED_ON_DIVERGENCE")

    def test_invalid_execution_id_values_fail_closed(self):
        checkpoint_path = self.tmp_path / "invalid_execution_ids.json"
        checkpoint_path.write_text(
            __import__("json").dumps({
                "version": 1,
                "timestamp_utc": "2026-09-06T00:00:00+00:00",
                "processed_successful_execution_ids": [123, "FILL-001"],
                "account_state": {
                    "starting_balance": 10000.0,
                    "available_balance": 10000.0,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 0.0,
                    "equity": 10000.0,
                    "cumulative_fees": 0.0,
                    "cumulative_slippage": 0.0,
                    "peak_equity": 10000.0,
                    "current_drawdown": 0.0,
                    "maximum_drawdown": 0.0,
                },
                "counters": {"trade_counter": 0, "order_counter": 0, "fill_counter": 0},
                "last_mark_price": None,
                "open_position": None,
            }),
            encoding="utf-8",
        )

        engine = AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(checkpoint_path),
            logger=self.logger,
            enabled=True,
            starting_balance=10000.0,
        )

        self.assertEqual(engine.recovery_status, "BLOCKED_ON_DIVERGENCE")

    def test_internally_inconsistent_accounting_state_fails_closed(self):
        checkpoint_path = self.tmp_path / "inconsistent_checkpoint.json"
        checkpoint_path.write_text(
            __import__("json").dumps({
                "version": 1,
                "timestamp_utc": "2026-09-06T00:00:00+00:00",
                "processed_successful_execution_ids": ["FILL-001"],
                "account_state": {
                    "starting_balance": 10000.0,
                    "available_balance": 9000.0,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 0.0,
                    "equity": 10000.0,
                    "cumulative_fees": 0.0,
                    "cumulative_slippage": 0.0,
                    "peak_equity": 10000.0,
                    "current_drawdown": 0.0,
                    "maximum_drawdown": 0.0,
                },
                "counters": {"trade_counter": 1, "order_counter": 2, "fill_counter": 2},
                "last_mark_price": 100.0,
                "open_position": None,
            }),
            encoding="utf-8",
        )

        engine = AccountingEngine(
            trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            account_state_path=str(self.tmp_path / "account_state.csv"),
            open_position_state_path=str(checkpoint_path),
            logger=self.logger,
            enabled=True,
            starting_balance=10000.0,
        )

        self.assertEqual(engine.recovery_status, "BLOCKED_ON_DIVERGENCE")

    def test_atomic_persistence_writes_complete_json(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        engine._persist_runtime_state()

        path = engine.open_position_state_path
        with open(path, "r", encoding="utf-8") as handle:
            payload = __import__("json").load(handle)

        self.assertIn("processed_successful_execution_ids", payload)
        self.assertIn("account_state", payload)
        self.assertIn("open_position", payload)

    def test_recovery_does_not_create_financial_effects(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        before_balance = engine.available_balance
        before_realized = engine.realized_pnl

        engine._restore_state_on_startup()

        self.assertAlmostEqual(engine.available_balance, before_balance, places=10)
        self.assertAlmostEqual(engine.realized_pnl, before_realized, places=10)

    def test_duplicate_fill_does_not_close_position_twice_or_duplicate_trade(self):
        engine = self._engine(fee_rate=0.001, slippage_bps=0.0)

        engine.process_execution(
            ExecutionEventObj("SIMULATED_ORDER_PREPARED", "entry_signal", execution_event_id="FILL-ENTRY-1"),
            bid=100.0,
            ask=100.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
        )
        close_event = ExecutionEventObj("SIMULATED_ORDER_PREPARED", "exit_signal", execution_event_id="FILL-EXIT-1")

        closed_first = engine.process_execution(
            close_event,
            bid=110.0,
            ask=110.5,
            timestamp_utc="2026-09-06T00:01:00+00:00",
        )
        available_after_first = engine.available_balance
        realized_after_first = engine.realized_pnl
        fees_after_first = engine.cumulative_fees
        slippage_after_first = engine.cumulative_slippage

        closed_second = engine.process_execution(
            close_event,
            bid=110.0,
            ask=110.5,
            timestamp_utc="2026-09-06T00:01:01+00:00",
        )

        self.assertIsNotNone(closed_first)
        self.assertIsNone(closed_second)
        self.assertIsNone(engine.open_position)
        self.assertAlmostEqual(engine.available_balance, available_after_first, places=10)
        self.assertAlmostEqual(engine.realized_pnl, realized_after_first, places=10)
        self.assertAlmostEqual(engine.cumulative_fees, fees_after_first, places=10)
        self.assertAlmostEqual(engine.cumulative_slippage, slippage_after_first, places=10)
        self.assertEqual(len(self._ledger_rows()), 1)

    def test_accounting_decision_status_tracks_accepted_duplicate_and_rejected_paths(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        accepted_event = ExecutionEventObj(
            "SIMULATED_ORDER_PREPARED",
            "entry_signal",
            execution_event_id="FILL-STATUS-ACCEPTED",
        )

        accepted = engine.process_execution(
            accepted_event,
            bid=100.0,
            ask=100.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
        )
        self.assertIsNone(accepted)
        self.assertEqual(engine.last_decision.status, "ACCEPTED")
        self.assertEqual(engine.last_decision.execution_event_id, "FILL-STATUS-ACCEPTED")

        duplicate = engine.process_execution(
            accepted_event,
            bid=101.0,
            ask=101.0,
            timestamp_utc="2026-09-06T00:00:01+00:00",
        )
        self.assertIsNone(duplicate)
        self.assertEqual(engine.last_decision.status, "DUPLICATE")
        self.assertEqual(engine.last_decision.execution_event_id, "FILL-STATUS-ACCEPTED")

        rejected = engine.process_execution(
            ExecutionEventObj("SKIPPED", "risk_rejected", execution_event_id="FILL-STATUS-REJECTED"),
            bid=101.0,
            ask=102.0,
            timestamp_utc="2026-09-06T00:00:02+00:00",
        )
        self.assertIsNone(rejected)
        self.assertEqual(engine.last_decision.status, "REJECTED")
        self.assertEqual(engine.last_decision.execution_event_id, "FILL-STATUS-REJECTED")

    def test_accounting_decision_status_tracks_failed_execution(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        failed = engine.process_execution(
            ExecutionEventObj("FAILED", "simulated_order_failed", execution_event_id="FILL-STATUS-FAILED"),
            bid=100.0,
            ask=100.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
        )

        self.assertIsNone(failed)
        self.assertEqual(engine.last_decision.status, "FAILED")
        self.assertEqual(engine.last_decision.execution_event_id, "FILL-STATUS-FAILED")

    def test_position_manager_accepts_only_accounting_decision_status_accepted(self):
        manager = PositionManager(
            output_path=str(self.tmp_path / "gated_positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        accepted = manager.process_accounting_decision(
            AccountingDecision(
                status="ACCEPTED",
                execution_event_id="FILL-ACCEPTED-1",
                execution_action="SIMULATED_ORDER_PREPARED",
                reason="accepted",
                financial_effect_applied=True,
                market="BTC-EUR",
                signal_strength=0.8,
                spread_pct=0.1,
            )
        )

        self.assertIsNotNone(accepted)
        self.assertEqual(accepted.lifecycle_action, "OPENED")

    def test_position_manager_ignores_duplicate_rejected_and_failed_accounting_decisions(self):
        manager = PositionManager(
            output_path=str(self.tmp_path / "gated_positions.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        accepted = manager.process_accounting_decision(
            AccountingDecision(
                status="ACCEPTED",
                execution_event_id="FILL-ACCEPTED-2",
                execution_action="SIMULATED_ORDER_PREPARED",
                reason="accepted",
                financial_effect_applied=True,
                market="BTC-EUR",
                signal_strength=0.7,
                spread_pct=0.05,
            )
        )
        self.assertIsNotNone(accepted)

        duplicate = manager.process_accounting_decision(
            AccountingDecision(
                status="DUPLICATE",
                execution_event_id="FILL-ACCEPTED-2",
                execution_action="SIMULATED_ORDER_PREPARED",
                reason="duplicate_execution_event_id",
                financial_effect_applied=False,
                market="BTC-EUR",
                signal_strength=0.7,
                spread_pct=0.05,
            )
        )
        rejected = manager.process_accounting_decision(
            AccountingDecision(
                status="REJECTED",
                execution_event_id="FILL-REJECTED-1",
                execution_action="SKIPPED",
                reason="risk_rejected",
                financial_effect_applied=False,
                market="BTC-EUR",
                signal_strength=0.4,
                spread_pct=0.03,
            )
        )
        failed = manager.process_accounting_decision(
            AccountingDecision(
                status="FAILED",
                execution_event_id="FILL-FAILED-1",
                execution_action="FAILED",
                reason="simulated_order_failed",
                financial_effect_applied=False,
                market="BTC-EUR",
                signal_strength=0.2,
                spread_pct=0.01,
            )
        )

        self.assertIsNone(duplicate)
        self.assertIsNone(rejected)
        self.assertIsNone(failed)
        self.assertIsNotNone(manager._active_position)

    def test_position_manager_rebuild_from_accounting_no_open_position(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        manager = PositionManager(
            output_path=str(self.tmp_path / "rebuild_none.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )
        manager._active_position = {"position_id": "stale", "market": "ETH-EUR", "hold_events": 99}

        result = manager.rebuild_from_accounting(engine)

        self.assertIsNone(result)
        self.assertIsNone(manager._active_position)

    def test_position_manager_rebuild_from_accounting_open_position_maps_required_fields(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=99.0, ts="2026-09-06T00:00:00+00:00")
        manager = PositionManager(
            output_path=str(self.tmp_path / "rebuild_open.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )
        manager._active_position = {"position_id": "stale", "market": "ETH-EUR", "hold_events": 99}

        result = manager.rebuild_from_accounting(engine)

        self.assertIsNotNone(result)
        self.assertEqual(manager._active_position["market"], engine.open_position.symbol)
        self.assertEqual(manager._active_position["side"], engine.open_position.side)
        self.assertEqual(manager._active_position["entry_time_utc"], engine.open_position.entry_timestamp_utc)
        self.assertAlmostEqual(manager._active_position["entry_price"], engine.open_position.entry_price, places=10)
        self.assertAlmostEqual(manager._active_position["position_size"], engine.open_position.position_size, places=10)
        self.assertEqual(manager._active_position["trade_id"], engine.open_position.trade_id)
        self.assertEqual(manager._active_position["hold_events"], 0)

    def test_position_manager_rebuild_from_accounting_replaces_stale_state(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=99.0, ts="2026-09-06T00:00:00+00:00")
        manager = PositionManager(
            output_path=str(self.tmp_path / "rebuild_replace.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )
        manager._active_position = {"position_id": "stale", "market": "ETH-EUR", "hold_events": 7, "entry_time_utc": "1999-01-01T00:00:00+00:00"}

        manager.rebuild_from_accounting(engine)

        self.assertEqual(manager._active_position["market"], "BTC-EUR")
        self.assertEqual(manager._active_position["hold_events"], 0)
        self.assertEqual(manager._active_position["trade_id"], engine.open_position.trade_id)

    def test_position_manager_rebuild_from_accounting_rejects_invalid_input(self):
        manager = PositionManager(
            output_path=str(self.tmp_path / "rebuild_invalid.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )
        manager._active_position = {"position_id": "stale", "market": "BTC-EUR", "hold_events": 7}

        result = manager.rebuild_from_accounting(None)

        self.assertIsNone(result)
        self.assertIsNone(manager._active_position)

    def test_position_manager_rebuild_from_accounting_is_deterministic_and_idempotent(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        self._open(engine, ask=100.0, bid=99.0, ts="2026-09-06T00:00:00+00:00")
        manager = PositionManager(
            output_path=str(self.tmp_path / "rebuild_idempotent.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        first = manager.rebuild_from_accounting(engine)
        second = manager.rebuild_from_accounting(engine)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first, second)
        self.assertEqual(manager._active_position["market"], "BTC-EUR")
        self.assertEqual(manager._active_position["trade_id"], engine.open_position.trade_id)

    def test_market_data_pipeline_only_updates_position_for_accepted_accounting_decisions(self):
        engine = MarketDataEngine(
            feature_engine_enabled=False,
            strategy_engine_enabled=False,
            risk_engine_enabled=False,
            execution_engine_enabled=False,
            position_manager_enabled=True,
            accounting_engine_enabled=True,
            accounting_trade_ledger_path=str(self.tmp_path / "trade_ledger.csv"),
            accounting_account_state_path=str(self.tmp_path / "account_state.csv"),
            accounting_open_position_state_path=str(self.tmp_path / "account_state.json"),
        )

        accepted_decision = AccountingDecision(
            status="ACCEPTED",
            execution_event_id="FILL-GATED-ACCEPTED",
            execution_action="SIMULATED_ORDER_PREPARED",
            reason="accepted",
            financial_effect_applied=True,
            market="BTC-EUR",
            signal_strength=0.9,
            spread_pct=0.05,
        )
        result = engine.update_position_manager(accepted_decision)

        self.assertIsNotNone(result)
        self.assertEqual(result.lifecycle_action, "OPENED")

        duplicate = engine.update_position_manager(
            AccountingDecision(
                status="DUPLICATE",
                execution_event_id="FILL-GATED-ACCEPTED",
                execution_action="SIMULATED_ORDER_PREPARED",
                reason="duplicate_execution_event_id",
                financial_effect_applied=False,
                market="BTC-EUR",
                signal_strength=0.9,
                spread_pct=0.05,
            )
        )
        self.assertIsNone(duplicate)

    def test_position_manager_raw_execution_event_is_disabled(self):
        manager = PositionManager(
            output_path=str(self.tmp_path / "raw_execution_blocked.csv"),
            logger=self.logger,
            enabled=True,
            max_hold_events=2,
        )

        raw_event = ExecutionEventObj(
            "SIMULATED_ORDER_PREPARED",
            "raw_execution_bypass",
            execution_event_id="RAW-BYPASS",
            market="BTC-EUR",
            signal_strength=0.9,
            spread_pct=0.05,
        )

        with self.assertRaises(RuntimeError):
            manager.process(raw_event)

        self.assertIsNone(manager._active_position)

    def test_market_data_update_position_manager_rejects_raw_execution_event(self):
        engine = MarketDataEngine(
            feature_engine_enabled=False,
            strategy_engine_enabled=False,
            risk_engine_enabled=False,
            execution_engine_enabled=False,
            position_manager_enabled=True,
            accounting_engine_enabled=True,
            accounting_trade_ledger_path=str(self.tmp_path / "trade_ledger_raw.csv"),
            accounting_account_state_path=str(self.tmp_path / "account_state_raw.csv"),
            accounting_open_position_state_path=str(self.tmp_path / "account_state_raw.json"),
        )

        raw_event = ExecutionEventObj(
            "SIMULATED_ORDER_PREPARED",
            "raw_execution_bypass",
            execution_event_id="RAW-BYPASS-PIPELINE",
            market="BTC-EUR",
            signal_strength=0.9,
            spread_pct=0.05,
        )

        result = engine.update_position_manager(raw_event)
        self.assertIsNone(result)

    def test_restart_then_replay_same_fill_remains_idempotent(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)
        event = ExecutionEventObj("SIMULATED_ORDER_PREPARED", "entry_signal", execution_event_id="FILL-123")

        engine.process_execution(
            event,
            bid=100.0,
            ask=100.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
        )
        trade_id_before = engine.open_position.trade_id
        available_before = engine.available_balance

        recovered = self._restart(fee_rate=0.0, slippage_bps=0.0)
        recovered.process_execution(
            event,
            bid=101.0,
            ask=101.0,
            timestamp_utc="2026-09-06T00:00:10+00:00",
        )

        self.assertIsNotNone(recovered.open_position)
        self.assertEqual(recovered.open_position.trade_id, trade_id_before)
        self.assertAlmostEqual(recovered.available_balance, available_before, places=10)
        self.assertEqual(len(self._ledger_rows()), 0)

    def test_genuinely_different_successful_fill_is_processed_normally(self):
        engine = self._engine(fee_rate=0.0, slippage_bps=0.0)

        engine.process_execution(
            ExecutionEventObj("SIMULATED_ORDER_PREPARED", "entry_signal", execution_event_id="FILL-ENTRY-1"),
            bid=100.0,
            ask=100.0,
            timestamp_utc="2026-09-06T00:00:00+00:00",
        )

        closed = engine.process_execution(
            ExecutionEventObj("SIMULATED_ORDER_PREPARED", "exit_signal", execution_event_id="FILL-EXIT-2"),
            bid=110.0,
            ask=111.0,
            timestamp_utc="2026-09-06T00:01:00+00:00",
        )

        self.assertIsNotNone(closed)
        self.assertEqual(len(self._ledger_rows()), 1)


if __name__ == "__main__":
    unittest.main()
