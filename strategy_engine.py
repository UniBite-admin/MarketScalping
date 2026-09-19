from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from feature_signal_engine import StrategyInput


@dataclass
class StrategyDecision:
    timestamp_utc: str
    market: str
    action: str
    reason: str
    signal_strength: float
    spread_pct: float
    micro_return_1: float | None
    micro_return_5: float | None
    tick_interval_ms: float | None

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "timestamp_utc",
            "market",
            "action",
            "reason",
            "signal_strength",
            "spread_pct",
            "micro_return_1",
            "micro_return_5",
            "tick_interval_ms",
        ]

    def to_csv_row(self) -> list[str]:
        return [
            self.timestamp_utc,
            self.market,
            self.action,
            self.reason,
            _fmt(self.signal_strength),
            _fmt(self.spread_pct),
            _fmt(self.micro_return_1),
            _fmt(self.micro_return_5),
            _fmt(self.tick_interval_ms),
        ]


class StrategyEngine:
    def __init__(
        self,
        output_path: str,
        logger,
        max_spread_pct: float = 0.02,
        max_tick_interval_ms: float = 2000.0,
        min_momentum_return: float = 0.0,
        persistence_batch_size: int = 1,
    ):
        self.output_path = output_path
        self.logger = logger
        self.max_spread_pct = max_spread_pct
        self.max_tick_interval_ms = max_tick_interval_ms
        self.min_momentum_return = min_momentum_return
        self.persistence_batch_size = max(int(persistence_batch_size), 1)
        self._pending_rows: list[list[str]] = []

        self._prepare_output_file()

    def _prepare_output_file(self) -> None:
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(self.output_path):
            with open(self.output_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(StrategyDecision.csv_headers())

            self.logger.info("strategy_output_initialized path=%s", self.output_path)

    def evaluate(self, strategy_input: StrategyInput, event_time_utc: str | None = None) -> StrategyDecision:
        decision_time = _resolve_event_time(event_time_utc)
        if decision_time is None and event_time_utc is not None:
            decision = self._build_decision(
                strategy_input,
                action="NO_TRADE",
                reason="invalid_event_time_utc",
                signal_strength=0.0,
                decision_time_utc=event_time_utc,
            )
            self._persist_decision(decision)
            return decision

        resolved_time_utc = decision_time.isoformat() if decision_time is not None else None

        momentum_ready = strategy_input.micro_return_1 is not None and strategy_input.micro_return_5 is not None
        fresh_tick = (
            strategy_input.tick_interval_ms is not None
            and strategy_input.tick_interval_ms <= self.max_tick_interval_ms
        )
        spread_ok = strategy_input.spread_pct <= self.max_spread_pct

        if not momentum_ready:
            decision = self._build_decision(
                strategy_input,
                action="NO_TRADE",
                reason="warmup_not_enough_momentum_history",
                signal_strength=0.0,
                decision_time_utc=resolved_time_utc,
            )
            self._persist_decision(decision)
            return decision

        momentum_score = self._momentum_score(strategy_input)
        bullish_momentum = momentum_score >= self.min_momentum_return

        if spread_ok and fresh_tick and bullish_momentum:
            decision = self._build_decision(
                strategy_input,
                action="CANDIDATE_TRADE",
                reason="momentum_positive_and_spread_acceptable",
                signal_strength=momentum_score,
                decision_time_utc=resolved_time_utc,
            )
        else:
            reasons = []
            if not spread_ok:
                reasons.append("spread_too_wide")
            if not fresh_tick:
                reasons.append("stale_tick_interval")
            if not bullish_momentum:
                reasons.append("momentum_not_positive")

            decision = self._build_decision(
                strategy_input,
                action="NO_TRADE",
                reason="|".join(reasons) if reasons else "guardrail_block",
                signal_strength=momentum_score,
                decision_time_utc=resolved_time_utc,
            )

        self._persist_decision(decision)
        return decision

    def _momentum_score(self, strategy_input: StrategyInput) -> float:
        # Weighted short-horizon momentum score for deterministic baseline decisions.
        r1 = strategy_input.micro_return_1 or 0.0
        r5 = strategy_input.micro_return_5 or 0.0
        return (0.7 * r1) + (0.3 * r5)

    def _build_decision(
        self,
        strategy_input: StrategyInput,
        action: str,
        reason: str,
        signal_strength: float,
        decision_time_utc: str | None = None,
    ) -> StrategyDecision:
        return StrategyDecision(
            timestamp_utc=decision_time_utc or datetime.now(timezone.utc).isoformat(),
            market=strategy_input.market,
            action=action,
            reason=reason,
            signal_strength=signal_strength,
            spread_pct=strategy_input.spread_pct,
            micro_return_1=strategy_input.micro_return_1,
            micro_return_5=strategy_input.micro_return_5,
            tick_interval_ms=strategy_input.tick_interval_ms,
        )

    def _persist_decision(self, decision: StrategyDecision) -> None:
        self._pending_rows.append(decision.to_csv_row())
        if len(self._pending_rows) >= self.persistence_batch_size:
            self.flush()

        self.logger.info(
            "strategy_decision action=%s reason=%s strength=%.8f spread_pct=%.8f",
            decision.action,
            decision.reason,
            decision.signal_strength,
            decision.spread_pct,
        )

    def flush(self) -> None:
        if not self._pending_rows:
            return

        with open(self.output_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(self._pending_rows)

        self._pending_rows.clear()

    def close(self) -> None:
        self.flush()


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10f}"


def _resolve_event_time(event_time_utc: str | None) -> datetime | None:
    if event_time_utc is None:
        return None

    try:
        parsed = datetime.fromisoformat(event_time_utc.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)