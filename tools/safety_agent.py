"""Deterministic Safety Agent executor for the MarketScalping workflow.

This agent performs independent local safety verification using only the canonical
inputs already defined by the active contract and design. It never reaches into
live systems, credentials, or the trading stack.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.agent_runtime import AgentExecutor, AgentResult, InvocationRequest

VALID_DECISIONS = {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE", "REQUIRE_HUMAN_APPROVAL"}
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
VALID_BLOCKING_STATUS = {"blocking", "non_blocking", "requires_human_approval"}


class SafetyExecutor(AgentExecutor):
    """Minimal deterministic Safety verifier.

    It validates the minimal Safety input set, checks for common safety hazards,
    and returns a canonical `safety_result` artifact. It remains read-only and
    deterministic; it never mutates workflow state or grants approval.
    """

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _task_spec(self, req: InvocationRequest) -> Dict[str, Any]:
        task_spec = req.task_spec or {}
        if not isinstance(task_spec, dict):
            raise ValueError("task_spec must be an object")
        return task_spec

    def _validate_required_inputs(self, req: InvocationRequest, spec: Dict[str, Any]) -> None:
        required = [
            "task_record",
            "architecture_result",
            "repository_context",
            "repository_revision",
            "implementation_artifact",
            "test_manifest",
            "qa_result",
            "run_id",
        ]
        for key in required:
            if key not in spec:
                raise ValueError(f"missing required Safety input: {key}")

        if not isinstance(spec.get("task_record"), dict):
            raise ValueError("task_record required")
        task_record = spec.get("task_record")
        if task_record.get("task_id") != req.task_id:
            raise ValueError("task identity mismatch")

        for key in ("architecture_result", "repository_context", "implementation_artifact", "test_manifest", "qa_result"):
            if not isinstance(spec.get(key), dict):
                raise ValueError(f"{key} required")

        if str(spec.get("repository_revision") or "") != str(req.repository_revision):
            raise ValueError("repository revision mismatch")

        forbidden = [
            "live_credentials",
            "withdrawal",
            "place_order",
            "market_activation_switch",
            "risk_limit_override",
            "merge_guard_bypass",
            "live_trading_enablement",
            "capital_release_toggle",
        ]
        flat = str(spec).lower()
        for token in forbidden:
            if token in flat:
                raise ValueError("unsafe or unauthorized Safety input")

    def _evidence(self, source: str, check: str, result: str, details: Any) -> Dict[str, Any]:
        if result not in {"CLAIM", "VERIFIED", "DERIVED", "MISSING", "INCONCLUSIVE"}:
            raise ValueError(f"invalid evidence result: {result}")
        return {"source": source, "check": check, "result": result, "details": details}

    def _derive_risk(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []
        impl = spec.get("implementation_artifact", {})
        content = impl.get("content") if isinstance(impl.get("content"), dict) else {}
        changed_files = content.get("changed_files") or []
        risky = ["risk_engine.py", "execution_engine.py", "accounting_engine.py", "position_manager.py"]
        touched_risky = [f for f in changed_files if f in risky]

        if touched_risky:
            evidence.append(self._evidence("implementation_artifact", "safety_sensitive_change", "VERIFIED", {"changed_files": touched_risky}))
        else:
            evidence.append(self._evidence("implementation_artifact", "safety_sensitive_change", "DERIVED", {"changed_files": changed_files}))

        qa = spec.get("qa_result", {})
        qa_content = qa.get("content") if isinstance(qa.get("content"), dict) else {}
        decision = str(qa_content.get("decision") or "").upper()
        if decision in {"FAIL", "BLOCKED", "INCONCLUSIVE"}:
            evidence.append(self._evidence("qa_result", "qa_gate_status", "VERIFIED", {"decision": decision}))
        elif decision == "PASS":
            evidence.append(self._evidence("qa_result", "qa_gate_status", "CLAIM", {"decision": decision}))
        else:
            evidence.append(self._evidence("qa_result", "qa_gate_status", "INCONCLUSIVE", {"decision": decision}))

        return evidence

    def _evaluate(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        evidence = self._derive_risk(spec)

        qa = spec.get("qa_result", {})
        qa_content = qa.get("content") if isinstance(qa.get("content"), dict) else {}
        qa_decision = str(qa_content.get("decision") or "").upper()

        impl = spec.get("implementation_artifact", {})
        impl_content = impl.get("content") if isinstance(impl.get("content"), dict) else {}
        changed_files = impl_content.get("changed_files") or []

        risky = ["risk_engine.py", "execution_engine.py", "accounting_engine.py", "position_manager.py"]
        touched_risky = [f for f in changed_files if f in risky]

        findings: List[Dict[str, Any]] = []
        blocking_status = "non_blocking"
        requires_human_approval = False
        decision = "PASS"
        severity = "LOW"

        if qa_decision in {"FAIL", "BLOCKED", "INCONCLUSIVE"}:
            finding = {
                "finding_id": str(uuid.uuid4()),
                "severity": "HIGH",
                "category": "verification_gate",
                "summary": "QA verification is not a clean pass; Safety cannot grant release approval.",
                "evidence": qa_decision,
                "recommendation": "Fix the QA findings or block the work item.",
            }
            findings.append(finding)
            decision = "BLOCKED"
            blocking_status = "blocking"
            severity = "HIGH"

        if touched_risky:
            finding = {
                "finding_id": str(uuid.uuid4()),
                "severity": "HIGH",
                "category": "risk_sensitive_change",
                "summary": "Risk-sensitive components changed; additional human review is required before release.",
                "evidence": touched_risky,
                "recommendation": "Require human approval and review the risk/execution/accounting impact before proceeding.",
            }
            findings.append(finding)
            requires_human_approval = True
            if decision == "PASS":
                decision = "REQUIRE_HUMAN_APPROVAL"
                severity = "HIGH"
                blocking_status = "requires_human_approval"

        if not touched_risky and qa_decision == "PASS":
            decision = "PASS"
            severity = "LOW"
            blocking_status = "non_blocking"

        # Conservative safety default: if we saw no evidence of violations but the task impacts risk-sensitive components, keep it gated.
        if decision == "REQUIRE_HUMAN_APPROVAL":
            requires_human_approval = True

        return {
            "decision": decision,
            "severity": severity,
            "evidence": evidence,
            "findings": findings,
            "blocking_status": blocking_status,
            "limitations": ["Local deterministic review only; no live market or exchange access."],
            "recommended_mitigations": [
                "Review risk sensitivity and ensure the change is covered by tests and safety review.",
                "Confirm explicit human approval before enabling live behavior or modifying risk limits.",
            ],
            "requires_human_approval": requires_human_approval,
        }

    def execute(self, req: InvocationRequest) -> AgentResult:
        try:
            spec = self._task_spec(req)
            self._validate_required_inputs(req, spec)
            result = self._evaluate(spec)
            safety_result = {
                "artifact_id": str(uuid.uuid4()),
                "artifact_type": "safety_result",
                "task_id": req.task_id,
                "run_id": req.run_id,
                "repository_revision": req.repository_revision,
                "producer": "safety",
                "created_at": self._now(),
                "content": {
                    "task_id": req.task_id,
                    "run_id": req.run_id,
                    "repository_revision": req.repository_revision,
                    "decision": result["decision"],
                    "severity": result["severity"],
                    "evidence": result["evidence"],
                    "findings": result["findings"],
                    "blocking_status": result["blocking_status"],
                    "limitations": result["limitations"],
                    "recommended_mitigations": result["recommended_mitigations"],
                    "requires_human_approval": result["requires_human_approval"],
                },
            }
            return AgentResult(
                task_id=req.task_id,
                agent_role="SAFETY",
                run_id=req.run_id or str(uuid.uuid4()),
                status="SUCCEEDED",
                started_at=self._now(),
                completed_at=self._now(),
                changed_files=[],
                output_artifacts=[safety_result],
                proposed_next_state="HUMAN_APPROVAL" if result["requires_human_approval"] else "MERGE",
                execution_metadata={
                    "repository_revision": req.repository_revision,
                    "worktree": req.worktree,
                    "attempt": req.attempt,
                    "decision": result["decision"],
                },
            )
        except Exception as exc:  # pragma: no cover - structured failure reporting
            err = {"type": exc.__class__.__name__, "message": str(exc)}
            return AgentResult(
                task_id=req.task_id,
                agent_role="SAFETY",
                run_id=req.run_id or str(uuid.uuid4()),
                status="BLOCKED",
                started_at=self._now(),
                completed_at=self._now(),
                changed_files=[],
                output_artifacts=[],
                error=err,
                execution_metadata={
                    "repository_revision": req.repository_revision,
                    "worktree": req.worktree,
                    "attempt": req.attempt,
                },
            )


__all__ = ["SafetyExecutor"]
