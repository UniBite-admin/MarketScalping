import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


DEFAULT_PATH = Path("data") / "normalized_events.csv"


def parse_iso(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_float(raw: str) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def summarize(path: Path) -> dict:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    total_rows = len(rows)
    layer_counts = Counter(row.get("layer", "") for row in rows)

    timestamps = [parse_iso(row.get("event_time_utc", "")) for row in rows]
    valid_timestamps = [ts for ts in timestamps if ts is not None]
    first_ts = min(valid_timestamps) if valid_timestamps else None
    last_ts = max(valid_timestamps) if valid_timestamps else None
    span_seconds = round((last_ts - first_ts).total_seconds(), 3) if first_ts and last_ts else 0.0
    events_per_min = round(total_rows / (span_seconds / 60), 3) if span_seconds > 0 else 0.0

    strategy_rows = [r for r in rows if r.get("layer") == "strategy"]
    strategy_action_counts = Counter(r.get("action", "") for r in strategy_rows)
    candidate_count = strategy_action_counts.get("CANDIDATE_TRADE", 0)
    no_trade_count = strategy_action_counts.get("NO_TRADE", 0)

    risk_rows = [r for r in rows if r.get("layer") == "risk"]
    risk_action_counts = Counter(r.get("action", "") for r in risk_rows)
    risk_reason_counts = Counter((r.get("reason") or "").strip() for r in risk_rows if (r.get("reason") or "").strip())
    approved_sim_count = risk_action_counts.get("APPROVED_SIMULATION", 0)
    blocked_count = risk_action_counts.get("BLOCKED", 0)

    execution_rows = [r for r in rows if r.get("layer") == "execution"]
    execution_action_counts = Counter(r.get("action", "") for r in execution_rows)

    position_rows = [r for r in rows if r.get("layer") == "position"]
    position_action_counts = Counter(r.get("action", "") for r in position_rows)
    open_positions = set()
    unique_position_ids = set()
    for row in position_rows:
        pid = (row.get("entity_id") or "").strip()
        action = row.get("action", "")
        if not pid:
            continue
        unique_position_ids.add(pid)
        if action == "OPENED":
            open_positions.add(pid)
        elif action == "CLOSED" and pid in open_positions:
            open_positions.remove(pid)

    spread_values = [
        parse_float(r.get("spread_pct", ""))
        for r in rows
        if r.get("spread_pct", "") != ""
    ]
    spread_values = [v for v in spread_values if v is not None]
    avg_spread_pct = round(sum(spread_values) / len(spread_values), 10) if spread_values else None

    acceptance_hints = {
        "has_rows": total_rows > 0,
        "has_all_layers": all(layer_counts.get(layer, 0) > 0 for layer in ["feature", "strategy", "risk", "execution", "position"]),
        "timestamps_parseable": len(valid_timestamps) == total_rows,
        "timestamps_ordered": rows == sorted(rows, key=lambda row: row.get("event_time_utc", "")),
        "has_strategy_and_risk_flow": candidate_count > 0 and len(risk_rows) > 0,
        "has_position_activity": len(position_rows) > 0 and position_action_counts.get("OPENED", 0) > 0,
        "open_position_count_reasonable": len(open_positions) <= 1,
    }

    return {
        "path": str(path),
        "total_rows": total_rows,
        "layer_counts": dict(layer_counts),
        "first_timestamp": first_ts.isoformat() if first_ts else None,
        "last_timestamp": last_ts.isoformat() if last_ts else None,
        "timespan_seconds": span_seconds,
        "events_per_minute": events_per_min,
        "strategy_action_counts": dict(strategy_action_counts),
        "risk_action_counts": dict(risk_action_counts),
        "risk_reason_counts": dict(risk_reason_counts),
        "execution_action_counts": dict(execution_action_counts),
        "position_action_counts": dict(position_action_counts),
        "unique_positions": len(unique_position_ids),
        "currently_open_positions": len(open_positions),
        "funnel_metrics": {
            "strategy_candidate_rows": candidate_count,
            "strategy_no_trade_rows": no_trade_count,
            "risk_approved_rows": approved_sim_count,
            "risk_blocked_rows": blocked_count,
            "execution_simulated_rows": execution_action_counts.get("SIMULATED_ORDER_PREPARED", 0),
            "execution_skipped_rows": execution_action_counts.get("SKIPPED", 0),
            "candidate_to_approved_ratio": ratio(approved_sim_count, candidate_count),
            "approved_to_execution_sim_ratio": ratio(execution_action_counts.get("SIMULATED_ORDER_PREPARED", 0), approved_sim_count),
        },
        "avg_spread_pct": avg_spread_pct,
        "acceptance_hints": acceptance_hints,
    }


def print_human(summary: dict) -> None:
    print("=== Normalized Event Analytics Summary ===")
    print(f"File: {summary['path']}")
    print(f"Rows: {summary['total_rows']}")
    print(f"First timestamp: {summary['first_timestamp']}")
    print(f"Last timestamp:  {summary['last_timestamp']}")
    print(f"Timespan (sec):  {summary['timespan_seconds']}")
    print(f"Events/minute:   {summary['events_per_minute']}")
    print(f"Avg spread pct:  {summary['avg_spread_pct']}")
    print()

    print("Layer counts")
    for layer in ["feature", "strategy", "risk", "execution", "position"]:
        print(f"- {layer}: {summary['layer_counts'].get(layer, 0)}")
    print()

    print("Strategy actions")
    if not summary["strategy_action_counts"]:
        print("- none")
    else:
        for action, count in sorted(summary["strategy_action_counts"].items(), key=lambda kv: kv[1], reverse=True):
            print(f"- {action or 'EMPTY'}: {count}")
    print()

    print("Risk actions")
    if not summary["risk_action_counts"]:
        print("- none")
    else:
        for action, count in sorted(summary["risk_action_counts"].items(), key=lambda kv: kv[1], reverse=True):
            print(f"- {action or 'EMPTY'}: {count}")
    print()

    print("Top risk reasons")
    reasons = summary["risk_reason_counts"]
    if not reasons:
        print("- none")
    else:
        for reason, count in sorted(reasons.items(), key=lambda kv: kv[1], reverse=True)[:10]:
            print(f"- {reason}: {count}")
    print()

    print("Execution actions")
    if not summary["execution_action_counts"]:
        print("- none")
    else:
        for action, count in sorted(summary["execution_action_counts"].items(), key=lambda kv: kv[1], reverse=True):
            print(f"- {action or 'EMPTY'}: {count}")
    print()

    print("Position lifecycle")
    if not summary["position_action_counts"]:
        print("- none")
    else:
        for action, count in sorted(summary["position_action_counts"].items(), key=lambda kv: kv[1], reverse=True):
            print(f"- {action or 'EMPTY'}: {count}")
    print(f"- unique_positions: {summary['unique_positions']}")
    print(f"- currently_open_positions: {summary['currently_open_positions']}")
    print()

    print("Funnel metrics")
    for key, value in summary["funnel_metrics"].items():
        print(f"- {key}: {value}")
    print()

    print("Acceptance hints")
    for key, value in summary["acceptance_hints"].items():
        print(f"- {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize normalized pipeline events for Stage 8 analytics.")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="Path to normalized events CSV")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"Normalized event file not found: {path}")

    summary = summarize(path)
    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print_human(summary)


if __name__ == "__main__":
    main()