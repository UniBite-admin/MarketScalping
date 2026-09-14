import os
import shutil
import tempfile
import unittest

from tools.orchestrator_core import Orchestrator


def _clean_orch():
    od = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".orchestrator")
    if os.path.exists(od):
        shutil.rmtree(od)


class HumanApprovalContractTests(unittest.TestCase):
    def setUp(self):
        _clean_orch()
        self.orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-approval-"))

    def test_valid_human_approval_record_is_persisted(self):
        task = self.orch.create_task("approval-ok", description="valid approval", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        record = self.orch.record_human_approval(
            task_id=task["task_id"],
            decision="APPROVE",
            actor="human",
            reason="risk gate satisfied",
            evidence_refs=[{"artifact_id": "e1", "artifact_type": "safety_result"}],
            timestamp_utc="2026-09-14T12:00:00Z",
            workflow_state_at_decision="HUMAN_APPROVAL",
            policy_context={"policy_id": "require_human_approval", "decision": "REQUIRE_HUMAN_APPROVAL"},
        )

        self.assertEqual(record["decision"], "APPROVE")
        self.assertEqual(record["task_id"], task["task_id"])
        self.assertEqual(record["actor"], "human")
        self.assertEqual(record["workflow_state_at_decision"], "HUMAN_APPROVAL")
        self.assertIn("approval_record_id", record)

        stored = self.orch.store.read_task(task["task_id"])
        self.assertTrue(any(artifact.get("artifact_type") == "human_approval_record" for artifact in stored.get("artifacts", [])))

    def test_valid_reject_is_persisted(self):
        task = self.orch.create_task("approval-reject", description="reject approval", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        record = self.orch.record_human_approval(
            task_id=task["task_id"],
            decision="REJECT",
            actor="human",
            reason="needs safety review",
            evidence_refs=[{"artifact_id": "e2", "artifact_type": "safety_result"}],
            timestamp_utc="2026-09-14T12:01:00Z",
            workflow_state_at_decision="HUMAN_APPROVAL",
            policy_context={"policy_id": "require_human_approval"},
        )

        self.assertEqual(record["decision"], "REJECT")
        self.assertEqual(record["reason"], "needs safety review")

    def test_missing_task_is_rejected(self):
        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id="missing-id",
                decision="APPROVE",
                actor="human",
                reason="x",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:00:00Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={},
            )

    def test_invalid_task_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id="",
                decision="APPROVE",
                actor="human",
                reason="x",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:00:00Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={},
            )

    def test_wrong_workflow_state_is_rejected(self):
        task = self.orch.create_task("approval-wrong-state", description="wrong state", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "QA", "orchestrator")

        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="APPROVE",
                actor="human",
                reason="wrong state",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:00:00Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={},
            )

    def test_invalid_decision_is_rejected(self):
        task = self.orch.create_task("approval-bad-decision", description="bad decision", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="MAYBE",
                actor="human",
                reason="bad",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:00:00Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={},
            )

    def test_missing_actor_is_rejected(self):
        task = self.orch.create_task("approval-no-actor", description="missing actor", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="APPROVE",
                actor="",
                reason="x",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:00:00Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={},
            )

    def test_invalid_timestamp_is_rejected(self):
        task = self.orch.create_task("approval-bad-ts", description="bad timestamp", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="APPROVE",
                actor="human",
                reason="x",
                evidence_refs=[],
                timestamp_utc="not-a-time",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={},
            )

    def test_malformed_evidence_reference_is_rejected(self):
        task = self.orch.create_task("approval-bad-evidence", description="bad evidence", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="APPROVE",
                actor="human",
                reason="x",
                evidence_refs=[{"artifact_id": 123}],
                timestamp_utc="2026-09-14T12:00:00Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={},
            )

    def test_stale_approval_is_rejected(self):
        task = self.orch.create_task("approval-stale", description="stale", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="APPROVE",
                actor="human",
                reason="x",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:00:00Z",
                workflow_state_at_decision="QA",
                policy_context={},
            )

    def test_duplicate_approval_is_rejected(self):
        task = self.orch.create_task("approval-dup", description="duplicate", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        self.orch.record_human_approval(
            task_id=task["task_id"],
            decision="APPROVE",
            actor="human",
            reason="first",
            evidence_refs=[],
            timestamp_utc="2026-09-14T12:00:00Z",
            workflow_state_at_decision="HUMAN_APPROVAL",
            policy_context={"policy_id": "require_human_approval"},
        )

        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="APPROVE",
                actor="human",
                reason="second",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:01:00Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={"policy_id": "require_human_approval"},
            )

    def test_approval_cannot_bypass_workflow(self):
        task = self.orch.create_task("approval-no-bypass", description="bypass", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "QA", "orchestrator")

        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="APPROVE",
                actor="human",
                reason="should not bypass",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:00:00Z",
                workflow_state_at_decision="QA",
                policy_context={"policy_id": "require_human_approval"},
            )

    def test_approval_record_persists_in_task_artifacts(self):
        task = self.orch.create_task("approval-persist", description="persist", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        record = self.orch.record_human_approval(
            task_id=task["task_id"],
            decision="APPROVE",
            actor="human",
            reason="allowed",
            evidence_refs=[{"artifact_id": "a1", "artifact_type": "safety_result"}],
            timestamp_utc="2026-09-14T12:00:00Z",
            workflow_state_at_decision="HUMAN_APPROVAL",
            policy_context={"policy_id": "require_human_approval"},
        )

        stored = self.orch.store.read_task(task["task_id"])
        artifact = next(a for a in stored.get("artifacts", []) if a.get("artifact_type") == "human_approval_record")
        self.assertEqual(artifact["content"]["approval_record_id"], record["approval_record_id"])

    def test_repeated_identical_decision_is_deterministic_and_safe(self):
        task = self.orch.create_task("approval-repeat", description="repeat", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        first = self.orch.record_human_approval(
            task_id=task["task_id"],
            decision="APPROVE",
            actor="human",
            reason="first",
            evidence_refs=[],
            timestamp_utc="2026-09-14T12:00:00Z",
            workflow_state_at_decision="HUMAN_APPROVAL",
            policy_context={"policy_id": "require_human_approval"},
        )

        self.assertEqual(first["decision"], "APPROVE")
        with self.assertRaises(ValueError):
            self.orch.record_human_approval(
                task_id=task["task_id"],
                decision="APPROVE",
                actor="human",
                reason="first",
                evidence_refs=[],
                timestamp_utc="2026-09-14T12:01:00Z",
                workflow_state_at_decision="HUMAN_APPROVAL",
                policy_context={"policy_id": "require_human_approval"},
            )

    def test_no_unrelated_state_mutation_occurs(self):
        task = self.orch.create_task("approval-no-mutation", description="no mutation", created_by="tester")
        before = self.orch.store.read_task(task["task_id"])
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")

        self.orch.record_human_approval(
            task_id=task["task_id"],
            decision="APPROVE",
            actor="human",
            reason="allowed",
            evidence_refs=[],
            timestamp_utc="2026-09-14T12:00:00Z",
            workflow_state_at_decision="HUMAN_APPROVAL",
            policy_context={"policy_id": "require_human_approval"},
        )

        after = self.orch.store.read_task(task["task_id"])
        self.assertEqual(after.get("task_id"), task["task_id"])
        self.assertEqual(after.get("title"), before.get("title"))
        self.assertEqual(after.get("status"), "HUMAN_APPROVAL")


if __name__ == "__main__":
    unittest.main()
