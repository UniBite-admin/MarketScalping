from __future__ import annotations

import argparse
import hashlib
import json
import time
from itertools import islice
from pathlib import Path
from typing import Iterable

from backtest_engine import BacktestConfig, BacktestEngine
from binance_trade_adapter import (
    audit_binance_trade_zip,
    canonicalize_binance_trade_zip,
    read_binance_checksum_file,
    verify_binance_archive_checksum,
)
from replay_runner import ReplayRunner, iter_replay_events_jsonl


DEFAULT_RAW_ZIP_PATH = Path("data") / "raw" / "binance_public" / "BTCUSDT-trades-2024-01.zip"
DEFAULT_CANONICAL_PATH = Path("data") / "canonical" / "binance_public" / "BTCUSDT-trades-2024-01-canonical.jsonl"
DEFAULT_AUDIT_PATH = Path("data") / "canonical" / "binance_public" / "BTCUSDT-trades-2024-01.audit.json"
DEFAULT_MANIFEST_PATH = Path("data") / "canonical" / "binance_public" / "BTCUSDT-trades-2024-01.manifest.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _resolve_checksum(zip_path: Path, *, checksum_path: Path | None, expected_hash: str | None) -> dict:
    resolved_expected = (expected_hash or "").strip().lower()
    if not resolved_expected and checksum_path is not None:
        resolved_expected = read_binance_checksum_file(checksum_path)

    actual_hash = _sha256_file(zip_path)
    if not resolved_expected:
        return {
            "status": "SKIPPED",
            "expected_sha256": None,
            "actual_sha256": actual_hash,
            "matched": None,
            "checksum_path": str(checksum_path) if checksum_path is not None else None,
        }

    return {
        "status": "VERIFIED" if verify_binance_archive_checksum(zip_path, resolved_expected) else "MISMATCH",
        "expected_sha256": resolved_expected,
        "actual_sha256": actual_hash,
        "matched": actual_hash.lower() == resolved_expected,
        "checksum_path": str(checksum_path) if checksum_path is not None else None,
    }


def _determinism_snapshot(report: dict) -> dict:
    return {
        "replay": {
            "events_total": report["replay"]["events_total"],
            "events_processed": report["replay"]["events_processed"],
            "events_rejected": report["replay"]["events_rejected"],
            "dataset_status": report["replay"]["dataset_status"],
            "canonicalization_result": report["replay"]["canonicalization_result"],
            "closed_trade_count": report["replay"]["closed_trade_count"],
            "final_account_balance": report["replay"]["final_account_balance"],
            "final_equity": report["replay"]["final_equity"],
            "realized_pnl": report["replay"]["realized_pnl"],
        },
        "backtest": {
            "run_id": report["backtest"]["run_id"],
            "dataset_id": report["backtest"]["dataset_id"],
            "validation_status": report["backtest"]["validation_status"],
            "replay_status": report["backtest"]["replay_status"],
            "event_start_utc": report["backtest"]["event_start_utc"],
            "event_end_utc": report["backtest"]["event_end_utc"],
            "final_cash": report["backtest"]["final_cash"],
            "final_position_quantity": report["backtest"]["final_position_quantity"],
            "final_equity": report["backtest"]["final_equity"],
            "realized_pnl": report["backtest"]["realized_pnl"],
            "metrics": report["backtest"]["metrics"],
            "trade_record_count": report["backtest"]["trade_record_count"],
            "equity_curve_points": report["backtest"]["equity_curve_points"],
        },
    }


def _determinism_report(first: dict, second: dict) -> dict:
    first_snapshot = _determinism_snapshot(first)
    second_snapshot = _determinism_snapshot(second)
    return {
        "requested": True,
        "matches": first_snapshot == second_snapshot,
        "backtest_run_id_match": first_snapshot["backtest"]["run_id"] == second_snapshot["backtest"]["run_id"],
        "backtest_dataset_id_match": first_snapshot["backtest"]["dataset_id"] == second_snapshot["backtest"]["dataset_id"],
        "snapshot_first": first_snapshot,
        "snapshot_second": second_snapshot,
    }


def _limited_events(path: Path, limit: int | None) -> Iterable[dict]:
    events = iter_replay_events_jsonl(path)
    if limit is None:
        return events
    return islice(events, limit)


def _backtest_summary(result) -> dict:
    return {
        "run_id": result.run_id,
        "dataset_id": result.dataset_id,
        "validation_status": result.validation_status,
        "replay_status": result.replay_status,
        "event_start_utc": result.event_start_utc,
        "event_end_utc": result.event_end_utc,
        "final_cash": result.final_cash,
        "final_position_quantity": result.final_position_quantity,
        "final_equity": result.final_equity,
        "realized_pnl": result.realized_pnl,
        "metrics": result.metrics,
        "warnings": result.warnings,
        "limitations": result.limitations,
        "replay_rejection_reasons": list(result.replay_rejection_reasons),
        "trade_record_count": len(result.trade_records),
        "equity_curve_points": len(result.equity_curve),
    }


def build_report(path: Path, *, limit: int | None, initial_capital: float) -> dict:
    replay_started = time.perf_counter()
    replay_result = ReplayRunner(
        market="BTC-USDT",
        position_max_hold_events=2,
        accounting_starting_balance=initial_capital,
    ).replay(
        _limited_events(path, limit),
        assume_canonical_chronological=True,
        summary_mode=True,
    )
    replay_elapsed = time.perf_counter() - replay_started

    backtest_started = time.perf_counter()
    backtest_result = BacktestEngine(
        BacktestConfig(
            market="BTC-USDT",
            initial_capital=initial_capital,
        )
    ).run(
        _limited_events(path, limit),
        summary_mode=True,
        assume_canonical_chronological=True,
    )
    backtest_elapsed = time.perf_counter() - backtest_started

    return {
        "archive": {
            "path": str(path),
            "file_size_bytes": path.stat().st_size,
            "limit": limit,
        },
        "manifest": {
            "source": "binance_public_canonical_jsonl",
            "market": "BTC-USDT",
            "assume_canonical_chronological": True,
            "summary_mode": True,
        },
        "replay": {
            "elapsed_seconds": round(replay_elapsed, 3),
            "events_total": replay_result.events_total,
            "events_processed": replay_result.events_processed,
            "events_rejected": replay_result.events_rejected,
            "dataset_status": replay_result.dataset_status,
            "canonicalization_result": replay_result.canonicalization_result,
            "rejection_reasons": list(replay_result.rejection_reasons),
            "strategy_decisions": replay_result.strategy_decisions,
            "risk_decisions": replay_result.risk_decisions,
            "execution_events": replay_result.execution_events,
            "position_events": replay_result.position_events,
            "closed_trade_count": replay_result.closed_trade_count,
            "final_account_balance": replay_result.final_account_balance,
            "final_equity": replay_result.final_equity,
            "realized_pnl": replay_result.realized_pnl,
        },
        "backtest": {
            "elapsed_seconds": round(backtest_elapsed, 3),
            **_backtest_summary(backtest_result),
        },
    }


def build_end_to_end_report(
    zip_path: Path,
    *,
    canonical_path: Path,
    audit_path: Path,
    manifest_path: Path,
    limit: int | None,
    initial_capital: float,
    market: str = "BTC-USDT",
    checksum_path: Path | None = None,
    expected_hash: str | None = None,
    repeat_check: bool = False,
) -> dict:
    checksum = _resolve_checksum(zip_path, checksum_path=checksum_path, expected_hash=expected_hash)
    audit = audit_binance_trade_zip(zip_path, audit_path=audit_path, market=market)
    canonical = canonicalize_binance_trade_zip(zip_path, output_path=canonical_path, market=market)
    summary = build_report(canonical_path, limit=limit, initial_capital=initial_capital)

    determinism = {"requested": False, "matches": None}
    if repeat_check:
        repeated_summary = build_report(canonical_path, limit=limit, initial_capital=initial_capital)
        determinism = _determinism_report(summary, repeated_summary)

    manifest = {
        "market": market,
        "source_zip_path": str(zip_path),
        "source_sha256": checksum["actual_sha256"],
        "checksum_status": checksum["status"],
        "checksum_expected_sha256": checksum["expected_sha256"],
        "checksum_matched": checksum["matched"],
        "canonical_path": str(canonical_path),
        "canonical_sha256": canonical["canonical_sha256"],
        "csv_member": canonical["csv_member"],
        "total_rows": audit["total_rows"],
        "valid_rows": canonical["valid_rows"],
        "duplicate_trade_ids": audit["duplicate_trade_ids"],
        "first_event_time_utc": canonical["first_event_time_utc"],
        "last_event_time_utc": canonical["last_event_time_utc"],
        "audit_status": audit["audit_status"],
        "canonicalization_status": canonical["canonicalization_status"],
        "dataset_status": summary["replay"]["dataset_status"],
        "validation_status": summary["backtest"]["validation_status"],
        "backtest_run_id": summary["backtest"]["run_id"],
        "backtest_dataset_id": summary["backtest"]["dataset_id"],
        "determinism_requested": repeat_check,
        "determinism_matches": determinism["matches"],
    }
    _write_json(manifest_path, manifest)

    return {
        "source_archive": {
            "path": str(zip_path),
            "file_size_bytes": zip_path.stat().st_size,
            **checksum,
        },
        "audit": audit,
        "canonical": {
            **canonical,
            "file_size_bytes": canonical_path.stat().st_size,
            "file_sha256": _sha256_file(canonical_path),
        },
        "manifest": manifest,
        "artifacts": {
            "audit_path": str(audit_path),
            "canonical_path": str(canonical_path),
            "manifest_path": str(manifest_path),
        },
        "summary": summary,
        "determinism": determinism,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Binance January 2024 historical pipeline from either a canonical JSONL archive or a raw Binance zip archive.")
    parser.add_argument("--path", default=str(DEFAULT_CANONICAL_PATH), help="Path to an existing canonical Binance JSONL archive")
    parser.add_argument("--zip-path", default=None, help="Optional path to the raw Binance zip archive to audit and canonicalize before replay/backtest")
    parser.add_argument("--checksum-path", default=None, help="Optional path to a Binance .CHECKSUM file for the raw archive")
    parser.add_argument("--expected-hash", default=None, help="Optional expected SHA-256 hash for the raw archive")
    parser.add_argument("--audit-output", default=str(DEFAULT_AUDIT_PATH), help="Path to write the raw-archive audit JSON")
    parser.add_argument("--canonical-output", default=str(DEFAULT_CANONICAL_PATH), help="Path to write the canonical JSONL when using --zip-path")
    parser.add_argument("--manifest-output", default=str(DEFAULT_MANIFEST_PATH), help="Path to write the manifest JSON when using --zip-path")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of events to stream")
    parser.add_argument("--initial-capital", type=float, default=1000.0, help="Backtest initial capital")
    parser.add_argument("--repeat-check", action="store_true", help="Run the summary replay/backtest twice and report whether deterministic outputs match")
    parser.add_argument("--output", default=None, help="Optional path to write the JSON report")
    args = parser.parse_args()

    if args.zip_path:
        zip_path = Path(args.zip_path)
        if not zip_path.exists():
            raise SystemExit(f"Raw Binance archive not found: {zip_path}")
        report = build_end_to_end_report(
            zip_path,
            canonical_path=Path(args.canonical_output),
            audit_path=Path(args.audit_output),
            manifest_path=Path(args.manifest_output),
            limit=args.limit,
            initial_capital=args.initial_capital,
            checksum_path=Path(args.checksum_path) if args.checksum_path else None,
            expected_hash=args.expected_hash,
            repeat_check=args.repeat_check,
        )
    else:
        path = Path(args.path)
        if not path.exists():
            raise SystemExit(f"Canonical archive not found: {path}")
        report = build_report(path, limit=args.limit, initial_capital=args.initial_capital)

    payload = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()