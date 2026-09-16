# STEP 8.2 — Strategy and Risk Integration Contract

## Status

Implementation evidence for Step 8.2.

This contract documents the repository-grounded strategy/risk integration implemented for Step 8.2 only. It is intentionally limited to strategy hooks, risk gate hooks, execution simulation hooks, accounting boundary semantics, and isolation/determinism guarantees. It does not claim completion of Step 8.3 or Step 8.4.

## 1. Purpose

This document defines the required Step 8.2 architecture:

- canonical replay data must reach strategy evaluation
- strategy decisions must be explicit state transitions
- strategy candidates must pass through the RiskEngine gate
- only approved risk decisions may reach the execution simulation boundary
- simulated execution remains separate from live execution authority
- accounting remains authoritative
- position state remains derived
- backtest state remains isolated
- determinism and no-look-ahead remain preserved

## 2. Scope

This contract covers only Step 8.2:

- Step 8.2 — Strategy and Risk Integration

This contract does not establish completion for:

- 8.3 — Fees, spread, slippage, latency, and fill realism
- 8.4 — backtest outputs and performance metrics
- Step 9 or later strategy validation stages

The roadmap dependency remains:

- 7 → 8.1 → 8.2 → 8.3 → 8.4

## 3. Canonical replay and strategy hook

The backtest must accept the canonical historical replay stream produced by the repository replay boundary and pass each valid canonical event into the existing StrategyEngine.

Normative rule:

- StrategyEngine evaluates canonical replay data using only information available at the current event.
- Strategy decisions are explicit objects with discrete outcomes.
- Strategy output must be distinguishable between candidate trade, no trade, and invalid or rejected strategy state.
- BacktestEngine must not inline a separate strategy decision path that bypasses the StrategyEngine contract.

The repository implementation uses [strategy_engine.py](../../strategy_engine.py) as the strategy authority and requires the backtest to record StrategyDecision results.

## 4. Risk gate hook

Any strategy candidate must pass through the existing RiskEngine before execution simulation is permitted.

Normative rule:

- RiskEngine is the permission authority for simulation execution.
- RiskEngine must evaluate the current accounting-derived risk state.
- RiskEngine must fail closed on invalid or missing risk state.
- A rejected risk decision must not reach execution simulation.
- A strategy decision that is not a candidate trade is not executed.

The repository implementation uses [risk_engine.py](../../risk_engine.py) as the guardrail before any simulated execution is permitted.

## 5. Execution simulation hook

Only an approved risk decision may reach the backtest execution simulation boundary.

Normative rule:

- simulated execution is performed by [backtest_execution_model.py](../../backtest_execution_model.py)
- simulated execution remains separate from live execution behavior in [execution_engine.py](../../execution_engine.py)
- live trading, exchange orders, credentials, and withdrawals remain forbidden by architecture
- execution realism is simulation-only and does not constitute 8.3 completion

This contract therefore preserves the simulation-only execution boundary while allowing explicit execution outcome representation.

## 6. Explicit state transition sequence

The required Step 8.2 sequence is:

REPLAY_EVENT
→ STRATEGY_DECISION
→ RISK_DECISION
→ EXECUTION_SIMULATION
→ ACCOUNTING_EFFECT
→ POSITION_PROJECTION
→ BACKTEST_RESULT

Normative rule:

- each stage must be explicit in the backtest run data model
- execution simulation is not entered without a preceding approved risk decision
- accounting effect is an explicit effect on the authoritative accounting architecture
- position projection remains derived and not authoritative

## 7. Accounting authority boundary

AccountingEngine remains authoritative.

Normative rule:

- the backtest may produce local simulation results, but it must not become a second authoritative financial ledger
- accepted simulation may produce an accounting effect only through the authoritative accounting semantics
- rejected or failed execution must not create an unauthorized financial mutation
- accepted execution must create exactly one appropriate accounting effect
- RiskEngine is a gate, not a ledger
- PositionManager remains derived state, not a competing authority

The repository implementation preserves this boundary through [accounting_engine.py](../../accounting_engine.py), [position_manager.py](../../position_manager.py), [risk_engine.py](../../risk_engine.py), and the backtest-local simulation records.

## 8. State isolation

Each backtest run must remain isolated.

Normative rule:

- backtest state must not mutate live/default financial state
- backtest state must not mutate production positions
- no credentials or live exchange calls may be used
- no live activation may occur
- results remain local to the backtest run

## 9. Determinism and no-look-ahead

The Step 8.2 implementation must preserve the Step 7.4 and Step 8.1 guarantees.

Normative rule:

- strategy sees only information available at or before the current replay event
- risk sees only current valid state
- execution simulation does not use future events
- identical canonical input and configuration produce reproducible results
- wall-clock and machine-time dependence are not introduced

This is preserved by the canonical replay ordering and the event-order evaluation in the backtest flow.

## 10. Acceptance evidence for Step 8.2

The repository-grounded acceptance evidence required for Step 8.2 is:

- explicit StrategyDecision generation from canonical replay data
- explicit RiskDecision gate before execution simulation
- explicit execution simulation model result
- authoritative accounting boundary preserved
- derived position projection preserved
- state isolation preserved
- no live activation path
- deterministic, no-look-ahead behavior preserved

The implementation must be documented in this contract and must remain limited to Step 8.2.

## 11. Final binding rule set

The following rules are binding for Step 8.2:

1. Backtest input remains canonical replay data.
2. Strategy decisions are explicit and derived from StrategyEngine.
3. RiskEngine is the permission gate before execution simulation.
4. Only approved risk decisions may reach the execution simulation model.
5. AccountingEngine remains the authoritative ledger.
6. PositionManager remains a derived state projection.
7. Backtest-local state remains isolated and non-authoritative.
8. Determinism and no-look-ahead remain enforced.
9. Live trading, credentials, withdrawals, and activation remain forbidden.
10. This contract covers Step 8.2 only and does not claim 8.3 or 8.4 completion.
