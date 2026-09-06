import argparse
import csv
import json
import re
from pathlib import Path
from datetime import datetime


DATA_DIR = Path("data")

DEFAULT_SOURCES = {
    "feature": DATA_DIR / "features_btc_eur.csv",
    "strategy": DATA_DIR / "strategy_decisions_btc_eur.csv",
    "risk": DATA_DIR / "risk_decisions_btc_eur.csv",
    "execution": DATA_DIR / "execution_simulation_btc_eur.csv",
    "position": DATA_DIR / "positions_simulation_btc_eur.csv",
}

OUTPUT_PATH = DATA_DIR / "normalized_events.csv"

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
MARKET_RE = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+$")

NORMALIZED_HEADERS = [
    "event_time_utc",
    "layer",
    "event_type",
    "market",
    "entity_id",
    "status",
    "action",
    "reason",
    "signal_strength",
    "spread_pct",
    "tick_interval_ms",
    "valid_flag",
    "source_file",
    "source_row_number",
    "payload_json",
]


def parse_float(raw: str) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def as_text(value) -> str:
    if value is None:
        return ""
    return str(value)


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def is_valid_timestamp(raw: str) -> bool:
    if not raw:
        return False
    if not TIMESTAMP_RE.match(raw):
        return False
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def is_valid_market(raw: str) -> bool:
    if not raw:
        return False
    return bool(MARKET_RE.match(raw))


def is_valid_core_row(row: dict) -> bool:
    return is_valid_timestamp(row.get("timestamp_utc", "")) and is_valid_market(row.get("market", ""))


def normalize_feature(rows: list[dict], source_name: str) -> tuple[list[dict], int]:
    events = []
    skipped = 0
    for idx, row in enumerate(rows, start=2):
        if not is_valid_core_row(row):
            skipped += 1
            continue

        payload = {
            "bid": row.get("bid"),
            "ask": row.get("ask"),
            "last": row.get("last"),
            "spread_abs": row.get("spread_abs"),
            "mid_price": row.get("mid_price"),
            "micro_return_1": row.get("micro_return_1"),
            "micro_return_5": row.get("micro_return_5"),
            "spread_change_1": row.get("spread_change_1"),
            "spread_change_5": row.get("spread_change_5"),
        }
        events.append(
            {
                "event_time_utc": row.get("timestamp_utc", ""),
                "layer": "feature",
                "event_type": "feature_snapshot",
                "market": row.get("market", ""),
                "entity_id": "",
                "status": "VALID" if row.get("is_valid") == "True" else "INVALID",
                "action": "FEATURE_COMPUTED",
                "reason": row.get("validation_errors", ""),
                "signal_strength": "",
                "spread_pct": as_text(parse_float(row.get("spread_pct", ""))),
                "tick_interval_ms": as_text(parse_float(row.get("tick_interval_ms", ""))),
                "valid_flag": row.get("is_valid", ""),
                "source_file": source_name,
                "source_row_number": str(idx),
                "payload_json": json.dumps(payload, ensure_ascii=True),
            }
        )
    return events, skipped


def normalize_strategy(rows: list[dict], source_name: str) -> tuple[list[dict], int]:
    events = []
    skipped = 0
    for idx, row in enumerate(rows, start=2):
        if not is_valid_core_row(row):
            skipped += 1
            continue

        payload = {
            "micro_return_1": row.get("micro_return_1"),
            "micro_return_5": row.get("micro_return_5"),
        }
        events.append(
            {
                "event_time_utc": row.get("timestamp_utc", ""),
                "layer": "strategy",
                "event_type": "strategy_decision",
                "market": row.get("market", ""),
                "entity_id": "",
                "status": "DECIDED",
                "action": row.get("action", ""),
                "reason": row.get("reason", ""),
                "signal_strength": as_text(parse_float(row.get("signal_strength", ""))),
                "spread_pct": as_text(parse_float(row.get("spread_pct", ""))),
                "tick_interval_ms": as_text(parse_float(row.get("tick_interval_ms", ""))),
                "valid_flag": "",
                "source_file": source_name,
                "source_row_number": str(idx),
                "payload_json": json.dumps(payload, ensure_ascii=True),
            }
        )
    return events, skipped


def normalize_risk(rows: list[dict], source_name: str) -> tuple[list[dict], int]:
    events = []
    skipped = 0
    for idx, row in enumerate(rows, start=2):
        if not is_valid_core_row(row):
            skipped += 1
            continue

        payload = {
            "strategy_action": row.get("strategy_action"),
            "candidates_last_minute": row.get("candidates_last_minute"),
        }
        events.append(
            {
                "event_time_utc": row.get("timestamp_utc", ""),
                "layer": "risk",
                "event_type": "risk_decision",
                "market": row.get("market", ""),
                "entity_id": "",
                "status": "APPROVED" if row.get("approved") == "True" else "REJECTED",
                "action": row.get("risk_action", ""),
                "reason": row.get("reason", ""),
                "signal_strength": as_text(parse_float(row.get("signal_strength", ""))),
                "spread_pct": as_text(parse_float(row.get("spread_pct", ""))),
                "tick_interval_ms": as_text(parse_float(row.get("tick_interval_ms", ""))),
                "valid_flag": row.get("approved", ""),
                "source_file": source_name,
                "source_row_number": str(idx),
                "payload_json": json.dumps(payload, ensure_ascii=True),
            }
        )
    return events, skipped


def normalize_execution(rows: list[dict], source_name: str) -> tuple[list[dict], int]:
    events = []
    skipped = 0
    for idx, row in enumerate(rows, start=2):
        if not is_valid_core_row(row):
            skipped += 1
            continue

        payload = {
            "strategy_action": row.get("strategy_action"),
            "risk_action": row.get("risk_action"),
        }
        events.append(
            {
                "event_time_utc": row.get("timestamp_utc", ""),
                "layer": "execution",
                "event_type": "execution_event",
                "market": row.get("market", ""),
                "entity_id": "",
                "status": "SIMULATION",
                "action": row.get("execution_action", ""),
                "reason": row.get("reason", ""),
                "signal_strength": as_text(parse_float(row.get("signal_strength", ""))),
                "spread_pct": as_text(parse_float(row.get("spread_pct", ""))),
                "tick_interval_ms": "",
                "valid_flag": "",
                "source_file": source_name,
                "source_row_number": str(idx),
                "payload_json": json.dumps(payload, ensure_ascii=True),
            }
        )
    return events, skipped


def normalize_position(rows: list[dict], source_name: str) -> tuple[list[dict], int]:
    events = []
    skipped = 0
    for idx, row in enumerate(rows, start=2):
        if not is_valid_core_row(row):
            skipped += 1
            continue

        payload = {
            "entry_time_utc": row.get("entry_time_utc"),
            "close_time_utc": row.get("close_time_utc"),
            "entry_reason": row.get("entry_reason"),
            "exit_reason": row.get("exit_reason"),
            "entry_signal_strength": row.get("entry_signal_strength"),
            "exit_signal_strength": row.get("exit_signal_strength"),
        }
        events.append(
            {
                "event_time_utc": row.get("timestamp_utc", ""),
                "layer": "position",
                "event_type": "position_lifecycle",
                "market": row.get("market", ""),
                "entity_id": row.get("position_id", ""),
                "status": row.get("status", ""),
                "action": row.get("lifecycle_action", ""),
                "reason": row.get("exit_reason", "") or row.get("entry_reason", ""),
                "signal_strength": as_text(parse_float(row.get("entry_signal_strength", ""))),
                "spread_pct": as_text(parse_float(row.get("entry_spread_pct", ""))),
                "tick_interval_ms": "",
                "valid_flag": "",
                "source_file": source_name,
                "source_row_number": str(idx),
                "payload_json": json.dumps(payload, ensure_ascii=True),
            }
        )
    return events, skipped


def normalize_all(source_paths: dict[str, Path]) -> tuple[list[dict], dict[str, int]]:
    normalized = []
    skipped_counts = {}

    feature_events, feature_skipped = normalize_feature(load_rows(source_paths["feature"]), source_paths["feature"].name)
    strategy_events, strategy_skipped = normalize_strategy(load_rows(source_paths["strategy"]), source_paths["strategy"].name)
    risk_events, risk_skipped = normalize_risk(load_rows(source_paths["risk"]), source_paths["risk"].name)
    execution_events, execution_skipped = normalize_execution(load_rows(source_paths["execution"]), source_paths["execution"].name)
    position_events, position_skipped = normalize_position(load_rows(source_paths["position"]), source_paths["position"].name)

    normalized.extend(feature_events)
    normalized.extend(strategy_events)
    normalized.extend(risk_events)
    normalized.extend(execution_events)
    normalized.extend(position_events)

    skipped_counts["feature"] = feature_skipped
    skipped_counts["strategy"] = strategy_skipped
    skipped_counts["risk"] = risk_skipped
    skipped_counts["execution"] = execution_skipped
    skipped_counts["position"] = position_skipped

    normalized.sort(key=lambda row: row.get("event_time_utc", ""))
    return normalized, skipped_counts


def write_normalized(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=NORMALIZED_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict], output_path: Path, skipped_counts: dict[str, int]) -> None:
    layer_counts = {}
    for row in rows:
        layer = row.get("layer", "unknown")
        layer_counts[layer] = layer_counts.get(layer, 0) + 1

    print("=== Normalization Summary ===")
    print(f"Output: {output_path}")
    print(f"Total normalized rows: {len(rows)}")
    print("Rows by layer:")
    for layer in ["feature", "strategy", "risk", "execution", "position"]:
        print(f"- {layer}: {layer_counts.get(layer, 0)}")
    print("Skipped malformed rows:")
    for layer in ["feature", "strategy", "risk", "execution", "position"]:
        print(f"- {layer}: {skipped_counts.get(layer, 0)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize pipeline CSV outputs into one unified event table.")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Path for normalized CSV output")
    args = parser.parse_args()

    source_paths = {name: path for name, path in DEFAULT_SOURCES.items()}
    normalized_rows, skipped_counts = normalize_all(source_paths)

    output_path = Path(args.output)
    write_normalized(normalized_rows, output_path)
    print_summary(normalized_rows, output_path, skipped_counts)


if __name__ == "__main__":
    main()
