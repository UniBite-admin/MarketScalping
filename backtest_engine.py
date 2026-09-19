from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import tempfile
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from accounting_engine import AccountingEngine
from backtest_execution_model import BacktestConfig, BacktestExecutionModel, ExecutionOutcome
from execution_engine import ExecutionEngine
from feature_signal_engine import FeatureSignalEngine, StrategyInput
from position_manager import PositionManager
from replay_runner import _normalize_replay_event
from risk_engine import RiskEngine, RiskState
from strategy_engine import StrategyEngine


@dataclass
class TradeRecord:
    trade_id: str
    open_time_utc: str
    close_time_utc: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    fees: float
    slippage: float
    net_pnl: float
    holding_time_seconds: float
    status: str = "CLOSED"


@dataclass
class CostAttribution:
    spread_cost: float
    slippage_cost: float
    fee_cost: float
    total_execution_cost: float
    gross_pnl: float
    net_pnl: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "spread_cost": self.spread_cost,
            "slippage_cost": self.slippage_cost,
            "fee_cost": self.fee_cost,
            "total_execution_cost": self.total_execution_cost,
            "gross_pnl": self.gross_pnl,
            "net_pnl": self.net_pnl,
            "identity": "gross_pnl - execution_costs = net_pnl",
        }


@dataclass
class PerformanceSummary:
    gross_pnl: float
    execution_costs: float
    net_pnl: float
    roi: float | None
    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    expectancy: float
    profit_factor: float
    max_drawdown: float
    current_drawdown: float
    current_drawdown_pct: float
    consecutive_losses: int
    average_holding_time_seconds: float
    sharpe: float | None = None
    sortino: float | None = None
    unsupported_metrics: list[str] = field(default_factory=lambda: ["sharpe", "sortino"])
    equity_definition: str = "accounting_engine.equity as the authoritative backtest equity signal; no separate fabricated unrealized-PnL layer"

    def as_dict(self) -> dict[str, Any]:
        return {
            "gross_pnl": self.gross_pnl,
            "execution_costs": self.execution_costs,
            "net_pnl": self.net_pnl,
            "roi": self.roi,
            "trade_count": self.trade_count,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "expectancy": self.expectancy,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "current_drawdown_pct": self.current_drawdown_pct,
            "consecutive_losses": self.consecutive_losses,
            "average_holding_time_seconds": self.average_holding_time_seconds,
            "sharpe": self.sharpe,
            "sortino": self.sortino,
            "unsupported_metrics": self.unsupported_metrics,
            "equity_definition": self.equity_definition,
        }


@dataclass
class RunMetadata:
    dataset_id: str
    event_count: int
    first_event_time_utc: str | None
    last_event_time_utc: str | None
    strategy_configuration: dict[str, Any]
    risk_configuration: dict[str, Any]
    execution_configuration: dict[str, Any]
    fee_configuration: dict[str, Any]
    spread_configuration: dict[str, Any]
    slippage_configuration: dict[str, Any]
    latency_configuration: dict[str, Any]
    run_signature: str
    schema_version: str = "step_8_4_analytics_v1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "event_count": self.event_count,
            "first_event_time_utc": self.first_event_time_utc,
            "last_event_time_utc": self.last_event_time_utc,
            "strategy_configuration": self.strategy_configuration,
            "risk_configuration": self.risk_configuration,
            "execution_configuration": self.execution_configuration,
            "fee_configuration": self.fee_configuration,
            "spread_configuration": self.spread_configuration,
            "slippage_configuration": self.slippage_configuration,
            "latency_configuration": self.latency_configuration,
            "run_signature": self.run_signature,
            "schema_version": self.schema_version,
        }


@dataclass
class BacktestAnalytics:
    trade_ledger: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]
    cost_attribution: CostAttribution
    performance_summary: PerformanceSummary
    run_metadata: RunMetadata


@dataclass
class BacktestResult:
    run_id: str
    dataset_id: str
    market: str
    event_start_utc: str | None
    event_end_utc: str | None
    repository_revision: str | None
    strategy_configuration: dict[str, Any]
    risk_configuration: dict[str, Any]
    execution_configuration: dict[str, Any]
    fee_configuration: dict[str, Any]
    spread_configuration: dict[str, Any]
    slippage_configuration: dict[str, Any]
    latency_configuration: dict[str, Any]
    initial_capital: float
    final_cash: float
    final_position_quantity: float
    final_equity: float
    realized_pnl: float
    trade_records: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]
    metrics: dict[str, Any]
    warnings: list[str]
    limitations: list[str]
    validation_status: str
    observed_assumptions: dict[str, Any]
    modeled_assumptions: dict[str, Any]
    replay_status: str
    replay_rejection_reasons: tuple[tuple[str, int], ...]
    state_isolated: bool = True
    strategy_decisions: list[dict[str, Any]] = field(default_factory=list)
    risk_decisions: list[dict[str, Any]] = field(default_factory=list)
    execution_events: list[dict[str, Any]] = field(default_factory=list)
    accounting_decisions: list[dict[str, Any]] = field(default_factory=list)
    position_events: list[dict[str, Any]] = field(default_factory=list)
    analytics: BacktestAnalytics | None = None


@dataclass
class BacktestState:
    cash: float
    position_quantity: float = 0.0
    position_side: str | None = None
    entry_price: float | None = None
    realized_pnl: float = 0.0
    fees_paid: float = 0.0
    slippage_paid: float = 0.0
    spread_paid: float = 0.0
    rejected_executions: int = 0
    approved_executions: int = 0
    current_equity: float = 0.0
    peak_equity: float = 0.0
    max_drawdown: float = 0.0
    open_trade: dict[str, Any] | None = None
    closed_trades: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[dict[str, Any]] = field(default_factory=list)
    pending_orders: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _NormalizationSummary:
    events_total: int = 0
    events_processed: int = 0
    rejection_reasons: Counter[str] = field(default_factory=Counter)

    @property
    def rejection_reason_items(self) -> tuple[tuple[str, int], ...]:
        return tuple(sorted(self.rejection_reasons.items()))

    @property
    def dataset_status(self) -> str:
        if self.events_total == 0:
            return "EMPTY_VALID_DATASET"
        if self.events_processed == 0:
            return "REJECTED"
        return "CANONICALIZED"

    @property
    def canonicalization_result(self) -> str:
        if self.events_total == 0:
            return "NOT_APPLICABLE"
        if self.events_processed == 0:
            return "REJECTED"
        return "SUCCESS"


@dataclass
class _HistoricalTickerState:
    market: str
    bid: float | None
    ask: float | None
    last: float | None

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
        return (self.bid + self.ask) / 2.0


class BacktestEngine:
    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()
        self.validation_errors = self.config.validate()
        self.execution_model = BacktestExecutionModel(self.config)
        self.logger = logging.getLogger("backtest_engine")

    def run(
        self,
        events: Iterable[dict],
        *,
        strategy_configuration: dict[str, Any] | None = None,
        risk_configuration: dict[str, Any] | None = None,
        summary_mode: bool = False,
        assume_canonical_chronological: bool = False,
    ) -> BacktestResult:
        if self.validation_errors:
            return self._invalid_result([], self.validation_errors, replay_status="INVALID")

        normalization = _NormalizationSummary()
        if assume_canonical_chronological:
            normalized_events: Iterable[dict[str, Any]] = self._iter_normalized_events(events, normalization)
        else:
            normalized_events = self._normalize_events(events, normalization)
            if normalization.dataset_status != "CANONICALIZED":
                return self._invalid_result(
                    list(normalized_events),
                    ["empty_or_rejected_dataset"] if normalization.events_total == 0 else [f"replay_status_{normalization.dataset_status.lower()}"],
                    replay_status=normalization.dataset_status,
                    replay_rejection_reasons=normalization.rejection_reason_items,
                )

        temp_dir = tempfile.mkdtemp(prefix="backtest_8_2_")
        buffered_persistence_batch_size = 512
        feature_engine = FeatureSignalEngine(
            os.path.join(temp_dir, "features.csv"),
            self.logger,
        )
        strategy_engine = StrategyEngine(
            os.path.join(temp_dir, "strategy.csv"),
            self.logger,
            persistence_batch_size=buffered_persistence_batch_size,
        )
        risk_engine = RiskEngine(
            os.path.join(temp_dir, "risk.csv"),
            self.logger,
            enabled=True,
            max_spread_pct=0.02,
            max_tick_interval_ms=2000.0,
            min_signal_strength=-1.0,
            max_candidates_per_minute=120,
            max_position_size=self.config.initial_capital / max(self.config.min_notional, 1.0),
            max_exposure=self.config.initial_capital * 2.0,
            max_risk_per_trade=self.config.initial_capital * 0.25,
            persistence_batch_size=buffered_persistence_batch_size,
        )
        accounting_engine = AccountingEngine(
            trade_ledger_path=os.path.join(temp_dir, "trade_ledger.csv"),
            account_state_path=os.path.join(temp_dir, "account_state.json"),
            open_position_state_path=os.path.join(temp_dir, "open_position.json"),
            logger=self.logger,
            enabled=True,
            strategy_name="backtest_8_2",
            starting_balance=self.config.initial_capital,
            order_notional_eur=max(self.config.min_notional, self.config.initial_capital * 0.1),
            fee_rate=self.config.fee_rate,
            slippage_bps=self.config.slippage_bps,
        )
        position_manager = PositionManager(os.path.join(temp_dir, "position_ledger.csv"), self.logger, enabled=True)
        execution_engine = ExecutionEngine(os.path.join(temp_dir, "execution_events.csv"), self.logger, enabled=True)

        state = BacktestState(cash=self.config.initial_capital)
        state.current_equity = self.config.initial_capital
        state.peak_equity = self.config.initial_capital
        state.max_drawdown = 0.0

        strategy_decisions: list[dict[str, Any]] = []
        risk_decisions: list[dict[str, Any]] = []
        execution_events: list[dict[str, Any]] = []
        accounting_decisions: list[dict[str, Any]] = []
        position_events: list[dict[str, Any]] = []
        store_traces = not summary_mode
        event_count = 0
        first_event_time_utc: str | None = None
        last_event_time_utc: str | None = None
        dataset_hasher = hashlib.sha256()

        try:
            for event_index, item in enumerate(normalized_events):
                raw_event = item["raw"]
                event = item["normalized"]
                event_count += 1
                if first_event_time_utc is None:
                    first_event_time_utc = event.event_time_utc
                last_event_time_utc = event.event_time_utc
                dataset_hasher.update(json.dumps(raw_event, sort_keys=True, separators=(",", ":")).encode("utf-8"))
                dataset_hasher.update(b"\n")

                strategy_input = self._build_historical_strategy_input(feature_engine, event)
                if strategy_input is None:
                    self._refresh_state_from_accounting(state, accounting_engine)
                    self._record_snapshot(state, event.event_time_utc, enabled=store_traces)
                    continue

                current_last = float(strategy_input.last)
                strategy_decision = strategy_engine.evaluate(strategy_input, event_time_utc=event.event_time_utc)
                if store_traces:
                    strategy_decisions.append(self._as_mapping(strategy_decision))

                risk_state = accounting_engine.build_risk_state()
                order_quantity = self._determine_order_quantity(current_last, state.cash, state.position_quantity)
                candidate_position_size = max(order_quantity, 0.0)
                candidate_entry_notional = order_quantity * current_last
                protected_exit_value = max(current_last * (1.0 - max(self.config.spread_pct, 0.0)), 0.0)
                risk_decision = risk_engine.evaluate(
                    strategy_decision,
                    event_time_utc=event.event_time_utc,
                    risk_state=risk_state,
                    candidate_position_size=candidate_position_size,
                    candidate_entry_notional=candidate_entry_notional,
                    protected_exit_value=protected_exit_value,
                )
                if store_traces:
                    risk_decisions.append(self._as_mapping(risk_decision))

                if strategy_decision.action != "CANDIDATE_TRADE":
                    self._refresh_state_from_accounting(state, accounting_engine)
                    self._record_snapshot(state, event.event_time_utc, enabled=store_traces)
                    continue

                if not risk_decision.approved:
                    self._refresh_state_from_accounting(state, accounting_engine)
                    self._record_snapshot(state, event.event_time_utc, enabled=store_traces)
                    continue

                if self.config.latency_ticks > 0:
                    state.pending_orders.append(
                        {
                            "event_index": event_index,
                            "signal": strategy_decision.action,
                            "reference_price": current_last,
                            "order_quantity": order_quantity,
                            "observation_time": event.event_time_utc,
                        }
                    )
                    while state.pending_orders and (event_index - state.pending_orders[0]["event_index"]) >= self.config.latency_ticks:
                        pending = state.pending_orders.pop(0)
                        if pending["signal"] == "NO_TRADE" or pending["signal"] == "INVALID":
                            continue
                        risk_decision = risk_engine.evaluate(
                            strategy_decision,
                            event_time_utc=pending["observation_time"],
                            risk_state=accounting_engine.build_risk_state(),
                            candidate_position_size=max(pending["order_quantity"], 0.0),
                            candidate_entry_notional=pending["order_quantity"] * pending["reference_price"],
                            protected_exit_value=max(pending["reference_price"] * (1.0 - max(self.config.spread_pct, 0.0)), 0.0),
                        )
                        if not risk_decision.approved:
                            continue
                        execution_event = execution_engine.process(risk_decision, event_time_utc=pending["observation_time"])
                        if store_traces:
                            execution_events.append(self._as_mapping(execution_event))
                        if execution_event.execution_action != "SIMULATED_ORDER_PREPARED":
                            continue
                        outcome = self.execution_model.simulate(
                            side="BUY" if strategy_decision.action == "CANDIDATE_TRADE" else "SELL",
                            reference_price=pending["reference_price"],
                            order_quantity=pending["order_quantity"],
                            event_time_utc=pending["observation_time"],
                            available_cash=max(accounting_engine.available_balance, 0.0),
                            position_quantity=max(accounting_engine.open_position.position_size, 0.0) if accounting_engine.open_position is not None else 0.0,
                            observed_bid=event.bid,
                            observed_ask=event.ask,
                        )
                        self._apply_outcome(state, outcome, event, event_index)
                        accounting_decision = accounting_engine.process_execution(
                            execution_event,
                            bid=event.bid,
                            ask=event.ask,
                            timestamp_utc=pending["observation_time"],
                            signal=strategy_decision.action,
                            confidence=strategy_decision.signal_strength,
                        )
                        if store_traces:
                            accounting_decisions.append(self._as_mapping(accounting_decision) if accounting_decision is not None else {"status": "REJECTED"})
                        if accounting_decision is not None and accounting_decision.financial_effect_applied:
                            position_event = position_manager.process_accounting_decision(accounting_decision, event_time_utc=pending["observation_time"])
                            if position_event is not None:
                                if store_traces:
                                    position_events.append(self._as_mapping(position_event))
                        self._refresh_state_from_accounting(state, accounting_engine)
                else:
                    execution_event = execution_engine.process(risk_decision, event_time_utc=event.event_time_utc)
                    if store_traces:
                        execution_events.append(self._as_mapping(execution_event))
                    if execution_event.execution_action != "SIMULATED_ORDER_PREPARED":
                        self._refresh_state_from_accounting(state, accounting_engine)
                        self._record_snapshot(state, event.event_time_utc, enabled=store_traces)
                        continue
                    outcome = self.execution_model.simulate(
                        side="BUY" if strategy_decision.action == "CANDIDATE_TRADE" else "SELL",
                        reference_price=current_last,
                        order_quantity=order_quantity,
                        event_time_utc=event.event_time_utc,
                        available_cash=max(accounting_engine.available_balance, 0.0),
                        position_quantity=max(accounting_engine.open_position.position_size, 0.0) if accounting_engine.open_position is not None else 0.0,
                        observed_bid=event.bid,
                        observed_ask=event.ask,
                    )
                    self._apply_outcome(state, outcome, event, event_index)
                    accounting_decision = accounting_engine.process_execution(
                        execution_event,
                        bid=event.bid,
                        ask=event.ask,
                        timestamp_utc=event.event_time_utc,
                        signal=strategy_decision.action,
                        confidence=strategy_decision.signal_strength,
                    )
                    if store_traces:
                        accounting_decisions.append(self._as_mapping(accounting_decision) if accounting_decision is not None else {"status": "REJECTED"})
                    if accounting_decision is not None and accounting_decision.financial_effect_applied:
                        position_event = position_manager.process_accounting_decision(accounting_decision, event_time_utc=event.event_time_utc)
                        if position_event is not None:
                            if store_traces:
                                position_events.append(self._as_mapping(position_event))
                    self._refresh_state_from_accounting(state, accounting_engine)

                self._record_snapshot(state, event.event_time_utc, enabled=store_traces)
        finally:
            risk_engine.close()
            strategy_engine.close()

        if normalization.dataset_status != "CANONICALIZED":
            return self._invalid_result(
                [],
                ["empty_or_rejected_dataset"] if normalization.events_total == 0 else [f"replay_status_{normalization.dataset_status.lower()}"],
                replay_status=normalization.dataset_status,
                replay_rejection_reasons=normalization.rejection_reason_items,
            )

        metrics = self._compute_metrics(state)
        dataset_id = dataset_hasher.hexdigest()
        observed = {
            "event_count": event_count,
            "first_event_time_utc": first_event_time_utc,
            "last_event_time_utc": last_event_time_utc,
            "dataset_status": normalization.dataset_status,
            "canonicalization_result": normalization.canonicalization_result,
        }
        modeled = {
            "fee_rate": self.config.fee_rate,
            "spread_pct": self.config.spread_pct,
            "slippage_bps": self.config.slippage_bps,
            "latency_ticks": self.config.latency_ticks,
            "partial_fill_ratio": self.config.partial_fill_ratio,
            "min_order_size": self.config.min_order_size,
            "min_notional": self.config.min_notional,
            "modeled_liquidity": self.config.model_liquidity,
            "liquidity_note": self.config.modeled_liquidity_note,
        }

        warnings: list[str] = []
        limitations: list[str] = []
        if self.config.model_liquidity:
            warnings.append("Historical liquidity depth was not observed; modeled liquidity assumption is active.")
        if self.config.latency_ticks > 0:
            warnings.append("Latency is modeled deterministically by event delay and not by real wall-clock time.")
        if self.config.partial_fill_ratio < 1.0:
            warnings.append("Partial fills are modeled as a deterministic configured fill ratio.")
        if self.config.model_liquidity is False:
            limitations.append("Order-book depth was not observed in the historical dataset and therefore is not inferred.")

        run_signature = hashlib.sha256(
            json.dumps(
                {
                    "config": {
                        "market": self.config.market,
                        "initial_capital": self.config.initial_capital,
                        "fee_rate": self.config.fee_rate,
                        "spread_pct": self.config.spread_pct,
                        "slippage_bps": self.config.slippage_bps,
                        "latency_ticks": self.config.latency_ticks,
                        "partial_fill_ratio": self.config.partial_fill_ratio,
                        "min_order_size": self.config.min_order_size,
                        "min_notional": self.config.min_notional,
                    },
                    "dataset_id": dataset_id,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        trade_ledger = [
            {
                "trade_id": entry.get("trade_id", f"trade-{idx + 1}"),
                "market": self.config.market,
                "side": entry.get("side", "UNKNOWN"),
                "entry_timestamp_utc": entry.get("open_time_utc"),
                "exit_timestamp_utc": entry.get("close_time_utc"),
                "entry_price": entry.get("entry_price", 0.0),
                "exit_price": entry.get("exit_price", 0.0),
                "quantity": entry.get("quantity", 0.0),
                "gross_pnl": entry.get("gross_pnl", 0.0),
                "spread_impact": entry.get("spread_impact", 0.0),
                "slippage_impact": entry.get("slippage_impact", entry.get("slippage", 0.0)),
                "fees": entry.get("fees", 0.0),
                "net_pnl": entry.get("net_pnl", 0.0),
                "holding_time_seconds": entry.get("holding_time_seconds", 0.0),
                "status": entry.get("status", "CLOSED"),
                "execution_status": entry.get("status", "CLOSED"),
            }
            for idx, entry in enumerate(state.closed_trades)
        ]

        equity_curve = [
            {
                "timestamp_utc": point["timestamp_utc"],
                "equity": float(point["equity"]),
                "cash": float(point["cash"]),
                "position_quantity": float(point["position_quantity"]),
                "realized_pnl": float(point["realized_pnl"]),
                "peak_equity": float(point["peak_equity"]),
                "max_drawdown": float(point["max_drawdown"]),
            }
            for point in state.snapshots
        ]

        realized_pnl = float(state.realized_pnl)
        gross_pnl = sum(float(trade["gross_pnl"]) for trade in trade_ledger)
        execution_costs = sum(float(trade["fees"]) + float(trade["slippage_impact"]) + float(trade["spread_impact"]) for trade in trade_ledger)
        net_pnl = realized_pnl if realized_pnl != 0 else sum(float(trade["net_pnl"]) for trade in trade_ledger)
        total_execution_cost = execution_costs
        max_drawdown = state.max_drawdown
        current_drawdown = max(0.0, (state.peak_equity - state.current_equity) / max(state.peak_equity, 1e-9))
        current_drawdown_pct = current_drawdown

        cost_attribution = CostAttribution(
            spread_cost=sum(float(trade["spread_impact"]) for trade in trade_ledger),
            slippage_cost=sum(float(trade["slippage_impact"]) for trade in trade_ledger),
            fee_cost=sum(float(trade["fees"]) for trade in trade_ledger),
            total_execution_cost=total_execution_cost,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
        )

        trade_count = len(trade_ledger)
        winning_trades = sum(1 for trade in trade_ledger if float(trade["net_pnl"]) > 0)
        losing_trades = sum(1 for trade in trade_ledger if float(trade["net_pnl"]) < 0)
        win_rate = (winning_trades / trade_count) if trade_count else 0.0
        average_win = (sum(float(trade["net_pnl"]) for trade in trade_ledger if float(trade["net_pnl"]) > 0) / winning_trades) if winning_trades else 0.0
        average_loss = (abs(sum(float(trade["net_pnl"]) for trade in trade_ledger if float(trade["net_pnl"]) < 0)) / losing_trades) if losing_trades else 0.0
        expectancy = (win_rate * average_win) - ((1.0 - win_rate) * average_loss)
        gross_profit = sum(float(trade["net_pnl"]) for trade in trade_ledger if float(trade["net_pnl"]) > 0)
        gross_loss = abs(sum(float(trade["net_pnl"]) for trade in trade_ledger if float(trade["net_pnl"]) < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss else (float("inf") if gross_profit > 0 else 0.0)
        roi = (net_pnl / max(self.config.initial_capital, 1e-9)) if self.config.initial_capital else 0.0
        average_holding_time = (sum(float(trade["holding_time_seconds"]) for trade in trade_ledger) / trade_count) if trade_count else 0.0
        consecutive_losses = 0
        current_streak = 0
        for trade in trade_ledger:
            pnl = float(trade["net_pnl"])
            if pnl < 0:
                current_streak += 1
                consecutive_losses = max(consecutive_losses, current_streak)
            else:
                current_streak = 0

        performance_summary = PerformanceSummary(
            gross_pnl=gross_pnl,
            execution_costs=execution_costs,
            net_pnl=net_pnl,
            roi=roi,
            trade_count=trade_count,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            average_win=average_win,
            average_loss=average_loss,
            expectancy=expectancy,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            current_drawdown=current_drawdown,
            current_drawdown_pct=current_drawdown_pct,
            consecutive_losses=consecutive_losses,
            average_holding_time_seconds=average_holding_time,
            sharpe=None,
            sortino=None,
            unsupported_metrics=["sharpe", "sortino"],
        )

        run_metadata = RunMetadata(
            dataset_id=dataset_id,
            event_count=event_count,
            first_event_time_utc=observed["first_event_time_utc"],
            last_event_time_utc=observed["last_event_time_utc"],
            strategy_configuration=strategy_configuration or {},
            risk_configuration=risk_configuration or {},
            execution_configuration={
                "latency_ticks": self.config.latency_ticks,
                "partial_fill_ratio": self.config.partial_fill_ratio,
                "max_position_fraction": self.config.max_position_fraction,
            },
            fee_configuration={"fee_rate": self.config.fee_rate},
            spread_configuration={"spread_pct": self.config.spread_pct},
            slippage_configuration={"slippage_bps": self.config.slippage_bps},
            latency_configuration={"latency_ticks": self.config.latency_ticks},
            run_signature=run_signature,
        )

        analytics = BacktestAnalytics(
            trade_ledger=trade_ledger,
            equity_curve=equity_curve,
            cost_attribution=cost_attribution,
            performance_summary=performance_summary,
            run_metadata=run_metadata,
        )

        result = BacktestResult(
            run_id=run_signature,
            dataset_id=dataset_id,
            market=self.config.market,
            event_start_utc=observed["first_event_time_utc"],
            event_end_utc=observed["last_event_time_utc"],
            repository_revision=None,
            strategy_configuration=strategy_configuration or {},
            risk_configuration=risk_configuration or {},
            execution_configuration={
                "latency_ticks": self.config.latency_ticks,
                "partial_fill_ratio": self.config.partial_fill_ratio,
                "max_position_fraction": self.config.max_position_fraction,
            },
            fee_configuration={"fee_rate": self.config.fee_rate},
            spread_configuration={"spread_pct": self.config.spread_pct},
            slippage_configuration={"slippage_bps": self.config.slippage_bps},
            latency_configuration={"latency_ticks": self.config.latency_ticks},
            initial_capital=self.config.initial_capital,
            final_cash=state.cash,
            final_position_quantity=state.position_quantity,
            final_equity=state.current_equity,
            realized_pnl=state.realized_pnl,
            trade_records=state.closed_trades,
            equity_curve=state.snapshots,
            metrics=metrics,
            warnings=warnings,
            limitations=limitations,
            validation_status="PASS" if normalization.dataset_status == "CANONICALIZED" else "INVALID",
            observed_assumptions=observed,
            modeled_assumptions=modeled,
            replay_status=normalization.dataset_status,
            replay_rejection_reasons=normalization.rejection_reason_items,
            strategy_decisions=strategy_decisions,
            risk_decisions=risk_decisions,
            execution_events=execution_events,
            accounting_decisions=accounting_decisions,
            position_events=position_events,
            analytics=analytics,
        )
        return result

    def _normalize_events(self, events: Iterable[dict], summary: _NormalizationSummary) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in self._iter_normalized_events(events, summary):
            normalized.append(item)
        normalized.sort(key=lambda item: (item["normalized"].event_time_dt, item["normalized"].original_index))
        return normalized

    def _iter_normalized_events(self, events: Iterable[dict], summary: _NormalizationSummary) -> Iterable[dict[str, Any]]:
        for original_index, raw_event in enumerate(events):
            summary.events_total += 1
            norm_event, rejection = _normalize_replay_event(raw_event, original_index)
            if norm_event is None:
                summary.rejection_reasons[rejection] += 1
                continue
            summary.events_processed += 1
            yield {"raw": raw_event, "normalized": norm_event}

    def _determine_order_quantity(self, reference_price: float, available_cash: float, position_quantity: float) -> float:
        candidate = max(self.config.min_order_size, min(available_cash * 0.5 / max(reference_price, 1e-9), self.config.initial_capital * self.config.max_position_fraction / max(reference_price, 1e-9)))
        return candidate

    def _build_historical_strategy_input(self, feature_engine: FeatureSignalEngine, event) -> StrategyInput | None:
        if getattr(event, "event_type", None) != "ticker":
            return None

        ticker_state = _HistoricalTickerState(
            market=event.market,
            bid=float(event.bid),
            ask=float(event.ask),
            last=float(event.last),
        )
        feature_engine.update(ticker_state, event_time_utc=event.event_time_utc)
        return feature_engine.get_latest_strategy_input()

    def _as_mapping(self, value):
        if value is None:
            return {}
        if hasattr(value, "__dict__"):
            return {key: getattr(value, key) for key in vars(value).keys() if not key.startswith("_")}
        return dict(value)

    def _refresh_state_from_accounting(self, state: BacktestState, accounting_engine: AccountingEngine) -> None:
        state.cash = accounting_engine.available_balance
        state.position_quantity = accounting_engine.open_position.position_size if accounting_engine.open_position is not None else 0.0
        state.realized_pnl = accounting_engine.realized_pnl
        state.current_equity = float(accounting_engine.equity)
        if state.current_equity > state.peak_equity:
            state.peak_equity = state.current_equity
        drawdown = max(0.0, (state.peak_equity - state.current_equity) / max(state.peak_equity, 1e-9))
        state.max_drawdown = max(state.max_drawdown, drawdown)

    def _record_snapshot(self, state: BacktestState, event_time_utc: str, *, enabled: bool) -> None:
        if not enabled:
            return
        state.snapshots.append(
            {
                "timestamp_utc": event_time_utc,
                "cash": state.cash,
                "position_quantity": state.position_quantity,
                "equity": state.current_equity,
                "realized_pnl": state.realized_pnl,
                "fees": state.fees_paid,
                "slippage": state.slippage_paid,
                "spread_cost": state.spread_paid,
                "peak_equity": state.peak_equity,
                "max_drawdown": state.max_drawdown,
            }
        )

    def _apply_outcome(self, state: BacktestState, outcome: ExecutionOutcome, event, event_index: int) -> None:
        if not outcome.accepted:
            state.rejected_executions += 1
            return

        state.approved_executions += 1
        if outcome.side == "BUY":
            quantity = outcome.fill_quantity
            cost = outcome.notional + outcome.fees + outcome.slippage_impact
            state.cash -= cost
            state.position_quantity += quantity
            if state.position_side is None:
                state.position_side = "BUY"
            if state.position_side == "SELL":
                state.position_side = "BUY"
            if state.entry_price is None:
                state.entry_price = outcome.execution_price
        elif outcome.side == "SELL":
            quantity = outcome.fill_quantity
            proceeds = outcome.notional - outcome.fees - outcome.slippage_impact
            state.cash += proceeds
            state.position_quantity -= quantity
            if state.position_side is None:
                state.position_side = "SELL"
            if state.position_side == "BUY":
                state.position_side = "SELL"
            if state.position_quantity <= 0:
                realized = (outcome.execution_price - (state.entry_price or outcome.execution_price)) * quantity
                state.realized_pnl += realized
                state.closed_trades.append(
                    {
                        "trade_id": f"trade-{len(state.closed_trades)+1}",
                        "open_time_utc": event.event_time_utc,
                        "close_time_utc": event.event_time_utc,
                        "side": "SELL",
                        "entry_price": state.entry_price or outcome.execution_price,
                        "exit_price": outcome.execution_price,
                        "quantity": quantity,
                        "gross_pnl": realized,
                        "fees": outcome.fees,
                        "slippage": outcome.slippage_impact,
                        "net_pnl": realized - outcome.fees - outcome.slippage_impact,
                        "holding_time_seconds": 0.0,
                        "status": "CLOSED",
                    }
                )
                state.position_quantity = 0.0
                state.position_side = None
                state.entry_price = None

        state.fees_paid += outcome.fees
        state.slippage_paid += outcome.slippage_impact
        state.spread_paid += outcome.spread_impact

    def _compute_metrics(self, state: BacktestState) -> dict[str, Any]:
        closed = state.closed_trades
        trade_count = len(closed)
        gross_profit = sum(item["net_pnl"] for item in closed if item["net_pnl"] > 0)
        gross_loss = abs(sum(item["net_pnl"] for item in closed if item["net_pnl"] < 0))
        net_pnl = sum(item["net_pnl"] for item in closed)
        win_rate = (sum(1 for item in closed if item["net_pnl"] > 0) / trade_count) if trade_count else 0.0
        avg_win = (sum(item["net_pnl"] for item in closed if item["net_pnl"] > 0) / max(sum(1 for item in closed if item["net_pnl"] > 0), 1)) if trade_count else 0.0
        avg_loss = (abs(sum(item["net_pnl"] for item in closed if item["net_pnl"] < 0)) / max(sum(1 for item in closed if item["net_pnl"] < 0), 1)) if trade_count else 0.0
        expectancy = (win_rate * avg_win) - ((1.0 - win_rate) * avg_loss)
        profit_factor = (gross_profit / gross_loss) if gross_loss else (float("inf") if gross_profit > 0 else 0.0)
        roi = (net_pnl / max(self.config.initial_capital, 1e-9))
        average_holding_time = sum(item["holding_time_seconds"] for item in closed) / trade_count if trade_count else 0.0
        wins = sum(1 for item in closed if item["net_pnl"] > 0)
        losses = sum(1 for item in closed if item["net_pnl"] < 0)
        consecutive_wins = 0
        consecutive_losses = 0
        best_streak = 0
        worst_streak = 0
        for item in closed:
            if item["net_pnl"] > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                best_streak = max(best_streak, consecutive_wins)
            elif item["net_pnl"] < 0:
                consecutive_losses += 1
                consecutive_wins = 0
                worst_streak = max(worst_streak, consecutive_losses)
            else:
                consecutive_wins = 0
                consecutive_losses = 0

        return {
            "net_pnl": net_pnl,
            "roi": roi,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "win_rate": win_rate,
            "average_win": avg_win,
            "average_loss": avg_loss,
            "expectancy": expectancy,
            "profit_factor": profit_factor,
            "max_drawdown": state.max_drawdown,
            "trade_count": trade_count,
            "average_holding_time_seconds": average_holding_time,
            "consecutive_wins": best_streak,
            "consecutive_losses": worst_streak,
            "total_fees": state.fees_paid,
            "total_slippage_impact": state.slippage_paid,
            "rejected_execution_count": state.rejected_executions,
            "approved_execution_count": state.approved_executions,
            "available_statistical_metrics": ["net_pnl", "roi", "gross_profit", "gross_loss", "win_rate", "average_win", "average_loss", "expectancy", "profit_factor", "max_drawdown", "trade_count", "average_holding_time_seconds", "consecutive_wins", "consecutive_losses", "total_fees", "total_slippage_impact"],
            "execution_cost_breakdown": {
                "fee_cost": state.fees_paid,
                "slippage_cost": state.slippage_paid,
                "spread_cost": state.spread_paid,
                "gross_trade_pnl_effect": net_pnl,
            },
        }

    def _invalid_result(self, normalized: list[dict[str, Any]], validation_errors: list[str], *, replay_status: str, replay_rejection_reasons: tuple[tuple[str, int], ...] = ()) -> BacktestResult:
        start = normalized[0]["normalized"].event_time_utc if normalized else None
        end = normalized[-1]["normalized"].event_time_utc if normalized else None
        run_signature = hashlib.sha256(
            json.dumps(
                {
                    "config": {
                        "market": self.config.market,
                        "initial_capital": self.config.initial_capital,
                        "fee_rate": self.config.fee_rate,
                        "spread_pct": self.config.spread_pct,
                        "slippage_bps": self.config.slippage_bps,
                        "latency_ticks": self.config.latency_ticks,
                    },
                    "errors": validation_errors,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        return BacktestResult(
            run_id=run_signature,
            dataset_id=hashlib.sha256(json.dumps({"errors": validation_errors}, sort_keys=True).encode("utf-8")).hexdigest(),
            market=self.config.market,
            event_start_utc=start,
            event_end_utc=end,
            repository_revision=None,
            strategy_configuration={},
            risk_configuration={},
            execution_configuration={"latency_ticks": self.config.latency_ticks},
            fee_configuration={"fee_rate": self.config.fee_rate},
            spread_configuration={"spread_pct": self.config.spread_pct},
            slippage_configuration={"slippage_bps": self.config.slippage_bps},
            latency_configuration={"latency_ticks": self.config.latency_ticks},
            initial_capital=self.config.initial_capital,
            final_cash=self.config.initial_capital,
            final_position_quantity=0.0,
            final_equity=self.config.initial_capital,
            realized_pnl=0.0,
            trade_records=[],
            equity_curve=[],
            metrics={"net_pnl": 0.0, "roi": 0.0, "trade_count": 0, "rejected_execution_count": len(validation_errors)},
            warnings=[],
            limitations=validation_errors,
            validation_status="INVALID",
            observed_assumptions={"event_count": len(normalized), "first_event_time_utc": start, "last_event_time_utc": end},
            modeled_assumptions={"fee_rate": self.config.fee_rate, "spread_pct": self.config.spread_pct, "slippage_bps": self.config.slippage_bps},
            replay_status=replay_status,
            replay_rejection_reasons=replay_rejection_reasons,
        )


__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "BacktestExecutionModel",
    "ExecutionOutcome",
]
