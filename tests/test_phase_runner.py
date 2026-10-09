import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.phase_runner import GOVERNANCE_DOCUMENTS, build_report


def write_fixture(root, overrides=None):
    overrides = overrides or {}
    for relative_path in GOVERNANCE_DOCUMENTS:
        target = root / Path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(overrides.get(relative_path, "## Status\n\nEvidence unavailable.\n"), encoding="utf-8")


class PhaseRunnerTests(unittest.TestCase):
    def test_narrow_approval_does_not_grant_implementation_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, {
                "docs/ROADMAP.md": "## Rules\nImplementation must not begin until the current phase is explicitly accepted.\n",
                "docs/phases/phase-02-touch-detection/DECISIONS.md": "## Status\nHUMAN APPROVED - PHASE 2 FORMATION-STATE DECISION\nDecision A - approved\n",
                "docs/phases/phase-02-touch-detection/SPEC.md": "## Status\nDecision A - approved\n",
            })
            with patch("tools.phase_runner.read_git_state", return_value=Mock(error=None)):
                report = build_report(root)

        self.assertEqual(report.gates["Phase 2"]["Narrow decision approval"].status, "SUPPORTED")
        self.assertEqual(report.gates["Phase 2"]["Implementation authorization"].status, "BLOCKED")

    def test_ambiguous_governance_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, {
                "docs/phases/phase-02-touch-detection/DECISIONS.md": "## Status\nHUMAN APPROVED - PHASE 2 FORMATION-STATE DECISION\n",
                "docs/phases/phase-02-touch-detection/SPEC.md": "## Status\nDecision A - not approved\n",
            })
            with patch("tools.phase_runner.read_git_state", return_value=Mock(error=None)):
                report = build_report(root)

        gate = report.gates["Phase 2"]["Narrow decision approval"]
        self.assertEqual(gate.status, "BLOCKED")
        self.assertIn("contradictory", gate.explanation)

    def test_phase_2_freeze_record_is_recognized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, {
                "docs/ROADMAP.md": "## Rules\nImplementation must not begin until the current phase is explicitly accepted.\n",
                "docs/phases/phase-02-touch-detection/DECISIONS.md": "## Status\nFROZEN — HUMAN APPROVED\nPhase 2 status: FROZEN / HUMAN APPROVED\nHuman decision: \"I freeze Phase 2 based on the current evidence.\"\n",
                "docs/phases/phase-02-touch-detection/SPEC.md": "## Status\nDecision A - approved\n",
            })
            with patch("tools.phase_runner.read_git_state", return_value=Mock(error=None)):
                report = build_report(root)

        self.assertEqual(report.gates["Phase 2"]["Phase freeze"].status, "SUPPORTED")

    def test_phase_2_decisions_record_explicit_implementation_authorization(self):
        root = Path(__file__).resolve().parents[1]
        decisions = (root / "docs/phases/phase-02-touch-detection/DECISIONS.md").read_text(encoding="utf-8")
        self.assertIn("Implementation is authorized", decisions)
        self.assertIn("narrow Phase 2 Touch Detection boundary only", decisions)
        self.assertIn("does not authorize broader lifecycle work", decisions)


if __name__ == "__main__":
    unittest.main()
