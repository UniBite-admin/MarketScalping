import os
import shutil
import tempfile
import unittest

from tools.operator_console import OperatorConsole
from tools.orchestrator_core import Orchestrator


def _clean_orch():
    od = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".orchestrator")
    if os.path.exists(od):
        shutil.rmtree(od)


class OperatorConsoleTests(unittest.TestCase):
    def setUp(self):
        _clean_orch()
        self.orch = Orchestrator(store_root=tempfile.mkdtemp(prefix="orch-console-"))
        self.console = OperatorConsole(orch=self.orch)

    def test_console_starts_and_help_works(self):
        help_text = self.console.handle_command("help")
        self.assertIn("status", help_text.lower())
        self.assertIn("help", help_text.lower())
        self.assertIn("exit", help_text.lower())

    def test_status_works(self):
        status = self.console.handle_command("status")
        self.assertIn("[INFO]", status)
        self.assertIn("SYSTEM STATUS", status)

    def test_tasks_listing_works(self):
        task = self.orch.create_task("console-task", description="task listing", created_by="tester")
        tasks = self.console.handle_command("tasks")
        self.assertIn(task["task_id"], tasks)
        self.assertIn("console-task", tasks)

    def test_show_task_works(self):
        task = self.orch.create_task("show-task", description="show me", created_by="tester")
        output = self.console.handle_command(f"show {task['task_id']}")
        self.assertIn(task["task_id"], output)
        self.assertIn("show-task", output)

    def test_history_task_works_with_populated_history(self):
        task = self.orch.create_task("history-task", description="history render", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "QA", "orchestrator", note="first review")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator", note="ready for approval")

        output = self.console.handle_command(f"history {task['task_id']}")
        self.assertIn("[INFO] TASK HISTORY", output)
        self.assertIn("QA", output)
        self.assertIn("HUMAN_APPROVAL", output)
        self.assertIn("orchestrator", output)

    def test_history_task_empty_history_renders_empty_state(self):
        task = self.orch.create_task("history-empty", description="empty history", created_by="tester")
        output = self.console.handle_command(f"history {task['task_id']}")
        self.assertIn("No history found", output)

    def test_history_missing_task_is_handled_deterministically(self):
        output = self.console.handle_command("history missing-task")
        self.assertIn("[ERROR]", output)
        self.assertIn("Task not found", output)

    def test_evidence_task_works_with_multiple_artifacts(self):
        task = self.orch.create_task("evidence-task", description="evidence render", created_by="tester")
        self.orch.store.append_artifact(task["task_id"], {
            "artifact_id": "art-1",
            "artifact_type": "safety_result",
            "task_id": task["task_id"],
            "run_id": "run-1",
            "producer": "safety",
            "created_at": "2026-09-14T12:00:00Z",
            "content": {"decision": "PASS", "summary": "safe"},
        })
        self.orch.store.append_artifact(task["task_id"], {
            "artifact_id": "art-2",
            "artifact_type": "qa_result",
            "task_id": task["task_id"],
            "run_id": "run-2",
            "producer": "qa",
            "created_at": "2026-09-14T12:05:00Z",
            "content": {"decision": "PASS", "notes": "checked"},
        })

        output = self.console.handle_command(f"evidence {task['task_id']}")
        self.assertIn("[INFO] TASK EVIDENCE", output)
        self.assertIn("art-1", output)
        self.assertIn("art-2", output)
        self.assertIn("safety_result", output)
        self.assertIn("qa_result", output)

    def test_evidence_task_with_no_artifacts_renders_empty_state(self):
        task = self.orch.create_task("evidence-empty", description="empty evidence", created_by="tester")
        output = self.console.handle_command(f"evidence {task['task_id']}")
        self.assertIn("No evidence found", output)

    def test_evidence_missing_task_is_handled_deterministically(self):
        output = self.console.handle_command("evidence missing-task")
        self.assertIn("[ERROR]", output)
        self.assertIn("Task not found", output)

    def test_history_and_evidence_commands_do_not_mutate_state(self):
        task = self.orch.create_task("inspect-no-mutation", description="read only", created_by="tester")
        before = self.orch.store.read_task(task["task_id"])
        self.console.handle_command(f"history {task['task_id']}")
        self.console.handle_command(f"evidence {task['task_id']}")
        after = self.orch.store.read_task(task["task_id"])
        self.assertEqual(before, after)

    def test_read_only_rendering_redacts_obvious_secrets(self):
        task = self.orch.create_task("secret-redaction", description="secret check", created_by="tester")
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

        output = self.console.handle_command(f"evidence {task['task_id']}")
        self.assertIn("[REDACTED]", output)
        self.assertNotIn("sk_live_12345", output)
        self.assertNotIn("super-secret", output)
        self.assertIn("safe context", output)

    def test_invalid_command_is_handled_safely(self):
        output = self.console.handle_command("totally-unknown-command")
        self.assertIn("[ERROR]", output)
        self.assertIn("Unknown command", output)

    def test_create_routes_through_existing_orchestrator(self):
        before = self.orch.store.list_tasks()
        output = self.console.handle_command("create 6C.2")
        after = self.orch.store.list_tasks()
        self.assertEqual(len(after), len(before) + 1)
        self.assertIn("[SUCCESS]", output)
        self.assertIn("6C.2", output)
        self.assertTrue(any(task.get("roadmap_stage_id") == "6C.2" for task in after))

    def test_ux_does_not_directly_mutate_authoritative_state_on_status(self):
        before = self.orch.store.list_tasks()
        self.console.handle_command("status")
        after = self.orch.store.list_tasks()
        self.assertEqual(before, after)

    def test_next_command_reports_next_step_without_invalid_state_changes(self):
        task = self.orch.create_task("next-task", description="next step test", created_by="tester")
        output = self.console.handle_command("next")
        self.assertIn(task["task_id"], output)
        self.assertIn("next", output.lower())

    def test_approve_flow_succeeds_for_human_approval_task(self):
        task = self.orch.create_task("approve-flow", description="approval flow", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator", note="policy requires approval")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })
        self.orch.store.append_artifact(task["task_id"], {
            "artifact_id": "artifact-approve",
            "artifact_type": "safety_result",
            "task_id": task["task_id"],
            "producer": "safety",
            "created_at": "2026-09-14T12:00:00Z",
            "content": {"decision": "PASS", "summary": "safe"},
        })

        output = self.console.handle_command(
            f"approve {task['task_id']} --actor human --reason 'ok to proceed' --evidence artifact-approve:safety_result --confirm yes"
        )
        self.assertIn("[SUCCESS] APPROVE recorded", output)
        self.assertIn(task["task_id"], output)

    def test_reject_flow_succeeds_for_human_approval_task(self):
        task = self.orch.create_task("reject-flow", description="reject flow", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator", note="policy requires approval")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        output = self.console.handle_command(
            f"reject {task['task_id']} --actor human --reason 'needs more review' --confirm yes"
        )
        self.assertIn("[SUCCESS] REJECT recorded", output)
        self.assertIn(task["task_id"], output)

    def test_approval_is_only_accepted_for_tasks_requiring_human_approval(self):
        task = self.orch.create_task("approve-not-required", description="not needed", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        output = self.console.handle_command(
            f"approve {task['task_id']} --actor human --reason 'not required' --confirm yes"
        )
        self.assertIn("does not currently require human approval", output)

    def test_reject_does_not_accidentally_behave_like_approval(self):
        task = self.orch.create_task("reject-not-approve", description="should reject", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        output = self.console.handle_command(
            f"reject {task['task_id']} --actor human --reason 'disallow' --confirm yes"
        )
        self.assertIn("[SUCCESS] REJECT recorded", output)
        self.assertNotIn("[SUCCESS] APPROVE recorded", output)

    def test_missing_task_fails_deterministically_for_approval(self):
        output = self.console.handle_command("approve missing-task --actor human --reason 'x' --confirm yes")
        self.assertIn("Task not found", output)

    def test_invalid_evidence_reference_is_rejected(self):
        task = self.orch.create_task("evidence-invalid", description="bad evidence", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        output = self.console.handle_command(
            f"approve {task['task_id']} --actor human --reason 'x' --evidence missing:artifact_type --confirm yes"
        )
        self.assertIn("Invalid evidence reference", output)

    def test_missing_actor_or_reason_is_rejected(self):
        task = self.orch.create_task("missing-fields", description="bad fields", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        output = self.console.handle_command(f"approve {task['task_id']} --confirm yes")
        self.assertIn("actor is required", output)

    def test_cancelled_decision_does_not_mutate_task_state(self):
        task = self.orch.create_task("approve-cancel", description="cancel approval", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })
        before = self.orch.store.read_task(task["task_id"])

        output = self.console.handle_command(
            f"approve {task['task_id']} --actor human --reason 'cancelled' --confirm no"
        )
        after = self.orch.store.read_task(task["task_id"])
        self.assertIn("Confirm decision?", output)
        self.assertEqual(before, after)

    def test_console_cannot_bypass_orchestrator_contract(self):
        task = self.orch.create_task("approval-bypass", description="bypass", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        output = self.console.handle_command(
            f"approve {task['task_id']} --actor human --reason 'bypass' --confirm yes"
        )
        self.assertIn("[SUCCESS] APPROVE recorded", output)
        self.assertTrue(any(artifact.get("artifact_type") == "human_approval_record" for artifact in self.orch.store.read_task(task["task_id"]).get("artifacts", [])))

    def test_approval_records_authoritative_approval_artifact(self):
        task = self.orch.create_task("approval-artifact", description="approval artifact", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "requires human approval",
        })

        self.console.handle_command(
            f"approve {task['task_id']} --actor human --reason 'artifact check' --confirm yes"
        )
        stored = self.orch.store.read_task(task["task_id"])
        artifact = next((a for a in stored.get("artifacts", []) if a.get("artifact_type") == "human_approval_record"), None)
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact["content"]["decision"], "APPROVE")

    def test_next_recommends_approval_for_human_required_task(self):
        task = self.orch.create_task("next-approve", description="human required", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "human approval required",
        })

        output = self.console.handle_command("next")
        self.assertIn("HUMAN_REQUIRED", output)
        self.assertIn(task["task_id"], output)
        self.assertIn("approve", output.lower())
        self.assertIn("reject", output.lower())

    def test_next_identifies_blocked_task(self):
        task = self.orch.create_task("next-blocked", description="blocked task", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "BLOCKED", "orchestrator", note="policy:block")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "block_rule",
            "decision": "BLOCK",
            "triggered": True,
            "reason": "manual review required",
        })

        output = self.console.handle_command("next")
        self.assertIn("BLOCKED", output)
        self.assertIn(task["task_id"], output)
        self.assertIn("manual review required", output)

    def test_next_identifies_active_work_and_agent_without_human_mutation(self):
        task = self.orch.create_task("next-active", description="active task", created_by="tester", assigned_agent="qa")
        self.orch.store.append_transition(task["task_id"], "QA", "orchestrator")

        output = self.console.handle_command("next")
        self.assertIn("ACTIVE", output)
        self.assertIn("qa", output.lower())
        self.assertNotIn("approve", output.lower())
        self.assertNotIn("reject", output.lower())

    def test_next_suggests_ready_or_backlog_task_when_actionable(self):
        task = self.orch.create_task("next-ready", description="ready task", created_by="tester", assigned_agent="architect")
        self.orch.store.append_transition(task["task_id"], "READY", "orchestrator")

        output = self.console.handle_command("next")
        self.assertIn("READY", output)
        self.assertIn(task["task_id"], output)
        self.assertIn("roadmap_stage_id", output.lower())

    def test_next_reports_no_action_when_no_actionable_task_exists(self):
        task = self.orch.create_task("next-complete", description="done", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "MERGE", "orchestrator")

        output = self.console.handle_command("next")
        self.assertIn("NO operator action required", output)

    def test_next_uses_deterministic_priority_across_multiple_tasks(self):
        blocked = self.orch.create_task("task-blocked", description="blocked", created_by="tester")
        self.orch.store.append_transition(blocked["task_id"], "BLOCKED", "orchestrator")
        self.orch.store.append_policy_result(blocked["task_id"], {
            "policy_id": "block_rule",
            "decision": "BLOCK",
            "triggered": True,
            "reason": "blocked higher priority",
        })

        human = self.orch.create_task("task-human", description="human task", created_by="tester")
        self.orch.store.append_transition(human["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(human["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "human approval required",
        })

        output = self.console.handle_command("next")
        self.assertIn("HUMAN_REQUIRED", output)
        self.assertIn(human["task_id"], output)
        self.assertNotIn(blocked["task_id"], output)

    def test_next_handles_missing_optional_metadata_without_crashing(self):
        task = self.orch.create_task("next-bare", description="bare task", created_by="tester")
        output = self.console.handle_command("next")
        self.assertIn("NEXT ACTION", output)
        self.assertIn(task["task_id"], output)

    def test_next_does_not_mutate_task_state(self):
        task = self.orch.create_task("next-no-mutation", description="read only", created_by="tester")
        before = self.orch.store.read_task(task["task_id"])
        self.console.handle_command("next")
        after = self.orch.store.read_task(task["task_id"])
        self.assertEqual(before, after)

    def test_existing_commands_remain_functional_after_next_guidance(self):
        task = self.orch.create_task("next-keep-working", description="keep working", created_by="tester")
        self.orch.store.append_transition(task["task_id"], "HUMAN_APPROVAL", "orchestrator")
        self.orch.store.append_policy_result(task["task_id"], {
            "policy_id": "require_human_approval",
            "decision": "REQUIRE_HUMAN_APPROVAL",
            "triggered": True,
            "reason": "human approval required",
        })

        self.assertIn("SYSTEM STATUS", self.console.handle_command("status"))
        self.assertIn(task["task_id"], self.console.handle_command("tasks"))
        self.assertIn(task["task_id"], self.console.handle_command(f"show {task['task_id']}"))
        self.assertIn("TASK HISTORY", self.console.handle_command(f"history {task['task_id']}"))
        self.assertIn("TASK EVIDENCE", self.console.handle_command(f"evidence {task['task_id']}"))
        self.assertIn("HUMAN_REQUIRED", self.console.handle_command("next"))

    def test_exit_command_closes_cleanly(self):
        output = self.console.handle_command("exit")
        self.assertIn("EXIT", output)


if __name__ == "__main__":
    unittest.main()
