# Stage 3 Milestone: Strategy Engine Baseline (Simulation Only)

## 1) What are we doing?

We are adding a deterministic strategy baseline that consumes validated feature inputs and emits simulated decisions.

## 2) Why are we doing it?

This creates a testable decision layer before introducing risk management or execution.

## 3) What are we going to build?

- Decision outputs: `NO_TRADE` or `CANDIDATE_TRADE`
- Deterministic rule-based logic only
- No order placement
- No API keys
- No private endpoints

Decision output file:

- [data/strategy_decisions_btc_eur.csv](data/strategy_decisions_btc_eur.csv)

Core implementation:

- [strategy_engine.py](strategy_engine.py)
- Integrated into [market_data_engine.py](market_data_engine.py)

## 4) What do I need to do?

1. Run the market data app for 2 to 5 minutes.
2. Stop with Ctrl+C.
3. Inspect decision outputs in [data/strategy_decisions_btc_eur.csv](data/strategy_decisions_btc_eur.csv).

Run command:

```powershell
.\.venv\Scripts\python.exe .\market_data.py
```

## 5) How will we test it?

- Decision file is auto-created.
- New decision rows are appended during runtime.
- Both actions are possible in live flow (`NO_TRADE` and/or `CANDIDATE_TRADE`).
- Reasons are explicit and readable.
- Runtime remains stable and read-only.

## 6) How will we know it is successful?

Pass if:

1. Strategy receives valid in-memory input contract and produces deterministic decisions.
2. Decision rows include timestamp, market, action, reason, signal strength, and spread context.
3. No execution behavior exists.
4. No runtime crash introduced by strategy integration.

After this stage passes, next step is Risk Management Engine as final decision gate before any future execution layer.