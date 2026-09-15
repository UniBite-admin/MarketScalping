import hashlib
import json
import os
import shutil
import tempfile
import unittest

from tools.orchestrator_core import Orchestrator
from tools.roadmap_loader import RoadmapLoader, RoadmapValidationError

ROOT = os.path.dirname(os.path.dirname(__file__))
ROADMAP_PATH = os.path.join(ROOT, ".agent", "roadmap", "master_roadmap.json")


class MasterRoadmapTests(unittest.TestCase):
    def setUp(self):
        self.loader = RoadmapLoader(roadmap_path=ROADMAP_PATH)

    def test_valid_master_roadmap_loads(self):
        self.assertEqual(self.loader.document["roadmap_id"], "marketscalping_master_roadmap")
        self.assertGreater(len(self.loader.document["stages"]), 20)

    def test_schema_validation_succeeds(self):
        self.assertIsNotNone(self.loader.get_stage("6A"))
        self.assertIsNotNone(self.loader.get_stage("6B"))
        self.assertIsNotNone(self.loader.get_stage("6C.1"))

    def test_duplicate_stage_ids_are_rejected(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        try:
            doc = {"roadmap_id": "x", "version": "1", "name": "x", "stages": [{"stage_id": "A", "title": "A", "description": "A", "depends_on": [], "risk_level": "low", "owner": "architect", "target_workflow_state": "READY", "required_evidence": ["e"], "exit_criteria": ["c"], "human_approval_required": False}, {"stage_id": "A", "title": "B", "description": "B", "depends_on": [], "risk_level": "low", "owner": "architect", "target_workflow_state": "READY", "required_evidence": ["e"], "exit_criteria": ["c"], "human_approval_required": False}]}
            json.dump(doc, tmp)
            tmp.close()
            with self.assertRaises(RoadmapValidationError):
                RoadmapLoader(roadmap_path=tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_missing_dependencies_rejected(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        try:
            doc = {"roadmap_id": "x", "version": "1", "name": "x", "stages": [{"stage_id": "B", "title": "B", "description": "B", "depends_on": ["A"], "risk_level": "low", "owner": "architect", "target_workflow_state": "READY", "required_evidence": ["e"], "exit_criteria": ["c"], "human_approval_required": False}]}
            json.dump(doc, tmp)
            tmp.close()
            with self.assertRaises(RoadmapValidationError):
                RoadmapLoader(roadmap_path=tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_dependency_cycles_are_rejected(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        try:
            doc = {"roadmap_id": "x", "version": "1", "name": "x", "stages": [{"stage_id": "A", "title": "A", "description": "A", "depends_on": ["B"], "risk_level": "low", "owner": "architect", "target_workflow_state": "READY", "required_evidence": ["e"], "exit_criteria": ["c"], "human_approval_required": False}, {"stage_id": "B", "title": "B", "description": "B", "depends_on": ["A"], "risk_level": "low", "owner": "architect", "target_workflow_state": "READY", "required_evidence": ["e"], "exit_criteria": ["c"], "human_approval_required": False}]}
            json.dump(doc, tmp)
            tmp.close()
            with self.assertRaises(RoadmapValidationError):
                RoadmapLoader(roadmap_path=tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_invalid_workflow_state_rejected(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        try:
            doc = {"roadmap_id": "x", "version": "1", "name": "x", "stages": [{"stage_id": "A", "title": "A", "description": "A", "depends_on": [], "risk_level": "low", "owner": "architect", "target_workflow_state": "NOT_A_REAL_STATE", "required_evidence": ["e"], "exit_criteria": ["c"], "human_approval_required": False}]}
            json.dump(doc, tmp)
            tmp.close()
            with self.assertRaises(RoadmapValidationError):
                RoadmapLoader(roadmap_path=tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_malformed_roadmap_fails_closed(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        try:
            tmp.write('{not valid json}')
            tmp.close()
            with self.assertRaises(RoadmapValidationError):
                RoadmapLoader(roadmap_path=tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_6a_and_6b_are_satisfied_at_repo_state(self):
        self.assertTrue(self.loader.determine_eligibility("6A", repo_root=ROOT))
        self.assertTrue(self.loader.determine_eligibility("6B", repo_root=ROOT))

    def test_6c1_eligible_and_6c2_unblocked_after_6c1_complete(self):
        self.assertTrue(self.loader.determine_eligibility("6C.1", completed_stage_ids=["6A", "6B"]))
        self.assertFalse(self.loader.determine_eligibility("6C.2", completed_stage_ids=["6A", "6B"]))
        self.assertTrue(self.loader.determine_eligibility("6C.2", completed_stage_ids=["6A", "6B", "6C.1"]))

    def test_step_7_blocked_until_step_6_closes(self):
        self.assertFalse(self.loader.determine_eligibility("7", completed_stage_ids=[]))
        self.assertTrue(self.loader.determine_eligibility("7", completed_stage_ids=["6"]))

    def test_roadmap_metadata_survives_task_creation(self):
        orch = Orchestrator()
        task = orch.create_task("Roadmap planning task", roadmap_stage_id="6C.1")
        self.assertEqual(task["roadmap_stage_id"], "6C.1")
        self.assertEqual(task["roadmap_id"], "marketscalping_master_roadmap")
        self.assertEqual(task["roadmap_version"], "2026.09.13")
        self.assertEqual(task["status"], "BACKLOG")
        self.assertTrue(task["task_id"])

    def test_roadmap_metadata_does_not_replace_task_state(self):
        orch = Orchestrator()
        task = orch.create_task("Task state check", roadmap_stage_id="6C.1")
        self.assertEqual(task["status"], "BACKLOG")
        self.assertTrue(task.get("task_id"))
        self.assertNotIn("workflow_state", task)

    def test_stage_7_materializes_first_child_stage_into_task_spec(self):
        orch = Orchestrator()
        task = orch.create_task("Stage 7 child materialization", created_by="operator", roadmap_stage_id="7")
        task_spec = task.get("task_spec") or {}
        self.assertEqual(task_spec.get("roadmap_parent_stage_id"), "7")
        self.assertEqual(task_spec.get("roadmap_child_stage_id"), "7.1")
        self.assertEqual(task_spec.get("roadmap_child_stage_title"), "7.1 — Historical Data Contract / Canonical Schema")
        self.assertIn("canonical", (task_spec.get("roadmap_child_stage_description") or "").lower())
        self.assertIn("required_evidence", task_spec)
        self.assertIn("exit_criteria", task_spec)

    def test_explicit_task_spec_values_are_preserved_when_roadmap_stage_is_materialized(self):
        orch = Orchestrator()
        explicit_spec = {"target_paths": ["market_data.py"], "keywords": ["historical"], "repository_context": {"file_list": ["market_data.py"]}}
        task = orch.create_task("Preserve explicit task spec", created_by="operator", roadmap_stage_id="7", task_spec=explicit_spec)
        task_spec = task.get("task_spec") or {}
        self.assertEqual(task_spec.get("target_paths"), ["market_data.py"])
        self.assertEqual(task_spec.get("keywords"), ["historical"])
        self.assertEqual(task_spec.get("repository_context"), {"file_list": ["market_data.py"]})
        self.assertEqual(task_spec.get("roadmap_child_stage_id"), "7.1")

    def test_roadmap_cannot_directly_perform_workflow_transitions(self):
        orch = Orchestrator()
        task = orch.create_task("Roadmap cannot bypass workflow", roadmap_stage_id="6C.1")
        with self.assertRaises(ValueError):
            orch.transition_task(task["task_id"], "MERGE", actor="tester")

    def test_runtime_does_not_write_or_update_roadmap(self):
        orch = Orchestrator()
        path = ROADMAP_PATH
        with open(path, "r", encoding="utf-8") as fh:
            before = fh.read()
        before_hash = hashlib.sha256(before.encode("utf-8")).hexdigest()
        orch.create_task("Runtime no-write", roadmap_stage_id="6C.1")
        with open(path, "r", encoding="utf-8") as fh:
            after = fh.read()
        self.assertEqual(hashlib.sha256(after.encode("utf-8")).hexdigest(), before_hash)

    def test_workflow_and_policy_authority_stays_unchanged(self):
        orch = Orchestrator()
        task = orch.create_task("Policy check", changed_paths=["risk_engine.py"])
        res = orch.transition_task(task["task_id"], "TRIAGE", actor="tester")
        self.assertIn(res["status"], ("ok", "pending_safety_review", "pending_human_approval", "blocked", "blocked_unknown", "noop"))
        self.assertNotIn("roadmap_stage_id", res)


if __name__ == "__main__":
    unittest.main()
