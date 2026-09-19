from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import zipfile


_HASH_CHUNK_SIZE = 1024 * 1024
_TRUE_VALUES = {"true", "1", "yes"}
_FALSE_VALUES = {"false", "0", "no"}


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_binance_archive_checksum(zip_path: str | Path, expected_checksum: str) -> bool:
    digest = _sha256_file(zip_path)
    return digest.lower() == str(expected_checksum).strip().lower()


def read_binance_checksum_file(checksum_path: str | Path) -> str:
    text = Path(checksum_path).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) >= 2:
            return parts[0].strip().lower()
    return ""


def _parse_binance_bool(value: Any) -> bool | None:
    normalized = str(value).strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return None


def _is_trade_header_row(row: list[str]) -> bool:
    if not row or not any(cell.strip() for cell in row):
        return False
    first = (row[0] or "").strip().lower()
    return first in {"trade id", "tradeid", "aggregate tradeid", "trade_id"} or (first.startswith("trade") and not first.replace("trade", "").strip())


def _inspect_trade_csv_row(row: list[str]) -> dict[str, Any]:
    is_blank_row = not row or not any(str(cell).strip() for cell in row)
    trade_id = str(row[0]).strip() if len(row) > 0 else ""
    timestamp_ms: int | None = None
    price: float | None = None
    qty: float | None = None
    is_buyer_maker: bool | None = None
    is_best_match: bool | None = None

    invalid_price = False
    invalid_quantity = False
    invalid_timestamp = False
    invalid_boolean = False
    malformed = (len(row) < 7 or not trade_id) and not is_blank_row

    if is_blank_row:
        invalid_price = False
    elif len(row) > 1:
        try:
            price = float(row[1])
            invalid_price = price <= 0
        except (TypeError, ValueError):
            invalid_price = True
    else:
        invalid_price = True

    if is_blank_row:
        invalid_quantity = False
    elif len(row) > 2:
        try:
            qty = float(row[2])
            invalid_quantity = qty <= 0
        except (TypeError, ValueError):
            invalid_quantity = True
    else:
        invalid_quantity = True

    if is_blank_row:
        invalid_timestamp = False
    elif len(row) > 4:
        try:
            timestamp_ms = int(float(row[4]))
            invalid_timestamp = timestamp_ms <= 0
        except (TypeError, ValueError):
            invalid_timestamp = True
    else:
        invalid_timestamp = True

    if is_blank_row:
        invalid_boolean = False
    elif len(row) > 5:
        is_buyer_maker = _parse_binance_bool(row[5])
        invalid_boolean = is_buyer_maker is None
    else:
        invalid_boolean = True

    if len(row) > 6:
        is_best_match = _parse_binance_bool(row[6])

    malformed = malformed or ((invalid_price or invalid_quantity or invalid_timestamp) and not is_blank_row)

    return {
        "is_blank_row": is_blank_row,
        "trade_id": trade_id or None,
        "timestamp_ms": timestamp_ms,
        "price": price,
        "qty": qty,
        "is_buyer_maker": is_buyer_maker,
        "is_best_match": is_best_match,
        "invalid_price": invalid_price,
        "invalid_quantity": invalid_quantity,
        "invalid_timestamp": invalid_timestamp,
        "invalid_boolean": invalid_boolean,
        "malformed": malformed,
        "valid": not is_blank_row and not malformed and not invalid_boolean,
    }


def _build_trade_event(row: list[str], inspection: dict[str, Any], *, market: str) -> dict[str, Any]:
    timestamp_ms = int(inspection["timestamp_ms"])
    price = float(inspection["price"])
    qty = float(inspection["qty"])
    event_time_utc = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).isoformat(timespec="milliseconds")
    return {
        "event_type": "trade",
        "event_time_utc": event_time_utc,
        "market": market,
        "trade_id": str(inspection["trade_id"]),
        "price": price,
        "qty": qty,
        "last": price,
        "side": "buy" if inspection["is_buyer_maker"] else "sell",
        "source": "binance_public_data",
        "raw": {
            "tradeId": str(inspection["trade_id"]),
            "price": price,
            "qty": qty,
            "quoteQty": row[3].strip() if len(row) > 3 else None,
            "time": timestamp_ms,
            "isBuyerMaker": inspection["is_buyer_maker"],
            "isBestMatch": inspection["is_best_match"],
        },
    }


def _parse_trade_csv_row(row: list[str], *, market: str) -> dict[str, Any] | None:
    inspection = _inspect_trade_csv_row(row)
    if not inspection["valid"]:
        return None
    return _build_trade_event(row, inspection, market=market)


def _resolve_zip_csv_member(archive: zipfile.ZipFile) -> str:
    for info in archive.infolist():
        if info.is_dir():
            continue
        if info.filename.lower().endswith(".csv"):
            return info.filename
    raise ValueError("Binance trade archive does not contain a CSV member")


def _iter_binance_trade_zip_rows(zip_path: str | Path) -> tuple[str, Any]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        member_name = _resolve_zip_csv_member(archive)
        with archive.open(member_name, "r") as raw_handle:
            with io.TextIOWrapper(raw_handle, encoding="utf-8", newline="") as text_handle:
                reader = csv.reader(text_handle)
                for row in reader:
                    if _is_trade_header_row(row):
                        continue
                    yield member_name, row


def audit_binance_trade_zip(zip_path: str | Path, *, audit_path: str | Path | None = None, market: str = "BTC-USDT") -> dict[str, Any]:
    zip_file = Path(zip_path)
    seen_trade_ids: set[str] = set()
    report: dict[str, Any] = {
        "zip_path": str(zip_file),
        "market": market,
        "source_sha256": _sha256_file(zip_file),
        "total_rows": 0,
        "valid_rows": 0,
        "duplicate_trade_ids": 0,
        "malformed_rows": 0,
        "invalid_prices": 0,
        "invalid_quantities": 0,
        "invalid_timestamps": 0,
        "invalid_boolean_values": 0,
        "first_trade_id": None,
        "last_trade_id": None,
        "first_event_time_utc": None,
        "last_event_time_utc": None,
        "audit_status": "EMPTY_VALID_DATASET",
        "csv_member": None,
    }

    for member_name, row in _iter_binance_trade_zip_rows(zip_file):
        report["csv_member"] = member_name
        report["total_rows"] += 1
        inspection = _inspect_trade_csv_row(row)
        trade_id = inspection["trade_id"]
        if trade_id is not None:
            if report["first_trade_id"] is None:
                report["first_trade_id"] = trade_id
            report["last_trade_id"] = trade_id
        if inspection["invalid_price"]:
            report["invalid_prices"] += 1
        if inspection["invalid_quantity"]:
            report["invalid_quantities"] += 1
        if inspection["invalid_timestamp"]:
            report["invalid_timestamps"] += 1
        if inspection["invalid_boolean"]:
            report["invalid_boolean_values"] += 1
        if inspection["malformed"]:
            report["malformed_rows"] += 1
        if not inspection["valid"]:
            continue
        if trade_id in seen_trade_ids:
            report["duplicate_trade_ids"] += 1
            continue
        seen_trade_ids.add(str(trade_id))
        event = _build_trade_event(row, inspection, market=market)
        report["valid_rows"] += 1
        if report["first_event_time_utc"] is None:
            report["first_event_time_utc"] = event["event_time_utc"]
        report["last_event_time_utc"] = event["event_time_utc"]

    if report["valid_rows"] > 0:
        report["audit_status"] = "SUCCESS"

    if audit_path is not None:
        Path(audit_path).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def canonicalize_binance_trade_zip(
    zip_path: str | Path,
    *,
    output_path: str | Path,
    market: str = "BTC-USDT",
) -> dict[str, Any]:
    zip_file = Path(zip_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    seen_trade_ids: set[str] = set()
    canonical_hasher = hashlib.sha256()
    total_rows = 0
    valid_rows = 0
    duplicate_trade_ids = 0
    first_event_time_utc: str | None = None
    last_event_time_utc: str | None = None
    csv_member: str | None = None

    with destination.open("w", encoding="utf-8", newline="") as handle:
        for member_name, row in _iter_binance_trade_zip_rows(zip_file):
            csv_member = member_name
            total_rows += 1
            inspection = _inspect_trade_csv_row(row)
            if not inspection["valid"]:
                continue
            trade_id = str(inspection["trade_id"])
            if trade_id in seen_trade_ids:
                duplicate_trade_ids += 1
                continue
            seen_trade_ids.add(trade_id)
            event = _build_trade_event(row, inspection, market=market)
            serialized = json.dumps(event, sort_keys=True, separators=(",", ":"))
            handle.write(serialized)
            handle.write("\n")
            canonical_hasher.update(serialized.encode("utf-8"))
            canonical_hasher.update(b"\n")
            valid_rows += 1
            if first_event_time_utc is None:
                first_event_time_utc = event["event_time_utc"]
            last_event_time_utc = event["event_time_utc"]

    return {
        "zip_path": str(zip_file),
        "canonical_path": str(destination),
        "csv_member": csv_member,
        "source_sha256": _sha256_file(zip_file),
        "canonical_sha256": canonical_hasher.hexdigest(),
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "duplicate_trade_ids": duplicate_trade_ids,
        "first_event_time_utc": first_event_time_utc,
        "last_event_time_utc": last_event_time_utc,
        "canonicalization_status": "SUCCESS" if valid_rows > 0 else "EMPTY_VALID_DATASET",
    }


def load_binance_trade_csv(path: str | Path, *, market: str = "BTC-USDT") -> list[dict[str, Any]]:
    csv_path = Path(path)
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if _is_trade_header_row(row):
                continue
            event = _parse_trade_csv_row(row, market=market)
            if event is not None:
                rows.append(event)
    return rows
