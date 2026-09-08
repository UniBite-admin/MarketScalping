import json
import os
import shutil
import unittest
from unittest.mock import patch

from tools.agent_runtime import AgentRuntime, InvocationRequest
from tools.safety_agent import SafetyExecutor
from tools.orchestrator_core import Orchestrator


def _clean_orch():
    od = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".orchestrator")
    if os.path.exists(od):
        shutil.rmtree(od)


class SafetyAgentTests(unittest.TestCase):
    def setUp(self):
        _clean_orch()
        self.executor = SafetyExecutor()
        self.runtime = AgentRuntime(executor=self.executor)

    def _base_spec(self, **overrides):
        task_record = {
            "task_id": "TASK-SAFE-1",
            "title": "Safety review for feature update",
            "status": "QA",
            "authorized": True,
        }
        architecture_result = {
            "task_id": "TASK-SAFE-1",
            "run_id": "arch-run-1",
            "repository_revision": "deadbeef",
            "architecture_assessment": {"summary": "ok"},
            "affected_components": ["market_data.py"],
            "acceptance_criteria": ["Feature works"],
            "developer_specification": {"files": ["market_data.py"]},
            "adr_required": False,
            "status": "READY",
        }
        implementation_artifact = {
            "artifact_id": "impl-1",
            "artifact_type": "implementation_artifact",
            "task_id": "TASK-SAFE-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {
                "changed_files": ["market_data.py"],
                "implementation_status": "IMPLEMENTED",
                "verification_status": "PENDING",
                "known_limitations": [],
                "blockers": [],
            },
        }
        test_manifest = {
            "artifact_id": "test-1",
            "artifact_type": "test_manifest",
            "task_id": "TASK-SAFE-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {
                "tests_executed": ["python -m unittest discover -s tests -p \"test_safety_agent.py\" -v"],
                "results": [{"command": "python -m unittest discover -s tests -p \"test_safety_agent.py\" -v", "status": "PASSED", "failure_details": []}],
                "verification_status": "PASSED",
                "relevant_failures": [],
            },
        }
        qa_result = {
            "artifact_id": "qa-1",
            "artifact_type": "qa_result",
            "task_id": "TASK-SAFE-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "qa",
            "created_at": "2026-01-01T00:00:00Z",
            "content": {
                "task_id": "TASK-SAFE-1",
                "run_id": "run-1",
                "repository_revision": "deadbeef",
                "decision": "PASS",
                "severity": "LOW",
                "verification_summary": "All checks passed",
                "evidence_references": [],
                "defects": [],
                "limitations": [],
                "safety_relevant_findings": [],
            },
        }
        spec = {
            "task_record": task_record,
            "architecture_result": architecture_result,
            "repository_context": {"file_list": ["market_data.py", "README.md"]},
            "repository_revision": "deadbeef",
            "implementation_artifact": implementation_artifact,
            "test_manifest": test_manifest,
            "qa_result": qa_result,
            "run_id": "run-1",
        }
        spec.update(overrides)
        return spec

    def _make_request(self, **overrides):
        base = {
            "task_id": "TASK-SAFE-1",
            "agent_role": "SAFETY",
            "repository_revision": "deadbeef",
            "worktree": "worktree/safety/TASK-SAFE-1",
            "task_spec": self._base_spec(),
            "input_artifacts": [],
            "policy_context": {},
            "timeout_seconds": 30,
            "attempt": 0,
            "run_id": "run-1",
        }
        base.update(overrides)
        return InvocationRequest(**base)

    def test_safety_pass_decision(self):
        req = self._make_request()
        result = self.runtime.invoke(req)
        self.assertEqual(result.status, "SUCCEEDED")
        safety_result = next(a for a in result.output_artifacts if a.get("artifact_type") == "safety_result")
        self.assertEqual(safety_result["content"]["decision"], "PASS")

    def test_safety_fail_and_blocked_decision(self):
        req = self._make_request(task_spec=self._base_spec(qa_result={
            "artifact_id": "qa-2",
            "artifact_type": "qa_result",
            "task_id": "TASK-SAFE-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "qa",
            "created_at": "2026-01-01T00:00:00Z",
            "content": {
                "task_id": "TASK-SAFE-1",
                "run_id": "run-1",
                "repository_revision": "deadbeef",
                "decision": "FAIL",
                "severity": "MEDIUM",
                "verification_summary": "QA failed",
                "evidence_references": [],
                "defects": [],
                "limitations": [],
                "safety_relevant_findings": [],
            },
        }))
        result = self.runtime.invoke(req)
        safety_result = next(a for a in result.output_artifacts if a.get("artifact_type") == "safety_result")
        self.assertEqual(safety_result["content"]["decision"], "BLOCKED")

    def test_safety_requires_human_approval_for_risk_sensitive_components(self):
        req = self._make_request(task_spec=self._base_spec(implementation_artifact={
            "artifact_id": "impl-risk",
            "artifact_type": "implementation_artifact",
            "task_id": "TASK-SAFE-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {
                "changed_files": ["risk_engine.py"],
                "implementation_status": "IMPLEMENTED",
                "verification_status": "PENDING",
                "known_limitations": [],
                "blockers": [],
            },
        }))
        result = self.runtime.invoke(req)
        safety_result = next(a for a in result.output_artifacts if a.get("artifact_type") == "safety_result")
        self.assertEqual(safety_result["content"]["decision"], "REQUIRE_HUMAN_APPROVAL")
        self.assertTrue(safety_result["content"]["requires_human_approval"])

    def test_safety_missing_required_input_blocks(self):
        spec = self._base_spec()
        spec.pop("qa_result")
        req = self._make_request(task_spec=spec)
        result = self.runtime.invoke(req)
        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("qa_result", str(result.error.get("message", "")).lower())

    def test_safety_result_matches_contract_shape(self):
        req = self._make_request()
        result = self.runtime.invoke(req)
        safety_result = next(a for a in result.output_artifacts if a.get("artifact_type") == "safety_result")
        content = safety_result["content"]
        required = [
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
        ]
        for key in required:
            self.assertIn(key, content)
        self.assertIn(content["decision"], ["PASS", "FAIL", "BLOCKED", "INCONCLUSIVE", "REQUIRE_HUMAN_APPROVAL"])
        self.assertIn(content["severity"], ["CRITICAL", "HIGH", "MEDIUM", "LOW"])

    def test_orchestrator_safety_integration_pass(self):
        orch = Orchestrator()
        payload = {
            "task_record": {
                "task_id": "TASK-SAFETY-OK",
                "title": "Safety gate ok",
                "status": "QA",
                "authorized": True,
            },
            "architecture_result": {
                "task_id": "TASK-SAFETY-OK",
                "run_id": "arch-ready",
                "repository_revision": "repo-123",
                "architecture_assessment": {"summary": "ok"},
                "affected_components": ["market_data.py"],
                "acceptance_criteria": ["Feature works"],
                "developer_specification": {"files": ["market_data.py"]},
                "adr_required": False,
                "status": "READY",
            },
            "repository_context": {"file_list": ["market_data.py", "README.md"]},
            "repository_revision": "repo-123",
            "implementation_artifact": {
                "artifact_id": "impl-safe",
                "artifact_type": "implementation_artifact",
                "task_id": "TASK-SAFETY-OK",
                "run_id": "run-safe",
                "repository_revision": "repo-123",
                "producer": "developer",
                "content": {
                    "changed_files": ["market_data.py"],
                    "implementation_status": "IMPLEMENTED",
                    "verification_status": "PENDING",
                    "known_limitations": [],
                    "blockers": [],
                },
            },
            "test_manifest": {
                "artifact_id": "test-safe",
                "artifact_type": "test_manifest",
                "task_id": "TASK-SAFETY-OK",
                "run_id": "run-safe",
                "repository_revision": "repo-123",
                "producer": "developer",
                "content": {
                    "tests_executed": ["python -m unittest discover -s tests -p \"test_safety_agent.py\" -v"],
                    "results": [{"command": "python -m unittest discover -s tests -p \"test_safety_agent.py\" -v", "status": "PASSED", "failure_details": []}],
                    "verification_status": "PASSED",
                    "relevant_failures": [],
                },
            },
            "qa_result": {
                "artifact_id": "qa-safe",
                "artifact_type": "qa_result",
                "task_id": "TASK-SAFETY-OK",
                "run_id": "run-safe",
                "repository_revision": "repo-123",
                "producer": "qa",
                "created_at": "2026-01-01T00:00:00Z",
                "content": {
                    "task_id": "TASK-SAFETY-OK",
                    "run_id": "run-safe",
                    "repository_revision": "repo-123",
                    "decision": "PASS",
                    "severity": "LOW",
                    "verification_summary": "All checks passed",
                    "evidence_references": [],
                    "defects": [],
                    "limitations": [],
                    "safety_relevant_findings": [],
                },
            },
            "run_id": "run-safe",
            "task_id": "TASK-SAFETY-OK",
        }
        task = orch.create_task("safety-pass", description="safe gate", created_by="tester", task_spec=payload)
        orch.store.update_task(task["task_id"], {"status": "QA"})
        res = orch.transition_task(task["task_id"], "SAFETY", actor="orchestrator")
        self.assertEqual(res["status"], "ok")
        persisted = orch.store.read_task(task["task_id"])
        self.assertTrue(any(a.get("artifact_type") == "safety_result" for a in persisted["artifacts"]))

    def test_orchestrator_safety_requires_human_approval(self):
        orch = Orchestrator()
        payload = self._base_spec()
        payload["implementation_artifact"] = {
            "artifact_id": "impl-human",
            "artifact_type": "implementation_artifact",
            "task_id": "TASK-SAFETY-REQ",
            "run_id": "run-safe-human",
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
        payload["task_record"]["task_id"] = "TASK-SAFETY-REQ"
        payload["task_id"] = "TASK-SAFETY-REQ"
        payload["run_id"] = "run-safe-human"
        task = orch.create_task("safety-human", description="risk gate", created_by="tester", task_spec=payload)
        orch.store.update_task(task["task_id"], {"status": "QA"})
        res = orch.transition_task(task["task_id"], "SAFETY", actor="orchestrator")
        self.assertEqual(res["status"], "ok")
        persisted = orch.store.read_task(task["task_id"])
        self.assertIn(persisted["status"], ["HUMAN_APPROVAL", "SAFETY"])

    def test_safety_same_run_id_different_qa_result_blocks(self):
        orch = Orchestrator()
        payload = self._base_spec()
        payload["task_record"]["task_id"] = "TASK-SAFETY-ID"
        payload["task_id"] = "TASK-SAFETY-ID"
        payload["run_id"] = "safe-stable"
        task = orch.create_task("safety-stable", description="stable idempotent path", created_by="tester", task_spec=payload)
        orch.store.update_task(task["task_id"], {"status": "QA"})
        first = orch.transition_task(task["task_id"], "SAFETY", actor="orchestrator")
        self.assertEqual(first["status"], "ok")

        payload2 = self._base_spec()
        payload2["task_record"]["task_id"] = "TASK-SAFETY-ID-2"
        payload2["task_id"] = "TASK-SAFETY-ID-2"
        payload2["run_id"] = "safe-stable"
        payload2["qa_result"]["content"]["decision"] = "FAIL"
        task2 = orch.create_task("safety-stable-other", description="stable path mismatch", created_by="tester", task_spec=payload2)
        orch.store.update_task(task2["task_id"], {"status": "QA"})
        with patch.object(orch.runtime, "invoke", wraps=orch.runtime.invoke) as invoke_mock:
            res = orch.transition_task(task2["task_id"], "SAFETY", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        invoke_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
