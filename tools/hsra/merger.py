from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .reader import SourceRecord, iter_quotes, iter_trades, compute_sha256


@dataclass
class CanonicalEvent:
    event_time_utc: str
    event_type: str
    market: str
    bid: float
    ask: float
    last: float


class HSRAError(Exception):
    pass


def _ensure_valid_number(v: Optional[float]) -> bool:
    return v is not None and isinstance(v, float) and v > 0


def _stable_identity_for_metadata(adapter_version: str, quotes_sha: str, trades_sha: str, canonical_events: List[CanonicalEvent]) -> str:
    payload = {
        "adapter_version": adapter_version,
        "quotes_sha256": quotes_sha,
        "trades_sha256": trades_sha,
        "ordering_rule": "timestamp_asc",
        "tie_break_rule": "trade_before_quote_when_equal_ts",
        "canonical_events": [
            {
                "event_time_utc": e.event_time_utc,
                "event_type": e.event_type,
                "market": e.market,
                "bid": e.bid,
                "ask": e.ask,
                "last": e.last,
            }
            for e in canonical_events
        ],
    }
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def canonicalize_window(quotes_path: Path, trades_path: Path, *, requested_start: datetime, requested_end: datetime, adapter_version: str = "0.1.0") -> Tuple[List[CanonicalEvent], List[dict], dict]:
    """Return (canonical_events, provenance_records, metadata)

    Strict fail-closed behavior per Step 7.3 contract:
    - missing required source file => INPUT_MISSING / COLLECTION_INCOMPLETE
    - valid source with incomplete requested window => PARTIAL_WINDOW => reject
    - complete source coverage => canonicalize
    """
    if not quotes_path.exists() or not quotes_path.is_file():
        raise HSRAError(json.dumps({
            "dataset_status": "REJECTED",
            "completeness_status": "INPUT_MISSING",
            "reason": "missing_required_source_file",
            "source": "quotes",
            "source_path": str(quotes_path),
        }))
    if not trades_path.exists() or not trades_path.is_file():
        raise HSRAError(json.dumps({
            "dataset_status": "REJECTED",
            "completeness_status": "INPUT_MISSING",
            "reason": "missing_required_source_file",
            "source": "trades",
            "source_path": str(trades_path),
        }))

    quotes = list(iter_quotes(quotes_path))
    trades = list(iter_trades(trades_path))

    # Filter to requested window
    quotes_in_window = [q for q in quotes if q.ts is not None and requested_start <= q.ts <= requested_end]
    trades_in_window = [t for t in trades if t.ts is not None and requested_start <= t.ts <= requested_end]

    quotes_sha = compute_sha256(quotes_path)
    trades_sha = compute_sha256(trades_path)
    metadata = {
        "dataset_status": "REJECTED",
        "completeness_status": "INPUT_MISSING",
        "input_quote_count": len(quotes_in_window),
        "input_trade_count": len(trades_in_window),
        "quotes_path_sha256": quotes_sha,
        "trades_path_sha256": trades_sha,
        "adapter_version": adapter_version,
        "ordering_rule": "timestamp_asc",
        "tie_break_rule": "trade_before_quote_when_equal_ts",
    }

    if len(trades_in_window) == 0:
        metadata["dataset_status"] = "REJECTED"
        metadata["completeness_status"] = "PARTIAL_WINDOW"
        metadata["reason"] = "no_trades_in_requested_window"
        raise HSRAError(json.dumps(metadata))

    # Determine first trade timestamp
    first_trade_ts = min(t.ts for t in trades_in_window)
    # Are there any quotes before first_trade_ts within the requested window?
    pre_first_trade_quotes = [q for q in quotes_in_window if q.ts < first_trade_ts]
    if pre_first_trade_quotes:
        metadata["dataset_status"] = "REJECTED"
        metadata["completeness_status"] = "PARTIAL_WINDOW"
        metadata["reason"] = "pre_first_trade_quotes_present"
        metadata["excluded_count"] = len(pre_first_trade_quotes)
        metadata["excluded_range"] = (pre_first_trade_quotes[0].ts.isoformat(), pre_first_trade_quotes[-1].ts.isoformat())
        raise HSRAError(json.dumps(metadata))

    metadata["dataset_status"] = "CANONICALIZED"
    metadata["completeness_status"] = "COMPLETE"

    # Merge by timestamp, trade before quote on equal ts
    events = []
    combined = []
    for t in trades_in_window:
        combined.append((t.ts, 0, t))
    for q in quotes_in_window:
        combined.append((q.ts, 1, q))
    combined.sort(key=lambda x: (x[0].timestamp(), x[1]))

    last_trade: Optional[SourceRecord] = None
    canonical_events: List[CanonicalEvent] = []
    provenance: List[dict] = []
    index = 0
    for ts, kind, rec in combined:
        if kind == 0:
            # trade
            if rec.price is None or rec.price <= 0:
                metadata = {"status": "REJECTED", "reason": "invalid_trade_price", "trade_id": rec.source_id}
                raise HSRAError(json.dumps(metadata))
            last_trade = rec
            continue
        # quote
        if rec.bid is None or rec.ask is None:
            metadata = {"status": "REJECTED", "reason": "missing_bid_ask", "quote_id": rec.source_id}
            raise HSRAError(json.dumps(metadata))
        if not (rec.bid < rec.ask):
            metadata = {"status": "REJECTED", "reason": "bid_not_lt_ask", "quote_id": rec.source_id}
            raise HSRAError(json.dumps(metadata))
        if last_trade is None:
            metadata = {"status": "REJECTED", "reason": "no_prior_trade_for_quote", "quote_id": rec.source_id}
            raise HSRAError(json.dumps(metadata))
        # build canonical
        ce = CanonicalEvent(
            event_time_utc=rec.ts.isoformat(),
            event_type="ticker",
            market=rec.market,
            bid=rec.bid,
            ask=rec.ask,
            last=last_trade.price,
        )
        canonical_events.append(ce)
        provenance.append({
            "canonical_index": index,
            "canonical_event_time": ce.event_time_utc,
            "source_quote_id": rec.source_id,
            "source_quote_ts": rec.ts.isoformat(),
            "source_trade_id": last_trade.source_id,
            "source_trade_ts": last_trade.ts.isoformat(),
            "adapter_version": adapter_version,
            "tie_break_rule": "trade_before_quote_when_equal_ts",
        })
        index += 1

    # metadata
    metadata.update({
        "dataset_status": "CANONICALIZED",
        "completeness_status": "COMPLETE",
        "status": "CANONICALIZED",
        "emitted_canonical_count": len(canonical_events),
        "adapter_version": adapter_version,
        "ordering_rule": "timestamp_asc",
        "tie_break_rule": "trade_before_quote_when_equal_ts",
        "deterministic_identity": _stable_identity_for_metadata(adapter_version, quotes_sha, trades_sha, canonical_events),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })

    return canonical_events, provenance, metadata
