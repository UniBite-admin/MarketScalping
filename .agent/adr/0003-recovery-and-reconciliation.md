# ADR 0003: Recovery and Reconciliation

## Status
Ready for implementation

## Context

The existing financial-state architecture has already established the correct authority model:

- ExecutionEngine = immutable execution journal
- AccountingEngine = authoritative financial state
- PositionManager = derived projection only
- RiskEngine = pre-commit risk gate
- execution_event_id = canonical idempotency key

This ADR addresses the next required architectural problem: recovery and reconciliation after crash or restart.

The authority model is correct, but the system currently has multiple persisted artifacts that can diverge during partial writes or process interruption. Because PositionManager is derived and not authoritative, the system must be able to recover a coherent financial state deterministically after restart without guessing.

The central question is:

If the process crashes at any point after execution acceptance but before all derived state is updated, can the system deterministically recover a coherent financial state from authoritative persisted information?

The architecture must answer this without introducing a second financial ledger, without making PositionManager authoritative, and without requiring distributed infrastructure or external persistence systems.

This ADR governs the recovery protocol after crash or restart. It does not authorize implementation of live trading or production deployment.

## Decision

The architecture will retain the following responsibilities:

- ExecutionEngine owns the immutable execution journal.
- AccountingEngine owns the authoritative financial state.
- PositionManager owns only the derived position projection.
- RiskEngine remains a pre-commit gate only.

The system will define recovery and reconciliation as a deterministic startup process whose authority is the persisted accounting state.

The system will treat the following as the authoritative financial truth:

- accepted execution_event_ids
- account balance
- realized PnL
- unrealized PnL
- equity
- open position state
- closed trade ledger
- relevant counters/metadata needed to preserve idempotency and continuity

The PositionManager projection will be rebuilt from this authoritative state whenever the process restarts or when persisted projection data is stale or partial.

The system must never guess financial state. If persisted authoritative state is incomplete, ambiguous, or materially inconsistent, the system must fail closed and block further market-event processing.

## Authority Model

### 1. Execution journal

The execution journal is evidence of execution activity. It records execution events and their timestamps, actions, and metadata.

It is not financial authority.

It may contain events that were never financially accepted, rejected, failed, skipped, or duplicated.

### 2. Accounting state

Accounting state is the authoritative financial state.

It must include the minimum persisted information needed to reconstruct financial state deterministically:

- processed/accepted execution_event_ids
- available balance
- realized PnL
- unrealized PnL
- equity
- open position state
- closed trade ledger
- relevant counters/metadata for continuity and idempotency

If any of the above are missing or contradictory, the system cannot safely continue.

### 3. PositionManager projection

PositionManager provides a derived projection of accounting state.

It is never authoritative.

Its CSV/history output is not authoritative financial state.

The projection must be deterministically rebuildable from authoritative accounting state and must be treated as a derived view, not as a second ledger.

### 4. RiskEngine

RiskEngine remains a pre-commit gate. It does not become a source of financial truth, and it does not replace accounting state.

## Financial Invariants

The core invariant is:

"Every accepted financial execution must be represented exactly once in authoritative Accounting state, and PositionManager state must be deterministically derivable from that authoritative state."

The following invariants are required:

1. Every accepted execution_event_id is represented exactly once in authoritative accounting state.
2. Only accepted financial executions may affect financial state.
3. Duplicate accepted execution_event_id values are idempotent.
4. Rejected, failed, skipped, and duplicate non-accepted execution outcomes produce no financial effect.
5. PositionManager state is derived from authoritative accounting state, not the other way around.
6. PositionManager state must be rebuildable without creating new financial effects.
7. Any disagreement between persisted authoritative state and the derived projection must be reconciled deterministically or blocked.
8. The system must fail closed when authoritative state cannot be safely validated.

This invariant is sufficient for recovery and reconciliation only when combined with explicit startup validation and fail-closed behavior.

## PositionManager Projection Contract

PositionManager state must be derived from accounting state.

The following projection must be rebuildable from authoritative accounting state:

- active/open position status
- lifecycle state (open, hold, close)
- entry timestamp and price metadata
- close timestamp and exit metadata
- hold event count / lifecycle progression
- provenance for audit and reporting

The current PositionManager CSV/history file may remain as a derived artifact, but it is not authoritative and must not be used as a basis for deciding accepted financial state.

Recommended smallest safe option:

- retain the existing CSV/history output as a derived artifact for audit and visibility
- rebuild it from accounting state on valid startup recovery
- validate it against the rebuilt projection
- do not treat it as the source of truth

The projection rebuild is a deterministic function of validated accounting state and should be repeatable without changing financial results.

## Execution Journal Reconciliation Rules

The execution journal and accounting accepted IDs must be compared according to the following rules.

### Case 1: execution exists, accounting does not

Classification: SAFE / RECONCILABLE when the execution is unaccepted and non-financial.

Examples:

- event was recorded but not accepted by accounting
- execution was rejected, skipped, or failed
- execution never reached financial acceptance

This is not an automatic financial error.

### Case 2: execution exists, accounting accepted

Classification: SAFE / normal accepted path.

This is the standard accepted execution lifecycle.

### Case 3: accounting accepted, execution missing

Classification: BLOCK unless the accepted accounting record can be proven valid without guessing.

This is a serious divergence because accounting is authoritative. If a financial effect is present in accounting but no execution record can be located, the recovery logic must verify whether the accounting ledger itself is internally valid before deciding whether to continue.

If the record cannot be proven valid, the system must block startup rather than guess.

### Case 4: exact duplicate execution journal rows

Classification: SAFE if payload-identical and represent the same execution_event_id.

Classification: BLOCK if materially conflicting.

Exact duplicates are not new financial events. They may be retained for audit but must not create extra financial effects.

### Case 5: malformed journal event

Classification: IGNORE if unrelated to accepted accounting state.

Classification: BLOCK if it affects authoritative validation or the integrity of recovery.

Malformed data should not cause the system to guess. A malformed event that is not connected to a valid financial effect may be ignored, but malformed data in the authoritative accounting path must block startup.

## Crash-Window Recovery Model

### 1. Execution persisted before accounting

Expected recovery result:

- execution journal row persists
- accounting does not yet reflect a financial effect
- system recovers by treating the event as unaccepted evidence or pending historical record
- no financial mutation occurs unless accounting later accepts it

### 2. Accounting accepted before PositionManager update

Expected recovery result:

- authoritative accounting state is retained
- position projection is stale or missing
- startup rebuild recreates the correct derived position state from accounting

### 3. PositionManager update before persistence completes

Expected recovery result:

- accounting remains authoritative
- the position projection is stale or partial
- the system rebuilds the projection from accounting state rather than trusting partial CSV output

### 4. Accounting persisted but position projection stale

Expected recovery result:

- accounting state remains the source of truth
- position projection is rebuilt deterministically from accounting
- no new financial effects are introduced

### 5. Position projection persisted but accounting state incomplete

Expected recovery result:

- this is a divergence
- position projection is not treated as authority
- startup must block unless accounting can be safely validated

### 6. Partial/corrupt accounting JSON

Expected recovery result:

- the accounting state is invalid until validated
- startup must fail closed and block new market processing

### 7. Partial/corrupt position ledger

Expected recovery result:

- position ledger is a derived artifact and may be rebuilt or ignored
- if accounting is valid, the projection is rebuilt from accounting state
- the stale ledger is not treated as financial truth

## Deterministic Startup Recovery Algorithm

The required startup sequence is:

BOOT
→ LOAD_ACCOUNTING
→ VALIDATE_ACCOUNTING
→ RECONCILE_EXECUTION_JOURNAL
→ REBUILD_POSITION_PROJECTION
→ VALIDATE_PROJECTION
→ READY

This sequence is correct because:

- accounting is the true financial authority
- execution journal is historical evidence, not authority
- the position projection is derived and must be rebuilt from validated accounting state
- validation must occur before new market events are accepted

The alternative sequence of rebuilding from stale PositionManager state would create a second financial authority and would violate the design.

## Idempotent Projection Rebuild

The projection rebuild must be deterministic and idempotent.

Running recovery multiple times must produce the same financial and position state.

The rebuild must:

- read authoritative accounting state only
- generate the same derived projection each time
- not create new financial effects
- not create new accepted execution IDs
- not alter the accounting ledger

Repeated rebuilds are valid as long as they are pure projection rebuilds.

## Fail-Closed Conditions

The system must be in READY only if:

- accounting state loads correctly
- account balance, PnL, open position, and closed trade ledger are internally consistent
- accepted execution IDs are unique and valid
- the execution journal can be reconciled without guessing
- the position projection rebuild is deterministic
- no unresolved divergence remains

The system must be in BLOCKED_ON_DIVERGENCE when:

- accounting state is incomplete or corrupt
- accepted execution IDs conflict or cannot be reconstructed safely
- execution journal/accounting mismatches require guessing
- projection rebuild cannot be made deterministic
- authoritative state cannot be validated

The system must never guess financial state.

## Startup Recovery Gate

Before the first new market event after restart, the system must enter an explicit startup gate.

Required behavior:

- RECOVERY_NOT_COMPLETE → no new market-event processing allowed
- RECOVERY_COMPLETE → market processing allowed

Specifically:

- if recovery is incomplete, startup must block all new processing
- if recovery completes successfully and validation passes, the system moves to READY
- if validation fails, the system moves to BLOCKED_ON_DIVERGENCE

This is a hard gate and is necessary to prevent the process from continuing with stale or uncertain financial state.

## Persistence Requirements

The minimal persistence model required by this ADR is intentionally small:

- authoritative accounting state must be persisted in a way that can be validated on startup
- append-only or consistent ledger writes are acceptable
- JSON snapshots or equivalent authoritative state files must be write-complete or replace-atomic where applicable
- position projection files are derived artifacts and may be overwritten during valid startup recovery
- corrupted or partial authoritative state is invalid until validated
- no new distributed infrastructure is required by this ADR

No database or distributed event bus is required for the recovery protocol described here.

## Replay Role and Boundaries

Replay is not the default live crash-recovery authority.

Replay may be used for:

- offline validation
- research and backtesting
- replay-based projection rebuild experiments
- deterministic verification that a given event stream recreates a known projected state

Replay must not be used as a substitute for authoritative accounting state during live recovery.

Live crash recovery must use validated accounting state as the authority. Replay is a tool for validation and offline modeling, not a financial authority.

## Recovery State Machine

The state machine should reflect the following lifecycle:

- BOOT
- LOAD_ACCOUNTING
- VALIDATE_ACCOUNTING
- RECONCILE_EXECUTION_JOURNAL
- REBUILD_POSITION_PROJECTION
- VALIDATE_PROJECTION
- READY
- BLOCKED_ON_DIVERGENCE

The system must not transition to READY unless the authoritative accounting state and derived projection have been validated.

## Required Implementation Boundaries

This ADR does not authorize any of the following:

- live trading
- exchange order placement
- leverage
- withdrawals
- API permission escalation
- autonomous production deployment
- making PositionManager authoritative
- introducing a second financial ledger
- adding external infrastructure to resolve a local-state problem

Implementation work must remain limited to the recovery and reconciliation contract described in this ADR.

## Required Test Categories

The implementation of this ADR will require tests covering at least the following categories:

1. accounting-state validation on startup
2. idempotent projection rebuild
3. duplicate execution journal row handling
4. malformed execution journal handling
5. stale or partial position projection recovery
6. fail-closed divergence handling
7. accepted-ID reconciliation with execution journal
8. startup gate behavior before first new market event
9. recovery repeatability and determinism

## Risks and Deferred Decisions

The following remain implementation decisions unless architecture requires resolution now:

- whether the existing PositionManager CSV is overwritten during valid startup recovery
- whether a separate derived projection artifact is preferable
- whether every mismatch or only unresolved financial mismatches should block startup
- how best to represent the exact audit trail for partial journal divergence

These decisions are intentionally deferred and do not change the authority model.

## Safety Constraints

This ADR does not authorize:

- live trading
- exchange order placement
- leverage
- withdrawals
- API permission escalation
- autonomous production deployment
- any change to the established risk and execution authority boundaries

The recovery protocol must remain minimal, deterministic, and fail-closed.

## Consequences

### Positive consequences

- single authoritative financial ledger remains clear
- recovery can be deterministic and auditable
- PositionManager remains a derived projection
- replay remains a validation tool, not a hidden authority
- startup can fail closed instead of guessing

### Negative consequences

- recovery requires explicit startup validation logic
- some stale or partial files must block processing
- the system may need to reject startup rather than continue with uncertain state
- the existing position CSV may need to be rebuilt rather than trusted

## Required implementation note

This ADR is design-only. No implementation work should occur as part of this task.

ADR STATUS:
READY_FOR_IMPLEMENTATION
