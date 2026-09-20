from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any

STRATEGY_MAX_SPREAD_PCT = 0.02
STRATEGY_MAX_TICK_INTERVAL_MS = 2000.0
STRATEGY_MIN_MOMENTUM_RETURN = 0.0
HORIZONS_SECONDS = [1, 2, 5, 10, 30, 60, 120, 300]
FEE_RATE = 0.001
SPREAD_PCT_REFERENCE = 0.001
SLIPPAGE_BPS = 10.0


def parse_event_time(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def relative_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def classify_forward_behavior(mfe_pct: float | None, mae_pct: float | None, spread_delta: float | None) -> str:
    if mfe_pct is None and mae_pct is None:
        return "insufficient observations"
    if mfe_pct is not None and mae_pct is not None:
        if mfe_pct > 0.0 and mae_pct < 0.0:
            return "favorable movement followed by reversal"
        if mfe_pct > 0.0 and abs(mfe_pct) >= 0.005:
            return "favorable continuation"
        if mae_pct < 0.0 and abs(mae_pct) >= 0.005:
            return "immediate adverse movement"
    if spread_delta is not None and abs(spread_delta) > 0.0005:
        return "spread deterioration"
    if mfe_pct is not None and mae_pct is not None and abs(mfe_pct) < 0.0005 and abs(mae_pct) < 0.0005:
        return "sideways / low movement"
    if mfe_pct is not None and mae_pct is not None and mfe_pct <= 0.0 and mae_pct >= 0.0:
        return "momentum decay"
    return "insufficient observations"


def load_events(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def build_feature_series(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    mid_history: deque[float] = deque(maxlen=6)
    last_tick_timestamp: datetime | None = None

    for event in events:
        if event.get("event_type") != "ticker":
            continue
        bid = safe_float(event.get("bid"))
        ask = safe_float(event.get("ask"))
        last = safe_float(event.get("last"))
        event_time = parse_event_time(event.get("event_time_utc"))
        if bid is None or ask is None or last is None or event_time is None:
            continue

        spread_abs = ask - bid
        mid_price = (bid + ask) / 2.0
        spread_pct = (spread_abs / bid) if bid not in (None, 0.0) else None

        tick_interval_ms = None
        if last_tick_timestamp is not None:
            tick_interval_ms = (event_time - last_tick_timestamp).total_seconds() * 1000.0

        micro_return_1 = relative_change(mid_price, mid_history[-1] if len(mid_history) >= 1 else None)
        micro_return_5 = relative_change(mid_price, mid_history[-5] if len(mid_history) >= 5 else None)
        momentum_score = None
        if micro_return_1 is not None and micro_return_5 is not None:
            momentum_score = (0.7 * micro_return_1) + (0.3 * micro_return_5)

        series.append(
            {
                "event_index": len(series),
                "event_time_utc": event["event_time_utc"],
                "event_time_dt": event_time,
                "bid": bid,
                "ask": ask,
                "last": last,
                "mid": mid_price,
                "spread_abs": spread_abs,
                "spread_pct": spread_pct,
                "tick_interval_ms": tick_interval_ms,
                "micro_return_1": micro_return_1,
                "micro_return_5": micro_return_5,
                "momentum_score": momentum_score,
            }
        )

        if mid_price is not None:
            mid_history.append(mid_price)
        last_tick_timestamp = event_time

    return series


def build_entry_observations(feature_series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for row in feature_series:
        if (
            row["spread_pct"] is not None
            and row["tick_interval_ms"] is not None
            and row["micro_return_1"] is not None
            and row["micro_return_5"] is not None
            and row["momentum_score"] is not None
            and row["spread_pct"] <= STRATEGY_MAX_SPREAD_PCT
            and row["tick_interval_ms"] <= STRATEGY_MAX_TICK_INTERVAL_MS
            and row["momentum_score"] >= STRATEGY_MIN_MOMENTUM_RETURN
        ):
            entries.append(
                {
                    "event_index": row["event_index"],
                    "event_time_utc": row["event_time_utc"],
                    "event_time_dt": row["event_time_dt"],
                    "bid": row["bid"],
                    "ask": row["ask"],
                    "last": row["last"],
                    "mid": row["mid"],
                    "spread_abs": row["spread_abs"],
                    "spread_pct": row["spread_pct"],
                    "tick_interval_ms": row["tick_interval_ms"],
                    "micro_return_1": row["micro_return_1"],
                    "micro_return_5": row["micro_return_5"],
                    "momentum_score": row["momentum_score"],
                }
            )
    return entries


def compute_forward_horizon(entry: dict[str, Any], feature_series: list[dict[str, Any]], horizon_seconds: int) -> dict[str, Any]:
    window: list[dict[str, Any]] = []
    entry_ts = entry["event_time_dt"]
    end_ts = entry_ts + timedelta(seconds=horizon_seconds)
    for row in feature_series:
        if row["event_time_dt"] < entry_ts:
            continue
        if row["event_time_dt"] > end_ts:
            continue
        if row["event_time_utc"] == entry["event_time_utc"]:
            continue
        window.append(row)

    if not window:
        return {
            "horizon_seconds": horizon_seconds,
            "status": "unavailable",
            "mfe_abs": None,
            "mfe_pct": None,
            "mae_abs": None,
            "mae_pct": None,
            "time_to_mfe": None,
            "time_to_mae": None,
            "mean_momentum_score": None,
            "median_momentum_score": None,
            "positive_fraction": None,
            "negative_fraction": None,
            "spread_change_abs_mean": None,
            "spread_change_abs_median": None,
            "tick_interval_ms_mean": None,
            "tick_interval_ms_median": None,
            "classification": "insufficient observations",
        }

    entry_mid = entry["mid"]
    deltas = [row["mid"] - entry_mid for row in window]
    max_delta = max(deltas, default=0.0)
    min_delta = min(deltas, default=0.0)
    mfe_abs = max_delta if max_delta > 0 else 0.0
    mae_abs = min_delta if min_delta < 0 else 0.0
    mfe_pct = mfe_abs / entry_mid if entry_mid != 0 else None
    mae_pct = mae_abs / entry_mid if entry_mid != 0 else None

    time_to_mfe = None
    time_to_mae = None
    if mfe_abs > 0:
        for row in window:
            if row["mid"] - entry_mid == mfe_abs:
                time_to_mfe = (row["event_time_dt"] - entry_ts).total_seconds()
                break
    if mae_abs < 0:
        for row in window:
            if row["mid"] - entry_mid == mae_abs:
                time_to_mae = (row["event_time_dt"] - entry_ts).total_seconds()
                break

    momentum_values = [row["momentum_score"] for row in window if row["momentum_score"] is not None]
    spread_values = [row["spread_pct"] for row in window if row["spread_pct"] is not None]
    tick_values = []
    for idx in range(1, len(window)):
        prev = window[idx - 1]
        curr = window[idx]
        tick_values.append((curr["event_time_dt"] - prev["event_time_dt"]).total_seconds() * 1000.0)

    momentum_mean = mean(momentum_values)
    momentum_median = median(momentum_values) if momentum_values else None
    positive_fraction = sum(1 for value in momentum_values if value > 0.0) / len(momentum_values)
    negative_fraction = sum(1 for value in momentum_values if value < 0.0) / len(momentum_values)
    spread_changes = [value - entry["spread_pct"] for value in spread_values]
    classification = classify_forward_behavior(mfe_pct, mae_pct, spread_changes[-1] if spread_changes else None)

    return {
        "horizon_seconds": horizon_seconds,
        "status": "ok",
        "mfe_abs": mfe_abs,
        "mfe_pct": mfe_pct,
        "mae_abs": mae_abs,
        "mae_pct": mae_pct,
        "time_to_mfe": time_to_mfe,
        "time_to_mae": time_to_mae,
        "mean_momentum_score": momentum_mean,
        "median_momentum_score": momentum_median,
        "positive_fraction": positive_fraction,
        "negative_fraction": negative_fraction,
        "spread_change_abs_mean": mean([abs(value) for value in spread_changes]) if spread_changes else None,
        "spread_change_abs_median": median([abs(value) for value in spread_changes]) if spread_changes else None,
        "tick_interval_ms_mean": mean(tick_values) if tick_values else None,
        "tick_interval_ms_median": median(tick_values) if tick_values else None,
        "classification": classification,
    }


def compute_cost_reference() -> dict[str, Any]:
    fee_cost_pct = 2 * FEE_RATE
    spread_cost_pct = SPREAD_PCT_REFERENCE
    slippage_cost_pct = SLIPPAGE_BPS / 10000.0
    round_trip_cost_pct = fee_cost_pct + spread_cost_pct + slippage_cost_pct
    return {
        "fee_rate": FEE_RATE,
        "spread_pct": SPREAD_PCT_REFERENCE,
        "slippage_bps": SLIPPAGE_BPS,
        "round_trip_cost_pct": round_trip_cost_pct,
        "round_trip_cost_basis": "entry fee + exit fee + spread + slippage; not a trading recommendation",
        "explicit_statement": "No exit strategy or TP/SL parameters were selected.",
    }


def summarize_horizons(entry_summary: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for horizon in HORIZONS_SECONDS:
        rows = [row for row in entry_summary if row["horizon_seconds"] == horizon]
        mfe_values = [row["mfe_pct"] for row in rows if row["mfe_pct"] is not None]
        mae_values = [row["mae_pct"] for row in rows if row["mae_pct"] is not None]
        time_to_mfe = [row["time_to_mfe"] for row in rows if row["time_to_mfe"] is not None]
        time_to_mae = [row["time_to_mae"] for row in rows if row["time_to_mae"] is not None]
        summary[str(horizon)] = {
            "observations": len(rows),
            "mfe_pct_mean": mean(mfe_values),
            "mfe_pct_median": median(mfe_values) if mfe_values else None,
            "mfe_pct_max": max(mfe_values) if mfe_values else None,
            "mae_pct_mean": mean(mae_values),
            "mae_pct_median": median(mae_values) if mae_values else None,
            "mae_pct_min": min(mae_values) if mae_values else None,
            "time_to_mfe_mean": mean(time_to_mfe) if time_to_mfe else None,
            "time_to_mae_mean": mean(time_to_mae) if time_to_mae else None,
            "classification_counts": {
                key: sum(1 for row in rows if row["classification"] == key)
                for key in sorted({row["classification"] for row in rows})
            },
        }
    return summary


def normalize_for_json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): normalize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_for_json(item) for item in value]
    return value


def generate_report(dataset_path: Path) -> dict[str, Any]:
    raw_events = load_events(dataset_path)
    feature_series = build_feature_series(raw_events)
    entries = build_entry_observations(feature_series)

    entry_records: list[dict[str, Any]] = []
    horizon_summary: list[dict[str, Any]] = []
    for entry in entries:
        record = {
            "event_index": entry["event_index"],
            "event_time_utc": entry["event_time_utc"],
            "bid": entry["bid"],
            "ask": entry["ask"],
            "last": entry["last"],
            "mid": entry["mid"],
            "spread_abs": entry["spread_abs"],
            "spread_pct": entry["spread_pct"],
            "tick_interval_ms": entry["tick_interval_ms"],
            "micro_return_1": entry["micro_return_1"],
            "micro_return_5": entry["micro_return_5"],
            "momentum_score": entry["momentum_score"],
            "horizons": {},
        }
        for horizon in HORIZONS_SECONDS:
            metrics = compute_forward_horizon(entry, feature_series, horizon)
            record["horizons"][str(horizon)] = metrics
            horizon_summary.append({
                "event_index": entry["event_index"],
                "entry_time_utc": entry["event_time_utc"],
                "horizon_seconds": horizon,
                **metrics,
            })
        entry_records.append(record)

    report = {
        "dataset_identity": str(dataset_path),
        "event_count": len(raw_events),
        "independent_entry_observation_count": len(entry_records),
        "entry_condition_definition": {
            "strategy_logic": "ENTRY_LONG when micro_return_1 and micro_return_5 are available, spread_pct <= 0.02, tick_interval_ms <= 2000.0, and momentum_score >= 0.0.",
            "mid_price_formula": "(bid + ask) / 2.0",
            "spread_abs_formula": "ask - bid",
            "spread_pct_formula": "(ask - bid) / bid",
            "micro_return_1_formula": "(mid_t - mid_{t-1}) / mid_{t-1}",
            "micro_return_5_formula": "(mid_t - mid_{t-5}) / mid_{t-5}",
            "momentum_score_formula": "0.7 * micro_return_1 + 0.3 * micro_return_5",
            "selection_rule": "Every qualifying canonical event is treated as an independent entry observation. This is not a simulated position lifecycle, and later events are not suppressed because an earlier analytical observation is still open.",
        },
        "backtest_reconciliation": {
            "backtest_strategy_decisions": 17261,
            "backtest_risk_approved": 28,
            "backtest_execution_events": 28,
            "backtest_closed_trades": 0,
            "difference_explained_by_code": [
                "The backtest pipeline is stateful and serializes a single live/open position at a time.",
                "StrategyEngine.evaluate() only emits ENTRY_LONG when the normalized position_state says the position is flat.",
                "This Stage 2 analysis intentionally ignores the live one-position lifecycle and evaluates the current entry gate at each historical event independently.",
                "As a result, the entry count is not expected to match the 28 executed backtest trades; it is specifically a trigger-qualification analysis, not a trade-execution simulation.",
            ],
        },
        "entry_observations": entry_records,
        "horizon_summary": summarize_horizons(horizon_summary),
        "cost_reference": compute_cost_reference(),
    }
    return normalize_for_json(report)


def write_report(report: dict[str, Any], output_md: Path, output_json: Path) -> None:
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Entry-Centric Historical Behavior Analysis",
        "",
        f"- Dataset identity: {report['dataset_identity']}",
        f"- Event count: {report['event_count']}",
        f"- Number of independent entry observations: {report['independent_entry_observation_count']}",
        "",
        "## 1. Entry condition definition",
        "- Current StrategyEngine entry gate: micro_return_1 and micro_return_5 available, spread_pct <= 0.02, tick_interval_ms <= 2000.0, momentum_score >= 0.0.",
        "- This analysis treats every qualifying canonical event as an independent historical probe, without applying the simulated one-position lifecycle.",
        "",
        "## 2. Reconciliation with BacktestEngine",
        f"- Previous backtest evidence: strategy decisions = {report['backtest_reconciliation']['backtest_strategy_decisions']}, risk approved = {report['backtest_reconciliation']['backtest_risk_approved']}, execution events = {report['backtest_reconciliation']['backtest_execution_events']}, closed trades = {report['backtest_reconciliation']['backtest_closed_trades']}.",
        "- The difference is expected because the backtest is stateful and serializes one active position, while this Stage 2 analysis is entry-centric and independent per event.",
        "- The code path in StrategyEngine is intentionally position-aware; this analysis removes that stateful suppression to measure historical trigger frequency at each qualifying event.",
        "",
        "## 3. Cost reference",
        f"- fee_rate = {report['cost_reference']['fee_rate']}",
        f"- spread_pct = {report['cost_reference']['spread_pct']}",
        f"- slippage_bps = {report['cost_reference']['slippage_bps']}",
        f"- approximate round-trip cost = {report['cost_reference']['round_trip_cost_pct']}",
        "- This is not a TP recommendation; it only shows the movement required to offset modeled execution costs under the existing assumptions.",
        "",
        "## 4. Horizon summary",
    ]
    summary = report["horizon_summary"]
    for horizon in HORIZONS_SECONDS:
        row = summary.get(str(horizon), {})
        lines.append(f"### {horizon}s")
        lines.append(f"- observations: {row.get('observations')}")
        lines.append(f"- mean MFE pct: {row.get('mfe_pct_mean')}")
        lines.append(f"- median MFE pct: {row.get('mfe_pct_median')}")
        lines.append(f"- mean MAE pct: {row.get('mae_pct_mean')}")
        lines.append(f"- median MAE pct: {row.get('mae_pct_median')}")
        lines.append(f"- mean time-to-MFE (s): {row.get('time_to_mfe_mean')}")
        lines.append(f"- mean time-to-MAE (s): {row.get('time_to_mae_mean')}")
        lines.append("")

    lines.append("No exit strategy or TP/SL parameters were selected.")
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Entry-centric historical behavior analysis.")
    parser.add_argument("--dataset", default="data/canonical/tardis_btc_eur_20191201/canonical_events.jsonl")
    parser.add_argument("--md", default="reports/exit_behavior_analysis_20191201.md")
    parser.add_argument("--json", default="reports/exit_behavior_analysis_20191201.json")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    md_path = Path(args.md)
    json_path = Path(args.json)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    report = generate_report(dataset_path)
    write_report(report, md_path, json_path)

    digest = hashlib.sha256(json.dumps(report, indent=2, sort_keys=True).encode("utf-8")).hexdigest()
    print(json.dumps({
        "dataset": str(dataset_path),
        "independent_entry_observation_count": report["independent_entry_observation_count"],
        "report_sha256": digest,
        "first_entry_utc": report["entry_observations"][0]["event_time_utc"] if report["entry_observations"] else None,
        "last_entry_utc": report["entry_observations"][-1]["event_time_utc"] if report["entry_observations"] else None,
    }, indent=2))


if __name__ == "__main__":
    main()
