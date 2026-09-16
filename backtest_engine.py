from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from accounting_engine import AccountingEngine
from backtest_execution_model import BacktestConfig, BacktestExecutionModel, ExecutionOutcome
from execution_engine import ExecutionEngine
from feature_signal_engine import StrategyInput
from position_manager import PositionManager
from replay_runner import ReplayRunner, _normalize_replay_event
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


@dataclass
class BacktestState:
    cash: float
    position_quantity: float = 0.0
    position_side: str | None = None
    entry_price: float | None = None
    realized_pnl: float = 0.0
    fees_paid: float = 0.0
    slippage_paid: float = 0.0
    rejected_executions: int = 0
    approved_executions: int = 0
    current_equity: float = 0.0
    peak_equity: float = 0.0
    max_drawdown: float = 0.0
    open_trade: dict[str, Any] | None = None
    closed_trades: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[dict[str, Any]] = field(default_factory=list)
    pending_orders: list[dict[str, Any]] = field(default_factory=list)


class BacktestEngine:
    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()
        self.validation_errors = self.config.validate()
        self.execution_model = BacktestExecutionModel(self.config)
        self.logger = logging.getLogger("backtest_engine")

    def run(self, events: Iterable[dict], *, strategy_configuration: dict[str, Any] | None = None, risk_configuration: dict[str, Any] | None = None) -> BacktestResult:
        normalized = self._normalize_events(events)
        if self.validation_errors:
            return self._invalid_result(normalized, self.validation_errors, replay_status="INVALID")
        if not normalized:
            return self._invalid_result([], ["empty_or_rejected_dataset"], replay_status="REJECTED")

        replay = ReplayRunner(
            market=self.config.market,
            position_max_hold_events=2,
            accounting_starting_balance=self.config.initial_capital,
        ).replay([event for event in [item["raw"] for item in normalized]])

        if replay.dataset_status != "CANONICALIZED":
            return self._invalid_result(
                normalized,
                [f"replay_status_{replay.dataset_status.lower()}"],
                replay_status=replay.dataset_status,
                replay_rejection_reasons=replay.rejection_reasons,
            )

        temp_dir = tempfile.mkdtemp(prefix="backtest_8_2_")
        strategy_engine = StrategyEngine(os.path.join(temp_dir, "strategy.csv"), self.logger)
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

        previous_last: float | None = None
        strategy_decisions: list[dict[str, Any]] = []
        risk_decisions: list[dict[str, Any]] = []
        execution_events: list[dict[str, Any]] = []
        accounting_decisions: list[dict[str, Any]] = []
        position_events: list[dict[str, Any]] = []
        pending_event_index = 0

        for event_index, item in enumerate(normalized):
            raw_event = item["raw"]
            event = item["normalized"]
            current_last = float(event.last)
            strategy_input = self._to_strategy_input(event)
            strategy_decision = strategy_engine.evaluate(strategy_input, event_time_utc=event.event_time_utc)
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
            risk_decisions.append(self._as_mapping(risk_decision))

            if strategy_decision.action != "CANDIDATE_TRADE":
                previous_last = current_last
                state.current_equity = float(accounting_engine.equity)
                if state.current_equity > state.peak_equity:
                    state.peak_equity = state.current_equity
                drawdown = max(0.0, (state.peak_equity - state.current_equity) / max(state.peak_equity, 1e-9))
                state.max_drawdown = max(state.max_drawdown, drawdown)
                state.snapshots.append(
                    {
                        "timestamp_utc": event.event_time_utc,
                        "cash": state.cash,
                        "position_quantity": state.position_quantity,
                        "equity": state.current_equity,
                        "realized_pnl": state.realized_pnl,
                        "fees": state.fees_paid,
                        "slippage": state.slippage_paid,
                        "peak_equity": state.peak_equity,
                        "max_drawdown": state.max_drawdown,
                    }
                )
                continue

            if not risk_decision.approved:
                previous_last = current_last
                state.current_equity = float(accounting_engine.equity)
                if state.current_equity > state.peak_equity:
                    state.peak_equity = state.current_equity
                drawdown = max(0.0, (state.peak_equity - state.current_equity) / max(state.peak_equity, 1e-9))
                state.max_drawdown = max(state.max_drawdown, drawdown)
                state.snapshots.append(
                    {
                        "timestamp_utc": event.event_time_utc,
                        "cash": state.cash,
                        "position_quantity": state.position_quantity,
                        "equity": state.current_equity,
                        "realized_pnl": state.realized_pnl,
                        "fees": state.fees_paid,
                        "slippage": state.slippage_paid,
                        "peak_equity": state.peak_equity,
                        "max_drawdown": state.max_drawdown,
                    }
                )
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
                    accounting_decisions.append(self._as_mapping(accounting_decision) if accounting_decision is not None else {"status": "REJECTED"})
                    if accounting_decision is not None and accounting_decision.financial_effect_applied:
                        position_event = position_manager.process_accounting_decision(accounting_decision, event_time_utc=pending["observation_time"])
                        if position_event is not None:
                            position_events.append(self._as_mapping(position_event))
                    state.cash = accounting_engine.available_balance
                    state.position_quantity = accounting_engine.open_position.position_size if accounting_engine.open_position is not None else 0.0
                    state.realized_pnl = accounting_engine.realized_pnl
                    state.current_equity = float(accounting_engine.equity)
            else:
                execution_event = execution_engine.process(risk_decision, event_time_utc=event.event_time_utc)
                execution_events.append(self._as_mapping(execution_event))
                if execution_event.execution_action != "SIMULATED_ORDER_PREPARED":
                    previous_last = current_last
                    state.current_equity = float(accounting_engine.equity)
                    if state.current_equity > state.peak_equity:
                        state.peak_equity = state.current_equity
                    drawdown = max(0.0, (state.peak_equity - state.current_equity) / max(state.peak_equity, 1e-9))
                    state.max_drawdown = max(state.max_drawdown, drawdown)
                    state.snapshots.append(
                        {
                            "timestamp_utc": event.event_time_utc,
                            "cash": state.cash,
                            "position_quantity": state.position_quantity,
                            "equity": state.current_equity,
                            "realized_pnl": state.realized_pnl,
                            "fees": state.fees_paid,
                            "slippage": state.slippage_paid,
                            "peak_equity": state.peak_equity,
                            "max_drawdown": state.max_drawdown,
                        }
                    )
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
                accounting_decisions.append(self._as_mapping(accounting_decision) if accounting_decision is not None else {"status": "REJECTED"})
                if accounting_decision is not None and accounting_decision.financial_effect_applied:
                    position_event = position_manager.process_accounting_decision(accounting_decision, event_time_utc=event.event_time_utc)
                    if position_event is not None:
                        position_events.append(self._as_mapping(position_event))
                state.cash = accounting_engine.available_balance
                state.position_quantity = accounting_engine.open_position.position_size if accounting_engine.open_position is not None else 0.0
                state.realized_pnl = accounting_engine.realized_pnl
                state.current_equity = float(accounting_engine.equity)

            previous_last = current_last
            if state.current_equity > state.peak_equity:
                state.peak_equity = state.current_equity
            drawdown = max(0.0, (state.peak_equity - state.current_equity) / max(state.peak_equity, 1e-9))
            state.max_drawdown = max(state.max_drawdown, drawdown)
            state.snapshots.append(
                {
                    "timestamp_utc": event.event_time_utc,
                    "cash": state.cash,
                    "position_quantity": state.position_quantity,
                    "equity": state.current_equity,
                    "realized_pnl": state.realized_pnl,
                    "fees": state.fees_paid,
                    "slippage": state.slippage_paid,
                    "peak_equity": state.peak_equity,
                    "max_drawdown": state.max_drawdown,
                }
            )

        metrics = self._compute_metrics(state)
        observed = {
            "event_count": len(normalized),
            "first_event_time_utc": normalized[0]["normalized"].event_time_utc if normalized else None,
            "last_event_time_utc": normalized[-1]["normalized"].event_time_utc if normalized else None,
            "dataset_status": replay.dataset_status,
            "canonicalization_result": replay.canonicalization_result,
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
                    "events": [event["raw"] for event in normalized],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        result = BacktestResult(
            run_id=run_signature,
            dataset_id=hashlib.sha256(json.dumps({"events": [event["raw"] for event in normalized]}, sort_keys=True).encode("utf-8")).hexdigest(),
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
            validation_status="PASS" if replay.dataset_status == "CANONICALIZED" else "INVALID",
            observed_assumptions=observed,
            modeled_assumptions=modeled,
            replay_status=replay.dataset_status,
            replay_rejection_reasons=replay.rejection_reasons,
            strategy_decisions=strategy_decisions,
            risk_decisions=risk_decisions,
            execution_events=execution_events,
            accounting_decisions=accounting_decisions,
            position_events=position_events,
        )
        return result

    def _normalize_events(self, events: Iterable[dict]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for original_index, raw_event in enumerate(events):
            norm_event, rejection = _normalize_replay_event(raw_event, original_index)
            if norm_event is None:
                continue
            normalized.append({"raw": raw_event, "normalized": norm_event})
        normalized.sort(key=lambda item: (item["normalized"].event_time_dt, item["normalized"].original_index))
        return normalized

    def _determine_order_quantity(self, reference_price: float, available_cash: float, position_quantity: float) -> float:
        candidate = max(self.config.min_order_size, min(available_cash * 0.5 / max(reference_price, 1e-9), self.config.initial_capital * self.config.max_position_fraction / max(reference_price, 1e-9)))
        return candidate

    def _to_strategy_input(self, event) -> StrategyInput:
        spread_abs = abs(float(event.ask) - float(event.bid)) if event.ask is not None and event.bid is not None else 0.0
        spread_pct = spread_abs / max(float(event.last), 1e-9) if float(event.last) else 0.0
        mid_price = (float(event.bid) + float(event.ask)) / 2.0 if event.bid is not None and event.ask is not None else float(event.last)
        return StrategyInput(
            timestamp_utc=event.event_time_utc,
            market=event.market,
            bid=float(event.bid),
            ask=float(event.ask),
            last=float(event.last),
            spread_abs=spread_abs,
            spread_pct=spread_pct,
            mid_price=mid_price,
            micro_return_1=None,
            micro_return_5=None,
            spread_change_1=None,
            spread_change_5=None,
            tick_interval_ms=None,
        )

    def _as_mapping(self, value):
        if value is None:
            return {}
        if hasattr(value, "__dict__"):
            return {key: getattr(value, key) for key in vars(value).keys() if not key.startswith("_")}
        return dict(value)

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
