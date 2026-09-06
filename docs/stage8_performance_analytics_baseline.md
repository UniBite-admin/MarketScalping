# Stage 8 Milestone: Performance Analytics Baseline

## What are we doing?

We are generating a baseline analytics report over the normalized simulation event stream to measure throughput, decision funnel behavior, risk gating outcomes, and position lifecycle health.

## Why are we doing it?

- Stage 7 unified all events into one schema.
- We now need objective performance-style metrics before advancing to storage/query or execution upgrades.
- This creates a repeatable acceptance checkpoint from one command.

## What was built?

- Analytics summary tool:
  - [tools/summarize_normalized_events.py](tools/summarize_normalized_events.py)

Primary input:

- [data/normalized_events.csv](data/normalized_events.csv)

## Metrics covered

- Total rows and per-layer counts.
- Timespan and events-per-minute throughput.
- Strategy action distribution (`NO_TRADE` vs `CANDIDATE_TRADE`).
- Risk action distribution and top block/decision reasons.
- Execution action distribution (`SIMULATED_ORDER_PREPARED`, `SKIPPED`, `NO_ACTION`).
- Position lifecycle counts (`OPENED`, `HOLD`, `CLOSED`) and current open positions.
- Funnel ratios:
  - candidate_to_approved_ratio
  - approved_to_execution_sim_ratio

## How to run

```powershell
.\.venv\Scripts\python.exe .\tools\summarize_normalized_events.py
```

Optional JSON output:

```powershell
.\.venv\Scripts\python.exe .\tools\summarize_normalized_events.py --json
```

## Success criteria

Pass if all are true:

1. Summary script runs without error.
2. All expected layers are present in counts.
3. Timestamps are parseable and ordered.
4. Strategy -> Risk -> Execution funnel metrics are produced.
5. Position activity is present (at least `OPENED`) and open position count is reasonable for single-position mode.