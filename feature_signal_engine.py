from __future__ import annotations

import csv
import os
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock


@dataclass
class FeatureSnapshot:
    timestamp_utc: str
    market: str
    bid: float | None
    ask: float | None
    last: float | None
    spread_abs: float | None
    spread_pct: float | None
    mid_price: float | None
    micro_return_1: float | None
    micro_return_5: float | None
    spread_change_1: float | None
    spread_change_5: float | None
    tick_interval_ms: float | None
    is_valid: bool
    validation_errors: str

    @staticmethod
    def csv_headers() -> list[str]:
        return [
            "timestamp_utc",
            "market",
            "bid",
            "ask",
            "last",
            "spread_abs",
            "spread_pct",
            "mid_price",
            "micro_return_1",
            "micro_return_5",
            "spread_change_1",
            "spread_change_5",
            "tick_interval_ms",
            "is_valid",
            "validation_errors",
        ]

    def to_csv_row(self) -> list[str]:
        return [
            self.timestamp_utc,
            self.market,
            _fmt(self.bid),
            _fmt(self.ask),
            _fmt(self.last),
            _fmt(self.spread_abs),
            _fmt(self.spread_pct),
            _fmt(self.mid_price),
            _fmt(self.micro_return_1),
            _fmt(self.micro_return_5),
            _fmt(self.spread_change_1),
            _fmt(self.spread_change_5),
            _fmt(self.tick_interval_ms),
            str(self.is_valid),
            self.validation_errors,
        ]


@dataclass
class StrategyInput:
    timestamp_utc: str
    market: str
    bid: float
    ask: float
    last: float
    spread_abs: float
    spread_pct: float
    mid_price: float
    micro_return_1: float | None
    micro_return_5: float | None
    spread_change_1: float | None
    spread_change_5: float | None
    tick_interval_ms: float | None

    def to_dict(self) -> dict:
        return {
            "timestamp_utc": self.timestamp_utc,
            "market": self.market,
            "bid": self.bid,
            "ask": self.ask,
            "last": self.last,
            "spread_abs": self.spread_abs,
            "spread_pct": self.spread_pct,
            "mid_price": self.mid_price,
            "micro_return_1": self.micro_return_1,
            "micro_return_5": self.micro_return_5,
            "spread_change_1": self.spread_change_1,
            "spread_change_5": self.spread_change_5,
            "tick_interval_ms": self.tick_interval_ms,
        }


class FeatureSignalEngine:
    def __init__(self, output_path: str, logger):
        self.output_path = output_path
        self.logger = logger

        self._lock = Lock()
        self._mid_history = deque(maxlen=6)
        self._spread_history = deque(maxlen=6)
        self._last_tick_timestamp = None
        self._last_validation_errors = None
        self._latest_valid_snapshot = None

        self._prepare_output_file()

    def _prepare_output_file(self) -> None:
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(self.output_path):
            with open(self.output_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(FeatureSnapshot.csv_headers())

            self.logger.info("feature_output_initialized path=%s", self.output_path)

    def update(self, ticker_state, event_time_utc: str | None = None) -> None:
        with self._lock:
            snapshot = self._build_snapshot(ticker_state, event_time_utc=event_time_utc)
            self._append_snapshot(snapshot)

            if not snapshot.is_valid:
                if snapshot.validation_errors != self._last_validation_errors:
                    self.logger.warning("feature_validation_warning errors=%s", snapshot.validation_errors)
                    self._last_validation_errors = snapshot.validation_errors
            elif self._last_validation_errors is not None:
                self.logger.info("feature_validation_recovered")
                self._last_validation_errors = None

            if snapshot.is_valid:
                self._latest_valid_snapshot = snapshot

    def get_latest_valid_snapshot(self) -> FeatureSnapshot | None:
        with self._lock:
            return self._latest_valid_snapshot

    def get_latest_strategy_input(self) -> StrategyInput | None:
        with self._lock:
            snapshot = self._latest_valid_snapshot
            if snapshot is None:
                return None

            if (
                snapshot.bid is None
                or snapshot.ask is None
                or snapshot.last is None
                or snapshot.spread_abs is None
                or snapshot.spread_pct is None
                or snapshot.mid_price is None
            ):
                return None

            return StrategyInput(
                timestamp_utc=snapshot.timestamp_utc,
                market=snapshot.market,
                bid=snapshot.bid,
                ask=snapshot.ask,
                last=snapshot.last,
                spread_abs=snapshot.spread_abs,
                spread_pct=snapshot.spread_pct,
                mid_price=snapshot.mid_price,
                micro_return_1=snapshot.micro_return_1,
                micro_return_5=snapshot.micro_return_5,
                spread_change_1=snapshot.spread_change_1,
                spread_change_5=snapshot.spread_change_5,
                tick_interval_ms=snapshot.tick_interval_ms,
            )

    def _build_snapshot(self, ticker_state, event_time_utc: str | None = None) -> FeatureSnapshot:
        if event_time_utc is None:
            now = datetime.now(timezone.utc)
        else:
            parsed_time = _parse_event_time_utc(event_time_utc)
            if parsed_time is None:
                return FeatureSnapshot(
                    timestamp_utc=event_time_utc,
                    market=ticker_state.market,
                    bid=ticker_state.bid,
                    ask=ticker_state.ask,
                    last=ticker_state.last,
                    spread_abs=ticker_state.spread,
                    spread_pct=ticker_state.spread_percentage,
                    mid_price=ticker_state.mid_price,
                    micro_return_1=None,
                    micro_return_5=None,
                    spread_change_1=None,
                    spread_change_5=None,
                    tick_interval_ms=None,
                    is_valid=False,
                    validation_errors="invalid_event_time_utc",
                )
            now = parsed_time

        bid = ticker_state.bid
        ask = ticker_state.ask
        last = ticker_state.last
        spread_abs = ticker_state.spread
        spread_pct = ticker_state.spread_percentage
        mid_price = ticker_state.mid_price

        tick_interval_ms = None
        if self._last_tick_timestamp is not None:
            tick_interval_ms = (now - self._last_tick_timestamp).total_seconds() * 1000

        micro_return_1 = _relative_change(mid_price, self._mid_history[-1] if len(self._mid_history) >= 1 else None)
        micro_return_5 = _relative_change(mid_price, self._mid_history[-5] if len(self._mid_history) >= 5 else None)

        spread_change_1 = _difference(spread_abs, self._spread_history[-1] if len(self._spread_history) >= 1 else None)
        spread_change_5 = _difference(spread_abs, self._spread_history[-5] if len(self._spread_history) >= 5 else None)

        is_valid, validation_errors = self._validate(
            now=now,
            bid=bid,
            ask=ask,
            last=last,
            spread_abs=spread_abs,
            mid_price=mid_price,
            tick_interval_ms=tick_interval_ms,
        )

        if mid_price is not None:
            self._mid_history.append(mid_price)
        if spread_abs is not None:
            self._spread_history.append(spread_abs)
        self._last_tick_timestamp = now

        return FeatureSnapshot(
            timestamp_utc=now.isoformat(),
            market=ticker_state.market,
            bid=bid,
            ask=ask,
            last=last,
            spread_abs=spread_abs,
            spread_pct=spread_pct,
            mid_price=mid_price,
            micro_return_1=micro_return_1,
            micro_return_5=micro_return_5,
            spread_change_1=spread_change_1,
            spread_change_5=spread_change_5,
            tick_interval_ms=tick_interval_ms,
            is_valid=is_valid,
            validation_errors=validation_errors,
        )

    def _validate(
        self,
        now,
        bid,
        ask,
        last,
        spread_abs,
        mid_price,
        tick_interval_ms,
    ) -> tuple[bool, str]:
        errors = []

        if bid is None or ask is None or last is None:
            errors.append("missing_core_fields")

        if bid is not None and bid <= 0:
            errors.append("bid_non_positive")

        if ask is not None and ask <= 0:
            errors.append("ask_non_positive")

        if last is not None and last <= 0:
            errors.append("last_non_positive")

        if spread_abs is not None and spread_abs < 0:
            errors.append("negative_spread")

        if mid_price is not None and mid_price <= 0:
            errors.append("mid_non_positive")

        if self._last_tick_timestamp is not None and now <= self._last_tick_timestamp:
            errors.append("non_monotonic_timestamp")

        if tick_interval_ms is not None and tick_interval_ms <= 0:
            errors.append("non_positive_tick_interval")

        return len(errors) == 0, ";".join(errors)

    def _append_snapshot(self, snapshot: FeatureSnapshot) -> None:
        with open(self.output_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(snapshot.to_csv_row())


def _relative_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous


def _difference(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10f}"


def _parse_event_time_utc(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)