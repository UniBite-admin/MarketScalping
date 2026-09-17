import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from unittest.mock import patch

from bitvavo_trade_collector import BitvavoHistoricalTrade, BitvavoTradeCollector, BitvavoTradeCollectorError


class DummyResponse:
    def __init__(self, payload: object):
        self._payload = payload

    def read(self):
        if isinstance(self._payload, (bytes, bytearray)):
            return self._payload
        return json.dumps(self._payload).encode("utf-8")


class CapturingFetcher:
    def __init__(self, response_payload: object):
        self.response_payload = response_payload
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return DummyResponse(self.response_payload)


class BitvavoTradeCollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _collector(self, response_payload: object):
        fetcher = CapturingFetcher(response_payload)
        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        return collector, fetcher

    def test_valid_trade_record(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800000,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        }]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertEqual(result.fetched, 1)
        self.assertEqual(result.accepted, 1)
        self.assertEqual(result.rejected, 0)
        self.assertEqual(result.duplicated, 0)
        self.assertEqual(len(result.records), 1)
        record = result.records[0]
        self.assertEqual(record.trade_id, "trade-1")
        self.assertEqual(record.market, "BTC-EUR")
        self.assertEqual(record.side, "buy")
        self.assertEqual(record.price, 95000.5)
        self.assertEqual(record.amount, 0.25)

    def test_timestamp_conversion(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800123,
            "amount": "0.25",
            "price": "95000.5",
            "side": "sell",
        }]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.records[0].event_time_utc, "2025-01-01T12:00:00.123+00:00")

    def test_invalid_timestamp(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": "not-a-timestamp",
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        }]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.accepted, 0)
        self.assertEqual(result.rejected, 1)
        self.assertIn(("invalid_timestamp", 1), result.rejection_reasons)

    def test_invalid_price(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800000,
            "amount": "0.25",
            "price": "abc",
            "side": "buy",
        }]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.accepted, 0)
        self.assertEqual(result.rejected, 1)
        self.assertIn(("invalid_price", 1), result.rejection_reasons)

    def test_invalid_amount(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800000,
            "amount": "0",
            "price": "95000.5",
            "side": "buy",
        }]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.accepted, 0)
        self.assertEqual(result.rejected, 1)
        self.assertIn(("non_positive_amount", 1), result.rejection_reasons)

    def test_raw_numeric_contract_rejects_nan_and_infinity(self):
        invalid_cases = [
            ({"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "0.25", "price": "nan", "side": "buy"}, "invalid_price"),
            ({"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "0.25", "price": "inf", "side": "buy"}, "invalid_price"),
            ({"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "0.25", "price": "-inf", "side": "buy"}, "invalid_price"),
            ({"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "nan", "price": "95000.5", "side": "buy"}, "invalid_amount"),
            ({"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "inf", "price": "95000.5", "side": "buy"}, "invalid_amount"),
            ({"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "-inf", "price": "95000.5", "side": "buy"}, "invalid_amount"),
        ]

        for row, reason in invalid_cases:
            with self.subTest(row=row):
                collector = BitvavoTradeCollector(fetcher=lambda request, row=row: DummyResponse([row]), default_output_dir=self.tmp_path / "raw")
                result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
                self.assertEqual(result.accepted, 0)
                self.assertEqual(result.rejected, 1)
                self.assertIn((reason, 1), result.rejection_reasons)

    def test_raw_zero_and_negative_prices_are_rejected(self):
        for row in [
            {"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "0.25", "price": "0", "side": "buy"},
            {"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "0.25", "price": "-10.0", "side": "buy"},
            {"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "0", "price": "95000.5", "side": "buy"},
            {"trade_id": "trade-1", "timestamp": 1735732800000, "amount": "-0.25", "price": "95000.5", "side": "buy"},
        ]:
            with self.subTest(row=row):
                collector = BitvavoTradeCollector(fetcher=lambda request, row=row: DummyResponse([row]), default_output_dir=self.tmp_path / "raw")
                result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
                self.assertEqual(result.accepted, 0)
                self.assertEqual(result.rejected, 1)
                self.assertTrue(any(reason in {"non_positive_price", "non_positive_amount"} for reason, _ in result.rejection_reasons))

    def test_invalid_side(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800000,
            "amount": "0.25",
            "price": "95000.5",
            "side": "hold",
        }]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.accepted, 0)
        self.assertEqual(result.rejected, 1)
        self.assertIn(("invalid_side", 1), result.rejection_reasons)

    def test_duplicate_trade_id(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([
            {
                "trade_id": "trade-1",
                "timestamp": 1735732800000,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            },
            {
                "trade_id": "trade-1",
                "timestamp": 1735732801000,
                "amount": "0.30",
                "price": "95001.5",
                "side": "sell",
            },
        ]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.accepted, 1)
        self.assertEqual(result.duplicated, 1)

    def test_invalid_window_is_explicitly_rejected(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800000,
            "amount": "invalid",
            "price": "95000.5",
            "side": "buy",
        }]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.collection_status, "rejected")
        self.assertFalse(result.window_complete)
        self.assertEqual(result.accepted, 0)
        self.assertIn("invalid_rows_present", result.integrity_issues)

    def test_empty_window_is_valid_and_successful(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.collection_status, "success")
        self.assertTrue(result.window_complete)
        self.assertEqual(result.accepted, 0)
        self.assertEqual(result.fetched, 0)

    def test_dataset_state_is_explicit_for_valid_empty_and_rejected_outputs(self):
        valid_collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800000,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        }]), default_output_dir=self.tmp_path / "raw")
        valid_result = valid_collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "valid.jsonl")
        self.assertEqual(valid_result.dataset_status, "VALIDATED")

        empty_collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([]), default_output_dir=self.tmp_path / "raw")
        empty_result = empty_collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "empty.jsonl")
        self.assertEqual(empty_result.dataset_status, "EMPTY_VALID_DATASET")

        invalid_collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800000,
            "amount": "invalid",
            "price": "95000.5",
            "side": "buy",
        }]), default_output_dir=self.tmp_path / "raw")
        invalid_result = invalid_collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "invalid.jsonl")
        self.assertEqual(invalid_result.dataset_status, "REJECTED")

    def test_out_of_window_timestamp_is_blocked(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([{
            "trade_id": "trade-1",
            "timestamp": 1735732800000,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        }]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732801000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.collection_status, "blocked")
        self.assertFalse(result.window_complete)
        self.assertIn("timestamp_outside_requested_window", result.integrity_issues)

    def test_chronological_sorting(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([
            {
                "trade_id": "trade-2",
                "timestamp": 1735732801000,
                "amount": "0.30",
                "price": "95001.5",
                "side": "sell",
            },
            {
                "trade_id": "trade-1",
                "timestamp": 1735732800000,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            },
        ]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual([record.trade_id for record in result.records], ["trade-1", "trade-2"])

    def test_deterministic_equal_timestamp_ordering(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([
            {
                "trade_id": "trade-b",
                "timestamp": 1735732800000,
                "amount": "0.30",
                "price": "95001.5",
                "side": "sell",
            },
            {
                "trade_id": "trade-a",
                "timestamp": 1735732800000,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            },
        ]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual([record.trade_id for record in result.records], ["trade-a", "trade-b"])

    def test_api_response_parsing(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse({
            "data": [
                {
                    "trade_id": "trade-1",
                    "timestamp": 1735732800000,
                    "amount": "0.25",
                    "price": "95000.5",
                    "side": "buy",
                }
            ]
        }), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.accepted, 1)
        self.assertEqual(result.records[0].trade_id, "trade-1")

    def test_api_id_field_is_supported_for_trade_id(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([
            {
                "id": "trade-from-id",
                "timestamp": 1735732800000,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            }
        ]), default_output_dir=self.tmp_path / "raw")

        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")
        self.assertEqual(result.accepted, 1)
        self.assertEqual(result.records[0].trade_id, "trade-from-id")

    def test_exact_1000_page_requires_continuation_and_preserves_additional_records(self):
        page_one = [{
            "trade_id": f"trade-{idx}",
            "timestamp": 1735732860000 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        } for idx in range(1000)]
        page_two = [{
            "trade_id": f"tail-{idx}",
            "timestamp": 1735731859999 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "sell",
        } for idx in range(7)]
        requests_seen = []

        def fetcher(request):
            requests_seen.append(request.full_url)
            if "tradeIdFrom" in request.full_url:
                if len(requests_seen) == 2:
                    return DummyResponse(page_two)
                return DummyResponse([])
            return DummyResponse(page_one)

        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        result = collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertEqual(len(requests_seen), 3)
        self.assertIn(f"tradeIdFrom={page_one[-1]['trade_id']}", requests_seen[1])
        self.assertEqual(result.page_count, 3)
        self.assertEqual(len(result.records), 1007)
        self.assertEqual(len({record.trade_id for record in result.records}), 1007)
        self.assertTrue(result.window_complete)
        self.assertTrue(result.coverage_exhausted)
        self.assertEqual(result.collection_status, "success")
        self.assertEqual(result.pagination_status, "empty_page")
        self.assertEqual([record.trade_id for record in result.records], [
            record.trade_id for record in sorted(result.records, key=lambda record: (record.raw_timestamp_ms, record.trade_id))
        ])

    def test_exact_1000_page_with_proven_exhaustion_finishes_without_extra_request(self):
        page_one = [{
            "trade_id": f"full-{idx}",
            "timestamp": 1735732860000 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        } for idx in range(1000)]
        requests_seen = []

        def fetcher(request):
            requests_seen.append(request.full_url)
            if "tradeIdFrom" in request.full_url:
                return DummyResponse([])
            return DummyResponse(page_one)

        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        result = collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertEqual(len(requests_seen), 2)
        self.assertTrue(result.window_complete)
        self.assertTrue(result.coverage_exhausted)
        self.assertEqual(result.page_count, 2)
        self.assertEqual(result.pagination_status, "empty_page_after_full_page")
        self.assertEqual(len(result.records), 1000)

    def test_trade_id_from_cursor_uses_last_trade_id_from_descending_page(self):
        page_one = [{
            "trade_id": f"newest-{idx}",
            "timestamp": 1735732860000 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        } for idx in range(1000)]
        page_two = [{
            "trade_id": "older-1",
            "timestamp": 1735732780000,
            "amount": "0.25",
            "price": "95000.5",
            "side": "sell",
        }]
        requests_seen = []

        def fetcher(request):
            requests_seen.append(request.full_url)
            if "tradeIdFrom" not in request.full_url:
                return DummyResponse(page_one)
            if len(requests_seen) == 2:
                self.assertIn(f"tradeIdFrom={page_one[-1]['trade_id']}", request.full_url)
                return DummyResponse(page_two)
            self.assertIn("tradeIdFrom=older-1", request.full_url)
            return DummyResponse([])

        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        result = collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertEqual(result.page_count, 3)
        self.assertEqual(result.pagination_mode, "tradeIdFrom")
        self.assertIn("older-1", {record.trade_id for record in result.records})
        self.assertEqual(len(result.records), 1001)
        self.assertEqual(len(requests_seen), 3)

    def test_page_boundary_overlap_is_allowed_once_and_pagination_continues(self):
        page_one = [{
            "trade_id": f"page1-{idx}",
            "timestamp": 1735732860000 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        } for idx in range(1000)]
        boundary_trade = page_one[-1]
        page_two = [
            {
                "trade_id": boundary_trade["trade_id"],
                "timestamp": boundary_trade["timestamp"],
                "amount": boundary_trade["amount"],
                "price": boundary_trade["price"],
                "side": boundary_trade["side"],
            },
            {
                "trade_id": "new-page2-1",
                "timestamp": 1735731801000,
                "amount": "0.20",
                "price": "94999.7",
                "side": "sell",
            },
            {
                "trade_id": "new-page2-2",
                "timestamp": 1735731802000,
                "amount": "0.18",
                "price": "94998.9",
                "side": "buy",
            },
        ]
        requests_seen = []

        def fetcher(request):
            requests_seen.append(request.full_url)
            if "tradeIdFrom" not in request.full_url:
                return DummyResponse(page_one)
            if len(requests_seen) == 2:
                return DummyResponse(page_two)
            return DummyResponse([])

        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        result = collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertEqual(len(requests_seen), 3)
        self.assertEqual(result.page_count, 3)
        self.assertTrue(result.window_complete)
        self.assertTrue(result.coverage_exhausted)
        self.assertEqual(result.pagination_status, "empty_page")
        self.assertEqual(len(result.records), 1002)
        self.assertEqual(len({record.trade_id for record in result.records}), 1002)
        self.assertEqual(sum(1 for record in result.records if record.trade_id == boundary_trade["trade_id"]), 1)
        self.assertIn("new-page2-1", {record.trade_id for record in result.records})
        self.assertIn("new-page2-2", {record.trade_id for record in result.records})

    def test_heavy_overlap_with_new_records_is_accepted_and_pagination_continues(self):
        page_one = [{
            "trade_id": f"page1-{idx}",
            "timestamp": 1735732860000 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        } for idx in range(1000)]
        page_two = [
            {"trade_id": page_one[idx]["trade_id"], "timestamp": page_one[idx]["timestamp"], "amount": page_one[idx]["amount"], "price": page_one[idx]["price"], "side": page_one[idx]["side"]}
            for idx in range(998)
        ]
        page_two.append({
            "trade_id": "new-page2-1",
            "timestamp": 1735731801000,
            "amount": "0.20",
            "price": "94999.7",
            "side": "sell",
        })

        def fetcher(request):
            if "tradeIdFrom" not in request.full_url:
                return DummyResponse(page_one)
            if "tradeIdFrom=page1-999" in request.full_url:
                return DummyResponse(page_two)
            return DummyResponse([])

        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        result = collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertEqual(result.page_count, 3)
        self.assertEqual(result.pagination_status, "empty_page")
        self.assertEqual(len(result.records), 1001)
        self.assertEqual(len({record.trade_id for record in result.records}), 1001)
        self.assertIn("new-page2-1", {record.trade_id for record in result.records})
        self.assertTrue(result.window_complete)
        self.assertTrue(result.coverage_exhausted)

    def test_multiple_consecutive_overlap_pages_make_progress(self):
        page_one = [{
            "trade_id": f"page1-{idx}",
            "timestamp": 1735732860000 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        } for idx in range(1000)]
        overlap_page_two = [
            {"trade_id": page_one[idx]["trade_id"], "timestamp": page_one[idx]["timestamp"], "amount": page_one[idx]["amount"], "price": page_one[idx]["price"], "side": page_one[idx]["side"]}
            for idx in range(998)
        ]
        overlap_page_two.append({
            "trade_id": "new-page2-1",
            "timestamp": 1735731801000,
            "amount": "0.20",
            "price": "94999.7",
            "side": "sell",
        })
        overlap_page_three = [
            {"trade_id": page_one[idx]["trade_id"], "timestamp": page_one[idx]["timestamp"], "amount": page_one[idx]["amount"], "price": page_one[idx]["price"], "side": page_one[idx]["side"]}
            for idx in range(995, 998)
        ]
        overlap_page_three.extend([
            {"trade_id": "new-page2-1", "timestamp": 1735731801000, "amount": "0.20", "price": "94999.7", "side": "sell"},
            {"trade_id": "new-page3-1", "timestamp": 1735731802000, "amount": "0.18", "price": "94998.9", "side": "buy"},
        ])

        request_count = {"value": 0}

        def fetcher(request):
            request_count["value"] += 1
            if request_count["value"] == 1:
                return DummyResponse(page_one)
            if request_count["value"] == 2:
                return DummyResponse(overlap_page_two)
            if request_count["value"] == 3:
                return DummyResponse(overlap_page_three)
            return DummyResponse([])

        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        result = collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertEqual(result.page_count, 4)
        self.assertEqual(len({record.trade_id for record in result.records}), len(result.records))
        self.assertIn("new-page2-1", {record.trade_id for record in result.records})
        self.assertIn("new-page3-1", {record.trade_id for record in result.records})
        self.assertTrue(result.window_complete)
        self.assertTrue(result.coverage_exhausted)

    def test_no_progress_overlap_page_raises(self):
        page_one = [{
            "trade_id": f"page1-{idx}",
            "timestamp": 1735732860000 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        } for idx in range(1000)]
        page_two = [
            {"trade_id": page_one[idx]["trade_id"], "timestamp": page_one[idx]["timestamp"], "amount": page_one[idx]["amount"], "price": page_one[idx]["price"], "side": page_one[idx]["side"]}
            for idx in range(999)
        ]

        def fetcher(request):
            if "tradeIdFrom" in request.full_url:
                return DummyResponse(page_two)
            return DummyResponse(page_one)

        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        with self.assertRaises(BitvavoTradeCollectorError):
            collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

    def test_non_boundary_duplicate_and_no_progress_boundary_still_fail_closed(self):
        page_one = [{
            "trade_id": f"page1-{idx}",
            "timestamp": 1735732860000 - idx,
            "amount": "0.25",
            "price": "95000.5",
            "side": "buy",
        } for idx in range(1000)]
        boundary_trade = page_one[-1]
        repeated_trade = page_one[500]
        new_trade = {
            "trade_id": "new-page2-1",
            "timestamp": 1735731801000,
            "amount": "0.20",
            "price": "94999.7",
            "side": "sell",
        }

        no_progress_case = [
            {
                "trade_id": boundary_trade["trade_id"],
                "timestamp": boundary_trade["timestamp"],
                "amount": boundary_trade["amount"],
                "price": boundary_trade["price"],
                "side": boundary_trade["side"],
            },
        ]
        progress_case = [
            {
                "trade_id": boundary_trade["trade_id"],
                "timestamp": boundary_trade["timestamp"],
                "amount": boundary_trade["amount"],
                "price": boundary_trade["price"],
                "side": boundary_trade["side"],
            },
            {
                "trade_id": repeated_trade["trade_id"],
                "timestamp": repeated_trade["timestamp"],
                "amount": repeated_trade["amount"],
                "price": repeated_trade["price"],
                "side": repeated_trade["side"],
            },
            new_trade,
        ]

        def no_progress_fetcher(request):
            if "tradeIdFrom" in request.full_url:
                return DummyResponse(no_progress_case)
            return DummyResponse(page_one)

        collector = BitvavoTradeCollector(fetcher=no_progress_fetcher, default_output_dir=self.tmp_path / "raw")
        with self.assertRaises(BitvavoTradeCollectorError):
            collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        call_count = {"value": 0}

        def progress_fetcher(request):
            call_count["value"] += 1
            if "tradeIdFrom" in request.full_url:
                if call_count["value"] == 2:
                    return DummyResponse(progress_case)
                return DummyResponse([])
            return DummyResponse(page_one)

        collector = BitvavoTradeCollector(fetcher=progress_fetcher, default_output_dir=self.tmp_path / "raw")
        result = collector.collect_window("BTC-EUR", 1735731800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertTrue(result.window_complete)
        self.assertTrue(result.coverage_exhausted)
        self.assertEqual(len(result.records), 1001)
        self.assertEqual(len({record.trade_id for record in result.records}), 1001)
        self.assertEqual(sum(1 for record in result.records if record.trade_id == new_trade["trade_id"]), 1)
        self.assertIn(new_trade["trade_id"], {record.trade_id for record in result.records})

    def test_max_page_guard_raises_on_unbounded_pagination_loop(self):
        call_count = {"value": 0}

        def fetcher(request):
            call_count["value"] += 1
            page = [{
                "trade_id": f"guard-{call_count['value']}-{idx}",
                "timestamp": 1735732800000 + idx,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            } for idx in range(1000)]
            return DummyResponse(page)

        collector = BitvavoTradeCollector(fetcher=fetcher, default_output_dir=self.tmp_path / "raw")
        with self.assertRaises(BitvavoTradeCollectorError) as exc:
            collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

        self.assertIn("maximum pagination iterations exceeded", str(exc.exception))
        self.assertGreaterEqual(call_count["value"], 1000)

    def test_http_failure_is_reported_safely(self):
        def failing_fetcher(request):
            raise URLError("simulated failure")

        collector = BitvavoTradeCollector(fetcher=failing_fetcher, default_output_dir=self.tmp_path / "raw")
        with self.assertRaises(BitvavoTradeCollectorError):
            collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=self.tmp_path / "out.jsonl")

    def test_request_uses_expected_query_parameters(self):
        collector, fetcher = self._collector([
            {
                "trade_id": "trade-1",
                "timestamp": 1735732800000,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            }
        ])

        collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, limit=1000, output_path=self.tmp_path / "out.jsonl")
        request = fetcher.requests[0]
        self.assertIn("/v2/BTC-EUR/trades", request.full_url)
        self.assertIn("start=1735732800000", request.full_url)
        self.assertIn("end=1735732860000", request.full_url)
        self.assertIn("limit=1000", request.full_url)

    def test_public_request_has_no_auth_headers_when_env_missing(self):
        collector, fetcher = self._collector([
            {
                "trade_id": "trade-1",
                "timestamp": 1735732800000,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            }
        ])

        with patch.dict(os.environ, {}, clear=True):
            collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, limit=1000, output_path=self.tmp_path / "out.jsonl")

        request = fetcher.requests[0]
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertNotIn("bitvavo-access-key", headers)
        self.assertNotIn("bitvavo-access-timestamp", headers)
        self.assertNotIn("bitvavo-access-signature", headers)

    def test_authenticated_request_includes_signature_headers(self):
        collector, fetcher = self._collector([
            {
                "trade_id": "trade-1",
                "timestamp": 1735732800000,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            }
        ])

        with patch.dict(
            os.environ,
            {"BITVAVO_API_KEY": "dummy-key", "BITVAVO_API_SECRET": "dummy-secret"},
            clear=False,
        ):
            collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, limit=1000, output_path=self.tmp_path / "out.jsonl")

        request = fetcher.requests[0]
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertIn("bitvavo-access-key", headers)
        self.assertIn("bitvavo-access-timestamp", headers)
        self.assertIn("bitvavo-access-signature", headers)
        self.assertIn("bitvavo-access-window", headers)

    def test_write_jsonl_output(self):
        collector = BitvavoTradeCollector(fetcher=lambda request: DummyResponse([
            {
                "trade_id": "trade-1",
                "timestamp": 1735732800000,
                "amount": "0.25",
                "price": "95000.5",
                "side": "buy",
            }
        ]), default_output_dir=self.tmp_path / "raw")

        output_path = self.tmp_path / "raw_output.jsonl"
        result = collector.collect_window("BTC-EUR", 1735732800000, 1735732860000, output_path=output_path)

        self.assertTrue(output_path.exists())
        with output_path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["trade_id"], "trade-1")
        self.assertEqual(payload["source"], "bitvavo_public_historical_trades")
        self.assertEqual(result.output_path, str(output_path))


if __name__ == "__main__":
    unittest.main()