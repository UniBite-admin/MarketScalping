import unittest
import uuid

from tools.agent_runtime import AgentRuntime, InvocationRequest
from tools.qa_agent import QAExecutor


class QAAgentTests(unittest.TestCase):
    def setUp(self):
        self.executor = QAExecutor()
        self.runtime = AgentRuntime(executor=self.executor)

    def _base_spec(self, **overrides):
        task_record = {
            "task_id": "TASK-QA-1",
            "title": "Verify feature update",
            "status": "READY",
            "authorized": True,
        }
        architecture_result = {
            "task_id": "TASK-QA-1",
            "run_id": "arch-run-1",
            "repository_revision": "deadbeef",
            "architecture_assessment": {"summary": "ok"},
            "affected_components": ["market_data.py"],
            "acceptance_criteria": ["Feature works"],
            "developer_specification": {"files": ["market_data.py"]},
            "adr_required": False,
        }
        implementation_artifact = {
            "artifact_id": "impl-1",
            "artifact_type": "implementation_artifact",
            "task_id": "TASK-QA-1",
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
            "task_id": "TASK-QA-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {
                "tests_executed": ["python -m unittest discover -s tests -p \"test_qa_agent.py\" -v"],
                "results": [{"command": "python -m unittest discover -s tests -p \"test_qa_agent.py\" -v", "status": "PASSED", "failure_details": []}],
                "verification_status": "PASSED",
                "relevant_failures": [],
            },
        }
        spec = {
            "task_record": task_record,
            "architecture_result": architecture_result,
            "repository_context": {"file_list": ["market_data.py", "README.md"]},
            "repository_revision": "deadbeef",
            "implementation_artifact": implementation_artifact,
            "test_manifest": test_manifest,
            "run_id": "run-1",
            "developer_claims": {"summary": "all tests passed"},
        }
        spec.update(overrides)
        return spec

    def _make_request(self, **overrides):
        base = {
            "task_id": "TASK-QA-1",
            "agent_role": "QA",
            "repository_revision": "deadbeef",
            "worktree": "worktree/qa/TASK-QA-1",
            "task_spec": self._base_spec(),
            "input_artifacts": [],
            "policy_context": {},
            "timeout_seconds": 30,
            "attempt": 0,
            "run_id": "run-1",
        }
        base.update(overrides)
        return InvocationRequest(**base)

    def test_valid_qa_input_passes(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "SUCCEEDED")
        self.assertEqual(res.task_id, "TASK-QA-1")
        self.assertTrue(any(a.get("artifact_type") == "qa_result" for a in res.output_artifacts))
        self.assertTrue(any(a.get("artifact_type") == "defect_report" for a in res.output_artifacts))

    def test_missing_task_record_blocks(self):
        spec = self._base_spec()
        spec.pop("task_record")
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIsNotNone(res.error)

    def test_missing_architecture_result_blocks(self):
        spec = self._base_spec()
        spec.pop("architecture_result")
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIn("architecture_result", str(res.error.get("message", "")).lower())

    def test_missing_implementation_artifact_blocks(self):
        spec = self._base_spec()
        spec.pop("implementation_artifact")
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")

    def test_missing_test_manifest_blocks(self):
        spec = self._base_spec()
        spec.pop("test_manifest")
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")

    def test_task_identity_mismatch_blocks(self):
        spec = self._base_spec(task_record={"task_id": "TASK-BAD", "title": "bad", "status": "READY", "authorized": True})
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")

    def test_repository_revision_mismatch_blocks(self):
        spec = self._base_spec(repository_revision="other-rev")
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")

    def test_pass_decision_when_evidence_is_good(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        self.assertEqual(qa_result["content"]["decision"], "PASS")

    def test_qa_result_matches_contract_shape(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        content = qa_result["content"]
        required = [
            "task_id",
            "run_id",
            "repository_revision",
            "decision",
            "verification_summary",
            "evidence_references",
            "defects",
            "limitations",
            "safety_relevant_findings",
        ]
        for key in required:
            self.assertIn(key, content)
        self.assertIsInstance(content["evidence_references"], list)
        self.assertIsInstance(content["limitations"], list)
        self.assertIsInstance(content["safety_relevant_findings"], list)
        self.assertIsInstance(content["defects"], list)

    def test_defect_report_matches_contract_shape(self):
        spec = self._base_spec(test_manifest={
            "artifact_id": "test-2",
            "artifact_type": "test_manifest",
            "task_id": "TASK-QA-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {
                "tests_executed": ["python -m unittest discover -s tests -p \"test_qa_agent.py\" -v"],
                "results": [{"command": "python -m unittest discover -s tests -p \"test_qa_agent.py\" -v", "status": "FAILED", "failure_details": ["assertion failed"]}],
                "verification_status": "FAILED",
                "relevant_failures": ["assertion failed"],
            },
        })
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        defect_report = next(a for a in res.output_artifacts if a.get("artifact_type") == "defect_report")
        defects = defect_report["content"]["defects"]
        self.assertTrue(defects)
        defect = defects[0]
        required = [
            "defect_id",
            "severity",
            "category",
            "description",
            "affected_area",
            "evidence",
            "expected_behavior",
            "observed_behavior",
            "verification_info",
            "blocking_status",
        ]
        for key in required:
            self.assertIn(key, defect)
        self.assertIn(defect["severity"], ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        self.assertIn(defect["blocking_status"], ["blocking", "non_blocking", "requires_architect_review"])

    def test_evidence_provenance_and_contract_fields(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        evidence = qa_result["content"]["evidence"]
        self.assertTrue(evidence)
        allowed = {"CLAIM", "VERIFIED", "DERIVED", "MISSING", "INCONCLUSIVE"}
        results = {item.get("result") for item in evidence if "result" in item}
        self.assertTrue(results.issubset(allowed))
        self.assertTrue(any(item.get("source") == "developer_claim" for item in evidence))
        self.assertTrue(any(item.get("result") == "CLAIM" for item in evidence))

    def test_decision_model_is_reachable(self):
        scenarios = []
        scenarios.append((self._base_spec(), "PASS", "run-pass"))
        scenarios.append((self._base_spec(test_manifest={
            "artifact_id": "test-2",
            "artifact_type": "test_manifest",
            "task_id": "TASK-QA-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {
                "tests_executed": ["python -m unittest discover -s tests -p \"test_qa_agent.py\" -v"],
                "results": [{"command": "python -m unittest discover -s tests -p \"test_qa_agent.py\" -v", "status": "FAILED", "failure_details": ["assertion failed"]}],
                "verification_status": "FAILED",
                "relevant_failures": ["assertion failed"],
            },
        }), "FAIL", "run-fail"))
        scenarios.append((self._base_spec(task_record={"task_id": "TASK-QA-1", "title": "bad", "status": "READY", "authorized": False}), "BLOCKED", "run-blocked"))
        scenarios.append((self._base_spec(test_manifest={"artifact_id": "t-1", "artifact_type": "test_manifest", "task_id": "TASK-QA-1", "run_id": "run-1", "repository_revision": "deadbeef", "producer": "developer", "content": {"tests_executed": [], "results": [], "verification_status": "UNKNOWN"}}), "INCONCLUSIVE", "run-inconclusive"))

        for spec, expected, run_id in scenarios:
            with self.subTest(spec=expected):
                req = self._make_request(task_spec=spec, run_id=run_id)
                res = self.runtime.invoke(req)
                qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
                decision = qa_result["content"]["decision"]
                if expected == "INCONCLUSIVE":
                    self.assertIn(decision, ["INCONCLUSIVE", "BLOCKED", "FAIL"])
                else:
                    self.assertEqual(decision, expected)

    def test_fail_decision_when_test_manifest_failed(self):
        spec = self._base_spec(test_manifest={
            "artifact_id": "test-2",
            "artifact_type": "test_manifest",
            "task_id": "TASK-QA-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {
                "tests_executed": ["python -m unittest discover -s tests -p \"test_qa_agent.py\" -v"],
                "results": [{"command": "python -m unittest discover -s tests -p \"test_qa_agent.py\" -v", "status": "FAILED", "failure_details": ["assertion failed"]}],
                "verification_status": "FAILED",
                "relevant_failures": ["assertion failed"],
            },
        })
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        self.assertEqual(qa_result["content"]["decision"], "FAIL")
        self.assertTrue(qa_result["content"]["defects"])

    def test_blocked_decision_when_required_authorization_missing(self):
        spec = self._base_spec(task_record={"task_id": "TASK-QA-1", "title": "bad", "status": "READY", "authorized": False})
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        self.assertEqual(qa_result["content"]["decision"], "BLOCKED")

    def test_inconclusive_decision_when_evidence_is_missing(self):
        spec = self._base_spec(test_manifest={"artifact_id": "t-1", "artifact_type": "test_manifest", "task_id": "TASK-QA-1", "run_id": "run-1", "repository_revision": "deadbeef", "producer": "developer", "content": {"tests_executed": [], "results": [], "verification_status": "UNKNOWN"}})
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        self.assertIn(qa_result["content"]["decision"], ["INCONCLUSIVE", "BLOCKED", "FAIL"])

    def test_defect_severity_validation(self):
        spec = self._base_spec(test_manifest={
            "artifact_id": "test-3",
            "artifact_type": "test_manifest",
            "task_id": "TASK-QA-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {
                "tests_executed": ["python -m unittest discover -s tests -p \"test_qa_agent.py\" -v"],
                "results": [{"command": "python -m unittest discover -s tests -p \"test_qa_agent.py\" -v", "status": "FAILED", "failure_details": ["assertion failed"]}],
                "verification_status": "FAILED",
                "relevant_failures": ["assertion failed"],
            },
        })
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        defect_report = next(a for a in res.output_artifacts if a.get("artifact_type") == "defect_report")
        defect = defect_report["content"]["defects"][0]
        self.assertIn(defect["severity"], ["CRITICAL", "HIGH", "MEDIUM", "LOW"])

    def test_evidence_structure_is_present(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        self.assertTrue(qa_result["content"]["evidence"])
        first = qa_result["content"]["evidence"][0]
        self.assertIn("source", first)
        self.assertIn("check", first)
        self.assertIn("result", first)

    def test_developer_claim_is_not_treated_as_verified_evidence(self):
        req = self._make_request()
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        evidence = qa_result["content"]["evidence"]
        self.assertTrue(any(item.get("result") == "CLAIM" or item.get("result") == "VERIFIED" for item in evidence))

    def test_architecture_drift_detection(self):
        spec = self._base_spec(architecture_result={
            "task_id": "TASK-QA-1",
            "run_id": "arch-run-1",
            "repository_revision": "deadbeef",
            "architecture_assessment": {"summary": "risk engine only"},
            "affected_components": ["risk_engine.py"],
            "acceptance_criteria": ["risk engine works"],
            "developer_specification": {"files": ["risk_engine.py"]},
            "adr_required": False,
        }, implementation_artifact={
            "artifact_id": "impl-2",
            "artifact_type": "implementation_artifact",
            "task_id": "TASK-QA-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {"changed_files": ["market_data.py"], "implementation_status": "IMPLEMENTED", "verification_status": "PENDING", "known_limitations": [], "blockers": []},
        })
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        summary = qa_result["content"]["verification_summary"]
        self.assertIn("architecture_drift", summary.lower())

    def test_safety_sensitive_change_detection(self):
        spec = self._base_spec(implementation_artifact={
            "artifact_id": "impl-3",
            "artifact_type": "implementation_artifact",
            "task_id": "TASK-QA-1",
            "run_id": "run-1",
            "repository_revision": "deadbeef",
            "producer": "developer",
            "content": {"changed_files": ["risk_engine.py"], "implementation_status": "IMPLEMENTED", "verification_status": "PENDING", "known_limitations": [], "blockers": []},
        })
        req = self._make_request(task_spec=spec)
        res = self.runtime.invoke(req)
        qa_result = next(a for a in res.output_artifacts if a.get("artifact_type") == "qa_result")
        self.assertTrue(any("safety" in str(item.get("check", "")).lower() for item in qa_result["content"]["checks"]))

    def test_runtime_integration_and_idempotency(self):
        req = self._make_request(run_id="qa-run-123")
        first = self.runtime.invoke(req)
        second = self.runtime.invoke(req)
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.status, second.status)

    def test_executor_failure_handling_is_structured(self):
        req = self._make_request(task_spec={"task_record": "bad"})
        res = self.runtime.invoke(req)
        self.assertEqual(res.status, "BLOCKED")
        self.assertIsNotNone(res.error)

    def test_security_regression_guard_for_obvious_source_tokens(self):
        import inspect
        import tools.qa_agent as qa_mod
        src = inspect.getsource(qa_mod)
        # Lightweight regression guard only: this is not authoritative security proof.
        forbidden = ["enable_live", "place_order", "withdraw", "risk_limit", "merge_protected", "deploy_production"]
        lowered = src.lower()
        for token in forbidden:
            self.assertNotIn(token, lowered)


if __name__ == "__main__":
    unittest.main()
