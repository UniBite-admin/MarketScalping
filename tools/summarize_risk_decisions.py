import argparse
import csv
import json
from pathlib import Path


DEFAULT_PATH = Path("data") / "risk_decisions_btc_eur.csv"


def summarize(path: Path) -> dict:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    total = len(rows)
    approved = sum(1 for r in rows if r.get("approved") == "True")
    blocked = sum(1 for r in rows if r.get("risk_action") == "BLOCKED")
    no_action = sum(1 for r in rows if r.get("risk_action") == "NO_ACTION")

    strategy_candidates = sum(1 for r in rows if r.get("strategy_action") == "CANDIDATE_TRADE")
    strategy_no_trade = sum(1 for r in rows if r.get("strategy_action") == "NO_TRADE")

    reason_counts = {}
    for r in rows:
        reason = (r.get("reason") or "").strip()
        if not reason:
            continue
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    first_ts = rows[0]["timestamp_utc"] if rows else None
    last_ts = rows[-1]["timestamp_utc"] if rows else None

    return {
        "path": str(path),
        "total_rows": total,
        "approved_rows": approved,
        "blocked_rows": blocked,
        "no_action_rows": no_action,
        "approved_ratio": round((approved / total), 6) if total else 0.0,
        "strategy_candidate_rows": strategy_candidates,
        "strategy_no_trade_rows": strategy_no_trade,
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "reason_counts": reason_counts,
        "acceptance_hints": {
            "has_rows": total > 0,
            "has_strategy_candidates": strategy_candidates > 0,
            "has_risk_outputs": (approved + blocked + no_action) > 0,
            "has_explicit_reasons": len(reason_counts) > 0,
        },
    }


def print_human(summary: dict) -> None:
    print("=== Risk Decision Summary ===")
    print(f"File: {summary['path']}")
    print(f"Rows: {summary['total_rows']}")
    print(f"Approved: {summary['approved_rows']}")
    print(f"Blocked: {summary['blocked_rows']}")
    print(f"No Action: {summary['no_action_rows']}")
    print(f"Approved ratio: {summary['approved_ratio']:.4f}")
    print(f"Strategy candidates: {summary['strategy_candidate_rows']}")
    print(f"Strategy no-trade: {summary['strategy_no_trade_rows']}")
    print(f"First timestamp: {summary['first_timestamp']}")
    print(f"Last timestamp:  {summary['last_timestamp']}")
    print()
    print("Top reasons")
    if not summary["reason_counts"]:
        print("- none")
    else:
        for reason, count in sorted(summary["reason_counts"].items(), key=lambda kv: kv[1], reverse=True)[:10]:
            print(f"- {reason}: {count}")
    print()
    print("Acceptance hints")
    hints = summary["acceptance_hints"]
    for key in ["has_rows", "has_strategy_candidates", "has_risk_outputs", "has_explicit_reasons"]:
        print(f"- {key}: {hints[key]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize risk decision outputs for MarketScalping.")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="Path to risk decisions CSV")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"Risk decision file not found: {path}")

    summary = summarize(path)
    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print_human(summary)


if __name__ == "__main__":
    main()