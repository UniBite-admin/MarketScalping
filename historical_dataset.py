from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bitvavo_trade_collector import BitvavoTradeCollector, BitvavoTradeCollectorError


DAY_MS = 24 * 60 * 60 * 1000


class HistoricalDatasetError(RuntimeError):
    pass


class HistoricalDatasetCollector:
    """Multi-window raw historical data acquisition and integrity layer."""

    def __init__(
        self,
        trade_collector: BitvavoTradeCollector | None = None,
        base_dir: str | Path = Path("data") / "raw" / "historical_datasets",
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        default_window_size_ms: int = DAY_MS,
    ):
        self.trade_collector = trade_collector or BitvavoTradeCollector(default_output_dir=Path("data") / "raw" / "bitvavo_trades")
        self.base_dir = Path(base_dir)
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.default_window_size_ms = default_window_size_ms

    def generate_windows(self, start_ms: int, end_ms: int, window_size_ms: int | None = None) -> list[tuple[int, int]]:
        if window_size_ms is None:
            window_size_ms = self.default_window_size_ms
        if end_ms <= start_ms:
            raise HistoricalDatasetError("requested end must be greater than start")
        if window_size_ms <= 0:
            raise HistoricalDatasetError("window size must be positive")

        windows: list[tuple[int, int]] = []
        cursor = start_ms
        while cursor < end_ms:
            next_end = min(cursor + window_size_ms, end_ms)
            windows.append((cursor, next_end))
            cursor = next_end
        return windows

    def collect_dataset(
        self,
        market: str,
        start_ms: int,
        end_ms: int,
        dataset_id: str | None = None,
        window_size_ms: int | None = None,
        base_output_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        if dataset_id is None:
            dataset_id = self._default_dataset_id(market, start_ms, end_ms)
        if window_size_ms is None:
            window_size_ms = self.default_window_size_ms

        dataset_root = Path(base_output_dir) if base_output_dir is not None else self.base_dir / dataset_id
        dataset_root.mkdir(parents=True, exist_ok=True)
        raw_dir = dataset_root / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = dataset_root / "manifest.json"
        existing_manifest = self._read_manifest(manifest_path)
        if existing_manifest and existing_manifest.get("dataset_id") != dataset_id:
            raise HistoricalDatasetError("manifest dataset_id mismatch")

        windows = self.generate_windows(start_ms, end_ms, window_size_ms)
        results: list[dict[str, Any]] = []
        skip_count = 0
        for window_start, window_end in windows:
            file_name = self._window_filename(market, window_start, window_end)
            output_path = raw_dir / file_name

            if self._has_valid_manifest_window(existing_manifest, file_name, output_path):
                results.append(self._manifest_window_record(existing_manifest, file_name, window_start, window_end, output_path))
                skip_count += 1
                continue

            result = self._collect_window_with_retry(market, window_start, window_end, output_path)
            results.append(result)

        manifest = self._aggregate_results(market, start_ms, end_ms, dataset_root, results)
        self._write_manifest(manifest_path, manifest)
        return manifest

    def validate_manifest(self, manifest_path: str | Path) -> dict[str, Any]:
        path = Path(manifest_path)
        payload = self._read_json(path)
        file_list = payload.get("file_list") or []
        file_hashes = payload.get("per_file_sha256") or {}
        for file_name in file_list:
            file_path = path.parent / "raw" / file_name
            if not file_path.exists():
                raise HistoricalDatasetError(f"missing file for manifest entry: {file_name}")
            actual_hash = self._sha256_file(file_path)
            expected_hash = file_hashes.get(file_name)
            if expected_hash is None or actual_hash != expected_hash:
                raise HistoricalDatasetError(f"hash mismatch for {file_name}")

        self._validate_manifest_windows(payload)

        duplicate_trade_ids = self._scan_duplicates(path.parent)
        if duplicate_trade_ids:
            raise HistoricalDatasetError(f"duplicate_trade_id across windows: {duplicate_trade_ids[:10]}")

        payload["validation_status"] = "VALIDATED"
        payload["collection_status"] = "VALIDATED"
        payload["completeness_status"] = "COMPLETE"
        self._write_json(path, payload)
        return payload

    def freeze_dataset(self, dataset_root: str | Path) -> dict[str, Any]:
        path = Path(dataset_root)
        manifest_path = path / "manifest.json"
        manifest = self._read_manifest(manifest_path)
        if not manifest:
            raise HistoricalDatasetError("no manifest to freeze")
        self.validate_manifest(manifest_path)
        manifest["frozen"] = True
        manifest["frozen_at_utc"] = self._utc_now_iso()
        self._write_json(manifest_path, manifest)
        return manifest

    def _collect_window_with_retry(self, market: str, start_ms: int, end_ms: int, output_path: Path) -> dict[str, Any]:
        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                result = self.trade_collector.collect_window(market, start_ms, end_ms, output_path=output_path)
                if result.output_path:
                    file_path = Path(result.output_path)
                    if file_path.exists():
                        digest = self._sha256_file(file_path)
                    else:
                        digest = None
                else:
                    digest = None

                return {
                    "market": market,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "status": result.dataset_status,
                    "attempt_count": attempt + 1,
                    "validation_status": result.dataset_status,
                    "accepted_count": result.accepted,
                    "rejected_count": result.rejected,
                    "duplicate_count": result.duplicated,
                    "file_path": str(file_path) if result.output_path else str(output_path),
                    "sha256": digest,
                    "integrity_issues": list(result.integrity_issues),
                    "page_count": result.page_count,
                    "page_sizes": list(result.page_sizes),
                    "coverage_exhausted": result.coverage_exhausted,
                    "pagination_mode": result.pagination_mode,
                    "pagination_status": result.pagination_status,
                    "window_complete": result.window_complete,
                }
            except (BitvavoTradeCollectorError, OSError, TimeoutError) as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds)
                    continue
                raise HistoricalDatasetError(f"window {start_ms}-{end_ms} failed after retries: {last_error}") from exc
            except Exception as exc:  # pragma: no cover
                last_error = str(exc)
                raise HistoricalDatasetError(f"window {start_ms}-{end_ms} failed with non-retryable error: {last_error}") from exc

        if last_error is not None:
            raise HistoricalDatasetError(f"window {start_ms}-{end_ms} failed: {last_error}")
        raise HistoricalDatasetError(f"window {start_ms}-{end_ms} failed without a result")

    @staticmethod
    def _read_manifest(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return HistoricalDatasetCollector._read_json(path)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _default_dataset_id(market: str, start_ms: int, end_ms: int) -> str:
        return f"{market.lower()}_{start_ms}_{end_ms}"

    @staticmethod
    def _window_filename(market: str, start_ms: int, end_ms: int) -> str:
        return f"{market}_{HistoricalDatasetCollector._format_utc_label(start_ms)}_{HistoricalDatasetCollector._format_utc_label(end_ms)}.jsonl"

    @staticmethod
    def _format_utc_label(timestamp_ms: int) -> str:
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%S") + f".{dt.microsecond // 1000:03d}Z"

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    def _aggregate_results(
        self,
        market: str,
        start_ms: int,
        end_ms: int,
        dataset_root: Path,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        file_list: list[str] = []
        per_file_record_count: dict[str, int] = {}
        per_file_start_utc: dict[str, str] = {}
        per_file_end_utc: dict[str, str] = {}
        per_file_sha256: dict[str, str] = {}
        file_is_valid: dict[str, bool] = {}
        integrity_issues: list[str] = []
        all_windows: list[dict[str, Any]] = []

        for item in results:
            file_path = Path(item.get("file_path", ""))
            if not file_path.exists():
                if item.get("status") in {"VALIDATED", "EMPTY_VALID_DATASET"}:
                    integrity_issues.append(f"{item.get('start_ms')}-{item.get('end_ms')}:missing_file")
                continue
            file_name = file_path.name
            if file_name not in file_list:
                file_list.append(file_name)
            per_file_record_count[file_name] = int(item.get("accepted_count", 0))
            per_file_start_utc[file_name] = self._unix_ms_to_iso_utc(item.get("start_ms", start_ms))
            per_file_end_utc[file_name] = self._unix_ms_to_iso_utc(item.get("end_ms", end_ms))
            digest = self._sha256_file(file_path)
            per_file_sha256[file_name] = digest
            file_is_valid[file_name] = item.get("status") not in {"REJECTED"}
            all_windows.append({
                "window_start_ms": item.get("start_ms"),
                "window_end_ms": item.get("end_ms"),
                "status": item.get("status"),
                "accepted_count": item.get("accepted_count", 0),
                "rejected_count": item.get("rejected_count", 0),
                "duplicate_count": item.get("duplicate_count", 0),
                "integrity_issues": item.get("integrity_issues", []),
                "sha256": digest,
                "file": file_name,
            })
            for issue in item.get("integrity_issues", []):
                integrity_issues.append(f"{item.get('start_ms')}-{item.get('end_ms')}:{issue}")
            if item.get("status") == "REJECTED":
                integrity_issues.append(f"{item.get('start_ms')}-{item.get('end_ms')}:rejected_window")

        duplicate_trade_ids = self._scan_duplicates(dataset_root)
        if duplicate_trade_ids:
            integrity_issues.append("duplicate_trade_id")

        total_record_count = sum(int(item.get("accepted_count", 0)) for item in results)
        coverage_status = "ZERO_TRADE_WINDOW" if total_record_count == 0 else "COVERAGE_OK"
        collection_status = "VALIDATED"
        validation_status = "VALIDATED"
        if integrity_issues:
            collection_status = "REJECTED"
            validation_status = "REJECTED"

        manifest = {
            "dataset_id": dataset_root.name,
            "market": market,
            "source": "bitvavo_public_historical_trades",
            "requested_start_utc": self._unix_ms_to_iso_utc(start_ms),
            "requested_end_utc": self._unix_ms_to_iso_utc(end_ms),
            "actual_start_utc": self._unix_ms_to_iso_utc(start_ms),
            "actual_end_utc": self._unix_ms_to_iso_utc(end_ms),
            "window_size_ms": self.default_window_size_ms,
            "window_count": len(results),
            "total_record_count": total_record_count,
            "file_list": file_list,
            "per_file_record_count": per_file_record_count,
            "per_file_start_utc": per_file_start_utc,
            "per_file_end_utc": per_file_end_utc,
            "per_file_sha256": per_file_sha256,
            "collection_status": collection_status,
            "validation_status": validation_status,
            "completeness_status": "COMPLETE" if file_list or total_record_count == 0 else "PARTIAL",
            "coverage_status": coverage_status,
            "created_at_utc": self._utc_now_iso(),
            "schema_version": "1.0",
            "windows": all_windows,
            "integrity_issues": sorted(set(integrity_issues)),
            "frozen": False,
            "frozen_at_utc": None,
            "attempt_count": sum(int(item.get("attempt_count", 0)) for item in results),
            "pagination_mode": max((item.get("pagination_mode") for item in results if item.get("pagination_mode") is not None), default="single_request"),
            "page_count": max((int(item.get("page_count", 0)) for item in results), default=0),
            "page_sizes": [page for item in results for page in item.get("page_sizes", [])],
            "coverage_exhausted": any(bool(item.get("coverage_exhausted")) for item in results),
            "pagination_status": max((str(item.get("pagination_status")) for item in results if item.get("pagination_status") is not None), default="not_required", key=lambda value: (value != "not_required", value != "continuing", value != "short_page_proves_exhaustion", value != "empty_page_after_full_page", value != "zero_trade_window")),
        }
        return manifest

    def _write_manifest(self, manifest_path: Path, manifest: dict[str, Any]) -> None:
        self._write_json(manifest_path, manifest)

    def _fail_closed_if_invalid_allows(self, manifest: dict[str, Any]) -> None:
        if manifest.get("collection_status") == "REJECTED":
            return
        if manifest.get("validation_status") == "REJECTED":
            return
        return

    def _has_valid_manifest_window(self, manifest: dict[str, Any], file_name: str, output_path: Path) -> bool:
        if not manifest:
            return False
        file_list = manifest.get("file_list") or []
        if file_name not in file_list:
            return False
        file_hashes = manifest.get("per_file_sha256") or {}
        expected_hash = file_hashes.get(file_name)
        if expected_hash is None:
            return False
        if not output_path.exists():
            return False
        actual_hash = self._sha256_file(output_path)
        return actual_hash == expected_hash

    def _manifest_window_record(self, manifest: dict[str, Any], file_name: str, window_start: int, window_end: int, output_path: Path) -> dict[str, Any]:
        digest = self._sha256_file(output_path)
        file_record_count = int((manifest.get("per_file_record_count") or {}).get(file_name, 0))
        return {
            "market": manifest.get("market", "BTC-EUR"),
            "start_ms": window_start,
            "end_ms": window_end,
            "status": "VALIDATED",
            "attempt_count": 0,
            "validation_status": "VALIDATED",
            "accepted_count": file_record_count,
            "rejected_count": 0,
            "duplicate_count": 0,
            "file_path": str(output_path),
            "sha256": digest,
            "integrity_issues": [],
        }

    def _validate_manifest_windows(self, manifest: dict[str, Any]) -> None:
        windows = manifest.get("windows") or []
        if not windows:
            return

        ordered = sorted(windows, key=lambda item: (int(item.get("window_start_ms", 0)), int(item.get("window_end_ms", 0))))
        previous_start = None
        previous_end = None
        for window in ordered:
            start_ms = int(window.get("window_start_ms"))
            end_ms = int(window.get("window_end_ms"))
            if end_ms <= start_ms:
                raise HistoricalDatasetError(f"invalid dataset window range: {start_ms}-{end_ms}")
            if previous_end is not None and start_ms < previous_end:
                raise HistoricalDatasetError(
                    f"overlapping dataset windows: {previous_start}-{previous_end} and {start_ms}-{end_ms}"
                )
            previous_start = start_ms
            previous_end = end_ms

    def _scan_duplicates(self, dataset_root: Path) -> list[str]:
        seen: set[str] = set()
        duplicates: list[str] = []
        raw_dir = dataset_root / "raw"
        if not raw_dir.exists():
            return duplicates
        for file_path in sorted(raw_dir.glob("*.jsonl")):
            with file_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    trade_id = payload.get("trade_id")
                    if trade_id in seen:
                        duplicates.append(str(trade_id))
                    else:
                        seen.add(str(trade_id))
        return duplicates

    @staticmethod
    def _unix_ms_to_iso_utc(timestamp_ms: int) -> str:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat(timespec="milliseconds")
