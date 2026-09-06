from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from risk_engine import RiskDecision


@dataclass
class ExecutionEvent:
    execution_event_id: str
    timestamp_utc: str
    market: str
    strategy_action: str
    risk_action: str
    execution_action: str
    reason: str
    signal_strength: float
    spread_pct: float

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "execution_event_id",
            "timestamp_utc",
            "market",
            "strategy_action",
            "risk_action",
            "execution_action",
            "reason",
            "signal_strength",
            "spread_pct",
        ]

    def to_csv_row(self) -> list[str]:
        return [
            self.execution_event_id,
            self.timestamp_utc,
            self.market,
            self.strategy_action,
            self.risk_action,
            self.execution_action,
            self.reason,
            _fmt(self.signal_strength),
            _fmt(self.spread_pct),
        ]


class ExecutionEngine:
    def __init__(self, output_path: str, logger, enabled: bool = True):
        self.output_path = output_path
        self.logger = logger
        self.enabled = enabled
        self._prepare_output_file()

    def _prepare_output_file(self) -> None:
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(self.output_path):
            with open(self.output_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(ExecutionEvent.csv_headers())

            self.logger.info("execution_output_initialized path=%s", self.output_path)

    def process(self, risk_decision: RiskDecision, event_time_utc: str | None = None) -> ExecutionEvent:
        resolved_time = _resolve_event_time(event_time_utc)
        if resolved_time is None and event_time_utc is not None:
            event = ExecutionEvent(
                execution_event_id=_build_execution_event_id(risk_decision=risk_decision),
                timestamp_utc=event_time_utc,
                market=risk_decision.market,
                strategy_action=risk_decision.strategy_action,
                risk_action=risk_decision.risk_action,
                execution_action="NO_ACTION",
                reason="invalid_event_time_utc",
                signal_strength=risk_decision.signal_strength,
                spread_pct=risk_decision.spread_pct,
            )
            self._persist(event)
            return event

        now = resolved_time.isoformat() if resolved_time is not None else datetime.now(timezone.utc).isoformat()
        execution_event_id = _build_execution_event_id(risk_decision=risk_decision)

        if not self.enabled:
            event = ExecutionEvent(
                execution_event_id=execution_event_id,
                timestamp_utc=now,
                market=risk_decision.market,
                strategy_action=risk_decision.strategy_action,
                risk_action=risk_decision.risk_action,
                execution_action="NO_ACTION",
                reason="execution_engine_disabled",
                signal_strength=risk_decision.signal_strength,
                spread_pct=risk_decision.spread_pct,
            )
            self._persist(event)
            return event

        if risk_decision.approved:
            event = ExecutionEvent(
                execution_event_id=execution_event_id,
                timestamp_utc=now,
                market=risk_decision.market,
                strategy_action=risk_decision.strategy_action,
                risk_action=risk_decision.risk_action,
                execution_action="SIMULATED_ORDER_PREPARED",
                reason="risk_approved_dry_run_only",
                signal_strength=risk_decision.signal_strength,
                spread_pct=risk_decision.spread_pct,
            )
        else:
            event = ExecutionEvent(
                execution_event_id=execution_event_id,
                timestamp_utc=now,
                market=risk_decision.market,
                strategy_action=risk_decision.strategy_action,
                risk_action=risk_decision.risk_action,
                execution_action="SKIPPED",
                reason=risk_decision.reason,
                signal_strength=risk_decision.signal_strength,
                spread_pct=risk_decision.spread_pct,
            )

        self._persist(event)
        return event

    def _persist(self, event: ExecutionEvent) -> None:
        with open(self.output_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(event.to_csv_row())

        self.logger.info(
            "execution_event action=%s reason=%s strategy_action=%s risk_action=%s",
            event.execution_action,
            event.reason,
            event.strategy_action,
            event.risk_action,
        )


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10f}"


def _build_execution_event_id(risk_decision: RiskDecision) -> str:
    return "|".join(
        [
            risk_decision.timestamp_utc,
            risk_decision.market,
            risk_decision.strategy_action,
            risk_decision.risk_action,
            risk_decision.reason,
            _fmt(risk_decision.signal_strength),
            _fmt(risk_decision.spread_pct),
        ]
    )


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