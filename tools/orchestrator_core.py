#!/usr/bin/env python3
"""Orchestrator core: TaskStore, WorkflowEngine, PolicyEvaluator, AgentRunner stub.

This module implements a minimal deterministic coordinator foundation for STEP 2.
Do NOT connect to live systems or modify trading engine files.
"""
import hashlib
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
from tools.qa_agent import QAExecutor
from tools.roadmap_loader import RoadmapLoader, RoadmapValidationError
from tools.safety_agent import SafetyExecutor

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
    def __init__(self, policies_path: Optional[str] = None, store_root: Optional[str] = None, roadmap_path: Optional[str] = None):
        self.store = TaskStore(root=store_root)
        self.wf = WorkflowEngine()
        self.pe = PolicyEvaluator(policies_path=policies_path)
        self.agent_runner = AgentRunner()
        self.roadmap_error = None
        try:
            self.roadmap_loader = RoadmapLoader(roadmap_path=roadmap_path)
        except RoadmapValidationError as exc:
            self.roadmap_loader = None
            self.roadmap_error = str(exc)
        except Exception as exc:  # pragma: no cover - defensive compatibility
            self.roadmap_loader = None
            self.roadmap_error = str(exc)
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

    def _project_task_record(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        projected = {}
        for key in ("task_id", "title", "description", "authorized", "status"):
            if key in value:
                projected[key] = value[key]
        if "scope" in value:
            projected["scope"] = value["scope"]
        if "task_spec" in value:
            projected["task_spec"] = value["task_spec"]
        return projected

    def _project_architecture_result(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        projected = {}
        for key in (
            "task_id",
            "repository_revision",
            "architecture_assessment",
            "affected_components",
            "acceptance_criteria",
            "developer_specification",
            "adr_required",
            "adr_reference",
            "status",
            "safety_implications",
        ):
            if key in value:
                projected[key] = value[key]
        return projected

    def _project_repository_context(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        projected = {}
        for key in ("repository_revision", "file_list", "files"):
            if key in value:
                projected[key] = value[key]
        if "repository_state" in value:
            projected["repository_state"] = value["repository_state"]
        return projected

    def _project_implementation_artifact(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        projected = {}
        if "task_id" in value:
            projected["task_id"] = value["task_id"]
        if "repository_revision" in value:
            projected["repository_revision"] = value["repository_revision"]
        content = value.get("content") if isinstance(value.get("content"), dict) else {}
        for key in (
            "changed_files",
            "implementation_status",
            "verification_status",
            "known_limitations",
            "blockers",
        ):
            if key in content:
                projected[key] = content[key]
        return projected

    def _project_test_manifest(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        projected = {}
        if "task_id" in value:
            projected["task_id"] = value["task_id"]
        if "repository_revision" in value:
            projected["repository_revision"] = value["repository_revision"]
        content = value.get("content") if isinstance(value.get("content"), dict) else {}
        for key in (
            "tests_executed",
            "results",
            "verification_status",
            "relevant_failures",
        ):
            if key in content:
                projected[key] = content[key]
        return projected

    def _normalize_qa_fingerprint_payload(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        canonical = {}
        for key in (
            "task_id",
            "repository_revision",
            "task_record",
            "architecture_result",
            "repository_context",
            "implementation_artifact",
            "test_manifest",
        ):
            value = task_spec.get(key)
            if value is None:
                continue
            if key == "task_record":
                canonical[key] = self._project_task_record(value)
            elif key == "architecture_result":
                canonical[key] = self._project_architecture_result(value)
            elif key == "repository_context":
                canonical[key] = self._project_repository_context(value)
            elif key == "implementation_artifact":
                canonical[key] = self._project_implementation_artifact(value)
            elif key == "test_manifest":
                canonical[key] = self._project_test_manifest(value)
            else:
                canonical[key] = value
        return canonical

    def _compute_qa_fingerprint(self, task_spec: Dict[str, Any]) -> str:
        canonical = self._normalize_qa_fingerprint_payload(task_spec)
        serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _project_qa_result(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        projected = {}
        for key in (
            "task_id",
            "run_id",
            "repository_revision",
            "decision",
            "severity",
            "verification_summary",
            "evidence_references",
            "defects",
            "limitations",
            "safety_relevant_findings",
            "blocking_status",
        ):
            if key in value:
                projected[key] = value[key]
        return projected

    def _normalize_safety_fingerprint_payload(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        canonical = {}
        for key in (
            "task_id",
            "repository_revision",
            "task_record",
            "architecture_result",
            "repository_context",
            "implementation_artifact",
            "test_manifest",
            "qa_result",
        ):
            value = task_spec.get(key)
            if value is None:
                continue
            if key == "task_record":
                canonical[key] = self._project_task_record(value)
            elif key == "architecture_result":
                canonical[key] = self._project_architecture_result(value)
            elif key == "repository_context":
                canonical[key] = self._project_repository_context(value)
            elif key == "implementation_artifact":
                canonical[key] = self._project_implementation_artifact(value)
            elif key == "test_manifest":
                canonical[key] = self._project_test_manifest(value)
            elif key == "qa_result":
                canonical[key] = self._project_qa_result(value)
            else:
                canonical[key] = value
        return canonical

    def _compute_safety_fingerprint(self, task_spec: Dict[str, Any]) -> str:
        canonical = self._normalize_safety_fingerprint_payload(task_spec)
        serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _get_qa_run_fingerprint(self, task_id: str, run_id: str, agent_role: str = "QA") -> Optional[str]:
        target_role = str(agent_role).upper()
        for task in reversed(self.store.list_tasks()):
            if task is None:
                continue
            for artifact in reversed(task.get("artifacts", [])):
                if artifact.get("artifact_type") != "invocation_record":
                    continue
                if artifact.get("run_id") != run_id:
                    continue
                content = artifact.get("content") or {}
                recorded_agent_role = (content.get("agent_role") or "").upper()
                if recorded_agent_role and recorded_agent_role != target_role:
                    continue
                if artifact.get("task_id") != task_id:
                    return "__existing_run_id__"
                if content.get("logical_fingerprint") is not None:
                    return content.get("logical_fingerprint")
                return "__existing_run_id__"
        return None

    def _get_safety_run_fingerprint(self, task_id: str, run_id: str, agent_role: str = "SAFETY") -> Optional[str]:
        target_role = str(agent_role).upper()
        for task in reversed(self.store.list_tasks()):
            if task is None:
                continue
            for artifact in reversed(task.get("artifacts", [])):
                if artifact.get("artifact_type") != "invocation_record":
                    continue
                if artifact.get("run_id") != run_id:
                    continue
                content = artifact.get("content") or {}
                recorded_agent_role = (content.get("agent_role") or "").upper()
                if recorded_agent_role and recorded_agent_role != target_role:
                    continue
                if artifact.get("task_id") != task_id:
                    return "__existing_run_id__"
                if content.get("logical_fingerprint") is not None:
                    return content.get("logical_fingerprint")
                return "__existing_run_id__"
        return None

    def _materialize_task_spec_from_artifacts(self, task: Dict[str, Any], task_spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged = dict(task_spec or {})
        artifacts = task.get("artifacts") or []
        artifact_by_type = {}
        for art in artifacts:
            if not isinstance(art, dict):
                continue
            t = art.get("artifact_type")
            if t:
                artifact_by_type.setdefault(t, []).append(art)

        for key, art_type in (
            ("architecture_result", "architecture_result"),
            ("implementation_artifact", "implementation_artifact"),
            ("test_manifest", "test_manifest"),
            ("ci_results", "ci_results"),
            ("qa_result", "qa_result"),
            ("defect_report", "defect_report"),
            ("safety_result", "safety_result"),
            ("human_approval_record", "human_approval_record"),
        ):
            if key in merged:
                continue
            candidates = artifact_by_type.get(art_type, [])
            if not candidates:
                continue
            merged[key] = candidates[-1]

        if "task_record" not in merged:
            merged["task_record"] = {
                "task_id": task.get("task_id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "authorized": True,
            }

        if "repository_revision" not in merged:
            merged["repository_revision"] = task.get("repository_revision")
        if "run_id" not in merged and task.get("task_spec") and isinstance(task.get("task_spec"), dict):
            merged["run_id"] = task["task_spec"].get("run_id")

        return merged

    def build_operator_snapshot(self) -> Dict[str, Any]:
        """Return a deterministic read-only projection of current orchestrator state.

        This is intentionally derived from existing task records, workflow history,
        policy results, runtime execution metadata, and task artifacts. It never
        mutates the store or creates secondary state.
        """
        tasks = self.store.list_tasks()
        ordered_tasks = sorted(
            tasks,
            key=lambda item: (
                item.get("created_at") or "",
                item.get("task_id") or "",
            ),
        )

        by_status: Dict[str, int] = {}
        task_rows: List[Dict[str, Any]] = []
        runtime_runs: List[Dict[str, Any]] = []
        seen_runs = set()

        snapshot_timestamps = []
        for task in ordered_tasks:
            status = task.get("status") or "UNKNOWN"
            by_status[status] = by_status.get(status, 0) + 1
            snapshot_timestamps.append(task.get("updated_at") or task.get("created_at") or "1970-01-01T00:00:00Z")
            for hist in task.get("history", []) or []:
                if isinstance(hist, dict):
                    snapshot_timestamps.append(hist.get("at") or "1970-01-01T00:00:00Z")
            for art in task.get("artifacts", []) or []:
                if isinstance(art, dict):
                    snapshot_timestamps.append(art.get("created_at") or "1970-01-01T00:00:00Z")

            run_ids = []
            agent_roles = []
            artifact_refs = []
            blockers = []
            policy_decisions = []
            for art in task.get("artifacts", []) or []:
                if not isinstance(art, dict):
                    continue
                art_type = art.get("artifact_type")
                if art_type:
                    artifact_refs.append({
                        "artifact_id": art.get("artifact_id"),
                        "artifact_type": art_type,
                        "run_id": art.get("run_id"),
                        "task_id": art.get("task_id"),
                    })
                content = art.get("content")
                if not isinstance(content, dict):
                    content = {}
                run_id = art.get("run_id")
                agent_role = content.get("agent_role")
                if run_id:
                    run_ids.append(run_id)
                    if agent_role:
                        agent_roles.append(str(agent_role))
                    if not isinstance(art.get("run_id"), type(None)):
                        run_key = (str(task.get("task_id") or ""), str(run_id))
                        if run_key not in seen_runs:
                            seen_runs.add(run_key)
                            runtime_runs.append({
                                "task_id": task.get("task_id"),
                                "run_id": run_id,
                                "agent_role": str(agent_role) if agent_role else "UNKNOWN",
                                "repository_revision": content.get("repository_revision") or task.get("repository_revision"),
                                "created_at": art.get("created_at") or task.get("created_at"),
                                "artifact_type": art_type,
                            })
            for item in task.get("policy_results", []) or []:
                if not isinstance(item, dict):
                    continue
                if item.get("triggered"):
                    policy_decisions.append({
                        "policy_id": item.get("policy_id"),
                        "decision": item.get("decision"),
                        "reason": item.get("reason"),
                    })
                    if item.get("decision") in {"BLOCK", "REQUIRE_SAFETY_REVIEW", "REQUIRE_HUMAN_APPROVAL"}:
                        blockers.append({
                            "policy_id": item.get("policy_id"),
                            "decision": item.get("decision"),
                            "reason": item.get("reason"),
                        })
            task_rows.append({
                "task_id": task.get("task_id"),
                "title": task.get("title"),
                "status": status,
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at"),
                "assigned_agent": task.get("assigned_agent"),
                "retry_count": task.get("attempt", 0),
                "max_attempts": task.get("max_attempts"),
                "repository_revision": task.get("repository_revision"),
                "agent_roles": sorted(set(agent_roles)),
                "active_run_ids": sorted(set(run_ids)),
                "workflow_transitions": task.get("history", []) or [],
                "artifact_refs": artifact_refs,
                "policy_decisions": policy_decisions,
                "blockers": blockers,
                "requires_human_approval": any(item.get("decision") == "REQUIRE_HUMAN_APPROVAL" for item in policy_decisions),
            })

        terminal_states = {"FAILED", "BLOCKED", "ESCALATED", "MERGE", "MONITOR"}
        active_task_count = sum(1 for row in task_rows if row["status"] not in terminal_states)

        ordered_runtime = sorted(
            runtime_runs,
            key=lambda item: (
                item.get("created_at") or "",
                item.get("task_id") or "",
                item.get("run_id") or "",
            ),
        )

        snapshot_time = max(snapshot_timestamps) if snapshot_timestamps else "1970-01-01T00:00:00Z"
        summary = {
            "snapshot_timestamp_utc": snapshot_time,
            "task_count": len(task_rows),
            "active_task_count": active_task_count,
            "by_status": {k: by_status.get(k, 0) for k in sorted(by_status)},
            "blocked_task_count": by_status.get("BLOCKED", 0),
            "failed_task_count": by_status.get("FAILED", 0) + by_status.get("ESCALATED", 0),
            "completed_task_count": by_status.get("MERGE", 0) + by_status.get("MONITOR", 0),
        }

        return {
            "snapshot_timestamp_utc": snapshot_time,
            "summary": summary,
            "tasks": task_rows,
            "runtime": {
                "run_count": len(ordered_runtime),
                "runs": ordered_runtime,
            },
            "source_of_truth": {
                "task_store": "TaskStore.tasks.jsonl",
                "workflow": ".agent/workflows/workflow.json",
                "policies": ".agent/policies/policies.json",
                "runtime": "AgentRuntime._runs",
            },
            "read_only": True,
        }

    def load_master_roadmap(self) -> Dict[str, Any]:
        if self.roadmap_loader is None:
            raise RoadmapValidationError(self.roadmap_error or "Master roadmap is unavailable or malformed.")
        return self.roadmap_loader.document

    def get_roadmap_stage(self, stage_id: str, completed_stage_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        if self.roadmap_loader is None:
            raise RoadmapValidationError(self.roadmap_error or "Master roadmap is unavailable or malformed.")
        stage = self.roadmap_loader.get_stage(stage_id)
        if stage is None:
            raise RoadmapValidationError(f"Unknown roadmap stage_id: {stage_id}")
        stage_payload = dict(stage)
        stage_payload["eligible"] = self.is_roadmap_stage_eligible(stage_id, completed_stage_ids=completed_stage_ids)
        return stage_payload

    def is_roadmap_stage_eligible(self, stage_id: str, completed_stage_ids: Optional[List[str]] = None) -> bool:
        if self.roadmap_loader is None:
            raise RoadmapValidationError(self.roadmap_error or "Master roadmap is unavailable or malformed.")
        return self.roadmap_loader.determine_eligibility(stage_id, completed_stage_ids=completed_stage_ids, repo_root=ROOT)

    def create_task(self, title: str, description: str = "", created_by: str = "system",
                    roadmap_stage_id: Optional[str] = None, roadmap_id: Optional[str] = None,
                    roadmap_version: Optional[str] = None, parent_stage_id: Optional[str] = None,
                    **kwargs) -> Dict[str, Any]:
        metadata: Dict[str, Any] = dict(kwargs)
        if roadmap_stage_id is not None:
            metadata["roadmap_stage_id"] = str(roadmap_stage_id)
            if self.roadmap_loader is not None:
                stage = self.roadmap_loader.get_stage(roadmap_stage_id)
                if stage is None:
                    raise RoadmapValidationError(f"Unknown roadmap stage_id: {roadmap_stage_id}")
                metadata["roadmap_id"] = self.roadmap_loader.document.get("roadmap_id")
                metadata["roadmap_version"] = self.roadmap_loader.document.get("version")
                metadata["parent_stage_id"] = stage.get("parent_stage_id")
                metadata["target_workflow_state"] = stage.get("target_workflow_state")
            else:
                metadata["roadmap_id"] = roadmap_id
                metadata["roadmap_version"] = roadmap_version
                metadata["parent_stage_id"] = parent_stage_id
        else:
            if roadmap_id is not None:
                metadata["roadmap_id"] = roadmap_id
            if roadmap_version is not None:
                metadata["roadmap_version"] = roadmap_version
            if parent_stage_id is not None:
                metadata["parent_stage_id"] = parent_stage_id
        return self.store.create_task(title, description, created_by, extra=metadata)

    def record_ci_result(self, task_id: str, run_id: str, status: str, command: str, evidence: Any,
                        repository_revision: Optional[str] = None, producer: str = "ci") -> Dict[str, Any]:
        task = self.store.read_task(task_id)
        if task is None:
            raise KeyError("task not found")

        repo_rev = repository_revision or task.get("repository_revision")
        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "artifact_type": "ci_results",
            "task_id": task_id,
            "run_id": run_id,
            "repository_revision": repo_rev,
            "producer": producer,
            "created_at": _now_iso(),
            "content": {
                "task_id": task_id,
                "run_id": run_id,
                "repository_revision": repo_rev,
                "status": str(status or "").upper(),
                "command": command,
                "evidence": evidence,
            },
        }

        self.store.append_artifact(task_id, artifact)
        task_spec = task.get("task_spec") or {}
        if not isinstance(task_spec, dict):
            task_spec = {}
        task_spec["ci_results"] = artifact
        if repo_rev is not None:
            task_spec["repository_revision"] = repo_rev
        self.store.update_task(task_id, {"task_spec": task_spec})
        return artifact

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

            if current == target_state and target_state in ("QA", "SAFETY"):
                task_spec = task.get("task_spec") or {}
                if isinstance(task_spec, dict):
                    repo_rev = task_spec.get("repository_revision") or task.get("repository_revision")
                    run_id = task_spec.get("run_id")
                    if repo_rev and run_id:
                        if target_state == "QA":
                            current_fingerprint = self._compute_qa_fingerprint(task_spec)
                            stored_fingerprint = self._get_qa_run_fingerprint(task_id, run_id, agent_role="QA")
                            if stored_fingerprint and stored_fingerprint != current_fingerprint:
                                self.store.append_transition(task_id, "BLOCKED", actor, note="qa_run_id_fingerprint_mismatch")
                                task = self.store.read_task(task_id)
                                task["attempt"] = task.get("attempt", 0) + 1
                                self.store.update_task(task_id, {"attempt": task["attempt"]})
                                if task["attempt"] > getattr(self, "retry_limit", 2):
                                    self.store.append_transition(task_id, "ESCALATED", actor, note="qa_run_id_fingerprint_mismatch")
                                    return {"status": "escalated", "reason": "qa_run_id_fingerprint_mismatch"}
                                return {"status": "blocked", "reason": "qa_run_id_fingerprint_mismatch"}
                        else:
                            current_fingerprint = self._compute_safety_fingerprint(task_spec)
                            stored_fingerprint = self._get_safety_run_fingerprint(task_id, run_id, agent_role="SAFETY")
                            if stored_fingerprint and stored_fingerprint != current_fingerprint:
                                self.store.append_transition(task_id, "BLOCKED", actor, note="safety_run_id_fingerprint_mismatch")
                                task = self.store.read_task(task_id)
                                task["attempt"] = task.get("attempt", 0) + 1
                                self.store.update_task(task_id, {"attempt": task["attempt"]})
                                if task["attempt"] > getattr(self, "retry_limit", 2):
                                    self.store.append_transition(task_id, "ESCALATED", actor, note="safety_run_id_fingerprint_mismatch")
                                    return {"status": "escalated", "reason": "safety_run_id_fingerprint_mismatch"}
                                return {"status": "blocked", "reason": "safety_run_id_fingerprint_mismatch"}

            # idempotency: no-op if already in desired state
            if current == target_state:
                return {"status": "noop", "task": task}

            # Validate state machine
            if not self.wf.validate_transition(current, target_state):
                if current in {"DEVELOPMENT", "CI"} and target_state in {"QA", "SAFETY"}:
                    self.store.append_transition(task_id, "BLOCKED", actor, note=f"invalid_transition:{current}->{target_state}")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "invalid_transition"}
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
                    if current == "HUMAN_APPROVAL" and target_state == "MERGE":
                        # Explicit human approval is already granted for this task; continue to the merge gate.
                        pass
                        
                    elif target_state == "HUMAN_APPROVAL":
                        # proceed to human approval state
                        self.store.append_transition(task_id, "HUMAN_APPROVAL", actor, note=f"policy:{pr.get('policy_id')}")
                        return {"status": "ok", "task": self.store.read_task(task_id)}
                    else:
                        self.store.append_transition(task_id, "PENDING_HUMAN_APPROVAL", actor, note=f"policy:{pr.get('policy_id')}")
                        return {"status": "pending_human_approval", "policy": pr}

            # Loop protection: only trigger when the workflow is oscillating on the same state,
            # not when it is legitimately moving forward through the state machine.
            hist = task.get("history", [])
            loop_threshold = getattr(self, "loop_threshold", 5)
            is_valid_merge_approval = current == "HUMAN_APPROVAL" and target_state == "MERGE"
            recent_states = [entry.get("state") for entry in reversed(hist) if isinstance(entry, dict) and entry.get("state") is not None]
            if not is_valid_merge_approval and recent_states:
                current_run = 0
                last_state = recent_states[0]
                for state in recent_states:
                    if state == last_state:
                        current_run += 1
                    else:
                        break
                if current_run >= loop_threshold:
                    self.store.append_transition(task_id, "ESCALATED", actor, note="loop_detected")
                    return {"status": "escalated", "reason": "loop_detected"}

            if target_state == "READY":
                task_spec = self._materialize_task_spec_from_artifacts(task, task.get("task_spec") or {})
                architecture_result = task_spec.get("architecture_result")
                if not isinstance(architecture_result, dict) or architecture_result.get("artifact_type") != "architecture_result":
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_valid_architecture_result")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_valid_architecture_result"}

                content = architecture_result.get("content") or {}
                required = (
                    "task_id",
                    "run_id",
                    "repository_revision",
                    "architecture_assessment",
                    "affected_components",
                    "proposed_changes",
                    "acceptance_criteria",
                    "developer_specification",
                    "adr_required",
                    "status",
                )
                if not all(k in content for k in required):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_architecture_result")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "malformed_architecture_result"}
                self.store.append_transition(task_id, target_state, actor, note="ready_after_architecture")
                self.store.update_task(task_id, {"attempt": 0})
                return {"status": "ok", "task": self.store.read_task(task_id)}

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
                logical_fingerprint = self._compute_qa_fingerprint(task_spec if isinstance(task_spec, dict) else {})
                invocation_record = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "invocation_record",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "orchestrator",
                    "created_at": _now_iso(),
                    "content": {
                        "agent_role": "ARCHITECT",
                        "repository_revision": repo_rev,
                        "attempt": task.get("attempt", 0),
                        "logical_fingerprint": logical_fingerprint,
                    },
                }
                self.store.append_artifact(task_id, invocation_record)

                # if existing run recorded, try to fetch its result first
                existing_result = runtime.get_result(run_id, agent_role="ARCHITECT")
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

            # Explicit CI gate: required evidence must exist and pass before QA.
            if target_state == "CI":
                task_spec = self._materialize_task_spec_from_artifacts(task, task.get("task_spec") or {})
                task["task_spec"] = task_spec
                self.store.update_task(task_id, {"task_spec": task_spec})

                ci_result = task_spec.get("ci_results")
                if not isinstance(ci_result, dict):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_ci_results")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_ci_results"}

                content = ci_result.get("content") or {}
                ci_status = str(content.get("status") or "").upper()
                if ci_status not in ("PASSED", "PASS"):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="ci_failed")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "ci_failed", "ci_result": content}

                self.store.append_transition(task_id, target_state, actor, note="ci_pass")
                self.store.update_task(task_id, {"attempt": 0})
                return {"status": "ok", "task": self.store.read_task(task_id)}

            # Special handling for QA: invoke QA via AgentRuntime
            if target_state == "QA":
                task_spec = self._materialize_task_spec_from_artifacts(task, task.get("task_spec") or {})
                task["task_spec"] = task_spec
                self.store.update_task(task_id, {"task_spec": task_spec})

                required_inputs = (
                    "task_record",
                    "architecture_result",
                    "repository_context",
                    "repository_revision",
                    "implementation_artifact",
                    "test_manifest",
                    "ci_results",
                )
                missing = [key for key in required_inputs if key not in task_spec or not task_spec.get(key)]
                if missing:
                    self.store.append_transition(task_id, "BLOCKED", actor, note=f"missing_qa_inputs:{','.join(missing)}")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_qa_inputs", "missing": missing}

                ci_result = task_spec.get("ci_results")
                if not isinstance(ci_result, dict) or ci_result.get("artifact_type") != "ci_results":
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_valid_ci_results")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_valid_ci_results"}

                ci_content = (ci_result.get("content") or {})
                if str(ci_content.get("status") or "").upper() not in ("PASSED", "PASS"):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="ci_failed")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "ci_failed"}

                task_record = task_spec.get("task_record") or {}
                if not isinstance(task_record, dict):
                    task_record = {}
                task_record["task_id"] = task_id
                task_record["status"] = "READY"
                task_spec["task_record"] = task_record
                task_spec["task_id"] = task_id

                architecture_result = task_spec.get("architecture_result") or {}
                if isinstance(architecture_result, dict):
                    architecture_result["task_id"] = task_id
                    architecture_result["run_id"] = task_spec.get("run_id") or str(uuid.uuid4())
                    architecture_result["repository_revision"] = task_spec.get("repository_revision") or task.get("repository_revision")
                    task_spec["architecture_result"] = architecture_result

                implementation_artifact = task_spec.get("implementation_artifact") or {}
                if isinstance(implementation_artifact, dict):
                    implementation_artifact["task_id"] = task_id
                    implementation_artifact["run_id"] = task_spec.get("run_id") or str(uuid.uuid4())
                    implementation_artifact["repository_revision"] = task_spec.get("repository_revision") or task.get("repository_revision")
                    task_spec["implementation_artifact"] = implementation_artifact

                test_manifest = task_spec.get("test_manifest") or {}
                if isinstance(test_manifest, dict):
                    test_manifest["task_id"] = task_id
                    test_manifest["run_id"] = task_spec.get("run_id") or str(uuid.uuid4())
                    test_manifest["repository_revision"] = task_spec.get("repository_revision") or task.get("repository_revision")
                    task_spec["test_manifest"] = test_manifest

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

                current_fingerprint = self._compute_qa_fingerprint(task_spec)
                stored_fingerprint = self._get_qa_run_fingerprint(task_id, run_id, agent_role="QA")
                if stored_fingerprint and stored_fingerprint != current_fingerprint:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="qa_run_id_fingerprint_mismatch")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    if task["attempt"] > getattr(self, "retry_limit", 2):
                        self.store.append_transition(task_id, "ESCALATED", actor, note="qa_run_id_fingerprint_mismatch")
                        return {"status": "escalated", "reason": "qa_run_id_fingerprint_mismatch"}
                    return {"status": "blocked", "reason": "qa_run_id_fingerprint_mismatch"}

                inv_req = InvocationRequest(
                    task_id=task_id,
                    agent_role="QA",
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
                runtime.executor = QAExecutor()
                invocation_record = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "invocation_record",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "orchestrator",
                    "created_at": _now_iso(),
                    "content": {
                        "agent_role": "QA",
                        "repository_revision": repo_rev,
                        "attempt": task.get("attempt", 0),
                        "logical_fingerprint": current_fingerprint,
                    },
                }
                self.store.append_artifact(task_id, invocation_record)

                existing_result = runtime.get_result(run_id, agent_role="QA")
                result = existing_result if existing_result is not None else runtime.invoke(inv_req)

                result_art = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "agent_result",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "qa_runtime",
                    "created_at": _now_iso(),
                    "content": {
                        "status": result.status,
                        "started_at": result.started_at,
                        "completed_at": result.completed_at,
                        "error": result.error,
                    },
                }
                self.store.append_artifact(task_id, result_art)

                if result.status in ("FAILED", "TIMED_OUT", "CANCELLED", "BLOCKED"):
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    if task["attempt"] > getattr(self, "retry_limit", 2):
                        self.store.append_transition(task_id, "ESCALATED", actor, note="qa_failed")
                        return {"status": "escalated", "reason": "qa_failed"}
                    self.store.append_transition(task_id, "BLOCKED", actor, note="qa_failed")
                    return {"status": "blocked", "reason": "qa_failed"}

                output_arts = result.output_artifacts or []
                if not output_arts:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="no_qa_artifacts")
                    return {"status": "blocked", "reason": "no_qa_artifacts"}

                required_env = ("artifact_id", "artifact_type", "task_id", "run_id", "repository_revision", "producer", "created_at", "content")
                qa_result = None
                defect_report = None
                for art in output_arts:
                    if not all(k in art for k in required_env):
                        self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_qa_envelope")
                        return {"status": "blocked", "reason": "malformed_qa_envelope"}
                    if art.get("artifact_type") == "qa_result":
                        qa_result = art
                    if art.get("artifact_type") == "defect_report":
                        defect_report = art

                if qa_result is None:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_qa_result")
                    return {"status": "blocked", "reason": "missing_qa_result"}
                if defect_report is None:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_defect_report")
                    return {"status": "blocked", "reason": "missing_defect_report"}

                qa_content = qa_result.get("content") or {}
                defect_content = defect_report.get("content") or {}
                qa_required = ("task_id", "run_id", "repository_revision", "decision", "verification_summary", "evidence_references", "defects", "limitations", "safety_relevant_findings")
                if not all(k in qa_content for k in qa_required):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_qa_result")
                    return {"status": "blocked", "reason": "malformed_qa_result"}
                if qa_content.get("task_id") != task_id:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="task_mismatch")
                    return {"status": "blocked", "reason": "task_mismatch"}
                if qa_content.get("run_id") != run_id:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="run_id_mismatch")
                    return {"status": "blocked", "reason": "run_id_mismatch"}
                if str(qa_content.get("repository_revision")) != str(repo_rev):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="repository_revision_mismatch")
                    return {"status": "blocked", "reason": "repository_revision_mismatch"}

                defect_required = ("task_id", "run_id", "repository_revision", "defects")
                if not all(k in defect_content for k in defect_required):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_defect_report")
                    return {"status": "blocked", "reason": "malformed_defect_report"}
                if defect_content.get("task_id") != task_id:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="defect_task_mismatch")
                    return {"status": "blocked", "reason": "defect_task_mismatch"}
                if defect_content.get("run_id") != run_id:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="defect_run_id_mismatch")
                    return {"status": "blocked", "reason": "defect_run_id_mismatch"}
                if str(defect_content.get("repository_revision")) != str(repo_rev):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="defect_repository_revision_mismatch")
                    return {"status": "blocked", "reason": "defect_repository_revision_mismatch"}

                self.store.append_artifact(task_id, qa_result)
                self.store.append_artifact(task_id, defect_report)

                decision = str(qa_content.get("decision") or "").upper()
                if decision not in ("PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="invalid_qa_decision")
                    return {"status": "blocked", "reason": "invalid_qa_decision"}

                # QA decides verification state; Orchestrator applies workflow consequence.
                if decision == "PASS":
                    self.store.append_transition(task_id, target_state, actor, note="qa_pass")
                    self.store.update_task(task_id, {"attempt": 0})
                    return {"status": "ok", "task": self.store.read_task(task_id)}

                self.store.append_transition(task_id, "BLOCKED", actor, note=f"qa_{decision.lower()}")
                task = self.store.read_task(task_id)
                task["attempt"] = task.get("attempt", 0) + 1
                self.store.update_task(task_id, {"attempt": task["attempt"]})
                if task["attempt"] > getattr(self, "retry_limit", 2):
                    self.store.append_transition(task_id, "ESCALATED", actor, note="qa_retry_limit_exceeded")
                    return {"status": "escalated", "reason": "qa_retry_limit_exceeded"}
                return {"status": "blocked", "reason": decision.lower(), "qa_result": qa_content}

            # Special handling for SAFETY: invoke Safety via AgentRuntime
            if target_state == "SAFETY":
                task_spec = self._materialize_task_spec_from_artifacts(task, task.get("task_spec") or {})
                task["task_spec"] = task_spec
                self.store.update_task(task_id, {"task_spec": task_spec})
                if not isinstance(task_spec, dict):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_safety_task_spec")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_safety_task_spec"}

                required_inputs = (
                    "task_record",
                    "architecture_result",
                    "repository_context",
                    "repository_revision",
                    "implementation_artifact",
                    "test_manifest",
                    "qa_result",
                )
                missing = [key for key in required_inputs if key not in task_spec or not task_spec.get(key)]
                if missing:
                    self.store.append_transition(task_id, "BLOCKED", actor, note=f"missing_safety_inputs:{','.join(missing)}")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_safety_inputs", "missing": missing}

                qa_result = task_spec.get("qa_result")
                if not isinstance(qa_result, dict) or qa_result.get("artifact_type") != "qa_result":
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_valid_qa_result")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    return {"status": "blocked", "reason": "missing_valid_qa_result"}

                task_record = task_spec.get("task_record") or {}
                if not isinstance(task_record, dict):
                    task_record = {}
                task_record["task_id"] = task_id
                task_record["status"] = "QA"
                task_spec["task_record"] = task_record
                task_spec["task_id"] = task_id

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

                current_fingerprint = self._compute_safety_fingerprint(task_spec)
                stored_fingerprint = self._get_safety_run_fingerprint(task_id, run_id, agent_role="SAFETY")
                if stored_fingerprint and stored_fingerprint != current_fingerprint:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="safety_run_id_fingerprint_mismatch")
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    if task["attempt"] > getattr(self, "retry_limit", 2):
                        self.store.append_transition(task_id, "ESCALATED", actor, note="safety_run_id_fingerprint_mismatch")
                        return {"status": "escalated", "reason": "safety_run_id_fingerprint_mismatch"}
                    return {"status": "blocked", "reason": "safety_run_id_fingerprint_mismatch"}

                inv_req = InvocationRequest(
                    task_id=task_id,
                    agent_role="SAFETY",
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
                runtime.executor = SafetyExecutor()
                invocation_record = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "invocation_record",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "orchestrator",
                    "created_at": _now_iso(),
                    "content": {
                        "agent_role": "SAFETY",
                        "repository_revision": repo_rev,
                        "attempt": task.get("attempt", 0),
                        "logical_fingerprint": current_fingerprint,
                    },
                }
                self.store.append_artifact(task_id, invocation_record)

                existing_result = runtime.get_result(run_id, agent_role="SAFETY")
                result = existing_result if existing_result is not None else runtime.invoke(inv_req)

                result_art = {
                    "artifact_id": str(uuid.uuid4()),
                    "artifact_type": "agent_result",
                    "task_id": task_id,
                    "run_id": run_id,
                    "producer": "safety_runtime",
                    "created_at": _now_iso(),
                    "content": {
                        "status": result.status,
                        "started_at": result.started_at,
                        "completed_at": result.completed_at,
                        "error": result.error,
                    },
                }
                self.store.append_artifact(task_id, result_art)

                if result.status in ("FAILED", "TIMED_OUT", "CANCELLED", "BLOCKED"):
                    task = self.store.read_task(task_id)
                    task["attempt"] = task.get("attempt", 0) + 1
                    self.store.update_task(task_id, {"attempt": task["attempt"]})
                    if task["attempt"] > getattr(self, "retry_limit", 2):
                        self.store.append_transition(task_id, "ESCALATED", actor, note="safety_failed")
                        return {"status": "escalated", "reason": "safety_failed"}
                    self.store.append_transition(task_id, "BLOCKED", actor, note="safety_failed")
                    return {"status": "blocked", "reason": "safety_failed"}

                output_arts = result.output_artifacts or []
                if not output_arts:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="no_safety_result")
                    return {"status": "blocked", "reason": "no_safety_result"}

                required_env = ("artifact_id", "artifact_type", "task_id", "run_id", "repository_revision", "producer", "created_at", "content")
                safety_result = None
                for art in output_arts:
                    if not all(k in art for k in required_env):
                        self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_safety_envelope")
                        return {"status": "blocked", "reason": "malformed_safety_envelope"}
                    if art.get("artifact_type") == "safety_result":
                        safety_result = art

                if safety_result is None:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_safety_result")
                    return {"status": "blocked", "reason": "missing_safety_result"}

                safety_content = safety_result.get("content") or {}
                safety_required = (
                    "task_id",
                    "run_id",
                    "repository_revision",
                    "decision",
                    "severity",
                    "evidence",
                    "findings",
                    "blocking_status",
                    "limitations",
                    "recommended_mitigations",
                    "requires_human_approval",
                )
                if not all(k in safety_content for k in safety_required):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="malformed_safety_result")
                    return {"status": "blocked", "reason": "malformed_safety_result"}
                if safety_content.get("task_id") != task_id:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="task_mismatch")
                    return {"status": "blocked", "reason": "task_mismatch"}
                if safety_content.get("run_id") != run_id:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="run_id_mismatch")
                    return {"status": "blocked", "reason": "run_id_mismatch"}
                if str(safety_content.get("repository_revision")) != str(repo_rev):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="repository_revision_mismatch")
                    return {"status": "blocked", "reason": "repository_revision_mismatch"}

                decision = str(safety_content.get("decision") or "").upper()
                if decision not in ("PASS", "FAIL", "BLOCKED", "INCONCLUSIVE", "REQUIRE_HUMAN_APPROVAL"):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="invalid_safety_decision")
                    return {"status": "blocked", "reason": "invalid_safety_decision"}

                self.store.append_artifact(task_id, safety_result)

                if decision == "PASS":
                    self.store.append_transition(task_id, target_state, actor, note="safety_pass")
                    self.store.update_task(task_id, {"attempt": 0})
                    return {"status": "ok", "task": self.store.read_task(task_id)}

                if decision == "REQUIRE_HUMAN_APPROVAL":
                    self.store.append_transition(task_id, "HUMAN_APPROVAL", actor, note="safety_requires_human_approval")
                    self.store.update_task(task_id, {"attempt": 0})
                    return {"status": "ok", "decision": decision, "task": self.store.read_task(task_id)}

                self.store.append_transition(task_id, "BLOCKED", actor, note=f"safety_{decision.lower()}")
                task = self.store.read_task(task_id)
                task["attempt"] = task.get("attempt", 0) + 1
                self.store.update_task(task_id, {"attempt": task["attempt"]})
                if task["attempt"] > getattr(self, "retry_limit", 2):
                    self.store.append_transition(task_id, "ESCALATED", actor, note="safety_retry_limit_exceeded")
                    return {"status": "escalated", "reason": "safety_retry_limit_exceeded"}
                return {"status": "blocked", "reason": decision.lower(), "safety_result": safety_content}

            if target_state == "HUMAN_APPROVAL":
                task_spec = self._materialize_task_spec_from_artifacts(task, task.get("task_spec") or {})
                task["task_spec"] = task_spec
                self.store.update_task(task_id, {"task_spec": task_spec})

                approval = task_spec.get("human_approval_record")
                if approval is None:
                    self.store.append_transition(task_id, "BLOCKED", actor, note="missing_human_approval_record")
                    return {"status": "blocked", "reason": "missing_human_approval_record"}
                if not approval.get("approved", False):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="human_approval_rejected")
                    return {"status": "blocked", "reason": "human_approval_rejected"}

                self.store.append_transition(task_id, target_state, actor, note="human_approval_granted")
                self.store.update_task(task_id, {"attempt": 0})
                return {"status": "ok", "task": self.store.read_task(task_id)}

            if target_state == "MERGE":
                task_spec = self._materialize_task_spec_from_artifacts(task, task.get("task_spec") or {})
                task["task_spec"] = task_spec
                self.store.update_task(task_id, {"task_spec": task_spec})
                approval = task_spec.get("human_approval_record")
                if approval is None or not approval.get("approved", False):
                    self.store.append_transition(task_id, "BLOCKED", actor, note="merge_requires_human_approval")
                    return {"status": "blocked", "reason": "merge_requires_human_approval"}

                self.store.append_transition(task_id, target_state, actor, note="merge_gate_eligible")
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
                existing_result = runtime.get_result(run_id, agent_role="DEVELOPER")
                result = existing_result if existing_result is not None else runtime.invoke(inv_req)

                if result.status not in ("FAILED", "TIMED_OUT", "CANCELLED"):
                    invocation_record = {
                        "artifact_id": str(uuid.uuid4()),
                        "artifact_type": "invocation_record",
                        "task_id": task_id,
                        "run_id": run_id,
                        "producer": "orchestrator",
                        "created_at": _now_iso(),
                        "content": {
                            "agent_role": "DEVELOPER",
                            "repository_revision": repo_rev,
                            "attempt": task.get("attempt", 0),
                            "logical_fingerprint": None,
                        },
                    }
                    self.store.append_artifact(task_id, invocation_record)

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

                for art in normalized_output:
                    if art.get("artifact_type") == "implementation_artifact":
                        task_spec["implementation_artifact"] = art
                    elif art.get("artifact_type") == "test_manifest":
                        task_spec["test_manifest"] = art
                task_spec["run_id"] = run_id
                task["task_spec"] = task_spec
                self.store.update_task(task_id, {"task_spec": task_spec})

                logical_fingerprint = self._compute_qa_fingerprint(task_spec)
                task_record = self.store.read_task(task_id)
                for artifact in reversed(task_record.get("artifacts", [])):
                    if artifact.get("artifact_type") != "invocation_record":
                        continue
                    content = artifact.get("content") or {}
                    if artifact.get("run_id") == run_id and content.get("agent_role") == "DEVELOPER":
                        artifact["content"] = {**content, "logical_fingerprint": logical_fingerprint}
                        self.store.update_task(task_id, {"artifacts": task_record["artifacts"]})
                        break

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
