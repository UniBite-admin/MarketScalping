from __future__ import annotations

import csv
import os
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from strategy_engine import StrategyDecision


@dataclass
class RiskDecision:
    timestamp_utc: str
    market: str
    strategy_action: str
    risk_action: str
    approved: bool
    reason: str
    signal_strength: float
    spread_pct: float
    tick_interval_ms: float | None
    candidates_last_minute: int

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "timestamp_utc",
            "market",
            "strategy_action",
            "risk_action",
            "approved",
            "reason",
            "signal_strength",
            "spread_pct",
            "tick_interval_ms",
            "candidates_last_minute",
        ]

    def to_csv_row(self) -> list[str]:
        return [
            self.timestamp_utc,
            self.market,
            self.strategy_action,
            self.risk_action,
            str(self.approved),
            self.reason,
            _fmt(self.signal_strength),
            _fmt(self.spread_pct),
            _fmt(self.tick_interval_ms),
            str(self.candidates_last_minute),
        ]


class RiskEngine:
    def __init__(
        self,
        output_path: str,
        logger,
        enabled: bool = True,
        emergency_stop: bool = False,
        max_spread_pct: float = 0.02,
        max_tick_interval_ms: float = 2000.0,
        min_signal_strength: float = -1.0,
        max_candidates_per_minute: int = 120,
    ):
        self.output_path = output_path
        self.logger = logger
        self.enabled = enabled
        self.emergency_stop = emergency_stop
        self.max_spread_pct = max_spread_pct
        self.max_tick_interval_ms = max_tick_interval_ms
        self.min_signal_strength = min_signal_strength
        self.max_candidates_per_minute = max_candidates_per_minute

        self._candidate_timestamps = deque()
        self._prepare_output_file()

    def _prepare_output_file(self) -> None:
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(self.output_path):
            with open(self.output_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(RiskDecision.csv_headers())

            self.logger.info("risk_output_initialized path=%s", self.output_path)

    def evaluate(self, strategy_decision: StrategyDecision, event_time_utc: str | None = None) -> RiskDecision:
        now = self._resolve_event_time(event_time_utc)
        if now is None:
            return self._persist(
                RiskDecision(
                    timestamp_utc=event_time_utc or "",
                    market=strategy_decision.market,
                    strategy_action=strategy_decision.action,
                    risk_action="BLOCKED",
                    approved=False,
                    reason="invalid_event_time_utc",
                    signal_strength=strategy_decision.signal_strength,
                    spread_pct=strategy_decision.spread_pct,
                    tick_interval_ms=strategy_decision.tick_interval_ms,
                    candidates_last_minute=len(self._candidate_timestamps),
                )
            )

        candidates_last_minute = self._count_recent_candidates(now)

        if not self.enabled:
            return self._persist(
                RiskDecision(
                    timestamp_utc=now.isoformat(),
                    market=strategy_decision.market,
                    strategy_action=strategy_decision.action,
                    risk_action="NO_ACTION",
                    approved=False,
                    reason="risk_engine_disabled",
                    signal_strength=strategy_decision.signal_strength,
                    spread_pct=strategy_decision.spread_pct,
                    tick_interval_ms=strategy_decision.tick_interval_ms,
                    candidates_last_minute=candidates_last_minute,
                )
            )

        if strategy_decision.action != "CANDIDATE_TRADE":
            return self._persist(
                RiskDecision(
                    timestamp_utc=now.isoformat(),
                    market=strategy_decision.market,
                    strategy_action=strategy_decision.action,
                    risk_action="NO_ACTION",
                    approved=False,
                    reason="no_strategy_candidate",
                    signal_strength=strategy_decision.signal_strength,
                    spread_pct=strategy_decision.spread_pct,
                    tick_interval_ms=strategy_decision.tick_interval_ms,
                    candidates_last_minute=candidates_last_minute,
                )
            )

        reasons = []
        if self.emergency_stop:
            reasons.append("emergency_stop")

        if strategy_decision.spread_pct > self.max_spread_pct:
            reasons.append("spread_above_risk_limit")

        if (
            strategy_decision.tick_interval_ms is None
            or strategy_decision.tick_interval_ms > self.max_tick_interval_ms
        ):
            reasons.append("tick_interval_above_risk_limit")

        if strategy_decision.signal_strength < self.min_signal_strength:
            reasons.append("signal_below_risk_threshold")

        if candidates_last_minute >= self.max_candidates_per_minute:
            reasons.append("candidate_rate_limit")

        approved = len(reasons) == 0
        risk_action = "APPROVED_SIMULATION" if approved else "BLOCKED"
        reason = "risk_checks_passed" if approved else "|".join(reasons)

        decision = RiskDecision(
            timestamp_utc=now.isoformat(),
            market=strategy_decision.market,
            strategy_action=strategy_decision.action,
            risk_action=risk_action,
            approved=approved,
            reason=reason,
            signal_strength=strategy_decision.signal_strength,
            spread_pct=strategy_decision.spread_pct,
            tick_interval_ms=strategy_decision.tick_interval_ms,
            candidates_last_minute=candidates_last_minute,
        )

        if approved:
            self._candidate_timestamps.append(now)

        return self._persist(decision)

    def _count_recent_candidates(self, now: datetime) -> int:
        while self._candidate_timestamps and (now - self._candidate_timestamps[0]).total_seconds() > 60:
            self._candidate_timestamps.popleft()
        return len(self._candidate_timestamps)

    def _resolve_event_time(self, event_time_utc: str | None) -> datetime | None:
        if event_time_utc is None:
            return datetime.now(timezone.utc)

        try:
            parsed = datetime.fromisoformat(event_time_utc.replace("Z", "+00:00"))
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return None

        return parsed.astimezone(timezone.utc)

    def _persist(self, decision: RiskDecision) -> RiskDecision:
        with open(self.output_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(decision.to_csv_row())

        self.logger.info(
            "risk_decision action=%s approved=%s reason=%s strength=%.8f spread_pct=%.8f",
            decision.risk_action,
            decision.approved,
            decision.reason,
            decision.signal_strength,
            decision.spread_pct,
        )

        return decision


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10f}"