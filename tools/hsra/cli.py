from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

from .merger import canonicalize_window, HSRAError
from .emitter import write_canonical_jsonl, write_metadata, write_provenance_sidecar


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--quotes", required=True)
    p.add_argument("--trades", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--adapter-version", default="0.1.0")
    args = p.parse_args(argv)

    quotes = Path(args.quotes)
    trades = Path(args.trades)
    start = _parse_iso(args.start)
    end = _parse_iso(args.end)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        events, prov, metadata = canonicalize_window(quotes, trades, requested_start=start, requested_end=end, adapter_version=args.adapter_version)
    except HSRAError as e:
        # write rejection metadata
        out = outdir / "metadata.json"
        try:
            import json
            md = json.loads(str(e))
        except Exception:
            md = {"status": "REJECTED", "reason": str(e)}
        write_metadata(md, out)
        print("HSRA: canonicalization blocked; metadata written to", out)
        return 2

    # success
    write_canonical_jsonl(events, outdir / "canonical_events.jsonl")
    write_provenance_sidecar(prov, outdir / "provenance_sidecar.jsonl")
    write_metadata(metadata, outdir / "metadata.json")
    print("HSRA: canonicalization succeeded; outputs in", outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
