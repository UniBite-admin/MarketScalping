import json
import os
import tempfile
import unittest

from market_data_engine import MarketDataEngine
from paper_backtest_comparator import compare_paper_to_backtest
from paper_session_evidence import PaperSessionEvidenceCollector


class _FakeAccountingEngine:
    def __init__(self):
        self.starting_balance = 1000.0
        self.available_balance = 995.0
        self.realized_pnl = 12.0
        self.unrealized_pnl = 3.0
        self.equity = 1008.0
        self.cumulative_fees = 4.0
        self.cumulative_slippage = 1.0
        self.recovery_status = "VALID"
        self.last_decision = type("Decision", (), {"status": "ACCEPTED", "reason": "accepted"})()
        self.open_position = {
            "trade_id": "TRD-000001",
            "symbol": "BTC-EUR",
            "side": "LONG",
            "entry_price": 1000.0,
            "position_size": 0.25,
            "entry_timestamp_utc": "2026-09-16T12:00:00+00:00",
        }


class _FakePositionManager:
    def __init__(self):
        self._active_position = {
            "trade_id": "TRD-000001",
            "market": "BTC-EUR",
            "symbol": "BTC-EUR",
            "side": "LONG",
            "entry_time_utc": "2026-09-16T12:00:00+00:00",
            "entry_price": 1000.0,
            "position_size": 0.25,
            "active": True,
        }


class PaperSessionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def _collector(self, **overrides):
        base = {
            "market": "BTC-EUR",
            "data_source": "Bitvavo WebSocket",
            "session_start_utc": "2026-09-16T12:00:00+00:00",
            "session_end_utc": "2026-09-16T12:10:00+00:00",
            "strategy_config": {"name": "baseline_momentum", "strategy_identity": "baseline_momentum_v1"},
            "risk_config": {"name": "simulation_risk", "risk_identity": "risk_v1"},
            "execution_config": {"mode": "SIMULATED_ORDER_PREPARED", "engine": "ExecutionEngine"},
            "fee_config": {"fee_rate": 0.001},
            "spread_config": {"spread_pct": 0.002},
            "slippage_config": {"slippage_bps": 10},
            "latency_config": {"latency_ticks": 2},
            "runtime_artifacts": ["data/execution_simulation_btc_eur.csv", "data/risk_decisions_btc_eur.csv"],
            "session_root_dir": os.path.join(self.tempdir.name, "paper_sessions"),
            "source_kind": "live_runtime_session",
        }
        base.update(overrides)
        return PaperSessionEvidenceCollector(**base)

    def test_valid_session_creates_valid_paper_result(self):
        collector = self._collector()
        paper_result = collector.finalize(
            accounting_engine=_FakeAccountingEngine(),
            position_manager=_FakePositionManager(),
            strategy_decisions=[{"action": "CANDIDATE_TRADE"}],
            risk_decisions=[{"approved": True, "risk_action": "APPROVED_SIMULATION"}],
            execution_events=[{"execution_action": "SIMULATED_ORDER_PREPARED"}],
            accounting_decisions=[{"status": "ACCEPTED", "financial_effect_applied": True}],
            position_events=[{"lifecycle_action": "OPENED", "status": "OPEN"}],
            data_quality_incidents=[{"type": "none"}],
        )
        self.assertIn("paper_session_id", paper_result)
        self.assertIn("paper_result", paper_result)
        self.assertEqual(paper_result["paper_result"]["market"], "BTC-EUR")
        self.assertEqual(paper_result["paper_result"]["authority_boundary"], "read_only_evidence")

    def test_unique_session_identity(self):
        collector_1 = self._collector()
        collector_2 = self._collector()
        self.assertNotEqual(collector_1.paper_session_id, collector_2.paper_session_id)

    def test_runtime_engine_creates_session_bound_paper_result(self):
        engine = MarketDataEngine(
            market="BTC-EUR",
            ws_url="ws://localhost:1",
            debug=False,
            reconnect_delay=0.1,
            max_reconnect_attempts=1,
            feature_output_path=os.path.join(self.tempdir.name, "features.csv"),
            strategy_output_path=os.path.join(self.tempdir.name, "strategy.csv"),
            risk_output_path=os.path.join(self.tempdir.name, "risk.csv"),
            execution_output_path=os.path.join(self.tempdir.name, "execution.csv"),
            position_output_path=os.path.join(self.tempdir.name, "positions.csv"),
            accounting_trade_ledger_path=os.path.join(self.tempdir.name, "trade_ledger.csv"),
            accounting_account_state_path=os.path.join(self.tempdir.name, "account_state.csv"),
            accounting_open_position_state_path=os.path.join(self.tempdir.name, "open_position.json"),
            accounting_strategy_name="baseline_momentum",
            accounting_starting_balance=1000.0,
            accounting_order_notional_eur=10.0,
            accounting_fee_rate=0.001,
            accounting_slippage_bps=1.0,
        )
        engine.recovery_status = "READY"
        engine.connection_state = "receiving_ticker"
        engine.start_paper_session()

        payload = {"event": "ticker", "market": "BTC-EUR", "bestBid": 100.0, "bestAsk": 101.0, "lastPrice": 100.5}
        engine.handle_control_message(payload)
        engine.finalize_paper_session()

        self.assertIsNotNone(engine.paper_result)
        self.assertIn("paper_session_id", engine.paper_result)
        self.assertIn("paper_result", engine.paper_result)
        self.assertEqual(engine.paper_result["paper_result"]["market"], "BTC-EUR")
        self.assertTrue(os.path.exists(engine.paper_result["artifact_path"]))

    def test_session_start_end_metadata(self):
        collector = self._collector()
        self.assertEqual(collector.session_start_utc, "2026-09-16T12:00:00+00:00")
        self.assertEqual(collector.session_end_utc, "2026-09-16T12:10:00+00:00")

    def test_configuration_identity_captured(self):
        collector = self._collector()
        self.assertIn("strategy_configuration", collector.configuration_snapshot)
        self.assertIn("configuration_identity", collector.configuration_snapshot)

    def test_operational_event_counters_captured(self):
        collector = self._collector()
        result = collector.finalize(
            accounting_engine=_FakeAccountingEngine(),
            position_manager=_FakePositionManager(),
            strategy_decisions=[{"action": "CANDIDATE_TRADE"}, {"action": "NO_TRADE"}],
            risk_decisions=[{"approved": True}, {"approved": False}],
            execution_events=[{"execution_action": "SIMULATED_ORDER_PREPARED"}, {"execution_action": "SKIPPED"}],
            accounting_decisions=[{"status": "ACCEPTED", "financial_effect_applied": True}, {"status": "REJECTED", "financial_effect_applied": False}],
            position_events=[{"lifecycle_action": "OPENED", "status": "OPEN"}],
            data_quality_incidents=[{"type": "none"}],
        )
        evidence = result["paper_result"]
        self.assertEqual(evidence["observed_assumptions"]["strategy_decision_count"], 2)
        self.assertEqual(evidence["observed_assumptions"]["risk_decision_count"], 2)
        self.assertEqual(evidence["observed_assumptions"]["execution_event_count"], 2)

    def test_financial_summary_comes_from_accounting_engine_authority(self):
        collector = self._collector()
        result = collector.finalize(
            accounting_engine=_FakeAccountingEngine(),
            position_manager=_FakePositionManager(),
            strategy_decisions=[],
            risk_decisions=[],
            execution_events=[],
            accounting_decisions=[],
            position_events=[],
            data_quality_incidents=[],
        )
        evidence = result["paper_result"]
        self.assertEqual(evidence["final_equity"], 1008.0)
        self.assertEqual(evidence["realized_pnl"], 12.0)
        self.assertEqual(evidence["financial_summary"]["starting_balance"], 1000.0)

    def test_position_summary_remains_derived(self):
        collector = self._collector()
        result = collector.finalize(
            accounting_engine=_FakeAccountingEngine(),
            position_manager=_FakePositionManager(),
            strategy_decisions=[],
            risk_decisions=[],
            execution_events=[],
            accounting_decisions=[],
            position_events=[],
            data_quality_incidents=[],
        )
        evidence = result["paper_result"]
        self.assertIn("position_summary", evidence)
        self.assertEqual(evidence["position_summary"]["market"], "BTC-EUR")
        self.assertEqual(evidence["position_summary"]["derived_from"], "AccountingEngine.open_position")

    def test_artifact_lineage_present(self):
        collector = self._collector()
        result = collector.finalize(
            accounting_engine=_FakeAccountingEngine(),
            position_manager=_FakePositionManager(),
            strategy_decisions=[],
            risk_decisions=[],
            execution_events=[],
            accounting_decisions=[],
            position_events=[],
            data_quality_incidents=[],
        )
        self.assertIn("evidence_lineage", result["paper_result"])
        self.assertTrue(result["paper_result"]["evidence_lineage"]["runtime_artifacts"])

    def test_deterministic_canonical_serialization_signature(self):
        collector = self._collector()
        result_1 = collector.finalize(
            accounting_engine=_FakeAccountingEngine(),
            position_manager=_FakePositionManager(),
            strategy_decisions=[{"action": "CANDIDATE_TRADE"}],
            risk_decisions=[{"approved": True}],
            execution_events=[{"execution_action": "SIMULATED_ORDER_PREPARED"}],
            accounting_decisions=[{"status": "ACCEPTED", "financial_effect_applied": True}],
            position_events=[{"lifecycle_action": "OPENED", "status": "OPEN"}],
            data_quality_incidents=[],
        )
        result_2 = collector.finalize(
            accounting_engine=_FakeAccountingEngine(),
            position_manager=_FakePositionManager(),
            strategy_decisions=[{"action": "CANDIDATE_TRADE"}],
            risk_decisions=[{"approved": True}],
            execution_events=[{"execution_action": "SIMULATED_ORDER_PREPARED"}],
            accounting_decisions=[{"status": "ACCEPTED", "financial_effect_applied": True}],
            position_events=[{"lifecycle_action": "OPENED", "status": "OPEN"}],
            data_quality_incidents=[],
        )
        self.assertEqual(result_1["paper_result"]["evidence_signature"], result_2["paper_result"]["evidence_signature"])

    def test_missing_session_boundary_fails_closed(self):
        with self.assertRaises(ValueError):
            PaperSessionEvidenceCollector(
                market="BTC-EUR",
                data_source="Bitvavo WebSocket",
                strategy_config={"name": "baseline_momentum"},
                risk_config={"name": "risk"},
                execution_config={"mode": "SIMULATED_ORDER_PREPARED"},
                fee_config={"fee_rate": 0.001},
                spread_config={"spread_pct": 0.002},
                slippage_config={"slippage_bps": 10},
                latency_config={"latency_ticks": 2},
                runtime_artifacts=["data/execution_simulation_btc_eur.csv"],
                session_root_dir=os.path.join(self.tempdir.name, "paper_sessions"),
                session_start_utc=None,
                session_end_utc=None,
                source_kind="live_runtime_session",
            ).finalize(
                accounting_engine=_FakeAccountingEngine(),
                position_manager=_FakePositionManager(),
                strategy_decisions=[],
                risk_decisions=[],
                execution_events=[],
                accounting_decisions=[],
                position_events=[],
                data_quality_incidents=[],
            )

    def test_missing_authoritative_financial_state_fails_closed(self):
        collector = self._collector()
        with self.assertRaises(ValueError):
            collector.finalize(
                accounting_engine=None,
                position_manager=_FakePositionManager(),
                strategy_decisions=[],
                risk_decisions=[],
                execution_events=[],
                accounting_decisions=[],
                position_events=[],
                data_quality_incidents=[],
            )

    def test_missing_required_configuration_fails_closed(self):
        collector = self._collector(strategy_config={})
        with self.assertRaises(ValueError):
            collector.finalize(
                accounting_engine=_FakeAccountingEngine(),
                position_manager=_FakePositionManager(),
                strategy_decisions=[],
                risk_decisions=[],
                execution_events=[],
                accounting_decisions=[],
                position_events=[],
                data_quality_incidents=[],
            )

    def test_evidence_layer_does_not_mutate_accounting_state(self):
        accounting = _FakeAccountingEngine()
        before = {
            "available_balance": accounting.available_balance,
            "realized_pnl": accounting.realized_pnl,
            "equity": accounting.equity,
        }
        collector = self._collector()
        collector.finalize(
            accounting_engine=accounting,
            position_manager=_FakePositionManager(),
            strategy_decisions=[],
            risk_decisions=[],
            execution_events=[],
            accounting_decisions=[],
            position_events=[],
            data_quality_incidents=[],
        )
        self.assertEqual(accounting.available_balance, before["available_balance"])
        self.assertEqual(accounting.realized_pnl, before["realized_pnl"])
        self.assertEqual(accounting.equity, before["equity"])

    def test_paper_result_separate_from_backtest_result(self):
        collector = self._collector()
        paper_result = collector.finalize(
            accounting_engine=_FakeAccountingEngine(),
            position_manager=_FakePositionManager(),
            strategy_decisions=[{"action": "CANDIDATE_TRADE"}],
            risk_decisions=[{"approved": True}],
            execution_events=[{"execution_action": "SIMULATED_ORDER_PREPARED"}],
            accounting_decisions=[{"status": "ACCEPTED", "financial_effect_applied": True}],
            position_events=[{"lifecycle_action": "OPENED", "status": "OPEN"}],
            data_quality_incidents=[],
        )
        backtest_result = {
            "final_equity": 1010.0,
            "realized_pnl": 10.0,
            "metrics": {"net_pnl": 10.0, "win_rate": 0.5},
            "observed_assumptions": {"event_count": 1, "first_event_time_utc": "2026-09-16T12:00:00+00:00", "last_event_time_utc": "2026-09-16T12:10:00+00:00"},
            "latency_configuration": {"latency_ticks": 2},
            "spread_configuration": {"spread_pct": 0.002},
            "fee_configuration": {"fee_rate": 0.001},
            "slippage_configuration": {"slippage_bps": 10},
            "strategy_decisions": [{"action": "CANDIDATE_TRADE"}],
            "risk_decisions": [{"approved": True}],
            "execution_events": [{"execution_action": "SIMULATED_ORDER_PREPARED"}],
            "accounting_decisions": [{"status": "ACCEPTED"}],
        }
        comparison = compare_paper_to_backtest(paper_result["paper_result"], backtest_result)
        self.assertIn("paper_result", comparison.as_dict())
        self.assertIn("backtest_result", comparison.as_dict())
        self.assertIsNot(paper_result["paper_result"], backtest_result)

    def test_synthetic_fixtures_not_mistaken_for_operational_evidence(self):
        with self.assertRaises(ValueError):
            PaperSessionEvidenceCollector(
                market="BTC-EUR",
                data_source="fixture",
                session_start_utc="2026-09-16T12:00:00+00:00",
                session_end_utc="2026-09-16T12:10:00+00:00",
                strategy_config={"name": "baseline_momentum", "strategy_identity": "baseline_momentum_v1"},
                risk_config={"name": "simulation_risk", "risk_identity": "risk_v1"},
                execution_config={"mode": "SIMULATED_ORDER_PREPARED", "engine": "ExecutionEngine"},
                fee_config={"fee_rate": 0.001},
                spread_config={"spread_pct": 0.002},
                slippage_config={"slippage_bps": 10},
                latency_config={"latency_ticks": 2},
                runtime_artifacts=[],
                session_root_dir=os.path.join(self.tempdir.name, "paper_sessions"),
                source_kind="synthetic_fixture",
            ).finalize(
                accounting_engine=_FakeAccountingEngine(),
                position_manager=_FakePositionManager(),
                strategy_decisions=[],
                risk_decisions=[],
                execution_events=[],
                accounting_decisions=[],
                position_events=[],
                data_quality_incidents=[],
            )


if __name__ == "__main__":
    unittest.main()
