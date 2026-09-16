# STEP 10.1 — Real-Time Market Data and Execution Simulation Contract

## Status

Architecture evidence for Step 10.1.

This contract is design-only and does not implement runtime production behavior. It captures the repository-grounded architecture required for the Step 10.1 paper-trading gate and preserves the authority model already established in the repo.

## 1. Purpose

This document defines the required architecture for Step 10.1 only:

- real-time market-data ingestion in a paper-trading environment
- deterministic execution simulation under operational failure conditions
- stale-data and churn handling
- restart/recovery behavior
- duplicate and corrupted event handling
- accounting/reconciliation integrity under failure and restart scenarios
- explicit evidence that paper trading remains simulation-only

This contract is limited to Step 10.1 and does not claim completion of Step 10.2 or Step 11.

## 2. Scope

This contract covers only Step 10.1:

- Step 10.1 — Real-Time Market Data and Execution Simulation

This contract explicitly does not establish completion for:

- Step 10.2 — Paper-vs-Backtest Comparison
- Step 11 — ML / AI Decision Layer
- live trading
- real order placement
- withdrawal capability
- leverage or margin activation
- credentialed exchange access
- any pathway that upgrades paper trading to live execution authority

The roadmap dependency remains:

- 9 → 10.1 → 10.2

## 3. Roadmap alignment

The authoritative roadmap definition for Step 10.1 is:

“Use real-time market data and deterministic execution assumptions in a paper environment with realistic latency, stale-data detection, restart handling, failure recovery, and event integrity guarantees.”

The required evidence list from the roadmap is:

- live market data feed
- execution simulation
- stale-data and churn handling
- WebSocket disconnect test evidence
- API failure handling evidence
- process-restart evidence
- accounting recovery evidence
- duplicate-event handling evidence
- corrupted-state handling evidence
- state-divergence detection evidence

The exit criteria from the roadmap are:

- Market data and execution remain deterministic under failure conditions
- WebSocket disconnects, stale data, and API failures are detected and handled without silent divergence
- Process restart and accounting recovery are tested and the system does not silently continue with corrupted state
- Duplicate or corrupted events are detected and reconciled
- State divergence is observable and blocks unsafe continuation
- Account reconciliation remains intact under operational risk conditions

## 4. Authority boundaries and simulation-only semantics

The repository’s existing authority model remains binding and is not altered by this contract.

- ExecutionEngine = execution intake and execution journal
- AccountingEngine = authoritative financial ledger
- PositionManager = derived position projection
- RiskEngine = pre-commit risk gate
- replay_runner.py = canonical historical replay boundary
- Step 10.1 paper trading = simulation-only operating layer, not a financial authority

Normative rules:

1. Step 10.1 must never create a second financial source of truth.
2. Real-time paper-trading execution must remain a simulation layer that records operational evidence, not live-money accounting authority.
3. RiskEngine remains a pre-commit gate and does not become a live-activation authority.
4. AccountingEngine remains the only authoritative ledger and must fail closed when recovery or reconciliation fails.
5. No live order placement, exchange credentials, auto-liveness path, or withdrawal permission may be introduced.
6. Any restart, reconnect, or failure path must preserve deterministic behavior and prevent silent divergence.
7. Paper trading may use real-time market data for observation and simulation, but it must not cross into live execution authority.

## 5. Repository-grounded architecture

### 5.1 Existing components to preserve

The current repo already contains the core architecture required to support Step 10.1 without redesigning the financial model.

- [market_data_engine.py](../market_data_engine.py)
  - real-time market-data ingestion and WebSocket lifecycle
  - stale-data monitoring
  - recovery startup gating
  - operational status tracking
- [execution_engine.py](../execution_engine.py)
  - execution intake and simulated order-preparation semantics
  - deterministic execution_event_id generation
  - dry-run / simulation-only execution behavior
- [accounting_engine.py](../accounting_engine.py)
  - authoritative ledger and startup recovery checks
  - checkpoint validation and fail-closed recovery logic
  - reconciliation and state restoration logic
- [position_manager.py](../position_manager.py)
  - derived position projection rebuilt from accounting state
- [risk_engine.py](../risk_engine.py)
  - pre-commit gate and no-live-path enforcement
- [execution_journal_reconciler.py](../execution_journal_reconciler.py)
  - execution journal reconciliation and divergence detection
- [replay_runner.py](../replay_runner.py)
  - canonical historical replay boundary and deterministic ordering semantics

### 5.2 Minimum architecture needed for Step 10.1

Step 10.1 is not a redesign of the trading system; it is a paper-trading operational envelope layered on top of the existing deterministic architecture.

The minimum architecture is:

1. Real-time market-data ingress
   - observed live market data is accepted only as a feed layer
   - feed freshness is monitored continuously
   - stale data is flagged and blocked from driving operational decisions when it crosses the configured freshness threshold

2. Simulation-only execution layer
   - execution assumptions remain deterministic and modeled, not live
   - execution decisions are recorded as simulated operation evidence
   - execution_output remains a journal of modeled events, not a live order confirmation system

3. Recovery and reconciliation gate
   - startup recovery must validate accounting, execution journal, and position projection consistency
   - if divergence is detected, the system must fail closed and block further market processing

4. Event integrity controls
   - duplicate event IDs must be recognized and rejected or reconciled
   - malformed or corrupted payloads must be rejected without altering accounting state
   - state divergence must produce an explicit signal and prevent unsafe continuation

5. Operational paper-trading evidence bundle
   - each failure mode must produce reproducible evidence for reconnect, stale-data, API issues, restart, accounting recovery, and state divergence
   - evidence is recorded as a read-only paper-trading artifact and not as a financial authority

## 6. Required behavior for failure and recovery cases

### 6.1 Stale market data

A stale market-data condition must:

- detect when the last market update exceeds the configured freshness threshold
- mark the feed as stale
- block strategy execution or forward event processing from stale data unless the system explicitly classifies the condition as a safe paper-trading hold state
- record the condition in the operational evidence artifact
- avoid silent continuation when stale data could mask bad execution assumptions

### 6.2 WebSocket disconnect

A WebSocket disconnect must:

- transition the connection state to a disconnected or degraded state
- stop relying on the stale socket feed
- attempt reconnect only within the configured retry policy
- mark the failure in the evidence trail
- prevent automatic activation of live execution logic

### 6.3 WebSocket reconnect

Reconnect behavior must:

- restore ordering and freshness checks after reestablishing a valid stream
- validate that the stream is consistent with the last known state before resuming feed-driven decisions
- reject reconnects that cannot prove continuity or state validity
- log the reconnect and any resumed state boundary

### 6.4 API failure

API failures must:

- fail closed for any operational action that depends on external API availability
- differentiate between feed interruption, API content failure, and invalid payloads
- retain the last known valid state without silently increasing authority or accepting stale data
- maintain deterministic behavior under retry or re-subscribe conditions

### 6.5 Malformed or invalid market events

Malformed events must:

- be rejected without mutating financial state
- be logged with the specific validation failure reason
- prevent unsafe continuation when the event could affect signal processing or reconciliation

### 6.6 Duplicate events

Duplicate events must:

- be recognized by event identity or replay identity rules
- be discarded or reconciled without double-counting execution or accounting effects
- protect execution_event_id idempotency and prevent repeated application of a single operational decision

### 6.7 Corrupted checkpoint or state

Corrupted state must:

- trigger the fail-closed recovery path
- block startup or runtime continuation if accounting state cannot be validated
- force reconciliation or explicit recovery denial instead of silently continuing

### 6.8 Restart during paper trading

A restart must:

- reload the valid accounting state before market processing resumes
- re-run reconciliation checks across execution journal and derived state
- validate position projection rebuilds against accounting state
- block startup if divergence remains unresolved

### 6.9 Restart after an execution event

If a restart occurs after a simulated execution event:

- the execution journal and accounting state must reconcile before the system continues
- duplicate or partially applied execution events must be identified and blocked or reconciled
- no state may silently drift from the prior valid accounting baseline

### 6.10 Accounting and execution-journal divergence

Any divergence between accounting state and execution journal must:

- be observable and explicit
- block unsafe continuation
- record the blocking reason and evidence reference
- require reconciliation before further operational processing

### 6.11 Duplicate execution_event_id

Duplicate execution_event_id values must:

- be treated as idempotency violations or duplicate processing attempts
- not create an additional financial effect
- trigger explicit evidence that the event was dropped or reconciled

### 6.12 Partial or incomplete state

Partial state must:

- be treated as invalid unless it can be proven to reconcile with the authoritative accounting state
- fail closed rather than continue with incomplete financial context

### 6.13 Recovery failure

If recovery cannot be proven valid:

- the system must remain blocked
- the paper-trading layer must not resume normal market processing
- the failure must be documented as evidence instead of silently proceeding

## 7. No live path and no paper-to-live activation

Step 10.1 must clearly prove that paper trading remains simulation-only.

This means:

- no real-money order placement
- no real exchange order submission
- no live order execution path in the default runtime
- no live credentials or wallet access
- no automatic activation from paper mode to live mode
- no withdrawal capability
- no leverage or margin path
- no bypass of RiskEngine pre-commit gating
- no bypass of AccountingEngine authority
- no hidden path from simulated operations to live-money execution

This contract therefore requires explicit runtime and design evidence that paper trading is an operational rehearsal layer only.

## 8. Evidence artifacts and tests required

The repository must provide evidence that each roadmap requirement has been satisfied.

Expected evidence artifacts:

- live feed health artifact
- stale-data detection artifact
- WebSocket disconnect/reconnect artifact
- API failure event artifact
- restart/recovery artifact
- accounting reconciliation artifact
- duplicate-event handling artifact
- corrupted-state artifact
- state-divergence detection artifact
- paper-trading simulation-only proof artifact

Required test coverage:

- feed freshness and staleness handling
- WebSocket disconnect and reconnect handling
- invalid/malformed market data rejection
- API failure scenarios
- duplicate event rejection or reconciliation
- corrupted checkpoint detection and fail-closed recovery
- restart during active paper-trading state
- restart after execution event processing
- accounting/execution divergence blocking
- duplicated execution_event_id idempotency
- no live/order placement activation path

## 9. Design gate against the roadmap

Step 10.1 is structurally complete only when all of the following are true:

1. real-time market data is treated as an observed feed, not a live trading authority
2. execution remains deterministic and simulation-only
3. stale and malformed data are detected before they drive decisions
4. WebSocket, API, and restart failure modes are explicitly represented
5. accounting recovery and reconciliation are fail-closed
6. duplicate or corrupted events are detected and reconciled
7. divergence is observable and blocks unsafe continuation
8. the system proves it remains paper trading only
9. the design remains limited to Step 10.1 and does not imply Step 10.2 or Step 11 completion

## 10. Binding rule set

The following rules are binding for Step 10.1:

1. Step 10.1 is simulation-only and cannot create live-money authority.
2. AccountingEngine stays authoritative.
3. PositionManager remains derived.
4. RiskEngine remains a pre-commit gate.
5. ExecutionEngine remains a journal for simulated and intake events only.
6. Feed freshness, reconnect, and failure proofs are required before operational approval.
7. Duplicate, stale, malformed, or corrupted events must never be silently accepted.
8. Restart and reconciliation failure must block the system.
9. Silent divergence is not permitted.
10. This contract covers Step 10.1 only and does not imply readiness for Step 10.2 or later stages.
