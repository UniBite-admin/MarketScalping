# Stage 10 Milestone: Monitoring / Alerting

## What are we doing?

We are adding a health monitoring and alerting layer that evaluates normalized pipeline events and flags degraded operating conditions.

## Why are we doing it?

- We now have normalized and queryable pipeline data.
- The system needs objective health checks before any live progression.
- Monitoring allows fast detection of feed quality and decision-flow issues.

## What was built?

- Health monitor tool:
  - [tools/monitor_pipeline_health.py](tools/monitor_pipeline_health.py)
- Input dataset:
  - [data/normalized_events.csv](data/normalized_events.csv)

## Alert checks (threshold-based)

- Stale feed spike: max `feature.tick_interval_ms` above threshold.
- Candidate drought: `strategy CANDIDATE_TRADE / strategy total` below threshold.
- Approval ratio drop: `risk APPROVED_SIMULATION / strategy CANDIDATE_TRADE` below threshold.
- Execution skip spike: `execution SKIPPED / (SIMULATED_ORDER_PREPARED + SKIPPED)` above threshold.
- No-candidate streak: longest consecutive strategy `NO_TRADE` run above threshold.

## How to run

```powershell
.\.venv\Scripts\python.exe .\tools\monitor_pipeline_health.py
```

Custom thresholds:

```powershell
.\.venv\Scripts\python.exe .\tools\monitor_pipeline_health.py `
  --stale-tick-ms-max 5000 `
  --min-candidate-ratio 0.05 `
  --min-approval-ratio 0.05 `
  --max-execution-skip-ratio 0.50 `
  --max-no-candidate-streak 200
```

JSON output:

```powershell
.\.venv\Scripts\python.exe .\tools\monitor_pipeline_health.py --json
```

## Success criteria

Pass if all are true:

1. Monitor script runs without runtime errors.
2. Health summary includes market/strategy/risk/execution sections.
3. Alert list is produced deterministically from thresholds.
4. Threshold overrides are accepted from CLI.
5. Output is usable in both human-readable and JSON forms.