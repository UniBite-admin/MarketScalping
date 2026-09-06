# Stage 1 Acceptance: Market Data Engine

This document defines how to validate the current BTC-EUR market data milestone before moving to the Feature / Signal Engine.

## 1) What are we doing?

We are validating that the Market Data Engine is operationally reliable for public Bitvavo spot data.

## 2) Why are we doing it?

All downstream layers depend on clean, timely market data. If this layer is unstable, any strategy or ML logic is untrustworthy.

## 3) What are we going to build in this step?

No new trading logic. We build evidence and acceptance proof using:

- live runtime checks
- log-based metrics from [logs/market_data.log](logs/market_data.log)
- objective pass/fail criteria

## 4) What do you need to do?

1. Start a fresh terminal in the project root.
2. Run the engine for a fixed observation window (recommended: 10 minutes).
3. Stop it with Ctrl+C.
4. Run the evidence summarizer.
5. Compare results against acceptance criteria below.

Run commands:

```powershell
.\.venv\Scripts\python.exe .\market_data.py
```

After stopping:

```powershell
.\.venv\Scripts\python.exe .\tools\summarize_market_data_log.py
```

Optional JSON output:

```powershell
.\.venv\Scripts\python.exe .\tools\summarize_market_data_log.py --json
```

## 5) How will we test it?

Functional checks while running:

- Dashboard renders one active table (no unreadable overlap).
- Bid updates over time.
- Ask updates over time.
- Last updates over time.
- Spread, spread %, and mid price are shown when bid/ask are available.
- Ctrl+C stops cleanly.

Operational checks from logs:

- Successful connection lifecycle appears:
  - `state=connecting`
  - `state=connected`
  - `state=subscription_sent`
  - `subscription_confirmed`
- No persistent failure loops.
- Reconnect behavior is visible and bounded if disconnections happen.
- Stale-data warnings are visible when feed pauses and clear when data resumes.

## 6) Success criteria (Pass/Fail)

Pass this stage if all are true:

1. At least one successful subscription confirmation exists.
2. At least one ticker/trade data period reaches `state=receiving_ticker` without immediate fatal stop.
3. Stale-data detections, if any, are followed by `data_fresh_again` in normal conditions.
4. If disconnections occur, reconnect attempts are logged and at least one reconnect succeeds.
5. No malformed JSON or parse-error storms during normal operation.

Fail this stage if any are true:

1. Repeated subscribe failures or no `subscription_confirmed`.
2. Constant stale state with no recovery.
3. Continuous disconnect loop with no stable receiving period.
4. Dashboard fields stay missing for extended windows despite active connection.

## Evidence record template

Use this template in your notes:

```text
Run date:
Observation duration:
Subscription confirmed count:
Disconnect count:
Reconnect attempts:
Stale detections:
Fresh-again events:
Socket errors:
Decision: PASS / FAIL
Comments:
```

## Gate to proceed

Proceed to Feature / Signal Engine only after explicit sign-off:

`I have done it.`
