from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from accounting_engine import AccountingDecision
from execution_engine import ExecutionEvent


@dataclass
class PositionLedgerEvent:
    timestamp_utc: str
    market: str
    position_id: str
    lifecycle_action: str
    status: str
    hold_events: int
    entry_time_utc: str
    close_time_utc: str
    entry_reason: str
    exit_reason: str
    entry_signal_strength: float | None
    entry_spread_pct: float | None
    exit_signal_strength: float | None
    exit_spread_pct: float | None

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "timestamp_utc",
            "market",
            "position_id",
            "lifecycle_action",
            "status",
            "hold_events",
            "entry_time_utc",
            "close_time_utc",
            "entry_reason",
            "exit_reason",
            "entry_signal_strength",
            "entry_spread_pct",
            "exit_signal_strength",
            "exit_spread_pct",
        ]

    def to_csv_row(self) -> list[str]:
        return [
            self.timestamp_utc,
            self.market,
            self.position_id,
            self.lifecycle_action,
            self.status,
            str(self.hold_events),
            self.entry_time_utc,
            self.close_time_utc,
            self.entry_reason,
            self.exit_reason,
            _fmt(self.entry_signal_strength),
            _fmt(self.entry_spread_pct),
            _fmt(self.exit_signal_strength),
            _fmt(self.exit_spread_pct),
        ]


class PositionManager:
    def __init__(
        self,
        output_path: str,
        logger,
        enabled: bool = True,
        max_hold_events: int = 250,
    ):
        self.output_path = output_path
        self.logger = logger
        self.enabled = enabled
        self.max_hold_events = max_hold_events

        self._position_counter = 0
        self._active_position = None

        self._prepare_output_file()

    def _prepare_output_file(self) -> None:
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(self.output_path):
            with open(self.output_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(PositionLedgerEvent.csv_headers())

            self.logger.info("position_output_initialized path=%s", self.output_path)

    def process(self, execution_event: ExecutionEvent, event_time_utc: str | None = None) -> PositionLedgerEvent | None:
        raise RuntimeError("PositionManager raw ExecutionEvent path is disabled; use process_accounting_decision() only.")

    def _process_accepted_execution_event(
        self,
        execution_event: ExecutionEvent,
        event_time_utc: str | None = None,
    ) -> PositionLedgerEvent | None:
        if not self.enabled:
            return None

        resolved_time = _resolve_event_time(event_time_utc)
        if resolved_time is None and event_time_utc is not None:
            self.logger.warning("position_event_ignored reason=invalid_event_time_utc event_time_utc=%s", event_time_utc)
            return None

        now = resolved_time.isoformat() if resolved_time is not None else datetime.now(timezone.utc).isoformat()

        if self._active_position is None:
            if execution_event.execution_action != "SIMULATED_ORDER_PREPARED":
                return None

            self._position_counter += 1
            position_id = f"SIMPOS-{self._position_counter:06d}"
            self._active_position = {
                "position_id": position_id,
                "market": execution_event.market,
                "entry_time_utc": now,
                "entry_reason": execution_event.reason,
                "entry_signal_strength": execution_event.signal_strength,
                "entry_spread_pct": execution_event.spread_pct,
                "hold_events": 0,
            }

            event = PositionLedgerEvent(
                timestamp_utc=now,
                market=execution_event.market,
                position_id=position_id,
                lifecycle_action="OPENED",
                status="OPEN",
                hold_events=0,
                entry_time_utc=now,
                close_time_utc="",
                entry_reason=execution_event.reason,
                exit_reason="",
                entry_signal_strength=execution_event.signal_strength,
                entry_spread_pct=execution_event.spread_pct,
                exit_signal_strength=None,
                exit_spread_pct=None,
            )
            self._persist(event)
            return event

        if execution_event.execution_action != "SIMULATED_ORDER_PREPARED":
            return None

        self._active_position["hold_events"] += 1
        should_close = self._active_position["hold_events"] >= self.max_hold_events

        if should_close:
            event = PositionLedgerEvent(
                timestamp_utc=now,
                market=self._active_position["market"],
                position_id=self._active_position["position_id"],
                lifecycle_action="CLOSED",
                status="CLOSED",
                hold_events=self._active_position["hold_events"],
                entry_time_utc=self._active_position["entry_time_utc"],
                close_time_utc=now,
                entry_reason=self._active_position["entry_reason"],
                exit_reason="max_hold_events_reached",
                entry_signal_strength=self._active_position["entry_signal_strength"],
                entry_spread_pct=self._active_position["entry_spread_pct"],
                exit_signal_strength=execution_event.signal_strength,
                exit_spread_pct=execution_event.spread_pct,
            )
            self._persist(event)
            self._active_position = None
            return event

        event = PositionLedgerEvent(
            timestamp_utc=now,
            market=self._active_position["market"],
            position_id=self._active_position["position_id"],
            lifecycle_action="HOLD",
            status="OPEN",
            hold_events=self._active_position["hold_events"],
            entry_time_utc=self._active_position["entry_time_utc"],
            close_time_utc="",
            entry_reason=self._active_position["entry_reason"],
            exit_reason="",
            entry_signal_strength=self._active_position["entry_signal_strength"],
            entry_spread_pct=self._active_position["entry_spread_pct"],
            exit_signal_strength=None,
            exit_spread_pct=None,
        )
        self._persist(event)
        return event

    def process_accounting_decision(
        self,
        decision: AccountingDecision | None,
        event_time_utc: str | None = None,
    ) -> PositionLedgerEvent | None:
        if not self.enabled or decision is None:
            return None

        if decision.status != "ACCEPTED" or not decision.financial_effect_applied:
            self.logger.info(
                "position_decision_ignored status=%s execution_event_id=%s reason=%s",
                decision.status,
                decision.execution_event_id,
                decision.reason,
            )
            return None

        execution_event = ExecutionEvent(
            execution_event_id=decision.execution_event_id or "accounting_decision_accepted",
            timestamp_utc=event_time_utc or datetime.now(timezone.utc).isoformat(),
            market=decision.market or "UNKNOWN",
            strategy_action="ACCOUNTING_GATED",
            risk_action="ACCOUNTING_GATED",
            execution_action=decision.execution_action or "SIMULATED_ORDER_PREPARED",
            reason=decision.reason or "accounting_accepted",
            signal_strength=float(decision.signal_strength) if decision.signal_strength is not None else 0.0,
            spread_pct=float(decision.spread_pct) if decision.spread_pct is not None else 0.0,
        )
        return self._process_accepted_execution_event(execution_event, event_time_utc=event_time_utc)

    def rebuild_from_accounting(self, accounting_engine) -> dict | None:
        """Rebuild only the derived current open-position projection from authoritative accounting state.

        This method intentionally ignores the PositionManager CSV history, execution journal,
        raw ExecutionEvent data, and wall-clock timestamps. It derives the projection only from
        accounting_engine.open_position and replaces any stale local state completely.
        """
        if not self.enabled or accounting_engine is None:
            self.logger.warning("position_rebuild_rejected reason=missing_accounting_state")
            self._active_position = None
            return None

        open_position = getattr(accounting_engine, "open_position", None)
        if open_position is None:
            self._active_position = None
            self.logger.info("position_rebuild state=inactive")
            return None

        try:
            market = str(open_position.symbol)
            side = str(open_position.side)
            entry_time_utc = str(open_position.entry_timestamp_utc)
            entry_price = float(open_position.entry_price)
            position_size = float(open_position.position_size)
            trade_id = str(open_position.trade_id)
        except (AttributeError, TypeError, ValueError):
            self.logger.warning("position_rebuild_rejected reason=invalid_accounting_open_position")
            self._active_position = None
            return None

        if not market or not entry_time_utc or not trade_id:
            self.logger.warning("position_rebuild_rejected reason=incomplete_accounting_open_position")
            self._active_position = None
            return None

        deterministic_position_id = f"ACCOUNTING-{trade_id}"
        self._active_position = {
            "position_id": deterministic_position_id,
            "market": market,
            "symbol": market,
            "side": side,
            "entry_time_utc": entry_time_utc,
            "entry_price": entry_price,
            "position_size": position_size,
            "trade_id": trade_id,
            "status": "OPEN",
            "active": True,
            "hold_events": 0,
            "entry_reason": "accounting_rebuild",
            "entry_signal_strength": None,
            "entry_spread_pct": None,
        }
        self.logger.info(
            "position_rebuild_applied market=%s side=%s trade_id=%s entry_price=%.10f position_size=%.10f",
            market,
            side,
            trade_id,
            entry_price,
            position_size,
        )
        return self._active_position

    def _persist(self, event: PositionLedgerEvent) -> None:
        with open(self.output_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(event.to_csv_row())

        self.logger.info(
            "position_event action=%s status=%s position_id=%s hold_events=%s",
            event.lifecycle_action,
            event.status,
            event.position_id,
            event.hold_events,
        )


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