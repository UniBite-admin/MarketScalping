import csv
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tmp_binance_pipeline import build_end_to_end_report


class TmpBinancePipelineTests(unittest.TestCase):
    def test_end_to_end_pipeline_writes_audit_canonical_manifest_and_repeat_check(self):
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "BTCUSDT-trades-2024-01.zip"
        csv_path = temp_dir / "BTCUSDT-trades-2024-01.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["trade Id", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])
            writer.writerow(["1001", "42000.00", "0.01000000", "420.00", "1704067200000", "True", "True"])
            writer.writerow(["1002", "42010.00", "0.02000000", "840.20", "1704067201000", "False", "True"])

        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.write(csv_path, arcname="BTCUSDT-trades-2024-01.csv")

        checksum_path = temp_dir / "BTCUSDT-trades-2024-01.zip.CHECKSUM"
        checksum_path.write_text(
            f"{hashlib.sha256(zip_path.read_bytes()).hexdigest()}  BTCUSDT-trades-2024-01.zip\n",
            encoding="utf-8",
        )

        audit_path = temp_dir / "audit.json"
        canonical_path = temp_dir / "canonical.jsonl"
        manifest_path = temp_dir / "manifest.json"

        report = build_end_to_end_report(
            zip_path,
            canonical_path=canonical_path,
            audit_path=audit_path,
            manifest_path=manifest_path,
            limit=None,
            initial_capital=1000.0,
            checksum_path=checksum_path,
            repeat_check=True,
        )

        self.assertEqual(report["source_archive"]["status"], "VERIFIED")
        self.assertEqual(report["audit"]["valid_rows"], 2)
        self.assertEqual(report["canonical"]["valid_rows"], 2)
        self.assertTrue(audit_path.exists())
        self.assertTrue(canonical_path.exists())
        self.assertTrue(manifest_path.exists())
        self.assertEqual(report["manifest"]["canonicalization_status"], "SUCCESS")
        self.assertEqual(report["manifest"]["validation_status"], "PASS")
        self.assertTrue(report["determinism"]["matches"])
        self.assertTrue(report["determinism"]["backtest_run_id_match"])

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["canonical_sha256"], report["canonical"]["canonical_sha256"])
        self.assertEqual(manifest["source_sha256"], report["source_archive"]["actual_sha256"])