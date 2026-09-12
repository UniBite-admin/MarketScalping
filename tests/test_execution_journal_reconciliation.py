import csv
import os
import tempfile
import unittest
from pathlib import Path

from accounting_engine import AccountingEngine
from execution_journal_reconciler import ExecutionJournalReconciler
from position_manager import PositionManager


class DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class ExecutionJournalReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.logger = DummyLogger()

    def tearDown(self):
        self.tmp.cleanup()

    def _engine(self, accepted_ids=None):
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
        if accepted_ids is not None:
            engine._processed_successful_execution_ids = set(accepted_ids)
            engine._processed_successful_execution_id_order = list(accepted_ids)
        return engine

    def _write_journal(self, rows, name="journal.csv"):
        path = self.tmp_path / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "execution_event_id",
                "timestamp_utc",
                "market",
                "strategy_action",
                "risk_action",
                "execution_action",
                "reason",
                "signal_strength",
                "spread_pct",
            ])
            writer.writerows(rows)
        return str(path)

    def test_accepted_id_and_matching_journal_safe(self):
        engine = self._engine(accepted_ids=["evt-001"])
        journal_path = self._write_journal([
            ["evt-001", "2026-01-01T00:00:00+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")
        self.assertEqual(result["missing_journal_ids"], [])

    def test_accepted_id_missing_journal_blocked(self):
        engine = self._engine(accepted_ids=["evt-001"])
        journal_path = self._write_journal([])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "BLOCKED_ON_DIVERGENCE")
        self.assertEqual(result["missing_journal_ids"], ["evt-001"])

    def test_zero_accepted_and_empty_journal_safe(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")

    def test_zero_accepted_and_missing_journal_safe(self):
        engine = self._engine(accepted_ids=[])
        journal_path = str(self.tmp_path / "missing.csv")

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")

    def test_unmatched_skipped_safe(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([
            ["evt-002", "2026-01-01T00:00:01+00:00", "BTC-EUR", "CANDIDATE_TRADE", "BLOCKED", "SKIPPED", "risk_rejected", "0.2", "0.05"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")
        self.assertIn("evt-002", result["unmatched_journal_ids"])

    def test_unmatched_failed_safe(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([
            ["evt-003", "2026-01-01T00:00:02+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "FAILED", "simulated_order_failed", "0.8", "0.02"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")

    def test_unmatched_no_action_safe(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([
            ["evt-004", "2026-01-01T00:00:03+00:00", "BTC-EUR", "CANDIDATE_TRADE", "NO_ACTION", "NO_ACTION", "no_strategy_candidate", "0.4", "0.04"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")

    def test_simulated_without_accepted_blocked(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([
            ["evt-005", "2026-01-01T00:00:04+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "BLOCKED_ON_DIVERGENCE")
        self.assertEqual(result["blocking_reason"], "SIMULATED_ORDER_PREPARED_without_accepted_accounting_id")

    def test_exact_duplicate_journal_rows_safe(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([
            ["evt-006", "2026-01-01T00:00:05+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SKIPPED", "duplicate_reason", "0.3", "0.03"],
            ["evt-006", "2026-01-01T00:00:05+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SKIPPED", "duplicate_reason", "0.3", "0.03"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")
        self.assertEqual(result["duplicate_identities"], ["evt-006"])

    def test_conflicting_duplicate_identity_blocked(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([
            ["evt-007", "2026-01-01T00:00:06+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "first", "0.8", "0.02"],
            ["evt-007", "2026-01-01T00:00:06+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "second", "0.8", "0.02"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "BLOCKED_ON_DIVERGENCE")
        self.assertIn("evt-007", result["conflicting_identities"])

    def test_malformed_unrelated_row_safe(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([
            ["evt-008", "malformed_time", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SKIPPED", "risk_rejected", "x", "0.02"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")
        self.assertEqual(result["malformed_records"], ["evt-008"])

    def test_malformed_accepted_linked_row_blocked(self):
        engine = self._engine(accepted_ids=["evt-009"])
        journal_path = self._write_journal([
            ["evt-009", "malformed_time", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "BLOCKED_ON_DIVERGENCE")

    def test_multiple_accepted_ids_all_present_safe(self):
        engine = self._engine(accepted_ids=["evt-010", "evt-011"])
        journal_path = self._write_journal([
            ["evt-010", "2026-01-01T00:00:10+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
            ["evt-011", "2026-01-01T00:00:11+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "exit_signal", "0.95", "0.02"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "SAFE")
        self.assertEqual(result["missing_journal_ids"], [])

    def test_one_accepted_id_missing_blocked(self):
        engine = self._engine(accepted_ids=["evt-010", "evt-012"])
        journal_path = self._write_journal([
            ["evt-010", "2026-01-01T00:00:10+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "BLOCKED_ON_DIVERGENCE")
        self.assertIn("evt-012", result["missing_journal_ids"])

    def test_journal_cannot_create_financial_acceptance(self):
        engine = self._engine(accepted_ids=[])
        journal_path = self._write_journal([
            ["evt-013", "2026-01-01T00:00:13+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "BLOCKED_ON_DIVERGENCE")
        self.assertNotIn("evt-013", result["accepted_accounting_ids_checked"])

    def test_reconciliation_does_not_mutate_accounting(self):
        engine = self._engine(accepted_ids=["evt-014"])
        before = {
            "processed": set(engine._processed_successful_execution_ids),
            "order": list(engine._processed_successful_execution_id_order),
        }
        journal_path = self._write_journal([
            ["evt-014", "2026-01-01T00:00:14+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
        ])

        ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(engine._processed_successful_execution_ids, before["processed"])
        self.assertEqual(engine._processed_successful_execution_id_order, before["order"])

    def test_reconciliation_does_not_mutate_position_manager(self):
        engine = self._engine(accepted_ids=[])
        pm = PositionManager(
            output_path=str(self.tmp_path / "position.csv"),
            logger=self.logger,
            enabled=True,
        )
        before = pm._ledger.copy() if hasattr(pm, "_ledger") else []
        journal_path = self._write_journal([
            ["evt-015", "2026-01-01T00:00:15+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
        ])

        ExecutionJournalReconciler.reconcile(journal_path, engine)

        if hasattr(pm, "_ledger"):
            self.assertEqual(pm._ledger, before)

    def test_repeated_reconcile_is_deterministic(self):
        engine = self._engine(accepted_ids=["evt-016", "evt-017"])
        journal_path = self._write_journal([
            ["evt-016", "2026-01-01T00:00:16+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
            ["evt-017", "2026-01-01T00:00:17+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "exit_signal", "0.95", "0.02"],
        ])

        first = ExecutionJournalReconciler.reconcile(journal_path, engine)
        second = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(first, second)

    def test_invalid_accounting_state_is_not_repaired(self):
        engine = self._engine(accepted_ids=["evt-018"])
        engine._processed_successful_execution_ids = set()
        engine._processed_successful_execution_id_order = []
        journal_path = self._write_journal([
            ["evt-018", "2026-01-01T00:00:18+00:00", "BTC-EUR", "CANDIDATE_TRADE", "APPROVED_SIMULATION", "SIMULATED_ORDER_PREPARED", "entry_signal", "0.9", "0.01"],
        ])

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "BLOCKED_ON_DIVERGENCE")
        self.assertEqual(engine._processed_successful_execution_ids, set())

    def test_trade_ledger_and_account_snapshot_cannot_be_authority(self):
        engine = self._engine(accepted_ids=["evt-019"])
        trade_path = self.tmp_path / "trade_ledger.csv"
        trade_path.write_text("trade_id,timestamp_utc,symbol,side,entry_price,exit_price,position_size,gross_pnl,fees,slippage,net_pnl,holding_time_seconds,strategy,signal,confidence,close_reason,entry_timestamp_utc,exit_timestamp_utc\nTRADE-1,2026-01-01T00:00:19+00:00,BTC-EUR,LONG,100,105,1,5,0,0,5,60,baseline,entry_signal,0.9,exit,2026-01-01T00:00:18+00:00,2026-01-01T00:00:19+00:00\n", encoding="utf-8")
        snapshot_path = self.tmp_path / "account_state.csv"
        snapshot_path.write_text("timestamp_utc,starting_balance,available_balance,realized_pnl,unrealized_pnl,equity,cumulative_fees,cumulative_slippage,peak_equity,current_drawdown,maximum_drawdown\n2026-01-01T00:00:19+00:00,1000,1000,0,0,1000,0,0,1000,0,0\n", encoding="utf-8")
        journal_path = str(self.tmp_path / "missing_journal.csv")

        result = ExecutionJournalReconciler.reconcile(journal_path, engine)

        self.assertEqual(result["overall_status"], "BLOCKED_ON_DIVERGENCE")
        self.assertEqual(result["missing_journal_ids"], ["evt-019"])


if __name__ == "__main__":
    unittest.main()
