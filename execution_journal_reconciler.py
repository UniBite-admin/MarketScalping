from __future__ import annotations

import csv
import os
from typing import Any


class ExecutionJournalReconciler:
    SAFE_ACTIONS = {"SKIPPED", "FAILED", "NO_ACTION"}
    FINANCIALLY_RELEVANT_ACTIONS = {"SIMULATED_ORDER_PREPARED"}

    @staticmethod
    def reconcile(journal_path: str | os.PathLike[str], accounting_engine: Any) -> dict[str, Any]:
        normalized_path = os.fspath(journal_path) if isinstance(journal_path, os.PathLike) else str(journal_path)
        accepted_ids = set(ExecutionJournalReconciler._accepted_ids(accounting_engine))
        ordered_accepted = sorted(accepted_ids)

        result = {
            "overall_status": "SAFE",
            "checked_journal_records": 0,
            "accepted_accounting_ids_checked": ordered_accepted,
            "unmatched_journal_ids": [],
            "missing_journal_ids": [],
            "duplicate_identities": [],
            "conflicting_identities": [],
            "malformed_records": [],
            "blocking_reason": None,
            "evidence_references": [
                {"type": "journal_file", "path": normalized_path},
                {"type": "accounting_authority", "source": "accounting_engine._processed_successful_execution_ids", "count": len(accepted_ids)},
            ],
        }

        if accounting_engine is None:
            if not normalized_path or not os.path.exists(normalized_path):
                return result
            return ExecutionJournalReconciler._finalize_block(result, "accounting_engine_missing")

        if not os.path.exists(normalized_path):
            if accepted_ids:
                result["missing_journal_ids"] = ordered_accepted
                return ExecutionJournalReconciler._finalize_block(result, "accepted_accounting_ids_without_journal_evidence")
            return result

        try:
            with open(normalized_path, "r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
        except (OSError, csv.Error, ValueError):
            if accepted_ids:
                result["missing_journal_ids"] = ordered_accepted
                return ExecutionJournalReconciler._finalize_block(result, "journal_unreadable_with_accepted_accounting_state")
            return result

        if not rows:
            if accepted_ids:
                result["missing_journal_ids"] = ordered_accepted
                return ExecutionJournalReconciler._finalize_block(result, "accepted_accounting_ids_without_journal_evidence")
            return result

        result["checked_journal_records"] = len(rows)

        seen_by_id: dict[str, dict[str, str]] = {}
        valid_ids: set[str] = set()
        duplicate_ids: set[str] = set()
        conflicting_ids: set[str] = set()
        malformed_ids: set[str] = set()
        financial_unaccepted: set[str] = set()

        for raw_row in rows:
            row = {str(k): (v if v is not None else "") for k, v in raw_row.items()}
            record_id = (row.get("execution_event_id") or "").strip()
            execution_action = (row.get("execution_action") or "").strip()

            if not record_id or not ExecutionJournalReconciler._is_well_formed_record(row):
                malformed_label = record_id or "<unknown_row>"
                result["malformed_records"].append(malformed_label)
                malformed_ids.add(malformed_label)
                continue

            valid_ids.add(record_id)

            if record_id in seen_by_id:
                if seen_by_id[record_id] == row:
                    duplicate_ids.add(record_id)
                else:
                    conflicting_ids.add(record_id)
            else:
                seen_by_id[record_id] = row

            if execution_action in ExecutionJournalReconciler.FINANCIALLY_RELEVANT_ACTIONS and record_id not in accepted_ids:
                financial_unaccepted.add(record_id)

        result["duplicate_identities"] = sorted(duplicate_ids)
        result["conflicting_identities"] = sorted(conflicting_ids)
        result["malformed_records"] = sorted(dict.fromkeys(result["malformed_records"]))
        result["unmatched_journal_ids"] = sorted(valid_ids - accepted_ids)
        result["missing_journal_ids"] = sorted(accepted_ids - valid_ids)

        malformed_accepted = {record_id for record_id in malformed_ids if record_id in accepted_ids}
        if malformed_accepted:
            result["missing_journal_ids"] = sorted(set(result["missing_journal_ids"]) | malformed_accepted)

        if result["duplicate_identities"]:
            result["duplicate_identities"] = sorted(dict.fromkeys(result["duplicate_identities"]))
        if result["conflicting_identities"]:
            result["conflicting_identities"] = sorted(dict.fromkeys(result["conflicting_identities"]))

        reasons: list[str] = []
        if result["conflicting_identities"]:
            reasons.append("conflicting_duplicate_identity")
        if financial_unaccepted:
            reasons.append("SIMULATED_ORDER_PREPARED_without_accepted_accounting_id")
        if result["missing_journal_ids"]:
            reasons.append("accepted_accounting_ids_without_journal_evidence")
        if malformed_accepted:
            reasons.append("malformed_accepted_linked_record")

        if reasons:
            return ExecutionJournalReconciler._finalize_block(result, reasons[0])

        return result

    @staticmethod
    def _accepted_ids(accounting_engine: Any) -> list[str]:
        if accounting_engine is None:
            return []

        if hasattr(accounting_engine, "_processed_successful_execution_ids"):
            value = getattr(accounting_engine, "_processed_successful_execution_ids")
            if isinstance(value, set):
                return list(value)
            if isinstance(value, (list, tuple)):
                return [str(item) for item in value]

        if hasattr(accounting_engine, "processed_successful_execution_ids"):
            value = getattr(accounting_engine, "processed_successful_execution_ids")
            if isinstance(value, set):
                return list(value)
            if isinstance(value, (list, tuple)):
                return [str(item) for item in value]

        return []

    @staticmethod
    def _is_well_formed_record(row: dict[str, str]) -> bool:
        required = [
            "execution_event_id",
            "timestamp_utc",
            "market",
            "strategy_action",
            "risk_action",
            "execution_action",
            "reason",
            "signal_strength",
            "spread_pct",
        ]
        if not all(key in row for key in required):
            return False

        execution_event_id = (row.get("execution_event_id") or "").strip()
        if not execution_event_id:
            return False

        execution_action = (row.get("execution_action") or "").strip()
        if execution_action not in {"SKIPPED", "FAILED", "NO_ACTION", "SIMULATED_ORDER_PREPARED"}:
            return False

        timestamp_utc = (row.get("timestamp_utc") or "").strip()
        try:
            from datetime import datetime

            if timestamp_utc:
                datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
        except ValueError:
            return False

        try:
            float(row.get("signal_strength") or 0.0)
            float(row.get("spread_pct") or 0.0)
        except ValueError:
            return False

        return True

    @staticmethod
    def _finalize_block(result: dict[str, Any], reason: str) -> dict[str, Any]:
        result["overall_status"] = "BLOCKED_ON_DIVERGENCE"
        result["blocking_reason"] = reason
        return result
