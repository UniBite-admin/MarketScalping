# STEP 10.2 PAPER SESSION EVIDENCE CONTRACT

## Status

This contract defines the minimum evidence layer required to turn an actual Step 10.1 paper-trading runtime session into a valid Step 10.2 paper_result artifact.

It is intentionally narrow. It does not redefine the overall Step 10.2 comparison contract or the model-level risk/strategy architecture.

## 1. Purpose

The repository already contains the paper-trading runtime and the comparison engine. What is missing is a deterministic, auditable, session-scoped evidence artifact that captures the actual runtime session and the authoritative accounting state.

This contract defines the minimum artifact needed to support:

- real paper session identity
- session configuration identity
- runtime evidence lineage
- paper_result summary creation
- comparison with a backtest_result without inventing authority

This contract does not create a second financial authority and does not authorize any step beyond paper evidence generation.

## 2. Definition of a valid paper session

A valid paper session is an actual runtime session started from the Step 10.1 runtime path, using the existing market-data runtime and simulation-only execution path.

A valid paper session must include:

- a unique paper_session_id
- a deterministic identity rule
- an observed start timestamp and end timestamp
- the market symbol
- the market data source identifier
- the configuration snapshot used for the session
- the authoritative accounting state captured at the end of the session
- evidence lineage to the underlying runtime output files

A synthetic fixture or a manually assembled dict is not a valid operational paper session.

## 3. Required identity and metadata

### 3.1 paper_session_id

The paper_session_id must:

- be unique per runtime session
- be deterministic for the same canonical session payload
- be reproducible from the canonical session metadata
- be persisted in the paper evidence artifact

### 3.2 session boundaries

The artifact must define:

- session_start_utc
- session_end_utc
- market
- data_source
- source_kind

If these cannot be established, the result must fail closed and remain invalid.

## 4. Configuration identity

The evidence artifact must capture the runtime configuration actually used by the session.

Required fields include only values materially relevant to reproducibility:

- strategy configuration / identity
- risk configuration / identity
- execution simulation configuration
- fee assumptions
- spread assumptions
- slippage assumptions
- latency assumptions
- session configuration identity hash

The configuration identity must be captured separately from the runtime artifact contents.

## 5. Operational evidence

The paper evidence summary must include sufficient runtime counts and event categories to explain the operational session, including:

- market-data event count
- strategy decision count
- risk decision count
- simulated execution event count
- fill/rejection summaries
- stale-data incidents
- disconnect/reconnect incidents
- recovery/reconciliation events
- data-quality incidents
- runtime artifact references

These summaries may be aggregates or minimal categories, but they must correspond to the actual runtime session and must not be fabricated.

## 6. Financial result

The evidence artifact must summarize the authoritative AccountingEngine state:

- initial balance/equity
- final balance/equity
- realized PnL
- unrealized PnL when applicable
- fees and costs
- final position state

The financial summary must come from the authoritative accounting engine, not from inferred or synthetic totals.

## 7. Position semantics

Position state remains derived.

The artifact may include a position summary derived from the authoritative accounting state, but it must explicitly state that the position view is derived from AccountingEngine and not a second financial authority.

## 8. Evidence lineage

The paper artifact must provide:

- runtime artifact paths / references
- file lineage
- data source identity
- session root or report location

This lineage is required to preserve traceability.

## 9. Result semantics

This contract separates the following concepts:

- operational raw evidence
- derived paper_result summary
- backtest_result
- comparison_result

A paper_result is not a ledger and is not a new financial authority. It is a reporting artifact derived from runtime evidence and authoritative accounting state.

## 10. Integrity and fail-closed behavior

The artifact must fail closed when any required condition is missing:

- session identity missing
- required financial state unavailable
- authoritative accounting state inconsistent
- required configuration identity missing
- session boundaries missing or invalid
- evidence lineage missing
- synthetic or fixture-only inputs presented as operational evidence

The artifact should include a deterministic evidence signature/hash over the canonicalized session evidence where practical. A signature is only meaningful when the underlying evidence is real and traceable.

## 11. Authority boundaries

The existing authority model remains binding:

- AccountingEngine remains the authoritative financial ledger
- PositionManager remains derived
- ExecutionEngine remains execution journal/intake authority
- RiskEngine remains the pre-commit gate
- evidence generation is read-only with respect to financial authority
- paper_result is evidence/reporting, not a new financial ledger

## 12. No fabricated evidence

A paper_result may only be created from an actual runtime session.

Tests may generate fixtures to validate schema and fail-closed behavior, but fixtures must never be represented as operational paper evidence.

## 13. Minimal acceptance rule

The evidence artifact is valid only when it can be produced from an actual paper runtime session and can be consumed by the existing Step 10.2 comparator without inventing evidence or financial authority.
