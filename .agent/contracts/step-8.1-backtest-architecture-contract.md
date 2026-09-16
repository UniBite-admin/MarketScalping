# STEP 8.1 — Backtest Architecture Contract

## Status

Architecture evidence for Step 8.1.

This contract is design-only and does not change runtime behavior. It captures the repository-grounded architecture required for the backtest architecture gate under Step 8.1 and preserves the authoritative Step 7 replay and financial authority contracts.

## 1. Purpose

This document defines the required backtest architecture for Step 8.1 only.

The purpose is to establish a single explicit model for:

- the canonical historical input used by the backtest
- the backtest event flow
- the simulation boundaries used in the backtest
- the authority split between replay, strategy, risk, execution, accounting, and position state
- the boundary between observed historical data, modeled simulation assumptions, and derived output state
- state isolation and live isolation
- deterministic replay requirements and no-look-ahead rules

This contract does not claim 8.2, 8.3, or 8.4 completion.

## 2. Scope

This contract covers only Step 8.1:

- Step 8.1 — Backtest Architecture

This contract explicitly does not establish completion for:

- 8.2 — Strategy and Risk Integration
- 8.3 — Fees, Spread, Slippage, Latency, and Fill Behavior
- 8.4 — Backtest Outputs and Performance Metrics
- Step 9 or later strategy validation stages

The roadmap child-stage dependency is:

- 7 → 8.1 → 8.2 → 8.3 → 8.4 → Step 8

## 3. Authority boundaries

The repository already defines a strict authority model that remains binding.

- ExecutionEngine = execution journal / intake
- AccountingEngine = authoritative financial ledger
- PositionManager = derived position projection
- RiskEngine = pre-commit risk gate
- replay_runner.py = canonical historical replay boundary

Normative rule:

- Historical replay is a deterministic simulation input, not a second financial authority.
- The backtest may simulate execution behavior, but it may not replace or compete with the authoritative accounting and execution ledger.
- The backtest may produce local simulation state for modeling and reporting, but that state remains subordinate to the repository’s existing financial authority model.

## 4. Historical replay boundary

The authoritative historical replay boundary remains Step 7.

The accepted source of canonical input for the backtest is the canonical replay stream produced by [replay_runner.py](../../replay_runner.py), derived from the validated dataset and Step 7 contracts.

Normative rule:

- The backtest MUST accept canonical replay input, not arbitrary raw historical rows.
- The backtest MUST NOT bypass Step 7 validation, normalization, ordering, or rejection logic.
- The backtest MUST NOT treat raw historical observations as if they were authoritative financial state.
- The backtest MUST use the canonical dataset as its event source.

The implementation requirement is therefore:

historical dataset
→ validated/canonical dataset
→ replay_runner
→ backtest
→ strategy/risk decisions
→ simulated execution
→ accounting state
→ position projection
→ result

## 5. Event model

The repository already contains the required concepts without inventing a competing model.

### 5.1 Input event

The input event is the canonical historical replay event.

This event comes from the repo’s replay layer and is shaped as the repository-defined canonical market timeline:

- event_time_utc
- event_type
- market
- bid
- ask
- last

This is consistent with the Step 7 contracts and the replay normalization flow in [replay_runner.py](../../replay_runner.py).

### 5.2 Strategy decision

A strategy decision is a simulation-time decision derived from the canonical historical event stream and the current backtest state.

It is not an execution authority and it does not mutate the main accounting ledger.

### 5.3 Risk decision

A risk decision is a gating decision produced by the risk architecture defined in [risk_engine.py](../../risk_engine.py).

It is pre-commit only and remains a decision gate, not financial authority.

### 5.4 Simulated execution event

A simulated execution event is a modeled execution outcome produced by the backtest execution model.

It represents assumptions about:

- execution cost
- price impact
- fees
- slippage
- latency
- fill behavior
- rejection/fail behavior

This is simulation-only and must remain separate from the live execution journal in [execution_engine.py](../../execution_engine.py).

### 5.5 Accounting effect

An accounting effect is the effect of a modeled execution on the local backtest ledger or local simulation state only.

It does not mutate the repository's authoritative ledger.

Normative rule:

- backtest-local accounting state is subordinate and isolated
- authoritative accounting state remains in [accounting_engine.py](../../accounting_engine.py)
- no backtest-local state may become a competing financial source of truth

### 5.6 Derived position state

A derived position state is the normalized position view produced from the local backtest state.

This is analogous to the role of [position_manager.py](../../position_manager.py), but within the isolated backtest simulation boundary and not in the live/default runtime state.

### 5.7 Final backtest result

The final backtest result is the output bundle produced by the backtest engine for reproducibility, auditability, and analysis.

It contains:

- observed historical input summary
- replay status
- modeled assumptions/configuration
- derived simulated state
- trade/equity/performance summaries
- reproducibility metadata

The result is a reporting artifact. It is not the authoritative financial ledger.

## 6. Data flow contract

The authoritative data flow for Step 8.1 is:

historical dataset
→ validated/canonical dataset
→ replay_runner
→ backtest
→ strategy/risk
→ simulated execution
→ accounting state
→ position projection
→ result

Normative rules:

1. The historical dataset is raw evidence and must be validated under Step 7 rules.
2. The canonical dataset is the deterministic replay input and must remain separate from raw evidence.
3. The replay boundary is the machine-enforced gate for accepted historical input.
4. The backtest consumes canonical replay data only.
5. Strategy and risk decisions are generated using that canonical stream and the backtest state.
6. Simulated execution acts on the backtest-local state.
7. Accounting and position views remain derived or local within the backtest context.
8. The final result is output only; it is not used to mutate the live/default state.

Validation occurs at each of the following boundaries:

- initial raw historical validation
- canonical replay validation
- replay order and timestamp validation
- backtest event processing validation
- local simulation-state validation

## 7. Simulation boundaries

The Step 8.1 architecture must distinguish exactly three categories:

### 7.1 Observed historical data

These are values actually present in the canonical historical input and retained by replay validation.

Examples include:

- event timestamps
- market identifier
- bid/ask/last if present in the historical canonical event
- canonical input record ordering

Observed values are historical evidence and not assumptions.

### 7.2 Modeled simulation assumptions

These values are not historical observations. They are explicit modeling assumptions introduced by the backtest.

Examples include:

- execution fees
- spread assumptions
- slippage assumptions
- latency assumptions
- partial-fill ratio
- minimum order size
- minimum notional
- modeled liquidity assumptions

Normative rule:

- modeled values MUST be labeled as assumptions and MUST NOT be presented as historical observations.
- modeled assumptions MUST remain declarative and reproducible.
- no modeled assumption may be silently treated as observed historical fact.

### 7.3 Derived financial/performance state

These are outputs computed from simulation, not observed historical evidence.

Examples include:

- simulated cash balance
- position projection
- equity curve
- realized PnL
- trade summaries
- performance metrics
- drawdown metrics

Normative rule:

- derived state is a consequence of the simulation model and historical input
- it is not a competing authoritative ledger
- it is reportable and auditable but subordinate to the repository’s financial authority model

## 8. Financial authority boundary and backtest-local state

The Step 8.1 architecture must preserve existing authority boundaries.

- ExecutionEngine remains the repository execution journal / intake authority.
- AccountingEngine remains the authoritative financial ledger.
- PositionManager remains the derived position projection authority for live/default state.
- RiskEngine remains the pre-commit risk gate.

The backtest must not create a second authoritative financial ledger.

Normative rule:

- if the backtest uses local accounting or position state, it must be clearly defined as backtest-local and isolated per run
- this state must not be confused with the production accounting state
- the backtest must never mutate the live/default runtime accounting state or position state

## 9. State isolation

Backtest state must be isolated per run.

Normative rule:

- each backtest run has independent simulation state
- no state leaks between runs
- backtest execution cannot mutate live/default runtime state
- backtest execution cannot mutate live account balances
- backtest execution cannot activate or alter realtime trading state
- the backtest environment must remain simulator-only

The result of one run must not alter the next run's internal state unless the next run explicitly starts from the same dataset and configuration.

## 10. Live isolation

The backtest architecture must explicitly prohibit live behavior.

Normative rule:

- no real exchange orders may be generated by the backtest
- no live trading credentials may be used
- no withdrawals may be triggered
- no live activation may occur
- no production trading state may be mutated

The backtest is strictly simulation-only and local to the backtest run.

## 11. Determinism boundary

The Step 8.1 architecture must be consistent with Step 7.4 replay determinism.

A backtest must depend on:

- canonical dataset
- canonical event ordering
- explicit event timestamps
- explicit simulation configuration

A backtest must not depend on:

- wall-clock time
- current exchange market data
- network state
- machine-local time or timezone assumptions
- uncontrolled random behavior

Normative rule:

- repeated runs with identical canonical input and configuration must produce equivalent results
- the same event stream and same simulation config must produce the same ordering and same summary output

## 12. No-look-ahead boundary

The architecture must explicitly enforce the no-look-ahead rule.

Normative rule:

- at event T, only information available at or before T may influence the decision made for T
- future historical events must not be visible to decisions at T
- the historical replay stream must be processed in deterministic event order
- no decision may look beyond the current event boundary into future data

This rule is architectural and MUST be preserved even if later 8.2, 8.3, or 8.4 stages add more advanced simulation logic.

## 13. Result boundary

The backtest result represents a simulation artifact, not a source of financial truth.

### 13.1 What belongs to the backtest result

- observed historical summary
- replay state and canonical event summary
- modeled assumptions/configuration
- run metadata and reproducibility metadata
- simulated execution outcomes
- derived financial and performance state

### 13.2 What does not belong to the backtest result

- live account balances
- production ledger entries
- live exchange execution state
- production risk or position state
- execution journal authority

Normative rule:

- the result is a report of what happened in the backtest under the configured modeled assumptions
- the result must not be presented as financial authority or live execution truth

## 14. Acceptance evidence for Step 8.1

The repository-grounded evidence required for acceptance of Step 8.1 is:

- explicit event model
- explicit data flow
- explicit simulation boundaries
- historical replay canonical input requirement
- preserved authority boundaries
- explicit state isolation
- explicit live isolation
- deterministic replay contract
- no-look-ahead boundary
- result boundary definition

This evidence can be captured in a formal contract artifact under [.agent/contracts](../contracts) and is the minimal architecture evidence required before any 8.2/8.3/8.4 work is considered eligible.

## 15. Scope boundary for Step 8.1

This contract intentionally does not establish completion of:

- strategy optimization
- parameter search
- model training
- walk-forward evaluation
- paper trading
- live trading
- leverage or scaling logic
- metrics-suite completion beyond the architectural output definition

Those remain separate roadmap gates and are explicitly outside the minimal acceptance scope for Step 8.1.

## 16. Decision summary

Context:

The repository already has useful replay and backtest groundwork in [replay_runner.py](../../replay_runner.py), [backtest_engine.py](../../backtest_engine.py), and [backtest_execution_model.py](../../backtest_execution_model.py). This is a valid implementation starting point, but it is not yet a roadmap-compliant 8.1 architecture artifact because the required evidence is not explicitly captured as the contract for the stage.

Decision:

The Step 8.1 contract MUST explicitly define the backtest event model, the canonical replay input boundary, the simulation boundary between observed and modeled data, the authority split between replay, risk, accounting, and execution, the deterministic and no-look-ahead requirements, and the isolation rules for backtest-local state.

Rationale:

This is required by the repository roadmap and preserved by the Step 7 contracts. The architecture must remain consistent with:

- [step-7.1-historical-data-contract.md](step-7.1-historical-data-contract.md)
- [step-7.3-raw-validated-canonical-contract.md](step-7.3-raw-validated-canonical-contract.md)
- [step-7.4-replay-determinism-realism-contract.md](step-7.4-replay-determinism-realism-contract.md)
- [replay_runner.py](../../replay_runner.py)
- [execution_engine.py](../../execution_engine.py)
- [accounting_engine.py](../../accounting_engine.py)
- [position_manager.py](../../position_manager.py)
- [risk_engine.py](../../risk_engine.py)
- [strategy_engine.py](../../strategy_engine.py)

Consequences:

- Backtest architecture is defined as a local simulation layer, not a competing source of financial truth.
- Replay remains the canonical input boundary.
- Strategy and risk remain integration stages that follow the 8.1 contract.
- Later stages 8.2, 8.3, and 8.4 remain separate and are not implied to be complete by this contract.

## 17. Final binding rule set

The following rules are binding for Step 8.1:

1. Historical replay remains the canonical input source for the backtest.
2. Raw historical records are not used as authoritative backtest input without Step 7 replay validation.
3. The backtest event model uses canonical replay events and explicit local simulation decisions.
4. Strategy and risk decisions are simulation-time decisions and do not hold accounting authority.
5. Backtest-local accounting and position state are subordinate and isolated.
6. The authoritative ledger remains in AccountingEngine and the execution journal remains in ExecutionEngine.
7. Backtest state must not mutate live/default runtime state.
8. Determinism depends on canonical dataset, ordering, timestamps, and explicit configuration.
9. No-look-ahead is a hard architectural rule at event T.
10. The backtest result is a reporting artifact and not a second source of financial truth.
11. This contract covers only Step 8.1 and does not imply completion of 8.2, 8.3, or 8.4.
