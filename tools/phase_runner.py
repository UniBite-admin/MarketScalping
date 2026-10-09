"""Read-only governance and worktree report for the current roadmap phases."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence


VERSION = "0.1"
DASH_SEPARATOR = r"-"

GOVERNANCE_DOCUMENTS = (
    "docs/ROADMAP.md",
    "docs/phases/phase-01-zone-formation/DECISIONS.md",
    "docs/phases/phase-01-zone-formation/SPEC.md",
    "docs/phases/phase-01-zone-formation/AUDIT.md",
    "docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md",
    "docs/phases/phase-01-zone-formation/PHASE_1_CLOSURE_AUDIT.md",
    "docs/phases/phase-02-touch-detection/DECISIONS.md",
    "docs/phases/phase-02-touch-detection/SPEC.md",
    "docs/phases/phase-02-touch-detection/AUDIT.md",
    "docs/phases/phase-02-touch-detection/TEST_REQUIREMENTS.md",
    "docs/phases/phase-02-touch-detection/EVIDENCE_ASSESSMENT.md",
)


@dataclass(frozen=True)
class Evidence:
    path: str
    line: int
    heading: str
    text: str

    def reference(self) -> str:
        suffix = " > " + self.heading if self.heading else ""
        return "{}:{}{}".format(self.path, self.line, suffix)


def _normalize_dashes(text: str) -> str:
    return "".join(
        "-" if unicodedata.category(character) == "Pd" or character == "\u2212" else character
        for character in text
    )


@dataclass(frozen=True)
class Document:
    path: str
    text: str

    def evidence(self, patterns: Iterable[str]) -> list[Evidence]:
        compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        results: list[Evidence] = []
        heading = ""
        for number, line in enumerate(self.text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                heading = line.lstrip("# ").strip()
            if any(pattern.search(_normalize_dashes(line)) for pattern in compiled):
                results.append(Evidence(self.path, number, heading, line.strip()[:240]))
        return results


@dataclass(frozen=True)
class Gate:
    status: str
    explanation: str
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class GitState:
    staged: tuple[str, ...] = ()
    unstaged: tuple[str, ...] = ()
    untracked: tuple[str, ...] = ()
    error: Optional[str] = None


@dataclass(frozen=True)
class Report:
    gates: dict[str, dict[str, Gate]]
    git: GitState
    missing_documents: tuple[str, ...]
    read_errors: tuple[str, ...]


def _deduplicate(evidence: Iterable[Evidence]) -> tuple[Evidence, ...]:
    seen: set[tuple[str, int]] = set()
    unique: list[Evidence] = []
    for item in evidence:
        key = (item.path, item.line)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return tuple(unique)


def _collect(documents: dict[str, Document], paths: Sequence[str], patterns: Iterable[str]) -> tuple[Evidence, ...]:
    found: list[Evidence] = []
    for path in paths:
        document = documents.get(path)
        if document is not None:
            found.extend(document.evidence(patterns))
    return _deduplicate(found)


def _gate(
    documents: dict[str, Document],
    missing: Sequence[str],
    paths: Sequence[str],
    positive_patterns: Sequence[str],
    negative_patterns: Sequence[str],
    description: str,
    not_established: str,
) -> Gate:
    relevant_missing = tuple(path for path in paths if path in missing)
    positive = _collect(documents, paths, positive_patterns)
    negative = _collect(documents, paths, negative_patterns)
    if relevant_missing:
        return Gate(
            "BLOCKED",
            "Required governance evidence is missing: {}.".format(", ".join(relevant_missing)),
            _deduplicate((*positive, *negative)),
        )
    if positive and negative:
        return Gate(
            "BLOCKED",
            "Governance evidence is contradictory; the runner does not choose a permissive interpretation.",
            _deduplicate((*positive, *negative)),
        )
    if negative:
        return Gate("BLOCKED", description, negative)
    if positive:
        return Gate("SUPPORTED", description, positive)
    return Gate("BLOCKED", not_established)


def read_documents(root: Path) -> tuple[dict[str, Document], tuple[str, ...], tuple[str, ...]]:
    documents: dict[str, Document] = {}
    missing: list[str] = []
    errors: list[str] = []
    for relative_path in GOVERNANCE_DOCUMENTS:
        path = root / Path(relative_path)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            missing.append(relative_path)
        except (OSError, UnicodeError) as exc:
            errors.append("{}: {}".format(relative_path, exc))
        else:
            documents[relative_path] = Document(relative_path, text)
    return documents, tuple(missing), tuple(errors)


def read_git_state(root: Path) -> GitState:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=str(root), capture_output=True, text=True, check=False, env=environment,
        )
    except OSError as exc:
        return GitState(error="unable to execute git status: {}".format(exc))
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic supplied"
        return GitState(error="git status exited with code {}: {}".format(result.returncode, detail))

    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 3:
            continue
        index_status, worktree_status = line[0], line[1]
        name = line[3:]
        if index_status == "?" and worktree_status == "?":
            untracked.append(name)
            continue
        if index_status != " ":
            staged.append(name)
        if worktree_status != " ":
            unstaged.append(name)
    return GitState(tuple(staged), tuple(unstaged), tuple(untracked))


def build_report(root: Path) -> Report:
    documents, missing, read_errors = read_documents(root)
    unavailable = (*missing, *(error.split(": ", 1)[0] for error in read_errors))
    roadmap = ("docs/ROADMAP.md",)
    phase1 = (
        "docs/phases/phase-01-zone-formation/DECISIONS.md",
        "docs/phases/phase-01-zone-formation/SPEC.md",
        "docs/phases/phase-01-zone-formation/AUDIT.md",
        "docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md",
    )
    phase1_closure = ("docs/phases/phase-01-zone-formation/PHASE_1_CLOSURE_AUDIT.md",)
    phase2 = (
        "docs/phases/phase-02-touch-detection/DECISIONS.md",
        "docs/phases/phase-02-touch-detection/SPEC.md",
        "docs/phases/phase-02-touch-detection/AUDIT.md",
        "docs/phases/phase-02-touch-detection/TEST_REQUIREMENTS.md",
        "docs/phases/phase-02-touch-detection/EVIDENCE_ASSESSMENT.md",
    )

    narrow1 = _gate(
        documents, unavailable, (phase1[0],),
        (
            r"FROZEN\s*" + DASH_SEPARATOR + r"\s*HUMAN APPROVED",
            r"human project authority has explicitly approved",
        ),
        (),
        "Narrow Phase 1 decision approval is recorded; this covers only the stated decision scopes.",
        "No explicit narrow Phase 1 human approval was found.",
    )
    narrow2 = _gate(
        documents, unavailable, phase2,
        (
            r"HUMAN APPROVED\s*" + DASH_SEPARATOR + r"\s*PHASE 2 FORMATION-STATE DECISION",
            r"Decision A\s*" + DASH_SEPARATOR + r"\s*approved",
        ),
        (r"Decision A\s*" + DASH_SEPARATOR + r"\s*not approved",),
        "The narrow Phase 2 formation-state/touch decision is approved; that does not establish phase freeze, acceptance, or implementation permission.",
        "No explicit narrow Phase 2 decision approval was found.",
    )
    freeze1 = _gate(
        documents, unavailable, (phase1[0],),
        (r"Phase 1 status:\s*FROZEN\s*/\s*HUMAN APPROVED",),
        (r"Phase 1 status:\s*NOT FROZEN",),
        "Phase 1 has an explicit phase freeze record.",
        "An explicit phase-level Phase 1 freeze record was not found.",
    )
    freeze2 = Gate(
        "BLOCKED",
        "A narrow Phase 2 semantic decision is recorded, but no explicit Phase 2 phase-freeze record was found.",
        _collect(documents, (phase2[0], phase2[1]), (
            r"HUMAN APPROVED\s*" + DASH_SEPARATOR + r"\s*PHASE 2 FORMATION-STATE DECISION",
            r"limited to the first valid Zone formation event",
            r"does not define later lifecycle semantics",
        )),
    )
    acceptance1 = _gate(
        documents, unavailable, phase1_closure,
        (
            r"Phase 1\s+(?:is\s+)?fully accepted",
            r"final Phase 1 acceptance:\s*ACCEPTED",
            r"Phase 1 satisfies its authoritative acceptance requirements",
            r"Phase 1 contract:\s*accepted as documented",
        ),
        (r"final human approval is still required", r"READY FOR HUMAN FREEZE", r"READY FOR HUMAN FREEZE\s+ONLY"),
        "Phase 1 full acceptance is explicitly recorded.",
        "The closure evidence does not establish unambiguous full Phase 1 acceptance.",
    )
    acceptance2 = _gate(
        documents, unavailable, (roadmap[0],) + phase2,
        (
            r"Phase 2 (?:full phase )?acceptance:\s*ACCEPTED",
            r"Phase 2 has been explicitly accepted",
        ),
        (r"Phase 2 status:\s*NOT STARTED", r"Human freeze readiness:\s*NO"),
        "Full Phase 2 acceptance is explicitly recorded.",
        "No explicit full Phase 2 acceptance is recorded; narrow decision approval and test requirements do not establish full phase acceptance.",
    )
    implementation = _gate(
        documents, unavailable, (roadmap[0], phase1[0], phase2[0]),
        (r"implementation\s+(?:is\s+)?authorized", r"authorized\s+to\s+implement"),
        (r"does not authorize implementation", r"does not authorize production implementation", r"implementation must not begin until"),
        "An explicit implementation authorization is recorded.",
        "No explicit implementation authorization was found; narrow approval or freeze is not treated as authorization.",
    )

    gates = {
        "Phase 1": {
            "Narrow decision approval": narrow1,
            "Phase freeze": freeze1,
            "Full phase acceptance": acceptance1,
            "Implementation authorization": implementation,
        },
        "Phase 2": {
            "Narrow decision approval": narrow2,
            "Phase freeze": freeze2,
            "Full phase acceptance": acceptance2,
            "Implementation authorization": implementation,
        },
    }
    return Report(gates, read_git_state(root), missing, read_errors)


def _format_evidence(evidence: Sequence[Evidence]) -> list[str]:
    return ["  - `{}` — {}".format(item.reference(), item.text) for item in evidence]


def render_report(report: Report) -> str:
    lines = ["# MarketScalping Phase Runner v{}".format(VERSION), ""]
    if report.missing_documents:
        lines.extend(["## Missing governance documents", ""])
        lines.extend("- `{}`".format(path) for path in report.missing_documents)
        lines.append("")
    if report.read_errors:
        lines.extend(["## Document read errors", ""])
        lines.extend("- {}".format(error) for error in report.read_errors)
        lines.append("")

    lines.extend(["## Governance gates", ""])
    for phase, phase_gates in report.gates.items():
        lines.extend(["### {}".format(phase), ""])
        for name, gate in phase_gates.items():
            lines.append("- **{}: {}** — {}".format(name, gate.status, gate.explanation))
            lines.extend(_format_evidence(gate.evidence))
        lines.append("")

    lines.extend(["## Git worktree status", ""])
    if report.git.error:
        lines.append("**ERROR** — {}".format(report.git.error))
    else:
        for label, entries in (("Staged", report.git.staged), ("Unstaged", report.git.unstaged), ("Untracked", report.git.untracked)):
            shown = ", ".join("`{}`".format(path) for path in entries) if entries else "none detected"
            lines.append("- **{} ({}):** {}".format(label, len(entries), shown))
    return "\n".join(lines) + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = build_report(root)
    sys.stdout.write(render_report(report))
    if (
        report.git.error
        or report.missing_documents
        or report.read_errors
        or any(
            gate.status == "BLOCKED"
            for phase_gates in report.gates.values()
            for gate in phase_gates.values()
        )
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())