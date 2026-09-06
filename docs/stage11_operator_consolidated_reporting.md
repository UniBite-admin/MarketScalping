# Stage 11 Milestone: Operator Consolidated Reporting

## What are we doing?

We are adding one command that runs Stage 8 analytics, Stage 9 reporting snapshots, and Stage 10 health monitoring, then writes a consolidated operator report.

## Why are we doing it?

- Operators need a single repeatable command per capture window.
- Separate scripts are useful, but daily workflow benefits from one consolidated artifact.
- This improves review speed and auditability.

## What was built?

- One-shot orchestrator:
  - [tools/run_operator_report.py](tools/run_operator_report.py)
- Inputs:
  - [data/normalized_events.csv](data/normalized_events.csv)
- Outputs:
  - [reports/operator_report_latest.json](reports/operator_report_latest.json)
  - [reports/operator_report_latest.md](reports/operator_report_latest.md)
  - timestamped JSON and Markdown report files in [reports](reports)

## How to run

```powershell
.\.venv\Scripts\python.exe .\tools\run_operator_report.py
```

Optional threshold overrides (forwarded to Stage 10 logic):

```powershell
.\.venv\Scripts\python.exe .\tools\run_operator_report.py `
  --stale-tick-ms-max 15000 `
  --min-candidate-ratio 0.10 `
  --min-approval-ratio 0.05 `
  --max-execution-skip-ratio 0.30 `
  --max-no-candidate-streak 50
```

## Success criteria

Pass if all are true:

1. One-shot command runs without runtime errors.
2. JSON and Markdown reports are both generated.
3. Report includes Stage 8, Stage 9, and Stage 10 sections.
4. Operator status reflects Stage 10 health status.
5. Timestamped historical artifacts are written for audit trail.