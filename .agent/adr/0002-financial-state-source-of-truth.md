# ADR 0002: Financial State Source of Truth

## Status
Accepted

## Context

The current trading pipeline is modeled as:

ExecutionEngine
→ PositionManager
→ AccountingEngine

This reflects the current simulation architecture, but the state transitions are not coordinated by a single shared atomic boundary. Each component persists its own state independently and is treated as an independent state authority over different aspects of the same trade lifecycle.

The current design has a verified risk: an execution event can be created and persisted, then a position can be opened by PositionManager, while AccountingEngine independently evaluates the same execution and may reject the corresponding financial event. In such a case, the execution history and the downstream financial state do not necessarily agree. This creates the possibility of inconsistent financial state: execution exists, position state may exist, and accounting may reject or fail to record the same trade.

The architecture problem is not merely about an incorrect value in one output file. It is a design-level issue: there is no authoritative financial ledger shared across all accepted execution outcomes, and there is no atomic transaction boundary covering:

- execution intake
- position mutation
- accounting mutation

The system is therefore an event-driven simulation pipeline rather than a single coherent financial-state machine.

This ADR addresses the verified architecture concern from the STEP 6A investigation. It does not change live or simulated trading behavior directly; it defines the source-of-truth model that must be implemented later.

## Decision

The architecture will adopt the following responsibilities:

- ExecutionEngine = immutable execution journal / execution intake layer
- AccountingEngine = authoritative financial ledger
- PositionManager = derived position-state view
- RiskEngine = pre-commit risk gate
- execution_event_id = canonical idempotency key across downstream financial state transitions

The key principle is that accepted financial executions must have one and only one financial effect. Rejected or failed executions must not mutate financial position or account balance.

This means the architecture must distinguish clearly between:

- Execution journal: What execution event occurred?
- Accounting ledger: What is the authoritative financial consequence of accepted execution events?
- Position view: What position state is derived from authoritative financial state?
- Risk: Should this candidate execution be allowed to proceed?

These responsibilities remain distinct and must not be merged into a single ambiguous state model.

## Financial-State Invariants

The following invariants are required:

1. Every accepted execution_event_id has exactly one financial effect.
2. Only accepted executions may mutate financial position or accounting state.
3. Duplicate execution_event_id values are idempotent.
4. Position state must reconcile to authoritative accounting state.
5. Rejected or failed executions create no financial balance or position effect.
6. Recovery must be able to reconstruct coherent state.
7. An unreconcilable financial state must block progression rather than silently continue.

## Component Responsibilities

| Component | Authority | State Ownership | Derived State | Orchestration Responsibility |
| --- | --- | --- | --- | --- |
| ExecutionEngine | No financial authority | Owns execution event journal and execution intake records | No | Records what execution was requested and accepted or rejected |
| AccountingEngine | Authoritative financial ledger | Owns balance, realized PnL, unrealized PnL, equity, accepted/rejected trade outcomes, trade identity | May derive account snapshots from ledger state | Validates accepted execution events and applies financial effects |
| PositionManager | No independent financial authority | Owns lifecycle metadata only as a derived representation | Position state is derived from accounting ledger and accepted execution results | Maintains position view for downstream consumers |
| RiskEngine | Pre-commit gate only | Owns risk decision records | No | Decides whether a candidate execution is allowed to proceed |
| MarketDataEngine | Coordinator / orchestrator | Owns pipeline wiring and sequencing | No | Calls the sequence of feature, strategy, risk, execution, position, and accounting stages |

## Alternatives Considered

### A. Execution + rollback/reconciliation

This option keeps execution as the primary state transition mechanism and attempts to restore consistency through rollback or reconciliation after the fact. It was considered as a repair model, but it is not a strong primary design because it relies on compensating actions after inconsistency has already been introduced. It is not sufficient as the main source-of-truth model.

### B. Accounting authorization before PositionManager commit

This option requires AccountingEngine to accept or reject a trade before PositionManager mutates position state. It is better than the current design because it moves the financial gate earlier. However, it still leaves PositionManager with a semi-independent state lifecycle unless it is explicitly derived from accounting state. It can be a useful implementation stage, but it is not the final decision.

### C. AccountingEngine as authoritative financial ledger + PositionManager derived view

This is the selected architecture. It gives the system a clear financial source of truth, makes idempotency easier, and supports deterministic recovery from execution history. It aligns with the verified accounting responsibilities already present in the code and minimizes ambiguous state ownership.

### D. PositionManager as authoritative state + AccountingEngine derived/reconciled

This option treats position state as the master state and reconstructs accounting from it. This is rejected because accounting is the component carrying the real financial truth: balance, equity, realized PnL, and trade acceptance/rejection. It exposes the system to a weaker accounting contract and makes the ledger vulnerable to drift from the position lifecycle.

### Other: immutable execution journal + derived financial state

This is conceptually useful as a lower-level decomposition, but it is not sufficient by itself unless the ledger layer is explicitly designated as the authoritative financial account state. The final architecture therefore adopts the ledger-first model as the complete design.

## Consequences

Positive consequences:

- single financial source of truth
- stronger idempotency guarantees
- deterministic recovery from journal + ledger state
- better replay compatibility
- clearer component responsibilities
- improved future live-trading safety
- cleaner separation between execution intake, financial authority, and derived position state

Negative consequences:

- PositionManager must eventually change from an independent financial source to a derived view
- AccountingEngine becomes more central and must be treated as a critical component
- persistence and recovery interfaces become more important
- existing tests may need architectural updates to assert ledger-level invariants
- migration must be controlled and delayed until implementation is properly staged

## Future Implementation Boundaries

This ADR does not itself authorize code changes or trading functionality. The implementation work that follows this ADR must address the following areas in a future development task:

- execution_event_id propagation across all downstream state transitions
- authoritative accounting acceptance or rejection logic
- derived PositionManager state
- atomic or transaction-like financial state handling
- reconciliation and recovery behavior
- restart behavior
- idempotency enforcement
- financial-state invariants enforcement
- risk inputs based on actual financial state, not just strategy signals

No implementation is performed in this ADR.

## Risk Engine Future Gap

This ADR explicitly notes that the current RiskEngine does not yet have access to the information required for a complete financial risk gate. In particular, it does not currently have enough information about:

- balance
- position size
- exposure
- open positions
- realized/unrealized PnL
- daily loss
- maximum risk per trade

This is an identified future architectural gap and is not part of the implementation scope of this ADR.

## Replay / Backtest Compatibility

This decision remains compatible with the project’s simulation and replay model:

historical data
→ replay
→ backtest
→ paper trading
→ future controlled live trading

The key reason is that the architecture keeps the execution journal immutable and makes the accounting ledger authoritative. A replay engine can rebuild the same financial state by processing the same accepted execution events in order. This is consistent with deterministic replay and with safer progression toward paper and live trading, as long as the implementation remains gated and validated.

## Rejected Interpretations

This ADR explicitly rejects the following interpretations:

- PositionManager is not the authoritative financial ledger.
- Execution history alone is not sufficient to represent financial account state.
- RiskEngine is not the financial source of truth.
- Reconciliation is not the primary architecture.

## Implementation Readiness

ARCHITECTURE READY FOR IMPLEMENTATION

This decision identifies a valid architecture for implementation, but it does not authorize direct implementation. Any implementation must occur only in a separate task that passes the required workflow gates:

Developer
→ CI
→ QA
→ Safety
→ Human Approval

before merge.

## Limitations

The STEP 6A investigation identified the following limits:

- the current system is simulation-only
- no full cross-component reconciliation test currently proves every execution path
- restart and crash behavior requires explicit future testing
- live exchange behavior is not part of this ADR

## Decision Authority

- Architect proposes and documents the architecture decision.
- Orchestrator controls workflow progression.
- Developer implements only after authorization.
- QA independently verifies implementation.
- Safety can block unsafe implementation.
- Human approval remains required for high-risk changes.

---

This ADR documents the architectural decision for financial state ownership and source-of-truth responsibility. It is a design record only and does not implement any production or simulation logic.
