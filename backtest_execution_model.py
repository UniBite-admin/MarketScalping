from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ExecutionOutcome:
    accepted: bool
    reason: str
    side: str
    quantity: float
    fill_quantity: float
    execution_price: float
    fees: float
    slippage_impact: float
    notional: float
    latency_delay_ticks: int = 0
    observed_price: float | None = None
    modeled_liquidity: str = "NOT_OBSERVED"


@dataclass
class BacktestConfig:
    market: str = "BTC-EUR"
    initial_capital: float = 1000.0
    fee_rate: float = 0.001
    spread_pct: float = 0.001
    slippage_bps: float = 10.0
    latency_ticks: int = 0
    min_order_size: float = 0.01
    min_notional: float = 1.0
    partial_fill_ratio: float = 1.0
    max_position_fraction: float = 0.25
    model_liquidity: bool = False
    modeled_liquidity_note: str = "Liquidity modeled as configured assumption; no historical depth was observed."
    seed: int | None = 0

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.initial_capital <= 0:
            errors.append("initial_capital_must_be_positive")
        if self.fee_rate < 0:
            errors.append("fee_rate_invalid")
        if self.spread_pct < 0:
            errors.append("spread_pct_invalid")
        if self.slippage_bps < 0:
            errors.append("slippage_bps_invalid")
        if self.latency_ticks < 0:
            errors.append("latency_ticks_invalid")
        if self.min_order_size <= 0:
            errors.append("min_order_size_invalid")
        if self.min_notional <= 0:
            errors.append("min_notional_invalid")
        if not 0 < self.partial_fill_ratio <= 1:
            errors.append("partial_fill_ratio_invalid")
        if not 0 < self.max_position_fraction <= 1:
            errors.append("max_position_fraction_invalid")
        return errors


@dataclass
class BacktestExecutionModel:
    config: BacktestConfig

    def simulate(self, *, side: str, reference_price: float, order_quantity: float, event_time_utc: str, observed_bid: float | None = None, observed_ask: float | None = None, available_cash: float = 0.0, position_quantity: float = 0.0) -> ExecutionOutcome:
        norm_side = str(side).upper()
        if norm_side not in {"BUY", "SELL"}:
            return ExecutionOutcome(False, "invalid_side", norm_side, order_quantity, 0.0, 0.0, 0.0, 0.0, 0.0, self.config.latency_ticks, reference_price, self._liquidity_mode())

        if order_quantity <= 0:
            return ExecutionOutcome(False, "order_quantity_invalid", norm_side, order_quantity, 0.0, 0.0, 0.0, 0.0, 0.0, self.config.latency_ticks, reference_price, self._liquidity_mode())
        if order_quantity < self.config.min_order_size:
            return ExecutionOutcome(False, "below_minimum_order_size", norm_side, order_quantity, 0.0, 0.0, 0.0, 0.0, 0.0, self.config.latency_ticks, reference_price, self._liquidity_mode())

        notional = order_quantity * reference_price
        if notional < self.config.min_notional:
            return ExecutionOutcome(False, "below_minimum_notional", norm_side, order_quantity, 0.0, 0.0, 0.0, 0.0, 0.0, self.config.latency_ticks, reference_price, self._liquidity_mode())

        if norm_side == "BUY" and available_cash < notional:
            return ExecutionOutcome(False, "insufficient_balance", norm_side, order_quantity, 0.0, 0.0, 0.0, 0.0, 0.0, self.config.latency_ticks, reference_price, self._liquidity_mode())
        if norm_side == "SELL" and position_quantity < order_quantity:
            return ExecutionOutcome(False, "insufficient_position_size", norm_side, order_quantity, 0.0, 0.0, 0.0, 0.0, 0.0, self.config.latency_ticks, reference_price, self._liquidity_mode())

        if self.config.model_liquidity and observed_bid is not None and observed_ask is not None:
            cost_base = reference_price
            spread_component = abs(observed_ask - observed_bid) / max(observed_bid, observed_ask, 1.0)
        else:
            cost_base = reference_price
            spread_component = self.config.spread_pct

        spread_rate = spread_component if spread_component > 0 else self.config.spread_pct
        slippage_rate = self.config.slippage_bps / 10000.0
        execution_price = cost_base * (1.0 + spread_rate / 2.0 + slippage_rate) if norm_side == "BUY" else cost_base * (1.0 - spread_rate / 2.0 - slippage_rate)

        fill_quantity = order_quantity * self.config.partial_fill_ratio
        if fill_quantity <= 0:
            return ExecutionOutcome(False, "partial_fill_ratio_invalid", norm_side, order_quantity, 0.0, 0.0, 0.0, 0.0, 0.0, self.config.latency_ticks, reference_price, self._liquidity_mode())

        fill_notional = fill_quantity * execution_price
        fees = fill_notional * self.config.fee_rate
        slippage_impact = fill_notional * (self.config.slippage_bps / 10000.0)

        return ExecutionOutcome(
            accepted=True,
            reason="simulated_fill",
            side=norm_side,
            quantity=order_quantity,
            fill_quantity=fill_quantity,
            execution_price=execution_price,
            fees=fees,
            slippage_impact=slippage_impact,
            notional=fill_notional,
            latency_delay_ticks=self.config.latency_ticks,
            observed_price=reference_price,
            modeled_liquidity=self._liquidity_mode(),
        )

    def _liquidity_mode(self) -> str:
        if self.config.model_liquidity:
            return "MODELED"
        return "NOT_OBSERVED"
