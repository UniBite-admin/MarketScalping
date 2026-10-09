import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from tools.phase_runner import (
    GOVERNANCE_DOCUMENTS,
    Gate,
    GitState,
    Report,
    build_report,
    main,
    read_git_state,
    render_report,
)


def write_fixture(root, overrides=None):
    overrides = overrides or {}
    for relative_path in GOVERNANCE_DOCUMENTS:
        target = root / Path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(overrides.get(relative_path, "## Status\n\nEvidence unavailable.\n"), encoding="utf-8")


class PhaseRunnerTests(unittest.TestCase):
    def test_ambiguous_governance_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, {
                "docs/phases/phase-02-touch-detection/DECISIONS.md": (
                    "## Status\nHUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION\n"
                ),
                "docs/phases/phase-02-touch-detection/SPEC.md": (
                    "## Status\nDecision A — not approved\n"
                ),
            })
            with patch("tools.phase_runner.read_git_state", return_value=Mock(error=None)):
                report = build_report(root)

        gate = report.gates["Phase 2"]["Narrow decision approval"]
        self.assertEqual(gate.status, "BLOCKED")
        self.assertIn("contradictory", gate.explanation)

    def test_narrow_approval_dashes_do_not_imply_broader_authorization(self):
        for dash in ("-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212", "\u2E3A", "\u2E3B", "\u2E40", "\uFE58", "\uFE63", "\uFF0D"):
            with self.subTest(dash=dash), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_fixture(root, {
                    "docs/phases/phase-01-zone-formation/DECISIONS.md": (
                        "FROZEN {} HUMAN APPROVED\n".format(dash)
                    ),
                    "docs/phases/phase-02-touch-detection/DECISIONS.md": (
                        "HUMAN APPROVED {} PHASE 2 FORMATION-STATE DECISION\n"
                        "Decision A {} approved\n".format(dash, dash)
                    ),
                })
                with patch("tools.phase_runner.read_git_state", return_value=GitState()):
                    report = build_report(root)

                phase1 = report.gates["Phase 1"]
                phase2 = report.gates["Phase 2"]
                self.assertEqual(phase1["Narrow decision approval"].status, "SUPPORTED")
                self.assertEqual(phase1["Phase freeze"].status, "BLOCKED")
                self.assertEqual(phase1["Full phase acceptance"].status, "BLOCKED")
                self.assertEqual(phase1["Implementation authorization"].status, "BLOCKED")
                self.assertEqual(phase2["Narrow decision approval"].status, "SUPPORTED")
                self.assertEqual(phase2["Phase freeze"].status, "BLOCKED")
                self.assertEqual(phase2["Full phase acceptance"].status, "BLOCKED")
                self.assertEqual(phase2["Implementation authorization"].status, "BLOCKED")

    def test_conflicting_approval_evidence_with_different_dashes_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, {
                "docs/phases/phase-02-touch-detection/DECISIONS.md": (
                    "HUMAN APPROVED \u2013 PHASE 2 FORMATION-STATE DECISION\n"
                ),
                "docs/phases/phase-02-touch-detection/SPEC.md": (
                    "Decision A \u2212 not approved\n"
                ),
            })
            with patch("tools.phase_runner.read_git_state", return_value=GitState()):
                report = build_report(root)

        gate = report.gates["Phase 2"]["Narrow decision approval"]
        self.assertEqual(gate.status, "BLOCKED")
        self.assertIn("contradictory", gate.explanation)

    def test_narrow_approval_does_not_grant_implementation_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, {
                "docs/ROADMAP.md": (
                    "## Rules\nImplementation must not begin until the current phase is explicitly accepted.\n"
                ),
                "docs/phases/phase-02-touch-detection/DECISIONS.md": (
                    "## Status\nHUMAN APPROVED — PHASE 2 FORMATION-STATE DECISION\n"
                    "Decision A — approved\n"
                ),
            })
            with patch("tools.phase_runner.read_git_state", return_value=Mock(error=None)):
                report = build_report(root)

        self.assertEqual(report.gates["Phase 2"]["Narrow decision approval"].status, "SUPPORTED")
        self.assertEqual(report.gates["Phase 2"]["Implementation authorization"].status, "BLOCKED")

    def test_missing_governance_document_blocks_phase_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            (root / "docs/ROADMAP.md").unlink()
            with patch("tools.phase_runner.read_git_state", return_value=GitState()):
                report = build_report(root)

        self.assertIn("docs/ROADMAP.md", report.missing_documents)
        self.assertEqual(report.gates["Phase 2"]["Full phase acceptance"].status, "BLOCKED")
        self.assertIn("Missing governance documents", render_report(report))

    def test_unreadable_governance_document_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)
            (root / "docs/phases/phase-02-touch-detection/DECISIONS.md").write_text(
                "HUMAN APPROVED \u2014 PHASE 2 FORMATION-STATE DECISION\n",
                encoding="utf-8",
            )
            original_read_text = Path.read_text

            def read_text(path, *args, **kwargs):
                if path.as_posix().endswith("docs/phases/phase-02-touch-detection/DECISIONS.md"):
                    raise PermissionError("read denied")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", read_text), patch(
                "tools.phase_runner.read_git_state", return_value=GitState()
            ):
                report = build_report(root)

        self.assertEqual(len(report.read_errors), 1)
        self.assertIn("docs/phases/phase-02-touch-detection/DECISIONS.md", report.read_errors[0])
        self.assertEqual(report.gates["Phase 2"]["Narrow decision approval"].status, "BLOCKED")
        self.assertIn("Document read errors", render_report(report))

    def test_main_returns_nonzero_for_blocked_gates_and_required_input_failures(self):
        reports = (
            Report({"Phase": {"gate": Gate("BLOCKED", "not established")}}, GitState(), (), ()),
            Report({}, GitState(), ("docs/ROADMAP.md",), ()),
            Report({}, GitState(), (), ("docs/ROADMAP.md: read denied",)),
            Report({}, GitState(error="git status failed"), (), ()),
        )
        for report in reports:
            with self.subTest(report=report), patch(
                "tools.phase_runner.build_report", return_value=report
            ), redirect_stdout(StringIO()):
                self.assertNotEqual(main(), 0)

    def test_main_returns_zero_when_every_gate_and_input_is_clear(self):
        report = Report({"Phase": {"gate": Gate("SUPPORTED", "recorded")}}, GitState(), (), ())
        with patch("tools.phase_runner.build_report", return_value=report), redirect_stdout(StringIO()):
            self.assertEqual(main(), 0)

    def test_git_command_failure_is_explicit(self):
        result = Mock(returncode=128, stdout="", stderr="not a git repository")
        with patch("tools.phase_runner.subprocess.run", return_value=result):
            state = read_git_state(Path("."))

        self.assertIsNotNone(state.error)
        self.assertIn("not a git repository", state.error)

    def test_git_status_classifies_staged_unstaged_and_untracked(self):
        result = Mock(returncode=0, stdout="M  staged.txt\n M unstaged.txt\n?? new.txt\nMM both.txt\n", stderr="")
        with patch("tools.phase_runner.subprocess.run", return_value=result):
            state = read_git_state(Path("."))

        self.assertEqual(state.staged, ("staged.txt", "both.txt"))
        self.assertEqual(state.unstaged, ("unstaged.txt", "both.txt"))
        self.assertEqual(state.untracked, ("new.txt",))
        self.assertIsNone(state.error)

    def test_git_execution_oserror_is_explicit(self):
        with patch("tools.phase_runner.subprocess.run", side_effect=OSError("git missing")):
            state = read_git_state(Path("."))

        self.assertIn("unable to execute git status", state.error)


if __name__ == "__main__":
    unittest.main()