import csv
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from binance_trade_adapter import (
    audit_binance_trade_zip,
    canonicalize_binance_trade_zip,
    load_binance_trade_csv,
    read_binance_checksum_file,
    verify_binance_archive_checksum,
)


class BinanceTradeAdapterTests(unittest.TestCase):
    def test_official_trade_row_is_converted_to_canonical_trade_event(self):
        csv_path = Path(tempfile.mkdtemp()) / "BTCUSDT-trades-sample.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["3344774379", "42283.58000000", "0.00069000", "29.17567020", "1704067200000", "True", "True"])

        events = load_binance_trade_csv(csv_path, market="BTC-USDT")

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["event_type"], "trade")
        self.assertEqual(event["market"], "BTC-USDT")
        self.assertEqual(event["last"], 42283.58)
        self.assertEqual(event["event_time_utc"], "2024-01-01T00:00:00.000+00:00")
        self.assertEqual(event["trade_id"], "3344774379")
        self.assertEqual(event["side"], "buy")

    def test_load_binance_trade_csv_ignores_headers_and_keeps_replay_ready_rows(self):
        csv_path = Path(tempfile.mkdtemp()) / "BTCUSDT-trades-sample.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["trade Id", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])
            writer.writerow(["3344774379", "42283.58000000", "0.00069000", "29.17567020", "1704067200000", "True", "True"])
            writer.writerow(["3344774380", "42283.59000000", "0.00144000", "60.88836960", "1704067200001", "False", "True"])

        events = load_binance_trade_csv(csv_path, market="BTC-USDT")

        self.assertEqual(len(events), 2)
        self.assertTrue(all(event["event_type"] == "trade" for event in events))
        self.assertTrue(all(event["market"] == "BTC-USDT" for event in events))
        self.assertTrue(all(event["last"] > 0 for event in events))
        self.assertEqual(events[0]["side"], "buy")
        self.assertEqual(events[1]["side"], "sell")

    def test_is_buyer_maker_semantics_follow_binance_contract(self):
        csv_path = Path(tempfile.mkdtemp()) / "BTCUSDT-trades-buyer-maker.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["trade Id", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])
            writer.writerow(["1001", "42000.00", "0.01", "420.00", "1704067200000", "True", "True"])
            writer.writerow(["1002", "42001.00", "0.01", "420.01", "1704067200001", "False", "True"])

        events = load_binance_trade_csv(csv_path, market="BTC-USDT")
        self.assertEqual(events[0]["side"], "buy")
        self.assertEqual(events[1]["side"], "sell")

    def test_checksum_file_parser_and_verifier_accept_expected_hash(self):
        checksum_path = Path(tempfile.mkdtemp()) / "BTCUSDT-trades-2024-01.zip.CHECKSUM"
        checksum_path.write_text("5c694c9e3ce6cadff6bbf1c5fdf502a7aa8ff97c7910a45ef78cc1c5f27cf618  BTCUSDT-trades-2024-01.zip\n", encoding="utf-8")

        zip_path = Path(tempfile.mkdtemp()) / "BTCUSDT-trades-2024-01.zip"
        zip_path.write_bytes(b"demo-binance-data")
        expected = read_binance_checksum_file(checksum_path)
        self.assertEqual(expected, "5c694c9e3ce6cadff6bbf1c5fdf502a7aa8ff97c7910a45ef78cc1c5f27cf618")
        self.assertFalse(verify_binance_archive_checksum(zip_path, expected))
        self.assertTrue(verify_binance_archive_checksum(zip_path, hashlib.sha256(zip_path.read_bytes()).hexdigest()))

    def test_streaming_archive_audit_is_persisted_and_counts_rows(self):
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "BTCUSDT-trades-2024-01.zip"
        csv_path = temp_dir / "BTCUSDT-trades-2024-01.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["trade Id", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])
            writer.writerow(["1001", "42000.00", "0.01000000", "420.00", "1704067200000", "True", "True"])
            writer.writerow(["1001", "42000.00", "0.01000000", "420.00", "1704067200000", "True", "True"])
            writer.writerow(["1002", "42001.00", "0.02000000", "840.02", "1704067201000", "False", "True"])
            writer.writerow(["1003", "", "0.03000000", "1260.03", "1704067202000", "False", "True"])
            writer.writerow(["1004", "42003.00", "0.00000000", "0.00", "1704067203000", "False", "True"])
            writer.writerow(["1005", "42004.00", "0.04000000", "1680.16", "1704067204000", "Maybe", "True"])
            writer.writerow([])

        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.write(csv_path, arcname="BTCUSDT-trades-2024-01.csv")

        audit_path = temp_dir / "BTCUSDT-trades-2024-01.audit.json"
        report = audit_binance_trade_zip(zip_path, audit_path=audit_path, market="BTC-USDT")

        self.assertEqual(report["total_rows"], 7)
        self.assertEqual(report["valid_rows"], 2)
        self.assertEqual(report["duplicate_trade_ids"], 1)
        self.assertEqual(report["malformed_rows"], 2)
        self.assertEqual(report["invalid_prices"], 1)
        self.assertEqual(report["invalid_quantities"], 1)
        self.assertEqual(report["invalid_boolean_values"], 1)
        self.assertEqual(report["first_trade_id"], "1001")
        self.assertEqual(report["last_trade_id"], "1005")
        self.assertTrue(audit_path.exists())
        with audit_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["valid_rows"], report["valid_rows"])

    def test_streaming_canonicalization_writes_jsonl_without_loading_zip(self):
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "BTCUSDT-trades-2024-01.zip"
        csv_path = temp_dir / "BTCUSDT-trades-2024-01.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["trade Id", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])
            writer.writerow(["1001", "42000.00", "0.01000000", "420.00", "1704067200000", "True", "True"])
            writer.writerow(["1001", "42000.00", "0.01000000", "420.00", "1704067200000", "True", "True"])
            writer.writerow(["1002", "42001.00", "0.02000000", "840.02", "1704067201000", "False", "True"])
            writer.writerow(["1003", "42002.00", "0.03000000", "1260.06", "1704067202000", "Maybe", "True"])

        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.write(csv_path, arcname="BTCUSDT-trades-2024-01.csv")

        canonical_path = temp_dir / "BTCUSDT-trades-2024-01-canonical.jsonl"
        report = canonicalize_binance_trade_zip(zip_path, output_path=canonical_path, market="BTC-USDT")

        self.assertEqual(report["total_rows"], 4)
        self.assertEqual(report["valid_rows"], 2)
        self.assertEqual(report["duplicate_trade_ids"], 1)
        self.assertEqual(report["canonicalization_status"], "SUCCESS")
        self.assertTrue(report["canonical_sha256"])
        self.assertTrue(canonical_path.exists())

        lines = canonical_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        first_event = json.loads(lines[0])
        second_event = json.loads(lines[1])
        self.assertEqual(first_event["trade_id"], "1001")
        self.assertEqual(second_event["trade_id"], "1002")
