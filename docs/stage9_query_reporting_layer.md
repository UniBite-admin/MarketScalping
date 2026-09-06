# Stage 9 Milestone: Query / Reporting Layer

## What are we doing?

We are adding a lightweight query and reporting layer on top of the normalized event table to support quick analysis, debugging, and operator review.

## Why are we doing it?

- Normalized data is available from Stage 7.
- Baseline analytics exists from Stage 8.
- We now need targeted, repeatable drilldowns without manual CSV inspection.

## What was built?

- Query/report tool:
  - [tools/query_normalized_events.py](tools/query_normalized_events.py)
- Input dataset:
  - [data/normalized_events.csv](data/normalized_events.csv)

## Report modes

- `rollup`: rows by day, by layer, and top layer/action pairs.
- `reasons`: top risk reasons with counts.
- `funnel`: strategy -> risk -> execution conversion metrics.
- `positions`: per-position lifecycle timeline summary.

## How to run

```powershell
.\.venv\Scripts\python.exe .\tools\query_normalized_events.py --report rollup
.\.venv\Scripts\python.exe .\tools\query_normalized_events.py --report reasons --top 10
.\.venv\Scripts\python.exe .\tools\query_normalized_events.py --report funnel
.\.venv\Scripts\python.exe .\tools\query_normalized_events.py --report positions
```

Optional filters:

- `--day YYYY-MM-DD`
- `--layer feature|strategy|risk|execution|position`
- `--json`

## Success criteria

Pass if all are true:

1. Each report mode runs without runtime errors.
2. Rollup reflects non-zero rows and expected layers.
3. Reasons report returns risk reason counts when risk rows exist.
4. Funnel report returns conversion metrics.
5. Positions report returns lifecycle entities and open/closed status.