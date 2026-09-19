from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .merger import CanonicalEvent


def write_canonical_jsonl(events: Iterable[CanonicalEvent], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as fh:
        for ev in events:
            obj = {
                "event_time_utc": ev.event_time_utc,
                "event_type": ev.event_type,
                "market": ev.market,
                "bid": ev.bid,
                "ask": ev.ask,
                "last": ev.last,
            }
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")


def write_provenance_sidecar(provenance: List[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in provenance:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")


def write_metadata(metadata: dict, out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(metadata, indent=2))
