"""Deterministic QA Agent executor for the MarketScalping workflow.

Design constraints:
- This is a verification-only agent.
- No live-market activation, credential access, deployment, or workflow transition logic.
- Works with the existing AgentRuntime / InvocationRequest / AgentResult interfaces.
- Keeps the canonical vocabulary established by the agent contract and workflow.
"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.agent_runtime import AgentExecutor, AgentResult, InvocationRequest

VALID_DECISIONS = {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
VALID_EVIDENCE_RESULTS = {"CLAIM", "VERIFIED", "DERIVED", "MISSING", "INCONCLUSIVE"}
VALID_BLOCKING_STATUS = {"blocking", "non_blocking", "requires_architect_review"}


class QAExecutor(AgentExecutor):
    """Minimal deterministic QA verifier.

    The executor validates the required canonical inputs, independently checks the
    supplied implementation and test evidence, and produces structured QA outputs.
    It never modifies Developer code or the architecture documents.
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
            "run_id",
        ]
        for key in required:
            if key not in spec:
                raise ValueError(f"missing required QA input: {key}")

        task_record = spec.get("task_record")
        if not isinstance(task_record, dict):
            raise ValueError("task_record required")
        if task_record.get("task_id") != req.task_id:
            raise ValueError("task identity mismatch")
        if not task_record.get("authorized", False):
            raise ValueError("task_record not authorized")

        architecture_result = spec.get("architecture_result")
        if not isinstance(architecture_result, dict):
            raise ValueError("architecture_result required")

        repository_context = spec.get("repository_context")
        if not isinstance(repository_context, dict):
            raise ValueError("repository_context required")

        repository_revision = spec.get("repository_revision")
        if not repository_revision:
            raise ValueError("repository_revision required")
        if str(repository_revision) != str(req.repository_revision):
            raise ValueError("repository revision mismatch")

        implementation_artifact = spec.get("implementation_artifact")
        if not isinstance(implementation_artifact, dict):
            raise ValueError("implementation_artifact required")

        test_manifest = spec.get("test_manifest")
        if not isinstance(test_manifest, dict):
            raise ValueError("test_manifest required")

        run_id = spec.get("run_id") or req.run_id
        if not run_id:
            raise ValueError("run_id required")

        # Security boundary: QA never receives or authorizes live-trading capabilities.
        forbidden = [
            "live_credentials",
            "cash_exit_capability",
            "market_activation_switch",
            "order_entry",
            "capital_release_toggle",
            "budget_limit_override",
            "release_target",
            "merge_guard_bypass",
        ]
        flat = str(spec).lower()
        for token in forbidden:
            if token in flat:
                raise ValueError("unsafe or unauthorized QA input")

    def _evidence_entry(self, source: str, check: str, result: str, details: Any) -> Dict[str, Any]:
        if result not in VALID_EVIDENCE_RESULTS:
            raise ValueError(f"invalid evidence result: {result}")
        return {
            "source": source,
            "check": check,
            "result": result,
            "details": details,
        }

    def _check_task_authorization(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = []
        task_record = spec.get("task_record") or {}
        checks.append(self._evidence_entry(
            "task_record",
            "task_authorized",
            "VERIFIED" if task_record.get("authorized") else "CLAIM",
            task_record.get("task_id") if task_record.get("task_id") else "missing task_id",
        ))
        return checks

    def _check_architecture_alignment(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = []
        arch = spec.get("architecture_result") or {}
        impl = spec.get("implementation_artifact") or {}
        changed_files = (impl.get("content") or {}).get("changed_files", [])
        affected = arch.get("affected_components") or []
        if changed_files and affected:
            overlap = [item for item in changed_files if item in affected]
            result = "VERIFIED" if overlap else "CLAIM"
            details = {"changed_files": changed_files, "affected_components": affected}
        else:
            result = "INCONCLUSIVE"
            details = {"changed_files": changed_files, "affected_components": affected}
        checks.append(self._evidence_entry("architecture_result", "architecture_alignment", result, details))
        return checks

    def _check_scope(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = []
        impl = spec.get("implementation_artifact") or {}
        content = impl.get("content") or {}
        changed_files = content.get("changed_files") or []
        scope = spec.get("task_record", {}).get("scope") or []
        scope_allowed = bool(not scope or all(file in changed_files for file in scope))
        checks.append(self._evidence_entry(
            "implementation_artifact",
            "scope_consistency",
            "VERIFIED" if scope_allowed else "CLAIM",
            {"scope": scope, "changed_files": changed_files},
        ))
        return checks

    def _check_test_manifest(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = []
        manifest = spec.get("test_manifest") or {}
        content = manifest.get("content") or {}
        results = content.get("results") or []
        status = content.get("verification_status") or "UNKNOWN"
        if results:
            any_failed = any((item.get("status") or "").upper() == "FAILED" for item in results)
            result = "VERIFIED" if not any_failed else "CLAIM"
            details = {"status": status, "results": results}
        else:
            result = "INCONCLUSIVE"
            details = {"status": status, "results": results}
        checks.append(self._evidence_entry("test_manifest", "test_manifest_consistency", result, details))
        return checks

    def _check_safety_sensitive(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = []
        impl = spec.get("implementation_artifact") or {}
        content = impl.get("content") or {}
        changed_files = content.get("changed_files") or []
        risky = [
            "risk_engine.py",
            "execution_engine.py",
            "accounting_engine.py",
            "position_manager.py",
        ]
        touched_risky = [item for item in changed_files if item in risky]
        checks.append(self._evidence_entry(
            "implementation_artifact",
            "safety_sensitive_change",
            "VERIFIED" if bool(touched_risky) else "DERIVED",
            {"touched_risky_components": touched_risky},
        ))
        return checks

    def _make_defect(self, defect_id: str, severity: str, category: str, description: str,
                    evidence: str, affected_area: str, blocking: bool, expected_behavior: str = "",
                    observed_behavior: str = "", verification_info: str = "") -> Dict[str, Any]:
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"invalid defect severity: {severity}")
        if isinstance(blocking, bool):
            blocking_status = "blocking" if blocking else "non_blocking"
        else:
            blocking_status = blocking
        if blocking_status not in VALID_BLOCKING_STATUS:
            raise ValueError(f"invalid blocking status: {blocking_status}")
        return {
            "defect_id": defect_id,
            "severity": severity,
            "category": category,
            "description": description,
            "affected_area": affected_area,
            "evidence": evidence,
            "expected_behavior": expected_behavior or "No violation is expected.",
            "observed_behavior": observed_behavior or description,
            "verification_info": verification_info or evidence,
            "blocking_status": blocking_status,
        }

    def _evaluate(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        evidence = []
        defects: List[Dict[str, Any]] = []
        checks = []

        checks.extend(self._check_task_authorization(spec))
        checks.extend(self._check_architecture_alignment(spec))
        checks.extend(self._check_scope(spec))
        checks.extend(self._check_test_manifest(spec))
        checks.extend(self._check_safety_sensitive(spec))

        evidence.extend(checks)

        task_record = spec.get("task_record") or {}
        impl = spec.get("implementation_artifact") or {}
        content = impl.get("content") or {}
        changed_files = content.get("changed_files") or []
        manifest = spec.get("test_manifest") or {}
        manifest_results = (manifest.get("content") or {}).get("results") or []
        verification_status = (manifest.get("content") or {}).get("verification_status") or "UNKNOWN"

        if not task_record.get("authorized", False):
            defects.append(self._make_defect(
                "QA-001",
                "CRITICAL",
                "authorization",
                "Task is not authorized for verification.",
                "task_record.authorized is false.",
                "task_record",
                True,
                expected_behavior="QA verification requires an authorized task_record.",
                observed_behavior="task_record.authorized is false.",
                verification_info="task_record authorization check",
            ))

        if not impl or not isinstance(impl, dict):
            defects.append(self._make_defect(
                "QA-002",
                "CRITICAL",
                "missing_input",
                "implementation_artifact is missing or invalid.",
                "implementation_artifact missing from input set.",
                "implementation_artifact",
                True,
                expected_behavior="A valid implementation_artifact is required.",
                observed_behavior="implementation_artifact absent or invalid.",
                verification_info="implementation_artifact validation",
            ))

        if not manifest or not manifest_results:
            defects.append(self._make_defect(
                "QA-003",
                "HIGH",
                "missing_evidence",
                "test_manifest contains no evidence to assess the implementation.",
                "test_manifest has no results entries.",
                "test_manifest",
                False,
                expected_behavior="Evidence-bearing test_manifest is required.",
                observed_behavior="test_manifest lacks executed result entries.",
                verification_info="test_manifest evidence check",
            ))

        if verification_status.upper() == "FAILED":
            defects.append(self._make_defect(
                "QA-004",
                "HIGH",
                "test_failure",
                "The provided test evidence reports failing checks.",
                "test_manifest verification_status is FAILED.",
                "test_manifest",
                True,
                expected_behavior="Verification should reach a passing or inconclusive state with valid evidence.",
                observed_behavior="test_manifest verification_status is FAILED.",
                verification_info="test_manifest verification_status",
            ))

        if task_record.get("task_id") != spec.get("task_record", {}).get("task_id"):
            defects.append(self._make_defect(
                "QA-005",
                "CRITICAL",
                "task_identity",
                "Task identity mismatch was detected.",
                "task_record.task_id does not match the runtime task_id.",
                "task_record",
                True,
                expected_behavior="Runtime task_id and task_record.task_id must match.",
                observed_behavior="task_record.task_id differs from the runtime task_id.",
                verification_info="task identity validation",
            ))

        architecture_result = spec.get("architecture_result") or {}
        architecture_assessment = architecture_result.get("architecture_assessment") or {}
        architecture_summary = str(architecture_assessment.get("summary") or "")
        affected_components = architecture_result.get("affected_components") or []
        if affected_components and changed_files:
            overlap = set(str(item) for item in changed_files).intersection(str(item) for item in affected_components)
            if not overlap:
                defects.append(self._make_defect(
                    "QA-006",
                    "MEDIUM",
                    "architecture_drift",
                    "Implementation appears to drift from the architecture assessment.",
                    "architecture_result and implementation_artifact disagree on the affected area.",
                    "architecture_result",
                    False,
                    expected_behavior="Implementation should remain aligned with architecture_result.affected_components.",
                    observed_behavior="Changed files do not overlap with the architecture-identified affected components.",
                    verification_info="architecture alignment check",
                ))
        elif architecture_summary and "risk" in architecture_summary.lower() and any("risk_engine" in str(item) for item in changed_files):
            defects.append(self._make_defect(
                "QA-006",
                "MEDIUM",
                "architecture_drift",
                "Implementation appears to drift from the architecture assessment.",
                "architecture_result and implementation_artifact disagree on the affected area.",
                "architecture_result",
                False,
                expected_behavior="Risk-sensitive implementation should match the architecture assessment.",
                observed_behavior="risk summary indicates a safety-sensitive area while changed files are inconsistent with the architecture-result mapping.",
                verification_info="architecture alignment check",
            ))

        if any("risk_engine.py" in str(item) for item in changed_files):
            defects.append(self._make_defect(
                "QA-007",
                "HIGH",
                "safety_sensitive_change",
                "Safety-sensitive components changed and must be reviewed by Safety.",
                "implementation_artifact touched risk_engine.py.",
                "risk_engine.py",
                False,
                expected_behavior="Safety-sensitive changes require explicit safety review and should not bypass the workflow.",
                observed_behavior="The implementation changed a safety-sensitive component without a qualifying safety review signal.",
                verification_info="safety-sensitive file check",
            ))

        if spec.get("developer_claims") and isinstance(spec.get("developer_claims"), dict):
            summary = spec["developer_claims"].get("summary")
            if summary and isinstance(summary, str):
                evidence.append(self._evidence_entry(
                    "developer_claim",
                    "claim_vs_verified_evidence",
                    "CLAIM",
                    {"claim": summary},
                ))

        # Determine QA decision.
        # Non-blocking advisory findings (such as safety-sensitive review signals)
        # must not fail an otherwise valid verification result.
        blocking_prereq_categories = {"authorization", "missing_input", "missing_evidence"}
        blocking_categories = {"authorization", "missing_input", "missing_evidence", "test_failure", "task_identity", "architecture_drift"}
        if defects and any(d.get("blocking") and d.get("category") in blocking_prereq_categories for d in defects):
            decision = "BLOCKED"
        elif defects and any(d.get("blocking") and d.get("category") in blocking_categories for d in defects):
            decision = "FAIL"
        elif defects and any(d.get("blocking") for d in defects):
            decision = "FAIL"
        elif defects and any(d.get("category") == "safety_sensitive_change" for d in defects):
            decision = "PASS"
        elif defects:
            decision = "FAIL"
        elif any(item.get("result") == "INCONCLUSIVE" for item in evidence):
            decision = "INCONCLUSIVE"
        else:
            decision = "PASS"

        return {
            "decision": decision,
            "checks": checks,
            "evidence": evidence,
            "defects": defects,
            "summary": self._summary(decision, defects, checks),
        }

    def _summary(self, decision: str, defects: List[Dict[str, Any]], checks: List[Dict[str, Any]]) -> str:
        if decision == "PASS":
            return "Evidence is sufficient and no blocking defect was found."
        if decision == "FAIL":
            if any(d.get("category") == "architecture_drift" for d in defects):
                return "QA found architecture_drift and other defects requiring corrective action."
            return f"QA found {len(defects)} defect(s) requiring corrective action."
        if decision == "BLOCKED":
            return "QA cannot safely complete verification because required inputs or authorization are missing or blocked."
        return "Available evidence is insufficient to establish PASS or FAIL with confidence."

    def execute(self, req: InvocationRequest) -> AgentResult:
        try:
            task_spec = self._task_spec(req)
            self._validate_required_inputs(req, task_spec)
            evaluation = self._evaluate(task_spec)

            evidence_references = [
                f"{item.get('source')}:{item.get('check')}" for item in evaluation["evidence"]
            ]
            limitations = []
            if any(item.get("result") == "INCONCLUSIVE" for item in evaluation["evidence"]):
                limitations.append("Available evidence is not sufficient to establish a confident PASS determination.")
            if any(item.get("result") == "MISSING" for item in evaluation["evidence"]):
                limitations.append("Required evidence is absent for at least one verification step.")
            safety_findings = []
            for defect in evaluation["defects"]:
                if defect.get("category") == "safety_sensitive_change":
                    safety_findings.append(defect.get("description", "Safety-sensitive change requires review."))
            qa_result = {
                "artifact_id": str(uuid.uuid4()),
                "artifact_type": "qa_result",
                "task_id": req.task_id,
                "run_id": req.run_id or task_spec.get("run_id"),
                "repository_revision": req.repository_revision,
                "producer": "qa",
                "created_at": self._now(),
                "content": {
                    "task_id": req.task_id,
                    "run_id": req.run_id or task_spec.get("run_id"),
                    "repository_revision": req.repository_revision,
                    "decision": evaluation["decision"],
                    "verification_summary": evaluation["summary"],
                    "evidence_references": evidence_references,
                    "defects": evaluation["defects"],
                    "limitations": limitations,
                    "safety_relevant_findings": safety_findings,
                    "checks": evaluation["checks"],
                    "evidence": evaluation["evidence"],
                },
            }

            defect_report = {
                "artifact_id": str(uuid.uuid4()),
                "artifact_type": "defect_report",
                "task_id": req.task_id,
                "run_id": req.run_id or task_spec.get("run_id"),
                "repository_revision": req.repository_revision,
                "producer": "qa",
                "created_at": self._now(),
                "content": {
                    "task_id": req.task_id,
                    "run_id": req.run_id or task_spec.get("run_id"),
                    "repository_revision": req.repository_revision,
                    "defects": evaluation["defects"],
                    "verification_summary": evaluation["summary"],
                },
            }

            result = AgentResult(
                task_id=req.task_id,
                agent_role="QA",
                run_id=req.run_id or task_spec.get("run_id"),
                status="SUCCEEDED",
                started_at=self._now(),
                completed_at=self._now(),
                changed_files=[],
                output_artifacts=[qa_result, defect_report],
                proposed_next_state="SAFETY",
                execution_metadata={
                    "repository_revision": req.repository_revision,
                    "worktree": req.worktree,
                    "attempt": req.attempt,
                    "decision": evaluation["decision"],
                },
            )
            return result
        except Exception as exc:
            error = {"type": exc.__class__.__name__, "message": str(exc)}
            qa_result = {
                "artifact_id": str(uuid.uuid4()),
                "artifact_type": "qa_result",
                "task_id": req.task_id,
                "run_id": req.run_id or "unknown",
                "repository_revision": req.repository_revision,
                "producer": "qa",
                "created_at": self._now(),
                "content": {
                    "decision": "BLOCKED",
                    "task_id": req.task_id,
                    "run_id": req.run_id or "unknown",
                    "repository_revision": req.repository_revision,
                    "checks": [],
                    "evidence": [{"source": "qa_execution", "check": "qa_validation", "result": "CLAIM", "details": {"error": error}}],
                    "defects": [],
                    "summary": f"QA validation could not complete: {error}",
                },
            }
            defect_report = {
                "artifact_id": str(uuid.uuid4()),
                "artifact_type": "defect_report",
                "task_id": req.task_id,
                "run_id": req.run_id or "unknown",
                "repository_revision": req.repository_revision,
                "producer": "qa",
                "created_at": self._now(),
                "content": {
                    "task_id": req.task_id,
                    "run_id": req.run_id or "unknown",
                    "repository_revision": req.repository_revision,
                    "defects": [],
                    "summary": f"QA validation could not complete: {error}",
                },
            }
            return AgentResult(
                task_id=req.task_id,
                agent_role="QA",
                run_id=req.run_id or "unknown",
                status="BLOCKED",
                started_at=self._now(),
                completed_at=self._now(),
                changed_files=[],
                output_artifacts=[qa_result, defect_report],
                error=error,
                execution_metadata={
                    "repository_revision": req.repository_revision,
                    "worktree": req.worktree,
                    "attempt": req.attempt,
                },
            )


__all__ = ["QAExecutor"]
