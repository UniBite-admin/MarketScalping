import unittest
import uuid

from tools.agent_runtime import AgentRuntime, InvocationRequest
from tools.developer_agent import DeveloperExecutor


class DeveloperAgentTests(unittest.TestCase):
    def setUp(self):
        self.exec = DeveloperExecutor()
        self.runtime = AgentRuntime(executor=self.exec)

    def _base_task_spec(self, **overrides):
        task_record = {
            "task_id": "TASK-DEV-1",
            "title": "Add minimal feature",
            "scope": ["market_data.py"],
            "authorized": True,
            "status": "READY",
        }
        architecture_result = {
            "task_id": "TASK-DEV-1",
            "run_id": "arch-run-1",
            "repository_revision": "deadbeef",
            "architecture_assessment": {"summary": "ok"},
            "affected_components": ["market_data.py"],
            "acceptance_criteria": ["Feature works"],
            "developer_specification": {"files": ["market_data.py"], "high_level_changes": ["Add minimal logic"]},
            "adr_required": False,
            "status": "PROPOSAL",
        }
        base = {
            "task_record": task_record,
            "architecture_result": architecture_result,
            "repository_context": {"file_list": ["market_data.py", "README.md"], "files": ["market_data.py", "README.md"]},
            "repository_revision": "deadbeef",
            "run_id": str(uuid.uuid4()),
            "orchestrator_authorization": {"authorized": True, "task_id": "TASK-DEV-1"},
            "scope": ["market_data.py"],
            "implementation_target": "market_data.py",
            "tests_to_run": ["python -m unittest discover -s tests -p \"test*.py\" -v"],
        }
        base.update(overrides)
        return base

    def _make_request(self, **overrides):
        base = {
            "task_id": "TASK-DEV-1",
            "agent_role": "DEVELOPER",
            "repository_revision": "deadbeef",
            "worktree": "worktree/dev/TASK-DEV-1",
            "task_spec": self._base_task_spec(),
            "input_artifacts": [],
            "policy_context": {},
            "timeout_seconds": 30,
            "attempt": 0,
            "run_id": str(uuid.uuid4()),
        }
        base.update(overrides)
        return InvocationRequest(**base)

    def test_valid_invocation_succeeds(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "SUCCEEDED")
        self.assertTrue(any(a.get("artifact_type") == "implementation_artifact" for a in res.output_artifacts))
        self.assertTrue(any(a.get("artifact_type") == "test_manifest" for a in res.output_artifacts))

    def test_missing_task_record_blocks(self):
        spec = self._base_task_spec()
        spec.pop("task_record")
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIsNotNone(res.error)

    def test_missing_architecture_result_blocks(self):
        spec = self._base_task_spec()
        spec.pop("architecture_result")
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIn("architecture_result", str(res.error.get("message")).lower())

    def test_missing_repository_context_blocks(self):
        spec = self._base_task_spec()
        spec.pop("repository_context")
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIn("repository_context", str(res.error.get("message")).lower())

    def test_invalid_input_blocks(self):
        req = self._make_request(task_spec={"task_record": "bad"})
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")

    def test_unauthorized_task_blocks(self):
        spec = self._base_task_spec(orchestrator_authorization={"authorized": False, "task_id": "TASK-DEV-1"})
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIn("authorization", str(res.error.get("message")).lower())

    def test_idempotent_repeated_run_id_reuses_result(self):
        req = self._make_request()
        first = self.runtime.invoke(req)
        second = self.runtime.invoke(req)
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.status, second.status)

    def test_implementation_artifact_generated(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        impl = next(a for a in res.output_artifacts if a.get("artifact_type") == "implementation_artifact")
        self.assertEqual(impl["task_id"], req.task_id)
        self.assertEqual(impl["repository_revision"], req.repository_revision)
        self.assertIn("changed_files", impl["content"])

    def test_test_manifest_generated(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        manifest = next(a for a in res.output_artifacts if a.get("artifact_type") == "test_manifest")
        self.assertIn("tests_executed", manifest["content"])
        self.assertIn("verification_status", manifest["content"])

    def test_failure_handling_is_structured(self):
        spec = self._base_task_spec()
        spec["simulate_failure"] = True
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIsNotNone(res.error)

    def test_scope_violation_blocks(self):
        spec = self._base_task_spec(scope=["market_data.py", "execution_engine.py"])
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIn("scope", str(res.error.get("message")).lower())

    def test_no_live_credential_or_trading_access(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        self.assertNotIn("bitvavo", str(res.output_artifacts).lower())
        self.assertNotIn("withdraw", str(res.output_artifacts).lower())

    def test_no_trading_invocation_in_source(self):
        import inspect
        import tools.developer_agent as dev_mod
        src = inspect.getsource(dev_mod)
        forbidden = ["bitvavo", "place_order", "withdraw", "enable_live", "LIVE_TRADING", "ccxt"]
        lowered = src.lower()
        for token in forbidden:
            self.assertNotIn(token, lowered)


if __name__ == "__main__":
    unittest.main()
