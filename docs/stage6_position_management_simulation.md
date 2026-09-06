# Stage 6 Milestone: Position Management (Simulation Ledger)

## What are we doing?

We are adding a position lifecycle ledger on top of dry-run execution events.

## Why are we doing it?

Before real execution, we need traceable position state transitions (open, hold, close) and clean observability.

## What was built?

- Position manager module:
  - [position_manager.py](position_manager.py)
- Pipeline integration:
  - [market_data_engine.py](market_data_engine.py)
- Position summary tool:
  - [tools/summarize_positions.py](tools/summarize_positions.py)

Output ledger:

- [data/positions_simulation_btc_eur.csv](data/positions_simulation_btc_eur.csv)

## Safety boundaries

- Simulation only
- No exchange orders
- No private API calls
- No capital at risk

## How to test

Run:

```powershell
.\.venv\Scripts\python.exe .\market_data.py
```

Then summarize:

```powershell
.\.venv\Scripts\python.exe .\tools\summarize_positions.py
```

## Success criteria

Pass if all are true:

1. Position ledger file is created automatically.
2. Ledger rows append during runtime.
3. Lifecycle actions are present (`OPENED`, `HOLD`, `CLOSED` where applicable).
4. Open position count remains controlled (at most one open in this baseline model).
5. Runtime remains stable.