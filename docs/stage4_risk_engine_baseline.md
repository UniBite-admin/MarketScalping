# Stage 4 Milestone: Risk Management Engine Baseline (Simulation Only)

## 1) What are we doing?

We are adding a risk gate after strategy decisions.

Flow now:

Market Data -> Feature Engine -> Strategy Engine -> Risk Engine

## 2) Why are we doing it?

Strategy output is not enough to act safely.
Risk must be final authority before any future execution layer.

## 3) What are we going to build?

- Risk decision outputs only (no orders)
- Decisions include:
  - `APPROVED_SIMULATION`
  - `BLOCKED`
  - `NO_ACTION`
- Clear reasons for every decision

Output file:

- [data/risk_decisions_btc_eur.csv](data/risk_decisions_btc_eur.csv)

Core implementation:

- [risk_engine.py](risk_engine.py)
- Integrated in [market_data_engine.py](market_data_engine.py)

## 4) What do I need to do?

1. Run the app for 2 to 5 minutes.
2. Stop with Ctrl+C.
3. Check [data/risk_decisions_btc_eur.csv](data/risk_decisions_btc_eur.csv).

Run command:

```powershell
.\.venv\Scripts\python.exe .\market_data.py
```

## 5) How will we test it?

- Risk output file is auto-created.
- Rows append during runtime.
- `strategy_action` appears in each row.
- `risk_action` and `reason` are explicit.
- Runtime remains read-only and stable.

## 6) How will we know it is successful?

Pass if all are true:

1. Risk decisions are emitted for strategy decisions.
2. CANDIDATE strategy decisions are either approved or blocked by risk logic.
3. No execution behavior exists.
4. No runtime crash introduced.

Key safety reminder:

- This is still simulation only.
- No private API usage.
- No order placement.