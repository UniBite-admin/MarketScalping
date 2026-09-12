import os
import shutil
import tempfile
import unittest

from tools.orchestrator_core import Orchestrator
from tools.run_operator_report import render_snapshot_text


def _clean_orch():
    od = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".orchestrator")
    if os.path.exists(od):
        shutil.rmtree(od)


class OperatorSnapshotTests(unittest.TestCase):
    def setUp(self):
        _clean_orch()

    def test_snapshot_generation_is_deterministic_for_same_state(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-"))
        task = orch.create_task("snapshot-one", description="deterministic snapshot", created_by="tester")
        orch.store.append_transition(task["task_id"], "READY", "tester")
        orch.store.append_artifact(task["task_id"], {
            "artifact_id": "a1",
            "artifact_type": "invocation_record",
            "task_id": task["task_id"],
            "run_id": "run-1",
            "producer": "orchestrator",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"agent_role": "ARCHITECT", "repository_revision": "abc123"},
        })

        first = orch.build_operator_snapshot()
        second = orch.build_operator_snapshot()

        self.assertEqual(first, second)
        self.assertEqual(first["summary"]["task_count"], 1)

    def test_snapshot_contains_expected_task_workflow_and_agent_information(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-"))
        task = orch.create_task("snapshot-two", description="task with run metadata", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "QA", "orchestrator", note="qa in progress")
        orch.store.append_artifact(task_id, {
            "artifact_id": "a1",
            "artifact_type": "invocation_record",
            "task_id": task_id,
            "run_id": "run-qa",
            "producer": "orchestrator",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"agent_role": "QA", "repository_revision": "abc123"},
        })

        snapshot = orch.build_operator_snapshot()

        self.assertEqual(snapshot["summary"]["task_count"], 1)
        self.assertIn("QA", snapshot["summary"]["by_status"])
        self.assertEqual(snapshot["tasks"][0]["task_id"], task_id)
        self.assertEqual(snapshot["tasks"][0]["status"], "QA")
        self.assertEqual(snapshot["tasks"][0]["workflow_transitions"][-1]["state"], "QA")
        self.assertEqual(snapshot["runtime"]["runs"][0]["agent_role"], "QA")

    def test_snapshot_is_derived_and_does_not_mutate_orchestrator_state(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-"))
        task = orch.create_task("snapshot-three", description="derived state", created_by="tester")
        task_id = task["task_id"]
        before = orch.store.read_task(task_id)

        orch.build_operator_snapshot()

        after = orch.store.read_task(task_id)
        self.assertEqual(before, after)
        self.assertEqual(len(after.get("artifacts", [])), 0)

    def test_snapshot_handles_missing_runtime_information_safely(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-"))
        orch.create_task("snapshot-four", description="missing runtime info", created_by="tester")

        snapshot = orch.build_operator_snapshot()

        self.assertEqual(snapshot["runtime"]["run_count"], 0)
        self.assertEqual(snapshot["runtime"]["runs"], [])
        self.assertEqual(snapshot["tasks"][0]["active_run_ids"], [])

    def test_snapshot_tracks_active_completed_failed_and_blocked_states(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-"))
        active = orch.create_task("active", description="active task", created_by="tester")
        failed = orch.create_task("failed", description="failed task", created_by="tester")
        blocked = orch.create_task("blocked", description="blocked task", created_by="tester")
        completed = orch.create_task("completed", description="completed task", created_by="tester")

        orch.store.append_transition(active["task_id"], "READY", "tester")
        orch.store.append_transition(failed["task_id"], "FAILED", "tester")
        orch.store.append_transition(blocked["task_id"], "BLOCKED", "tester")
        orch.store.append_transition(completed["task_id"], "MERGE", "tester")

        snapshot = orch.build_operator_snapshot()
        states = {task["status"] for task in snapshot["tasks"]}

        self.assertIn("READY", states)
        self.assertIn("FAILED", states)
        self.assertIn("BLOCKED", states)
        self.assertIn("MERGE", states)
        self.assertEqual(snapshot["summary"]["active_task_count"], 1)

    def test_snapshot_cli_renders_empty_state_safely(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-empty-"))
        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertIn("SYSTEM STATUS", text)
        self.assertIn("No tasks", text)
        self.assertIn("No active tasks", text)

    def test_snapshot_cli_renders_active_task_workflow_agent_and_evidence(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-render-"))
        task = orch.create_task("render-task", description="show control room", created_by="tester", repository_revision="rev-123")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "QA", "orchestrator", note="qa in progress")
        orch.store.append_artifact(task_id, {
            "artifact_id": "a1",
            "artifact_type": "invocation_record",
            "task_id": task_id,
            "run_id": "qa-run-1",
            "producer": "orchestrator",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"agent_role": "QA", "repository_revision": "rev-123"},
        })
        orch.store.append_artifact(task_id, {
            "artifact_id": "a2",
            "artifact_type": "qa_result",
            "task_id": task_id,
            "run_id": "qa-run-1",
            "producer": "qa",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"task_id": task_id, "run_id": "qa-run-1", "decision": "PASS", "repository_revision": "rev-123"},
        })

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertIn("CURRENT TASK", text)
        self.assertIn(task_id, text)
        self.assertIn("QA", text)
        self.assertIn("qa-run-1", text)
        self.assertIn("qa_result", text)
        self.assertIn("rev-123", text)

    def test_snapshot_cli_renders_blockers_and_human_approval_requirements(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-block-"))
        task = orch.create_task("needs-approval", description="approval required", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "SAFETY", "orchestrator")
        orch.store.append_policy_result(task_id, {
            "policy_id": "require_human_approval",
            "triggered": True,
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "reason": "human approval required",
        })
        orch.store.append_artifact(task_id, {
            "artifact_id": "b1",
            "artifact_type": "safety_result",
            "task_id": task_id,
            "run_id": "safe-run-1",
            "producer": "safety",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"decision": "REVIEW_REQUIRED", "blocking_status": "requires_human_review"},
        })

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertIn("BLOCKERS / ESCALATIONS", text)
        self.assertIn("REQUIRE_HUMAN_APPROVAL", text)
        self.assertIn("HUMAN APPROVAL", text)
        self.assertIn("safety_result", text)

    def test_snapshot_cli_renders_required_dashboard_sections_in_order(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-order-"))
        task = orch.create_task("ordered-view", description="dashboard order", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "CI", "orchestrator")
        orch.store.append_artifact(task_id, {
            "artifact_id": "a1",
            "artifact_type": "ci_results",
            "task_id": task_id,
            "run_id": "ci-run-1",
            "producer": "ci",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"status": "PASSED"},
        })

        text = render_snapshot_text(orch.build_operator_snapshot())
        order = [
            "SYSTEM STATUS",
            "CURRENT TASK",
            "WORKFLOW",
            "AGENT ACTIVITY",
            "EVIDENCE",
            "QA / SAFETY",
            "BLOCKERS / ESCALATIONS",
            "HUMAN APPROVAL",
        ]
        positions = [text.index(section) for section in order]
        self.assertEqual(positions, sorted(positions))

    def test_snapshot_cli_is_deterministic_and_does_not_mutate_state(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-deterministic-"))
        task = orch.create_task("deterministic-cli", description="stable readout", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "READY", "tester")
        orch.store.append_artifact(task_id, {
            "artifact_id": "r1",
            "artifact_type": "invocation_record",
            "task_id": task_id,
            "run_id": "run-1",
            "producer": "orchestrator",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"agent_role": "ARCHITECT", "repository_revision": "abc"},
        })
        before = orch.store.read_task(task_id)

        first = render_snapshot_text(orch.build_operator_snapshot())
        second = render_snapshot_text(orch.build_operator_snapshot())

        self.assertEqual(first, second)
        self.assertEqual(before, orch.store.read_task(task_id))

    def test_snapshot_and_render_are_read_only_guardrails(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-readonly-"))
        task = orch.create_task("guardrail-task", description="must remain read-only", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "QA", "tester", note="qa in progress")
        orch.store.append_artifact(task_id, {
            "artifact_id": "g1",
            "artifact_type": "invocation_record",
            "task_id": task_id,
            "run_id": "guard-run-1",
            "producer": "orchestrator",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"agent_role": "QA", "repository_revision": "rev-guard"},
        })
        orch.store.append_policy_result(task_id, {
            "policy_id": "guardrail_check",
            "triggered": True,
            "decision": "BLOCK",
            "reason": "guardrail evidence only",
        })
        before = orch.store.read_task(task_id)

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertEqual(before, orch.store.read_task(task_id))
        self.assertIn(task_id, text)
        self.assertIn("QA", text)
        self.assertIn("guard-run-1", text)
        self.assertEqual(snapshot["read_only"], True)

    def test_empty_repository_snapshot_is_safe_and_deterministic(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-empty-repo-"))
        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertEqual(snapshot["summary"]["task_count"], 0)
        self.assertEqual(snapshot["summary"]["active_task_count"], 0)
        self.assertIn("No tasks", text)
        self.assertIn("No active tasks", text)
        self.assertIn("SYSTEM STATUS", text)

    def test_active_task_snapshot_reports_progressing_workflow(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-active-"))
        task = orch.create_task("active-task", description="currently progressing", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "READY", "tester")
        orch.store.append_transition(task_id, "QA", "orchestrator", note="in progress")
        orch.store.append_artifact(task_id, {
            "artifact_id": "active-1",
            "artifact_type": "invocation_record",
            "task_id": task_id,
            "run_id": "active-run-1",
            "producer": "orchestrator",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"agent_role": "QA", "repository_revision": "rev-active"},
        })

        snapshot = orch.build_operator_snapshot()
        task_row = snapshot["tasks"][0]
        text = render_snapshot_text(snapshot)

        self.assertEqual(task_row["status"], "QA")
        self.assertEqual(snapshot["summary"]["active_task_count"], 1)
        self.assertIn("CURRENT TASK", text)
        self.assertIn(task_id, text)
        self.assertIn("QA", text)

    def test_completed_task_snapshot_is_reported_as_completed(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-complete-"))
        task = orch.create_task("complete-task", description="already complete", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "MERGE", "tester")

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertEqual(snapshot["summary"]["completed_task_count"], 1)
        self.assertEqual(snapshot["tasks"][0]["status"], "MERGE")
        self.assertIn("MERGE", text)

    def test_blocked_task_snapshot_exposes_blocker_information(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-blocked-"))
        task = orch.create_task("blocked-task", description="blocked by policy", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "BLOCKED", "tester")
        orch.store.append_policy_result(task_id, {
            "policy_id": "must_review",
            "triggered": True,
            "decision": "BLOCK",
            "reason": "blocked by security policy",
        })

        snapshot = orch.build_operator_snapshot()
        task_row = snapshot["tasks"][0]
        text = render_snapshot_text(snapshot)

        self.assertEqual(task_row["status"], "BLOCKED")
        self.assertIn("blocked by security policy", str(task_row["policy_decisions"]))
        self.assertIn("BLOCKERS / ESCALATIONS", text)
        self.assertIn("BLOCK", text)

    def test_failed_agent_snapshot_represents_agent_failure(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-agent-fail-"))
        task = orch.create_task("agent-failure", description="agent failed", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "FAILED", "tester", note="agent crashed")
        orch.store.append_artifact(task_id, {
            "artifact_id": "fail-1",
            "artifact_type": "invocation_record",
            "task_id": task_id,
            "run_id": "agent-failure-run",
            "producer": "qa",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"agent_role": "QA", "status": "FAILED", "error": "agent crashed"},
        })

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertEqual(snapshot["summary"]["failed_task_count"], 1)
        self.assertIn("agent-failure-run", text)
        self.assertIn("FAILED", text)

    def test_qa_failure_evidence_is_visible_in_snapshot(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-qa-fail-"))
        task = orch.create_task("qa-failure-task", description="quality gate failed", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "QA", "tester")
        orch.store.append_artifact(task_id, {
            "artifact_id": "qa-1",
            "artifact_type": "qa_result",
            "task_id": task_id,
            "run_id": "qa-fail-run",
            "producer": "qa",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"task_id": task_id, "run_id": "qa-fail-run", "decision": "FAIL", "repository_revision": "rev-qa"},
        })

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertIn("qa_result", str(snapshot["tasks"][0]["artifact_refs"]))
        self.assertIn("QA / SAFETY", text)
        self.assertIn("qa_result", text)

    def test_safety_block_and_human_approval_are_visible_as_evidence_only(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-safety-"))
        task = orch.create_task("safety-task", description="safety review required", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "SAFETY", "tester")
        orch.store.append_policy_result(task_id, {
            "policy_id": "require_human_approval",
            "triggered": True,
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "reason": "human approval required",
        })
        orch.store.append_artifact(task_id, {
            "artifact_id": "s1",
            "artifact_type": "safety_result",
            "task_id": task_id,
            "run_id": "safety-run-1",
            "producer": "safety",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"decision": "BLOCKED", "blocking_status": "requires_human_approval"},
        })

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertTrue(snapshot["tasks"][0]["requires_human_approval"])
        self.assertIn("safety_result", str(snapshot["tasks"][0]["artifact_refs"]))
        self.assertIn("REQUIRE_HUMAN_APPROVAL", text)
        self.assertIn("HUMAN APPROVAL", text)
        self.assertNotIn("approve", text.lower())

    def test_human_approval_status_is_read_only_and_not_controlled(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-human-approval-"))
        task = orch.create_task("approval-task", description="approval is required", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "HUMAN_APPROVAL", "tester")
        orch.store.append_policy_result(task_id, {
            "policy_id": "require_human_approval",
            "triggered": True,
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "reason": "pending human approval",
        })

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertTrue(snapshot["tasks"][0]["requires_human_approval"])
        self.assertIn("required: YES", text)
        self.assertIn("PENDING", text)
        self.assertNotIn("approval button", text.lower())
        self.assertNotIn("approve now", text.lower())

    def test_malformed_optional_evidence_degrades_safely(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-malformed-"))
        task = orch.create_task("malformed-evidence", description="missing optional evidence", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "READY", "tester")
        orch.store.append_artifact(task_id, {
            "artifact_id": "bad-1",
            "artifact_type": "invocation_record",
            "task_id": task_id,
            "run_id": "bad-run",
            "producer": "orchestrator",
            "created_at": "2026-09-12T00:00:00Z",
            "content": "not-a-dict",
        })
        orch.store.append_artifact(task_id, {
            "artifact_id": "bad-2",
            "artifact_type": "qa_result",
            "task_id": task_id,
            "run_id": None,
            "producer": "qa",
            "created_at": "2026-09-12T00:00:00Z",
            "content": None,
        })

        snapshot = orch.build_operator_snapshot()
        text = render_snapshot_text(snapshot)

        self.assertIn("SYSTEM STATUS", text)
        self.assertIn("QA / SAFETY", text)
        self.assertIn("qa_result", text)
        self.assertEqual(snapshot["runtime"]["run_count"], 1)

    def test_snapshot_render_is_deterministic_for_identical_state(self):
        orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-snap-repeat-"))
        task = orch.create_task("repeat-task", description="same snapshot twice", created_by="tester")
        task_id = task["task_id"]
        orch.store.append_transition(task_id, "READY", "tester")
        orch.store.append_artifact(task_id, {
            "artifact_id": "repeat-1",
            "artifact_type": "invocation_record",
            "task_id": task_id,
            "run_id": "repeat-run",
            "producer": "orchestrator",
            "created_at": "2026-09-12T00:00:00Z",
            "content": {"agent_role": "ARCHITECT", "repository_revision": "rev-repeat"},
        })

        first = render_snapshot_text(orch.build_operator_snapshot())
        second = render_snapshot_text(orch.build_operator_snapshot())

        self.assertEqual(first, second)
        self.assertEqual(orch.store.read_task(task_id)["status"], "READY")


if __name__ == "__main__":
    unittest.main()
