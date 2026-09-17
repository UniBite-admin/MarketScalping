import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from historical_dataset import HistoricalDatasetCollector, HistoricalDatasetError
from bitvavo_trade_collector import BitvavoTradeCollector


DAY_MS = 24 * 60 * 60 * 1000


def _iso_utc(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat(timespec="milliseconds")


def _row(trade_id: str, ts_ms: int, amount: str = "0.25", price: str = "95000.5", side: str = "buy"):
    return {
        "trade_id": trade_id,
        "timestamp": ts_ms,
        "amount": amount,
        "price": price,
        "side": side,
    }


class HistoricalDatasetCollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_window_generation_respects_24h_maximum(self):
        collector = HistoricalDatasetCollector(base_dir=self.tmp_path / "datasets")
        windows = collector.generate_windows(0, 2 * DAY_MS + 60000, window_size_ms=DAY_MS)
        self.assertEqual(windows, [(0, DAY_MS), (DAY_MS, 2 * DAY_MS), (2 * DAY_MS, 2 * DAY_MS + 60000)])

    def test_exact_boundary_is_not_split_into_extra_window(self):
        collector = HistoricalDatasetCollector(base_dir=self.tmp_path / "datasets")
        windows = collector.generate_windows(0, 2 * DAY_MS, window_size_ms=DAY_MS)
        self.assertEqual(windows, [(0, DAY_MS), (DAY_MS, 2 * DAY_MS)])

    def test_collect_dataset_generates_manifest_and_validates_happy_path(self):
        def fetcher_factory(request):
            query = request.full_url
            if "start=0" in query and "end=86400000" in query:
                return __import__("json").dumps([_row("t-1", 0), _row("t-2", 5000)]).encode("utf-8")
            if "start=86400000" in query and "end=172800000" in query:
                return __import__("json").dumps([_row("t-3", 86401000), _row("t-4", 86402000)]).encode("utf-8")
            return __import__("json").dumps([]).encode("utf-8")

        collector = HistoricalDatasetCollector(
            trade_collector=BitvavoTradeCollector(fetcher=fetcher_factory, default_output_dir=self.tmp_path / "raw"),
            base_dir=self.tmp_path / "datasets",
        )

        result = collector.collect_dataset("BTC-EUR", 0, 2 * DAY_MS, dataset_id="dataset-01")
        self.assertEqual(result["collection_status"], "VALIDATED")
        self.assertEqual(result["validation_status"], "VALIDATED")
        self.assertEqual(len(result["windows"]), 2)
        self.assertTrue((self.tmp_path / "datasets" / "dataset-01" / "manifest.json").exists())

    def test_manifest_tracks_pagination_continuation_and_hashes(self):
        page_one = [_row(f"t-{idx}", 1000 + idx) for idx in range(1000)]
        page_two = [_row("tail-1", 2000), _row("tail-2", 2500)]
        fetch_calls = {"count": 0}

        def fetcher_factory(request):
            fetch_calls["count"] += 1
            if "tradeIdFrom" in request.full_url:
                return __import__("json").dumps(page_two).encode("utf-8")
            return __import__("json").dumps(page_one).encode("utf-8")

        base_dir = self.tmp_path / "datasets"
        collector = HistoricalDatasetCollector(
            trade_collector=BitvavoTradeCollector(fetcher=fetcher_factory, default_output_dir=self.tmp_path / "raw"),
            base_dir=base_dir,
        )

        result = collector.collect_dataset("BTC-EUR", 0, DAY_MS, dataset_id="pagination-manifest")

        self.assertEqual(result["collection_status"], "VALIDATED")
        self.assertEqual(result["page_count"], 2)
        self.assertTrue(result["coverage_exhausted"])
        self.assertEqual(result["total_record_count"], 1002)
        self.assertEqual(result["pagination_mode"], "tradeIdFrom")
        self.assertEqual(result["pagination_status"], "short_page_proves_exhaustion")
        manifest_path = base_dir / "pagination-manifest" / "manifest.json"
        self.assertTrue(manifest_path.exists())
        validated = collector.validate_manifest(manifest_path)
        self.assertEqual(validated["validation_status"], "VALIDATED")
        self.assertEqual(validated["total_record_count"], 1002)
        self.assertEqual(validated["page_count"], 2)
        self.assertEqual(fetch_calls["count"], 2)

    def test_resume_ignores_existing_valid_windows_and_continues(self):
        base_dir = self.tmp_path / "datasets" / "resume-case"
        base_dir.mkdir(parents=True, exist_ok=True)

        def fetcher_factory(request):
            query = request.full_url
            if "start=0" in query and "end=86400000" in query:
                return __import__("json").dumps([_row("t-1", 1000)]).encode("utf-8")
            if "start=86400000" in query and "end=172800000" in query:
                return __import__("json").dumps([_row("t-2", 86401000)]).encode("utf-8")
            return __import__("json").dumps([]).encode("utf-8")

        collector = HistoricalDatasetCollector(
            trade_collector=BitvavoTradeCollector(fetcher=fetcher_factory, default_output_dir=base_dir / "raw"),
            base_dir=base_dir,
        )

        first = collector.collect_dataset("BTC-EUR", 0, 2 * DAY_MS, dataset_id="resume-case")
        self.assertEqual(first["collection_status"], "VALIDATED")

        second = collector.collect_dataset("BTC-EUR", 0, 2 * DAY_MS, dataset_id="resume-case")
        self.assertEqual(second["collection_status"], "VALIDATED")
        self.assertEqual(second["attempt_count"], 0)

    def test_duplicate_trade_ids_across_windows_reject_dataset(self):
        def fetcher_factory(request):
            query = request.full_url
            if "start=0" in query and "end=86400000" in query:
                return __import__("json").dumps([_row("shared-id", 1000)]).encode("utf-8")
            if "start=86400000" in query and "end=172800000" in query:
                return __import__("json").dumps([_row("shared-id", 86401000)]).encode("utf-8")
            return __import__("json").dumps([]).encode("utf-8")

        collector = HistoricalDatasetCollector(
            trade_collector=BitvavoTradeCollector(fetcher=fetcher_factory, default_output_dir=self.tmp_path / "raw"),
            base_dir=self.tmp_path / "datasets",
        )

        result = collector.collect_dataset("BTC-EUR", 0, 2 * DAY_MS, dataset_id="dup-check")
        self.assertEqual(result["collection_status"], "REJECTED")
        self.assertEqual(result["validation_status"], "REJECTED")
        self.assertIn("duplicate_trade_id", result["integrity_issues"])

    def test_hash_mismatch_fail_closes_now(self):
        base_dir = self.tmp_path / "datasets" / "hash-check"
        base_dir.mkdir(parents=True, exist_ok=True)
        raw_dir = base_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        file_path = raw_dir / "BTC-EUR_19700101T000000.000Z_19700102T000000.000Z.jsonl"
        file_path.write_text(json.dumps(_row("t-1", 1000)) + "\n", encoding="utf-8")

        manifest = {
            "dataset_id": "hash-check",
            "market": "BTC-EUR",
            "source": "bitvavo_public_historical_trades",
            "requested_start_utc": _iso_utc(0),
            "requested_end_utc": _iso_utc(2 * DAY_MS),
            "actual_start_utc": _iso_utc(0),
            "actual_end_utc": _iso_utc(2 * DAY_MS),
            "window_size_ms": DAY_MS,
            "window_count": 2,
            "total_record_count": 1,
            "file_list": [file_path.name],
            "per_file_record_count": {file_path.name: 1},
            "per_file_start_utc": {file_path.name: _iso_utc(0)},
            "per_file_end_utc": {file_path.name: _iso_utc(2 * DAY_MS)},
            "per_file_sha256": {file_path.name: "bad-hash"},
            "collection_status": "VALIDATED",
            "validation_status": "VALIDATED",
            "completeness_status": "COMPLETE",
            "created_at_utc": _iso_utc(0),
            "schema_version": "1.0",
            "windows": [],
        }
        (base_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        collector = HistoricalDatasetCollector(base_dir=base_dir)
        with self.assertRaises(HistoricalDatasetError):
            collector.validate_manifest(base_dir / "manifest.json")

    def test_zero_trade_window_is_not_treated_as_gap(self):
        def fetcher_factory(request):
            return __import__("json").dumps([]).encode("utf-8")

        collector = HistoricalDatasetCollector(
            trade_collector=BitvavoTradeCollector(fetcher=fetcher_factory, default_output_dir=self.tmp_path / "raw"),
            base_dir=self.tmp_path / "datasets",
        )
        result = collector.collect_dataset("BTC-EUR", 0, DAY_MS, dataset_id="zero-window")
        self.assertEqual(result["collection_status"], "VALIDATED")
        self.assertEqual(result["coverage_status"], "ZERO_TRADE_WINDOW")

    def test_adjacent_persisted_windows_are_allowed(self):
        dataset_root = self.tmp_path / "datasets" / "adjacent-ok"
        raw_dir = dataset_root / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        win1 = raw_dir / "win-1.jsonl"
        win2 = raw_dir / "win-2.jsonl"
        win1.write_text('{"trade_id": "a"}\n', encoding="utf-8")
        win2.write_text('{"trade_id": "b"}\n', encoding="utf-8")

        manifest = {
            "dataset_id": "adjacent-ok",
            "market": "BTC-EUR",
            "source": "bitvavo_public_historical_trades",
            "requested_start_utc": _iso_utc(0),
            "requested_end_utc": _iso_utc(2 * DAY_MS),
            "file_list": ["win-1.jsonl", "win-2.jsonl"],
            "per_file_sha256": {
                "win-1.jsonl": hashlib.sha256(win1.read_bytes()).hexdigest(),
                "win-2.jsonl": hashlib.sha256(win2.read_bytes()).hexdigest(),
            },
            "windows": [
                {"window_start_ms": 0, "window_end_ms": DAY_MS},
                {"window_start_ms": DAY_MS, "window_end_ms": 2 * DAY_MS},
            ],
        }
        manifest_path = dataset_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        collector = HistoricalDatasetCollector(base_dir=self.tmp_path / "datasets")
        validated = collector.validate_manifest(manifest_path)
        self.assertEqual(validated["validation_status"], "VALIDATED")

    def test_overlapping_persisted_windows_fail_closed(self):
        dataset_root = self.tmp_path / "datasets" / "overlap-fail"
        raw_dir = dataset_root / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        win1 = raw_dir / "win-1.jsonl"
        win2 = raw_dir / "win-2.jsonl"
        win1.write_text('{"trade_id": "a"}\n', encoding="utf-8")
        win2.write_text('{"trade_id": "b"}\n', encoding="utf-8")

        manifest = {
            "dataset_id": "overlap-fail",
            "market": "BTC-EUR",
            "source": "bitvavo_public_historical_trades",
            "requested_start_utc": _iso_utc(0),
            "requested_end_utc": _iso_utc(2 * DAY_MS),
            "file_list": ["win-1.jsonl", "win-2.jsonl"],
            "per_file_sha256": {
                "win-1.jsonl": hashlib.sha256(win1.read_bytes()).hexdigest(),
                "win-2.jsonl": hashlib.sha256(win2.read_bytes()).hexdigest(),
            },
            "windows": [
                {"window_start_ms": 0, "window_end_ms": DAY_MS},
                {"window_start_ms": DAY_MS // 2, "window_end_ms": 2 * DAY_MS},
            ],
        }
        manifest_path = dataset_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        collector = HistoricalDatasetCollector(base_dir=self.tmp_path / "datasets")
        with self.assertRaises(HistoricalDatasetError):
            collector.validate_manifest(manifest_path)

    def test_resume_does_not_silently_hide_overlap(self):
        base_dir = self.tmp_path / "datasets" / "resume-overlap"
        base_dir.mkdir(parents=True, exist_ok=True)
        raw_dir = base_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        win1 = raw_dir / "win-1.jsonl"
        win2 = raw_dir / "win-2.jsonl"
        win1.write_text('{"trade_id": "a"}\n', encoding="utf-8")
        win2.write_text('{"trade_id": "b"}\n', encoding="utf-8")

        manifest = {
            "dataset_id": "resume-overlap",
            "market": "BTC-EUR",
            "source": "bitvavo_public_historical_trades",
            "requested_start_utc": _iso_utc(0),
            "requested_end_utc": _iso_utc(2 * DAY_MS),
            "file_list": ["win-1.jsonl", "win-2.jsonl"],
            "per_file_sha256": {
                "win-1.jsonl": hashlib.sha256(win1.read_bytes()).hexdigest(),
                "win-2.jsonl": hashlib.sha256(win2.read_bytes()).hexdigest(),
            },
            "windows": [
                {"window_start_ms": 0, "window_end_ms": DAY_MS},
                {"window_start_ms": DAY_MS // 2, "window_end_ms": 2 * DAY_MS},
            ],
            "collection_status": "VALIDATED",
            "validation_status": "VALIDATED",
            "completeness_status": "COMPLETE",
        }
        (base_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        collector = HistoricalDatasetCollector(base_dir=base_dir)
        with self.assertRaises(HistoricalDatasetError):
            collector.validate_manifest(base_dir / "manifest.json")

    def test_retryable_failure_retries_once_then_succeeds(self):
        attempts = {"count": 0}

        def fetcher_factory(request):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise OSError("temporary network failure")
            return __import__("json").dumps([_row("retry-ok", 1000)]).encode("utf-8")

        collector = HistoricalDatasetCollector(
            trade_collector=BitvavoTradeCollector(fetcher=fetcher_factory, default_output_dir=self.tmp_path / "raw"),
            base_dir=self.tmp_path / "datasets",
            max_retries=2,
            backoff_seconds=0,
        )

        result = collector.collect_dataset("BTC-EUR", 0, DAY_MS, dataset_id="retry-case")
        self.assertEqual(result["collection_status"], "VALIDATED")
        self.assertEqual(attempts["count"], 2)

    def test_permanent_failure_does_not_retry(self):
        attempts = {"count": 0}

        def fetcher_factory(request):
            attempts["count"] += 1
            return __import__("json").dumps([_row("bad", 1000, amount="invalid", price="95000.5", side="buy")]).encode("utf-8")

        collector = HistoricalDatasetCollector(
            trade_collector=BitvavoTradeCollector(fetcher=fetcher_factory, default_output_dir=self.tmp_path / "raw"),
            base_dir=self.tmp_path / "datasets",
            max_retries=3,
            backoff_seconds=0,
        )

        result = collector.collect_dataset("BTC-EUR", 0, DAY_MS, dataset_id="permanent-case")
        self.assertEqual(result["collection_status"], "REJECTED")
        self.assertEqual(attempts["count"], 1)


if __name__ == "__main__":
    unittest.main()
