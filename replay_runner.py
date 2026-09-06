from __future__ import annotations

import csv
import json
import re
import tempfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import market_data_engine as market_data_module
from market_data_engine import MarketDataEngine


MARKET_RE = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+$")


@dataclass(frozen=True)
class ReplayResult:
    events_total: int
    events_processed: int
    events_rejected: int
    rejection_reasons: tuple[tuple[str, int], ...]
    strategy_decisions: int
    risk_decisions: int
    execution_events: int
    position_events: int
    closed_trade_count: int
    final_account_balance: float | None
    final_equity: float | None
    realized_pnl: float | None
    event_timestamps: tuple[str, ...]
    strategy_timestamps: tuple[str, ...]
    risk_timestamps: tuple[str, ...]
    execution_timestamps: tuple[str, ...]
    position_timestamps: tuple[str, ...]
    account_timestamps: tuple[str, ...]
    trade_timestamps: tuple[str, ...]


@dataclass(frozen=True)
class _NormalizedReplayEvent:
    original_index: int
    event_time_utc: str
    event_time_dt: datetime
    event_type: str
    market: str
    bid: float | None
    ask: float | None
    last: float | None


class _NullLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None

    def debug(self, *args, **kwargs):
        return None


class ReplayRunner:
    """Minimal offline replay runner that reuses the live MarketDataEngine pipeline.

    Events are sorted chronologically by their canonical UTC timestamp before replay.
    """

    def __init__(
        self,
        market: str = "BTC-EUR",
        position_max_hold_events: int = 2,
        accounting_order_notional_eur: float = 10.0,
        accounting_starting_balance: float = 1000.0,
        accounting_fee_rate: float = 0.001,
        accounting_slippage_bps: float = 1.0,
    ):
        self.market = market
        self.position_max_hold_events = position_max_hold_events
        self.accounting_order_notional_eur = accounting_order_notional_eur
        self.accounting_starting_balance = accounting_starting_balance
        self.accounting_fee_rate = accounting_fee_rate
        self.accounting_slippage_bps = accounting_slippage_bps

    def replay(self, events: Iterable[dict]) -> ReplayResult:
        raw_events = list(events)
        normalized_events: list[_NormalizedReplayEvent] = []
        rejection_reasons = Counter()

        for original_index, raw_event in enumerate(raw_events):
            normalized_event, rejection_reason = _normalize_replay_event(raw_event, original_index)
            if normalized_event is None:
                rejection_reasons[rejection_reason] += 1
                continue
            normalized_events.append(normalized_event)

        normalized_events.sort(key=lambda item: (item.event_time_dt, item.original_index))

        with tempfile.TemporaryDirectory() as temp_dir:
            engine = self._build_engine(Path(temp_dir))
            for normalized_event in normalized_events:
                engine.handle_control_message(
                    _to_market_data_message(normalized_event),
                    event_time_utc=normalized_event.event_time_utc,
                )

            return _build_replay_result(
                output_dir=Path(temp_dir),
                events_total=len(raw_events),
                events_processed=len(normalized_events),
                rejection_reasons=rejection_reasons,
                normalized_events=normalized_events,
            )

    def _build_engine(self, output_dir: Path) -> MarketDataEngine:
        no_op_logger = _NullLogger()
        original_configure_logging = market_data_module.configure_logging

        def _patched_configure_logging(debug: bool = False):
            return no_op_logger

        market_data_module.configure_logging = _patched_configure_logging
        try:
            return MarketDataEngine(
                market=self.market,
                debug=False,
                feature_output_path=str(output_dir / "features.csv"),
                feature_engine_enabled=True,
                strategy_output_path=str(output_dir / "strategy.csv"),
                strategy_engine_enabled=True,
                risk_output_path=str(output_dir / "risk.csv"),
                risk_engine_enabled=True,
                execution_output_path=str(output_dir / "execution.csv"),
                execution_engine_enabled=True,
                position_output_path=str(output_dir / "positions.csv"),
                position_manager_enabled=True,
                position_max_hold_events=self.position_max_hold_events,
                accounting_engine_enabled=True,
                accounting_trade_ledger_path=str(output_dir / "trade_ledger.csv"),
                accounting_account_state_path=str(output_dir / "account_state.csv"),
                accounting_open_position_state_path=str(output_dir / "open_position_state.json"),
                accounting_starting_balance=self.accounting_starting_balance,
                accounting_order_notional_eur=self.accounting_order_notional_eur,
                accounting_fee_rate=self.accounting_fee_rate,
                accounting_slippage_bps=self.accounting_slippage_bps,
            )
        finally:
            market_data_module.configure_logging = original_configure_logging


def load_replay_events_jsonl(path: str | Path) -> list[dict]:
    events: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            events.append(json.loads(raw))
    return events


def _normalize_replay_event(raw_event: dict, original_index: int) -> tuple[_NormalizedReplayEvent | None, str]:
    if not isinstance(raw_event, dict):
        return None, "invalid_event_object"

    event_time_utc = raw_event.get("event_time_utc")
    event_time_dt = _parse_event_time_utc(event_time_utc)
    if event_time_dt is None:
        return None, "invalid_event_time_utc"

    event_type = str(raw_event.get("event_type") or "ticker").strip().lower()
    if event_type not in {"ticker", "trade"}:
        return None, "invalid_event_type"

    market = str(raw_event.get("market") or "").strip()
    if not MARKET_RE.match(market):
        return None, "invalid_market"

    try:
        bid = _to_float(raw_event.get("bid"))
        ask = _to_float(raw_event.get("ask"))
        last = _to_float(raw_event.get("last"))
    except ValueError:
        return None, "invalid_price"

    if event_type == "ticker":
        if bid is None or ask is None or last is None:
            return None, "missing_required_price"
        if bid <= 0:
            return None, "non_positive_bid"
        if ask <= 0:
            return None, "non_positive_ask"
        if last <= 0:
            return None, "non_positive_last"
    else:
        if last is None:
            return None, "missing_required_price"
        if last <= 0:
            return None, "non_positive_price"
        bid = bid if bid is not None and bid > 0 else last
        ask = ask if ask is not None and ask > 0 else last

    return (
        _NormalizedReplayEvent(
            original_index=original_index,
            event_time_utc=event_time_dt.isoformat(),
            event_time_dt=event_time_dt,
            event_type=event_type,
            market=market,
            bid=bid,
            ask=ask,
            last=last,
        ),
        "",
    )


def _to_market_data_message(event: _NormalizedReplayEvent) -> dict:
    if event.event_type == "trade":
        return {
            "event": "trade",
            "market": event.market,
            "price": event.last,
        }

    return {
        "event": "ticker",
        "market": event.market,
        "bestBid": event.bid,
        "bestAsk": event.ask,
        "lastPrice": event.last,
    }


def _build_replay_result(
    output_dir: Path,
    events_total: int,
    events_processed: int,
    rejection_reasons: Counter,
    normalized_events: list[_NormalizedReplayEvent],
) -> ReplayResult:
    strategy_rows = _read_csv_rows(output_dir / "strategy.csv")
    risk_rows = _read_csv_rows(output_dir / "risk.csv")
    execution_rows = _read_csv_rows(output_dir / "execution.csv")
    position_rows = _read_csv_rows(output_dir / "positions.csv")
    account_rows = _read_csv_rows(output_dir / "account_state.csv")
    trade_rows = _read_csv_rows(output_dir / "trade_ledger.csv")

    final_account = account_rows[-1] if account_rows else {}

    return ReplayResult(
        events_total=events_total,
        events_processed=events_processed,
        events_rejected=events_total - events_processed,
        rejection_reasons=tuple(sorted(rejection_reasons.items())),
        strategy_decisions=len(strategy_rows),
        risk_decisions=len(risk_rows),
        execution_events=len(execution_rows),
        position_events=len(position_rows),
        closed_trade_count=len(trade_rows),
        final_account_balance=_to_float(final_account.get("available_balance")),
        final_equity=_to_float(final_account.get("equity")),
        realized_pnl=_to_float(final_account.get("realized_pnl")),
        event_timestamps=tuple(event.event_time_utc for event in normalized_events),
        strategy_timestamps=tuple(_csv_column(strategy_rows, "timestamp_utc")),
        risk_timestamps=tuple(_csv_column(risk_rows, "timestamp_utc")),
        execution_timestamps=tuple(_csv_column(execution_rows, "timestamp_utc")),
        position_timestamps=tuple(_csv_column(position_rows, "timestamp_utc")),
        account_timestamps=tuple(_csv_column(account_rows, "timestamp_utc")),
        trade_timestamps=tuple(_csv_column(trade_rows, "timestamp_utc")),
    )


def _read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _csv_column(rows: list[dict], column: str) -> list[str]:
    values = []
    for row in rows:
        value = row.get(column)
        if value:
            values.append(value)
    return values


def _parse_event_time_utc(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _to_float(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    return float(raw)