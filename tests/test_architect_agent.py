import unittest
import uuid

from tools.agent_runtime import AgentRuntime, InvocationRequest
from tools.architect_agent import ArchitectExecutor


class ArchitectAgentTests(unittest.TestCase):
    def setUp(self):
        self.exec = ArchitectExecutor()
        self.runtime = AgentRuntime(executor=self.exec)

    def _base_task_spec(self, files=None):
        return {
            "repository_context": {"file_list": files or [
                "market_data.py",
                "market_data_engine.py",
                "risk_engine.py",
                "execution_engine.py",
                "accounting_engine.py",
                "position_manager.py",
                "tools/agent_runtime.py",
            ]}
        }

    def _make_request(self, **overrides):
        base = {
            "task_id": "T-ARCH-1",
            "agent_role": "ARCHITECT",
            "repository_revision": "deadbeef",
            "worktree": None,
            "task_spec": self._base_task_spec(),
            "input_artifacts": [],
            "policy_context": {},
            "timeout_seconds": 30,
            "attempt": 0,
            "run_id": str(uuid.uuid4()),
        }
        base.update(overrides)
        return InvocationRequest(**base)

    def test_valid_architect_input_succeeds(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "SUCCEEDED")
        self.assertTrue(len(res.output_artifacts) >= 1)
        art = res.output_artifacts[0]
        self.assertEqual(art.get("artifact_type"), "architecture_result")
        content = art.get("content")
        # check required output fields
        for k in ("architecture_assessment", "affected_components", "proposed_changes", "acceptance_criteria", "developer_specification"):
            self.assertIn(k, content)

    def test_required_field_validation(self):
        # missing repository_context inside task_spec
        bad_spec = {"repository_context": None}
        req = self._make_request(task_spec=bad_spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "FAILED")
        self.assertIsNotNone(res.error)

    def test_adr_required_detection_for_sensitive_files(self):
        ts = self._base_task_spec()
        ts["target_paths"] = ["risk_engine.py"]
        req = self._make_request(task_spec=ts)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "SUCCEEDED")
        art = res.output_artifacts[0]["content"]
        self.assertTrue(art.get("adr_required"))
        self.assertTrue(len(art.get("safety_implications", [])) > 0)

    def test_safety_sensitive_task_flagged(self):
        ts = self._base_task_spec()
        ts["target_paths"] = ["execution_engine.py"]
        req = self._make_request(task_spec=ts)
        res = self.runtime.invoke(req)
        content = res.output_artifacts[0]["content"]
        self.assertTrue(content.get("adr_required"))

    def test_architect_cannot_invoke_other_agents(self):
        # ensure result contains no accidental 'invoke' instructions
        req = self._make_request()
        res = self.runtime.invoke(req)
        content = res.output_artifacts[0]["content"]
        self.assertNotIn("invoke_developer", content)
        self.assertNotIn("invoke_qa", content)
        self.assertNotIn("invoke_safety", content)

    def test_idempotency_run_id_reuse(self):
        req = self._make_request()
        first = self.runtime.invoke(req)
        # call again with same run_id
        second = self.runtime.invoke(req)
        self.assertEqual(first.run_id, second.run_id)
        # executor should have been executed only once
        self.assertEqual(self.exec.exec_count, 1)

    def test_integration_smoke_end_to_end(self):
        # Minimal integration: architect analysis runs and produces proposal
        ts = self._base_task_spec()
        ts["change_area"] = "market_data"
        req = self._make_request(task_spec=ts)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "SUCCEEDED")
        content = res.output_artifacts[0]["content"]
        self.assertIn("architecture_assessment", content)


if __name__ == "__main__":
    unittest.main()
