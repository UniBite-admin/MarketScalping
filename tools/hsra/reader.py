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
        # Accept Z or offset-aware
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


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
            ts = _parse_iso_ts(row.get("timestamp") or row.get("event_time") or row.get("event_time_utc") or "")
            yield SourceRecord(
                source="quote",
                source_id=str(row.get("quote_id") or f"{path.name}:{offset}"),
                market=str(row.get("market") or row.get("symbol") or "").replace("/", "-").upper(),
                ts=ts,
                bid=float(row["bid"]) if row.get("bid") else None,
                ask=float(row["ask"]) if row.get("ask") else None,
                price=None,
                raw_row=row,
            )


def iter_trades(path: Path) -> Iterator[SourceRecord]:
    with _open_csv(path) as handle:
        reader = csv.DictReader(handle)
        for offset, row in enumerate(reader):
            ts = _parse_iso_ts(row.get("timestamp") or row.get("event_time") or row.get("event_time_utc") or "")
            yield SourceRecord(
                source="trade",
                source_id=str(row.get("trade_id") or f"{path.name}:{offset}"),
                market=str(row.get("market") or row.get("symbol") or "").replace("/", "-").upper(),
                ts=ts,
                bid=None,
                ask=None,
                price=float(row["price"]) if row.get("price") else None,
                raw_row=row,
            )
