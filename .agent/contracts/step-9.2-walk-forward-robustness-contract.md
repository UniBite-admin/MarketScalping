# STEP 9.2 — Walk-Forward and Robustness Testing Contract

## Status

Architecture evidence for Step 9.2.

This contract is design-only and does not change runtime behavior. It captures the repository-grounded architecture required for the walk-forward and robustness gate under Step 9.2 and preserves the authoritative Step 8 backtest architecture, Step 8.2 risk integration, and Step 9.1 baseline/benchmarking contract.

## 1. Purpose

This document defines the required Step 9.2 architecture:

- development / validation / out-of-sample separation
- walk-forward evaluation design
- regime analysis requirements
- robustness testing requirements
- parameter sensitivity analysis
- statistical validity requirements
- validation_result semantics
- failure semantics for a rejected strategy
- authority boundaries and evidence-only semantics
- reproducibility and traceability requirements
- explicit exclusions that remain outside this gate

This contract is limited to Step 9.2 only and does not claim completion of Step 10 or later stages.

## 2. Scope

This contract covers only Step 9.2:

- Step 9.2 — Walk-Forward and Robustness Testing

This contract explicitly does not establish completion for:

- Step 10 — Paper Trading
- live trading or exchange activation
- live-wallet or withdrawal permissions
- new financial authority for strategy validation
- execution journal mutation or accounting authority changes
- any live market-data or operational execution path
- benchmark manipulation or post-hoc benchmark retuning
- model tuning after OOS evaluation begins

The roadmap dependency remains:

- 8 → 9.1 → 9.2

## 3. Roadmap alignment

The authoritative roadmap definition for Step 9.2 is:

"Evaluate the strategy with time-series aware validation, walk-forward splits, regime analysis, robustness testing, parameter sensitivity, and statistical validity under varying market conditions. The result must be able to reject the strategy when it fails, without treating that rejection as a defect in the process."

Normative rules:

- Step 9.2 is a validation gate, not a financial-authorization stage.
- Candidate strategies are evaluated in a time-series-aware manner and must survive a walk-forward process before a positive claim is made.
- A failed strategy is valid research evidence. It is not a defect in the validation process.
- Validation evidence must be objective, reproducible, and separable from development choices.
- A strategy is not promoted beyond research without passing the defined validation process with objective evidence.

## 4. Authority boundaries and evidence-only semantics

The repository’s existing authority model remains binding and is not altered by this contract.

- AccountingEngine = authoritative financial ledger
- PositionManager = derived position projection
- RiskEngine = pre-commit gate only
- replay_runner.py = canonical historical replay boundary
- Step 9.2 validation = read-only evidence artifact, not a financial authority

Normative rules:

1. Strategy validation must never mutate the authoritative accounting ledger.
2. Validation output may report performance, failure, and evidence, but it may not change the financial source of truth.
3. RiskEngine remains a pre-commit gate and is not upgraded into a validator of strategy acceptance.
4. Backtest/local simulation artifacts remain isolated and subordinate to the authoritative ledger.
5. Step 9.2 does not authorize paper trading, live trading, or any execution activation path.
6. `validation_result` is a reporting artifact used to document objective evidence and stage status; it is not a second ledger, execution journal, or risk authority.

This contract therefore preserves the architecture established in [step-8.1-backtest-architecture-contract.md](step-8.1-backtest-architecture-contract.md), [step-8.2-strategy-risk-integration-contract.md](step-8.2-strategy-risk-integration-contract.md), and [step-9.1-baseline-benchmark-contract.md](step-9.1-baseline-benchmark-contract.md).

## 5. Development, validation, and out-of-sample separation

### 5.1 Required split

The repository requires strict separation between development, validation, and out-of-sample evaluation.

Normative rules:

- the development set is used only for strategy design, feature generation, and parameter exploration
- the validation set is used for model selection and acceptance checks under time-series-aware conditions
- the out-of-sample (OOS) set is reserved for final evidence and must not be touched for tuning
- there must be no leakage across the splits by time, event order, look-ahead, or data leakage
- if the strategy uses parameter tuning or regime-specific adjustments, those adjustments must be frozen before the OOS set is evaluated

### 5.2 No-leakage requirements

The following are forbidden in Step 9.2:

- using future data in prior windows
- re-fitting after observing validation or OOS performance
- selecting hyperparameters using the same OOS period that is intended for final evaluation
- mixing development and OOS windows into a single evaluation sample without explicit labeling
- treating a profitable single window as sufficient evidence when other windows fail

### 5.3 Frozen evaluation contract

Once the OOS window is fixed:

- all parameter choices must be frozen
- all thresholds must be frozen
- all signal logic must be frozen
- all benchmark assumptions must remain consistent with Step 9.1
- the OOS result is then read and recorded as evidence

This preserves deterministic validation behavior and avoids hidden optimization after the fact.

## 6. Walk-forward evaluation

### 6.1 Required design

The repository requires an explicit, time-series-aware walk-forward design.

A valid walk-forward design must include:

- a fixed chronological ordering
- rolling or expanding training/development windows
- forward validation periods
- final OOS holdout or final-period evaluation when the gate requires final confirmation
- consistent benchmark and cost assumptions across each fold
- complete evidence for each fold and the aggregate result

### 6.2 Minimal walk-forward semantics

A conservative Step 9.2 design should require:

1. define the evaluation horizon
2. define a fixed sequence of walk-forward windows
3. evaluate each fold using only data available at that fold boundary
4. preserve chronological order and no look-ahead
5. aggregate performance across folds with explicit summary metrics
6. require a failure result if the strategy degrades materially or fails repeatedly across folds

### 6.3 Acceptance criteria for walk-forward evidence

A strategy is not considered validated on the basis of a single favorable fold or a single favorable summary statistic.

The following must be reported for walk-forward evidence:

- fold definitions
- training window range
- validation window range
- OOS window range if applicable
- candidate result per fold
- baseline result per fold
- performance summary across folds
- regime mix per fold
- failure or warning counts per fold
- reasons for any fold rejection

Normative rule:

- walk-forward performance must be treated as evidence of stability across time, not as a narrative claim that a single period proves generalization.

## 7. Regime analysis

### 7.1 Required practice

Step 9.2 requires regime analysis under varying market conditions.

A valid regime analysis must separate performance by market condition, not only by aggregate result.

Examples of regime labels may include:

- trending vs ranging market
- high-volatility vs low-volatility periods
- macro stress / dislocation periods
- event-driven or discontinuous periods
- periods with elevated spread / slippage assumptions

Normative rules:

- the regime taxonomy must be defined before performance is interpreted
- a strategy may be valid in one regime and invalid in another; that must be reported as evidence
- the repository must not hide regime failure behind aggregate profitability
- regime sensitivity must be reported with the same dataset and consistent cost assumptions

### 7.2 Regime evidence requirements

The regime analysis record must include:

- regime definition
- regime boundaries
- number of periods in each regime
- candidate performance by regime
- baseline performance by regime
- evidence of regime-specific failure or dependence
- whether the strategy is robust across the observed regimes

A strategy that underperforms or collapses under a defined regime is still valid evidence and must not be treated as a process error.

## 8. Robustness testing

### 8.1 Robustness scope

Robustness testing under Step 9.2 must test whether the strategy survives reasonable variations in the evaluation conditions without requiring a new authority model.

Valid robustness variations include:

- cost assumption changes (fees, spread, slippage)
- parameter perturbation around the selected configuration
- regime shifts or non-stationary conditions
- altered event ordering assumptions within the canonical replay boundary
- reduced signal quality or missing event quality scenarios
- representative data-quality or timing stress cases within the historical replay scope

Normative rules:

- robustness testing must be deterministic and reproducible
- robustness scenarios must be defined before they are run
- the strategy may legitimately fail under one or more robustness scenarios
- a failed robustness scenario is valid evidence and is not a defect of the evaluation process
- no claim of robustness is valid without explicit scenario outcomes

### 8.2 Robustness evidence record

The robustness evidence must include:

- scenario definition
- scenario assumptions
- dataset identity and time window
- changed assumptions relative to the base case
- resulting performance
- pass/fail status for each scenario
- aggregate robustness assessment

If the strategy only survives the base case and fails under modest realistic perturbation, the result must be recorded as a failure or instability signal, not as success by omission.

## 9. Parameter sensitivity

### 9.1 Required analysis

Parameter sensitivity is required to prevent acceptance based on a single lucky configuration.

Normative rules:

- the selected parameter set must not be judged in isolation
- at minimum, the strategy must report sensitivity around the selected configuration
- sensitivity must be measured under the same canonical dataset and evaluation contract
- a parameter that causes large performance swings is evidence of fragility and must be reported

### 9.2 Minimal sensitivity evidence

The sensitivity record should include:

- parameter name
- base value
- range or grid explored
- metric or outcome summary per value
- whether the reported performance is stable or unstable across the range
- whether the selected parameter is materially dependent on a narrow favorable region

If the strategy requires a narrow parameter band to survive validation, that is evidence of fragility and is not a basis for blanket success claims.

## 10. Statistical validity

### 10.1 Conservative interpretation

The repository requires statistical validity or at least explicit statistical caution when performance claims are made.

Normative rules:

- aggregate performance claims must not be based on a single favorable period alone
- any inference beyond descriptive comparison must be justified by sample size, independence assumptions, and test choice
- if inferential statistics are unavailable or weak, the result must be reported as descriptive evidence only
- a strategy must not be called superior simply because the mean return is positive in a single period

### 10.2 Required reporting

When statistical validity is used, the report must include:

- metric definition
- sample size or number of periods/folds
- test or confidence method used
- assumptions behind the method
- interpretation limits
- whether the result is descriptive-only or inferential

If statistical testing cannot reasonably support the claim, the contract requires a conservative statement such as:

- the result is descriptive evidence only
- the strategy is not yet statistically validated
- the strategy is not accepted on the basis of a single favorable outcome

This is stricter than claiming success based on a single profitable backtest.

## 11. `validation_result` artifact semantics

The repository already treats `validation_result` as a required stage outcome artifact for strategy validation.

A valid `validation_result` for Step 9.2 must include at a minimum:

- strategy identifier
- dataset identity and canonical snapshot reference
- baseline identity and benchmark configuration reference
- development window definition
- validation window definition
- OOS window definition
- walk-forward summary
- regime analysis summary
- robustness test summary
- parameter sensitivity summary
- statistical validity summary
- final outcome: PASS / FAIL / INCONCLUSIVE
- reason codes
- evidence references
- repository revision / artifact hash where applicable

Normative rules:

- `validation_result` is read-only evidence and must not become a financial authority
- it records objective stage status, not trade execution or ledger state
- `FAIL` is an acceptable outcome and must be respected as valid research evidence
- `PASS` requires objective evidence across the defined validation process
- `INCONCLUSIVE` is allowed only when evidence is incomplete or too limited to support a definitive claim

The artifact must be explicit about whether the strategy survived walk-forward, regime robustness, and parameter sensitivity requirements before it may be considered for later stages.

## 12. Failure semantics

### 12.1 Failure is valid research evidence

This contract explicitly rejects the idea that a failed validation outcome is a defect in the process.

A strategy may fail for valid reasons, including:

- walk-forward instability
- failure in one or more time periods or regimes
- strong sensitivity to a narrow parameter region
- breakdown under realistic cost assumptions
- poor robustness under modest scenario variations
- statistical weakness or insufficient evidence
- leakage or unclean separation between development and OOS data
- inability to justify performance over the relevant baseline

### 12.2 Failure must be recorded as evidence

Failure must be recorded with clear reason codes and the relevant evidence references.

Normative rules:

- failure cannot be hidden behind a profitable single window
- failure cannot be reinterpreted as success after the fact
- the validation process must be transparent about reasons for rejection
- a rejected strategy is still valid research evidence and can be retained as a negative result for later study

## 13. Reproducibility

### 13.1 Required reproducibility contract

All Step 9.2 evaluation artifacts must be reproducible from the repository state and the canonical dataset snapshot.

Required reproducibility metadata includes:

- dataset identity
- canonical replay status
- evaluation window definitions
- benchmark definition
- cost assumptions and scenario assumptions
- parameter values used
- repository revision
- configuration hashes or equivalent fingerprints where available
- result generation order and artifact lineage

Normative rules:

- no hidden randomness in evaluation logic unless explicitly identified and traceable
- no implicit machine-dependent timing or calendar assumptions may alter the result
- event ordering and canonical replay rules remain authoritative
- the same input data and configuration must yield the same validation outcome

## 14. Data flow contract

The Step 9.2 evidence flow remains:

canonical historical dataset
→ Step 9.1 benchmark reference
→ development split
→ validation split
→ walk-forward evaluation
→ regime analysis
→ robustness scenarios
→ parameter sensitivity analysis
→ statistical validity review
→ validation_result

Normative rules:

1. The canonical replay boundary remains the entry point for all evaluation.
2. Development, validation, and OOS windows are explicit and time-ordered.
3. Benchmark and baseline conditions remain frozen and comparable.
4. Walk-forward results are generated before any final strategy claim is made.
5. Validation output remains evidence-only and does not change financial authority.

## 15. Explicit exclusions

This contract intentionally excludes the following items:

- live trading decisions or execution permission
- real order placement or withdrawal authority
- any deployment safety bypass
- any change to the AccountingEngine authority model
- any change to the RiskEngine pre-commit gate semantics
- any claim that a failed or inconclusive strategy is a defect in the process
- performance improvement claims without baseline comparison and validation evidence
- any attempt to broaden Step 9.2 into paper trading or live trading requirements

## 16. Exit criteria for Step 9.2

Step 9.2 is considered structurally complete only when all of the following are true:

1. development, validation, and OOS windows are strictly separated
2. walk-forward evaluation is time-aware and reproducible
3. regime analysis is documented and non-hiding
4. robustness tests are defined and reported
5. parameter sensitivity is measured and documented
6. statistical validity or explicit statistical caution is reported
7. `validation_result` records pass/fail/inconclusive outcomes and evidence references
8. failed strategy outcomes are treated as valid research evidence
9. no financial authority or live-trading path is introduced
10. the contract remains intentionally limited to Step 9.2 and does not claim Step 10 completion

## 17. Binding rule set

The following rules are binding for Step 9.2:

1. Development, validation, and OOS splits must remain separate.
2. Walk-forward evaluation must be chronological and deterministic.
3. Regime analysis must report dependency and failure modes.
4. Robustness testing must be explicit and reproducible.
5. Parameter sensitivity must avoid single-configuration acceptance.
6. Statistical validity must be reported conservatively.
7. `validation_result` must be evidence-only and non-authoritative.
8. Failure is valid research evidence and cannot be hidden.
9. No live trading or live execution authority may be introduced.
10. This contract covers Step 9.2 only and does not imply Step 10 readiness.
