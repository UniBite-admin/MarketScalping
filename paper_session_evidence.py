from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PaperSessionEvidenceCollector:
    market: str
    data_source: str
    session_start_utc: str | None
    session_end_utc: str | None
    strategy_config: dict[str, Any]
    risk_config: dict[str, Any]
    execution_config: dict[str, Any]
    fee_config: dict[str, Any]
    spread_config: dict[str, Any]
    slippage_config: dict[str, Any]
    latency_config: dict[str, Any]
    runtime_artifacts: list[str] | None = None
    session_root_dir: str = "data/paper_sessions"
    source_kind: str = "live_runtime_session"
    paper_session_id: str | None = None
    configuration_snapshot: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.market or not self.data_source:
            raise ValueError("market and data_source are required")
        if self.source_kind not in {"live_runtime_session", "replay_session", "synthetic_fixture"}:
            raise ValueError("invalid source_kind")
        if self.source_kind == "synthetic_fixture":
            raise ValueError("synthetic fixtures are not valid operational paper session evidence")
        if not self.session_start_utc or not self.session_end_utc:
            raise ValueError("session_start_utc and session_end_utc are required")
        if not self._valid_datetime(self.session_start_utc) or not self._valid_datetime(self.session_end_utc):
            raise ValueError("session timestamps must be ISO-8601 UTC strings")
        self.runtime_artifacts = list(self.runtime_artifacts or [])
        self.configuration_snapshot = self._build_configuration_snapshot()
        if self.paper_session_id is None:
            self.paper_session_id = self._build_session_id()

    def _valid_datetime(self, value: str | None) -> bool:
        if not value:
            return False
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed.tzinfo is not None

    def _canonical_session_payload(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "data_source": self.data_source,
            "session_start_utc": self.session_start_utc,
            "session_end_utc": self.session_end_utc,
            "source_kind": self.source_kind,
            "strategy_config": self.strategy_config,
            "risk_config": self.risk_config,
            "execution_config": self.execution_config,
            "fee_config": self.fee_config,
            "spread_config": self.spread_config,
            "slippage_config": self.slippage_config,
            "latency_config": self.latency_config,
            "runtime_artifacts": sorted(self.runtime_artifacts),
        }

    def _build_configuration_snapshot(self) -> dict[str, Any]:
        snapshot = {
            "strategy_configuration": self.strategy_config,
            "risk_configuration": self.risk_config,
            "execution_configuration": self.execution_config,
            "fee_configuration": self.fee_config,
            "spread_configuration": self.spread_config,
            "slippage_configuration": self.slippage_config,
            "latency_configuration": self.latency_config,
            "configuration_identity": hashlib.sha256(
                json.dumps(
                    {
                        "strategy_configuration": self.strategy_config,
                        "risk_configuration": self.risk_config,
                        "execution_configuration": self.execution_config,
                        "fee_configuration": self.fee_config,
                        "spread_configuration": self.spread_config,
                        "slippage_configuration": self.slippage_config,
                        "latency_configuration": self.latency_config,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        }
        return snapshot

    def _require_material_configuration(self) -> None:
        required = [
            self.strategy_config,
            self.risk_config,
            self.execution_config,
            self.fee_config,
            self.spread_config,
            self.slippage_config,
            self.latency_config,
        ]
        if any(not item for item in required):
            raise ValueError("all required configuration blocks are required")

    def _build_session_id(self) -> str:
        return uuid.uuid4().hex

    def _session_root(self) -> str:
        return os.path.join(self.session_root_dir, self.paper_session_id)

    def _canonical_evidence(self, *,
        accounting_engine: Any,
        position_manager: Any,
        strategy_decisions: list[dict[str, Any]],
        risk_decisions: list[dict[str, Any]],
        execution_events: list[dict[str, Any]],
        accounting_decisions: list[dict[str, Any]],
        position_events: list[dict[str, Any]],
        data_quality_incidents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if accounting_engine is None:
            raise ValueError("accounting_engine is required")
        if getattr(accounting_engine, "recovery_status", "VALID") != "VALID":
            raise ValueError("authoritative accounting state is inconsistent")

        financial_summary = {
            "initial_balance": getattr(accounting_engine, "starting_balance", None),
            "starting_balance": getattr(accounting_engine, "starting_balance", None),
            "final_balance": getattr(accounting_engine, "available_balance", None),
            "available_balance": getattr(accounting_engine, "available_balance", None),
            "final_equity": getattr(accounting_engine, "equity", None),
            "realized_pnl": getattr(accounting_engine, "realized_pnl", None),
            "unrealized_pnl": getattr(accounting_engine, "unrealized_pnl", None),
            "fees": getattr(accounting_engine, "cumulative_fees", None),
            "cumulative_fees": getattr(accounting_engine, "cumulative_fees", None),
            "cumulative_slippage": getattr(accounting_engine, "cumulative_slippage", None),
        }

        position_summary = {
            "market": self.market,
            "derived_from": "AccountingEngine.open_position",
            "active": bool(getattr(position_manager, "_active_position", None) is not None or getattr(accounting_engine, "open_position", None) is not None),
            "trade_id": getattr(getattr(accounting_engine, "open_position", None), "trade_id", None),
            "symbol": getattr(getattr(accounting_engine, "open_position", None), "symbol", None),
            "side": getattr(getattr(accounting_engine, "open_position", None), "side", None),
            "entry_time_utc": getattr(getattr(accounting_engine, "open_position", None), "entry_timestamp_utc", None),
            "entry_price": getattr(getattr(accounting_engine, "open_position", None), "entry_price", None),
            "position_size": getattr(getattr(accounting_engine, "open_position", None), "position_size", None),
        }

        observed = {
            "market": self.market,
            "event_count": 0,
            "first_event_time_utc": self.session_start_utc,
            "last_event_time_utc": self.session_end_utc,
            "strategy_decision_count": len(strategy_decisions),
            "risk_decision_count": len(risk_decisions),
            "execution_event_count": len(execution_events),
            "accounting_decision_count": len(accounting_decisions),
            "position_event_count": len(position_events),
            "data_quality_incident_count": len(data_quality_incidents),
            "stale_data_incident_count": sum(1 for item in data_quality_incidents if "stale" in str(item).lower()),
            "disconnect_reconnect_count": 0,
            "recovery_reconciliation_count": 0,
        }

        evidence = {
            "paper_session_id": self.paper_session_id,
            "market": self.market,
            "data_source": self.data_source,
            "source_kind": self.source_kind,
            "session_start_utc": self.session_start_utc,
            "session_end_utc": self.session_end_utc,
            "observed_assumptions": observed,
            "configuration_identity": self.configuration_snapshot["configuration_identity"],
            "strategy_configuration": self.strategy_config,
            "risk_configuration": self.risk_config,
            "execution_configuration": self.execution_config,
            "fee_configuration": self.fee_config,
            "spread_configuration": self.spread_config,
            "slippage_configuration": self.slippage_config,
            "latency_configuration": self.latency_config,
            "initial_balance": financial_summary["initial_balance"],
            "final_balance": financial_summary["final_balance"],
            "final_equity": financial_summary["final_equity"],
            "realized_pnl": financial_summary["realized_pnl"],
            "unrealized_pnl": financial_summary["unrealized_pnl"],
            "fees": financial_summary["fees"],
            "financial_summary": financial_summary,
            "position_summary": position_summary,
            "strategy_decisions": strategy_decisions,
            "risk_decisions": risk_decisions,
            "execution_events": execution_events,
            "accounting_decisions": accounting_decisions,
            "position_events": position_events,
            "data_quality_incidents": data_quality_incidents,
            "evidence_lineage": {
                "runtime_artifacts": list(self.runtime_artifacts),
                "session_root_dir": self._session_root(),
                "derived_from": [
                    "MarketDataEngine",
                    "StrategyEngine",
                    "RiskEngine",
                    "ExecutionEngine",
                    "AccountingEngine",
                    "PositionManager",
                    "paper_backtest_comparator",
                ],
            },
            "authority_boundary": "read_only_evidence",
            "deterministic": True,
            "paper_result_semantics": {
                "operational_raw_evidence": "runtime-generated event outputs and logs",
                "derived_paper_result_summary": "evidence bundle assembled for comparison",
                "backtest_result": "historical backtest artifact",
                "comparison_result": "read-only comparison of paper_result and backtest_result",
            },
            "status": "VALID",
        }
        return evidence

    def _serialize_canonical(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def finalize(
        self,
        *,
        accounting_engine: Any,
        position_manager: Any,
        strategy_decisions: list[dict[str, Any]],
        risk_decisions: list[dict[str, Any]],
        execution_events: list[dict[str, Any]],
        accounting_decisions: list[dict[str, Any]],
        position_events: list[dict[str, Any]],
        data_quality_incidents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.session_start_utc or not self.session_end_utc:
            raise ValueError("session boundaries are required")
        if accounting_engine is None:
            raise ValueError("accounting_engine is required")
        if getattr(accounting_engine, "recovery_status", "VALID") != "VALID":
            raise ValueError("authoritative accounting state is inconsistent")
        self._require_material_configuration()
        if not self.configuration_snapshot.get("configuration_identity"):
            raise ValueError("required configuration identity is missing")

        evidence = self._canonical_evidence(
            accounting_engine=accounting_engine,
            position_manager=position_manager,
            strategy_decisions=strategy_decisions,
            risk_decisions=risk_decisions,
            execution_events=execution_events,
            accounting_decisions=accounting_decisions,
            position_events=position_events,
            data_quality_incidents=data_quality_incidents,
        )

        evidence["evidence_signature"] = hashlib.sha256(
            self._serialize_canonical(evidence).encode("utf-8")
        ).hexdigest()

        session_dir = self._session_root()
        os.makedirs(session_dir, exist_ok=True)
        artifact_path = os.path.join(session_dir, "paper_result.json")
        with open(artifact_path, "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, sort_keys=True, indent=2)
            handle.write("\n")

        return {
            "paper_session_id": self.paper_session_id,
            "paper_result": evidence,
            "artifact_path": artifact_path,
            "session_root_dir": session_dir,
        }


__all__ = ["PaperSessionEvidenceCollector"]
