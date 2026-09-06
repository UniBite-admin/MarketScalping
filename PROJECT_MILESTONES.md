# PROJECT_MILESTONES

## Purpose
This document is the authoritative handoff and state record for the MarketScalping project. Future development sessions should review this file before starting the next critical milestone.

## 1) Project Overview
MarketScalping is intended to become a professional, measurable, testable, and controlled automated crypto scalping system.

Capital constraints and rollout intent:
- Maximum capital allocated to the project: EUR 50
- First intended live experiment: approximately EUR 10
- Spot trading initially
- No leverage initially
- Capital preservation before growth
- No guaranteed-return assumptions

Core philosophy:

DATA -> TEST -> VALIDATE -> AUTOMATE -> CONTROL -> SCALE

## 2) Architectural Philosophy
The system is being built as a deterministic, safety-first pipeline with strict separation of concerns and validation gates between layers.

Target architecture:

MARKET DATA ENGINE
        ↓
FEATURE / SIGNAL ENGINE
        ↓
STRATEGY ENGINE
        ↓
AI / ML DECISION LAYER
        ↓
RISK MANAGEMENT ENGINE
        ↓
EXECUTION ENGINE
        ↓
POSITION MANAGEMENT
        ↓
DATABASE / LOGGING
        ↓
PERFORMANCE ANALYTICS
        ↓
MONITORING / ALERTING

AI/ML policy:
- The AI/ML layer is not intended to be an LLM queried every second.
- Real-time trading decisions should eventually be handled by deterministic code and/or low-latency ML models.
- LLM reasoning may later be used for:
  - strategy research
  - market-regime analysis
  - anomaly detection
  - parameter analysis
  - post-trade analysis
- No uncontrolled self-modification of live trading logic is allowed.

## 3) Completed Milestones

### Milestone 1 - Core pipeline safety and deterministic timestamps
Completed:
- deterministic event timestamp support
- historical timestamps propagate through Feature, Strategy, Risk, Execution and Position layers
- explicit historical timestamps override wall-clock time
- malformed/naive explicit historical timestamps are rejected safely
- no wall-clock fallback for invalid explicit historical timestamps
- canonical timestamp resolved once at orchestration boundary
- downstream components receive the same event timestamp

### Milestone 2 - Offline ReplayRunner
Completed:
- replay_runner.py
- deterministic offline replay
- JSONL/dict input
- chronological ordering
- stable ordering for equal timestamps
- validation of timestamps, market and prices
- isolated MarketDataEngine
- no live WebSocket during replay
- deterministic repeated replay tests

### Milestone 3 - Historical data audit
Completed:
- audited current market-data pipeline
- identified currently consumed ticker/trade fields
- confirmed current pipeline does not yet consume full trade-flow/order-book information
- identified existing CSV files as pipeline outputs rather than raw historical datasets
- established separation between raw historical data and normalized replay input

### Milestone 4 - Bitvavo historical trade collector
Completed:
- bitvavo_trade_collector.py
- documented market-specific endpoint support: /v2/{market}/trades

Canonical raw schema:
- trade_id
- event_time_utc
- market
- price
- amount
- side
- source

Implemented:
- timestamp conversion to UTC
- numeric validation
- side validation
- duplicate detection
- chronological sorting
- bounded historical window handling
- JSONL output
- official Bitvavo id field compatibility
- environment-based authentication
- request signing
- credentials are not persisted in raw output

### Milestone 5 - Collector test suite and authoritative full-suite validation
Authoritative project test command:

python -m unittest discover -s tests -p "test*.py" -v

Latest authoritative result:

Ran 106 tests in 1.763s
OK

Important:
- Pattern -p "test.py" is not the authoritative full-suite discovery pattern.
- Do not use any -p "test.py" run as authoritative project-wide validation.

### Milestone 6 - Real Bitvavo historical data acquisition
A real authenticated historical collection was successfully completed.

Market:
- BTC-EUR

Exact window:
- 2026-09-05T12:00:00Z -> 2026-09-05T12:10:00Z

Validated result:
- 71 real trade records
- first timestamp: 2026-09-05T12:00:03.494+00:00
- last timestamp: 2026-09-05T12:09:59.457+00:00
- chronological: True
- duplicate trade IDs: False
- required fields valid: True
- market valid: True
- prices valid: True
- amounts valid: True
- sides valid: True
- timestamps inside requested window: True
- credentials/authentication data present in output: False

Output location:
- Stored under the canonical raw directory pattern: data/raw/bitvavo_trades/
- No machine-specific absolute path is required for milestone tracking.

## 4) What Has Been Tested
Coverage currently includes:
- accounting baseline invariants and restart/idempotency behavior
- orchestration safety and deterministic timestamp propagation
- replay determinism and replay safety isolation
- collector validation, deduplication, sorting, and JSONL output behavior
- collector request-shape and auth-header behavior under env/no-env conditions

Relevant tests:
- tests/test_accounting_baseline.py
- tests/test_safety_and_accounting_audit.py
- tests/test_replay_runner.py
- tests/test_bitvavo_trade_collector.py

## 5) Real Data Validation Summary
Validated with real Bitvavo historical BTC-EUR trade data:
- authenticated retrieval works with the documented endpoint path
- bounded historical window retrieval works
- output integrity checks passed
- credential/auth marker leakage checks passed

No strategy profitability conclusions are derived from this step.

## 6) What Has NOT Been Implemented Yet
Not implemented / not validated yet:
- no validated profitable scalping strategy
- no AI/ML trading model
- no live automated trading
- no leverage
- no futures/perpetual trading
- no autonomous strategy optimization
- no production trading deployment

## 7) Current Project State
Current achievement:
- The system can safely acquire and validate real historical Bitvavo trade data.
- Deterministic replay/testing foundations are in place.

Current limitation:
- Project profitability is not proven.

## 8) Next Planned Milestones (Prioritized)

### Next milestone - Historical data to Replay adapter
Build adapter: Raw Bitvavo Trade JSONL -> ReplayRunner input format.

Requirements:
- preserve timestamps
- preserve price
- preserve amount
- preserve side
- preserve trade ID
- deterministic ordering
- no information leakage
- no live exchange connection

### Following milestone - Real-data replay validation
Replay real historical dataset through existing pipeline.

Verify:
- deterministic results
- correct timestamps
- no wall-clock leakage
- correct event ordering
- no accidental live WebSocket startup
- repeatability

### Later milestone - Larger historical dataset
After 10-minute dataset replay path is validated, expand gradually.

Investigate:
- trade flow
- short-term momentum
- volatility
- spread
- liquidity
- market regime

Rule:
- Do not add features merely because they are popular indicators.

### Later milestone - Strategy research
Only after sufficient historical data:
- define baseline strategy
- backtest
- include fees
- include spread
- include slippage
- include latency assumptions
- consider partial fills
- consider failed orders
- consider minimum order sizes

### Later milestone - Paper trading
Only after robust historical behavior is demonstrated.

### Later milestone - Small live test
Only after paper trading validation.

Live pilot constraints:
- initial live capital target: approximately EUR 10
- no leverage
- risk engine remains authoritative

## 9) Risk Principles
Prominent rule:

AI BUY signal != automatic trade

Risk management must be able to reject any candidate.

Eventually include:
- maximum position size
- maximum risk per trade
- stop loss
- take profit
- trailing logic
- maximum daily loss
- maximum consecutive losses
- maximum open positions
- emergency kill switch
- API failure protection
- abnormal market detection

## 10) Security and Credential Handling
- API keys must come from environment variables or secure secret storage.
- Never hardcode credentials.
- Withdrawal permission must remain disabled.
- Collector must remain read-only.
- Never log credentials.
- Never persist authentication headers/signatures.
- Never paste credentials into ChatGPT/Copilot conversations.
- Unit tests must use dummy credentials only.
- Live trading permissions must not be added until explicitly required.

## 11) Current Repository Components
Relevant modules:
- market_data_engine.py
- market_data.py
- feature_signal_engine.py
- strategy_engine.py
- risk_engine.py
- execution_engine.py
- position_manager.py
- accounting_engine.py
- replay_runner.py
- bitvavo_trade_collector.py

Relevant tests:
- tests/test_accounting_baseline.py
- tests/test_safety_and_accounting_audit.py
- tests/test_replay_runner.py
- tests/test_bitvavo_trade_collector.py

## 12) Authoritative Test Command
The authoritative project-wide command is:

python -m unittest discover -s tests -p "test*.py" -v

## 13) Development Rule
Do not jump directly to AI, optimization, or live trading.

Mandatory progression:

DATA
 ↓
VALIDATE
 ↓
REPLAY
 ↓
BACKTEST
 ↓
PAPER TRADE
 ↓
SMALL LIVE TEST
 ↓
VALIDATE
 ↓
CONTROLLED SCALE

A future development session must inspect PROJECT_MILESTONES.md before starting the next critical milestone.

## 14) Current Stopping Point
Development is intentionally paused after successful real historical data acquisition and integrity validation.

Next technical task:
Build the Raw Bitvavo Trade JSONL -> ReplayRunner adapter and validate deterministic replay using real historical data.

Do not implement that adapter in this milestone document step.
