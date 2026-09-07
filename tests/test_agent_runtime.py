import unittest
import uuid
import os
import inspect

from tools.agent_runtime import (
    AgentRuntime,
    InvocationRequest,
    MockAgentExecutor,
    AgentExecutor,
    AgentResult,
)


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = AgentRuntime()

    def _make_request(self, **overrides):
        base = {
            "task_id": "T-123",
            "agent_role": "DEVELOPER",
            "repository_revision": "deadbeef",
            "worktree": None,
            "task_spec": {},
            "input_artifacts": [],
            "policy_context": {},
            "timeout_seconds": 30,
            "attempt": 0,
        }
        base.update(overrides)
        return InvocationRequest(**base)

    def test_valid_invocation_produces_success(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        self.assertIsInstance(res, AgentResult)
        self.assertEqual(res.task_id, req.task_id)
        self.assertEqual(res.agent_role, req.agent_role)
        self.assertEqual(res.status, "SUCCEEDED")

    def test_invalid_request_missing_fields(self):
        req = self._make_request(task_id="")
        with self.assertRaises(ValueError):
            self.runtime.invoke(req)

    def test_run_id_generation_and_reuse(self):
        req = self._make_request()
        res1 = self.runtime.invoke(req)
        self.assertIsNotNone(res1.run_id)
        # reuse run_id
        req2 = self._make_request(run_id=res1.run_id)
        res2 = self.runtime.invoke(req2)
        self.assertEqual(res1.run_id, res2.run_id)
        self.assertEqual(res1.status, res2.status)

    def test_mock_executor_failure(self):
        req = self._make_request(task_spec={"simulate": "fail"})
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "FAILED")
        self.assertIsNotNone(res.error)

    def test_mock_executor_timeout(self):
        req = self._make_request(task_spec={"simulate": "timeout"})
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "TIMED_OUT")
        self.assertIsNotNone(res.error)

    def test_deterministic_artifact_and_changed_files(self):
        req = self._make_request(task_spec={"touch_file": "foo.txt", "proposed_next_state": "MERGE"})
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "SUCCEEDED")
        self.assertIn("foo.txt", res.changed_files)
        self.assertEqual(res.proposed_next_state, "MERGE")
        self.assertTrue(len(res.output_artifacts) >= 1)

    def test_idempotency_no_double_execute(self):
        # wrap executor to count executions
        class CountingExecutor(MockAgentExecutor):
            def __init__(self):
                super().__init__()
                self.count = 0

            def execute(self, request):
                self.count += 1
                return super().execute(request)

        ce = CountingExecutor()
        runtime = AgentRuntime(executor=ce)
        req = self._make_request()
        res1 = runtime.invoke(req)
        # call again with same run_id
        req2 = self._make_request(run_id=res1.run_id)
        res2 = runtime.invoke(req2)
        self.assertEqual(ce.count, 1)
        self.assertEqual(res1.run_id, res2.run_id)

    def test_repository_revision_recorded(self):
        req = self._make_request(repository_revision="cafebabe")
        res = self.runtime.invoke(req)
        self.assertEqual(res.execution_metadata.get("repository_revision"), "cafebabe")

    def test_task_id_correlation(self):
        req = self._make_request(task_id="TASK-XYZ")
        res = self.runtime.invoke(req)
        self.assertEqual(res.task_id, "TASK-XYZ")

    def test_security_boundary_no_trading_imports_present(self):
        # Ensure agent runtime source does not contain forbidden trading keywords
        src = inspect.getsource(__import__("tools.agent_runtime", fromlist=["*"]))
        for forbidden in ("websocket", "ccxt", "bitvavo", "place_order", "withdraw", "deploy", "ssh", "paramiko"):
            self.assertNotIn(forbidden, src.lower())

    def test_orchestrator_integration_smoke(self):
        # minimal smoke: orchestrator would call runtime.invoke(req)
        # We only demonstrate the call path without modifying orchestrator code.
        req = self._make_request()
        res = self.runtime.invoke(req)
        self.assertEqual(res.task_id, req.task_id)


if __name__ == "__main__":
    unittest.main()
