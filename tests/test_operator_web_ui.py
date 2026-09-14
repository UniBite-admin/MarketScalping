import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(REPO_ROOT, ".venv", "Scripts", "python.exe")
ENTRYPOINT_PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

from tools.operator_console import OperatorConsole
from tools.operator_web_ui import LocalOperatorWebServer
from tools.orchestrator_core import Orchestrator


class LocalOperatorWebUITests(unittest.TestCase):
    def setUp(self):
        self.orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="webui-orch-"))
        self.server = LocalOperatorWebServer(orch=self.orch, host="127.0.0.1", port=0)
        self.server.start()
        self.port = self.server.httpd.server_address[1]

    def tearDown(self):
        self.server.shutdown()

    def _fetch(self, path):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = response.read().decode("utf-8")
                return response.status, payload
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8")
            return exc.code, payload

    def _fetch_json(self, path):
        status, body = self._fetch(path)
        return status, json.loads(body)

    def _post_json(self, path, payload):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = response.read().decode("utf-8")
                return response.status, json.loads(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8")
            try:
                return exc.code, json.loads(payload)
            except json.JSONDecodeError:
                return exc.code, {"error": payload}

    def test_server_starts_through_intended_entry_point(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        env = os.environ.copy()
        env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")

        proc = subprocess.Popen(
            [ENTRYPOINT_PYTHON, "tools/operator_web_ui.py", "--host", "127.0.0.1", "--port", str(port)],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            last_error = None
            for _ in range(20):
                if proc.poll() is not None:
                    stdout, stderr = proc.communicate(timeout=5)
                    self.fail(f"Process exited early with code {proc.returncode}. stdout={stdout!r} stderr={stderr!r}")
                try:
                    req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="GET")
                    with urllib.request.urlopen(req, timeout=2) as response:
                        body = response.read().decode("utf-8")
                        self.assertEqual(response.status, 200)
                        self.assertIn("MARKETSCALPING", body)
                        return
                except Exception as exc:  # pragma: no cover - retry loop for startup race
                    last_error = exc
                    time.sleep(0.25)
            self.fail(f"Server never became ready on port {port}: {last_error}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def test_dashboard_page_is_served(self):
        status, payload = self._fetch("/")
        self.assertEqual(status, 200)
        self.assertIn("MARKETSCALPING", payload)
        self.assertIn("WHAT NEEDS MY ATTENTION", payload)

    def test_operator_status_route_returns_authoritative_snapshot_data(self):
        task = self.orch.create_task("status-task", description="status check", created_by="tester")
        status, payload = self._fetch_json("/api/operator/status")
        self.assertEqual(status, 200)
        self.assertEqual(payload["summary"]["task_count"], 1)
        self.assertIn(task["task_id"], json.dumps(payload))

    def test_next_route_returns_deterministic_next_action_information(self):
        task = self.orch.create_task("next-task", description="next check", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "human approval required",
        })

        status, payload = self._fetch_json("/api/operator/next")
        self.assertEqual(status, 200)
        self.assertTrue(payload["deterministic"])
        self.assertIn(task["task_id"], payload["message"])
        self.assertIn("HUMAN_REQUIRED", payload["message"]) or self.assertIn("human approval", payload["message"].lower())

    def test_tasks_route_returns_task_data(self):
        task = self.orch.create_task("list-task", description="task list", created_by="tester")
        status, payload = self._fetch_json("/api/tasks")
        self.assertEqual(status, 200)
        self.assertIsInstance(payload, list)
        self.assertTrue(any(item.get("task_id") == task["task_id"] for item in payload))

    def test_task_detail_route_returns_correct_task(self):
        task = self.orch.create_task("detail-task", description="detail check", created_by="tester")
        status, payload = self._fetch_json(f"/api/tasks/{task['task_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(payload["task_id"], task["task_id"])
        self.assertEqual(payload["title"], "detail-task")

    def test_missing_task_returns_deterministic_404_response(self):
        status, payload = self._fetch_json("/api/tasks/missing-task")
        self.assertEqual(status, 404)
        self.assertIn("Task not found", payload["error"])

    def test_get_requests_do_not_mutate_task_or_workflow_state(self):
        task = self.orch.create_task("no-mutation-task", description="read only", created_by="tester")
        before = json.dumps(self.orch.store.read_task(task["task_id"]), sort_keys=True)

        self._fetch_json("/api/operator/status")
        self._fetch_json("/api/operator/next")
        self._fetch_json(f"/api/tasks/{task['task_id']}")

        after = json.dumps(self.orch.store.read_task(task["task_id"]), sort_keys=True)
        self.assertEqual(before, after)

    def test_web_layer_uses_orchestrator_api_not_direct_files(self):
        snapshot = self.orch.build_operator_snapshot()
        status, payload = self._fetch_json("/api/operator/status")
        self.assertEqual(payload, snapshot)

    def test_existing_cli_operator_console_still_works(self):
        task = self.orch.create_task("console-check", description="console still works", created_by="tester")
        output = OperatorConsole(self.orch)._render_tasks()
        self.assertIn(task["task_id"], output)
        self.assertIn("TASKS", output)

    def test_web_ui_does_not_expose_sensitive_content(self):
        task = self.orch.create_task("secret-check", description="secret render", created_by="tester")
        self.orch.store.append_artifact(task["task_id"], {
            "artifact_id": "secret-art",
            "artifact_type": "safety_result",
            "task_id": task["task_id"],
            "producer": "safety",
            "created_at": "2026-09-14T12:00:00Z",
            "content": {
                "decision": "PASS",
                "api_key": "sk_live_12345",
                "password": "super-secret",
                "notes": "safe context",
            },
        })

        status, payload = self._fetch_json(f"/api/tasks/{task['task_id']}")
        self.assertEqual(status, 200)
        body = json.dumps(payload)
        self.assertIn("[REDACTED]", body)
        self.assertNotIn("sk_live_12345", body)
        self.assertNotIn("super-secret", body)
        self.assertIn("safe context", body)

    def test_web_approve_route_accepts_valid_human_approval(self):
        task = self.orch.create_task("web-approve-ok", description="web approval", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })
        self.orch.store.append_artifact(task["task_id"], {
            "artifact_id": "approve-artifact",
            "artifact_type": "safety_result",
            "task_id": task["task_id"],
            "producer": "safety",
            "created_at": "2026-09-14T12:00:00Z",
            "content": {"decision": "PASS", "summary": "safe"},
        })

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "reason": "risk gate satisfied",
            "evidence_refs": [{"artifact_id": "approve-artifact", "artifact_type": "safety_result"}],
            "confirm": True,
        })
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["record"]["decision"], "APPROVE")
        self.assertIn(task["task_id"], json.dumps(payload))

    def test_web_reject_route_accepts_valid_human_rejection(self):
        task = self.orch.create_task("web-reject-ok", description="web rejection", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "REJECT",
            "actor": "human",
            "reason": "needs more analysis",
            "evidence_refs": [],
            "confirm": True,
        })
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["record"]["decision"], "REJECT")

    def test_web_approval_requires_actor(self):
        task = self.orch.create_task("web-no-actor", description="missing actor", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "reason": "missing actor",
            "evidence_refs": [],
            "confirm": True,
        })
        self.assertEqual(status, 400)
        self.assertIn("actor", payload["error"].lower())

    def test_web_approval_requires_reason(self):
        task = self.orch.create_task("web-no-reason", description="missing reason", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "evidence_refs": [],
            "confirm": True,
        })
        self.assertEqual(status, 400)
        self.assertIn("reason", payload["error"].lower())

    def test_web_approval_requires_confirmation(self):
        task = self.orch.create_task("web-no-confirm", description="missing confirm", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "reason": "needs confirm",
            "evidence_refs": [],
            "confirm": False,
        })
        self.assertEqual(status, 400)
        self.assertIn("confirm", payload["error"].lower())

    def test_web_approval_rejects_invalid_decision(self):
        task = self.orch.create_task("web-bad-decision", description="bad decision", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "MAYBE",
            "actor": "human",
            "reason": "bad decision",
            "evidence_refs": [],
            "confirm": True,
        })
        self.assertEqual(status, 400)
        self.assertIn("decision", payload["error"].lower())

    def test_web_approval_rejects_malformed_json(self):
        task = self.orch.create_task("web-bad-json", description="bad json", created_by="tester")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/tasks/{task['task_id']}/approval",
            data=b'{"decision":',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            self.fail("malformed request unexpectedly succeeded")
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            self.assertEqual(exc.code, 400)
            self.assertIn("json", payload["error"].lower())

    def test_web_approval_unknown_task_is_404(self):
        status, payload = self._post_json("/api/tasks/missing-task/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "reason": "unknown task",
            "evidence_refs": [],
            "confirm": True,
        })
        self.assertEqual(status, 404)
        self.assertIn("task not found", payload["error"].lower())

    def test_web_approval_rejects_wrong_workflow_state(self):
        task = self.orch.create_task("web-wrong-state", description="wrong state", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "QA", "orchestrator")

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "reason": "state mismatch",
            "evidence_refs": [],
            "confirm": True,
        })
        self.assertIn(status, {400, 409})
        self.assertIn("state", payload["error"].lower())

    def test_web_approval_rejects_policy_not_required(self):
        task = self.orch.create_task("web-policy-no", description="policy not required", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "NO_ACTION",
            "triggered": False,
            "reason": "no approval required",
        })

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "reason": "should not pass",
            "evidence_refs": [],
            "confirm": True,
        })
        self.assertIn(status, {400, 409})
        self.assertIn("approval", payload["error"].lower())

    def test_web_approval_rejects_duplicate_approval(self):
        task = self.orch.create_task("web-duplicate", description="duplicate", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })
        self.orch.record_human_approval(
            task_id=task["task_id"],
            decision="APPROVE",
            actor="human",
            reason="already recorded",
            evidence_refs=[],
            timestamp_utc="2026-09-14T12:00:00Z",
            workflow_state_at_decision="HUMAN_APPROVAL",
            policy_context={"policy_id": "require_human_approval"},
        )

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "reason": "second approval",
            "evidence_refs": [],
            "confirm": True,
        })
        self.assertIn(status, {400, 409})
        self.assertIn("duplicate", payload["error"].lower())

    def test_web_approval_validates_evidence_refs_shape(self):
        task = self.orch.create_task("web-evidence-bad", description="bad evidence", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "reason": "bad evidence",
            "evidence_refs": [{"artifact_id": 123}],
            "confirm": True,
        })
        self.assertEqual(status, 400)
        self.assertIn("evidence", payload["error"].lower())

    def test_web_approval_unsupported_method_is_rejected(self):
        task = self.orch.create_task("web-unsupported", description="unsupported", created_by="tester")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/tasks/{task['task_id']}/approval",
            method="GET",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            self.fail("unsupported method unexpectedly succeeded")
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            self.assertEqual(exc.code, 405)
            self.assertIn("method", payload["error"].lower())

    def test_web_approval_uses_orchestrator_authority(self):
        task = self.orch.create_task("web-authoritative", description="authoritative", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        before = json.dumps(self.orch.store.read_task(task["task_id"]), sort_keys=True)
        status, payload = self._post_json(f"/api/tasks/{task['task_id']}/approval", {
            "decision": "APPROVE",
            "actor": "human",
            "reason": "authoritative path",
            "evidence_refs": [],
            "confirm": True,
        })
        after = json.dumps(self.orch.store.read_task(task["task_id"]), sort_keys=True)
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertNotEqual(before, after)
        self.assertTrue(any(a.get("artifact_type") == "human_approval_record" for a in self.orch.store.read_task(task["task_id"]).get("artifacts", [])))


if __name__ == "__main__":
    unittest.main()
