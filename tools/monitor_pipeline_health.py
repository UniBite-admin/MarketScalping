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


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def analyze(rows: list[dict], stale_tick_ms_max: float, min_candidate_ratio: float, min_approval_ratio: float, max_execution_skip_ratio: float, max_no_candidate_streak: int) -> dict:
    alerts = []

    total_rows = len(rows)
    layer_counts = Counter(row.get("layer", "") for row in rows)

    timestamps = [parse_iso(row.get("event_time_utc", "")) for row in rows]
    valid_ts = [ts for ts in timestamps if ts is not None]
    first_ts = min(valid_ts) if valid_ts else None
    last_ts = max(valid_ts) if valid_ts else None

    feature_rows = [r for r in rows if r.get("layer") == "feature"]
    feature_tick_values = []
    for row in feature_rows:
        raw = row.get("tick_interval_ms", "")
        if raw == "":
            continue
        try:
            feature_tick_values.append(float(raw))
        except ValueError:
            continue

    max_tick_ms = max(feature_tick_values) if feature_tick_values else None
    avg_tick_ms = sum(feature_tick_values) / len(feature_tick_values) if feature_tick_values else None
    if max_tick_ms is not None and max_tick_ms > stale_tick_ms_max:
        alerts.append(
            {
                "severity": "WARN",
                "code": "STALE_FEED_SPIKE",
                "message": f"Feature tick interval spike detected: max_tick_ms={max_tick_ms:.3f} > threshold={stale_tick_ms_max:.3f}",
            }
        )

    strategy_rows = [r for r in rows if r.get("layer") == "strategy"]
    strategy_actions = Counter(r.get("action", "") for r in strategy_rows)
    strategy_candidates = strategy_actions.get("CANDIDATE_TRADE", 0)
    strategy_no_trade = strategy_actions.get("NO_TRADE", 0)
    strategy_total = len(strategy_rows)
    candidate_ratio = ratio(strategy_candidates, strategy_total)
    if strategy_total > 0 and candidate_ratio < min_candidate_ratio:
        alerts.append(
            {
                "severity": "WARN",
                "code": "CANDIDATE_DROUGHT",
                "message": f"Candidate ratio low: {candidate_ratio:.6f} < threshold={min_candidate_ratio:.6f}",
            }
        )

    max_no_candidate_run = 0
    current_run = 0
    for row in strategy_rows:
        if row.get("action") == "NO_TRADE":
            current_run += 1
            max_no_candidate_run = max(max_no_candidate_run, current_run)
        else:
            current_run = 0

    if max_no_candidate_run > max_no_candidate_streak:
        alerts.append(
            {
                "severity": "WARN",
                "code": "NO_CANDIDATE_STREAK",
                "message": f"Longest NO_TRADE streak too high: {max_no_candidate_run} > threshold={max_no_candidate_streak}",
            }
        )

    risk_rows = [r for r in rows if r.get("layer") == "risk"]
    risk_actions = Counter(r.get("action", "") for r in risk_rows)
    risk_approved = risk_actions.get("APPROVED_SIMULATION", 0)
    risk_blocked = risk_actions.get("BLOCKED", 0)
    risk_no_action = risk_actions.get("NO_ACTION", 0)
    approval_ratio = ratio(risk_approved, strategy_candidates)
    if strategy_candidates > 0 and approval_ratio < min_approval_ratio:
        alerts.append(
            {
                "severity": "WARN",
                "code": "APPROVAL_RATIO_DROP",
                "message": f"Risk approval ratio low: {approval_ratio:.6f} < threshold={min_approval_ratio:.6f}",
            }
        )

    execution_rows = [r for r in rows if r.get("layer") == "execution"]
    execution_actions = Counter(r.get("action", "") for r in execution_rows)
    execution_sim = execution_actions.get("SIMULATED_ORDER_PREPARED", 0)
    execution_skip = execution_actions.get("SKIPPED", 0)
    execution_total = execution_sim + execution_skip
    execution_skip_ratio = ratio(execution_skip, execution_total)
    if execution_total > 0 and execution_skip_ratio > max_execution_skip_ratio:
        alerts.append(
            {
                "severity": "WARN",
                "code": "EXECUTION_SKIP_SPIKE",
                "message": f"Execution skip ratio high: {execution_skip_ratio:.6f} > threshold={max_execution_skip_ratio:.6f}",
            }
        )

    risk_reasons = Counter((r.get("reason") or "").strip() for r in risk_rows if (r.get("reason") or "").strip())

    health_status = "HEALTHY" if not alerts else "DEGRADED"

    return {
        "health_status": health_status,
        "total_rows": total_rows,
        "window_start": first_ts.isoformat() if first_ts else None,
        "window_end": last_ts.isoformat() if last_ts else None,
        "layer_counts": dict(layer_counts),
        "strategy": {
            "total": strategy_total,
            "candidate": strategy_candidates,
            "no_trade": strategy_no_trade,
            "candidate_ratio": round(candidate_ratio, 6),
            "max_no_trade_streak": max_no_candidate_run,
        },
        "risk": {
            "total": len(risk_rows),
            "approved": risk_approved,
            "blocked": risk_blocked,
            "no_action": risk_no_action,
            "approval_ratio_vs_candidates": round(approval_ratio, 6),
            "top_reasons": dict(sorted(risk_reasons.items(), key=lambda kv: kv[1], reverse=True)[:10]),
        },
        "execution": {
            "total": len(execution_rows),
            "simulated": execution_sim,
            "skipped": execution_skip,
            "skip_ratio": round(execution_skip_ratio, 6),
        },
        "market_data": {
            "feature_rows": len(feature_rows),
            "avg_tick_interval_ms": round(avg_tick_ms, 3) if avg_tick_ms is not None else None,
            "max_tick_interval_ms": round(max_tick_ms, 3) if max_tick_ms is not None else None,
        },
        "thresholds": {
            "stale_tick_ms_max": stale_tick_ms_max,
            "min_candidate_ratio": min_candidate_ratio,
            "min_approval_ratio": min_approval_ratio,
            "max_execution_skip_ratio": max_execution_skip_ratio,
            "max_no_candidate_streak": max_no_candidate_streak,
        },
        "alerts": alerts,
    }


def print_human(result: dict) -> None:
    print("=== Pipeline Health Monitor ===")
    print(f"Health status: {result['health_status']}")
    print(f"Rows: {result['total_rows']}")
    print(f"Window start: {result['window_start']}")
    print(f"Window end:   {result['window_end']}")
    print()

    print("Layer counts")
    for layer in ["feature", "strategy", "risk", "execution", "position"]:
        print(f"- {layer}: {result['layer_counts'].get(layer, 0)}")
    print()

    print("Market data health")
    md = result["market_data"]
    print(f"- avg_tick_interval_ms: {md['avg_tick_interval_ms']}")
    print(f"- max_tick_interval_ms: {md['max_tick_interval_ms']}")
    print()

    print("Strategy health")
    st = result["strategy"]
    print(f"- total: {st['total']}")
    print(f"- candidate: {st['candidate']}")
    print(f"- no_trade: {st['no_trade']}")
    print(f"- candidate_ratio: {st['candidate_ratio']}")
    print(f"- max_no_trade_streak: {st['max_no_trade_streak']}")
    print()

    print("Risk health")
    rk = result["risk"]
    print(f"- total: {rk['total']}")
    print(f"- approved: {rk['approved']}")
    print(f"- blocked: {rk['blocked']}")
    print(f"- no_action: {rk['no_action']}")
    print(f"- approval_ratio_vs_candidates: {rk['approval_ratio_vs_candidates']}")
    print("- top_reasons:")
    if not rk["top_reasons"]:
        print("  - none")
    else:
        for reason, count in rk["top_reasons"].items():
            print(f"  - {reason}: {count}")
    print()

    print("Execution health")
    ex = result["execution"]
    print(f"- total: {ex['total']}")
    print(f"- simulated: {ex['simulated']}")
    print(f"- skipped: {ex['skipped']}")
    print(f"- skip_ratio: {ex['skip_ratio']}")
    print()

    print("Alerts")
    if not result["alerts"]:
        print("- none")
    else:
        for alert in result["alerts"]:
            print(f"- [{alert['severity']}] {alert['code']}: {alert['message']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor normalized simulation pipeline health and emit threshold alerts.")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="Path to normalized events CSV")
    parser.add_argument("--stale-tick-ms-max", type=float, default=5000.0, help="Warn if max feature tick interval exceeds this")
    parser.add_argument("--min-candidate-ratio", type=float, default=0.05, help="Warn if strategy candidate ratio falls below this")
    parser.add_argument("--min-approval-ratio", type=float, default=0.05, help="Warn if risk approvals / strategy candidates falls below this")
    parser.add_argument("--max-execution-skip-ratio", type=float, default=0.50, help="Warn if execution skipped ratio exceeds this")
    parser.add_argument("--max-no-candidate-streak", type=int, default=200, help="Warn if NO_TRADE streak exceeds this")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"Normalized file not found: {path}")

    rows = read_rows(path)
    result = analyze(
        rows=rows,
        stale_tick_ms_max=args.stale_tick_ms_max,
        min_candidate_ratio=args.min_candidate_ratio,
        min_approval_ratio=args.min_approval_ratio,
        max_execution_skip_ratio=args.max_execution_skip_ratio,
        max_no_candidate_streak=args.max_no_candidate_streak,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print_human(result)


if __name__ == "__main__":
    main()