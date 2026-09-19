from __future__ import annotations

import csv
import json
import math
import re
import sqlite3
import tempfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

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
    dataset_status: str = "REJECTED"
    canonicalization_result: str = "REJECTED"


@dataclass(frozen=True)
class _CsvSummary:
    row_count: int
    timestamps: tuple[str, ...]
    last_row: dict[str, str]


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

    def replay(
        self,
        events: Iterable[dict],
        *,
        assume_canonical_chronological: bool = False,
        summary_mode: bool = False,
    ) -> ReplayResult:
        rejection_reasons = Counter()
        total_event_count = 0
        events_processed = 0
        capture_timestamps = not summary_mode
        event_timestamps: list[str] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            if assume_canonical_chronological:
                engine = self._build_engine(output_dir)
                for original_index, raw_event in enumerate(events):
                    total_event_count += 1
                    normalized_event, rejection_reason = _normalize_replay_event(raw_event, original_index)
                    if normalized_event is None:
                        rejection_reasons[rejection_reason] += 1
                        continue
                    if _should_skip_historical_event(normalized_event):
                        rejection_reasons["historical_trade_only_event"] += 1
                        continue
                    events_processed += 1
                    if capture_timestamps:
                        event_timestamps.append(normalized_event.event_time_utc)
                    engine.handle_control_message(
                        _to_market_data_message(normalized_event),
                        event_time_utc=normalized_event.event_time_utc,
                    )

                return _build_replay_result(
                    output_dir=output_dir,
                    events_total=total_event_count,
                    events_processed=events_processed,
                    rejection_reasons=rejection_reasons,
                    event_timestamps=tuple(event_timestamps),
                    capture_timestamps=capture_timestamps,
                )

            db_path = output_dir / "normalized_events.sqlite3"
            connection = sqlite3.connect(str(db_path))
            connection.execute(
                """
                CREATE TABLE normalized_events (
                    sort_key REAL NOT NULL,
                    original_index INTEGER NOT NULL,
                    event_time_utc TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    market TEXT NOT NULL,
                    bid REAL,
                    ask REAL,
                    last REAL
                )
                """
            )
            try:
                for original_index, raw_event in enumerate(events):
                    total_event_count += 1
                    normalized_event, rejection_reason = _normalize_replay_event(raw_event, original_index)
                    if normalized_event is None:
                        rejection_reasons[rejection_reason] += 1
                        continue
                    connection.execute(
                        "INSERT INTO normalized_events (sort_key, original_index, event_time_utc, event_type, market, bid, ask, last) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            normalized_event.event_time_dt.timestamp(),
                            original_index,
                            normalized_event.event_time_utc,
                            normalized_event.event_type,
                            normalized_event.market,
                            normalized_event.bid,
                            normalized_event.ask,
                            normalized_event.last,
                        ),
                    )
                connection.commit()
                engine = self._build_engine(output_dir)
                for row in connection.execute(
                    "SELECT original_index, event_time_utc, event_type, market, bid, ask, last FROM normalized_events ORDER BY sort_key ASC, original_index ASC"
                ):
                    original_index, event_time_utc, event_type, market, bid, ask, last = row
                    normalized_event = _NormalizedReplayEvent(
                        original_index=original_index,
                        event_time_utc=event_time_utc,
                        event_time_dt=_parse_event_time_utc(event_time_utc),
                        event_type=event_type,
                        market=market,
                        bid=bid,
                        ask=ask,
                        last=last,
                    )
                    if _should_skip_historical_event(normalized_event):
                        rejection_reasons["historical_trade_only_event"] += 1
                        continue
                    events_processed += 1
                    if capture_timestamps:
                        event_timestamps.append(event_time_utc)
                    engine.handle_control_message(
                        _to_market_data_message(normalized_event),
                        event_time_utc=normalized_event.event_time_utc,
                    )
            finally:
                connection.close()

            return _build_replay_result(
                output_dir=output_dir,
                events_total=total_event_count,
                events_processed=events_processed,
                rejection_reasons=rejection_reasons,
                event_timestamps=tuple(event_timestamps),
                capture_timestamps=capture_timestamps,
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
    return list(iter_replay_events_jsonl(path))


def iter_replay_events_jsonl(path: str | Path) -> Iterator[dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            yield json.loads(raw)


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


def _should_skip_historical_event(event: _NormalizedReplayEvent) -> bool:
    return event.event_type == "trade"


def _build_replay_result(
    output_dir: Path,
    events_total: int,
    events_processed: int,
    rejection_reasons: Counter,
    event_timestamps: tuple[str, ...],
    capture_timestamps: bool,
) -> ReplayResult:
    strategy_summary = _summarize_csv(output_dir / "strategy.csv", capture_timestamps=capture_timestamps)
    risk_summary = _summarize_csv(output_dir / "risk.csv", capture_timestamps=capture_timestamps)
    execution_summary = _summarize_csv(output_dir / "execution.csv", capture_timestamps=capture_timestamps)
    position_summary = _summarize_csv(output_dir / "positions.csv", capture_timestamps=capture_timestamps)
    account_summary = _summarize_csv(output_dir / "account_state.csv", capture_timestamps=capture_timestamps)
    trade_summary = _summarize_csv(output_dir / "trade_ledger.csv", capture_timestamps=capture_timestamps)

    final_account = account_summary.last_row
    dataset_status, canonicalization_result = _classify_dataset_status(events_total, events_processed)

    return ReplayResult(
        events_total=events_total,
        events_processed=events_processed,
        events_rejected=events_total - events_processed,
        rejection_reasons=tuple(sorted(rejection_reasons.items())),
        strategy_decisions=strategy_summary.row_count,
        risk_decisions=risk_summary.row_count,
        execution_events=execution_summary.row_count,
        position_events=position_summary.row_count,
        closed_trade_count=trade_summary.row_count,
        final_account_balance=_to_float(final_account.get("available_balance")),
        final_equity=_to_float(final_account.get("equity")),
        realized_pnl=_to_float(final_account.get("realized_pnl")),
        event_timestamps=event_timestamps,
        strategy_timestamps=strategy_summary.timestamps,
        risk_timestamps=risk_summary.timestamps,
        execution_timestamps=execution_summary.timestamps,
        position_timestamps=position_summary.timestamps,
        account_timestamps=account_summary.timestamps,
        trade_timestamps=trade_summary.timestamps,
        dataset_status=dataset_status,
        canonicalization_result=canonicalization_result,
    )


def _summarize_csv(path: Path, *, capture_timestamps: bool) -> _CsvSummary:
    if not path.exists():
        return _CsvSummary(row_count=0, timestamps=(), last_row={})

    row_count = 0
    timestamps: list[str] = []
    last_row: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            row_count += 1
            last_row = row
            if capture_timestamps:
                timestamp = row.get("timestamp_utc")
                if timestamp:
                    timestamps.append(timestamp)
    return _CsvSummary(row_count=row_count, timestamps=tuple(timestamps), last_row=last_row)


def _classify_dataset_status(events_total: int, events_processed: int) -> tuple[str, str]:
    if events_total == 0:
        return "EMPTY_VALID_DATASET", "NOT_APPLICABLE"
    if events_processed == 0:
        return "REJECTED", "REJECTED"
    return "CANONICALIZED", "SUCCESS"


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
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("non-finite number")
    return value