from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CANONICAL_ROOT = Path("data/canonical")
TIMEFRAME_MINUTES = 15
UTC = timezone.utc


def parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)


def canonical_price(rec: dict[str, Any]) -> float | None:
    last = rec.get("last")
    if last not in (None, ""):
        try:
            return float(last)
        except (TypeError, ValueError):
            return None
    bid = rec.get("bid")
    ask = rec.get("ask")
    if bid not in (None, "") and ask not in (None, ""):
        try:
            return (float(bid) + float(ask)) / 2.0
        except (TypeError, ValueError):
            return None
    return None


def bucket_start(ts: datetime) -> datetime:
    minute_bucket = (ts.minute // TIMEFRAME_MINUTES) * TIMEFRAME_MINUTES
    return ts.replace(minute=minute_bucket, second=0, microsecond=0)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return ordered[lo]
    fraction = rank - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * fraction


def median(values: list[float]) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 0:
        return (ordered[mid - 1] + ordered[mid]) / 2.0
    return ordered[mid]


def build_reconstructed_bars() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    files = sorted(CANONICAL_ROOT.glob("**/canonical_events.jsonl"))
    if not files:
        raise SystemExit("No canonical_events.jsonl files found under data/canonical")

    events: list[dict[str, Any]] = []
    for fp in files:
        with fp.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = parse_ts(rec["event_time_utc"])
                price = canonical_price(rec)
                if price is None:
                    continue
                events.append({
                    "event_time_utc": ts,
                    "price": price,
                    "source": str(fp),
                    "line_no": line_no,
                })

    if not events:
        raise SystemExit("No valid price-bearing canonical events found")

    events.sort(key=lambda e: (e["event_time_utc"], e["source"], e["line_no"]))
    first_ts = events[0]["event_time_utc"]
    last_ts = events[-1]["event_time_utc"]
    start_bucket = bucket_start(first_ts)
    end_bucket = bucket_start(last_ts)
    total_range = end_bucket - start_bucket
    total_bin_count = int(total_range.total_seconds() // (TIMEFRAME_MINUTES * 60)) + 1

    bars_by_bucket: dict[datetime, list[float]] = {}
    for event in events:
        bucket = bucket_start(event["event_time_utc"])
        bars_by_bucket.setdefault(bucket, []).append(event["price"])

    bucket_list = [start_bucket + timedelta(minutes=TIMEFRAME_MINUTES * i) for i in range(total_bin_count)]
    reconstructed_bars: list[dict[str, Any]] = []
    for idx, bucket in enumerate(bucket_list):
        values = bars_by_bucket.get(bucket, [])
        if not values:
            continue
        open_price = values[0]
        high_price = max(values)
        low_price = min(values)
        close_price = values[-1]
        reconstructed_bars.append({
            "index": idx,
            "bucket_start_utc": bucket,
            "bucket_end_utc": bucket + timedelta(minutes=TIMEFRAME_MINUTES),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
        })

    highs: list[dict[str, Any]] = []
    lows: list[dict[str, Any]] = []
    for idx in range(1, len(reconstructed_bars) - 1):
        bar = reconstructed_bars[idx]
        prev_bar = reconstructed_bars[idx - 1]
        next_bar = reconstructed_bars[idx + 1]
        if bar["high"] > prev_bar["high"] and bar["high"] > next_bar["high"]:
            highs.append({"time": bar["bucket_start_utc"], "price": bar["high"], "index": idx})
        if bar["low"] < prev_bar["low"] and bar["low"] < next_bar["low"]:
            lows.append({"time": bar["bucket_start_utc"], "price": bar["low"], "index": idx})

    return reconstructed_bars, highs, lows


def compute_true_range(high: float, low: float, prev_close: float | None) -> float:
    if prev_close is None:
        return high - low
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr_series(bars: list[dict[str, Any]], window: int = 14) -> list[float]:
    if len(bars) < 2:
        return [0.0] * len(bars)
    tr_values = []
    for idx in range(len(bars)):
        prev_close = bars[idx - 1]["close"] if idx > 0 else bars[0]["open"]
        tr_values.append(compute_true_range(bars[idx]["high"], bars[idx]["low"], prev_close))

    atr = [0.0] * len(bars)
    first_atr = sum(tr_values[1:window + 1]) / window if len(tr_values) >= window + 1 else sum(tr_values[1:]) / max(1, len(tr_values) - 1)
    atr[min(window, len(bars) - 1)] = first_atr
    for idx in range(window + 1, len(bars)):
        atr[idx] = ((window - 1) * atr[idx - 1] + tr_values[idx]) / window
    return atr


def cluster_swings(swings: list[dict[str, Any]], tolerance_value: float) -> list[list[dict[str, Any]]]:
    if not swings:
        return []
    clusters: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [swings[0]]

    for s in swings[1:]:
        last = current[-1]
        if abs(s["price"] - last["price"]) <= tolerance_value:
            current.append(s)
        else:
            clusters.append(current)
            current = [s]

    if current:
        clusters.append(current)
    return clusters


def mixed_cluster_swings(swings: list[dict[str, Any]], a_value: float, r_value: float) -> list[list[dict[str, Any]]]:
    if not swings:
        return []
    clusters: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [swings[0]]
    for s in swings[1:]:
        last = current[-1]
        ref_price = float(last["price"])
        tol = max(a_value, r_value * abs(ref_price))
        if abs(s["price"] - last["price"]) <= tol:
            current.append(s)
        else:
            clusters.append(current)
            current = [s]
    if current:
        clusters.append(current)
    return clusters


def summarize_clusters(clusters: list[list[dict[str, Any]]], total_swings: int) -> dict[str, Any]:
    if not clusters:
        return {
            "cluster_count": 0,
            "singleton_count": 0,
            "singleton_pct": 0.0,
            "avg_members": 0.0,
            "median_members": 0.0,
            "max_members": 0,
            "multi_member_swings": 0,
            "multi_member_pct": 0.0,
            "member_size_distribution": {},
            "largest_cluster_span": 0.0,
            "largest_cluster_range_price": 0.0,
        }

    sizes = [len(c) for c in clusters]
    singleton_count = sum(1 for s in sizes if s == 1)
    multi_member_swings = sum(len(c) for c in clusters if len(c) >= 2)
    price_spans = []
    for c in clusters:
        values = [s["price"] for s in c]
        price_spans.append(max(values) - min(values))
    clusters_sorted = sorted(clusters, key=lambda c: len(c), reverse=True)
    largest = clusters_sorted[0]
    largest_span = max(s["price"] for s in largest) - min(s["price"] for s in largest)
    member_dist = {}
    for size in sizes:
        member_dist[size] = member_dist.get(size, 0) + 1

    return {
        "cluster_count": len(clusters),
        "singleton_count": singleton_count,
        "singleton_pct": singleton_count / total_swings if total_swings else 0.0,
        "avg_members": sum(sizes) / len(sizes),
        "median_members": median(sizes),
        "max_members": max(sizes),
        "multi_member_swings": multi_member_swings,
        "multi_member_pct": multi_member_swings / total_swings if total_swings else 0.0,
        "member_size_distribution": {str(k): v for k, v in sorted(member_dist.items())},
        "largest_cluster_span": largest_span,
        "largest_cluster_range_price": max(price_spans) if price_spans else 0.0,
    }


def family_results(bars: list[dict[str, Any]], swings: list[dict[str, Any]], name: str, candidates: list[float], mode: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    atr_values = atr_series(bars)
    for candidate in candidates:
        clusters = []
        for direction in ("high", "low"):
            pass

        if mode == "fixed_abs":
            clusters = cluster_swings(swings, candidate)
        elif mode == "fixed_rel":
            explicit = []
            current = []
            for s in swings:
                if not current:
                    current = [s]
                    continue
                ref = current[-1]["price"]
                if abs(s["price"] - current[-1]["price"]) <= abs(candidate * ref):
                    current.append(s)
                else:
                    explicit.append(current)
                    current = [s]
            if current:
                explicit.append(current)
            clusters = explicit
        elif mode == "mixed":
            abs_floor, rel_fraction = candidate
            explicit = []
            current = []
            for s in swings:
                if not current:
                    current = [s]
                    continue
                ref = current[-1]["price"]
                tol = max(abs_floor, rel_fraction * abs(ref))
                if abs(s["price"] - current[-1]["price"]) <= tol:
                    current.append(s)
                else:
                    explicit.append(current)
                    current = [s]
            if current:
                explicit.append(current)
            clusters = explicit
        elif mode == "atr":
            explicit = []
            current = []
            for s in swings:
                if not current:
                    current = [s]
                    continue
                last_idx = current[-1]["index"]
                atr_value = atr_values[last_idx]
                tol = candidate * atr_value
                if abs(s["price"] - current[-1]["price"]) <= tol:
                    current.append(s)
                else:
                    explicit.append(current)
                    current = [s]
            if current:
                explicit.append(current)
            clusters = explicit
        else:
            raise ValueError(f"Unknown mode: {mode}")

        summary = summarize_clusters(clusters, len(swings))
        out.append({
            "family": name,
            "candidate": candidate,
            "mode": mode,
            "eligible_swings": len(swings),
            "cluster_count": summary["cluster_count"],
            "singleton_count": summary["singleton_count"],
            "singleton_pct": round(summary["singleton_pct"], 6),
            "avg_members": round(summary["avg_members"], 4),
            "median_members": round(summary["median_members"], 4),
            "max_members": summary["max_members"],
            "multi_member_pct": round(summary["multi_member_pct"], 6),
            "largest_cluster_span": round(summary["largest_cluster_span"], 4),
            "largest_cluster_range_price": round(summary["largest_cluster_range_price"], 4),
            "member_size_distribution": summary["member_size_distribution"],
        })
    return out


def mixed_surface(swings: list[dict[str, Any]], a_values: list[float], r_values: list[float]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for a_value in a_values:
        for r_value in r_values:
            clusters = mixed_cluster_swings(swings, a_value, r_value)
            summary = summarize_clusters(clusters, len(swings))
            result.append({
                "A": a_value,
                "r": r_value,
                "cluster_count": summary["cluster_count"],
                "singleton_count": summary["singleton_count"],
                "singleton_pct": round(summary["singleton_pct"], 6),
                "multi_member_pct": round(summary["multi_member_pct"], 6),
                "avg_members": round(summary["avg_members"], 4),
                "median_members": round(summary["median_members"], 4),
                "max_members": summary["max_members"],
                "member_size_distribution": summary["member_size_distribution"],
                "largest_cluster_span": round(summary["largest_cluster_span"], 4),
                "largest_cluster_range_price": round(summary["largest_cluster_range_price"], 4),
            })
    return result


def main() -> None:
    bars, highs, lows = build_reconstructed_bars()

    absolute_candidates = [1, 2, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 500]
    relative_candidates = [1e-6, 2e-6, 5e-6, 1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3]
    mixed_candidates = [
        (2, 2e-6), (2, 5e-6), (2, 1e-5), (5, 5e-6), (5, 1e-5), (10, 2e-5),
        (10, 5e-5), (20, 1e-4), (20, 2e-4), (50, 1e-4), (50, 2e-4), (100, 5e-4)
    ]
    atr_candidates = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]
    a_surface = [5, 10, 15, 20, 30, 40, 50, 60, 75, 100, 150]
    r_surface = [0.5e-4, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3]

    sweep = {
        "dataset": {
            "canonical_files": [str(p) for p in sorted(CANONICAL_ROOT.glob("**/canonical_events.jsonl"))],
            "event_count": sum(1 for fp in sorted(CANONICAL_ROOT.glob("**/canonical_events.jsonl")) for _ in open(fp, "r", encoding="utf-8")),
            "reconstructed_bar_count": len(bars),
            "eligible_high_swings": len(highs),
            "eligible_low_swings": len(lows),
            "ethics": "research-only; no profit optimization; no implementation",
            "timeframe_minutes": TIMEFRAME_MINUTES,
        },
        "group_a_frozen": {
            "swing_high_rule": "High[i] > High[i-1] AND High[i] > High[i+1]",
            "swing_low_rule": "Low[i] < Low[i-1] AND Low[i] < Low[i+1]",
            "causal_requirement": "confirmed in order; created_at is second qualifying swing; no backdating",
        },
        "families": {
            "fixed_absolute": family_results(bars, highs, "fixed_absolute_highs", absolute_candidates, "fixed_abs"),
            "fixed_relative": family_results(bars, highs, "fixed_relative_highs", relative_candidates, "fixed_rel"),
            "mixed_relative_absolute": family_results(bars, highs, "mixed_relative_absolute_highs", mixed_candidates, "mixed"),
            "atr_alt": family_results(bars, highs, "atr_alt_highs", atr_candidates, "atr"),
        },
        "low_direction": {
            "fixed_absolute": family_results(bars, lows, "fixed_absolute_lows", absolute_candidates, "fixed_abs"),
            "fixed_relative": family_results(bars, lows, "fixed_relative_lows", relative_candidates, "fixed_rel"),
            "mixed_relative_absolute": family_results(bars, lows, "mixed_relative_absolute_lows", mixed_candidates, "mixed"),
            "atr_alt": family_results(bars, lows, "atr_alt_lows", atr_candidates, "atr"),
        },
        "mixed_family_surface_highs": mixed_surface(highs, a_surface, r_surface),
        "mixed_family_surface_lows": mixed_surface(lows, a_surface, r_surface),
        "mixed_family_surface_combined": mixed_surface(highs + lows, a_surface, r_surface),
    }

    print(json.dumps(sweep, indent=2, default=str))


if __name__ == "__main__":
    main()
