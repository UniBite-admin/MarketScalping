# STEP 10.2 — Paper-vs-Backtest Comparison Contract

## Status

Architecture evidence for Step 10.2.

This contract defines the minimum architecture required for the official STEP 10.2 comparison gate and preserves the repository’s fail-safe authority model.

## 1. Purpose

This document defines the required architecture for Step 10.2 only:

- compare real-time paper-trading outcomes with historical backtest results
- explain divergence caused by operational conditions and model assumptions
- preserve fail-closed evidence semantics
- prevent silent success when unexplained paper/backtest divergence remains

This contract does not authorize Step 11 or any live-money activation path.

## 2. Authoritative roadmap definition

The authoritative definition in [.agent/roadmap/master_roadmap.json](../roadmap/master_roadmap.json) is:

> Compare paper-trading outcomes with historical backtest results and identify divergence caused by latency, spread, data quality, execution assumptions, or operational conditions. The objective is to prove the real-time operation matches the modeled assumptions before live trading is considered.

The required evidence list is:

- paper/backtest discrepancy analysis
- execution realism analysis
- data quality controls
- paper-trading result
- backtest_result

The exit criteria are:

- Differences are explained and attributable to real-world operating conditions or model assumptions
- No unrecognized divergence remains after a sufficient observation period
- A strategy is not promoted without observed realism and a documented explanation of any live-vs-paper gap
- The paper-trading process is demonstrably representative of the validated strategy and operational constraints

## 3. Scope and non-goals

This contract covers only Step 10.2.

It does not establish readiness for:

- Step 11
- live trading
- live order placement
- withdrawal privileges
- leverage or margin activation
- any automatic promotion from paper to live

## 4. Authority boundaries

The existing authority model remains binding:

- ExecutionEngine = execution intake and execution journal
- AccountingEngine = authoritative financial ledger
- PositionManager = derived position projection
- RiskEngine = risk gate
- Step 10.2 is read-only evidence and comparison analysis only

The comparison layer must not create a second financial authority.

## 5. Required comparison behavior

Step 10.2 must not simply compare final PnL and silently pass.

It must produce an auditable discrepancy analysis that explains WHY paper and backtest diverge across:

- market-data differences
- timing differences
- strategy-decision differences
- risk-decision differences
- execution/fill differences
- fee differences
- spread differences
- slippage differences
- latency differences
- partial-fill differences
- rejected/failed execution differences
- accounting differences

### Required outcomes

1. A deterministic discrepancy analysis is generated for each material difference.
2. Each difference must have an explanation or a blocked validation result.
3. Unexplained divergence must prevent a pass result.
4. Data-quality controls must be explicit and reproducible.
5. Paper-trading results and backtest results remain separately identifiable.
6. The comparison must remain evidence-only and cannot create financial authority.

## 6. Required evidence artifact shape

The comparison evidence must include:

- comparison_id
- paper_result
- backtest_result
- data_quality_controls
- discrepancy_analysis
- summary_status
- unexplained_divergence
- authority_boundary
- deterministic

A material difference without an explanation is a validation failure, not a pass condition.

## 7. Minimal architecture needed for Step 10.2

The minimal implementation is a read-only comparison engine that accepts the existing backtest result artifact and the paper-trading result artifact, studies the explainable differences across the required operational dimensions, and returns a deterministic pass/fail result.

It must:

- compare separately identifiable result objects
- attribute divergence to specific operational causes
- record any unexplained differences as a blocked result
- remain read-only and fail-closed
- avoid implicit live-trading promotion

## 8. Approval rule

Step 10.2 is acceptable only when the comparison engine can demonstrate structured, auditable explanation of divergence rather than a simple net-PnL match check.
