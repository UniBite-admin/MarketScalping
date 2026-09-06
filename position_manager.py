from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone

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