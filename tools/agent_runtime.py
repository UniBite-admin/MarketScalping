"""Minimal Agent Runtime (STEP 3B) - local mock executor only.

Design constraints enforced:
- No network calls, no external providers.
- No trading/runtime module modifications.
"""
from __future__ import annotations

import uuid
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class InvocationRequest:
    task_id: str
    agent_role: str
    repository_revision: str
    worktree: Optional[str]
    task_spec: Dict[str, Any]
    input_artifacts: List[Dict[str, Any]]
    policy_context: Dict[str, Any]
    timeout_seconds: int
    attempt: int
    run_id: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class ArtifactDescriptor:
    artifact_id: str
    artifact_type: str
    path: str
    producer_agent: str
    task_id: str
    run_id: str


@dataclass
class AgentResult:
    task_id: str
    agent_role: str
    run_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    changed_files: List[str] = field(default_factory=list)
    output_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    proposed_next_state: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)


class AgentExecutor:
    """Abstract executor interface."""

    def execute(self, request: InvocationRequest) -> AgentResult:
        raise NotImplementedError()


class MockAgentExecutor(AgentExecutor):
    """Deterministic mock executor used for local testing.

    Behavior is controlled by `task_spec` keys:
    - task_spec.get('simulate') == 'fail' -> raise RuntimeError
    - task_spec.get('simulate') == 'timeout' -> raise TimeoutError
    Otherwise, returns a deterministic successful AgentResult.
    """

    def execute(self, request: InvocationRequest) -> AgentResult:
        start = datetime.utcnow().isoformat() + "Z"
        run_id = request.run_id or str(uuid.uuid4())

        simulate = None
        try:
            simulate = request.task_spec.get("simulate") if isinstance(request.task_spec, dict) else None
        except Exception:
            simulate = None

        if simulate == "timeout":
            raise TimeoutError("simulated timeout")
        if simulate == "fail":
            raise RuntimeError("simulated failure")

        # produce deterministic artifact and changed_files based on task_spec
        proposed = None
        changed = []
        artifacts: List[Dict[str, Any]] = []
        if isinstance(request.task_spec, dict):
            proposed = request.task_spec.get("proposed_next_state")
            extra_file = request.task_spec.get("touch_file")
            if extra_file:
                changed.append(extra_file)
                art = {
                    "artifact_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{extra_file}")),
                    "artifact_type": "patch",
                    "path": extra_file,
                    "producer_agent": request.agent_role,
                    "task_id": request.task_id,
                    "run_id": run_id,
                }
                artifacts.append(art)

        end = datetime.utcnow().isoformat() + "Z"
        result = AgentResult(
            task_id=request.task_id,
            agent_role=request.agent_role,
            run_id=run_id,
            status="SUCCEEDED",
            started_at=start,
            completed_at=end,
            changed_files=changed,
            output_artifacts=artifacts,
            proposed_next_state=proposed,
            error=None,
            execution_metadata={
                "repository_revision": request.repository_revision,
                "worktree": request.worktree,
                "attempt": request.attempt,
            },
        )
        return result


class AgentRuntime:
    """Minimal runtime facade.

    Responsibilities:
    - Validate requests
    - Generate run_id when missing
    - Track runs and ensure idempotency
    - Invoke the provided executor and capture result
    """

    def __init__(self, executor: Optional[AgentExecutor] = None):
        self.executor = executor or MockAgentExecutor()
        # simple in-memory registry: run_id -> AgentResult
        self._runs: Dict[str, AgentResult] = {}

    def _validate(self, req: InvocationRequest) -> None:
        if not req.task_id:
            raise ValueError("task_id required")
        if not req.agent_role:
            raise ValueError("agent_role required")
        if not req.repository_revision:
            raise ValueError("repository_revision required")
        if req.timeout_seconds is None:
            raise ValueError("timeout_seconds required")
        if req.attempt is None:
            raise ValueError("attempt required")

    def invoke(self, req: InvocationRequest) -> AgentResult:
        # idempotency: if run_id present and known return cached result
        run_id = req.run_id or str(uuid.uuid4())
        if req.run_id and req.run_id in self._runs:
            return self._runs[req.run_id]

        # validate required fields
        req.run_id = run_id
        self._validate(req)

        # record CREATED
        started_at = datetime.utcnow().isoformat() + "Z"
        temp_result = AgentResult(
            task_id=req.task_id,
            agent_role=req.agent_role,
            run_id=run_id,
            status="STARTING",
            started_at=started_at,
            execution_metadata={"repository_revision": req.repository_revision, "worktree": req.worktree},
        )
        self._runs[run_id] = temp_result

        # Execute
        try:
            # mark running
            temp_result.status = "RUNNING"
            self._runs[run_id] = temp_result
            result = self.executor.execute(req)
            result.execution_metadata.setdefault("repository_revision", req.repository_revision)
            result.execution_metadata.setdefault("worktree", req.worktree)
            result.started_at = temp_result.started_at
            result.completed_at = datetime.utcnow().isoformat() + "Z"
            self._runs[run_id] = result
            return result
        except TimeoutError as te:
            err = {"type": "TimeoutError", "message": str(te), "trace": traceback.format_exc()}
            res = AgentResult(
                task_id=req.task_id,
                agent_role=req.agent_role,
                run_id=run_id,
                status="TIMED_OUT",
                started_at=temp_result.started_at,
                completed_at=datetime.utcnow().isoformat() + "Z",
                error=err,
                execution_metadata={"repository_revision": req.repository_revision, "worktree": req.worktree},
            )
            self._runs[run_id] = res
            return res
        except Exception as exc:
            # Any other execution exception -> mark FAILED and record
            err = {"type": exc.__class__.__name__, "message": str(exc), "trace": traceback.format_exc()}
            res = AgentResult(
                task_id=req.task_id,
                agent_role=req.agent_role,
                run_id=run_id,
                status="FAILED",
                started_at=temp_result.started_at,
                completed_at=datetime.utcnow().isoformat() + "Z",
                error=err,
                execution_metadata={"repository_revision": req.repository_revision, "worktree": req.worktree},
            )
            self._runs[run_id] = res
            return res

    def get_result(self, run_id: str) -> Optional[AgentResult]:
        """Return the stored AgentResult for the given run_id or None if not found.

        Behavior notes (design-only):
        - Does not re-execute runs.
        - Returns current state for active runs (STARTING, RUNNING) and full result for completed runs.
        - If runtime is in-memory only, results are only available while the process lives; durable persistence is out of scope for STEP 4D.
        """
        return self._runs.get(run_id)
