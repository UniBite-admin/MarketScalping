import argparse
import csv
import json
import math
from pathlib import Path


DEFAULT_FEATURE_PATH = Path("data") / "features_btc_eur.csv"

NUMERIC_FIELDS = [
    "bid",
    "ask",
    "last",
    "spread_abs",
    "spread_pct",
    "mid_price",
    "micro_return_1",
    "micro_return_5",
    "spread_change_1",
    "spread_change_5",
    "tick_interval_ms",
]


def parse_float(value: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def stddev(values: list[float], avg: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - avg) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def compute_outliers(values: list[float], z_threshold: float = 5.0) -> int:
    if len(values) < 3:
        return 0

    avg = mean(values)
    sd = stddev(values, avg)
    if sd == 0:
        return 0

    return sum(1 for v in values if abs((v - avg) / sd) > z_threshold)


def summarize(path: Path) -> dict:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    total_rows = len(rows)
    valid_rows = sum(1 for row in rows if row.get("is_valid") == "True")
    invalid_rows = total_rows - valid_rows

    validation_error_counts = {}
    for row in rows:
        err = (row.get("validation_errors") or "").strip()
        if not err:
            continue
        validation_error_counts[err] = validation_error_counts.get(err, 0) + 1

    numeric_summary = {}
    for field_name in NUMERIC_FIELDS:
        values = [parse_float(row.get(field_name, "")) for row in rows]
        present_values = [v for v in values if v is not None]
        missing_count = total_rows - len(present_values)

        if not present_values:
            numeric_summary[field_name] = {
                "present": 0,
                "missing": missing_count,
                "missing_ratio": 1.0 if total_rows else 0.0,
                "min": None,
                "max": None,
                "mean": None,
                "stddev": None,
                "outliers_z_gt_5": 0,
            }
            continue

        avg = mean(present_values)
        sd = stddev(present_values, avg)
        numeric_summary[field_name] = {
            "present": len(present_values),
            "missing": missing_count,
            "missing_ratio": round((missing_count / total_rows), 6) if total_rows else 0.0,
            "min": min(present_values),
            "max": max(present_values),
            "mean": avg,
            "stddev": sd,
            "outliers_z_gt_5": compute_outliers(present_values),
        }

    first_timestamp = rows[0]["timestamp_utc"] if rows else None
    last_timestamp = rows[-1]["timestamp_utc"] if rows else None

    return {
        "path": str(path),
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "valid_ratio": round((valid_rows / total_rows), 6) if total_rows else 0.0,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "validation_error_counts": validation_error_counts,
        "numeric_summary": numeric_summary,
    }


def print_human(summary: dict) -> None:
    print("=== Feature Quality Summary ===")
    print(f"File: {summary['path']}")
    print(f"Rows: {summary['total_rows']} | Valid: {summary['valid_rows']} | Invalid: {summary['invalid_rows']}")
    print(f"Valid ratio: {summary['valid_ratio']:.4f}")
    print(f"First timestamp: {summary['first_timestamp']}")
    print(f"Last timestamp:  {summary['last_timestamp']}")
    print()

    print("Validation errors")
    if not summary["validation_error_counts"]:
        print("- none")
    else:
        for key, count in sorted(summary["validation_error_counts"].items(), key=lambda item: item[0]):
            print(f"- {key}: {count}")
    print()

    print("Field coverage and stats")
    for field_name in NUMERIC_FIELDS:
        field = summary["numeric_summary"][field_name]
        print(
            f"- {field_name}: present={field['present']}, missing={field['missing']}, "
            f"missing_ratio={field['missing_ratio']}, outliers_z_gt_5={field['outliers_z_gt_5']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize feature quality for MarketScalping CSV output.")
    parser.add_argument("--path", default=str(DEFAULT_FEATURE_PATH), help="Path to feature CSV file")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    csv_path = Path(args.path)
    if not csv_path.exists():
        raise SystemExit(f"Feature file not found: {csv_path}")

    summary = summarize(csv_path)
    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print_human(summary)


if __name__ == "__main__":
    main()