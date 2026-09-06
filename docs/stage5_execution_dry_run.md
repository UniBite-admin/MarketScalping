# Stage 5 Milestone: Execution Engine (Dry-Run Only)

## What are we doing?

We are adding an execution-layer skeleton that consumes risk decisions and records what would happen, without placing real orders.

## Why are we doing it?

This validates pipeline wiring and observability before any real exchange order path exists.

## What was built?

- Risk summary tool:
  - [tools/summarize_risk_decisions.py](tools/summarize_risk_decisions.py)
- Dry-run execution module:
  - [execution_engine.py](execution_engine.py)
- Integrated pipeline in [market_data_engine.py](market_data_engine.py):
  - Feature -> Strategy -> Risk -> Execution (dry-run)

Outputs:

- [data/risk_decisions_btc_eur.csv](data/risk_decisions_btc_eur.csv)
- [data/execution_simulation_btc_eur.csv](data/execution_simulation_btc_eur.csv)

## Safety boundaries

- No private API usage
- No API keys required
- No order placement
- No withdrawals
- No leverage logic

## Run and test

Run:

```powershell
.\.venv\Scripts\python.exe .\market_data.py
```

Then inspect:

```powershell
Get-Content .\data\risk_decisions_btc_eur.csv -Tail 10
Get-Content .\data\execution_simulation_btc_eur.csv -Tail 10
.\.venv\Scripts\python.exe .\tools\summarize_risk_decisions.py
```

## Success criteria

Pass if all are true:

1. Risk and execution output files are created automatically.
2. Rows append during live runtime.
3. Execution actions are simulation-only (`SIMULATED_ORDER_PREPARED`, `SKIPPED`, `NO_ACTION`).
4. Reasons are explicit and traceable.
5. Runtime remains stable.