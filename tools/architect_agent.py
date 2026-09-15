"""Architect Agent Executor implementation (local, deterministic, mock reasoning).

This executor is compatible with `tools.agent_runtime.AgentExecutor` and intended
to run under the existing `AgentRuntime` for STEP 4B. It performs read-only
analysis of the provided `InvocationRequest` and produces a structured
architecture result as an output artifact. No external calls, no LLMs, no
side-effects.
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.agent_runtime import AgentExecutor, InvocationRequest, AgentResult


SENSITIVE_COMPONENT_FILES = {
    "risk_engine.py",
    "execution_engine.py",
    "accounting_engine.py",
    "position_manager.py",
    "market_data_engine.py",
}


@dataclass
class ArchitectureResult:
    task_id: str
    run_id: str
    agent_identity: str = "architect"
    agent_role: str = "ARCHITECT"
    repository_revision: Optional[str] = None
    architecture_assessment: Dict[str, Any] = None
    affected_components: List[str] = None
    proposed_changes: List[Dict[str, Any]] = None
    interfaces_contracts: List[Dict[str, Any]] = None
    data_flow_impact: Dict[str, Any] = None
    state_ownership_impact: Dict[str, Any] = None
    risks: List[Dict[str, Any]] = None
    safety_implications: List[Dict[str, Any]] = None
    testing_strategy: Dict[str, Any] = None
    acceptance_criteria: List[str] = None
    developer_specification: Dict[str, Any] = None
    adr_required: bool = False
    adr_reference: Optional[str] = None
    assumptions: List[str] = None
    open_questions: List[str] = None
    escalation: Optional[Dict[str, Any]] = None
    status: str = "PROPOSAL"


class ArchitectExecutor(AgentExecutor):
    """A deterministic, local Architect executor.

    It inspects `request.task_spec` for `repository_context` (required) and
    optional hints such as `target_paths` or `change_area`. It produces a
    structured ArchitectureResult and returns it as an `output_artifacts`
    entry inside an `AgentResult` so it is consumable by the Orchestrator.
    """

    def __init__(self):
        self.exec_count = 0

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _validate_input(self, req: InvocationRequest) -> None:
        if not req.task_id:
            raise ValueError("task_id required")
        # repository_context is expected to be in task_spec per contract
        ts = req.task_spec or {}
        repo_ctx = ts.get("repository_context")
        if not repo_ctx or not isinstance(repo_ctx, dict):
            raise ValueError("task_spec.repository_context required and must be an object")

    def _detect_affected(self, req: InvocationRequest) -> List[str]:
        ts = req.task_spec or {}
        repo = ts.get("repository_context", {})
        file_list = repo.get("file_list") or repo.get("files") or []
        targets = []

        def add_if_present(candidate):
            if not candidate:
                return
            if candidate in file_list:
                targets.append(candidate)
                return
            base = os.path.basename(str(candidate))
            if base in file_list:
                targets.append(base)

        roadmap_stage = ts.get("roadmap_stage") or {}
        stage_id = str(ts.get("roadmap_stage_id") or ts.get("roadmap_child_stage_id") or "").strip()
        stage_title = str(roadmap_stage.get("title") or ts.get("roadmap_child_stage_title") or "").lower()
        stage_description = str(roadmap_stage.get("description") or ts.get("roadmap_child_stage_description") or "").lower()
        required_evidence = roadmap_stage.get("required_evidence") or ts.get("roadmap_required_evidence") or []
        if isinstance(required_evidence, str):
            required_evidence = [required_evidence]
        required_evidence_text = " ".join(str(item) for item in required_evidence).lower()

        # stage-aware repository-grounded investigation. This is intentionally specific
        # to the roadmap stage semantics and only resolves against files already present
        # in repository_context.file_list.
        stage_hints = stage_title + " " + stage_description + " " + required_evidence_text
        if stage_id == "7.1" or any(token in stage_hints for token in ["historical data", "canonical schema", "replay", "normalized", "timestamp", "field validation"]):
            for f in [
                "market_data.py",
                "market_data_engine.py",
                "bitvavo_trade_collector.py",
                "replay_runner.py",
            ]:
                add_if_present(f)

        # direct hint
        if isinstance(ts.get("target_paths"), list):
            for p in ts.get("target_paths"):
                add_if_present(p)

        # change_area semantic hints
        if not targets and ts.get("change_area"):
            area = ts.get("change_area")
            mapping = {
                "risk": ["risk_engine.py"],
                "execution": ["execution_engine.py"],
                "accounting": ["accounting_engine.py"],
                "position": ["position_manager.py"],
                "market_data": ["market_data_engine.py", "market_data.py"],
            }
            if area in mapping:
                for f in mapping[area]:
                    add_if_present(f)

        # fallback: attempt to match keywords in filenames
        if not targets and ts.get("keywords"):
            kws = ts.get("keywords")
            for f in file_list:
                for kw in kws:
                    if kw.lower() in f.lower():
                        targets.append(f)
                        break

        # dedupe
        return list(dict.fromkeys(targets))

    def _assess_safety_and_adr(self, affected: List[str]) -> (bool, List[Dict[str, Any]]):
        safety_flags = []
        adr_needed = False
        for f in affected:
            if f in SENSITIVE_COMPONENT_FILES:
                adr_needed = True
                safety_flags.append({"file": f, "reason": "safety-sensitive component"})
        return adr_needed, safety_flags

    def _build_adr_artifact(self, req: InvocationRequest, ts: Dict[str, Any], affected: List[str], stage_context: Dict[str, Any]) -> Dict[str, Any]:
        task_title = str(ts.get("title") or req.task_id or "architecture-task")
        stage_id = str(ts.get("roadmap_stage_id") or ts.get("roadmap_child_stage_id") or stage_context.get("roadmap_stage_id") or "unknown")
        stage_title = str(stage_context.get("roadmap_child_stage_title") or ts.get("roadmap_child_stage_title") or "Architecture decision")
        decision_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{req.task_id}:{req.run_id or 'unknown'}:adr"))
        adr_content = {
            "adr_id": decision_id,
            "title": f"ADR {stage_id}: {stage_title}",
            "task_id": req.task_id,
            "run_id": req.run_id or str(uuid.uuid4()),
            "repository_revision": req.repository_revision,
            "status": "PROPOSED",
            "context": {
                "task_title": task_title,
                "stage_id": stage_id,
                "stage_title": stage_title,
                "affected_components": affected,
                "repository_context": ts.get("repository_context", {}),
            },
            "decision": {
                "summary": "The architecture decision for this stage is documented in the associated architecture result and ADR artifact.",
                "owner": stage_context.get("owner") or ts.get("owner") or "architect",
                "decision_type": "architecture_change",
            },
            "consequences": {
                "positive": ["Clear architectural boundary and evidence for execution.", "Improves traceability and reviewability."],
                "negative": ["Requires explicit ADR validation before proceeding to implementation."],
            },
            "alternatives_considered": [
                "Proceed without a formal ADR and rely on informal design notes.",
                "Treat the change as a simple implementation-only task without architecture review.",
            ],
            "references": {
                "task_spec": {
                    "roadmap_stage_id": ts.get("roadmap_stage_id"),
                    "roadmap_child_stage_id": ts.get("roadmap_child_stage_id"),
                    "required_evidence": ts.get("roadmap_required_evidence") or stage_context.get("required_evidence") or [],
                    "exit_criteria": ts.get("roadmap_exit_criteria") or stage_context.get("exit_criteria") or [],
                }
            },
        }
        return {
            "artifact_id": decision_id,
            "artifact_type": "adr",
            "task_id": req.task_id,
            "run_id": req.run_id or str(uuid.uuid4()),
            "repository_revision": req.repository_revision,
            "producer": "architect",
            "created_at": self._now(),
            "path": f".agent/adr/{decision_id}.md",
            "content": adr_content,
        }

    def execute(self, req: InvocationRequest) -> AgentResult:
        self.exec_count += 1
        # validate required inputs per contract
        self._validate_input(req)

        ts = req.task_spec or {}
        repo_ctx = ts.get("repository_context", {})

        affected = self._detect_affected(req)

        adr_required, safety_implications = self._assess_safety_and_adr(affected)

        # build outputs
        stage_context = {
            "roadmap_stage_id": ts.get("roadmap_stage_id") or ts.get("roadmap_child_stage_id") or None,
            "roadmap_child_stage_title": ts.get("roadmap_child_stage_title") or (ts.get("roadmap_stage") or {}).get("title"),
            "roadmap_child_stage_description": ts.get("roadmap_child_stage_description") or (ts.get("roadmap_stage") or {}).get("description"),
            "required_evidence": ts.get("roadmap_required_evidence") or ((ts.get("roadmap_stage") or {}).get("required_evidence") or []),
            "exit_criteria": ts.get("roadmap_exit_criteria") or ((ts.get("roadmap_stage") or {}).get("exit_criteria") or []),
            "owner": (ts.get("roadmap_stage") or {}).get("owner") or ts.get("owner") or (repo_ctx.get("owners") or {}).get("suggested") or None,
        }
        assessment = {
            "summary": f"Architect analysis for task {req.task_id}",
            "repository_revision": req.repository_revision,
            "files_scanned": len(repo_ctx.get("file_list", [])),
            "roadmap_stage": stage_context,
        }

        proposed_changes = []
        interfaces = []
        developer_spec = {
            "files": affected,
            "high_level_changes": [],
            "tests_to_add": [],
        }

        # Create conservative proposals per affected file
        for f in affected:
            proposed_changes.append({
                "file": f,
                "proposal": f"Update {f} to expose clearer interface and separation of concerns.",
            })
            interfaces.append({
                "file": f,
                "interface_example": f"def handle_{os.path.splitext(f)[0]}(input) -> dict: ...",
            })
            developer_spec["high_level_changes"].append(f"Refactor {f} into smaller functions; add typed interfaces.")
            developer_spec["tests_to_add"].append(f"tests/test_{os.path.splitext(f)[0]}_integration.py")

        risks = []
        for f in affected:
            risks.append({"file": f, "risk": "breaking change", "mitigation": "add tests and feature flags"})

        testing_strategy = {
            "unit": [f"pytest -q tests/test_{os.path.splitext(f)[0]}*.py" for f in affected],
            "integration": ["python -m unittest discover -s tests -p \"test*.py\" -v"],
        }

        acceptance_criteria = [
            "All new unit tests pass",
            "No regression in existing integration tests for affected modules",
        ]

        assumptions = []
        open_questions = []
        if not affected and (ts.get("roadmap_stage_id") or ts.get("roadmap_child_stage_id") or ts.get("roadmap_child_stage_title") or ts.get("roadmap_stage")):
            open_questions.append("Roadmap stage context was provided, but no existing repository component matched the stage evidence. Which component should be treated as the authoritative historical-data/replay owner?")
        if not repo_ctx.get("owners"):
            open_questions.append("Who owns the affected components (suggested owner missing) ?")

        adr_artifact = None
        adr_reference = None
        try:
            simulate_adr_persistence_failure = req.task_spec.get("simulate_adr_persistence_failure") if isinstance(req.task_spec, dict) else False
        except Exception:
            simulate_adr_persistence_failure = False

        if adr_required:
            try:
                adr_artifact = self._build_adr_artifact(req, ts, affected, stage_context)
                if simulate_adr_persistence_failure:
                    raise RuntimeError("simulated ADR persistence failure")
                adr_reference = adr_artifact["artifact_id"]
            except Exception as exc:
                return AgentResult(
                    task_id=req.task_id,
                    agent_role="ARCHITECT",
                    run_id=req.run_id or str(uuid.uuid4()),
                    status="FAILED",
                    started_at=self._now(),
                    completed_at=self._now(),
                    changed_files=[],
                    output_artifacts=[],
                    proposed_next_state=None,
                    error={"type": exc.__class__.__name__, "message": f"ADR creation/persistence failed: {exc}", "trace": ""},
                    execution_metadata={"repository_revision": req.repository_revision},
                )

        arch_result = ArchitectureResult(
            task_id=req.task_id,
            run_id=req.run_id,
            repository_revision=req.repository_revision,
            architecture_assessment=assessment,
            affected_components=affected,
            proposed_changes=proposed_changes,
            interfaces_contracts=interfaces,
            data_flow_impact={"note": "manual review required"},
            state_ownership_impact={"note": "no state migration proposed"},
            risks=risks,
            safety_implications=safety_implications,
            testing_strategy=testing_strategy,
            acceptance_criteria=acceptance_criteria,
            developer_specification=developer_spec,
            adr_required=adr_required,
            adr_reference=adr_reference,
            assumptions=assumptions,
            open_questions=open_questions,
            escalation={"requires_human_review": adr_required or bool(safety_implications)} if (adr_required or safety_implications) else None,
            status="PROPOSAL",
        )
        now = self._now()

        # simulation hook for tests: produce malformed artifact when requested
        try:
            simulate_malformed = req.task_spec.get("simulate_malformed") if isinstance(req.task_spec, dict) else False
        except Exception:
            simulate_malformed = False

        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "artifact_type": "architecture_result",
            "task_id": req.task_id,
            "run_id": req.run_id,
            "repository_revision": req.repository_revision,
            "producer": "architect",
            "created_at": now,
            "content": asdict(arch_result),
        }
        if simulate_malformed:
            artifact.pop("content", None)

        output_artifacts = [artifact]
        if adr_artifact is not None:
            output_artifacts.append(adr_artifact)

        result = AgentResult(
            task_id=req.task_id,
            agent_role="ARCHITECT",
            run_id=req.run_id or str(uuid.uuid4()),
            status="SUCCEEDED",
            started_at=now,
            completed_at=now,
            changed_files=[],
            output_artifacts=output_artifacts,
            proposed_next_state=None,
            error=None,
            execution_metadata={"repository_revision": req.repository_revision},
        )

        return result


__all__ = ["ArchitectExecutor", "ArchitectureResult"]
