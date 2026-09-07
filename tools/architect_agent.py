"""Architect Agent Executor implementation (local, deterministic, mock reasoning).

This executor is compatible with `tools.agent_runtime.AgentExecutor` and intended
to run under the existing `AgentRuntime` for STEP 4B. It performs read-only
analysis of the provided `InvocationRequest` and produces a structured
architecture result as an output artifact. No external calls, no LLMs, no
side-effects.
"""
from __future__ import annotations

import os
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
        # direct hint
        if isinstance(ts.get("target_paths"), list):
            for p in ts.get("target_paths"):
                if p in file_list:
                    targets.append(p)
                else:
                    # accept if appears as basename
                    base = os.path.basename(p)
                    if base in file_list:
                        targets.append(base)

        # change_area semantic hints
        if not targets and ts.get("change_area"):
            area = ts.get("change_area")
            # map known areas
            mapping = {
                "risk": ["risk_engine.py"],
                "execution": ["execution_engine.py"],
                "accounting": ["accounting_engine.py"],
                "position": ["position_manager.py"],
                "market_data": ["market_data_engine.py", "market_data.py"],
            }
            if area in mapping:
                for f in mapping[area]:
                    if f in file_list:
                        targets.append(f)

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

    def execute(self, req: InvocationRequest) -> AgentResult:
        self.exec_count += 1
        # validate required inputs per contract
        self._validate_input(req)

        ts = req.task_spec or {}
        repo_ctx = ts.get("repository_context", {})

        affected = self._detect_affected(req)

        adr_required, safety_implications = self._assess_safety_and_adr(affected)

        # build outputs
        assessment = {
            "summary": f"Architect analysis for task {req.task_id}",
            "repository_revision": req.repository_revision,
            "files_scanned": len(repo_ctx.get("file_list", [])),
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
        if not repo_ctx.get("owners"):
            open_questions.append("Who owns the affected components (suggested owner missing) ?")

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
            adr_reference=None,
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
        result = AgentResult(
            task_id=req.task_id,
            agent_role="ARCHITECT",
            run_id=req.run_id or str(uuid.uuid4()),
            status="SUCCEEDED",
            started_at=now,
            completed_at=now,
            changed_files=[],
            output_artifacts=[artifact],
            proposed_next_state=None,
            error=None,
            execution_metadata={"repository_revision": req.repository_revision},
        )

        return result


__all__ = ["ArchitectExecutor", "ArchitectureResult"]
