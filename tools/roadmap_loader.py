#!/usr/bin/env python3
"""Deterministic planning-layer support for the Master Roadmap.

This module does not execute runtime workflow transitions. It loads a versioned
roadmap definition, validates its integrity, and exposes dependency-resolution and
eligibility checks to the Orchestrator without turning the roadmap into a second
runtime authority.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional, Set

ROOT = os.path.dirname(os.path.dirname(__file__))
DEFAULT_ROADMAP_PATH = os.path.join(ROOT, ".agent", "roadmap", "master_roadmap.json")
WORKFLOW_PATH = os.path.join(ROOT, ".agent", "workflows", "workflow.json")


class RoadmapValidationError(ValueError):
    """Raised when the roadmap definition is malformed or ambiguous."""


class RoadmapLoader:
    """Validate and query the project roadmap without writing runtime state."""

    def __init__(self, roadmap_path: Optional[str] = None, workflow_path: Optional[str] = None):
        self.roadmap_path = roadmap_path or DEFAULT_ROADMAP_PATH
        self.workflow_path = workflow_path or WORKFLOW_PATH
        self.document = self._load_document()
        self.stages_by_id = self._index_stages(self.document.get("stages", []))
        self.workflow_states = self._load_workflow_states()
        self._validate_document(self.document)
        self._validate_schema()

    def _load_document(self) -> Dict[str, Any]:
        if not os.path.exists(self.roadmap_path):
            raise RoadmapValidationError(f"Roadmap file not found: {self.roadmap_path}")
        with open(self.roadmap_path, "r", encoding="utf-8") as fh:
            try:
                doc = json.load(fh)
            except json.JSONDecodeError as exc:
                raise RoadmapValidationError(f"Malformed roadmap JSON: {exc}") from exc
        if not isinstance(doc, dict):
            raise RoadmapValidationError("Roadmap root must be a JSON object.")
        return doc

    def _load_workflow_states(self) -> Set[str]:
        if not os.path.exists(self.workflow_path):
            return set()
        with open(self.workflow_path, "r", encoding="utf-8") as fh:
            try:
                wf = json.load(fh)
            except json.JSONDecodeError as exc:
                raise RoadmapValidationError(f"Malformed workflow JSON: {exc}") from exc
        states = wf.get("states", [])
        if not isinstance(states, list):
            raise RoadmapValidationError("Workflow states must be a list.")
        return {str(state) for state in states}

    def _index_stages(self, stages: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        indexed: Dict[str, Dict[str, Any]] = {}
        for item in stages:
            if not isinstance(item, dict):
                raise RoadmapValidationError("Each roadmap stage must be an object.")
            stage_id = str(item.get("stage_id") or "").strip()
            if not stage_id:
                raise RoadmapValidationError("Each roadmap stage requires a non-empty stage_id.")
            indexed[stage_id] = item
        return indexed

    def _validate_schema(self) -> None:
        schema_path = os.path.join(ROOT, ".agent", "roadmap", "roadmap.schema.json")
        if not os.path.exists(schema_path):
            raise RoadmapValidationError("Roadmap schema file not found.")
        with open(schema_path, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
        if not isinstance(schema, dict):
            raise RoadmapValidationError("Roadmap schema must be a JSON object.")
        required_schema_keys = ("$schema", "title", "type", "properties", "$defs")
        for key in required_schema_keys:
            if key not in schema:
                raise RoadmapValidationError(f"Roadmap schema missing required field: {key}")
        if not isinstance(self.document.get("stages", []), list):
            raise RoadmapValidationError("Roadmap stages must be an array as required by the schema.")
        for stage in self.document.get("stages", []):
            if not isinstance(stage, dict):
                raise RoadmapValidationError("Each roadmap stage must be an object.")
            for field in ("stage_id", "title", "description", "depends_on", "risk_level", "owner", "target_workflow_state", "required_evidence", "exit_criteria", "human_approval_required"):
                if field not in stage:
                    raise RoadmapValidationError(f"Roadmap stage missing required field: {field}")

    def _validate_document(self, document: Dict[str, Any]) -> None:
        required = ("roadmap_id", "version", "name", "stages")
        for key in required:
            if key not in document:
                raise RoadmapValidationError(f"Roadmap missing required field: {key}")
        stages = document.get("stages")
        if not isinstance(stages, list) or not stages:
            raise RoadmapValidationError("Roadmap stages must be a non-empty list.")

        seen: Set[str] = set()
        for stage in stages:
            if not isinstance(stage, dict):
                raise RoadmapValidationError("Each stage must be an object.")
            stage_id = str(stage.get("stage_id") or "").strip()
            if not stage_id:
                raise RoadmapValidationError("Stage requires a non-empty stage_id.")
            if stage_id in seen:
                raise RoadmapValidationError(f"Duplicate stage_id detected: {stage_id}")
            seen.add(stage_id)

            for field in ("title", "description"):
                if not stage.get(field):
                    raise RoadmapValidationError(f"Stage {stage_id} missing {field}.")
            if "depends_on" in stage and not isinstance(stage.get("depends_on"), list):
                raise RoadmapValidationError(f"Stage {stage_id} depends_on must be a list.")
            if "target_workflow_state" in stage and stage.get("target_workflow_state") not in self.workflow_states:
                raise RoadmapValidationError(
                    f"Stage {stage_id} declares an unknown workflow state: {stage.get('target_workflow_state')}"
                )
            if "required_evidence" in stage and not isinstance(stage.get("required_evidence"), list):
                raise RoadmapValidationError(f"Stage {stage_id} required_evidence must be a list.")
            if "exit_criteria" in stage and not isinstance(stage.get("exit_criteria"), list):
                raise RoadmapValidationError(f"Stage {stage_id} exit_criteria must be a list.")
            if "human_approval_required" in stage and not isinstance(stage.get("human_approval_required"), bool):
                raise RoadmapValidationError(f"Stage {stage_id} human_approval_required must be boolean.")

        for stage in stages:
            stage_id = str(stage.get("stage_id") or "").strip()
            depends = stage.get("depends_on", [])
            if not isinstance(depends, list):
                raise RoadmapValidationError(f"Stage {stage_id} has invalid depends_on format.")
            for dep in depends:
                dep_id = str(dep).strip()
                if dep_id not in seen:
                    raise RoadmapValidationError(f"Stage {stage_id} depends on unknown stage {dep_id}.")
            parent = stage.get("parent_stage_id")
            if parent is not None:
                parent_id = str(parent).strip()
                if parent_id not in seen:
                    raise RoadmapValidationError(f"Stage {stage_id} references unknown parent {parent_id}.")

        self._validate_no_cycles(stages)

    def _validate_no_cycles(self, stages: List[Dict[str, Any]]) -> None:
        stage_map = {str(stage.get("stage_id") or "").strip(): stage for stage in stages}
        visited: Set[str] = set()
        stack: Set[str] = set()

        def visit(stage_id: str) -> None:
            if stage_id in stack:
                raise RoadmapValidationError(f"Dependency cycle detected involving stage {stage_id}.")
            if stage_id in visited:
                return
            stack.add(stage_id)
            for dep in stage_map.get(stage_id, {}).get("depends_on", []) or []:
                visit(str(dep))
            stack.remove(stage_id)
            visited.add(stage_id)

        for stage_id in stage_map:
            visit(stage_id)

    def stage_ids(self) -> List[str]:
        return sorted(self.stages_by_id.keys())

    def get_stage(self, stage_id: str) -> Optional[Dict[str, Any]]:
        return self.stages_by_id.get(str(stage_id))

    def resolve_dependencies(self, stage_id: str) -> List[str]:
        stage = self.get_stage(stage_id)
        if stage is None:
            raise RoadmapValidationError(f"Unknown stage_id: {stage_id}")
        ordered: List[str] = []
        seen: Set[str] = set()

        def walk(current: str) -> None:
            if current in seen:
                return
            seen.add(current)
            for dep in stage_map(current).get("depends_on", []) or []:
                walk(str(dep))
            ordered.append(current)

        def stage_map(current: str) -> Dict[str, Any]:
            return self.stages_by_id.get(str(current), {})

        walk(str(stage_id))
        return ordered

    def determine_eligibility(
        self,
        stage_id: str,
        completed_stage_ids: Optional[Iterable[str]] = None,
        repo_root: Optional[str] = None,
    ) -> bool:
        stage = self.get_stage(stage_id)
        if stage is None:
            return False

        completed = {str(item) for item in (completed_stage_ids or [])}
        if repo_root is not None:
            completed |= self.default_completed_stages(repo_root)

        deps = stage.get("depends_on", []) or []
        if not deps:
            return True
        return all(str(dep) in completed for dep in deps)

    def default_completed_stages(self, repo_root: Optional[str] = None) -> Set[str]:
        root = repo_root or ROOT
        completed: Set[str] = set()
        for stage in self.document.get("stages", []):
            stage_id = str(stage.get("stage_id") or "").strip()
            evidence_refs = stage.get("evidence_refs", []) or []
            if not isinstance(evidence_refs, list):
                continue
            if not evidence_refs:
                continue
            evidence_ok = True
            for ref in evidence_refs:
                raw = str(ref).replace("\\", "/")
                normalized = raw
                if normalized.startswith("./"):
                    normalized = normalized[2:]
                if normalized.startswith("/"):
                    normalized = normalized[1:]
                resolved = os.path.join(root, normalized)
                if not os.path.exists(resolved):
                    evidence_ok = False
                    break
            if evidence_ok:
                completed.add(stage_id)
        return completed

    @classmethod
    def load_default(cls, repo_root: Optional[str] = None) -> "RoadmapLoader":
        return cls(roadmap_path=os.path.join(repo_root or ROOT, ".agent", "roadmap", "master_roadmap.json"))


__all__ = ["RoadmapLoader", "RoadmapValidationError"]
