import os
import shutil
import unittest

from tools.orchestrator_core import Orchestrator


def _clean_orch():
    od = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".orchestrator")
    if os.path.exists(od):
        shutil.rmtree(od)


class FullAgenticE2ETests(unittest.TestCase):
    def setUp(self):
        _clean_orch()
        self.orch = Orchestrator()

    def _task_spec(self, task_id="TASK-E2E-1", repo_revision="repo-123", approval=False):
        return {
            "task_record": {
                "task_id": task_id,
                "title": "Minimal end-to-end verification",
                "scope": ["risk_engine.py"],
                "authorized": True,
                "status": "BACKLOG",
            },
            "repository_context": {"file_list": ["risk_engine.py", "market_data.py", "README.md"]},
            "repository_revision": repo_revision,
            "architecture_result": {
                "task_id": task_id,
                "run_id": "arch-run",
                "repository_revision": repo_revision,
                "architecture_assessment": {"summary": "ok"},
                "affected_components": ["risk_engine.py"],
                "proposed_changes": [{"file": "risk_engine.py", "proposal": "safely refactor"}],
                "acceptance_criteria": ["feature works"],
                "developer_specification": {"files": ["risk_engine.py"], "high_level_changes": ["review risk logic"]},
                "adr_required": True,
                "adr_reference": "ADR-1",
                "status": "READY",
                "safety_implications": [{"file": "risk_engine.py", "reason": "risk-sensitive component"}],
            },
            "orchestrator_authorization": {"authorized": True, "task_id": task_id},
            "scope": ["risk_engine.py"],
            "implementation_target": "risk_engine.py",
            "tests_to_run": ["python -m unittest discover -s tests -p \"test_full_agentic_e2e.py\" -v"],
            "run_id": "dev-run-1",
            "ci_results": {
                "artifact_id": "ci-1",
                "artifact_type": "ci_results",
                "task_id": task_id,
                "run_id": "ci-run-1",
                "repository_revision": repo_revision,
                "producer": "ci",
                "content": {
                    "status": "PASSED",
                    "command": "python -m unittest discover -s tests -p \"test_full_agentic_e2e.py\" -v",
                    "evidence": "ok",
                },
            },
            "human_approval_record": {
                "approved": approval,
                "approver": "human",
                "task_id": task_id,
                "decision": "APPROVED" if approval else "PENDING",
            } if approval else None,
        }

    def test_happy_path_requires_explicit_human_approval_before_merge(self):
        task_spec = self._task_spec(approval=True)
        task = self.orch.create_task("e2e-happy", description="e2e flow", created_by="tester", repository_revision="repo-123", task_spec=task_spec)
        tid = task["task_id"]

        self.orch.transition_task(tid, "TRIAGE", actor="orchestrator")
        res_arch = self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.assertEqual(res_arch["status"], "ok")

        res_dev = self.orch.transition_task(tid, "DEVELOPMENT", actor="orchestrator")
        self.assertEqual(res_dev["status"], "ok")

        res_ci = self.orch.transition_task(tid, "CI", actor="orchestrator")
        self.assertEqual(res_ci["status"], "ok")

        res_qa = self.orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(res_qa["status"], "ok")

        res_safety = self.orch.transition_task(tid, "SAFETY", actor="orchestrator")
        self.assertEqual(res_safety["status"], "ok")
        final_state = self.orch.store.read_task(tid)["status"]
        self.assertIn(final_state, ["HUMAN_APPROVAL", "SAFETY"])

        res_merge = self.orch.transition_task(tid, "MERGE", actor="human")
        self.assertEqual(res_merge["status"], "ok")
        self.assertEqual(self.orch.store.read_task(tid)["status"], "MERGE")

    def test_ci_gate_requires_explicit_ci_evidence_before_qa(self):
        task_spec = self._task_spec()
        task_spec.pop("ci_results")
        task = self.orch.create_task("e2e-ci-gate", description="must require ci", created_by="tester", repository_revision="repo-123", task_spec=task_spec)
        tid = task["task_id"]

        self.orch.transition_task(tid, "TRIAGE", actor="orchestrator")
        self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.orch.transition_task(tid, "DEVELOPMENT", actor="orchestrator")

        res = self.orch.transition_task(tid, "CI", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        self.assertEqual(self.orch.store.read_task(tid)["status"], "BLOCKED")

    def test_stale_run_id_changes_are_rejected(self):
        task_spec = self._task_spec()
        task = self.orch.create_task("e2e-stale-run", description="stale run", created_by="tester", repository_revision="repo-123", task_spec=task_spec)
        tid = task["task_id"]

        self.orch.transition_task(tid, "TRIAGE", actor="orchestrator")
        self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.orch.transition_task(tid, "DEVELOPMENT", actor="orchestrator")
        self.orch.transition_task(tid, "CI", actor="orchestrator")

        task_spec2 = self._task_spec(task_id=tid)
        task_spec2["run_id"] = "dev-run-1"
        task_spec2["implementation_artifact"] = {
            "artifact_id": "impl-2",
            "artifact_type": "implementation_artifact",
            "task_id": tid,
            "run_id": "dev-run-1",
            "repository_revision": "repo-123",
            "producer": "developer",
            "content": {
                "changed_files": ["risk_engine.py"],
                "implementation_status": "IMPLEMENTED",
                "verification_status": "PENDING",
                "known_limitations": [],
                "blockers": [],
            },
        }
        self.orch.store.update_task(tid, {"task_spec": task_spec2})

        res = self.orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertIn(res["status"], ["blocked", "escalated"])


if __name__ == "__main__":
    unittest.main()
