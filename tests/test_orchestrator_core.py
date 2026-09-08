import os
import shutil
import json
import tempfile
import unittest
from unittest.mock import patch
from tools.orchestrator_core import TaskStore, WorkflowEngine, PolicyEvaluator, Orchestrator


def _clean_orch():
    od = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".orchestrator")
    if os.path.exists(od):
        shutil.rmtree(od)


class OrchestratorCoreTests(unittest.TestCase):
    def setUp(self):
        _clean_orch()

    def test_taskstore_create_read_update(self):
        ts = TaskStore()
        t = ts.create_task("T1", description="desc", created_by="tester")
        tid = t["task_id"]
        self.assertEqual(ts.read_task(tid)["title"], "T1")
        ts.append_transition(tid, "TRIAGE", "tester", note="moved")
        r = ts.read_task(tid)
        self.assertEqual(r["status"], "TRIAGE")
        ts.append_artifact(tid, {"name": "a"})
        self.assertTrue(any(a["name"] == "a" for a in ts.read_task(tid)["artifacts"]))

    def test_policy_driven_retry_limits(self):
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        try:
            doc = {
                "policies": [
                    {"id": "agent_retry_limits", "condition": {"concept": "agent_run"}, "action": {"type": "limit_retries", "max_retries": 1}},
                    {"id": "no-auto-live-trading-enable", "condition": {"path_regex": "enable_live"}, "action": "block"}
                ]
            }
            json.dump(doc, tmp)
            tmp.flush()
            tmp.close()
            orch = Orchestrator(policies_path=tmp.name)
            t = orch.create_task("live-enable", description="enable live", created_by="tester", changed_paths=["enable_live_config.py"]) 
            tid = t["task_id"]
            r1 = orch.transition_task(tid, "TRIAGE", actor="tester")
            self.assertIn(r1["status"], ("blocked", "blocked_unknown"))
            r2 = orch.transition_task(tid, "TRIAGE", actor="tester")
            self.assertIn(r2["status"], ("escalated",))
        finally:
            try:
                os.remove(tmp.name)
            except Exception:
                pass

    def test_policy_evaluator_concept_trigger_and_human(self):
        pe = PolicyEvaluator()
        task = {"concepts": ["paper_to_live"]}
        results = pe.evaluate(task)
        pr = next((r for r in results if r["policy_id"] == "paper_to_live_requires_human"), None)
        self.assertIsNotNone(pr)
        self.assertTrue(pr["triggered"])
        self.assertEqual(pr["decision"], "REQUIRE_HUMAN_APPROVAL")

    def test_allow_for_non_triggering_docs(self):
        orch = Orchestrator()
        t = orch.create_task("docs", description="just docs", created_by="tester", changed_paths=["README.md"]) 
        tid = t["task_id"]
        res = orch.transition_task(tid, "TRIAGE", actor="tester")
        self.assertEqual(res["status"], "ok")

    def test_workflow_gates_and_developer_restrictions(self):
        orch = Orchestrator()
        t = orch.create_task("dev-task", description="dev", created_by="developer", changed_paths=["some.py"]) 
        tid = t["task_id"]
        orch.store.append_transition(tid, "DEVELOPMENT", "developer")
        with self.assertRaises(ValueError):
            orch.transition_task(tid, "MERGE", actor="developer")
        with self.assertRaises(ValueError):
            orch.transition_task(tid, "DEPLOY", actor="developer")

    def test_qA_cannot_bypass_safety(self):
        orch = Orchestrator()
        t = orch.create_task("safety-needed", description="risk change", created_by="tester", changed_paths=["risk_engine.py"]) 
        tid = t["task_id"]
        orch.store.append_transition(tid, "QA", "qa")
        # QA -> MERGE is not an allowed workflow transition; expect ValueError
        with self.assertRaises(ValueError):
            orch.transition_task(tid, "MERGE", actor="qa")

    def test_safety_to_human_approval_allows_progress(self):
        orch = Orchestrator()
        t = orch.create_task("to-human", description="prod deploy", created_by="tester", concepts=["production_deploy"]) 
        tid = t["task_id"]
        orch.store.append_transition(tid, "SAFETY", "safety")
        res = orch.transition_task(tid, "HUMAN_APPROVAL", actor="safety")
        self.assertEqual(res["status"], "ok")

    def test_idempotency_duplicate_transition(self):
        orch = Orchestrator()
        t = orch.create_task("idemp", description="idemp test", created_by="tester")
        tid = t["task_id"]
        res1 = orch.transition_task(tid, "TRIAGE", actor="tester")
        h1 = orch.store.read_task(tid).get("history", [])
        res2 = orch.transition_task(tid, "TRIAGE", actor="tester")
        h2 = orch.store.read_task(tid).get("history", [])
        self.assertIn(res2["status"], ("noop", "ok"))
        self.assertEqual(len(h2), len(h1))

    def test_persistence_and_recovery_and_partial_line_handling(self):
        ts = TaskStore()
        t = ts.create_task("persist", description="persist test", created_by="tester")
        tid = t["task_id"]
        ts.append_transition(tid, "TRIAGE", "tester")
        ts2 = TaskStore()
        r = ts2.read_task(tid)
        self.assertIsNotNone(r)
        self.assertEqual(r["status"], "TRIAGE")
        with open(ts.tasks_file, "a", encoding="utf-8") as f:
            f.write("{this is not valid json}\n")
        ts3 = TaskStore()
        _ = ts3.list_tasks()

    def test_locking_single_file_lock(self):
        ts = TaskStore()
        t = ts.create_task("locktest", description="lock", created_by="tester")
        tid = t["task_id"]
        ts.acquire_lock(tid, "owner1")
        try:
            with self.assertRaises(Exception):
                ts.acquire_lock(tid, "owner2")
        finally:
            ts.release_lock(tid)

    def test_security_boundary_source_level(self):
        p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "orchestrator_core.py")
        with open(p, "r", encoding="utf-8") as fh:
            src = fh.read()
        for forbidden in ("requests", "websocket", "socket", "ccxt", "bitvavo", "place_order", "withdraw", "deploy", "ssh", "paramiko"):
            self.assertNotIn(forbidden, src.lower())

    def test_workflow_valid_and_invalid(self):
        wf = WorkflowEngine()
        self.assertTrue(wf.validate_transition("BACKLOG", "TRIAGE"))
        self.assertFalse(wf.validate_transition("BACKLOG", "DEPLOY"))

    def test_policy_evaluator_path_based(self):
        pe = PolicyEvaluator()
        task = {"changed_paths": ["risk_engine.py"]}
        results = pe.evaluate(task)
        pr = next((r for r in results if r["policy_id"].startswith("safety_review_for_risk") or r["policy_id"]=="safety_review_for_risk_execution_accounting"), None)
        self.assertIsNotNone(pr)
        self.assertEqual(pr["decision"], "REQUIRE_SAFETY_REVIEW")

    def test_orchestrator_transition_policy_blocking(self):
        orch = Orchestrator()
        t = orch.create_task("T2", description="desc", created_by="tester", changed_paths=["some_unknown_file.py"]) 
        tid = t["task_id"]
        res = orch.transition_task(tid, "TRIAGE", actor="tester")
        self.assertIn(res["status"], ("ok", "blocked", "pending_safety_review", "pending_human_approval", "noop"))

    def _developer_task_payload(self, task_id: str, run_id: str = "dev-run-1"):
        return {
            "task_record": {
                "task_id": task_id,
                "title": "Add minimal feature",
                "scope": ["market_data.py"],
                "authorized": True,
                "status": "READY",
            },
            "architecture_result": {
                "task_id": task_id,
                "run_id": run_id,
                "repository_revision": "repo-123",
                "architecture_assessment": {"summary": "ok"},
                "affected_components": ["market_data.py"],
                "proposed_changes": ["Add feature"],
                "acceptance_criteria": ["Feature works"],
                "developer_specification": {"files": ["market_data.py"], "high_level_changes": ["Add minimal logic"]},
                "adr_required": False,
                "status": "READY",
            },
            "repository_context": {"file_list": ["market_data.py", "README.md"], "files": ["market_data.py", "README.md"]},
            "repository_revision": "repo-123",
            "run_id": run_id,
            "orchestrator_authorization": {"authorized": True, "task_id": task_id},
            "scope": ["market_data.py"],
            "implementation_target": "market_data.py",
            "tests_to_run": ["python -m unittest discover -s tests -p \"test*.py\" -v"],
        }

    def _qa_task_payload(self, task_id: str, run_id: str = "qa-run-1", failed: bool = False):
        test_manifest = {
            "artifact_id": "test-manifest-1",
            "artifact_type": "test_manifest",
            "task_id": task_id,
            "run_id": run_id,
            "repository_revision": "repo-123",
            "producer": "developer",
            "content": {
                "tests_executed": ["python -m unittest discover -s tests -p \"test_orchestrator_core.py\" -v"],
                "results": [{"command": "python -m unittest discover -s tests -p \"test_orchestrator_core.py\" -v", "status": "PASSED" if not failed else "FAILED", "failure_details": [] if not failed else ["assertion failed"]}],
                "verification_status": "PASSED" if not failed else "FAILED",
                "relevant_failures": [] if not failed else ["assertion failed"],
            },
        }
        implementation_artifact = {
            "artifact_id": "implementation-1",
            "artifact_type": "implementation_artifact",
            "task_id": task_id,
            "run_id": run_id,
            "repository_revision": "repo-123",
            "producer": "developer",
            "content": {
                "changed_files": ["market_data.py"],
                "implementation_status": "IMPLEMENTED",
                "verification_status": "PENDING",
                "known_limitations": [],
                "blockers": [],
            },
        }
        return {
            "task_record": {
                "task_id": task_id,
                "title": "Verify feature update",
                "authorized": True,
                "status": "CI",
            },
            "architecture_result": {
                "task_id": task_id,
                "run_id": run_id,
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
            "implementation_artifact": implementation_artifact,
            "test_manifest": test_manifest,
            "run_id": run_id,
            "task_id": task_id,
        }

    def test_orchestrator_qa_integration_success(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-pass")
        task = orch.create_task("qa-pass", description="qa gate pass", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        res = orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "ok")
        persisted = orch.store.read_task(tid)
        self.assertEqual(persisted["status"], "QA")
        self.assertTrue(any(a.get("artifact_type") == "qa_result" for a in persisted["artifacts"]))
        self.assertTrue(any(a.get("artifact_type") == "defect_report" for a in persisted["artifacts"]))

    def test_orchestrator_qa_integration_fail_blocks(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-fail", failed=True)
        task = orch.create_task("qa-fail", description="qa gate fail", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        res = orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        persisted = orch.store.read_task(tid)
        self.assertIn("BLOCKED", [h.get("state") for h in persisted.get("history", [])])

    def test_qa_same_run_id_same_inputs_is_idempotent(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-idempotent")
        task = orch.create_task("qa-idempotent", description="qa gate idempotent", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        first = orch.transition_task(tid, "QA", actor="orchestrator")
        second = orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(first["status"], "ok")
        self.assertIn(second["status"], ("noop", "ok"))

    def test_qa_same_run_id_different_task_id_blocks(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-task-mismatch", run_id="qa-stable")
        task = orch.create_task("qa-task-mismatch", description="qa gate mismatch", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        first = orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(first["status"], "ok")

        payload2 = self._qa_task_payload("task-qa-other", run_id="qa-stable")
        task2 = orch.create_task("qa-other", description="qa gate mismatch 2", created_by="tester", task_spec=payload2)
        tid2 = task2["task_id"]
        orch.store.update_task(tid2, {"status": "CI"})
        with patch.object(orch.runtime, "invoke", wraps=orch.runtime.invoke) as invoke_mock:
            res = orch.transition_task(tid2, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        invoke_mock.assert_not_called()

    def test_qa_same_run_id_different_repository_revision_blocks(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-rev", run_id="qa-rev-stable")
        task = orch.create_task("qa-rev", description="qa gate rev", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        first = orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(first["status"], "ok")

        payload2 = self._qa_task_payload("task-qa-rev-2", run_id="qa-rev-stable")
        payload2["repository_revision"] = "repo-999"
        task2 = orch.create_task("qa-rev-2", description="qa gate rev 2", created_by="tester", task_spec=payload2)
        tid2 = task2["task_id"]
        orch.store.update_task(tid2, {"status": "CI"})
        with patch.object(orch.runtime, "invoke", wraps=orch.runtime.invoke) as invoke_mock:
            res = orch.transition_task(tid2, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        invoke_mock.assert_not_called()

    def test_qa_same_run_id_different_implementation_artifact_blocks(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-impl", run_id="qa-impl-stable")
        task = orch.create_task("qa-impl", description="qa gate impl", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        self.assertEqual(orch.transition_task(tid, "QA", actor="orchestrator")["status"], "ok")

        payload2 = self._qa_task_payload("task-qa-impl-2", run_id="qa-impl-stable")
        payload2["implementation_artifact"] = {"artifact_id": "impl-2", "artifact_type": "implementation_artifact", "task_id": "task-qa-impl-2", "run_id": "qa-impl-stable", "repository_revision": "repo-123", "producer": "developer", "content": {"changed_files": ["risk_engine.py"], "implementation_status": "IMPLEMENTED", "verification_status": "PENDING", "known_limitations": [], "blockers": []}}
        task2 = orch.create_task("qa-impl-2", description="qa gate impl 2", created_by="tester", task_spec=payload2)
        tid2 = task2["task_id"]
        orch.store.update_task(tid2, {"status": "CI"})
        with patch.object(orch.runtime, "invoke", wraps=orch.runtime.invoke) as invoke_mock:
            res = orch.transition_task(tid2, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        invoke_mock.assert_not_called()

    def test_qa_same_run_id_different_test_manifest_blocks(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-test", run_id="qa-test-stable")
        task = orch.create_task("qa-test", description="qa gate test", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        self.assertEqual(orch.transition_task(tid, "QA", actor="orchestrator")["status"], "ok")

        payload2 = self._qa_task_payload("task-qa-test-2", run_id="qa-test-stable")
        payload2["test_manifest"] = {"artifact_id": "test-2", "artifact_type": "test_manifest", "task_id": "task-qa-test-2", "run_id": "qa-test-stable", "repository_revision": "repo-123", "producer": "developer", "content": {"tests_executed": ["python -m unittest discover -s tests -p \"test_qa_agent.py\" -v"], "results": [{"command": "python -m unittest discover -s tests -p \"test_qa_agent.py\" -v", "status": "FAILED", "failure_details": ["assertion failed"]}], "verification_status": "FAILED", "relevant_failures": ["assertion failed"]}}
        task2 = orch.create_task("qa-test-2", description="qa gate test 2", created_by="tester", task_spec=payload2)
        tid2 = task2["task_id"]
        orch.store.update_task(tid2, {"status": "CI"})
        with patch.object(orch.runtime, "invoke", wraps=orch.runtime.invoke) as invoke_mock:
            res = orch.transition_task(tid2, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        invoke_mock.assert_not_called()

    def test_qa_same_run_id_different_architecture_result_blocks(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-arch", run_id="qa-arch-stable")
        task = orch.create_task("qa-arch", description="qa gate arch", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        self.assertEqual(orch.transition_task(tid, "QA", actor="orchestrator")["status"], "ok")

        payload2 = self._qa_task_payload("task-qa-arch-2", run_id="qa-arch-stable")
        payload2["architecture_result"] = {"task_id": "task-qa-arch-2", "run_id": "qa-arch-stable", "repository_revision": "repo-123", "architecture_assessment": {"summary": "risk review required"}, "affected_components": ["risk_engine.py"], "acceptance_criteria": ["Safety required"], "developer_specification": {"files": ["risk_engine.py"]}, "adr_required": False, "status": "READY"}
        task2 = orch.create_task("qa-arch-2", description="qa gate arch 2", created_by="tester", task_spec=payload2)
        tid2 = task2["task_id"]
        orch.store.update_task(tid2, {"status": "CI"})
        with patch.object(orch.runtime, "invoke", wraps=orch.runtime.invoke) as invoke_mock:
            res = orch.transition_task(tid2, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        invoke_mock.assert_not_called()

    def test_qa_same_run_id_different_repository_context_blocks(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-context", run_id="qa-context-stable")
        task = orch.create_task("qa-context", description="qa gate context", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        self.assertEqual(orch.transition_task(tid, "QA", actor="orchestrator")["status"], "ok")

        payload2 = self._qa_task_payload("task-qa-context-2", run_id="qa-context-stable")
        payload2["repository_context"] = {"file_list": ["risk_engine.py", "README.md"]}
        task2 = orch.create_task("qa-context-2", description="qa gate context 2", created_by="tester", task_spec=payload2)
        tid2 = task2["task_id"]
        orch.store.update_task(tid2, {"status": "CI"})
        with patch.object(orch.runtime, "invoke", wraps=orch.runtime.invoke) as invoke_mock:
            res = orch.transition_task(tid2, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "blocked")
        invoke_mock.assert_not_called()

    def test_qa_new_run_id_is_fresh_invocation(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-new-run", run_id="qa-new-run-1")
        task = orch.create_task("qa-new-run", description="qa gate new run", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "CI"})
        res = orch.transition_task(tid, "QA", actor="orchestrator")
        self.assertEqual(res["status"], "ok")

    def test_qa_fingerprint_is_deterministic(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-fingerprint")
        first = orch._compute_qa_fingerprint(payload)
        second = orch._compute_qa_fingerprint(dict(payload))
        self.assertEqual(first, second)

    def test_qa_fingerprint_excludes_nondeterministic_runtime_metadata(self):
        orch = Orchestrator()
        payload = self._qa_task_payload("task-qa-noise")
        payload["execution_metadata"] = {"started_at": "2026-01-01T00:00:00Z", "completed_at": "2026-01-01T00:00:01Z"}
        payload["created_at"] = "2026-01-01T00:00:00Z"
        payload["updated_at"] = "2026-01-01T00:00:01Z"
        first = orch._compute_qa_fingerprint(self._qa_task_payload("task-qa-noise"))
        second = orch._compute_qa_fingerprint(payload)
        self.assertEqual(first, second)

    def test_qa_fingerprint_changes_for_materially_relevant_inputs(self):
        orch = Orchestrator()
        base = self._qa_task_payload("task-qa-material")
        baseline = orch._compute_qa_fingerprint(base)

        different_task = self._qa_task_payload("task-qa-material-other")
        self.assertNotEqual(baseline, orch._compute_qa_fingerprint(different_task))

        different_revision = self._qa_task_payload("task-qa-material")
        different_revision["repository_revision"] = "repo-999"
        self.assertNotEqual(baseline, orch._compute_qa_fingerprint(different_revision))

        different_context = self._qa_task_payload("task-qa-material")
        different_context["repository_context"] = {"file_list": ["risk_engine.py", "README.md"], "files": ["risk_engine.py", "README.md"]}
        self.assertNotEqual(baseline, orch._compute_qa_fingerprint(different_context))

        different_arch = self._qa_task_payload("task-qa-material")
        different_arch["architecture_result"] = {
            "task_id": "task-qa-material",
            "run_id": "qa-run-2",
            "repository_revision": "repo-123",
            "architecture_assessment": {"summary": "risk review required"},
            "affected_components": ["risk_engine.py"],
            "acceptance_criteria": ["Safety required"],
            "developer_specification": {"files": ["risk_engine.py"]},
            "adr_required": False,
            "status": "READY",
        }
        self.assertNotEqual(baseline, orch._compute_qa_fingerprint(different_arch))

        different_impl = self._qa_task_payload("task-qa-material")
        different_impl["implementation_artifact"] = {
            "artifact_id": "implementation-2",
            "artifact_type": "implementation_artifact",
            "task_id": "task-qa-material",
            "run_id": "qa-run-2",
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
        self.assertNotEqual(baseline, orch._compute_qa_fingerprint(different_impl))

        different_test = self._qa_task_payload("task-qa-material")
        different_test["test_manifest"] = {
            "artifact_id": "test-manifest-2",
            "artifact_type": "test_manifest",
            "task_id": "task-qa-material",
            "run_id": "qa-run-2",
            "repository_revision": "repo-123",
            "producer": "developer",
            "content": {
                "tests_executed": ["python -m unittest discover -s tests -p \"test_risk_engine.py\" -v"],
                "results": [{"command": "python -m unittest discover -s tests -p \"test_risk_engine.py\" -v", "status": "FAILED", "failure_details": ["assertion failed"]}],
                "verification_status": "FAILED",
                "relevant_failures": ["assertion failed"],
            },
        }
        self.assertNotEqual(baseline, orch._compute_qa_fingerprint(different_test))

    def test_qa_fingerprint_ignores_incidental_metadata(self):
        orch = Orchestrator()
        base = self._qa_task_payload("task-qa-noise")
        noisy = json.loads(json.dumps(base))
        noisy["artifact_id"] = "artifact-123"
        noisy["producer"] = "qa-agent"
        noisy["created_at"] = "2026-01-01T00:00:00Z"
        noisy["updated_at"] = "2026-01-01T00:00:01Z"
        noisy["started_at"] = "2026-01-01T00:00:02Z"
        noisy["completed_at"] = "2026-01-01T00:00:03Z"
        noisy["correlation_id"] = "corr-123"
        noisy["execution_metadata"] = {"started_at": "2026-01-01T00:00:02Z", "completed_at": "2026-01-01T00:00:03Z"}
        noisy["task_record"]["artifact_id"] = "task-artifact-123"
        noisy["task_record"]["producer"] = "orchestrator"
        noisy["task_record"]["created_at"] = "2026-01-01T00:00:00Z"
        noisy["implementation_artifact"]["artifact_id"] = "impl-artifact-123"
        noisy["implementation_artifact"]["producer"] = "developer"
        noisy["implementation_artifact"]["created_at"] = "2026-01-01T00:00:00Z"
        noisy["test_manifest"]["artifact_id"] = "test-artifact-123"
        noisy["test_manifest"]["producer"] = "developer"
        noisy["test_manifest"]["created_at"] = "2026-01-01T00:00:00Z"
        noisy["architecture_result"]["artifact_id"] = "arch-artifact-123"
        noisy["architecture_result"]["producer"] = "architect"
        noisy["architecture_result"]["created_at"] = "2026-01-01T00:00:00Z"

        self.assertEqual(orch._compute_qa_fingerprint(base), orch._compute_qa_fingerprint(noisy))

    def test_orchestrator_developer_integration_success(self):
        orch = Orchestrator()
        task = orch.create_task("dev-task", description="build feature", created_by="tester", task_spec=self._developer_task_payload("task-dev-1"))
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "READY"})
        res = orch.transition_task(tid, "DEVELOPMENT", actor="developer")
        self.assertEqual(res["status"], "ok")
        persisted = orch.store.read_task(tid)
        self.assertEqual(persisted["status"], "DEVELOPMENT")
        self.assertTrue(any(a.get("artifact_type") == "implementation_artifact" for a in persisted["artifacts"]))
        self.assertTrue(any(a.get("artifact_type") == "test_manifest" for a in persisted["artifacts"]))

    def test_orchestrator_developer_integration_blocks_missing_architecture(self):
        orch = Orchestrator()
        payload = self._developer_task_payload("task-dev-2")
        payload.pop("architecture_result")
        task = orch.create_task("dev-task-missing-arch", description="build feature", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "READY"})
        res = orch.transition_task(tid, "DEVELOPMENT", actor="developer")
        self.assertEqual(res["status"], "blocked")

    def test_orchestrator_developer_integration_failure_blocks_workflow(self):
        orch = Orchestrator()
        payload = self._developer_task_payload("task-dev-3")
        payload["simulate_failure"] = True
        task = orch.create_task("dev-task-fail", description="fail feature", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "READY"})
        res = orch.transition_task(tid, "DEVELOPMENT", actor="developer")
        self.assertEqual(res["status"], "blocked")
        self.assertIn("BLOCKED", [a.get("state") for a in orch.store.read_task(tid).get("history", [])])

    def test_orchestrator_developer_integration_idempotent_run_id(self):
        orch = Orchestrator()
        payload = self._developer_task_payload("task-dev-4", run_id="stable-run")
        task = orch.create_task("dev-task-idempotent", description="stable run", created_by="tester", task_spec=payload)
        tid = task["task_id"]
        orch.store.update_task(tid, {"status": "READY"})
        res1 = orch.transition_task(tid, "DEVELOPMENT", actor="developer")
        res2 = orch.transition_task(tid, "DEVELOPMENT", actor="developer")
        self.assertEqual(res1["status"], "ok")
        self.assertIn(res2["status"], ("noop", "ok"))


if __name__ == "__main__":
    unittest.main()
