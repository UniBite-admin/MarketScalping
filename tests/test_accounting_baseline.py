import csv
import tempfile
import unittest
from pathlib import Path

from accounting_engine import AccountingEngine


class DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class ExecutionEventObj:
    def __init__(self, action: str, reason: str = "risk_approved_dry_run_only", execution_event_id: str | None = None):
        self.execution_action = action
        self.reason = reason
        self.market = "BTC-EUR"
        self.execution_event_id = execution_event_id


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
