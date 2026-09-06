import argparse
import csv
import json
from collections import Counter, defaultdict
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


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def filter_rows(rows: list[dict], day: str | None, layer: str | None) -> list[dict]:
    filtered = rows
    if day:
        filtered = [r for r in filtered if (r.get("event_time_utc", "").startswith(day))]
    if layer:
        filtered = [r for r in filtered if r.get("layer") == layer]
    return filtered


def report_rollup(rows: list[dict]) -> dict:
    by_day = Counter()
    by_layer = Counter()
    by_layer_action = Counter()

    for row in rows:
        ts = row.get("event_time_utc", "")
        day = ts[:10] if len(ts) >= 10 else "unknown"
        layer = row.get("layer", "")
        action = row.get("action", "")

        by_day[day] += 1
        by_layer[layer] += 1
        by_layer_action[(layer, action)] += 1

    return {
        "total_rows": len(rows),
        "rows_by_day": dict(sorted(by_day.items())),
        "rows_by_layer": dict(by_layer),
        "rows_by_layer_action": [
            {"layer": layer, "action": action, "count": count}
            for (layer, action), count in sorted(by_layer_action.items(), key=lambda kv: kv[1], reverse=True)
        ],
    }


def report_reasons(rows: list[dict], top: int = 10) -> dict:
    risk_rows = [r for r in rows if r.get("layer") == "risk"]
    reason_counts = Counter((r.get("reason") or "").strip() for r in risk_rows if (r.get("reason") or "").strip())
    top_reasons = sorted(reason_counts.items(), key=lambda kv: kv[1], reverse=True)[:top]

    return {
        "risk_rows": len(risk_rows),
        "distinct_reasons": len(reason_counts),
        "top_reasons": [{"reason": reason, "count": count} for reason, count in top_reasons],
    }


def _count(rows: list[dict], layer: str, action: str) -> int:
    return sum(1 for r in rows if r.get("layer") == layer and r.get("action") == action)


def report_funnel(rows: list[dict]) -> dict:
    strategy_candidates = _count(rows, "strategy", "CANDIDATE_TRADE")
    strategy_no_trade = _count(rows, "strategy", "NO_TRADE")
    risk_approved = _count(rows, "risk", "APPROVED_SIMULATION")
    risk_blocked = _count(rows, "risk", "BLOCKED")
    risk_no_action = _count(rows, "risk", "NO_ACTION")
    execution_sim = _count(rows, "execution", "SIMULATED_ORDER_PREPARED")
    execution_skip = _count(rows, "execution", "SKIPPED")

    return {
        "strategy_candidate_rows": strategy_candidates,
        "strategy_no_trade_rows": strategy_no_trade,
        "risk_approved_rows": risk_approved,
        "risk_blocked_rows": risk_blocked,
        "risk_no_action_rows": risk_no_action,
        "execution_simulated_rows": execution_sim,
        "execution_skipped_rows": execution_skip,
        "candidate_to_approved_ratio": round((risk_approved / strategy_candidates), 6) if strategy_candidates else 0.0,
        "approved_to_execution_sim_ratio": round((execution_sim / risk_approved), 6) if risk_approved else 0.0,
    }


def report_positions(rows: list[dict]) -> dict:
    position_rows = [r for r in rows if r.get("layer") == "position"]

    position_state: dict[str, dict] = defaultdict(
        lambda: {
            "market": "",
            "opened_at": None,
            "closed_at": None,
            "hold_events": 0,
            "open_spread_pct": None,
            "close_spread_pct": None,
            "status": "",
        }
    )

    for row in position_rows:
        pid = (row.get("entity_id") or "").strip()
        if not pid:
            continue

        ts = parse_iso(row.get("event_time_utc", ""))
        action = row.get("action", "")
        state = position_state[pid]
        state["market"] = row.get("market", "")
        state["status"] = row.get("status", "")

        if action == "OPENED":
            state["opened_at"] = ts
            state["open_spread_pct"] = parse_float(row.get("spread_pct", ""))
        elif action == "HOLD":
            state["hold_events"] += 1
        elif action == "CLOSED":
            state["closed_at"] = ts
            state["close_spread_pct"] = parse_float(row.get("spread_pct", ""))

    items = []
    for pid, state in sorted(position_state.items()):
        opened_at = state["opened_at"]
        closed_at = state["closed_at"]
        duration_sec = None
        if opened_at and closed_at:
            duration_sec = round((closed_at - opened_at).total_seconds(), 3)

        items.append(
            {
                "position_id": pid,
                "market": state["market"],
                "status": state["status"],
                "opened_at": opened_at.isoformat() if opened_at else None,
                "closed_at": closed_at.isoformat() if closed_at else None,
                "hold_events": state["hold_events"],
                "duration_sec": duration_sec,
                "open_spread_pct": state["open_spread_pct"],
                "close_spread_pct": state["close_spread_pct"],
            }
        )

    return {
        "position_rows": len(position_rows),
        "position_count": len(items),
        "open_positions": sum(1 for p in items if p["closed_at"] is None),
        "closed_positions": sum(1 for p in items if p["closed_at"] is not None),
        "positions": items,
    }


def print_text(report_type: str, result: dict) -> None:
    if report_type == "rollup":
        print("=== Query Report: Rollup ===")
        print(f"Total rows: {result['total_rows']}")
        print("Rows by day")
        for day, count in result["rows_by_day"].items():
            print(f"- {day}: {count}")
        print("Rows by layer")
        for layer, count in result["rows_by_layer"].items():
            print(f"- {layer or 'EMPTY'}: {count}")
        print("Top layer/action pairs")
        for item in result["rows_by_layer_action"][:12]:
            print(f"- {item['layer']}/{item['action'] or 'EMPTY'}: {item['count']}")
        return

    if report_type == "reasons":
        print("=== Query Report: Risk Reasons ===")
        print(f"Risk rows: {result['risk_rows']}")
        print(f"Distinct reasons: {result['distinct_reasons']}")
        if not result["top_reasons"]:
            print("- no reasons")
            return
        print("Top reasons")
        for item in result["top_reasons"]:
            print(f"- {item['reason']}: {item['count']}")
        return

    if report_type == "funnel":
        print("=== Query Report: Funnel ===")
        for key, value in result.items():
            print(f"- {key}: {value}")
        return

    if report_type == "positions":
        print("=== Query Report: Position Timeline ===")
        print(f"Position rows: {result['position_rows']}")
        print(f"Position count: {result['position_count']}")
        print(f"Open positions: {result['open_positions']}")
        print(f"Closed positions: {result['closed_positions']}")
        if not result["positions"]:
            print("- no position entities")
            return
        print("Positions")
        for pos in result["positions"]:
            print(
                "- "
                f"{pos['position_id']} market={pos['market']} status={pos['status']} "
                f"opened_at={pos['opened_at']} closed_at={pos['closed_at']} "
                f"hold_events={pos['hold_events']} duration_sec={pos['duration_sec']}"
            )
        return

    raise SystemExit(f"Unsupported report type: {report_type}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query and report over normalized market simulation events.")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="Path to normalized events CSV")
    parser.add_argument("--report", choices=["rollup", "reasons", "funnel", "positions"], required=True)
    parser.add_argument("--day", default=None, help="Optional day filter in YYYY-MM-DD")
    parser.add_argument("--layer", default=None, help="Optional layer filter")
    parser.add_argument("--top", type=int, default=10, help="Top N reasons for reasons report")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"Normalized file not found: {path}")

    rows = read_rows(path)
    rows = filter_rows(rows, day=args.day, layer=args.layer)

    if args.report == "rollup":
        result = report_rollup(rows)
    elif args.report == "reasons":
        result = report_reasons(rows, top=args.top)
    elif args.report == "funnel":
        result = report_funnel(rows)
    else:
        result = report_positions(rows)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print_text(args.report, result)


if __name__ == "__main__":
    main()