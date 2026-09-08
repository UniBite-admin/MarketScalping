"""Developer Agent executor.

This is a minimal, deterministic local implementation that follows the formal
runtime contract and artifact vocabulary. It remains isolated to the requested
repository scope and never performs live market or account operations.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.agent_runtime import AgentExecutor, AgentResult, InvocationRequest


class DeveloperExecutor(AgentExecutor):
    """Deterministic developer executor for the canonical workflow.

    Requirements enforced:
    - authorized task
    - valid task_record
    - valid architecture_result
    - repository_context and repository_revision
    - run_id preserved for idempotency
    - implementation_artifact and test_manifest are emitted
    - no live trading / credential access / deploy authority
    - scope enforcement
    """

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _read_task_spec(self, req: InvocationRequest) -> Dict[str, Any]:
        ts = req.task_spec or {}
        if not isinstance(ts, dict):
            raise ValueError("task_spec must be an object")
        return ts

    def _validate_required_inputs(self, req: InvocationRequest, task_spec: Dict[str, Any]) -> None:
        if not req.task_id:
            raise ValueError("task_id required")
        if not req.run_id:
            raise ValueError("run_id required")
        if not req.repository_revision:
            raise ValueError("repository_revision required")

        req_task_record = task_spec.get("task_record")
        if not isinstance(req_task_record, dict):
            raise ValueError("task_record required")
        if not req_task_record.get("authorized", False):
            raise ValueError("task_record authorization required")

        architecture = task_spec.get("architecture_result")
        if not isinstance(architecture, dict):
            raise ValueError("architecture_result required")

        repo_context = task_spec.get("repository_context")
        if not isinstance(repo_context, dict):
            raise ValueError("repository_context required")

        repo_revision = task_spec.get("repository_revision") or req.repository_revision
        if not repo_revision:
            raise ValueError("repository_revision required")

        auth = task_spec.get("orchestrator_authorization")
        if not isinstance(auth, dict) or not auth.get("authorized", False):
            raise ValueError("orchestrator authorization required")

        if auth.get("task_id") and auth.get("task_id") != req.task_id:
            raise ValueError("authorization task mismatch")

        # Check for safe scope and no live trading / credential exposure.
        scope = task_spec.get("scope") or []
        if scope and not isinstance(scope, list):
            raise ValueError("scope must be a list")

        impl_target = task_spec.get("implementation_target")
        if impl_target and not isinstance(impl_target, str):
            raise ValueError("implementation_target must be a string")

        forbidden_keys = (
            "live_credentials",
            "trade_enablement",
            "account_control",
            "funds_release",
            "execution_gate",
        )
        flat = str(task_spec).lower()
        for key in forbidden_keys:
            if key in flat:
                raise ValueError("unsafe or unauthorized developer input")

    def _scope_ok(self, task_spec: Dict[str, Any]) -> bool:
        scope = task_spec.get("scope") or []
        if not scope:
            return True
        if not isinstance(scope, list):
            return False
        if len(scope) != 1:
            return False
        implementation_target = task_spec.get("implementation_target")
        if implementation_target:
            return str(implementation_target) == str(scope[0])
        return True

    def _generate_implementation_artifact(self, req: InvocationRequest, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        changed_files = []
        impl_target = task_spec.get("implementation_target")
        if impl_target:
            changed_files.append(str(impl_target))

        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "artifact_type": "implementation_artifact",
            "task_id": req.task_id,
            "run_id": req.run_id,
            "repository_revision": req.repository_revision,
            "producer": "developer",
            "created_at": now,
            "content": {
                "task_id": req.task_id,
                "run_id": req.run_id,
                "repository_revision": req.repository_revision,
                "architecture_reference": task_spec.get("architecture_result", {}).get("task_id"),
                "changed_files": changed_files,
                "implementation_status": "IMPLEMENTED",
                "verification_status": "PENDING",
                "known_limitations": [],
                "blockers": [],
                "scope": task_spec.get("scope") or [],
            },
        }
        return artifact

    def _generate_test_manifest(self, req: InvocationRequest, task_spec: Dict[str, Any], failed: bool = False) -> Dict[str, Any]:
        now = self._now()
        tests_executed = task_spec.get("tests_to_run") or ["python -m unittest discover -s tests -p \"test*.py\" -v"]
        status = "FAILED" if failed else "PASSED"
        failure_details = [] if not failed else ["simulated validation failure"]
        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "artifact_type": "test_manifest",
            "task_id": req.task_id,
            "run_id": req.run_id,
            "repository_revision": req.repository_revision,
            "producer": "developer",
            "created_at": now,
            "content": {
                "tests_executed": tests_executed,
                "commands": tests_executed,
                "results": [{"command": c, "status": status, "failure_details": failure_details} for c in tests_executed],
                "verification_status": status,
                "relevant_failures": failure_details,
                "environment_limitations": [],
                "sufficient_for_task": not failed,
            },
        }
        return artifact

    def execute(self, req: InvocationRequest) -> AgentResult:
        try:
            task_spec = self._read_task_spec(req)
            self._validate_required_inputs(req, task_spec)

            if not self._scope_ok(task_spec):
                raise ValueError("scope violation: requested implementation target is outside authorized scope")

            if task_spec.get("simulate_failure"):
                raise RuntimeError("simulated developer failure")

            impl_art = self._generate_implementation_artifact(req, task_spec)
            test_manifest = self._generate_test_manifest(req, task_spec, failed=False)

            result = AgentResult(
                task_id=req.task_id,
                agent_role="DEVELOPER",
                run_id=req.run_id or str(uuid.uuid4()),
                status="SUCCEEDED",
                started_at=self._now(),
                completed_at=self._now(),
                changed_files=impl_art["content"]["changed_files"],
                output_artifacts=[impl_art, test_manifest],
                proposed_next_state="CI",
                execution_metadata={
                    "repository_revision": req.repository_revision,
                    "worktree": req.worktree,
                    "attempt": req.attempt,
                    "task_record": task_spec.get("task_record", {}),
                    "architecture_reference": task_spec.get("architecture_result", {}).get("task_id"),
                },
            )
            return result
        except Exception as exc:  # pragma: no cover - structured failure reporting
            err = {"type": exc.__class__.__name__, "message": str(exc)}
            result = AgentResult(
                task_id=req.task_id,
                agent_role="DEVELOPER",
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
            return result


__all__ = ["DeveloperExecutor"]
