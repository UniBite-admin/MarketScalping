# Stage 7 Milestone: Database / Logging Normalization

## What are we doing?

We are consolidating all simulation pipeline outputs into one normalized event table for analytics and future database loading.

## Why are we doing it?

- Current outputs are split across multiple CSV files.
- Analytics and monitoring become simpler with a unified schema.
- Future migration to PostgreSQL/Supabase needs consistent event contracts.

## What was built?

- Normalization tool:
  - [tools/normalize_pipeline_data.py](tools/normalize_pipeline_data.py)
- Unified output:
  - [data/normalized_events.csv](data/normalized_events.csv)

Sources consumed:

- [data/features_btc_eur.csv](data/features_btc_eur.csv)
- [data/strategy_decisions_btc_eur.csv](data/strategy_decisions_btc_eur.csv)
- [data/risk_decisions_btc_eur.csv](data/risk_decisions_btc_eur.csv)
- [data/execution_simulation_btc_eur.csv](data/execution_simulation_btc_eur.csv)
- [data/positions_simulation_btc_eur.csv](data/positions_simulation_btc_eur.csv)

## Normalized schema

Core fields in [data/normalized_events.csv](data/normalized_events.csv):

- event_time_utc
- layer
- event_type
- market
- entity_id
- status
- action
- reason
- signal_strength
- spread_pct
- tick_interval_ms
- valid_flag
- source_file
- source_row_number
- payload_json

## How to run

```powershell
.\.venv\Scripts\python.exe .\tools\normalize_pipeline_data.py
```

## Success criteria

Pass if all are true:

1. Normalized file is generated successfully.
2. Rows exist from each available layer source.
3. Timestamps are ordered.
4. Source lineage is preserved (`source_file`, `source_row_number`).
5. No runtime or parsing crash.