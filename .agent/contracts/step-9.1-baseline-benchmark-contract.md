# STEP 9.1 — Baseline Strategies and Benchmarking Contract

## Status

Architecture evidence for Step 9.1.

This contract is design-only and does not change runtime behavior. It captures the repository-grounded architecture required for the baseline and benchmarking gate under Step 9.1 and preserves the authoritative Step 8 backtest and financial authority contracts.

## 1. Purpose

This document defines the required Step 9.1 architecture:

- formal buy-and-hold baseline definition
- formal no-trade baseline definition
- benchmark definition and freeze rules
- candidate-vs-baseline comparison contract
- required comparison evidence for Step 9.1
- failure semantics for a non-beating strategy
- reproducibility metadata for benchmark comparison
- explicit authority boundaries and read-only evidence semantics
- deterministic benchmark behavior without introducing Step 9.2 validation requirements

This contract is limited to Step 9.1 only and does not claim Step 9.2 completion.

## 2. Scope

This contract covers only Step 9.1:

- Step 9.1 — Baseline Strategies and Benchmarking

This contract explicitly does not establish completion for:

- Step 9.2 — Walk-Forward and Robustness Testing
- development/validation/out-of-sample split implementation
- walk-forward validation
- regime analysis
- robustness testing
- parameter sensitivity analysis
- statistical validity implementation
- ML/AI strategy evaluation
- any live trading, live execution, or credential activation path

The roadmap dependency remains:

- 8 → 9.1 → 9.2

## 3. Roadmap alignment

The authoritative roadmap definition for Step 9.1 is:

"Establish baseline strategies, no-trade baselines, and benchmark comparisons before evaluating candidate strategy improvements. Baselines must be used as a control against claims of improvement and to make failed strategy outcomes meaningful."

Normative rule:

- Step 9.1 is a baseline control and benchmarking gate.
- A candidate strategy is not judged in isolation.
- A candidate strategy must be compared against meaningful baseline references before it is considered a meaningful improvement.
- A negative comparison outcome is valid research evidence and must not be hidden behind a single profitable backtest.

## 4. Buy-and-hold baseline

### 4.1 Definition

The buy-and-hold baseline for this project is a deterministic BTC-EUR spot benchmark using the same dataset and the same evaluation window as the candidate strategy under review.

Normative rules:

- market pair = BTC-EUR
- instrument type = spot
- benchmark style = buy-and-hold
- input dataset = the same canonical dataset and time range used by the candidate strategy
- starting capital = the same starting capital as the candidate strategy
- entry rule = purchase the full allocated capital at the first valid market price in the evaluation window
- exit rule = liquidate at the final valid market price at the end of the evaluation window
- execution realism = fees, spread, and slippage must be treated as explicit modeled assumptions when they are included in the benchmark output

### 4.2 Deterministic entry and exit assumptions

The buy-and-hold benchmark is deterministic and must not change after the benchmark configuration is frozen.

Required assumptions:

- the benchmark uses the same event ordering as the candidate strategy
- the benchmark uses the same dataset identity and time window as the candidate strategy
- the benchmark uses the same starting capital as the candidate strategy
- the benchmark uses explicit, reproducible cost assumptions where appropriate
- there is no hidden tuning or post-hoc adjustment of the benchmark after candidate results are known

### 4.3 Cost treatment

The contract requires explicit cost treatment, but it does not require a more complex cost model than the repo can defensibly support at this Step 9.1 gate.

Normative rule:

- if cost assumptions are included, they must be stated explicitly as modeled assumptions
- if no cost treatment is included for the benchmark, this must be recorded as a contract assumption and must remain consistent across benchmark runs
- benchmark costs must be comparable to candidate costs where the repository architecture allows direct comparison

### 4.4 Observed vs modeled assumptions

The benchmark must distinguish observed facts from modeled assumptions.

Observed assumptions:

- dataset identity
- dataset time window
- canonical event timestamps
- market quotes available in the canonical dataset
- event ordering and replay status

Modeled assumptions:

- fees
- spread assumptions
- slippage assumptions
- latency assumptions
- fill or partial-fill assumptions
- rounding assumptions
- any benchmark assumptions that are not directly present in historical observation

Normative rule:

- observed historical values are evidence
- modeled assumptions are explicit simulation parameters
- neither type is silently mixed without metadata

## 5. No-trade baseline

### 5.1 Definition

The no-trade baseline is the deterministic baseline where the strategy does not enter or exit any trade during the evaluation window.

Normative rules:

- starting capital = same capital as the candidate strategy
- trade count = zero
- trade behavior = no order generation
- no entry execution
- no exit execution
- deterministic final equity = the starting cash equivalent as defined by the contract
- PnL = zero from trade execution, unless explicit cost assumptions are recorded for a non-trading baseline

### 5.2 Final equity and PnL semantics

The no-trade baseline must have a clearly stated financial interpretation.

Normative rule:

- final equity is defined as the capital state with zero trading activity under the benchmark contract
- PnL for the baseline is the change relative to the starting capital, with any explicit costs or adjustments recorded transparently
- no hidden costs or hidden behavior are permitted

## 6. Benchmark definition

### 6.1 Valid benchmark for this project

A valid benchmark for this repository is one that is:

- frozen before candidate comparison
- generated from the same canonical historical input used by the candidate strategy
- relevant to BTC-EUR spot trading
- reproducible from the repository state and the data snapshot
- comparable to the candidate under the same evaluation window and starting capital
- documented as either observed-only, modeled, or mixed

### 6.2 Benchmark configuration identity

The benchmark must have an explicit configuration identity.

This identity should include:

- dataset identity
- market pair
- evaluation window
- starting capital
- benchmark type (buy-and-hold or no-trade)
- cost assumptions
- repository revision
- configuration version or hash

Normative rule:

- benchmark results cannot be retuned after the candidate result is known
- benchmark configuration must be treated as a frozen contract, not an adjustable optimization target

### 6.3 Preventing benchmark manipulation

Candidate results must not be used to tune the benchmark after the fact.

Normative rules:

- the benchmark configuration must be fixed independently of candidate performance
- no benchmark parameter may be adjusted to make the candidate appear better
- no benchmark output may be redefined after seeing the candidate result
- benchmark comparison must preserve auditability and reproducibility

## 7. Benchmark freeze rules

The benchmark configuration must be frozen before the comparison is performed.

Normative rules:

1. The benchmark dataset is fixed.
2. The evaluation window is fixed.
3. The starting capital is fixed.
4. The benchmark type is fixed.
5. The cost assumptions are fixed.
6. The repository revision is recorded.
7. The comparison evidence is produced only after the contract is frozen.
8. Benchmark tuning based on observed candidate performance is forbidden.

This is a contract-level gate and is not a Step 9.2 walk-forward or robustness gate.

## 8. Candidate-vs-baseline comparison

The comparison is a read-only benchmark comparison and must be limited to Step 9.1 evidence.

The comparison must include, where defensible:

- candidate final equity
- candidate PnL
- buy-and-hold final equity
- buy-and-hold PnL
- no-trade final equity
- no-trade PnL
- drawdown where available and relevant
- execution costs and cost attribution where available
- trade count where relevant
- absolute comparison
- relative comparison
- dataset identity
- evaluation window
- configuration identity

Normative rule:

- the comparison must be meaningful and comparable
- the candidate strategy must not be judged only by a single favorable metric in isolation
- the comparison must clearly state whether the candidate improved over the baseline, failed to improve, or was not defensibly comparable

The comparison must not require metrics beyond the repository’s current Step 8 architecture unless they are explicitly defensible and reproducible.

## 9. Required comparison evidence

The minimum comparison record for Step 9.1 must include:

- candidate result
- buy-and-hold result
- no-trade result
- absolute comparison values
- relative comparison values where defensible
- cost attribution or cost summary where available
- evaluation window
- dataset identity
- configuration identity
- repository revision
- benchmark configuration identity

This evidence is design-only and read-only. It does not become a new financial authority.

## 10. Failure semantics

A candidate strategy that does not beat or justify its benchmark is a valid negative research result.

Normative rule:

- the outcome is not a defect in the validation process
- the outcome is not a defect in the benchmark definition
- the outcome is not evidence of a broken repository
- the outcome is valid research evidence that must be recorded clearly

The required distinct research outcome is:

FAILED_BASELINE_COMPARISON

This status must mean:

- the candidate strategy did not demonstrate sufficient improvement over the relevant baseline
- the strategy remains a valid result of research and documentation
- the result should be preserved for future investigation or refinement
- the negative outcome must not be hidden behind a single profitable backtest or cherry-picked result

## 11. Reproducibility metadata

The baseline comparison must be reproducible from the archived configuration and evidence.

Minimum metadata required:

- dataset identity
- repository revision
- starting capital
- benchmark configuration
- cost assumptions
- evaluation window
- strategy configuration where applicable
- benchmark type
- candidate result identity
- comparison result status

Normative rule:

- this metadata must be stored with the comparison artifact
- reproduction must not require undocumented manual interpretation
- the same benchmark must reproduce the same comparison result given the same repository revision, dataset, and frozen configuration

## 12. Observed vs modeled assumptions

Step 9.1 must explicitly separate data from model assumptions.

Observed values:

- historical input values actually present in the canonical dataset
- canonical event stream and ordering
- timestamps and quotes from the dataset

Modeled values:

- fees
- spread assumptions
- slippage assumptions
- latency assumptions
- partial-fill assumptions
- any execution assumptions added by simulation

Normative rule:

- observed values are recorded as evidence
- modeled assumptions are recorded as assumptions
- candidate and baseline comparisons must not blur the distinction

## 13. Authority boundaries

The repository authority model remains binding.

- AccountingEngine remains the authoritative financial ledger.
- PositionManager remains a derived position projection.
- RiskEngine remains the risk gate.
- Baseline and benchmark evaluation is read-only evidence.
- No second accounting ledger is permitted.
- No second risk engine is permitted.
- No live execution is permitted.
- No paper-trading activation is permitted.
- No live credentials are permitted.

Normative rule:

- the baseline and benchmark layer is evidence-only and does not become an operational financial authority
- it cannot alter the live/default financial source of truth
- it cannot enable execution or activation paths

## 14. Determinism

The Step 9.1 benchmark comparison must be deterministic and transparent.

Normative rules:

- the same dataset, repository revision, benchmark configuration, and candidate configuration must produce the same comparison outcome
- no hidden randomness is allowed
- no benchmark tuning based on the candidate result is allowed
- no look-ahead behavior is permitted in benchmark evaluation
- benchmark comparison is a deterministic artifact generated from the canonical historical replay and the frozen benchmark configuration

## 15. Required evidence

The repository requires the following evidence to satisfy Step 9.1:

- buy-and-hold baseline definition
- no-trade baseline definition
- benchmark definition
- benchmark freeze record
- candidate result
- buy-and-hold result
- no-trade result
- comparison summary
- failure classification where appropriate
- reproducibility metadata
- authority boundary statement

This evidence must exist as design and/or artifact output, but must remain read-only and non-authoritative.

## 16. Exit / acceptance criteria

Step 9.1 is considered structurally complete when all of the following are true:

1. The project defines both a buy-and-hold and no-trade baseline.
2. Benchmarks are defined for the BTC-EUR spot context and the same canonical dataset/window as the candidate.
3. Benchmark configuration is frozen independently of candidate performance.
4. Candidate results are compared against baseline controls.
5. Required comparison evidence is recorded.
6. A failed comparison is recorded as a valid research outcome, not as a process defect.
7. The comparison remains read-only and does not create a second ledger or second risk authority.
8. Reproducibility metadata is sufficient to reproduce the same benchmark comparison.
9. The Step 9.1 contract remains limited to baseline/benchmarking and does not incorporate Step 9.2 validation logic.

## 17. Explicit exclusions

This contract explicitly excludes:

- development/validation/out-of-sample split implementation
- walk-forward testing
- regime analysis
- robustness testing
- parameter sensitivity analysis
- statistical validity implementation
- ML/AI strategy deployment or research layer
- risk-engine redesign or financial authority change
- second ledger creation
- new live execution permission
- paper-trading activation
- live credential use

These items belong to Step 9.2 or later and are not part of this Step 9.1 contract.

## 18. Final binding rule

The following rules are binding for Step 9.1:

1. Candidate strategies must be compared against meaningful baselines.
2. Benchmark definitions must be fixed before candidate comparison.
3. A failed baseline comparison is valid research evidence and not a validation defect.
4. Benchmarking remains read-only and non-authoritative.
5. Accounting, risk, and execution authority remain unchanged.
6. This contract covers only Step 9.1 and does not broaden into Step 9.2.
