# STEP 7.4 — Replay Determinism & Realism Contract

## Status

ARCHITECTURE FINALIZED FOR IMPLEMENTATION.

This contract defines the repository-grounded architecture for deterministic historical replay and explicitly freezes the historical realism boundary. It is design-only and does not change runtime behavior, tests, or roadmap state.

## 1. Purpose

This contract defines how the repository must replay canonical historical datasets deterministically while preserving historical honesty. The purpose is to answer one question clearly:

- Can the same canonical dataset and same replay configuration reproduce the same system behavior on repeated execution without depending on mutable runtime state, wall-clock time, or hidden external conditions?

The answer for this repository is: yes, but only if the replay path is strictly deterministic and only if the system does not overclaim realism beyond trade-only evidence.

This contract therefore defines:

- the canonical replay input contract
- the deterministic event ordering rule
- timestamp semantics
- no-look-ahead rules
- state isolation requirements
- minimal replay configuration
- evidence requirements for reproducibility
- failure semantics
- the boundary between what trade-only historical data can support and what it cannot support reliably

## 2. Scope

This contract applies to the replay path:

- canonical historical dataset
- validated replay input
- deterministic event replay
- MarketDataEngine ingestion
- feature and signal generation
- strategy decision generation
- risk gating
- execution simulation
- accounting and position state

This contract does not apply to:

- live trading
- live exchange connectivity
- live credentials
- withdrawals
- leverage or futures
- production deployment
- ML optimization or strategy search
- STEP 8 backtesting implementation
- STEP 9 strategy validation
- STEP 10 paper trading

This contract is purposely limited to historical replay determinism and realism boundaries.

## 3. Historical replay vs live/default runtime boundary

This contract defines a strict execution boundary between two different operational modes.

### 3.1 Historical replay mode

Historical replay is an explicit deterministic execution context whose inputs are already validated canonical replay events. In this mode:

- the event timestamp is historical event time supplied by the replay dataset
- replay MUST fail closed if the event time is missing, malformed, or naive
- replay MUST NOT substitute current wall-clock time
- replay MUST NOT depend on local timezone or machine state
- replay MUST NOT rely on implicit engine defaults for timestamp creation

The authoritative enforcement point for this mode is the replay boundary itself, before the dataset is handed to the production pipeline. The replay runner is responsible for validating and normalizing each event timestamp and for rejecting invalid or incomplete historical input.

### 3.2 Live/default runtime mode

Live/default runtime behavior remains the repository’s existing operational behavior outside historical replay. In this mode:

- missing timestamps may still be tolerated when the runtime is operating in live, non-historical mode
- engine-level fallback behavior may still be used for operational continuity when no historical timestamp is supplied
- the production runtime may still use current-time semantics for live monitoring and operational state

This mode remains valid and must not be globally disabled by historical replay requirements.

### 3.3 Architectural rule

The replay fix MUST be applied at the replay boundary, not by globally changing every engine in the production stack.

Normative rule:

- historical replay data must be timestamp-valid before it is passed into the engine pipeline
- live/default runtime behavior must remain unchanged unless a specific architecture decision requires otherwise
- the engine pipeline may retain its existing `event_time_utc or now` semantics for live/default use, but replay must never reach those defaults with missing or invalid timestamps

This is the core boundary that prevents the regression seen when the developer removed timestamp fallbacks across the shared runtime stack.

## 4. Authority

The authority model remains unchanged and is authoritative for this repository:

- ExecutionEngine: immutable execution journal / intake authority
- AccountingEngine: authoritative financial ledger
- PositionManager: derived position projection
- RiskEngine: final pre-commit risk gate

Historical replay remains non-authoritative.

Normative rule:

- replay output is a deterministic simulation record, not a financial source of truth
- replay must never become an alternate financial ledger
- no replay path may infer live trading authority or let historical simulation mutate the authoritative financial ledger

## 4. Replay input requirements

The replay system MUST accept only a canonical historical dataset that satisfies the following requirements:

1. It is already validated as a complete, acceptable dataset for replay.
2. It is a canonicalized normalized stream, not raw exchange evidence.
3. It contains only runtime-relevant fields for deterministic replay processing.
4. It has a single, explicit schema/contract version.
5. It must be stable across repeated runs for the same dataset and configuration.

The repository contract requires the canonical stream to use the runtime-relevant minimal event shape that is already established in Step 7.3:

- event_time_utc
- event_type
- market
- bid
- ask
- last

The canonical replay stream intentionally does not carry raw exchange identity fields such as trade_id, amount, or side because those fields are raw historical evidence, not replay state. Those raw fields are preserved for auditability in the raw and validated layers but are not the authoritative stream for replay.

A replay dataset is valid only if:

- every event is structurally valid
- every timestamp is valid UTC-aware
- every required numeric field is finite and positive
- every event type is supported
- the dataset is complete for the configured replay window
- duplicates and invalid records are already resolved or rejected before replay begins

## 5. Deterministic ordering

The authoritative replay ordering rule is:

- sort by (event_time_dt, original_index)

This is the repository-defined deterministic rule established in Step 7.3 and remains the canonical ordering rule for Step 7.4.

### 5.1 Meaning of original_index

`original_index` MUST mean:

- the original zero-based position of the canonical event in the canonical replay dataset after validation and normalization
- a stable deterministic tie-breaker used only when multiple events share the same UTC timestamp
- a replay-local ordering token, not an exchange sequence number
- a value that is preserved only within the canonical dataset and replay execution context

`original_index` MUST NOT be interpreted as:

- exchange event sequence number
- execution sequence number
- real exchange trading priority
- a claim of actual market order fill ordering

The lifetime of `original_index` is:

- created during canonicalization
- retained for deterministic ordering while replay is configured
- not exported as authoritative exchange identity
- not reused across different canonical datasets unless the dataset and ordering are exactly the same

### 5.2 Edge cases

Identical timestamps:
- events with the same event_time_dt are ordered by original_index
- this makes ordering deterministic and stable across identical canonical inputs

Multiple trades at the same timestamp:
- they are processed in a deterministic tie-break order based on original_index
- no hidden ordering from Python iteration or filesystem state is allowed

Out-of-order source records:
- replay ordering must ignore source fetch order and operate only on event_time_dt and original_index
- the canonical dataset itself is the source-of-truth ordering

Duplicate events:
- duplicate canonical records must be rejected before processing
- duplicates are not silently merged or resequenced

Timestamp precision:
- timestamps must be normalized to UTC and compared at a deterministic precision that preserves historical order
- no implicit truncation or local-time adjustment is allowed

Timezone normalization:
- all timestamps are converted to UTC
- naive timestamps are rejected
- local timezone drift cannot affect replay ordering

Stable ordering across runs:
- repeated runs over the same canonical dataset and configuration must produce identical event order

## 6. Timestamp semantics

Timestamp semantics are a critical determinism requirement.

### 6.1 Required behavior

- event_time is the historical event time
- processing_time is never substituted for event_time
- naive timestamps are rejected
- timestamps are normalized to UTC
- invalid timestamps fail closed
- no `datetime.now()`, wall-clock fallback, or local-time conversion may influence replay order or resampling

### 6.2 Repository rule

The replay path MUST accept timestamps only when they are:

- parseable as timezone-aware ISO timestamps
- normalized to UTC without ambiguity
- valid in the dataset window
- not missing

If a timestamp is malformed or naive, replay MUST reject the event and terminate or fail as configured; it MUST NOT continue with an implicit fallback.

### 6.3 Required timestamp plumbing

Every place in the replay path where timestamps are created or consumed must be explicit:

- raw collector parse and validation
- canonical normalization
- replay event ordering
- feature windowing and signal generation
- strategy event timestamps
- risk decision timestamps
- execution timestamps
- accounting timestamps
- position timestamps

There must be no hidden wall-clock fallback anywhere in this chain.

## 7. Market-state reconstruction

Historical trade-only data does not provide a full market state. The replay system must reconstruct only what can be justified from the available evidence.

### 7.1 Known facts

From a trade event, the replay can know:

- event time
- market identifier
- trade execution price (`last`)
- that a trade occurred

### 7.2 Reconstructed values

When quote-side values are unavailable, the repo contract allows a compatibility rule from Step 7.1 and Step 7.3:

- trade `last` is the observed execution price
- synthetic `bid` and `ask` values may be set to `last` to keep downstream processing compatible

This is not a real quote. It is a compatibility placeholder required by the runtime pipeline.

### 7.3 Synthetic interpretation rule

Synthetic bid/ask values MUST be clearly understood as:

- reconstructed compatibility values
- not observed historical quotes
- not order-book state
- not bid/ask spread evidence
- not exchange-provided market depth

The replay system must never imply that synthetic bid/ask equal to last is historical quote evidence. It is only a compatibility invariant required for downstream simulation code paths.

### 7.4 Not knowable from trade-only history

The following cannot be recovered reliably from trade-only historical data:

- real bid/ask spread
- order-book state
- queue position
- liquidity depth
- trade direction from order-book perspective
- actual slippage mechanism
- latency
- partial fill behavior
- hidden exchange matching engine state
- true queue priority

These are out of scope for this replay architecture and MUST be treated as unavailable unless later backtesting infrastructure adds explicit assumptions.

## 8. No-look-ahead

A historical event may only influence:

- its own processing
- subsequent state

It must never influence earlier events.

This requirement applies to all replay stages:

- event sorting
- feature calculation
- rolling windows
- moving averages
- momentum
- volatility
- signal generation
- strategy state
- risk state
- execution simulation
- accounting/position state

### 8.1 Rules

- sorting MUST be chronological and stable
- features must be computed only from data available up to the event time
- rolling windows MUST not include future events
- strategy decisions MUST not reference post-event data
- risk decisions MUST use state available at the time of evaluation
- execution simulation MUST use state as of the current event only

Any future-data leakage is a determinism and realism violation and must be rejected by design.

## 9. Replay state isolation

A replay run must start from a known clean state and must not be affected by any prior replay run.

### 9.1 Required isolation guarantees

- previous replay state cannot leak into a new run
- accounting state resets correctly
- position state resets correctly
- strategy state resets correctly
- feature state resets correctly
- execution simulation state resets correctly

### 9.2 Required approach

Each replay run MUST start from a fresh in-memory or newly initialized state object, and all engine configuration must be explicit and reproducible.

The replay system MUST NOT rely on:

- global mutable engine state
- singleton caches that persist between runs
- process-local temporary state
- machine-local runtime context
- hidden filesystem state

A replay MUST be reproducible regardless of how many previous replays have already run.

## 10. Replay configuration

The minimal replay configuration required for reproducibility is:

- dataset identity
- schema/contract version
- market
- start and end event time
- initial capital or balance
- strategy configuration
- risk configuration
- execution simulation configuration
- deterministic ordering configuration

This is the minimum set. Additional configuration is allowed only if it directly affects replay behavior and is included in the replay evidence metadata.

The replay configuration MUST be treated as input identity. If the configuration changes, the resulting replay identity changes even if the dataset is identical.

## 11. Replay evidence

To prove a replay is reproducible, the system must record enough evidence to prove the dataset and replay configuration were the same across runs.

### 11.1 Minimum evidence requirements

At minimum, the replay evidence should include:

- dataset identity
- dataset checksum or stable hash if available
- contract/schema version
- event count
- first and last event time
- replay status
- final accounting state
- final position state
- execution-event count
- strategy-decision count
- risk-decision count
- deterministic replay identity result
- configuration identity

This is sufficient to prove identical replay inputs and outputs without introducing unnecessary infrastructure.

### 11.2 Proof semantics

A replay result is considered reproducible only when the same deterministic inputs produce the same deterministic outputs across repeated runs.

The evidence must capture:

- same dataset identity
- same configuration identity
- same ordering rule
- same final state summary
- same decision counts

## 12. Failure semantics

Replay must fail closed.

A replay MUST fail when any of the following occurs:

- invalid canonical dataset
- incomplete dataset
- timestamp inconsistency
- duplicate canonical records
- unsupported event type
- malformed event
- market-state reconstruction failure
- engine exception
- accounting divergence
- position divergence

### 12.1 Failure rule

The system MUST NOT silently continue after a condition that can alter reproducibility or make the replay output ambiguous.

The failure behavior MUST be explicit and must prevent partial acceptance of a replay that is not equivalent to a deterministic, valid replay run.

## 13. Historical realism boundary

The replay system must be historically honest about what trade-only data supports and what it cannot support reliably.

### 13.1 What trade-only data can support

- event time
- trade execution price
- market identity
- occurrence of a trade
- basic sequential chronology for the dataset
- deterministic replay of a market-state approximation capable of reusing the production pipeline

### 13.2 What it cannot support reliably

- bid/ask spread as observed real market quote spread
- order-book depth or queue shape
- trade direction beyond the trade record itself
- true liquidity conditions
- slippage under realistic market microstructure
- queue position or exchange latency
- partial fills and matching engine scheduling
- actual fee schedule beyond a configured approximation

This contract explicitly forbids overclaiming realism. Trade-only replay is an evidence-based simulation of a constrained market-state model, not a reconstructed full exchange microstructure model.

## 14. Financial-state boundaries

The existing repo authority remains the governing rule.

- ExecutionEngine is the authoritative intake and journaling layer for execution events.
- AccountingEngine is the authoritative ledger for financial state.
- PositionManager derives position projections from execution/accounting state.
- RiskEngine is the final pre-commit gate.

Historical replay is non-authoritative and must never be treated as a source of financial truth. This includes:

- ledger creation
- execution-identity claims
- position authority
- risk authority

The domain boundary is explicit: historical replay simulates system behavior; the financial ledger remains governed by execution and accounting authority.

## 15. QA acceptance matrix

The architecture is accepted by QA only when all of the following are true:

- deterministic ordering is stable for repeated runs
- event order is identical across repeated executions for the same inputs
- timestamps are UTC-normalized and non-naive
- invalid timestamps fail closed
- synthetic bid/ask placeholders are clearly marked as non-observed values
- no wall-clock time or machine-local time influences replay behavior
- no prior replay state leaks into subsequent runs
- replay cannot proceed with incomplete or invalid canonical input
- final accounting and position summaries are consistent and reproducible

A replay is rejected by QA if any of the following are true:

- ordering depends on unordered container iteration
- hidden state leaks across runs
- timestamps are replaced with processing time
- future data is used in feature generation
- canonical data is allowed to proceed without strict validation
- synthetic quote values are treated as real historical quotes

## 16. Safety guardrails

This replay architecture is intentionally narrow and safe.

Safety guardrails include:

- no live trading logic
- no live credentials or withdrawal capability
- no leverage or futures exposure
- no default production activation
- no historical replay path that overrides risk authority
- no financial ledger mutation from replay data
- no inference of real market depth or quote quality beyond trade-only evidence
- no silent continuation after invalid or inconsistent replay conditions

The system must remain conservative: if realism or determinism are uncertain, the replay must fail rather than continue.

## 17. Implementation rule set

The following rules are binding for STEP 7.4 implementation:

1. Replay ordering MUST be deterministic and MUST use (event_time_dt, original_index).
2. original_index MUST be a canonical replay tie-breaker, not an exchange event number.
3. Event time MUST be historical event time, never processing time.
4. Naive timestamps MUST be rejected.
5. All timestamps MUST be UTC-normalized.
6. Replay MUST fail closed on invalid timestamps, malformed events, or unsupported event types.
7. Synthetic bid/ask values are compatibility placeholders only and MUST NOT be treated as observed market quotes.
8. Historical trade-only data MUST NOT be used to infer order-book depth, liquidity, spread, or queue state.
9. Replay must be isolated from previous runs and from hidden mutable state.
10. Replay config MUST include dataset identity, schema version, market, time bounds, balance, strategy, risk, execution config, and deterministic ordering config.
11. Replay evidence MUST include enough information to prove reproducibility.
12. Historical replay is non-authoritative and cannot override the financial source-of-truth model.

## 18. Contradiction check against Step 7.1 and Step 7.3

This contract is intentionally consistent with the authoritative Step 7.1 and Step 7.3 contracts.

Consistency checks:

- Step 7.1 requires raw data and canonical replay data to remain distinct. This contract preserves that distinction.
- Step 7.1 requires synthetic bid/ask fallback to last when quote-side values are absent. This contract preserves that requirement and explicitly defines it as a compatibility placeholder, not a historical quote.
- Step 7.3 requires ordering by (event_time_dt, original_index). This contract preserves it as the authoritative replay ordering rule.
- Step 7.3 requires finite positive numeric values and no invalid timestamp fallback. This contract preserves that rule.
- Step 7.3 requires replay dataset completeness and rejection semantics for partial/incomplete input. This contract preserves that rule and elevates it to the replay determinism requirement.
- Step 7.3 requires historical data to remain non-authoritative relative to financial state. This contract preserves that boundary.

There is no contradiction with the repository’s earlier historical-data contracts.

Final status: IMPLEMENTATION READY
