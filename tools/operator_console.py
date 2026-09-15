"""Thin interactive operator console for the existing Orchestrator.

This module is purposely small: it does not maintain its own authoritative state,
workflow engine, or task store. It reads the canonical Orchestrator state and
routes operator actions through the existing APIs.
"""

from __future__ import annotations

import shlex
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.orchestrator_core import Orchestrator


class OperatorConsole:
    """Minimal terminal UX that calls into the authoritative Orchestrator."""

    def __init__(self, orch: Optional[Orchestrator] = None):
        self.orch = orch or Orchestrator()

    @staticmethod
    def _redact_sensitive_value(value: Any) -> Any:
        if isinstance(value, dict):
            redacted = {}
            for key, item in value.items():
                key_lower = str(key).lower()
                if any(token in key_lower for token in ("secret", "token", "key", "password", "passwd", "authorization", "bearer", "credential")):
                    redacted[key] = "[REDACTED]"
                else:
                    redacted[key] = OperatorConsole._redact_sensitive_value(item)
            return redacted
        if isinstance(value, list):
            return [OperatorConsole._redact_sensitive_value(item) for item in value]
        if isinstance(value, str):
            if any(token in value.lower() for token in ("sk_live_", "pk_live_", "api_key", "token", "password", "secret")):
                return "[REDACTED]"
            return value
        return value

    @staticmethod
    def _summarize_content(content: Any, max_items: int = 4) -> str:
        if not content:
            return "(no content)"
        if isinstance(content, dict):
            summary_parts = []
            for key, value in list(content.items())[:max_items]:
                key_lower = str(key).lower()
                if any(token in key_lower for token in ("secret", "token", "key", "password", "passwd", "authorization", "bearer", "credential")):
                    summary_parts.append(f"{key}=[REDACTED]")
                else:
                    summary_parts.append(f"{key}={value}")
            if len(content) > max_items:
                summary_parts.append("...")
            return ", ".join(summary_parts)
        if isinstance(content, list):
            return f"[{len(content)} item(s)]"
        return str(content)

    def _render_status(self) -> str:
        snapshot = self.orch.build_operator_snapshot()
        summary = snapshot.get("summary") or {}
        tasks = snapshot.get("tasks") or []
        lines = [
            "[INFO] SYSTEM STATUS",
            f"- task_count: {summary.get('task_count', 0)}",
            f"- active_task_count: {summary.get('active_task_count', 0)}",
            f"- blocked_task_count: {summary.get('blocked_task_count', 0)}",
            f"- failed_task_count: {summary.get('failed_task_count', 0)}",
            f"- snapshot_timestamp_utc: {snapshot.get('snapshot_timestamp_utc', 'unknown')}",
            f"- by_status: {summary.get('by_status', {})}",
        ]
        if not tasks:
            lines.append("- No active tasks")
            return "\n".join(lines)

        lines.append("- Active tasks:")
        for task in tasks[:5]:
            lines.append(
                f"  * {task.get('task_id', 'unknown')} | "
                f"status={task.get('status', 'UNKNOWN')} | "
                f"agent={task.get('assigned_agent') or 'unassigned'} | "
                f"roadmap={task.get('roadmap_stage_id', 'n/a')}"
            )
        return "\n".join(lines)

    def _render_tasks(self) -> str:
        tasks = self.orch.store.list_tasks()
        if not tasks:
            return "[INFO] No tasks found."

        lines = ["[INFO] TASKS"]
        for task in sorted(tasks, key=lambda item: item.get("created_at") or ""):
            lines.append(
                f"- {task.get('task_id', 'unknown')} | {task.get('title', 'untitled')} | "
                f"status={task.get('status', 'UNKNOWN')} | "
                f"agent={task.get('assigned_agent') or 'unassigned'} | "
                f"roadmap={task.get('roadmap_stage_id', 'n/a')}"
            )
        return "\n".join(lines)

    def _render_task(self, task_id: str) -> str:
        task = self.orch.store.read_task(task_id)
        if task is None:
            return f"[ERROR] Task not found: {task_id}"

        lines = [
            "[INFO] TASK DETAILS",
            f"- task_id: {task.get('task_id')}",
            f"- title: {task.get('title', 'untitled')}",
            f"- description: {task.get('description', '')}",
            f"- workflow_state: {task.get('status', 'UNKNOWN')}",
            f"- roadmap_stage_id: {task.get('roadmap_stage_id', 'n/a')}",
            f"- assigned_agent: {task.get('assigned_agent') or 'unassigned'}",
            f"- created_by: {task.get('created_by', 'unknown')}",
            f"- updated_at: {task.get('updated_at', 'unknown')}",
        ]

        history = task.get("history") or []
        if history:
            latest = history[-1]
            lines.append(f"- latest_history_event: {latest.get('state')} @ {latest.get('at')} by {latest.get('actor')}")

        policy_results = task.get("policy_results") or []
        if policy_results:
            lines.append("- policy_results:")
            for item in policy_results[-5:]:
                details = item.get("reason") or item.get("message") or "no further detail"
                lines.append(f"  * {item.get('policy_id')}: {item.get('decision')} ({details})")

        artifacts = task.get("artifacts") or []
        if artifacts:
            lines.append("- artifact_refs:")
            for art in artifacts[-5:]:
                if not isinstance(art, dict):
                    continue
                lines.append(
                    f"  * {art.get('artifact_id', 'unknown')} | "
                    f"type={art.get('artifact_type', 'unknown')} | "
                    f"run_id={art.get('run_id') or 'n/a'} | "
                    f"producer={art.get('producer') or 'unknown'}"
                )

        task_spec = task.get("task_spec") or {}
        if isinstance(task_spec, dict):
            human_approval = task_spec.get("human_approval_record")
            if human_approval:
                lines.append(f"- latest_result: human_approval_record={human_approval.get('decision')} by {human_approval.get('actor')}")

        next_action = task.get("next_action") or task.get("target_workflow_state") or task.get("status")
        if next_action:
            lines.append(f"- next_action: {next_action}")

        return "\n".join(lines)

    def _render_history(self, task_id: str) -> str:
        task = self.orch.store.read_task(task_id)
        if task is None:
            return f"[ERROR] Task not found: {task_id}"

        history = task.get("history") or []
        if not history:
            return "[INFO] TASK HISTORY\n- No history found for this task."

        lines = ["[INFO] TASK HISTORY"]
        for item in history:
            if not isinstance(item, dict):
                continue
            prev_state = item.get("previous_state") or item.get("from") or "unknown"
            new_state = item.get("state") or item.get("to") or item.get("status") or "unknown"
            actor = item.get("actor") or "unknown"
            timestamp = item.get("at") or item.get("timestamp") or "unknown"
            note = item.get("note") or item.get("reason") or item.get("details")
            lines.append(f"- {timestamp} | {prev_state} -> {new_state} | actor={actor}")
            if note:
                safe_note = self._summarize_content(self._redact_sensitive_value({"note": note}), max_items=1)
                lines.append(f"  * note: {safe_note}")
        return "\n".join(lines)

    def _render_evidence(self, task_id: str) -> str:
        task = self.orch.store.read_task(task_id)
        if task is None:
            return f"[ERROR] Task not found: {task_id}"

        artifacts = task.get("artifacts") or []
        if not artifacts:
            return "[INFO] TASK EVIDENCE\n- No evidence found for this task."

        lines = ["[INFO] TASK EVIDENCE"]
        for art in artifacts:
            if not isinstance(art, dict):
                continue
            content = art.get("content") or {}
            artifact_id = art.get("artifact_id", "unknown")
            artifact_type = art.get("artifact_type", "unknown")
            run_id = art.get("run_id") or "n/a"
            producer = art.get("producer") or "unknown"
            created_at = art.get("created_at") or "unknown"
            summary = self._summarize_content(self._redact_sensitive_value(content), max_items=4)
            lines.append(
                f"- {artifact_id} | type={artifact_type} | task_id={art.get('task_id') or task_id} | "
                f"run_id={run_id} | producer={producer} | created_at={created_at}"
            )
            lines.append(f"  * summary: {summary}")
        return "\n".join(lines)

    def _approval_usage(self, action: str) -> str:
        return (
            f"[VALIDATION ERROR] Usage: {action} <task_id> --actor <actor> --reason \"<reason>\" "
            f"[--evidence <artifact_id>:<artifact_type> ...] [--confirm yes|no]"
        )

    def _parse_evidence_refs(self, task: Dict[str, Any], evidence_specs: List[str]) -> List[Dict[str, Any]]:
        if not evidence_specs:
            return []

        artifact_by_id = {}
        for art in task.get("artifacts") or []:
            if isinstance(art, dict):
                artifact_by_id[art.get("artifact_id")] = art

        refs: List[Dict[str, Any]] = []
        for spec in evidence_specs:
            if not spec:
                continue
            candidates = []
            if ":" in spec:
                candidates = [spec]
            else:
                candidates = [spec]
            for item in candidates:
                text = item.strip()
                if not text:
                    continue
                parts = [p.strip() for p in text.split(":", 1)]
                if len(parts) == 2 and parts[0] and parts[1]:
                    artifact_id, artifact_type = parts
                    art = artifact_by_id.get(artifact_id)
                    if art is None:
                        raise ValueError(f"unknown evidence artifact_id: {artifact_id}")
                    if art.get("artifact_type") and art.get("artifact_type") != artifact_type:
                        raise ValueError(f"evidence artifact_type mismatch for {artifact_id}: {artifact_type}")
                    refs.append({"artifact_id": artifact_id, "artifact_type": artifact_type})
                else:
                    raise ValueError(f"invalid evidence format: {text}; expected <artifact_id>:<artifact_type>")
        return refs

    def _handle_approval_action(self, decision: str, task_id: str, actor: Optional[str] = None,
                               reason: Optional[str] = None, evidence_specs: Optional[List[str]] = None,
                               confirm: Optional[str] = None) -> str:
        task = self.orch.store.read_task(task_id)
        if task is None:
            return f"[ERROR] Task not found: {task_id}"

        if task.get("status") != "HUMAN_APPROVAL":
            return f"[ERROR] Task {task_id} is not awaiting human approval. Current state: {task.get('status', 'UNKNOWN')}"

        requires_human_approval = any(
            (item.get("triggered") is True and str(item.get("decision") or "").upper() == "REQUIRE_HUMAN_APPROVAL")
            for item in (task.get("policy_results") or [])
            if isinstance(item, dict)
        )
        if not requires_human_approval:
            return f"[ERROR] Task {task_id} does not currently require human approval."

        if not actor or not str(actor).strip():
            return "[VALIDATION ERROR] actor is required for this approval decision."
        if not reason or not str(reason).strip():
            return "[VALIDATION ERROR] reason is required for this approval decision."

        if confirm is None or str(confirm).strip().lower() not in {"y", "yes", "true", "1"}:
            return (
                f"[INFO] {decision} pending for task {task_id}\n"
                f"- task: {task.get('title', 'untitled')}\n"
                f"- current_state: {task.get('status', 'UNKNOWN')}\n"
                f"- actor: {actor}\n"
                f"- reason: {reason}\n"
                f"- policy_context: {next((item for item in (task.get('policy_results') or []) if isinstance(item, dict) and str(item.get('decision') or '').upper() == 'REQUIRE_HUMAN_APPROVAL'), {})}\n"
                "Confirm decision? Use --confirm yes to submit the decision."
            )

        try:
            evidence_refs = self._parse_evidence_refs(task, evidence_specs or [])
        except ValueError as exc:
            return f"[ERROR] Invalid evidence reference: {exc}"

        policy_context = next(
            (item for item in (task.get("policy_results") or []) if isinstance(item, dict) and str(item.get("decision") or "").upper() == "REQUIRE_HUMAN_APPROVAL"),
            {},
        )

        try:
            record = self.orch.record_human_approval(
                task_id=task_id,
                decision=decision,
                actor=str(actor).strip(),
                reason=str(reason).strip(),
                evidence_refs=evidence_refs,
                timestamp_utc=datetime.utcnow().isoformat() + "Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context=policy_context,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            return f"[ERROR] Orchestrator rejected {decision} for task {task_id}: {exc}"

        task_after = self.orch.store.read_task(task_id)
        return (
            f"[SUCCESS] {decision} recorded for task {task_id}\n"
            f"- task: {task_after.get('title', 'untitled')}\n"
            f"- workflow_state: {task_after.get('status', 'UNKNOWN')}\n"
            f"- actor: {record.get('actor')}\n"
            f"- reason: {record.get('reason')}\n"
            f"- approval_record_id: {record.get('approval_record_id')}\n"
            f"- evidence_refs: {record.get('evidence_refs') or '[]'}"
        )

    def _handle_create(self, value: str) -> str:
        stage_id = value.strip()
        if not stage_id:
            return "[ERROR] create requires a roadmap stage ID, e.g. create 6C.2"
        try:
            task = self.orch.create_task(f"operator-created-{stage_id}", description=f"Operator-created task for {stage_id}", created_by="operator", roadmap_stage_id=stage_id)
        except Exception as exc:  # pragma: no cover - defensive guard
            return f"[BLOCKED] Unable to create task for {stage_id}: {exc}"
        return f"[SUCCESS] Created task {task.get('task_id')} for roadmap stage {stage_id}"

    def _handle_next(self) -> str:
        tasks = self.orch.store.list_tasks()
        if not tasks:
            return "[INFO] No actionable work. There are currently no tasks in the authoritative task store."

        ordered = sorted(tasks, key=lambda item: (item.get("created_at") or "", item.get("task_id") or ""))
        task_rows = []
        for task in ordered:
            if not isinstance(task, dict):
                continue
            status = str(task.get("status") or "UNKNOWN").upper()
            policy_results = task.get("policy_results") or []
            blockers = []
            for item in policy_results:
                if not isinstance(item, dict):
                    continue
                if item.get("triggered") and str(item.get("decision") or "").upper() in {"BLOCK", "REQUIRE_SAFETY_REVIEW", "REQUIRE_HUMAN_APPROVAL"}:
                    blockers.append(item)
            requires_human_approval = any(
                isinstance(item, dict) and item.get("triggered") is True and str(item.get("decision") or "").upper() == "REQUIRE_HUMAN_APPROVAL"
                for item in policy_results
            )
            task_rows.append({
                "task": task,
                "status": status,
                "requires_human_approval": requires_human_approval,
                "blockers": blockers,
            })

        def rank(entry):
            status = entry["status"]
            if entry["requires_human_approval"] and status == "HUMAN_APPROVAL":
                return 0
            if status in {"BLOCKED", "FAILED", "ESCALATED"}:
                return 1
            if status in {"PENDING_HUMAN_APPROVAL", "PENDING_SAFETY_REVIEW"}:
                return 2
            if status in {"QA", "SAFETY", "DEVELOPMENT", "CI", "ARCHITECTURE", "READY", "BACKLOG", "TRIAGE"}:
                return 3
            if status in {"MERGE", "MONITOR"}:
                return 4
            return 5

        selected = sorted(task_rows, key=lambda e: (rank(e), e["task"].get("created_at") or "", e["task"].get("task_id") or ""))[0]
        task = selected["task"]
        status = str(task.get("status") or "UNKNOWN").upper()

        if selected["requires_human_approval"] and status == "HUMAN_APPROVAL":
            reason = ""
            for item in task.get("policy_results") or []:
                if isinstance(item, dict) and item.get("triggered") and str(item.get("decision") or "").upper() == "REQUIRE_HUMAN_APPROVAL":
                    reason = str(item.get("reason") or item.get("message") or "human approval required")
                    break
            return (
                "[INFO] NEXT ACTION\n"
                f"- priority: HUMAN_REQUIRED\n"
                f"- task_id: {task.get('task_id')}\n"
                f"- title: {task.get('title', 'untitled')}\n"
                f"- current_state: {status}\n"
                f"- reason: {reason}\n"
                f"- operator_action: approve {task.get('task_id')} or reject {task.get('task_id')}"
            )

        if status in {"BLOCKED", "FAILED", "ESCALATED"}:
            blockers = selected["blockers"]
            blocker_reason = ""
            if blockers:
                blocker_reason = str(blockers[0].get("reason") or blockers[0].get("message") or blockers[0].get("decision") or "blocked")
            else:
                blocker_reason = str(task.get("status") or "blocked")
            return (
                "[INFO] NEXT ACTION\n"
                f"- priority: BLOCKED\n"
                f"- task_id: {task.get('task_id')}\n"
                f"- title: {task.get('title', 'untitled')}\n"
                f"- current_state: {status}\n"
                f"- blocker: {blocker_reason}\n"
                f"- next_step: human intervention or the responsible agent is required; no automated transition was performed."
            )

        if status in {"QA", "SAFETY", "DEVELOPMENT", "CI", "ARCHITECTURE", "TRIAGE"}:
            agent = task.get("assigned_agent") or "unassigned"
            return (
                "[INFO] NEXT ACTION\n"
                f"- priority: ACTIVE\n"
                f"- task_id: {task.get('task_id')}\n"
                f"- title: {task.get('title', 'untitled')}\n"
                f"- current_state: {status}\n"
                f"- assigned_agent: {agent}\n"
                "- next_step: the workflow is already progressing automatically; no human mutation is required."
            )

        if status in {"READY", "BACKLOG", "PENDING_HUMAN_APPROVAL", "PENDING_SAFETY_REVIEW"}:
            stage = task.get("roadmap_stage_id") or task.get("parent_stage_id") or "n/a"
            agent = task.get("assigned_agent") or "unassigned"
            return (
                "[INFO] NEXT ACTION\n"
                f"- priority: READY\n"
                f"- task_id: {task.get('task_id')}\n"
                f"- title: {task.get('title', 'untitled')}\n"
                f"- current_state: {status}\n"
                f"- roadmap_stage_id: {stage}\n"
                f"- assigned_agent: {agent}\n"
                "- next_step: proceed according to the existing authoritative workflow and task state; no automatic transition was made."
            )

        return (
            "[INFO] NEXT ACTION\n"
            "- priority: NONE\n"
            "- NO operator action required at this time; the current task graph does not require a manual workflow decision."
        )

    def _handle_dispatch(self) -> str:
        try:
            result = self.orch.dispatch_next_task()
        except Exception as exc:  # pragma: no cover - defensive guard
            return f"[ERROR] Dispatch failed: {exc}"

        payload = result if isinstance(result, dict) else {}
        status = str(payload.get("status") or "UNKNOWN").upper()
        task_id = payload.get("task_id") or "n/a"
        reason = payload.get("reason") or (payload.get("result") or {}).get("reason") or "no action"

        if status in {"NOOP", "NO_ACTIONABLE_TASK", "NO_TASKS"}:
            return (
                "[INFO] DISPATCH\n"
                f"- status: {status}\n"
                f"- task_id: {task_id}\n"
                f"- reason: {reason}"
            )

        if status in {"BLOCKED", "FAILED", "ESCALATED"}:
            return (
                "[WARN] DISPATCH\n"
                f"- status: {status}\n"
                f"- task_id: {task_id}\n"
                f"- reason: {reason}"
            )

        return (
            "[SUCCESS] DISPATCH\n"
            f"- task_id: {task_id}\n"
            f"- status: {status}\n"
            f"- result: {payload.get('result') or reason}"
        )

    def _handle_help(self) -> str:
        return (
            "[INFO] Available commands:\n"
            "  status             - show current orchestrator status\n"
            "  tasks              - list tasks\n"
            "  show <task_id>     - inspect a task\n"
            "  history <task_id>  - render task history\n"
            "  evidence <task_id> - render task evidence\n"
            "  approve <task_id>  - submit a human approval through the Orchestrator\n"
            "  reject <task_id>   - submit a human rejection through the Orchestrator\n"
            "  create <stage_id>  - create a task through the orchestrator\n"
            "  dispatch           - execute the next deterministic operator action through the Orchestrator\n"
            "  next               - show the next deterministic operator action\n"
            "  help               - show this help\n"
            "  exit               - terminate the console"
        )

    def handle_command(self, raw_command: str) -> str:
        command = (raw_command or "").strip()
        if not command:
            return "[INFO] No command entered. Type 'help' for instructions."

        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            return f"[VALIDATION ERROR] Invalid command syntax: {exc}"

        name = tokens[0].lower()

        if name == "status":
            return self._render_status()
        if name == "tasks":
            return self._render_tasks()
        if name == "show":
            if len(tokens) < 2:
                return "[VALIDATION ERROR] Usage: show <task_id>"
            return self._render_task(tokens[1])
        if name == "history":
            if len(tokens) < 2:
                return "[VALIDATION ERROR] Usage: history <task_id>"
            return self._render_history(tokens[1])
        if name == "evidence":
            if len(tokens) < 2:
                return "[VALIDATION ERROR] Usage: evidence <task_id>"
            return self._render_evidence(tokens[1])
        if name == "approve":
            if len(tokens) < 2:
                return self._approval_usage("approve")
            task_id = tokens[1]
            arg_map = {}
            i = 2
            while i < len(tokens):
                key = tokens[i]
                if key in {"--actor", "-a"}:
                    if i + 1 >= len(tokens):
                        return self._approval_usage("approve")
                    arg_map["actor"] = tokens[i + 1]
                    i += 2
                    continue
                if key in {"--reason", "-r"}:
                    if i + 1 >= len(tokens):
                        return self._approval_usage("approve")
                    arg_map["reason"] = tokens[i + 1]
                    i += 2
                    continue
                if key in {"--evidence", "-e"}:
                    evidence_values = []
                    i += 1
                    while i < len(tokens) and not tokens[i].startswith("--"):
                        evidence_values.append(tokens[i])
                        i += 1
                    arg_map.setdefault("evidence", []).extend(evidence_values)
                    continue
                if key in {"--confirm", "-c"}:
                    if i + 1 >= len(tokens):
                        return self._approval_usage("approve")
                    arg_map["confirm"] = tokens[i + 1]
                    i += 2
                    continue
                return self._approval_usage("approve")
            return self._handle_approval_action(
                "APPROVE",
                task_id,
                actor=arg_map.get("actor"),
                reason=arg_map.get("reason"),
                evidence_specs=arg_map.get("evidence", []),
                confirm=arg_map.get("confirm"),
            )
        if name == "reject":
            if len(tokens) < 2:
                return self._approval_usage("reject")
            task_id = tokens[1]
            arg_map = {}
            i = 2
            while i < len(tokens):
                key = tokens[i]
                if key in {"--actor", "-a"}:
                    if i + 1 >= len(tokens):
                        return self._approval_usage("reject")
                    arg_map["actor"] = tokens[i + 1]
                    i += 2
                    continue
                if key in {"--reason", "-r"}:
                    if i + 1 >= len(tokens):
                        return self._approval_usage("reject")
                    arg_map["reason"] = tokens[i + 1]
                    i += 2
                    continue
                if key in {"--evidence", "-e"}:
                    evidence_values = []
                    i += 1
                    while i < len(tokens) and not tokens[i].startswith("--"):
                        evidence_values.append(tokens[i])
                        i += 1
                    arg_map.setdefault("evidence", []).extend(evidence_values)
                    continue
                if key in {"--confirm", "-c"}:
                    if i + 1 >= len(tokens):
                        return self._approval_usage("reject")
                    arg_map["confirm"] = tokens[i + 1]
                    i += 2
                    continue
                return self._approval_usage("reject")
            return self._handle_approval_action(
                "REJECT",
                task_id,
                actor=arg_map.get("actor"),
                reason=arg_map.get("reason"),
                evidence_specs=arg_map.get("evidence", []),
                confirm=arg_map.get("confirm"),
            )
        if name == "create":
            if len(tokens) < 2:
                return "[VALIDATION ERROR] Usage: create <roadmap_stage_id>"
            return self._handle_create(tokens[1])
        if name == "dispatch":
            return self._handle_dispatch()
        if name == "next":
            return self._handle_next()
        if name == "help":
            return self._handle_help()
        if name in {"exit", "quit"}:
            return "[SUCCESS] EXIT"
        return f"[ERROR] Unknown command: {name}. Type 'help' to see supported commands."

    def run(self) -> None:
        print("Operator Console started. Type 'help' for commands. Type 'exit' to quit.")
        while True:
            try:
                raw = input("operator> ")
            except EOFError:
                print("[INFO] Console closed.")
                break
            except KeyboardInterrupt:
                print("\n[INFO] Console interrupted. Exiting cleanly.")
                break

            result = self.handle_command(raw)
            print(result)
            if result.startswith("[SUCCESS] EXIT"):
                print("[INFO] Console terminated cleanly.")
                break


if __name__ == "__main__":
    OperatorConsole().run()
