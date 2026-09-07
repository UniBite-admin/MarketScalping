import unittest

from tools.orchestrator_core import Orchestrator


class ArchitectOrchestratorIntegrationTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp(prefix="orch_test_")
        self.orch = Orchestrator(store_root=self._tmpdir)

    def _base_task_spec(self, files=None):
        return {"repository_context": {"file_list": files or [
            "market_data.py",
            "market_data_engine.py",
            "tools/agent_runtime.py",
        ]}}

    def test_successful_architect_invocation_no_adr(self):
        t = self.orch.create_task("arch-no-adr", created_by="tester", repository_revision="r1",
                      task_spec=self._base_task_spec())
        # advance to TRIAGE per workflow before requesting ARCHITECTURE
        self.orch.transition_task(t["task_id"], "TRIAGE", actor="orchestrator")
        tid = t["task_id"]
        res = self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.assertEqual(res.get("status"), "ok")
        task = self.orch.store.read_task(tid)
        self.assertEqual(task.get("status"), "READY")

    def test_adr_required_missing_blocks(self):
        # include the sensitive file in the repository context so Architect detects it
        spec = self._base_task_spec(files=["risk_engine.py", "market_data.py", "market_data_engine.py"]) 
        spec["target_paths"] = ["risk_engine.py"]
        t = self.orch.create_task("arch-adr-missing", created_by="tester", repository_revision="r2", task_spec=spec)
        self.orch.transition_task(t["task_id"], "TRIAGE", actor="orchestrator")
        tid = t["task_id"]
        res = self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.assertIn(res.get("status"), ("blocked",))
        task = self.orch.store.read_task(tid)
        self.assertEqual(task.get("status"), "BLOCKED")

    def test_malformed_artifact_blocks(self):
        spec = self._base_task_spec()
        spec["simulate_malformed"] = True
        t = self.orch.create_task("arch-malformed", created_by="tester", repository_revision="r3", task_spec=spec)
        self.orch.transition_task(t["task_id"], "TRIAGE", actor="orchestrator")
        tid = t["task_id"]
        res = self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        self.assertIn(res.get("status"), ("blocked",))
        task = self.orch.store.read_task(tid)
        self.assertEqual(task.get("status"), "BLOCKED")

    def test_idempotent_run_reuse(self):
        t = self.orch.create_task("arch-idempotent", created_by="tester", repository_revision="r4", task_spec=self._base_task_spec())
        self.orch.transition_task(t["task_id"], "TRIAGE", actor="orchestrator")
        tid = t["task_id"]
        res1 = self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        # call again; should be noop or ok but not duplicate transitions
        try:
            res2 = self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
            self.assertIn(res2.get("status"), ("noop", "ok", "pending_safety_review"))
        except ValueError:
            # allowed: transition invalid because workflow advanced to READY
            pass
        task = self.orch.store.read_task(tid)
        # status should have settled to READY for non-adr case
        self.assertIn(task.get("status"), ("READY", "ARCHITECTURE", "BLOCKED", "PENDING_SAFETY_REVIEW"))

    def test_runtime_get_result_returns_existing(self):
        t = self.orch.create_task("arch-get-result", created_by="tester", repository_revision="r5", task_spec=self._base_task_spec())
        self.orch.transition_task(t["task_id"], "TRIAGE", actor="orchestrator")
        tid = t["task_id"]
        res = self.orch.transition_task(tid, "ARCHITECTURE", actor="orchestrator")
        # find invocation_record artifact
        artifacts = self.orch.store.read_task(tid).get("artifacts", [])
        inv = next((a for a in artifacts if a.get("artifact_type")=="invocation_record"), None)
        self.assertIsNotNone(inv)
        run_id = inv.get("run_id")
        # runtime get_result should return a result
        result = self.orch.runtime.get_result(run_id)
        self.assertIsNotNone(result)
        self.assertIn(result.status, ("SUCCEEDED", "FAILED", "TIMED_OUT"))


if __name__ == '__main__':
    unittest.main()
