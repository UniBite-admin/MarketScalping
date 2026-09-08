#!/usr/bin/env python3
"""Orchestrator core: TaskStore, WorkflowEngine, PolicyEvaluator, AgentRunner stub.

This module implements a minimal deterministic coordinator foundation for STEP 2.
Do NOT connect to live systems or modify trading engine files.
"""
import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from tools.agent_runtime import AgentRuntime, InvocationRequest
from tools.architect_agent import ArchitectExecutor
from tools.developer_agent import DeveloperExecutor

ROOT = os.path.dirname(os.path.dirname(__file__))
ORCH_DIR = os.path.join(ROOT, ".orchestrator")
TASKS_FILE = os.path.join(ORCH_DIR, "tasks.jsonl")
LOCKS_DIR = os.path.join(ORCH_DIR, "locks")


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


class LockError(RuntimeError):
    pass


class TaskStore:
    """Append-oriented JSONL task store with safe update semantics.

    Note: Runtime-only storage at `.orchestrator/` and should be gitignored.
    """

    def __init__(self, root: Optional[str] = None):
        self.root = ORCH_DIR if root is None else root
        self.tasks_file = os.path.join(self.root, "tasks.jsonl")
        self.locks_dir = os.path.join(self.root, "locks")
        os.makedirs(self.root, exist_ok=True)
        os.makedirs(self.locks_dir, exist_ok=True)

    def _fsync_and_close(self, f):
        try:
            f.flush()
            os.fsync(f.fileno())
        finally:
            f.close()

    def create_task(self, title: str, description: str = "", created_by: str = "system",
                    assigned_agent: Optional[str] = None, repository_revision: Optional[str] = None,
                    parent_task_id: Optional[str] = None, max_attempts: int = 2, extra: Optional[Dict[str,Any]] = None) -> Dict[str, Any]:
        # Deterministic-ish id: derive from title + creator + timestamp using UUID5
        now = _now_iso()
        task_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{title}|{created_by}|{now}").hex
        task = {
            "task_id": task_id,
            "title": title,
            "description": description,
            "status": "BACKLOG",
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "assigned_agent": assigned_agent,
            "repository_revision": repository_revision,
            "parent_task_id": parent_task_id,
            "attempt": 0,
            "max_attempts": max_attempts,
            "artifacts": [],
            "policy_results": [],
            "history": [],
        }
        if extra:
            task.update(extra)

        line = json.dumps(task, ensure_ascii=False)
        # atomic append: open, write, fsync
        with open(self.tasks_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            self._fsync_and_close(f)

        return task

    def list_tasks(self) -> List[Dict[str, Any]]:
        items = []
        if not os.path.exists(self.tasks_file):
            return items
        with open(self.tasks_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    # skip corrupted lines (safe recovery)
                    continue
        return items

    def _find_task_index(self, task_id: str) -> Optional[int]:
        tasks = self.list_tasks()
        for i, t in enumerate(tasks):
            if t.get("task_id") == task_id:
                return i
        return None

    def read_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        tasks = self.list_tasks()
        # return the latest matching
        for t in tasks:
            if t.get("task_id") == task_id:
                return t
        return None

    def _write_all_tasks(self, tasks: List[Dict[str, Any]]):
        # write to temp and replace to avoid partial writes
        fd, tmp = tempfile.mkstemp(prefix="tasks", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for t in tasks:
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")
                self._fsync_and_close(f)
            os.replace(tmp, self.tasks_file)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass

    def update_task(self, task_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        tasks = self.list_tasks()
        found = False
        for i, t in enumerate(tasks):
            if t.get("task_id") == task_id:
                t.update(patch)
                t["updated_at"] = _now_iso()
                tasks[i] = t
                found = True
                break
        if not found:
            raise KeyError("task not found")
        self._write_all_tasks(tasks)
        return t

    def append_transition(self, task_id: str, state: str, actor: str, note: Optional[str] = None):
        t = self.read_task(task_id)
        if t is None:
            raise KeyError("task not found")
        entry = {"at": _now_iso(), "state": state, "actor": actor}
        if note:
            entry["note"] = note
        t.setdefault("history", []).append(entry)
        t["status"] = state
        t["updated_at"] = _now_iso()
        self.update_task(task_id, {"history": t["history"], "status": state})

    def append_artifact(self, task_id: str, artifact: Dict[str, Any]):
        t = self.read_task(task_id)
        if t is None:
            raise KeyError("task not found")
        t.setdefault("artifacts", []).append(artifact)
        self.update_task(task_id, {"artifacts": t["artifacts"]})

    def append_policy_result(self, task_id: str, policy_result: Dict[str, Any]):
        t = self.read_task(task_id)
        if t is None:
            raise KeyError("task not found")
        t.setdefault("policy_results", []).append(policy_result)
        self.update_task(task_id, {"policy_results": t["policy_results"]})

    # simple filesystem lock
    def acquire_lock(self, task_id: str, owner: str, timeout: int = 5) -> None:
        lockfn = os.path.join(self.locks_dir, f"{task_id}.lock")
        try:
            fd = os.open(lockfn, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps({"owner": owner, "at": _now_iso()}))
            return
        except FileExistsError:
            raise LockError("lock exists")

    def release_lock(self, task_id: str) -> None:
        lockfn = os.path.join(self.locks_dir, f"{task_id}.lock")
        try:
            os.remove(lockfn)
        except FileNotFoundError:
            pass


class WorkflowEngine:
    """Loads workflow definition from .agent/workflows/workflow.json and validates transitions."""

    def __init__(self, workflow_path: Optional[str] = None):
        wf_path = workflow_path or os.path.join(ROOT, ".agent", "workflows", "workflow.json")
        with open(wf_path, "r", encoding="utf-8") as f:
            wf = json.load(f)
        self.states = wf.get("states", [])
        self.transitions = wf.get("transitions", [])
        # build allowed map
        self.allowed = {}
        for t in self.transitions:
            frm = t.get("from")
            to = t.get("to")
            if frm not in self.allowed:
                self.allowed[frm] = set()
            self.allowed[frm].add(to)

    def validate_transition(self, current: str, target: str) -> bool:
        if current == target:
            return True
        if current not in self.states:
            raise ValueError(f"Unknown current state: {current}")
        if target not in self.states:
            raise ValueError(f"Unknown target state: {target}")
        allowed = self.allowed.get(current, set())
        return target in allowed


class PolicyEvaluator:
    """Deterministic policy evaluator that loads .agent/policies/policies.json.

    Only performs deterministic detectors (path-based, operation-based). Returns
    structured policy results. When a policy cannot be deterministically decided,
    the evaluator returns decision='UNKNOWN' and the caller must treat that
    conservatively.
    """

    def __init__(self, policies_path: Optional[str] = None):
        ppath = policies_path or os.path.join(ROOT, ".agent", "policies", "policies.json")
        with open(ppath, "r", encoding="utf-8") as f:
            doc = json.load(f)
        self.policies = doc.get("policies", [])

    def get_policy_config(self, policy_id: str) -> Optional[Dict[str, Any]]:
        for p in self.policies:
            if p.get("id") == policy_id:
                return p
        return None

    def _match_path_regex(self, pattern: str, paths: List[str]) -> bool:
        try:
            r = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return False
        for p in paths:
            if r.search(p):
                return True
        return False

    def evaluate(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all policies against the provided task context.

        task may contain `changed_paths` (list of repo paths), `operation`,
        `target_branch` and other metadata. Returns list of policy result dicts.
        """
        results = []
        paths = task.get("changed_paths") or []
        operation = task.get("operation")
        target_branch = task.get("target_branch")

        for p in self.policies:
            pid = p.get("id")
            cond = p.get("condition", {})
            action = p.get("action")
            decision = "UNKNOWN"
            reason = "no deterministic detector matched"
            evidence: List[str] = []
            triggered = False
            deterministic = False

            # concrete detectors: exact paths
            if "paths" in cond:
                for cp in cond.get("paths", []):
                    if cp in paths:
                        triggered = True
                        deterministic = True
                        decision = self._normalize_action(action)
                        reason = f"changed path matched {cp}"
                        evidence.append(cp)
                        break

            # path regex detector
            if not triggered and "path_regex" in cond:
                pattern = cond.get("path_regex")
                if self._match_path_regex(pattern, paths):
                    triggered = True
                    deterministic = True
                    decision = self._normalize_action(action)
                    reason = f"path_regex {pattern} matched"
                    evidence.append(pattern)

            # operation-based detector
            if not triggered and "operation" in cond:
                if operation and cond.get("operation") == operation:
                    tbpat = cond.get("target_branch_pattern")
                    if tbpat and target_branch:
                        try:
                            if re.search(tbpat, target_branch):
                                triggered = True
                                deterministic = True
                                decision = self._normalize_action(action)
                                reason = f"operation {operation} matches branch {target_branch}"
                                evidence.append(target_branch)
                        except re.error:
                            pass
                    else:
                        triggered = True
                        deterministic = True
                        decision = self._normalize_action(action)
                        reason = f"operation {operation} matched"

            # concept-based or role-based conditions cannot be deterministically decided here
            # concept-based or role-based conditions: allow explicit task metadata to trigger
            if not triggered and "concept" in cond:
                task_concepts = task.get("concepts") or []
                # cond['concept'] may be a string or list
                want = cond.get("concept")
                if isinstance(want, str) and want in task_concepts:
                    triggered = True
                    deterministic = True
                    decision = self._normalize_action(action)
                    reason = f"concept {want} declared in task metadata"
                    evidence.append(want)
                elif isinstance(want, list) and any(w in task_concepts for w in want):
                    triggered = True
                    deterministic = True
                    decision = self._normalize_action(action)
                    reason = f"one of concepts {want} declared in task metadata"
                    evidence.extend([w for w in want if w in task_concepts])
                else:
                    # We cannot detect trigger reliably from diffs alone — not triggered
                    triggered = False
                    deterministic = False
                    reason = "conceptual condition; not deterministically triggered"
            elif not triggered and "role" in cond:
                # role-based conditions: evaluate explicit actor role if provided
                actor_role = task.get("actor_role")
                role_cond = cond.get("role")
                if actor_role and role_cond:
                    try:
                        pattern = re.compile(role_cond)
                        if pattern.search(actor_role):
                            triggered = True
                            deterministic = True
                            decision = self._normalize_action(action)
                            reason = f"actor_role {actor_role} matches {role_cond}"
                            evidence.append(actor_role)
                    except re.error:
                        pass

            # If triggered but normalization returned UNKNOWN (e.g., structured action), mark as triggered but unknown
            if triggered and decision == "UNKNOWN":
                deterministic = False
                reason = "triggered but decision could not be deterministically normalized"

            results.append({
                "policy_id": pid,
                "triggered": triggered,
                "deterministic": deterministic,
                "decision": decision,
                "action": action,
                "reason": reason,
                "evidence": evidence,
            })

        return results

    def _normalize_action(self, action: Any) -> str:
        # Normalizes action definitions to one of the canonical decisions.
        if isinstance(action, str):
            a = action.lower()
            if a in ("block", "deny", "forbid"):
                return "BLOCK"
            if a in ("require_safety_review", "require_safety"):
                return "REQUIRE_SAFETY_REVIEW"
            if a in ("require_human_approval", "require_human"):
                return "REQUIRE_HUMAN_APPROVAL"
            if a in ("allow", "permit"):
                return "ALLOW"
            return action.upper()
        if isinstance(action, dict):
            # treat structured actions conservatively as UNKNOWN semantics
            return "UNKNOWN"
        return "UNKNOWN"


class AgentRunner:
    """Stubbed AgentRunner interface. Does not invoke models or external systems.

    Later this can be extended to call Architect/Developer/QA/Safety workers.
    """

    def __init__(self):
        pass

    def run(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        # Return a dummy result suitable for integration tests. No side effects.
        return {"agent_id": agent_id, "status": "ok", "message": "stub"}


class Orchestrator:
    def __init__(self, policies_path: Optional[str] = None, store_root: Optional[str] = None):
        self.store = TaskStore(root=store_root)
        self.wf = WorkflowEngine()
        self.pe = PolicyEvaluator(policies_path=policies_path)
        self.agent_runner = AgentRunner()
        # persistent runtime for idempotent runs (in-memory for STEP 4D)
        self.runtime = AgentRuntime()
        # Load policy-driven limits with explicit safe fallbacks
        # agent_retry_limits
        pr_cfg = self.pe.get_policy_config("agent_retry_limits")
        if pr_cfg and isinstance(pr_cfg.get("action"), dict):
            self.retry_limit = pr_cfg.get("action", {}).get("max_retries", 2)
        else:
            self.retry_limit = 2  # explicit fallback

        # infinite_loop_prevention
        il_cfg = self.pe.get_policy_config("infinite_loop_prevention")
        if il_cfg and isinstance(il_cfg.get("action"), dict):
            self.loop_threshold = il_cfg.get("action", {}).get("threshold", 5)
        else:
            self.loop_threshold = 5  # explicit fallback

    def create_task(self, title: str, description: str = "", created_by: str = "system", **kwargs) -> Dict[str, Any]:
        return self.store.create_task(title, description, created_by, extra=kwargs)

    def transition_task(self, task_id: str, target_state: str, actor: str) -> Dict[str, Any]:
        # Acquire lock
        try:
            self.store.acquire_lock(task_id, owner=actor)
        except LockError:
            raise

        try:
            task = self.store.read_task(task_id)
            if task is None:
                raise KeyError("task not found")

            current = task.get("status")
            # idempotency: no-op if already in desired state
            if current == target_state:
                return {"status": "noop", "task": task}

            # Validate state machine
            if not self.wf.validate_transition(current, target_state):
                # allow retry attempts from BLOCKED state to re-evaluate policies
                if current != "BLOCKED":
                    raise ValueError(f"Invalid transition {current} -> {target_state}")

            # Evaluate policies conservatively
            policy_results = self.pe.evaluate(task)
            # persist policy results
            for pr in policy_results:
                self.store.append_policy_result(task_id, pr)
            # Decision logic (conservative): any BLOCK or UNKNOWN -> block/escalate
            found_block = None
            found_unknown = None
            for pr in policy_results:
                # only consider policies that were actually triggered
                if not pr.get("triggered"):
                    continue
                d = pr.get("decision")
                if d == "BLOCK":
                    found_block = pr
                    break
                if d == "UNKNOWN":
                    found_unknown = pr

            # If explicit BLOCK, record and stop
            if found_block is not None:
                self.store.append_transition(task_id, "BLOCKED", actor, note=f"policy:{found_block.get('policy_id')}")
                # increment attempt and escalate if exceeded (policy-driven)
                task = self.store.read_task(task_id)
                task["attempt"] = task.get("attempt", 0) + 1
                if task["attempt"] > getattr(self, "retry_limit", 2):
                    self.store.append_transition(task_id, "ESCALATED", actor, note="retry_limit_exceeded")
                    return {"status": "escalated", "policy": found_block}
                self.store.update_task(task_id, {"attempt": task["attempt"]})
                return {"status": "blocked", "policy": found_block}

            # If unknown detections exist, treat conservatively and block
            if found_unknown is not None:
                self.store.append_transition(task_id, "BLOCKED", actor, note=f"unknown_policy:{found_unknown.get('policy_id')}")
                task = self.store.read_task(task_id)
                task["attempt"] = task.get("attempt", 0) + 1
                if task["attempt"] > getattr(self, "retry_limit", 2):
                    self.store.append_transition(task_id, "ESCALATED", actor, note="retry_limit_exceeded")
                    return {"status": "escalated", "policy": found_unknown}
                self.store.update_task(task_id, {"attempt": task["attempt"]})
                return {"status": "blocked_unknown", "policy": found_unknown}

            # If any require safety/human approval, set pending states
            for pr in policy_results:
                if pr.get("decision") == "REQUIRE_SAFETY_REVIEW":
                    # If target is SAFETY, allow moving directly to HUMAN gate if appropriate
                    self.store.append_transition(task_id, "PENDING_SAFETY_REVIEW", actor, note=f"policy:{pr.get('policy_id')}")
                    return {"status": "pending_safety_review", "policy": pr}
                if pr.get("decision") == "REQUIRE_HUMAN_APPROVAL":
                    # If the desired target is HUMAN_APPROVAL, proceed; otherwise mark pending
                    if target_state == "HUMAN_APPROVAL":
                        # proceed to human approval state
                        self.store.append_transition(task_id, "HUMAN_APPROVAL", actor, note=f"policy:{pr.get('policy_id')}")
                        return {"status": "ok", "task": self.store.read_task(task_id)}
                    self.store.append_transition(task_id, "PENDING_HUMAN_APPROVAL", actor, note=f"policy:{pr.get('policy_id')}")
                    return {"status": "pending_human_approval", "policy": pr}

            # Loop protection: if history is too long, escalate
            hist = task.get("history", [])
            loop_threshold = getattr(self, "loop_threshold", 5)
            if len(hist) > loop_threshold:
                self.store.append_transition(task_id, "ESCALATED", actor, note="loop_detected")
                return {"status": "escalated", "reason": "loop_detected"}

            # Otherwise perform transition and reset attempt counter
            # Special handling for ARCHITECTURE: invoke Architect via AgentRuntime
            if target_state == "ARCHITECTURE":
                # prepare invocation
                task_spec = task.get("task_spec") or {}
                repo_rev = task.get("repository_revision") or task_spec.get("repository_revision")
                if not repo_rev:
                    # missing repository context -> block
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_repository_revision")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_repository_revision"}

                # reuse prior run_id if present to preserve idempotency
                existing_inv = None
                for a in reversed(task.get("artifacts", [])):
                    if a.get("artifact_type") == "invocation_record":
                        existing_inv = a
                        break

                if existing_inv:
                    run_id = existing_inv.get("run_id")
                else:
                    run_id = str(uuid.uuid4())

                inv_req = InvocationRequest(
                    task_id=task_id,
                    agent_role="ARCHITECT",
                    repository_revision=repo_rev,
                    worktree=None,
                    task_spec=task_spec,
                    input_artifacts=task.get("artifacts", []),
                    policy_context={p.get("policy_id"): p for p in policy_results},
                    timeout_seconds=60,
                    attempt=task.get("attempt", 0),
                    run_id=run_id,
                )

                runtime = self.runtime
                runtime.executor = ArchitectExecutor()
                # record invocation artifact (audit)
                invocation_record = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "invocation_record",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "orchestrator",
                    "created_at": _now_iso(),
                    "content": {"agent_role": "ARCHITECT", "repository_revision": repo_rev, "attempt": task.get("attempt", 0)},
                }
                self.store.append_artifact(task_id, invocation_record)

                # if existing run recorded, try to fetch its result first
                existing_result = runtime.get_result(run_id)
                if existing_result is not None:
                    result = existing_result
                else:
                    result = runtime.invoke(inv_req)

                # store runtime result for audit
                result_art = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "agent_result",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "architect_runtime",
                    "created_at": _now_iso(),
                    "content": {
                        "status": result.status,
                        "started_at": result.started_at,
                        "completed_at": result.completed_at,
                        "error": result.error,
                    },
                }
                self.store.append_artifact(task_id, result_art)

                # handle failed or timed-out results
                if result.status in ("FAILED", "TIMED_OUT"):
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    if task["attempt"] > getattr(self, "retry_limit", 2):
                        self.store.append_transition(task_id, "ESCALATED", actor, note="architect_failed")
                        return {"status": "escalated", "reason": "architect_failed"}
                    self.store.append_transition(task_id, "BLOCKED", actor, note="architect_failed")
                    return {"status": "blocked", "reason": "architect_failed"}

                # expect at least one architecture_result artifact
                out_arts = result.output_artifacts or []
                if not out_arts:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="no_architecture_result")
                    return {"status": "blocked", "reason": "no_architecture_result"}

                art = out_arts[0]
                # validate envelope required fields
                required_env = ("artifact_id", "artifact_type", "task_id", "run_id", "repository_revision", "producer", "created_at", "content")
                if not all(k in art for k in required_env):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_architecture_envelope")
                    return {"status": "blocked", "reason": "malformed_architecture_envelope"}

                if art.get("artifact_type") != "architecture_result":
                    self.store.append_transition(task_id, "BLOCKED", actor, note="unexpected_artifact_type")
                    return {"status": "blocked", "reason": "unexpected_artifact_type"}

                # validate content fields
                content = art.get("content") or {}
                content_required = ("task_id", "run_id", "repository_revision", "architecture_assessment", "affected_components", "proposed_changes", "acceptance_criteria", "developer_specification", "adr_required", "status")
                if not all(k in content for k in content_required):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_architecture_content")
                    return {"status": "blocked", "reason": "malformed_architecture_content"}

                # verify task_id and run_id match
                if content.get("task_id") != task_id or content.get("run_id") != run_id:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="id_mismatch")
                    return {"status": "blocked", "reason": "id_mismatch"}

                # persist architecture_result artifact into task
                self.store.append_artifact(task_id, art)

                # ADR predicate handling
                adr_required = bool(content.get("adr_required"))
                if not adr_required:
                    # proceed to READY if no safety implications found
                    safety_imp = content.get("safety_implications") or []
                    if safety_imp:
                        self.store.append_transition(task_id, "PENDING_SAFETY_REVIEW", actor, note="safety_implications_detected")
                        return {"status": "pending_safety_review"}
                    self.store.append_transition(task_id, "READY", actor)
                    self.store.update_task(task_id, {"attempt": 0})
                    return {"status": "ok", "task": self.store.read_task(task_id)}
                else:
                    # check for ADR artifact in task artifacts or adr_reference in content
                    existing = self.store.read_task(task_id).get("artifacts", [])
                    has_adr = any(a.get("artifact_type") == "adr" for a in existing)
                    adr_ref = content.get("adr_reference")
                    if not has_adr and not adr_ref:
                        self.store.append_transition(task_id, "BLOCKED", actor, note="adr_required_missing")
                        return {"status": "blocked", "reason": "adr_required_missing"}
                    # minimal ADR validation: presence suffices here
                    self.store.append_transition(task_id, "READY", actor)
                    self.store.update_task(task_id, {"attempt": 0})
                    return {"status": "ok", "task": self.store.read_task(task_id)}

            # Special handling for DEVELOPMENT: invoke Developer via AgentRuntime
            if target_state == "DEVELOPMENT":
                task_spec = dict(task.get("task_spec") or {})
                if not isinstance(task_spec, dict):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_developer_task_spec")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_developer_task_spec"}

                required_inputs = ("task_record", "architecture_result", "repository_context", "repository_revision", "run_id")
                missing = [key for key in required_inputs if key not in task_spec or not task_spec.get(key)]
                if missing:
                    self.store.append_transition(task_id, "BLOCKED", actor, note=f"missing_developer_inputs:{','.join(missing)}")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_developer_inputs", "missing": missing}

                task_record = task_spec.get("task_record") or {}
                if not isinstance(task_record, dict):
                    task_record = {}
                task_record["task_id"] = task_id
                task_record["status"] = "READY"
                task_spec["task_record"] = task_record

                architecture_result = task_spec.get("architecture_result") or {}
                if not isinstance(architecture_result, dict):
                    architecture_result = {}
                architecture_result["task_id"] = task_id
                architecture_result["run_id"] = task_spec.get("run_id") or str(uuid.uuid4())
                architecture_result["repository_revision"] = task_spec.get("repository_revision") or task.get("repository_revision")
                task_spec["architecture_result"] = architecture_result

                orchestrator_authorization = task_spec.get("orchestrator_authorization") or {}
                if not isinstance(orchestrator_authorization, dict):
                    orchestrator_authorization = {}
                orchestrator_authorization["authorized"] = True
                orchestrator_authorization["task_id"] = task_id
                task_spec["orchestrator_authorization"] = orchestrator_authorization

                if missing:
                    self.store.append_transition(task_id, "BLOCKED", actor, note=f"missing_developer_inputs:{','.join(missing)}")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_developer_inputs", "missing": missing}

                repo_rev = task_spec.get("repository_revision") or task.get("repository_revision")
                if not repo_rev:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_repository_revision")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_repository_revision"}

                run_id = task_spec.get("run_id") or str(uuid.uuid4())
                task_spec["run_id"] = run_id
                task["task_spec"] = task_spec
                self.store.update_task(task_id, {"task_spec": task_spec})

                existing_inv = None
                for a in reversed(task.get("artifacts", [])):
                    if a.get("artifact_type") == "invocation_record" and a.get("run_id") == run_id:
                        existing_inv = a
                        break
                if existing_inv is not None:
                    run_id = existing_inv.get("run_id") or run_id

                inv_req = InvocationRequest(
                    task_id=task_id,
                    agent_role="DEVELOPER",
                    repository_revision=repo_rev,
                    worktree=None,
                    task_spec=task_spec,
                    input_artifacts=task.get("artifacts", []),
                    policy_context={p.get("policy_id"): p for p in policy_results},
                    timeout_seconds=60,
                    attempt=task.get("attempt", 0),
                    run_id=run_id,
                )

                runtime = self.runtime
                runtime.executor = DeveloperExecutor()
                invocation_record = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "invocation_record",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "orchestrator",
                    "created_at": _now_iso(),
                    "content": {"agent_role": "DEVELOPER", "repository_revision": repo_rev, "attempt": task.get("attempt", 0)},
                }
                self.store.append_artifact(task_id, invocation_record)

                existing_result = runtime.get_result(run_id)
                result = existing_result if existing_result is not None else runtime.invoke(inv_req)

                result_art = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "agent_result",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "developer_runtime",
                    "created_at": _now_iso(),
                    "content": {
                        "status": result.status,
                        "started_at": result.started_at,
                        "completed_at": result.completed_at,
                        "error": result.error,
                    },
                }
                self.store.append_artifact(task_id, result_art)

                if result.status in ("FAILED", "TIMED_OUT", "CANCELLED"):
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    if task["attempt"] > getattr(self, "retry_limit", 2):
                        self.store.append_transition(task_id, "ESCALATED", actor, note="developer_failed")
                        return {"status": "escalated", "reason": "developer_failed"}
                    self.store.append_transition(task_id, "BLOCKED", actor, note="developer_failed")
                    return {"status": "blocked", "reason": "developer_failed"}

                output_arts = result.output_artifacts or []
                if not output_arts:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="no_developer_artifacts")
                    return {"status": "blocked", "reason": "no_developer_artifacts"}

                required_env = ("artifact_id", "artifact_type", "task_id", "run_id", "repository_revision", "producer", "created_at", "content")
                normalized_output = []
                for art in output_arts:
                    if not all(k in art for k in required_env):
                        self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_developer_envelope")
                        return {"status": "blocked", "reason": "malformed_developer_envelope"}
                    if art.get("artifact_type") not in ("implementation_artifact", "test_manifest"):
                        normalized_output.append(art)
                        continue
                    normalized_output.append(art)
                    self.store.append_artifact(task_id, art)

                if not any(a.get("artifact_type") == "implementation_artifact" for a in normalized_output):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_implementation_artifact")
                    return {"status": "blocked", "reason": "missing_implementation_artifact"}
                if not any(a.get("artifact_type") == "test_manifest" for a in normalized_output):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_test_manifest")
                    return {"status": "blocked", "reason": "missing_test_manifest"}

                self.store.append_transition(task_id, target_state, actor, note="developer_execution")
                self.store.update_task(task_id, {"attempt": 0})
                return {"status": "ok", "task": self.store.read_task(task_id)}

            # Otherwise normal transition
            self.store.append_transition(task_id, target_state, actor)
            self.store.update_task(task_id, {"attempt": 0})
            return {"status": "ok", "task": self.store.read_task(task_id)}
        finally:
            try:
                self.store.release_lock(task_id)
            except Exception:
                pass


__all__ = ["TaskStore", "WorkflowEngine", "PolicyEvaluator", "AgentRunner", "Orchestrator"]
