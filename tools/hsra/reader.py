from __future__ import annotations

import csv
import gzip
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from io import TextIOWrapper
from pathlib import Path
from typing import Iterable, Iterator, Optional, Tuple


@dataclass(frozen=True)
class SourceRecord:
    source: str  # "quote" or "trade"
    source_id: str
    market: str
    ts: datetime
    bid: Optional[float]
    ask: Optional[float]
    price: Optional[float]
    raw_row: dict


def _open_csv(path: Path):
    if path.suffix.lower().endswith(".gz"):
        f = gzip.open(path, "rt", encoding="utf-8")
        return f
    return path.open("r", encoding="utf-8", newline="")


def _parse_iso_ts(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Accept Z or offset-aware ISO-8601 timestamps.
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _parse_tardis_epoch_microseconds(s: str) -> Optional[datetime]:
    if s is None:
        return None
    value = str(s).strip()
    if not value:
        return None
    if value.startswith("-"):
        return None
    try:
        ts_int = int(value)
    except ValueError:
        return None
    # Tardis is explicit: integer epoch timestamps in microseconds.
    try:
        return datetime.fromtimestamp(ts_int / 1_000_000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _parse_ts_value(s: str) -> Optional[datetime]:
    if not s:
        return None
    normalized = str(s).strip()
    if not normalized:
        return None
    # Explicit Tardis epoch-microseconds support. Keep ISO parsing for contract-compatible inputs.
    if normalized.isdigit():
        return _parse_tardis_epoch_microseconds(normalized)
    iso_dt = _parse_iso_ts(normalized)
    if iso_dt is not None:
        return iso_dt
    return None


def _normalize_market(value: object) -> str:
    raw = str(value or "").strip().replace("/", "-").replace("_", "-").upper()
    if not raw:
        return ""
    if "-" in raw:
        return raw
    if len(raw) >= 6 and raw[:-3].isalpha() and raw[-3:].isalpha():
        return f"{raw[:-3]}-{raw[-3:]}"
    return raw


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    if path.suffix.lower().endswith(".gz"):
        f = gzip.open(path, "rb")
    else:
        f = path.open("rb")
    with f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_quotes(path: Path) -> Iterator[SourceRecord]:
    with _open_csv(path) as handle:
        reader = csv.DictReader(handle)
        for offset, row in enumerate(reader):
            ts = _parse_ts_value(row.get("timestamp") or row.get("event_time") or row.get("event_time_utc") or "")
            bid_value = row.get("bid_price") if row.get("bid_price") not in (None, "") else row.get("bid")
            ask_value = row.get("ask_price") if row.get("ask_price") not in (None, "") else row.get("ask")
            yield SourceRecord(
                source="quote",
                source_id=str(row.get("quote_id") or f"{path.name}:{offset}"),
                market=_normalize_market(row.get("market") or row.get("symbol") or ""),
                ts=ts,
                bid=float(bid_value) if bid_value not in (None, "") else None,
                ask=float(ask_value) if ask_value not in (None, "") else None,
                price=None,
                raw_row=row,
            )


def iter_trades(path: Path) -> Iterator[SourceRecord]:
    with _open_csv(path) as handle:
        reader = csv.DictReader(handle)
        for offset, row in enumerate(reader):
            ts = _parse_ts_value(row.get("timestamp") or row.get("event_time") or row.get("event_time_utc") or "")
            yield SourceRecord(
                source="trade",
                source_id=str(row.get("trade_id") or row.get("id") or f"{path.name}:{offset}"),
                market=_normalize_market(row.get("market") or row.get("symbol") or ""),
                ts=ts,
                bid=None,
                ask=None,
                price=float(row["price"]) if row.get("price") else None,
                raw_row=row,
            )
