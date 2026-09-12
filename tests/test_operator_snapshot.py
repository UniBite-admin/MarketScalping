import os
import shutil
import tempfile
import unittest

from tools.orchestrator_core import Orchestrator


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


if __name__ == "__main__":
    unittest.main()
