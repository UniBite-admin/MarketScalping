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
        task_spec["run_id"] = "qa-stale-run"
        task = self.orch.create_task("e2e-stale-run", description="stale run", created_by="tester", repository_revision="repo-123", task_spec=task_spec)
        tid = task["task_id"]

        self.orch.transition_task(tid, "TRIAGE", actor="orchestrator")
        self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.orch.transition_task(tid, "DEVELOPMENT", actor="orchestrator")
        self.orch.transition_task(tid, "CI", actor="orchestrator")

        first = self.orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(first["status"], "ok")

        stale_spec = self.orch.store.read_task(tid)["task_spec"]
        stale_spec["repository_revision"] = "repo-999"
        stale_spec["implementation_artifact"] = {
            "artifact_id": "impl-2",
            "artifact_type": "implementation_artifact",
            "task_id": tid,
            "run_id": "qa-stale-run",
            "repository_revision": "repo-999",
            "producer": "developer",
            "content": {
                "changed_files": ["market_data.py"],
                "implementation_status": "IMPLEMENTED",
                "verification_status": "PENDING",
                "known_limitations": [],
                "blockers": [],
            },
        }
        stale_spec["architecture_result"] = {
            "task_id": tid,
            "run_id": "qa-stale-run",
            "repository_revision": "repo-999",
            "architecture_assessment": {"summary": "different architecture"},
            "affected_components": ["market_data.py"],
            "proposed_changes": [{"file": "market_data.py", "proposal": "alternate approach"}],
            "acceptance_criteria": ["different feature works"],
            "developer_specification": {"files": ["market_data.py"], "high_level_changes": ["different logic"]},
            "adr_required": False,
            "status": "READY",
        }
        self.orch.store.update_task(tid, {"task_spec": stale_spec})

        res = self.orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertIn(res["status"], ["blocked", "escalated"])

    def test_full_task_ledger_contains_authoritative_orchestration_artifacts(self):
        task_spec = self._task_spec(approval=True)
        task = self.orch.create_task("e2e-full-ledger", description="full persisted chain", created_by="tester", repository_revision="repo-123", task_spec=task_spec)
        tid = task["task_id"]

        self.orch.transition_task(tid, "TRIAGE", actor="orchestrator")
        res_arch = self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.assertEqual(res_arch["status"], "ok")

        res_dev = self.orch.transition_task(tid, "DEVELOPMENT", actor="orchestrator")
        self.assertEqual(res_dev["status"], "ok")

        ci_record = self.orch.record_ci_result(
            tid,
            run_id="ci-run-1",
            status="PASSED",
            command="python -m unittest discover -s tests -p \"test*.py\" -v",
            evidence="ok",
            repository_revision="repo-123",
        )
        self.assertEqual(ci_record["artifact_type"], "ci_results")
        self.assertEqual(self.orch.transition_task(tid, "CI", actor="orchestrator")["status"], "ok")

        res_qa = self.orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(res_qa["status"], "ok")

        res_safety = self.orch.transition_task(tid, "SAFETY", actor="orchestrator")
        self.assertEqual(res_safety["status"], "ok")

        task_record = self.orch.store.read_task(tid)
        artifact_types = [a.get("artifact_type") for a in task_record.get("artifacts", [])]
        self.assertIn("invocation_record", artifact_types)
        self.assertIn("architecture_result", artifact_types)
        self.assertIn("implementation_artifact", artifact_types)
        self.assertIn("test_manifest", artifact_types)
        self.assertIn("ci_results", artifact_types)
        self.assertIn("qa_result", artifact_types)
        self.assertIn("defect_report", artifact_types)
        self.assertIn("safety_result", artifact_types)

        arch_idx = artifact_types.index("architecture_result")
        dev_idx = artifact_types.index("implementation_artifact")
        ci_idx = artifact_types.index("ci_results")
        qa_idx = artifact_types.index("qa_result")
        safety_idx = artifact_types.index("safety_result")
        self.assertLess(arch_idx, dev_idx)
        self.assertLess(dev_idx, ci_idx)
        self.assertLess(ci_idx, qa_idx)
        self.assertLess(qa_idx, safety_idx)

    def test_qa_requires_persisted_ci_results_and_passes_only_when_green(self):
        task_spec = self._task_spec(approval=True)
        task = self.orch.create_task("e2e-qa-ci-gate", description="qa requires ci", created_by="tester", repository_revision="repo-123", task_spec=task_spec)
        tid = task["task_id"]

        self.orch.transition_task(tid, "TRIAGE", actor="orchestrator")
        self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.orch.transition_task(tid, "READY", actor="orchestrator")
        self.orch.transition_task(tid, "DEVELOPMENT", actor="orchestrator")

        res_missing = self.orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(res_missing["status"], "blocked")

        self.orch.record_ci_result(tid, run_id="ci-run-1", status="FAILED", command="pytest -q", evidence="failed")
        res_failed = self.orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(res_failed["status"], "blocked")

    def test_safety_requires_real_persisted_qa_artifact(self):
        task_spec = self._task_spec(approval=True)
        task = self.orch.create_task("e2e-safety-qa-gate", description="safety requires qa", created_by="tester", repository_revision="repo-123", task_spec=task_spec)
        tid = task["task_id"]

        self.orch.transition_task(tid, "TRIAGE", actor="orchestrator")
        self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.orch.transition_task(tid, "READY", actor="orchestrator")
        self.orch.transition_task(tid, "DEVELOPMENT", actor="orchestrator")
        self.orch.record_ci_result(tid, run_id="ci-run-1", status="PASSED", command="python -m unittest discover -s tests -p \"test*.py\" -v", evidence="ok")
        self.orch.transition_task(tid, "CI", actor="orchestrator")

        self.orch.store.update_task(tid, {"task_spec": {**self.orch.store.read_task(tid).get("task_spec", {}), "qa_result": "summary only: QA passed"}})
        res_summary = self.orch.transition_task(tid, "SAFETY", actor="orchestrator")
        self.assertEqual(res_summary["status"], "blocked")

        self.orch.transition_task(tid, "QA", actor="orchestrator")
        qa_art = next(a for a in self.orch.store.read_task(tid)["artifacts"] if a.get("artifact_type") == "qa_result")
        task_spec_after_qa = self.orch.store.read_task(tid).get("task_spec", {})
        task_spec_after_qa["qa_result"] = qa_art
        self.orch.store.update_task(tid, {"task_spec": task_spec_after_qa})
        res_real = self.orch.transition_task(tid, "SAFETY", actor="orchestrator")
        self.assertEqual(res_real["status"], "ok")

    def test_development_requires_architecture_result_and_ready_requires_valid_architecture_result(self):
        task_spec = self._task_spec(approval=True)
        task = self.orch.create_task("e2e-arch-gate", description="require architecture", created_by="tester", repository_revision="repo-123", task_spec=task_spec)
        tid = task["task_id"]

        self.orch.transition_task(tid, "TRIAGE", actor="orchestrator")
        self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        task_after_arch = self.orch.store.read_task(tid)
        self.assertEqual(task_after_arch["status"], "READY")

        self.orch.store.update_task(tid, {"task_spec": {**self.orch.store.read_task(tid).get("task_spec", {}), "architecture_result": None}})
        res_dev = self.orch.transition_task(tid, "DEVELOPMENT", actor="orchestrator")
        self.assertEqual(res_dev["status"], "blocked")

        self.orch.store.update_task(tid, {"task_spec": {**self.orch.store.read_task(tid).get("task_spec", {}), "architecture_result": {"artifact_id": "bad", "artifact_type": "architecture_result", "content": {"status": "bad"}}}})
        res_ready = self.orch.transition_task(tid, "READY", actor="orchestrator")
        self.assertIn(res_ready["status"], ["blocked", "escalated"])


if __name__ == "__main__":
    unittest.main()
