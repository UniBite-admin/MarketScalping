import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from accounting_engine import AccountingEngine, AccountingDecision
from execution_engine import ExecutionEngine, ExecutionEvent
from market_data_engine import MarketDataEngine


class Step101PaperTradingTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _engine_paths(self, name: str):
        return {
            "feature_output_path": str(self.root / f"{name}_features.csv"),
            "strategy_output_path": str(self.root / f"{name}_strategy.csv"),
            "risk_output_path": str(self.root / f"{name}_risk.csv"),
            "execution_output_path": str(self.root / f"{name}_execution.csv"),
            "position_output_path": str(self.root / f"{name}_positions.csv"),
            "accounting_trade_ledger_path": str(self.root / f"{name}_trade_ledger.csv"),
            "accounting_account_state_path": str(self.root / f"{name}_account_state.csv"),
            "accounting_open_position_state_path": str(self.root / f"{name}_open_position_state.json"),
        }

    def test_stale_market_data_blocks_forward_processing(self):
        engine = MarketDataEngine(**self._engine_paths("stale"))
        engine.recovery_status = "READY"
        engine.connection_state = "receiving_ticker"
        engine._last_market_update_monotonic = time.monotonic() - 30
        engine.set_status("stale_data", "No BTC-EUR update for 30.0s; waiting for new data")

        with mock.patch.object(engine, "update_features") as mock_features, \
             mock.patch.object(engine, "update_strategy") as mock_strategy, \
             mock.patch.object(engine, "update_risk") as mock_risk, \
             mock.patch.object(engine, "update_execution") as mock_execution:
            payload = {"event": "ticker", "market": "BTC-EUR", "bestBid": 100.0, "bestAsk": 101.0, "lastPrice": 100.5}
            engine.handle_control_message(payload)

        mock_features.assert_not_called()
        mock_strategy.assert_not_called()
        mock_risk.assert_not_called()
        mock_execution.assert_not_called()
        self.assertEqual(engine.connection_state, "stale_data")

    def test_websocket_disconnect_and_reconnect_recovery(self):
        engine = MarketDataEngine(**self._engine_paths("ws"))
        engine.on_close(None, 1006, "connection lost")
        self.assertEqual(engine.connection_state, "disconnected")
        self.assertIn("connection lost", engine.last_error)

        ws = mock.Mock()
        engine.on_open(ws)
        self.assertEqual(engine.connection_state, "subscription_sent")
        self.assertIn("Subscription sent for BTC-EUR", engine.status_message)
        ws.send.assert_called_once()

    def test_repeated_malformed_churn_messages_block_pipeline(self):
        engine = MarketDataEngine(**self._engine_paths("churn"))
        engine.recovery_status = "READY"
        engine.connection_state = "receiving_ticker"

        churn_payloads = [
            {"event": "ticker", "market": "BTC-EUR", "bestBid": "bad", "bestAsk": 101.0, "lastPrice": 100.5},
            {"event": "ticker", "market": "BTC-EUR", "bestBid": 100.0, "bestAsk": 101.0, "lastPrice": -1.0},
            {"event": "subscribed", "subscriptions": {"ticker": ["ETH-EUR"], "trades": ["BTC-EUR"]}},
        ]

        with mock.patch.object(engine, "update_features") as mock_features, \
             mock.patch.object(engine, "update_strategy") as mock_strategy, \
             mock.patch.object(engine, "update_risk") as mock_risk, \
             mock.patch.object(engine, "update_execution") as mock_execution, \
             mock.patch.object(engine, "update_accounting") as mock_accounting, \
             mock.patch.object(engine, "update_position_manager") as mock_position_manager:
            for payload in churn_payloads:
                engine.handle_control_message(payload)

        self.assertIn(engine.connection_state, {"message_error", "subscription_error"})
        mock_features.assert_not_called()
        mock_strategy.assert_not_called()
        mock_risk.assert_not_called()
        mock_execution.assert_not_called()
        mock_accounting.assert_not_called()
        mock_position_manager.assert_not_called()

    def test_api_error_response_sets_fail_closed_state_without_mutation(self):
        engine = MarketDataEngine(**self._engine_paths("api"))
        engine.recovery_status = "READY"
        engine.connection_state = "receiving_ticker"

        with mock.patch.object(engine, "update_features") as mock_features, \
             mock.patch.object(engine, "update_strategy") as mock_strategy, \
             mock.patch.object(engine, "update_risk") as mock_risk, \
             mock.patch.object(engine, "update_execution") as mock_execution, \
             mock.patch.object(engine, "update_accounting") as mock_accounting, \
             mock.patch.object(engine, "update_position_manager") as mock_position_manager:
            engine.handle_control_message({"error": "Bitvavo API unavailable"})

        self.assertEqual(engine.connection_state, "api_error")
        self.assertEqual(engine.status_message, "Bitvavo returned an error message")
        self.assertEqual(engine.last_error, "Bitvavo API unavailable")
        mock_features.assert_not_called()
        mock_strategy.assert_not_called()
        mock_risk.assert_not_called()
        mock_execution.assert_not_called()
        mock_accounting.assert_not_called()
        mock_position_manager.assert_not_called()

    def test_duplicate_execution_event_is_rejected_without_financial_effect(self):
        engine = AccountingEngine(
            trade_ledger_path=str(self.root / "dup_trade_ledger.csv"),
            account_state_path=str(self.root / "dup_account_state.csv"),
            open_position_state_path=str(self.root / "dup_open_position_state.json"),
            logger=__import__("logging").getLogger("dup-accounting"),
            enabled=True,
            starting_balance=1000.0,
            order_notional_eur=10.0,
        )
        event = ExecutionEvent(
            execution_event_id="dup-1",
            timestamp_utc="2026-09-17T12:00:00+00:00",
            market="BTC-EUR",
            strategy_action="CANDIDATE_TRADE",
            risk_action="APPROVED_SIMULATION",
            execution_action="SIMULATED_ORDER_PREPARED",
            reason="risk_approved_dry_run_only",
            signal_strength=0.8,
            spread_pct=0.01,
        )

        engine.process_execution(event, bid=100.0, ask=101.0, timestamp_utc=event.timestamp_utc, signal="test", confidence=0.8)
        engine.process_execution(event, bid=100.0, ask=101.0, timestamp_utc=event.timestamp_utc, signal="test", confidence=0.8)

        self.assertEqual(engine.last_decision.status, "DUPLICATE")
        self.assertEqual(len(engine._processed_successful_execution_ids), 1)
        self.assertIn("dup-1", engine._processed_successful_execution_ids)

    def test_corrupted_checkpoint_blocks_startup_recovery(self):
        checkpoint_path = self.root / "corrupt_checkpoint.json"
        checkpoint_path.write_text('{"version": 1, "account_state": {', encoding="utf-8")

        paths = self._engine_paths("corrupt")
        paths["accounting_open_position_state_path"] = str(checkpoint_path)
        engine = MarketDataEngine(**paths)

        self.assertEqual(engine.recovery_status, "BLOCKED_ON_DIVERGENCE")
        self.assertIn("accounting_state_invalid", engine.last_error.lower())

    def test_execution_journal_divergence_blocks_market_processing(self):
        accounting_path = self.root / "divergence_open_state.json"
        valid_checkpoint = {
            "version": 1,
            "timestamp_utc": "2026-09-17T00:00:00+00:00",
            "processed_successful_execution_ids": ["evt-001"],
            "account_state": {
                "starting_balance": 1000.0,
                "available_balance": 1000.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "equity": 1000.0,
                "cumulative_fees": 0.0,
                "cumulative_slippage": 0.0,
                "peak_equity": 1000.0,
                "current_drawdown": 0.0,
                "maximum_drawdown": 0.0,
            },
            "counters": {"trade_counter": 0, "order_counter": 0, "fill_counter": 0},
            "last_mark_price": 100.0,
            "open_position": None,
        }
        accounting_path.write_text(json.dumps(valid_checkpoint), encoding="utf-8")

        execution_path = self.root / "divergence_execution.csv"
        execution_path.write_text(
            "execution_event_id,timestamp_utc,market,strategy_action,risk_action,execution_action,reason,signal_strength,spread_pct\n"
            "evt-999,2026-09-17T00:00:01+00:00,BTC-EUR,CANDIDATE_TRADE,APPROVED_SIMULATION,SIMULATED_ORDER_PREPARED,risk_approved_dry_run_only,0.5,0.01\n",
            encoding="utf-8",
        )

        paths = self._engine_paths("divergence")
        paths["execution_output_path"] = str(execution_path)
        paths["accounting_open_position_state_path"] = str(accounting_path)
        engine = MarketDataEngine(**paths)

        self.assertEqual(engine.recovery_status, "BLOCKED_ON_DIVERGENCE")
        self.assertIn("simulated_order_prepared", engine.last_error.lower())


if __name__ == "__main__":
    unittest.main()
