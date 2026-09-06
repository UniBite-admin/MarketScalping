import argparse
import json
import re
from pathlib import Path


LOG_PATH = Path("logs") / "market_data.log"


def summarize_log(log_text: str) -> dict:
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]

    counts = {
        "total_lines": len(lines),
        "connecting": 0,
        "connected": 0,
        "subscription_sent": 0,
        "subscription_confirmed": 0,
        "receiving_ticker": 0,
        "stale_data": 0,
        "data_fresh_again": 0,
        "socket_error": 0,
        "socket_closed_unexpectedly": 0,
        "reconnect_attempt": 0,
        "json_error": 0,
        "ticker_parse_error": 0,
        "trade_parse_error": 0,
        "api_error": 0,
        "shutdown_requested": 0,
    }

    first_timestamp = None
    last_timestamp = None

    ts_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})")

    for line in lines:
        ts_match = ts_pattern.match(line)
        if ts_match:
            if first_timestamp is None:
                first_timestamp = ts_match.group(1)
            last_timestamp = ts_match.group(1)

        if "state=connecting" in line:
            counts["connecting"] += 1
        if "state=connected" in line:
            counts["connected"] += 1
        if "state=subscription_sent" in line:
            counts["subscription_sent"] += 1
        if "subscription_confirmed" in line:
            counts["subscription_confirmed"] += 1
        if "state=receiving_ticker" in line:
            counts["receiving_ticker"] += 1
        if "stale_data_detected" in line or "state=stale_data" in line:
            counts["stale_data"] += 1
        if "data_fresh_again" in line:
            counts["data_fresh_again"] += 1
        if "socket_error" in line:
            counts["socket_error"] += 1
        if "socket_closed_unexpectedly" in line:
            counts["socket_closed_unexpectedly"] += 1
        if "reconnect_attempt" in line:
            counts["reconnect_attempt"] += 1
        if "json_error" in line:
            counts["json_error"] += 1
        if "ticker_parse_error" in line:
            counts["ticker_parse_error"] += 1
        if "trade_parse_error" in line:
            counts["trade_parse_error"] += 1
        if "api_error" in line:
            counts["api_error"] += 1
        if "shutdown_requested" in line:
            counts["shutdown_requested"] += 1

    acceptance_hints = {
        "has_subscription_confirmation": counts["subscription_confirmed"] > 0,
        "has_connection": counts["connected"] > 0,
        "has_disconnects": counts["socket_closed_unexpectedly"] > 0,
        "has_stale_detection": counts["stale_data"] > 0,
        "stale_recovered": counts["data_fresh_again"] >= 1 if counts["stale_data"] > 0 else True,
        "parse_errors_present": (counts["json_error"] + counts["ticker_parse_error"] + counts["trade_parse_error"]) > 0,
    }

    return {
        "log_path": str(LOG_PATH),
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "counts": counts,
        "acceptance_hints": acceptance_hints,
    }


def print_human(summary: dict) -> None:
    counts = summary["counts"]
    hints = summary["acceptance_hints"]

    print("=== Market Data Log Summary ===")
    print(f"Log file: {summary['log_path']}")
    print(f"First event: {summary['first_timestamp']}")
    print(f"Last event:  {summary['last_timestamp']}")
    print()
    print("Lifecycle")
    print(f"- connecting: {counts['connecting']}")
    print(f"- connected: {counts['connected']}")
    print(f"- subscription_sent: {counts['subscription_sent']}")
    print(f"- subscription_confirmed: {counts['subscription_confirmed']}")
    print()
    print("Resilience")
    print(f"- socket_error: {counts['socket_error']}")
    print(f"- socket_closed_unexpectedly: {counts['socket_closed_unexpectedly']}")
    print(f"- reconnect_attempt: {counts['reconnect_attempt']}")
    print(f"- stale_data: {counts['stale_data']}")
    print(f"- data_fresh_again: {counts['data_fresh_again']}")
    print()
    print("Data Quality")
    print(f"- json_error: {counts['json_error']}")
    print(f"- ticker_parse_error: {counts['ticker_parse_error']}")
    print(f"- trade_parse_error: {counts['trade_parse_error']}")
    print(f"- api_error: {counts['api_error']}")
    print()
    print("Acceptance Hints")
    print(f"- has_subscription_confirmation: {hints['has_subscription_confirmation']}")
    print(f"- has_connection: {hints['has_connection']}")
    print(f"- has_disconnects: {hints['has_disconnects']}")
    print(f"- has_stale_detection: {hints['has_stale_detection']}")
    print(f"- stale_recovered: {hints['stale_recovered']}")
    print(f"- parse_errors_present: {hints['parse_errors_present']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize MarketScalping market_data.log evidence metrics.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary instead of human-readable output")
    args = parser.parse_args()

    if not LOG_PATH.exists():
        raise SystemExit(f"Log file not found: {LOG_PATH}")

    log_text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
    summary = summarize_log(log_text)

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print_human(summary)


if __name__ == "__main__":
    main()