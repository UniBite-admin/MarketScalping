# Group B Sequence Semantics Analysis

## Status

- Group B: NOT FROZEN
- analysis-only
- no production implementation
- no decision is frozen by this document
- no tolerance formula is frozen by this document

## 1. Objective

This analysis addresses the first root-decision batch identified in the Group B dependency analysis:

1. same-direction observation set
2. gap definition
3. causal observation history
4. whether the current swing is included or excluded from the tolerance history
5. exact availability timing of observations for a new eligible swing

The objective is not to choose the final tolerance formula. It is to define the smallest defensible semantic contract for the historical same-direction sequence that can later feed a tolerance calculation without inventing missing technical meanings.

The analysis respects the existing frozen state:
- Group A remains frozen and human-approved.
- the 15-minute OHLC/bar contract remains frozen and human-approved.
- Group B remains not frozen.
- Phase 2 remains not started.

## 2. Frozen Inputs

FROZEN

- Group A swing semantics are frozen.
- 15-minute OHLC/bar contract is frozen.
- Event exactly at bar_end belongs to the next bar.
- Closed bars are immutable.
- Trailing/incomplete bars are excluded from finalized evaluation.
- Final partial bar at dataset end is discarded.
- Group A confirmation and eligibility timing remain authoritative.

RESEARCH-SUPPORTED

- The canonical BTC-EUR dataset supports 78 eligible swing highs and 68 eligible swing lows.
- The same-direction sequence must be separated by direction.
- Mixed high+low calibration is methodologically invalid for same-direction tolerance evidence.
- The research data supports descriptive spacing statistics for highs and lows separately.

UNDEFINED

- the exact final historical observation semantics for a future Group B tolerance rule
- the exact gap representation for future tolerance math
- the exact causal state model for tolerance update timing

## 3. Same-Direction Observation Set

### 3.1 Governing rule from frozen inputs

The frozen Group A rule defines a confirmed swing as a local extremum that becomes valid only when the required right-side comparison is observable and the canonical replay order supports the confirmation.

Therefore, for Group B, the observation set cannot be a vague series of raw prices. It must be a sequence of eligible confirmed swings in canonical ordering, grouped by direction.

### 3.2 Recommended semantic interpretation

The minimal defensible interpretation is:

- observed same-direction sequence for high swings = sequence of eligible confirmed swing highs, ordered by eligibility timestamp
- observed same-direction sequence for low swings = sequence of eligible confirmed swing lows, ordered by eligibility timestamp
- no mixing across directions
- no use of non-eligible swings
- no use of future swings

This is the strongest evidence-supported semantic definition because it is the direct output of the frozen Group A pipeline and the already-established archival research facts.

### 3.3 Why this is the most defensible definition

Evidence basis:
- the research explicitly separated highs and lows as distinct sequences
- the mixed high+low sequence was previously identified as methodologically invalid for same-direction calibration
- the frozen bar contract and frozen Group A timing give a clear event ordering for eligibility

Remaining limitation:
- this defines the stream correctly, but it does not yet determine whether the future tolerance should be computed from absolute gaps, relative gaps, or another transformed quantity

### 3.4 What is not justified

The following are not supported by the current evidence and therefore are not recommended as the semantic contract:
- cross-direction historical sequences
- unconfirmed or partially confirmed swings
- a hidden future-looking stream
- a tolerance history that includes yet-to-be-eligible swings from later bars

### 3.5 Timing semantics

For any eligible swing S_i, the observation sequence should be ordered by the time at which the swing becomes legally available to downstream logic, not by a later historical inference.

The most defensible interpretation is:
- swing occurrence time: time of the price bar / swing event
- confirmation time: time when required Group A evidence is available
- eligibility time: the first time the confirmed swing may affect downstream logic
- ordering key for the historical observation stream: eligibility timestamp, then canonical replay order as tie-break

This is consistent with the frozen Group A causality model and does not invent any new semantics beyond what the frozen design already implies.

## 4. Gap Definition Candidates

This section evaluates candidate gap meanings without choosing a final tolerance formula.

### 4.1 Candidate A — absolute price gap

Definition:

G_abs(i, i-1) = |P_i - P_{i-1}|

where P_i and P_{i-1} are the prices of two consecutive eligible same-direction swings in the historical observation sequence.

Exact formula:
- if using consecutive same-direction eligible swings in time order: absolute difference in price units

Units:
- price units of the asset, e.g. EUR for BTC-EUR

Invariance properties:
- invariant to direction sign because the sequence is already same-direction
- directly interpretable in price units
- directly compatible with a later tolerance measured in the same price unit

Causal availability:
- available whenever both observations are already eligible and in canonical order

Compatibility with future tolerance architecture:
- high compatibility because it is the most directly interpretable primitive for later tolerance math

Risks of hidden assumptions:
- it presumes the tolerance should live in the same units as price and may therefore be sensitive to asset scale
- this is not a fatal problem, but it is a real modeling choice that must be made explicitly later

### 4.2 Candidate B — relative price gap

Definition:

G_rel(i, i-1) = |P_i - P_{i-1}| / R

where R is a chosen reference price.

Exact formula:
- the numerator is an absolute price gap
- denominator must be explicitly specified later

Units:
- dimensionless ratio, if R is in the same price units

Invariance properties:
- more scale-normalized than absolute price gap
- depends on the chosen reference price and therefore requires an explicit reference definition

Causal availability:
- available when the numerator and reference are both known at the time of evaluation

Compatibility with future tolerance architecture:
- compatible only if the denominator is defined and kept causal

Risks of hidden assumptions:
- denominator selection is not justified by existing evidence
- relative-gap semantics can become arbitrary if the denominator is not already specified by repository semantics

### 4.3 Candidate C — normalized gap

Definition:

G_norm(i, i-1) = |P_i - P_{i-1}| / max(P_i, P_{i-1}, epsilon)

or similar normalized variants.

Exact formula:
- requires a precise normalization formula and a convention for epsilon or zero handling

Units:
- dimensionless ratio

Invariance properties:
- scale-invariant by construction
- requires explicit decisions for zero values and extreme price ranges

Causal availability:
- available once both relevant observations are known

Compatibility with future tolerance architecture:
- possible, but not justified as the smallest valid root semantics

Risks of hidden assumptions:
- different normalizations produce different results
- zero or near-zero price conditions must be defined
- the repo evidence does not justify a single normalization choice

### 4.4 Candidate D — other transformation not yet justified by evidence

Examples include:
- percentile residuals of the gap distribution
- rolling z-scores
- ATR-based normalized gaps
- regime-conditioned scaling
- mixed absolute + relative transformation with an unproven reference rule

These are not recommended as the root semantic definition because they presume a tolerance architecture before the observation history is formalized.

### 4.5 Evidence-supported conclusion on gap semantics

The evidence supports the following minimal statement:
- the root object is a same-direction gap between two consecutive eligible confirmed swings, measured in a defined price space
- the exact transformation into absolute, relative, or normalized form is not determined by the current evidence and therefore remains a later decision layer

This means the smallest defensible semantic contract is: same-direction historical sequence + ordered gaps measured in a well-defined price domain. It does not yet freeze the specific gap formula.

## 5. Causal Availability Contract

### 5.1 Required causal rule

For a current eligible swing S_i, the future tolerance logic must only use observations that are available at the time S_i becomes eligible.

The underlying principle is:
- no future values may be used to define the tolerance used to evaluate S_i itself
- no later bars may retroactively create a historical observation that changes the legal set of prior values for S_i
- no same-direction observation after the current swing may participate in the tolerance used for that swing

### 5.2 Recommended contract

The minimal fully defensible contract is:

- let H_high be the set of eligible confirmed swing highs with eligibility_time <= current_swing_eligibility_time
- let H_low be the set of eligible confirmed swing lows with eligibility_time <= current_swing_eligibility_time
- the future tolerance calculation must operate only on the subset of prior observations in the same direction and earlier in canonical time order
- the current swing S_i itself is not included in the history used to evaluate S_i

This is the cleanest causal contract supported by the frozen Group A semantics and the frozen bar contract.

### 5.3 Exact availability question

For a current eligible swing S_i, the legally available observations are:
- previous same-direction eligible swings with eligibility_time < S_i.eligibility_time
- not the current swing itself
- not any later swing with eligibility_time > S_i.eligibility_time
- not any future bar or unseen confirmation

### 5.4 Canonical replay implications

Canonical replay ordering is already frozen as timestamp order with deterministic tie-break rules for equal timestamps. That resolves the ordering of legal historical observations.

Therefore, the availability rule should be defined in the following way:
- legal prior observation = an eligible confirmed swing whose canonical eligibility timestamp is less than the current swing’s eligibility timestamp
- if the same timestamp is possible, use the canonical replay ordering / stable index to provide deterministic precedence

### 5.5 What is not justified

The following should be explicitly rejected as a semantic rule unless human approval later chooses them:
- using values from the current swing in the tolerance history used to evaluate the current swing
- using a rolling history that is updated after the current swing is already considered
- using future bars or later zone members in the tolerance state used for a current decision

## 6. Current-Swing Inclusion Analysis

Two architectures are possible.

### 6.1 Architecture A — current swing excluded from tolerance history

Definition:
- a rule is computed from prior observations only
- current swing S_i does not contribute to the tolerance history used for the decision on S_i

Reasoning:
- this is the cleanest causal interpretation
- it avoids self-referential rule creation
- it is consistent with the frozen Group A causal model

Evidence basis:
- both the proposal and the research documents repeatedly refer to prior-observations-only semantics as the correct causal posture

Remaining limitation:
- the exact history depth and exact update timing remain unresolved

### 6.2 Architecture B — current swing included after measuring its distance

Definition:
- the current swing is used for membership evaluation, and the tolerance state may be updated using the current swing after the decision is made

Reasoning:
- this can be mathematically coherent if clearly separated into two stages: evaluate membership using prior state, then append current swing to history for future decisions

Critical difference:
- this is not the same as including the current swing in the tolerance used to decide itself

This is a valid research distinction, but it must be specified as a two-phase update model:
1. evaluate on prior history
2. append current swing to history only after the decision is completed

The dataflow requirement is:
- the decision on S_i must not depend on S_i itself
- historical state update may occur after the decision is committed

### 6.3 Conclusion

The evidence supports the following causal principle:
- the current swing must not be used to evaluate itself
- the current swing may be appended to the historical state after the decision is made, but only under a formal post-decision update contract

This is the clearest minimal causal semantics supported by the current evidence.

## 7. Insufficient-History Analysis

This section does not invent a fallback tolerance. It describes what the evidence can and cannot determine.

### 7.1 Zero prior observations

State:
- no earlier same-direction eligible swing exists

Legality:
- no tolerance calculation is legally meaningful in the current evidence if the rule requires a historical same-direction gap sequence

Meaning:
- the system cannot define a meaningful same-direction tolerance before a prior observation exists

### 7.2 One prior observation

State:
- one prior eligible same-direction swing exists

Legality:
- a historical gap exists if a prior observation is available, but the gap set is extremely small and likely under-powered for a robust tolerance statistic

Meaning:
- the data may support a minimum-history threshold concept, but the evidence is insufficient to select a value

### 7.3 Two prior observations

State:
- two prior same-direction eligible swings exist

Legality:
- a single gap is available for the current sequence

Meaning:
- a tolerance statistic may be available mathematically, but the evidence does not establish whether this is the minimum meaningful threshold for future cluster creation

### 7.4 More observations

State:
- more than two prior same-direction observations already exist

Meaning:
- the future tolerance statistic may become more statistically meaningful, but the exact required minimum depth is not yet established by evidence

### 7.5 Defensible conclusion

The evidence supports this minimal statement:
- tolerance is not legally available before any prior same-direction observation exists
- the exact minimum number of prior observations required for a meaningful tolerance remains unresolved and requires either empirical evidence or explicit human decision

This is an analysis-only conclusion. It does not authorize any chosen threshold.

## 8. Dataset Evidence

This section separates the evidence by type.

### 8.1 Descriptive evidence

The following are descriptive and supported by existing research:
- eligible swing highs: 78
- eligible swing lows: 68
- high and low sequences are materially different
- same-direction spacing exists in both high and low streams
- a mixed high+low analysis is not valid for same-direction calibration
- the gap distribution has a small central mass and a large long tail

This evidence establishes that the sequence is real and directionally structured, but it does not identify a final tolerance formula.

### 8.2 Methodological evidence

The following are methodological conclusions that are important for the semantic contract:
- same-direction sequences must be separated by direction
- future Group B semantics must not inherit the invalid mixed-direction analysis
- the pipeline must operate in canonical replay order
- the current swing must not be treated as prior evidence for itself

These conclusions are robust and directly support the semantic contract recommendation below.

### 8.3 Calibration evidence

The following are calibration-related observations and must not be mistaken for final rule choices:
- absolute median gaps are roughly 33.78 for highs and 35.85 for lows
- p90 / p95 values are much larger, indicating long-tail spacing
- the mixed family is not demonstrably invalid, but it is often A-dominant and therefore weak as an informative calibration surface

This evidence is useful for understanding the structure of the sequence, but it does not justify a final tolerance family, a final window, or a final threshold.

## 9. Recommended Semantic Contract

The minimal semantic contract that is most defensible from the evidence is:

1. Observation set
- use only eligible confirmed swings of the same direction
- separate high and low streams permanently
- no cross-direction observation mixing

2. Prior observation definition
- a prior observation for swing S_i is any same-direction eligible confirmed swing with canonical eligibility timestamp strictly less than S_i.eligibility_time

3. Gap definition
- the root gap is a same-direction gap between two eligible confirmed swings, expressed in a well-defined price-domain quantity
- the exact absolute-vs-relative transform is not resolved by the evidence, so it remains a later decision layer

4. Causal availability timing
- legal prior observations are those available before the current swing is evaluated in canonical replay order
- later swings, later bars, and later zone members are not legal prior evidence for the current swing

5. Current swing inclusion
- the current swing must not participate in the tolerance history used to evaluate itself
- post-decision state updates may append the current swing to future history only under an explicitly defined two-phase semantics

6. Insufficient-history state
- before any prior same-direction observation exists, no historical tolerance based on same-direction gaps is legally available
- a smaller or larger minimum depth for a future tolerance statistic remains unresolved and requires either empirical study or human decision

### Recommended evidence basis

- evidence basis: frozen Group A causality; frozen bar contract; canonical dataset structure; research separation of highs/lows; invalidation of mixed high+low calibration
- confidence: moderate for the semantic contract itself
- remaining limitation: the exact numerical gap transform and minimum history threshold remain unresolved and cannot be justified from repository evidence alone

## 10. Human Decisions Required

These are the genuine governance decisions that cannot be established by current evidence alone:

1. whether the future gap quantity is absolute, relative, normalized, or another explicit price-domain transform
2. whether the future tolerance calculation uses a count-based or time-based window
3. the minimum number of prior observations required before a future tolerance statistic is treated as valid
4. whether the current swing may be appended to history after its decision is made, or whether the state update occurs only in a later step
5. whether any future tolerance statistic is allowed to use a reference price that is not already an explicit project-defined quantity

These are not technical details to invent. They are governance decisions the repository evidence cannot determine by itself.

## 11. Dependency Impact

This semantic contract unlocks the following downstream decisions:
- future tolerance family and formula selection
- future rolling window semantics
- future membership distance decision
- future zone creation trigger logic
- future center and geometry definition
- future overlap resolution and immutable historical state decisions

The following remain blocked until the semantic contract is approved:
- exact tolerance formula selection
- exact future membership algorithm
- exact creation threshold
- exact center lifecycle and geometry
- exact overlap policy
- exact replay-safe historical state model

## 12. Governance Status

- Group A remains frozen.
- 15m bar contract remains frozen.
- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- No production code changed.
- No tests changed.
- No tolerance formula was frozen.
- No trading behavior changed.

## Final Architectural Conclusion

The evidence supports a conservative and defensible semantic foundation for future Group B tolerance logic:

- use only eligible confirmed swings of the same direction
- maintain separate high and low sequences
- define legal prior observations using eligibility time in canonical replay order
- exclude the current swing from the tolerance history used to evaluate itself
- do not define a final gap formula or minimum-history threshold without additional explicit governance or empirical design work

This is the smallest semantic contract that is both causally valid and consistent with the frozen Group A and frozen bar inputs.
