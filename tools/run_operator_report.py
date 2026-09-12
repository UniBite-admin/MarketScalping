import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from tools.monitor_pipeline_health import analyze as monitor_analyze
    from tools.monitor_pipeline_health import read_rows as monitor_read_rows
    from tools.query_normalized_events import report_funnel
    from tools.query_normalized_events import report_positions
    from tools.query_normalized_events import report_reasons
    from tools.query_normalized_events import report_rollup
    from tools.summarize_normalized_events import summarize as summarize_normalized
except ImportError:  # pragma: no cover - direct script execution fallback
    from monitor_pipeline_health import analyze as monitor_analyze
    from monitor_pipeline_health import read_rows as monitor_read_rows
    from query_normalized_events import report_funnel
    from query_normalized_events import report_positions
    from query_normalized_events import report_reasons
    from query_normalized_events import report_rollup
    from summarize_normalized_events import summarize as summarize_normalized

from tools.orchestrator_core import Orchestrator


DEFAULT_INPUT = Path("data") / "normalized_events.csv"
DEFAULT_REPORT_DIR = Path("reports")


def _to_jsonable(obj):
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, tuple):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def build_report(
    input_path: Path,
    stale_tick_ms_max: float,
    min_candidate_ratio: float,
    min_approval_ratio: float,
    max_execution_skip_ratio: float,
    max_no_candidate_streak: int,
) -> dict:
    rows = monitor_read_rows(input_path)

    stage8 = summarize_normalized(input_path)
    stage9 = {
        "rollup": report_rollup(rows),
        "reasons": report_reasons(rows, top=10),
        "funnel": report_funnel(rows),
        "positions": report_positions(rows),
    }
    stage10 = monitor_analyze(
        rows=rows,
        stale_tick_ms_max=stale_tick_ms_max,
        min_candidate_ratio=min_candidate_ratio,
        min_approval_ratio=min_approval_ratio,
        max_execution_skip_ratio=max_execution_skip_ratio,
        max_no_candidate_streak=max_no_candidate_streak,
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    operator_status = "HEALTHY" if stage10.get("health_status") == "HEALTHY" else "DEGRADED"

    return {
        "generated_at_utc": generated_at,
        "input_file": str(input_path),
        "operator_status": operator_status,
        "stage8": _to_jsonable(stage8),
        "stage9": _to_jsonable(stage9),
        "stage10": _to_jsonable(stage10),
    }


def render_markdown(report: dict) -> str:
    lines = []
    lines.append("# Operator Consolidated Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): {report['generated_at_utc']}")
    lines.append(f"- Input: {report['input_file']}")
    lines.append(f"- Operator status: {report['operator_status']}")
    lines.append("")

    s8 = report["stage8"]
    lines.append("## Stage 8 Analytics")
    lines.append(f"- Total rows: {s8.get('total_rows')}")
    lines.append(f"- First timestamp: {s8.get('first_timestamp')}")
    lines.append(f"- Last timestamp: {s8.get('last_timestamp')}")
    lines.append(f"- Events per minute: {s8.get('events_per_minute')}")
    lines.append(f"- Avg spread pct: {s8.get('avg_spread_pct')}")
    lines.append("")

    lines.append("### Layer Counts")
    for layer in ["feature", "strategy", "risk", "execution", "position"]:
        lines.append(f"- {layer}: {s8.get('layer_counts', {}).get(layer, 0)}")
    lines.append("")

    s9 = report["stage9"]
    lines.append("## Stage 9 Query Snapshot")
    funnel = s9.get("funnel", {})
    lines.append(f"- Strategy candidates: {funnel.get('strategy_candidate_rows', 0)}")
    lines.append(f"- Risk approved: {funnel.get('risk_approved_rows', 0)}")
    lines.append(f"- Execution simulated: {funnel.get('execution_simulated_rows', 0)}")
    lines.append(f"- Candidate to approved ratio: {funnel.get('candidate_to_approved_ratio', 0.0)}")
    lines.append(f"- Approved to simulated ratio: {funnel.get('approved_to_execution_sim_ratio', 0.0)}")
    lines.append("")

    reasons = s9.get("reasons", {}).get("top_reasons", [])
    lines.append("### Top Risk Reasons")
    if not reasons:
        lines.append("- none")
    else:
        for item in reasons:
            lines.append(f"- {item.get('reason')}: {item.get('count')}")
    lines.append("")

    pos = s9.get("positions", {})
    lines.append("### Position Snapshot")
    lines.append(f"- Position entities: {pos.get('position_count', 0)}")
    lines.append(f"- Open positions: {pos.get('open_positions', 0)}")
    lines.append(f"- Closed positions: {pos.get('closed_positions', 0)}")
    lines.append("")

    s10 = report["stage10"]
    lines.append("## Stage 10 Monitoring")
    lines.append(f"- Health status: {s10.get('health_status')}")
    lines.append("### Alerts")
    alerts = s10.get("alerts", [])
    if not alerts:
        lines.append("- none")
    else:
        for alert in alerts:
            lines.append(f"- [{alert.get('severity')}] {alert.get('code')}: {alert.get('message')}")

    return "\n".join(lines) + "\n"


def render_snapshot_text(snapshot: dict) -> str:
    lines = []
    summary = snapshot.get("summary") or {}
    tasks = snapshot.get("tasks") or []
    runs = (snapshot.get("runtime") or {}).get("runs") or []

    def _task_for_context():
        if not tasks:
            return None
        terminal_states = {"FAILED", "BLOCKED", "ESCALATED", "MERGE", "MONITOR"}
        return next((task for task in tasks if task.get("status") not in terminal_states), tasks[0])

    active_task = _task_for_context()
    current_state = active_task.get("status") if active_task else "UNKNOWN"
    current_agent = "UNKNOWN"
    if runs:
        current_agent = runs[-1].get("agent_role", "UNKNOWN")

    lines.append("SYSTEM STATUS")
    lines.append(f"- overall_status: {summary.get('task_count', 0)} task(s) | {summary.get('active_task_count', 0)} active")
    if not tasks:
        lines.append("- No active tasks")
    lines.append(f"- repository_revision: {active_task.get('repository_revision', 'unknown') if active_task else 'unknown'}")
    lines.append(f"- snapshot_timestamp: {snapshot.get('snapshot_timestamp_utc', 'unknown')}")
    lines.append(f"- by_status: {summary.get('by_status', {})}")
    lines.append("")

    lines.append("CURRENT TASK")
    if not active_task:
        lines.append("- task_id: NONE")
        lines.append("- task_status: NONE")
        lines.append("- current_workflow_state: NONE")
        lines.append("- responsible_agent: NONE")
    else:
        lines.append(f"- task_id: {active_task.get('task_id', 'unknown')}")
        lines.append(f"- task_status: {current_state}")
        lines.append(f"- current_workflow_state: {current_state}")
        lines.append(f"- responsible_agent: {current_agent}")
    lines.append("")

    lines.append("WORKFLOW")
    workflow_states = ["TASK", "TRIAGE", "ARCHITECTURE", "READY", "DEVELOPMENT", "CI", "QA", "SAFETY", "HUMAN_APPROVAL", "MERGE"]
    if not active_task:
        lines.append("TASK")
        lines.append("  ↓")
        lines.append("No tasks")
        lines.append("  ↓")
        lines.append("Empty")
    else:
        for idx, state in enumerate(workflow_states):
            marker = "CURRENT" if state == current_state else " "
            prefix = "->" if idx > 0 else " "
            lines.append(f"{prefix} {state}{' [CURRENT]' if marker == 'CURRENT' else ''}")
            if idx < len(workflow_states) - 1:
                lines.append("  ↓")
    lines.append("")

    lines.append("AGENT ACTIVITY")
    if not runs:
        lines.append("- NONE")
    else:
        for run in runs:
            role = run.get("agent_role", "UNKNOWN")
            run_id = run.get("run_id", "unknown")
            status = run.get("artifact_type", "UNKNOWN")
            lines.append(f"- role: {role} | run_id: {run_id} | status: {status}")
    lines.append("")

    lines.append("EVIDENCE")
    evidence_groups = {
        "architecture": [],
        "implementation": [],
        "ci": [],
        "qa": [],
        "safety": [],
    }
    for task in tasks:
        for ref in task.get("artifact_refs") or []:
            art_type = ref.get("artifact_type")
            if art_type == "architecture_result":
                evidence_groups["architecture"].append(ref)
            elif art_type == "implementation_artifact":
                evidence_groups["implementation"].append(ref)
            elif art_type == "ci_results":
                evidence_groups["ci"].append(ref)
            elif art_type == "qa_result":
                evidence_groups["qa"].append(ref)
            elif art_type == "safety_result":
                evidence_groups["safety"].append(ref)
    all_empty = all(not vals for vals in evidence_groups.values())
    if all_empty:
        lines.append("- NONE")
    else:
        for label, vals in evidence_groups.items():
            if not vals:
                continue
            lines.append(f"- {label}: {', '.join(str(v.get('artifact_type')) for v in vals)}")
    lines.append("")

    lines.append("QA / SAFETY")
    qa_value = "NONE"
    safety_value = "NONE"
    for task in tasks:
        for ref in task.get("artifact_refs") or []:
            art_type = ref.get("artifact_type")
            if art_type == "qa_result":
                qa_value = ref.get("artifact_type", "qa_result")
            if art_type == "safety_result":
                safety_value = ref.get("artifact_type", "safety_result")
    lines.append(f"- QA: {qa_value}")
    lines.append(f"- Safety: {safety_value}")
    lines.append("")

    lines.append("BLOCKERS / ESCALATIONS")
    blockers = []
    for task in tasks:
        blockers.extend(task.get("blockers") or [])
    if not blockers:
        lines.append("- NONE")
    else:
        for item in blockers:
            lines.append(f"- {item}")
    lines.append("")

    lines.append("HUMAN APPROVAL")
    required = any(task.get("requires_human_approval") for task in tasks)
    lines.append(f"- required: {'YES' if required else 'NO'}")
    lines.append(f"- state: {'PENDING' if required else 'NOT_REQUIRED'}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_reports(report: dict, report_dir: Path) -> tuple[Path, Path, Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")

    latest_json = report_dir / "operator_report_latest.json"
    latest_md = report_dir / "operator_report_latest.md"
    stamped_json = report_dir / f"operator_report_{ts}.json"
    stamped_md = report_dir / f"operator_report_{ts}.md"

    payload = json.dumps(report, indent=2)
    markdown = render_markdown(report)

    latest_json.write_text(payload, encoding="utf-8")
    latest_md.write_text(markdown, encoding="utf-8")
    stamped_json.write_text(payload, encoding="utf-8")
    stamped_md.write_text(markdown, encoding="utf-8")

    return latest_json, latest_md, stamped_json, stamped_md


def print_summary(report: dict, latest_json: Path, latest_md: Path, stamped_json: Path, stamped_md: Path) -> None:
    print("=== Operator Consolidated Report ===")
    print(f"Status: {report['operator_status']}")
    print(f"Input: {report['input_file']}")
    print(f"Generated at: {report['generated_at_utc']}")
    print("Report files:")
    print(f"- latest json: {latest_json}")
    print(f"- latest md:   {latest_md}")
    print(f"- stamped json:{stamped_json}")
    print(f"- stamped md:  {stamped_md}")

    s10 = report.get("stage10", {})
    alerts = s10.get("alerts", [])
    print(f"Alerts: {len(alerts)}")
    for alert in alerts:
        print(f"- [{alert.get('severity')}] {alert.get('code')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 8/9/10 checks and write one consolidated operator report.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to normalized events CSV")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Directory for report output")
    parser.add_argument("--stale-tick-ms-max", type=float, default=5000.0)
    parser.add_argument("--min-candidate-ratio", type=float, default=0.05)
    parser.add_argument("--min-approval-ratio", type=float, default=0.05)
    parser.add_argument("--max-execution-skip-ratio", type=float, default=0.50)
    parser.add_argument("--max-no-candidate-streak", type=int, default=200)
    parser.add_argument("--snapshot", action="store_true", help="Render the authoritative orchestrator snapshot as a local read-only Control Room summary.")
    args = parser.parse_args()

    if args.snapshot:
        orch = Orchestrator()
        snapshot = orch.build_operator_snapshot()
        print(render_snapshot_text(snapshot))
        return

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    report = build_report(
        input_path=input_path,
        stale_tick_ms_max=args.stale_tick_ms_max,
        min_candidate_ratio=args.min_candidate_ratio,
        min_approval_ratio=args.min_approval_ratio,
        max_execution_skip_ratio=args.max_execution_skip_ratio,
        max_no_candidate_streak=args.max_no_candidate_streak,
    )

    latest_json, latest_md, stamped_json, stamped_md = write_reports(report, Path(args.report_dir))
    print_summary(report, latest_json, latest_md, stamped_json, stamped_md)


if __name__ == "__main__":
    main()