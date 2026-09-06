import argparse
import csv
import json
from pathlib import Path


DEFAULT_PATH = Path("data") / "positions_simulation_btc_eur.csv"


def summarize(path: Path) -> dict:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    total = len(rows)
    opened = sum(1 for row in rows if row.get("lifecycle_action") == "OPENED")
    hold = sum(1 for row in rows if row.get("lifecycle_action") == "HOLD")
    closed = sum(1 for row in rows if row.get("lifecycle_action") == "CLOSED")

    position_ids = {row.get("position_id") for row in rows if row.get("position_id")}
    first_ts = rows[0]["timestamp_utc"] if rows else None
    last_ts = rows[-1]["timestamp_utc"] if rows else None

    open_positions = set()
    for row in rows:
        pid = row.get("position_id")
        action = row.get("lifecycle_action")
        if not pid:
            continue
        if action == "OPENED":
            open_positions.add(pid)
        if action == "CLOSED" and pid in open_positions:
            open_positions.remove(pid)

    return {
        "path": str(path),
        "total_rows": total,
        "opened_rows": opened,
        "hold_rows": hold,
        "closed_rows": closed,
        "unique_positions": len(position_ids),
        "currently_open_positions": len(open_positions),
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "acceptance_hints": {
            "has_rows": total > 0,
            "has_open_events": opened > 0,
            "has_lifecycle_records": (opened + hold + closed) > 0,
            "open_count_reasonable": len(open_positions) <= 1,
        },
    }


def print_human(summary: dict) -> None:
    print("=== Position Ledger Summary ===")
    print(f"File: {summary['path']}")
    print(f"Rows: {summary['total_rows']}")
    print(f"Opened: {summary['opened_rows']}")
    print(f"Hold: {summary['hold_rows']}")
    print(f"Closed: {summary['closed_rows']}")
    print(f"Unique positions: {summary['unique_positions']}")
    print(f"Currently open positions: {summary['currently_open_positions']}")
    print(f"First timestamp: {summary['first_timestamp']}")
    print(f"Last timestamp:  {summary['last_timestamp']}")
    print()
    print("Acceptance hints")
    for key, value in summary["acceptance_hints"].items():
        print(f"- {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize simulation position ledger for MarketScalping.")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="Path to position ledger CSV")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"Position file not found: {path}")

    summary = summarize(path)
    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print_human(summary)


if __name__ == "__main__":
    main()
