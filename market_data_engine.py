import json
import logging
import math
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import websocket

from accounting_engine import AccountingDecision, AccountingEngine
from execution_journal_reconciler import ExecutionJournalReconciler
from feature_signal_engine import FeatureSignalEngine
from execution_engine import ExecutionEngine
from paper_session_evidence import PaperSessionEvidenceCollector
from position_manager import PositionManager
from risk_engine import RiskEngine
from strategy_engine import StrategyEngine


WS_URL = "wss://ws.bitvavo.com/v2"
MARKET = "BTC-EUR"
LOG_DIR = "logs"
LOG_FILE = "market_data.log"


@dataclass
class TickerState:
    market: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def spread(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return self.ask - self.bid

    @property
    def spread_percentage(self) -> float | None:
        spread = self.spread
        if spread is None or self.bid in (None, 0):
            return None
        return (spread / self.bid) * 100

    @property
    def mid_price(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2


def configure_logging(debug: bool = False) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("market_data")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        log_path = os.path.join(LOG_DIR, LOG_FILE)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class MarketDataEngine:
    def __init__(
        self,
        market: str = MARKET,
        ws_url: str = WS_URL,
        debug: bool = False,
        reconnect_delay: float = 3.0,
        max_reconnect_attempts: int = 5,
        render_interval: float = 0.25,
        stale_after_seconds: float = 5.0,
        stale_check_interval: float = 1.0,
        feature_output_path: str = "data/features_btc_eur.csv",
        feature_engine_enabled: bool = True,
        strategy_output_path: str = "data/strategy_decisions_btc_eur.csv",
        strategy_engine_enabled: bool = True,
        strategy_max_spread_pct: float = 0.02,
        strategy_max_tick_interval_ms: float = 2000.0,
        strategy_min_momentum_return: float = 0.0,
        risk_output_path: str = "data/risk_decisions_btc_eur.csv",
        risk_engine_enabled: bool = True,
        risk_emergency_stop: bool = False,
        risk_max_spread_pct: float = 0.02,
        risk_max_tick_interval_ms: float = 2000.0,
        risk_min_signal_strength: float = -1.0,
        risk_max_candidates_per_minute: int = 120,
        execution_output_path: str = "data/execution_simulation_btc_eur.csv",
        execution_engine_enabled: bool = True,
        position_output_path: str = "data/positions_simulation_btc_eur.csv",
        position_manager_enabled: bool = True,
        position_max_hold_events: int = 250,
        accounting_engine_enabled: bool = True,
        accounting_trade_ledger_path: str = "data/trade_ledger_btc_eur.csv",
        accounting_account_state_path: str = "data/account_state_btc_eur.csv",
        accounting_open_position_state_path: str = "data/accounting_open_position_state_btc_eur.json",
        accounting_strategy_name: str = "baseline_momentum",
        accounting_starting_balance: float = 1000.0,
        accounting_order_notional_eur: float = 10.0,
        accounting_fee_rate: float = 0.001,
        accounting_slippage_bps: float = 1.0,
    ):
        self.market = market
        self.ws_url = ws_url
        self.debug = debug
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.render_interval = render_interval
        self.stale_after_seconds = stale_after_seconds
        self.stale_check_interval = stale_check_interval
        self.feature_output_path = feature_output_path
        self.feature_engine_enabled = feature_engine_enabled
        self.strategy_output_path = strategy_output_path
        self.strategy_engine_enabled = strategy_engine_enabled
        self.strategy_max_spread_pct = strategy_max_spread_pct
        self.strategy_max_tick_interval_ms = strategy_max_tick_interval_ms
        self.strategy_min_momentum_return = strategy_min_momentum_return
        self.risk_output_path = risk_output_path
        self.risk_engine_enabled = risk_engine_enabled
        self.risk_emergency_stop = risk_emergency_stop
        self.risk_max_spread_pct = risk_max_spread_pct
        self.risk_max_tick_interval_ms = risk_max_tick_interval_ms
        self.risk_min_signal_strength = risk_min_signal_strength
        self.risk_max_candidates_per_minute = risk_max_candidates_per_minute
        self.execution_output_path = execution_output_path
        self.execution_engine_enabled = execution_engine_enabled
        self.position_output_path = position_output_path
        self.position_manager_enabled = position_manager_enabled
        self.position_max_hold_events = position_max_hold_events
        self.accounting_engine_enabled = accounting_engine_enabled
        self.accounting_trade_ledger_path = accounting_trade_ledger_path
        self.accounting_account_state_path = accounting_account_state_path
        self.accounting_open_position_state_path = accounting_open_position_state_path
        self.accounting_strategy_name = accounting_strategy_name
        self.accounting_starting_balance = accounting_starting_balance
        self.accounting_order_notional_eur = accounting_order_notional_eur
        self.accounting_fee_rate = accounting_fee_rate
        self.accounting_slippage_bps = accounting_slippage_bps

        self.logger = configure_logging(debug=debug)
        self.ws = None
        self.should_stop = False
        self.ticker_state = None
        self.connection_state = "idle"
        self.status_message = "Waiting to start"
        self.last_message_summary = "No messages received yet"
        self.last_error = "None"
        self._state_lock = threading.Lock()
        self._render_event = threading.Event()
        self._render_thread = None
        self._watchdog_thread = None
        self._screen_initialized = False
        self._last_frame = ""
        self._last_market_update_monotonic = time.monotonic()
        self._stale_warning_active = False
        self.recovery_status = "RECOVERY_NOT_COMPLETE"
        self._startup_recovery_attempted = False
        self.paper_session = None
        self.paper_session_id = None
        self.session_start_utc = None
        self.session_end_utc = None
        self.paper_result = None
        self._paper_session_strategy_decisions: list[dict] = []
        self._paper_session_risk_decisions: list[dict] = []
        self._paper_session_execution_events: list[dict] = []
        self._paper_session_accounting_decisions: list[dict] = []
        self._paper_session_position_events: list[dict] = []
        self._paper_session_data_quality_incidents: list[dict] = []

        self.feature_engine = None
        if self.feature_engine_enabled:
            self.feature_engine = FeatureSignalEngine(output_path=self.feature_output_path, logger=self.logger)
            self.logger.info("feature_engine_enabled path=%s", self.feature_output_path)
        else:
            self.logger.info("feature_engine_disabled")

        self.strategy_engine = None
        if self.strategy_engine_enabled:
            self.strategy_engine = StrategyEngine(
                output_path=self.strategy_output_path,
                logger=self.logger,
                max_spread_pct=self.strategy_max_spread_pct,
                max_tick_interval_ms=self.strategy_max_tick_interval_ms,
                min_momentum_return=self.strategy_min_momentum_return,
            )
            self.logger.info("strategy_engine_enabled path=%s", self.strategy_output_path)
        else:
            self.logger.info("strategy_engine_disabled")

        self.risk_engine = RiskEngine(
            output_path=self.risk_output_path,
            logger=self.logger,
            enabled=self.risk_engine_enabled,
            emergency_stop=self.risk_emergency_stop,
            max_spread_pct=self.risk_max_spread_pct,
            max_tick_interval_ms=self.risk_max_tick_interval_ms,
            min_signal_strength=self.risk_min_signal_strength,
            max_candidates_per_minute=self.risk_max_candidates_per_minute,
        )
        self.logger.info(
            "risk_engine_config enabled=%s emergency_stop=%s path=%s",
            self.risk_engine_enabled,
            self.risk_emergency_stop,
            self.risk_output_path,
        )

        self.execution_engine = ExecutionEngine(
            output_path=self.execution_output_path,
            logger=self.logger,
            enabled=self.execution_engine_enabled,
        )
        self.logger.info(
            "execution_engine_config enabled=%s path=%s",
            self.execution_engine_enabled,
            self.execution_output_path,
        )

        self.position_manager = PositionManager(
            output_path=self.position_output_path,
            logger=self.logger,
            enabled=self.position_manager_enabled,
            max_hold_events=self.position_max_hold_events,
        )
        self.logger.info(
            "position_manager_config enabled=%s path=%s max_hold_events=%s",
            self.position_manager_enabled,
            self.position_output_path,
            self.position_max_hold_events,
        )

        self.accounting_engine = AccountingEngine(
            trade_ledger_path=self.accounting_trade_ledger_path,
            account_state_path=self.accounting_account_state_path,
            open_position_state_path=self.accounting_open_position_state_path,
            logger=self.logger,
            enabled=self.accounting_engine_enabled,
            strategy_name=self.accounting_strategy_name,
            starting_balance=self.accounting_starting_balance,
            order_notional_eur=self.accounting_order_notional_eur,
            fee_rate=self.accounting_fee_rate,
            slippage_bps=self.accounting_slippage_bps,
        )
        self.logger.info(
            "accounting_engine_config enabled=%s trade_ledger=%s account_state=%s open_state=%s fee_rate=%s slippage_bps=%s",
            self.accounting_engine_enabled,
            self.accounting_trade_ledger_path,
            self.accounting_account_state_path,
            self.accounting_open_position_state_path,
            self.accounting_fee_rate,
            self.accounting_slippage_bps,
        )

        self.run_startup_recovery()

    def start_paper_session(self) -> dict[str, object] | None:
        if self.paper_session is not None:
            return self.paper_result

        self.session_start_utc = datetime.now(timezone.utc).isoformat()
        self.session_end_utc = self.session_start_utc
        self.paper_session = PaperSessionEvidenceCollector(
            market=self.market,
            data_source="Bitvavo WebSocket",
            session_start_utc=self.session_start_utc,
            session_end_utc=self.session_end_utc,
            strategy_config={
                "name": self.accounting_strategy_name,
                "strategy_identity": self.accounting_strategy_name,
                "max_spread_pct": self.strategy_max_spread_pct,
                "max_tick_interval_ms": self.strategy_max_tick_interval_ms,
                "min_momentum_return": self.strategy_min_momentum_return,
            },
            risk_config={
                "name": "simulation_risk",
                "risk_identity": "simulation_risk_v1",
                "max_spread_pct": self.risk_max_spread_pct,
                "max_tick_interval_ms": self.risk_max_tick_interval_ms,
                "min_signal_strength": self.risk_min_signal_strength,
                "max_candidates_per_minute": self.risk_max_candidates_per_minute,
            },
            execution_config={
                "mode": "SIMULATED_ORDER_PREPARED",
                "engine": "ExecutionEngine",
                "enabled": self.execution_engine_enabled,
            },
            fee_config={"fee_rate": self.accounting_fee_rate},
            spread_config={"spread_pct": self.strategy_max_spread_pct},
            slippage_config={"slippage_bps": self.accounting_slippage_bps},
            latency_config={
                "render_interval_seconds": self.render_interval,
                "stale_after_seconds": self.stale_after_seconds,
                "stale_check_interval_seconds": self.stale_check_interval,
                "reconnect_delay_seconds": self.reconnect_delay,
            },
            runtime_artifacts=[
                self.feature_output_path,
                self.strategy_output_path,
                self.risk_output_path,
                self.execution_output_path,
                self.position_output_path,
                self.accounting_trade_ledger_path,
                self.accounting_account_state_path,
                self.accounting_open_position_state_path,
            ],
            session_root_dir="data/paper_sessions",
            source_kind="live_runtime_session",
        )
        self.paper_session_id = self.paper_session.paper_session_id
        self.logger.info(
            "paper_session_started session_id=%s market=%s start_utc=%s",
            self.paper_session_id,
            self.market,
            self.session_start_utc,
        )
        return {"paper_session_id": self.paper_session_id, "paper_result": None, "artifact_path": None}

    def _record_data_quality_incident(self, incident_type: str, details: str) -> None:
        if self.paper_session is None:
            return
        self._paper_session_data_quality_incidents.append(
            {
                "type": incident_type,
                "details": details,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "source": "MarketDataEngine",
            }
        )

    def _record_runtime_event(self, collection_name: str, event: object) -> None:
        if self.paper_session is None or event is None:
            return
        payload = getattr(event, "__dict__", None)
        if payload is None:
            if isinstance(event, dict):
                payload = event
            else:
                payload = {"value": str(event)}
        target = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        target_collection = getattr(self, collection_name, None)
        if target_collection is not None:
            target_collection.append(target)

    def finalize_paper_session(self) -> dict[str, object] | None:
        if self.paper_session is None:
            return None

        self.session_end_utc = datetime.now(timezone.utc).isoformat()
        self.paper_session.session_end_utc = self.session_end_utc

        result = self.paper_session.finalize(
            accounting_engine=self.accounting_engine,
            position_manager=self.position_manager,
            strategy_decisions=self._paper_session_strategy_decisions,
            risk_decisions=self._paper_session_risk_decisions,
            execution_events=self._paper_session_execution_events,
            accounting_decisions=self._paper_session_accounting_decisions,
            position_events=self._paper_session_position_events,
            data_quality_incidents=self._paper_session_data_quality_incidents,
        )
        self.paper_result = result
        self.logger.info(
            "paper_session_finalized session_id=%s path=%s end_utc=%s",
            self.paper_session_id,
            result["artifact_path"],
            self.session_end_utc,
        )
        return result

    def run_startup_recovery(self) -> str:
        if self._startup_recovery_attempted and self.recovery_status in {"READY", "BLOCKED_ON_DIVERGENCE"}:
            return self.recovery_status

        self._startup_recovery_attempted = True
        self.recovery_status = "RECOVERY_NOT_COMPLETE"

        if self.accounting_engine is None:
            self.recovery_status = "BLOCKED_ON_DIVERGENCE"
            self.last_error = "startup_recovery_blocked reason=missing_accounting_engine"
            self.logger.error("startup_recovery_blocked reason=missing_accounting_engine")
            return self.recovery_status

        if getattr(self.accounting_engine, "recovery_status", "VALID") != "VALID":
            self.recovery_status = "BLOCKED_ON_DIVERGENCE"
            self.last_error = "startup_recovery_blocked reason=accounting_state_invalid"
            self.logger.error(
                "startup_recovery_blocked reason=accounting_state_invalid checkpoint=%s",
                self.accounting_open_position_state_path,
            )
            return self.recovery_status

        journal_result = ExecutionJournalReconciler.reconcile(self.execution_output_path, self.accounting_engine)
        if journal_result.get("overall_status") == "BLOCKED_ON_DIVERGENCE":
            self.recovery_status = "BLOCKED_ON_DIVERGENCE"
            self.last_error = (
                f"startup_recovery_blocked reason={journal_result.get('blocking_reason') or 'journal_divergence'}"
            )
            self.logger.error(
                "startup_recovery_blocked reason=%s journal_path=%s",
                journal_result.get("blocking_reason") or "journal_divergence",
                self.execution_output_path,
            )
            return self.recovery_status

        if self.position_manager is not None:
            rebuild_method = getattr(self.position_manager, "rebuild_from_accounting", None)
            if callable(rebuild_method):
                built_projection = rebuild_method(self.accounting_engine)
                if built_projection is None and getattr(self.accounting_engine, "open_position", None) is not None:
                    self.recovery_status = "BLOCKED_ON_DIVERGENCE"
                    self.last_error = "startup_recovery_blocked reason=position_projection_rebuild_failed"
                    self.logger.error("startup_recovery_blocked reason=position_projection_rebuild_failed")
                    return self.recovery_status
                if not self._validate_position_projection_against_accounting():
                    self.recovery_status = "BLOCKED_ON_DIVERGENCE"
                    self.last_error = "startup_recovery_blocked reason=position_projection_invalid"
                    self.logger.error("startup_recovery_blocked reason=position_projection_invalid")
                    return self.recovery_status

        self.recovery_status = "READY"
        self.logger.info("startup_recovery_status status=READY")
        return self.recovery_status

    def _validate_position_projection_against_accounting(self) -> bool:
        accounting_state = self.accounting_engine
        if accounting_state is None:
            return False

        accounting_open_position = getattr(accounting_state, "open_position", None)
        projected_state = getattr(self.position_manager, "_active_position", None)

        if accounting_open_position is None:
            return projected_state is None or not bool(projected_state.get("active", False))

        if projected_state is None:
            return False

        for key in ["trade_id", "market", "symbol", "side", "entry_time_utc", "entry_price", "position_size"]:
            if key not in projected_state:
                return False

        if projected_state.get("market") != accounting_open_position.symbol:
            return False
        if projected_state.get("symbol") != accounting_open_position.symbol:
            return False
        if projected_state.get("side") != accounting_open_position.side:
            return False
        if projected_state.get("entry_time_utc") != accounting_open_position.entry_timestamp_utc:
            return False
        if abs(float(projected_state.get("entry_price", 0.0)) - float(accounting_open_position.entry_price)) > 1e-9:
            return False
        if abs(float(projected_state.get("position_size", 0.0)) - float(accounting_open_position.position_size)) > 1e-9:
            return False
        if projected_state.get("trade_id") != accounting_open_position.trade_id:
            return False

        return True

    def _can_process_market_events(self) -> bool:
        if self.connection_state == "stale_data":
            self.last_error = "market_event_blocked reason=stale_data"
            self.logger.warning("market_event_blocked reason=stale_data connection_state=%s", self.connection_state)
            return False

        if self.connection_state in {"disconnected", "reconnecting", "waiting_to_reconnect", "socket_error", "message_error", "subscription_error", "api_error", "closed", "stopped"}:
            self.last_error = f"market_event_blocked connection_state={self.connection_state}"
            self.logger.warning("market_event_blocked connection_state=%s", self.connection_state)
            return False

        if self.recovery_status == "READY":
            silence_seconds = time.monotonic() - self._last_market_update_monotonic
            if silence_seconds >= self.stale_after_seconds:
                self._stale_warning_active = True
                self.last_error = f"No market update received for {silence_seconds:.1f}s"
                self.logger.warning(
                    "market_event_blocked reason=stale_data market=%s silence_seconds=%.2f threshold=%.2f",
                    self.market,
                    silence_seconds,
                    self.stale_after_seconds,
                )
                self.set_status("stale_data", f"No BTC-EUR update for {silence_seconds:.1f}s; waiting for new data")
                return False
            return True

        self.last_error = f"market_event_blocked recovery_status={self.recovery_status}"
        self.logger.warning("market_event_blocked recovery_status=%s", self.recovery_status)
        return False

    def update_features(self, ticker_state: TickerState, event_time_utc: str | None = None) -> None:
        if self.feature_engine is None:
            return

        try:
            self.feature_engine.update(ticker_state, event_time_utc=event_time_utc)
            if self.debug:
                strategy_input = self.feature_engine.get_latest_strategy_input()
                if strategy_input is not None:
                    self.logger.debug(
                        "strategy_input_ready timestamp=%s mid=%.4f spread=%.8f",
                        strategy_input.timestamp_utc,
                        strategy_input.mid_price,
                        strategy_input.spread_pct,
                    )
        except Exception as exc:
            self.logger.error("feature_engine_update_error error=%s", exc)
            self._record_data_quality_incident("feature_engine_error", str(exc))

    def update_strategy(self, event_time_utc: str | None = None) -> None:
        if self.feature_engine is None or self.strategy_engine is None:
            return None

        strategy_input = self.feature_engine.get_latest_strategy_input()
        if strategy_input is None:
            return None

        try:
            decision = self.strategy_engine.evaluate(strategy_input, event_time_utc=event_time_utc)
            if self.paper_session is not None and decision is not None:
                self._paper_session_strategy_decisions.append(
                    {
                        "timestamp_utc": decision.timestamp_utc,
                        "market": decision.market,
                        "action": decision.action,
                        "reason": decision.reason,
                        "signal_strength": decision.signal_strength,
                        "spread_pct": decision.spread_pct,
                        "micro_return_1": decision.micro_return_1,
                        "micro_return_5": decision.micro_return_5,
                        "tick_interval_ms": decision.tick_interval_ms,
                    }
                )
            if self.debug:
                self.logger.debug(
                    "strategy_decision_debug action=%s reason=%s strength=%.8f",
                    decision.action,
                    decision.reason,
                    decision.signal_strength,
                )
            return decision
        except Exception as exc:
            self.logger.error("strategy_engine_update_error error=%s", exc)
            self._record_data_quality_incident("strategy_engine_error", str(exc))
            return None

    def update_risk(self, strategy_decision, event_time_utc: str | None = None):
        if strategy_decision is None:
            return None

        try:
            risk_decision = self.risk_engine.evaluate(strategy_decision, event_time_utc=event_time_utc)
            if self.paper_session is not None and risk_decision is not None:
                self._paper_session_risk_decisions.append(
                    {
                        "timestamp_utc": risk_decision.timestamp_utc,
                        "market": risk_decision.market,
                        "strategy_action": risk_decision.strategy_action,
                        "risk_action": risk_decision.risk_action,
                        "approved": risk_decision.approved,
                        "reason": risk_decision.reason,
                        "signal_strength": risk_decision.signal_strength,
                        "spread_pct": risk_decision.spread_pct,
                        "tick_interval_ms": risk_decision.tick_interval_ms,
                        "candidates_last_minute": risk_decision.candidates_last_minute,
                    }
                )
            if self.debug:
                self.logger.debug(
                    "risk_decision_debug action=%s approved=%s reason=%s",
                    risk_decision.risk_action,
                    risk_decision.approved,
                    risk_decision.reason,
                )
            return risk_decision
        except Exception as exc:
            self.logger.error("risk_engine_update_error error=%s", exc)
            self._record_data_quality_incident("risk_engine_error", str(exc))
            return None

    def update_execution(self, risk_decision, event_time_utc: str | None = None):
        if risk_decision is None:
            return None

        try:
            execution_event = self.execution_engine.process(risk_decision, event_time_utc=event_time_utc)
            if self.paper_session is not None and execution_event is not None:
                self._paper_session_execution_events.append(
                    {
                        "execution_event_id": execution_event.execution_event_id,
                        "timestamp_utc": execution_event.timestamp_utc,
                        "market": execution_event.market,
                        "strategy_action": execution_event.strategy_action,
                        "risk_action": execution_event.risk_action,
                        "execution_action": execution_event.execution_action,
                        "reason": execution_event.reason,
                        "signal_strength": execution_event.signal_strength,
                        "spread_pct": execution_event.spread_pct,
                    }
                )
            if self.debug:
                self.logger.debug(
                    "execution_event_debug action=%s reason=%s",
                    execution_event.execution_action,
                    execution_event.reason,
                )
            return execution_event
        except Exception as exc:
            self.logger.error("execution_engine_update_error error=%s", exc)
            self._record_data_quality_incident("execution_engine_error", str(exc))
            return None

    def update_position_manager(self, accounting_decision: AccountingDecision | None, event_time_utc: str | None = None):
        if accounting_decision is None:
            return None

        if not isinstance(accounting_decision, AccountingDecision):
            self.logger.error(
                "position_manager_update_error error=raw_execution_event_bypass_denied type=%s",
                type(accounting_decision).__name__,
            )
            return None

        try:
            position_event = self.position_manager.process_accounting_decision(
                accounting_decision,
                event_time_utc=event_time_utc,
            )
            if self.paper_session is not None and position_event is not None:
                self._paper_session_position_events.append(
                    {
                        "timestamp_utc": position_event.timestamp_utc,
                        "market": position_event.market,
                        "position_id": position_event.position_id,
                        "lifecycle_action": position_event.lifecycle_action,
                        "status": position_event.status,
                        "hold_events": position_event.hold_events,
                        "entry_time_utc": position_event.entry_time_utc,
                        "close_time_utc": position_event.close_time_utc,
                        "entry_reason": position_event.entry_reason,
                        "exit_reason": position_event.exit_reason,
                        "entry_signal_strength": position_event.entry_signal_strength,
                        "entry_spread_pct": position_event.entry_spread_pct,
                        "exit_signal_strength": position_event.exit_signal_strength,
                        "exit_spread_pct": position_event.exit_spread_pct,
                    }
                )
            if self.debug and position_event is not None:
                self.logger.debug(
                    "position_event_debug action=%s status=%s id=%s",
                    position_event.lifecycle_action,
                    position_event.status,
                    position_event.position_id,
                )
            return position_event
        except Exception as exc:
            self.logger.error("position_manager_update_error error=%s", exc)
            self._record_data_quality_incident("position_manager_error", str(exc))
            return None

    def update_accounting(self, execution_event, ticker_state, strategy_decision, event_time_utc: str | None = None) -> None:
        if self.accounting_engine is None:
            return

        try:
            signal = strategy_decision.reason if strategy_decision is not None else ""
            confidence = strategy_decision.signal_strength if strategy_decision is not None else None
            timestamp_utc = event_time_utc or datetime.now(timezone.utc).isoformat()

            self.accounting_engine.process_execution(
                execution_event=execution_event,
                bid=ticker_state.bid,
                ask=ticker_state.ask,
                timestamp_utc=timestamp_utc,
                signal=signal,
                confidence=confidence,
            )
            if self.paper_session is not None:
                decision = getattr(self.accounting_engine, "last_decision", None)
                if decision is not None:
                    self._paper_session_accounting_decisions.append(
                        {
                            "status": decision.status,
                            "execution_event_id": decision.execution_event_id,
                            "execution_action": decision.execution_action,
                            "reason": decision.reason,
                            "financial_effect_applied": decision.financial_effect_applied,
                            "market": decision.market,
                            "signal_strength": decision.signal_strength,
                            "spread_pct": decision.spread_pct,
                        }
                    )
        except Exception as exc:
            self.logger.error("accounting_engine_update_error error=%s", exc)
            self._record_data_quality_incident("accounting_engine_error", str(exc))

    def get_latest_strategy_input(self):
        if self.feature_engine is None:
            return None
        return self.feature_engine.get_latest_strategy_input()

    def build_subscription(self) -> dict:
        return {
            "action": "subscribe",
            "channels": [
                {
                    "name": "ticker",
                    "markets": [self.market],
                },
                {
                    "name": "trades",
                    "markets": [self.market],
                },
            ],
        }

    def set_status(self, state: str, message: str) -> None:
        with self._state_lock:
            state_changed = self.connection_state != state or self.status_message != message
            self.connection_state = state
            self.status_message = message

        if state_changed:
            self.logger.info("state=%s message=%s", state, message)

        self.request_render()

    def request_render(self) -> None:
        self._render_event.set()

    def touch_market_update(self) -> None:
        self._last_market_update_monotonic = time.monotonic()
        if self._stale_warning_active:
            self._stale_warning_active = False
            self.last_error = "None"
            self.logger.info("data_fresh_again market=%s", self.market)

    def summarize_message(self, data: object) -> str:
        compact = json.dumps(data, separators=(",", ":"), ensure_ascii=True)
        if len(compact) > 180:
            return f"{compact[:177]}..."
        return compact

    def ensure_ticker_state(self, market: str) -> TickerState:
        with self._state_lock:
            if self.ticker_state is None:
                self.ticker_state = TickerState(market=market, updated_at=datetime.now())
            return self.ticker_state

    def parse_ticker_message(self, data: dict, event_time_utc: str | None = None) -> TickerState | None:
        market = data.get("market")
        if not market:
            self.last_error = "Ticker message missing market"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("ticker_parse_error reason=missing_market payload=%s", self.last_message_summary)
            self.set_status("message_error", "Ticker message received without a market field")
            return None

        ticker_state = self.ensure_ticker_state(str(market))

        try:
            if "bestBid" in data:
                bid_value = float(data["bestBid"])
                if not math.isfinite(bid_value):
                    raise ValueError("non-finite bid")
                ticker_state.bid = bid_value
            if "bestAsk" in data:
                ask_value = float(data["bestAsk"])
                if not math.isfinite(ask_value):
                    raise ValueError("non-finite ask")
                ticker_state.ask = ask_value
            if "lastPrice" in data:
                last_value = float(data["lastPrice"])
                if not math.isfinite(last_value):
                    raise ValueError("non-finite last")
                ticker_state.last = last_value
        except (TypeError, ValueError) as exc:
            self.last_error = f"Ticker field conversion failed: {exc}"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("ticker_parse_error reason=invalid_numeric payload=%s", self.last_message_summary)
            self.set_status("message_error", "Ticker message contained invalid numeric values")
            return None

        if ticker_state.bid is not None and ticker_state.bid <= 0:
            self.last_error = "Ticker best bid must be greater than zero"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("ticker_parse_error reason=non_positive_bid payload=%s", self.last_message_summary)
            self.set_status("message_error", "Ticker message contained non-positive values")
            return None

        if ticker_state.ask is not None and ticker_state.ask <= 0:
            self.last_error = "Ticker best ask must be greater than zero"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("ticker_parse_error reason=non_positive_ask payload=%s", self.last_message_summary)
            self.set_status("message_error", "Ticker message contained non-positive values")
            return None

        if ticker_state.last is not None and ticker_state.last <= 0:
            self.last_error = "Ticker last price must be greater than zero"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("ticker_parse_error reason=non_positive_last payload=%s", self.last_message_summary)
            self.set_status("message_error", "Ticker message contained non-positive values")
            return None

        resolved_time = _parse_event_time_utc(event_time_utc) if event_time_utc is not None else None
        if event_time_utc is not None and resolved_time is None:
            self.last_error = "Ticker event timestamp invalid"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("ticker_parse_error reason=invalid_event_time_utc payload=%s", self.last_message_summary)
            self.set_status("message_error", "Ticker message contained an invalid event timestamp")
            return None

        ticker_state.updated_at = resolved_time or datetime.now()
        self.touch_market_update()
        if self.debug:
            self.logger.debug(
                "ticker_event market=%s bid=%s ask=%s last=%s",
                ticker_state.market,
                ticker_state.bid,
                ticker_state.ask,
                ticker_state.last,
            )
        self.request_render()
        return ticker_state

    def parse_trade_message(self, data: dict, event_time_utc: str | None = None) -> TickerState | None:
        market = data.get("market")
        price = data.get("price")

        if not market or price is None:
            self.last_error = "Trade message missing market or price"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("trade_parse_error reason=missing_fields payload=%s", self.last_message_summary)
            self.set_status("message_error", "Trade message received without required fields")
            return None

        ticker_state = self.ensure_ticker_state(str(market))

        try:
            last_value = float(price)
            if not math.isfinite(last_value):
                raise ValueError("non-finite trade price")
            ticker_state.last = last_value
        except (TypeError, ValueError) as exc:
            self.last_error = f"Trade price conversion failed: {exc}"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("trade_parse_error reason=invalid_price payload=%s", self.last_message_summary)
            self.set_status("message_error", "Trade message contained an invalid price")
            return None

        if ticker_state.last <= 0:
            self.last_error = "Trade price must be greater than zero"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("trade_parse_error reason=non_positive_price payload=%s", self.last_message_summary)
            self.set_status("message_error", "Trade message contained a non-positive price")
            return None

        resolved_time = _parse_event_time_utc(event_time_utc) if event_time_utc is not None else None
        if event_time_utc is not None and resolved_time is None:
            self.last_error = "Trade event timestamp invalid"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("trade_parse_error reason=invalid_event_time_utc payload=%s", self.last_message_summary)
            self.set_status("message_error", "Trade message contained an invalid event timestamp")
            return None

        ticker_state.updated_at = resolved_time or datetime.now()
        self.touch_market_update()
        if self.debug:
            self.logger.debug(
                "trade_event market=%s last=%s",
                ticker_state.market,
                ticker_state.last,
            )
        self.request_render()
        return ticker_state

    def handle_control_message(self, data: dict, event_time_utc: str | None = None) -> None:
        event = data.get("event")

        canonical_event_time_utc = _resolve_canonical_event_time_utc(data, event_time_utc)

        if event == "subscribed":
            ticker_subscriptions = data.get("subscriptions", {}).get("ticker", [])
            trade_subscriptions = data.get("subscriptions", {}).get("trades", [])
            if self.market in ticker_subscriptions and self.market in trade_subscriptions:
                self.last_message_summary = self.summarize_message(data)
                self.logger.info("subscription_confirmed market=%s channels=ticker,trades", self.market)
                self.set_status("subscribed", f"Ticker and trades subscriptions confirmed for {self.market}")
            else:
                self.last_error = "Subscription acknowledgement did not include all requested channels"
                self.last_message_summary = self.summarize_message(data)
                self.logger.error("subscription_error payload=%s", self.last_message_summary)
                self.set_status("subscription_error", "Received subscribed event, but not all channels were confirmed")
            return

        if event == "ticker":
            ticker_state = self.parse_ticker_message(data, event_time_utc=canonical_event_time_utc)
            if ticker_state is None:
                return

            if not self._can_process_market_events():
                self.logger.warning(
                    "market_event_blocked market=%s event=%s recovery_status=%s",
                    self.market,
                    event,
                    self.recovery_status,
                )
                return

            self.ticker_state = ticker_state
            self.update_features(ticker_state, event_time_utc=canonical_event_time_utc)
            strategy_decision = self.update_strategy(event_time_utc=canonical_event_time_utc)
            risk_decision = self.update_risk(strategy_decision, event_time_utc=canonical_event_time_utc)
            execution_event = self.update_execution(risk_decision, event_time_utc=canonical_event_time_utc)
            self.update_accounting(execution_event, ticker_state, strategy_decision, event_time_utc=canonical_event_time_utc)
            self.update_position_manager(self.accounting_engine.last_decision, event_time_utc=canonical_event_time_utc)
            self.last_message_summary = self.summarize_message(data) if self.debug else "Latest ticker event processed"
            self.connection_state = "receiving_ticker"
            self.status_message = f"Receiving live ticker updates for {self.market}"
            self.last_error = "None"
            self.request_render()
            return

        if event == "trade":
            ticker_state = self.parse_trade_message(data, event_time_utc=canonical_event_time_utc)
            if ticker_state is None:
                return

            if not self._can_process_market_events():
                self.logger.warning(
                    "market_event_blocked market=%s event=%s recovery_status=%s",
                    self.market,
                    event,
                    self.recovery_status,
                )
                return

            self.ticker_state = ticker_state
            self.update_features(ticker_state, event_time_utc=canonical_event_time_utc)
            strategy_decision = self.update_strategy(event_time_utc=canonical_event_time_utc)
            risk_decision = self.update_risk(strategy_decision, event_time_utc=canonical_event_time_utc)
            execution_event = self.update_execution(risk_decision, event_time_utc=canonical_event_time_utc)
            self.update_accounting(execution_event, ticker_state, strategy_decision, event_time_utc=canonical_event_time_utc)
            self.update_position_manager(self.accounting_engine.last_decision, event_time_utc=canonical_event_time_utc)
            self.last_message_summary = self.summarize_message(data) if self.debug else "Latest trade event processed"
            self.connection_state = "receiving_ticker"
            self.status_message = f"Receiving live ticker and trade updates for {self.market}"
            self.last_error = "None"
            self.request_render()
            return

        if data.get("error"):
            self.last_error = str(data.get("error"))
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("api_error payload=%s", self.last_message_summary)
            self.set_status("api_error", "Bitvavo returned an error message")
            return

        self.last_message_summary = self.summarize_message(data)
        if self.debug:
            self.logger.debug("non_ticker_message payload=%s", self.last_message_summary)
            self.set_status("non_ticker_message", "Received a non-ticker message")

    def on_open(self, ws) -> None:
        self.ws = ws
        self.logger.info("socket_connected url=%s market=%s", self.ws_url, self.market)
        self.set_status("connected", "Connected to Bitvavo")

        subscription = self.build_subscription()
        if ws is not None:
            ws.send(json.dumps(subscription))

        self.last_message_summary = self.summarize_message(subscription) if self.debug else "Ticker subscription request sent"
        self.logger.info("subscription_sent payload=%s", self.summarize_message(subscription))
        self.set_status("subscription_sent", f"Subscription sent for {self.market}; awaiting confirmation")

    def on_message(self, ws, message: str, event_time_utc: str | None = None) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError as exc:
            self.last_error = f"Malformed JSON received: {exc}"
            self.last_message_summary = message if self.debug else "Malformed JSON payload received"
            self.logger.error("json_error error=%s payload=%s", exc, message[:180])
            self.set_status("message_error", "Received malformed JSON from websocket")
            return

        if not isinstance(data, dict):
            self.last_error = f"Unexpected payload type: {type(data).__name__}"
            self.last_message_summary = self.summarize_message(data)
            self.logger.error("payload_type_error type=%s payload=%s", type(data).__name__, self.last_message_summary)
            self.set_status("message_error", "Received a JSON payload that was not an object")
            return

        self.handle_control_message(data, event_time_utc=event_time_utc)

    def on_error(self, ws, error: object) -> None:
        self.last_error = str(error)
        self.logger.error("socket_error error=%s", error)
        self.set_status("socket_error", "WebSocket error encountered")

    def on_close(self, ws, close_status_code: int, close_msg: str) -> None:
        self.ws = None

        if self.should_stop:
            self.logger.info("socket_closed_cleanly")
            self.set_status("closed", "Connection closed cleanly")
            return

        close_reason = f"Socket closed unexpectedly (status={close_status_code}, message={close_msg})"
        self.last_error = close_reason
        self.logger.warning("socket_closed_unexpectedly status=%s message=%s", close_status_code, close_msg)
        self.set_status("disconnected", close_reason)

    def build_dashboard(self) -> str:
        with self._state_lock:
            ticker_state = self.ticker_state
            connection_state = self.connection_state
            status_message = self.status_message
            last_error = self.last_error
            last_message_summary = self.last_message_summary

        lines = [
            "=============================================",
            "          BITVAVO MARKET DATA",
            "=============================================",
            f"Market: {self.market}",
            "",
        ]

        if ticker_state is None:
            lines.extend(
                [
                    "Bid: N/A",
                    "Ask: N/A",
                    "Last: N/A",
                    "",
                    "Spread: N/A",
                    "Spread %: N/A",
                    "Mid Price: N/A",
                    "",
                    "Updated: Waiting for first ticker...",
                ]
            )
        else:
            ticker = ticker_state
            lines.extend(
                [
                    f"Bid: {self.format_eur(ticker.bid)}",
                    f"Ask: {self.format_eur(ticker.ask)}",
                    f"Last: {self.format_eur(ticker.last)}",
                    "",
                    f"Spread: {self.format_eur(ticker.spread)}",
                    f"Spread %: {self.format_percentage(ticker.spread_percentage)}",
                    f"Mid Price: {self.format_eur(ticker.mid_price)}",
                    "",
                    f"Updated: {ticker.updated_at.strftime('%H:%M:%S')}",
                ]
            )

        lines.extend(
            [
                "",
                f"State: {connection_state}",
                f"Status: {status_message}",
                f"Last Error: {last_error}",
            ]
        )

        if self.debug:
            lines.append(f"Last Message: {last_message_summary}")

        lines.extend(
            [
                "",
                "Press Ctrl+C to stop",
                "=============================================",
            ]
        )

        return "\n".join(lines)

    def render_dashboard(self, force: bool = False) -> None:
        frame = self.build_dashboard()
        if not force and frame == self._last_frame:
            return

        os.system("cls" if os.name == "nt" else "clear")
        sys.stdout.write(frame + "\n")
        sys.stdout.flush()
        self._screen_initialized = True
        self._last_frame = frame

    def render_loop(self) -> None:
        while not self.should_stop:
            self._render_event.wait(timeout=self.render_interval)
            self._render_event.clear()
            self.render_dashboard()

        self.render_dashboard(force=True)

    @staticmethod
    def format_eur(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"€{value:,.2f}"

    @staticmethod
    def format_percentage(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.4f}%"

    def create_websocket_app(self) -> websocket.WebSocketApp:
        return websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

    def stop(self) -> None:
        if self.paper_session is not None and self.paper_result is None:
            self.finalize_paper_session()
        self.should_stop = True
        self.logger.info("shutdown_requested")
        self.set_status("closing", "Stopping market data engine")
        self._render_event.set()
        if self.ws is not None:
            self.ws.close()

    def start_renderer(self) -> None:
        if self._render_thread is not None:
            return

        self._render_thread = threading.Thread(target=self.render_loop, name="market-data-renderer", daemon=True)
        self._render_thread.start()

    def watchdog_loop(self) -> None:
        while not self.should_stop:
            time.sleep(self.stale_check_interval)

            if self.should_stop:
                break

            if self.connection_state not in {"receiving_ticker", "subscribed"}:
                continue

            silence_seconds = time.monotonic() - self._last_market_update_monotonic
            if silence_seconds < self.stale_after_seconds:
                continue

            if self._stale_warning_active:
                continue

            self._stale_warning_active = True
            self.last_error = f"No market update received for {silence_seconds:.1f}s"
            self.logger.warning(
                "stale_data_detected market=%s silence_seconds=%.2f threshold=%.2f",
                self.market,
                silence_seconds,
                self.stale_after_seconds,
            )
            self.set_status("stale_data", f"No BTC-EUR update for {silence_seconds:.1f}s; waiting for new data")

    def start_watchdog(self) -> None:
        if self._watchdog_thread is not None:
            return

        self._watchdog_thread = threading.Thread(target=self.watchdog_loop, name="market-data-watchdog", daemon=True)
        self._watchdog_thread.start()

    def run(self) -> None:
        attempt = 0
        self.start_renderer()
        self.start_watchdog()

        while not self.should_stop:
            if attempt >= self.max_reconnect_attempts:
                self.logger.error("reconnect_limit_reached attempts=%s", attempt)
                self.set_status("stopped", "Maximum reconnect attempts reached")
                break

            display_attempt = attempt + 1
            if attempt == 0:
                self.set_status("connecting", f"Connecting to Bitvavo for {self.market}")
            else:
                self.logger.warning("reconnect_attempt current=%s max=%s", display_attempt, self.max_reconnect_attempts)
                self.set_status(
                    "reconnecting",
                    f"Reconnect attempt {display_attempt}/{self.max_reconnect_attempts} in progress",
                )

            websocket_app = self.create_websocket_app()
            websocket_app.run_forever(ping_interval=20, ping_timeout=10)

            if self.should_stop:
                break

            attempt += 1
            if attempt < self.max_reconnect_attempts:
                self.set_status(
                    "waiting_to_reconnect",
                    f"Reconnecting in {self.reconnect_delay:.0f} seconds",
                )
                time.sleep(self.reconnect_delay)

        self.should_stop = True
        self._render_event.set()
        if self._render_thread is not None:
            self._render_thread.join(timeout=1)
        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=1)


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float, minimum: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        value = float(raw.strip())
    except ValueError:
        print(f"Invalid {name}='{raw}'. Using default {default}.")
        return default

    if minimum is not None and value < minimum:
        print(f"Invalid {name}={value}. Minimum is {minimum}. Using default {default}.")
        return default

    return value


def env_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        value = int(raw.strip())
    except ValueError:
        print(f"Invalid {name}='{raw}'. Using default {default}.")
        return default

    if minimum is not None and value < minimum:
        print(f"Invalid {name}={value}. Minimum is {minimum}. Using default {default}.")
        return default

    return value


def main() -> None:
    engine = MarketDataEngine(
        market=os.getenv("BITVAVO_MARKET", MARKET),
        ws_url=os.getenv("BITVAVO_WS_URL", WS_URL),
        debug=env_flag("BITVAVO_DEBUG"),
        reconnect_delay=env_float("BITVAVO_RECONNECT_DELAY_SECONDS", 3.0, minimum=0.1),
        max_reconnect_attempts=env_int("BITVAVO_MAX_RECONNECT_ATTEMPTS", 5, minimum=1),
        render_interval=env_float("BITVAVO_RENDER_INTERVAL_SECONDS", 0.25, minimum=0.05),
        stale_after_seconds=env_float("BITVAVO_STALE_AFTER_SECONDS", 5.0, minimum=0.5),
        stale_check_interval=env_float("BITVAVO_STALE_CHECK_INTERVAL_SECONDS", 1.0, minimum=0.1),
        feature_output_path=os.getenv("FEATURE_OUTPUT_PATH", "data/features_btc_eur.csv"),
        feature_engine_enabled=env_flag("FEATURE_ENGINE_ENABLED", True),
        strategy_output_path=os.getenv("STRATEGY_OUTPUT_PATH", "data/strategy_decisions_btc_eur.csv"),
        strategy_engine_enabled=env_flag("STRATEGY_ENGINE_ENABLED", True),
        strategy_max_spread_pct=env_float("STRATEGY_MAX_SPREAD_PCT", 0.02, minimum=0.0),
        strategy_max_tick_interval_ms=env_float("STRATEGY_MAX_TICK_INTERVAL_MS", 2000.0, minimum=1.0),
        strategy_min_momentum_return=env_float("STRATEGY_MIN_MOMENTUM_RETURN", 0.0),
        risk_output_path=os.getenv("RISK_OUTPUT_PATH", "data/risk_decisions_btc_eur.csv"),
        risk_engine_enabled=env_flag("RISK_ENGINE_ENABLED", True),
        risk_emergency_stop=env_flag("RISK_EMERGENCY_STOP", False),
        risk_max_spread_pct=env_float("RISK_MAX_SPREAD_PCT", 0.02, minimum=0.0),
        risk_max_tick_interval_ms=env_float("RISK_MAX_TICK_INTERVAL_MS", 2000.0, minimum=1.0),
        risk_min_signal_strength=env_float("RISK_MIN_SIGNAL_STRENGTH", -1.0),
        risk_max_candidates_per_minute=env_int("RISK_MAX_CANDIDATES_PER_MINUTE", 120, minimum=1),
        execution_output_path=os.getenv("EXECUTION_OUTPUT_PATH", "data/execution_simulation_btc_eur.csv"),
        execution_engine_enabled=env_flag("EXECUTION_ENGINE_ENABLED", True),
        position_output_path=os.getenv("POSITION_OUTPUT_PATH", "data/positions_simulation_btc_eur.csv"),
        position_manager_enabled=env_flag("POSITION_MANAGER_ENABLED", True),
        position_max_hold_events=env_int("POSITION_MAX_HOLD_EVENTS", 250, minimum=1),
        accounting_engine_enabled=env_flag("ACCOUNTING_ENGINE_ENABLED", True),
        accounting_trade_ledger_path=os.getenv("ACCOUNTING_TRADE_LEDGER_PATH", "data/trade_ledger_btc_eur.csv"),
        accounting_account_state_path=os.getenv("ACCOUNTING_ACCOUNT_STATE_PATH", "data/account_state_btc_eur.csv"),
        accounting_open_position_state_path=os.getenv("ACCOUNTING_OPEN_POSITION_STATE_PATH", "data/accounting_open_position_state_btc_eur.json"),
        accounting_strategy_name=os.getenv("ACCOUNTING_STRATEGY_NAME", "baseline_momentum"),
        accounting_starting_balance=env_float("ACCOUNTING_STARTING_BALANCE", 1000.0, minimum=0.0),
        accounting_order_notional_eur=env_float("ACCOUNTING_ORDER_NOTIONAL_EUR", 10.0, minimum=0.01),
        accounting_fee_rate=env_float("ACCOUNTING_FEE_RATE", 0.001, minimum=0.0),
        accounting_slippage_bps=env_float("ACCOUNTING_SLIPPAGE_BPS", 1.0, minimum=0.0),
    )

    try:
        engine.start_paper_session()
        engine.run()
    except KeyboardInterrupt:
        engine.stop()
    finally:
        if engine.paper_session is not None and engine.paper_result is None:
            engine.finalize_paper_session()


def _extract_payload_event_time_utc(data: dict) -> str | None:
    for key in ("event_time_utc", "timestamp_utc", "timestamp", "time", "eventTime", "event_time"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _resolve_canonical_event_time_utc(data: dict, explicit_event_time_utc: str | None = None) -> str:
    if explicit_event_time_utc is not None:
        parsed = _parse_event_time_utc(explicit_event_time_utc)
        if parsed is not None:
            return parsed.isoformat()
        return explicit_event_time_utc

    payload_event_time_utc = _extract_payload_event_time_utc(data)
    if payload_event_time_utc is not None:
        parsed = _parse_event_time_utc(payload_event_time_utc)
        if parsed is not None:
            return parsed.isoformat()

    return datetime.now(timezone.utc).isoformat()


def _parse_event_time_utc(raw: str | None) -> datetime | None:
    if raw is None:
        return None

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)
