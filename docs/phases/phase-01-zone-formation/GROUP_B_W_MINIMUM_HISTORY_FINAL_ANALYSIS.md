# Group B W / Minimum-History Final Analysis

## Status

- Group B: NOT FROZEN
- research-only bounded decision analysis
- no production implementation
- no executable tests modified
- no freeze of W
- no freeze of minimum-history policy
- no numerical tolerance parameter frozen

## 1. Objective

This document is the final bounded decision analysis for the unresolved Group B tolerance-history semantics.

The objective is not to find new architectures or run a broad search. It is to determine whether the existing evidence is sufficient to:

A. define the semantics of W
B. determine a unique W
C. define minimum-history behavior
D. determine whether any of those decisions require explicit human approval

The governing principle is strict evidence discipline:

- if the evidence uniquely determines the rule, the rule may be stated
- if the evidence does not uniquely determine the rule, the decision remains unresolved
- if the evidence is insufficient, the decision is HUMAN DECISION REQUIRED

## 2. Authoritative evidence

### FROZEN

- Group A swing semantics: FROZEN / HUMAN APPROVED
- 15-minute UTC bar contract: FROZEN / HUMAN APPROVED
- canonical replay ordering and deterministic event sequencing remain authoritative
- same-direction treatment remains required
- no look-ahead is allowed
- current swing may not contribute to the tolerance used to evaluate itself

### SUPPORTED

- same-direction high and low streams are distinct
- same-direction absolute price gaps are the currently supported gap representation
- median is the strongest currently supported statistic for prior-gap tolerance
- fixed-count rolling history is the strongest supported bounded-memory architecture
- time-based rolling history is not yet justified
- current evidence supports a prior-only causal gap history

### UNRESOLVED

- exact W
- exact minimum-history policy
- exact historical snapshot semantics for tolerance used at evaluation time
- exact update timing after evaluation
- whether a later human-approved W should be fixed-count or expanding

## 3. Current supported mathematical foundation

For the currently supported same-direction sequence:

- S_1, S_2, ..., S_i are eligible same-direction swings in canonical replay order
- consecutive legal same-direction gaps are:
  - g_j = abs(S_j - S_(j-1))
- the gap stream is direction-specific and is not mixed across highs and lows
- future or unconfirmed swings are not legal observations for current evaluation

For the current swing S_i:

- T_i(W) = median(last W legal prior same-direction gaps)

This is the currently supported mathematical form and not a frozen implementation contract.

### Required distinction

- swing count: number of legal swings in the same-direction stream
- gap count: number of legal consecutive same-direction gaps in that stream
- observation order: canonical eligibility order of swings
- eligibility time: time the swing becomes legally usable downstream
- evaluation time: time the current swing is evaluated using prior legal history
- tolerance calculation time: the moment the median is computed from the prior gap window
- append/update time: the moment the newly available gap is appended to the legal prior history after the current decision

### Supported semantics

- W counts legal prior gaps, not swings
- the current swing is excluded from the history used to evaluate itself
- the tolerance for S_i is computed from history strictly before the current evaluation
- future observations cannot change the tolerance snapshot used for S_i
- the historical record is append-only after evaluation for future legal decisions

### Not supported

- a tolerance that uses the current swing value to define its own acceptance rule
- a tolerance calculated from future swings
- a tolerance that “revises” earlier past decisions after the fact
- a time-based fixed-interval window that has not been justified by the project evidence

## 4. W semantic analysis

### 4.1 Candidate interpretations

#### Interpretation 1: recent same-direction structural memory

SUPPORTED in principle.

Evidence supporting it:

- same-direction spacing contains real structure
- the same-direction gap process is not random
- the project evidence already supports a bounded rolling prior-gap architecture

Evidence against it:

- the current project evidence does not specify what recent means in a statistically or structurally justified sense
- no unique W is established as the correct memory horizon

Testability:

- testable as a structural design concept
- not testable as a unique final value from the current evidence alone

Reproducible rule?

- no unique W-selection rule is justified by the existing evidence

Conclusion:

- W SEMANTIC MEANING = PARTIALLY SUPPORTED

#### Interpretation 2: local spacing-regime memory

PARTIALLY SUPPORTED.

Evidence supporting it:

- gap spacing shows periods of different local scale and long-tail distribution
- a rolling window would naturally follow a recent spacing regime

Evidence against it:

- the evidence does not define what counts as a “regime” or how long it should persist before it becomes a binding architecture decision
- no unique W emerges from the observed regime durations

Testability:

- possible as a conceptual description
- not unique enough for a final W rule

Reproducible rule?

- no

Conclusion:

- W SEMANTIC MEANING = PARTIALLY SUPPORTED

#### Interpretation 3: adaptation horizon

PARTIALLY SUPPORTED.

Evidence supporting it:

- the bounded rolling median naturally adapts to recent same-direction behavior
- shorter windows adapt faster; longer windows adapt more slowly

Evidence against it:

- the project evidence does not justify a unique adaptation horizon or window that matches an objective regime transition boundary

Testability:

- yes in a descriptive sense
- no in the sense of a unique justified W

Reproducible rule?

- no

Conclusion:

- W SEMANTIC MEANING = PARTIALLY SUPPORTED

#### Interpretation 4: robust local scale estimate

SUPPORTED as a descriptive interpretation.

Evidence supporting it:

- median is robust under outlier-heavy same-direction gaps
- the same-direction gap distribution has a long tail, which is exactly where the median is more robust than the mean
- a bounded rolling median is a natural local scale estimator for recent same-direction gap structure

Evidence against it:

- it does not determine a unique W period
- local scale estimate still requires a definition of “local” and a minimum amount of evidence

Testability:

- yes, but only descriptively

Reproducible rule?

- no unique W derived from current evidence

Conclusion:

- W SEMANTIC MEANING = SUPPORTED as a general interpretation
- but not as a unique W-selection rule

### Final classification

`W SEMANTIC MEANING = PARTIALLY SUPPORTED`

The evidence supports the idea that W is a bounded local scale / recent-structure memory parameter.

It does not support a unique, objective, reproducible W meaning to the level of an exact numeric value.

## 5. Data-derived-W analysis

The central question is whether the dataset itself uniquely determines one W without tuning against downstream zone outcomes.

### Considered objective evidence

Possible objective properties:

- persistence length of gap-scale behavior
- duration of identifiable local spacing regimes
- stability of local gap distributions
- measurable transition behavior between compressed and expanded spacing
- observation density

### Evidence assessment

The project evidence shows that:

- same-direction gap behavior is structured and long-tailed
- there are periods with different local spacing behavior
- the median remains more robust than the mean under those conditions

However, the evidence does not establish a documented objective rule that says:

- W must equal X because the historical gap process has a stable regime length of exactly X
- W must equal X because the local distribution becomes stable after X observations
- W must equal X because the same-direction transitions can be objectively identified with a unique threshold

This is the key result: the repository evidence supports the existence of time-varying local structure, but not a uniquely justified W-selection mechanism.

### Conclusion

`UNIQUE W FROM EXISTING EVIDENCE: NO`

This conclusion is required because the project does not establish a reproducible rule that uniquely determines W from the historical gap stream without either:

- hidden tuning
- an unsupported statistical criterion
- downstream optimization pressure

No criterion may be invented merely to produce a preferred number.

## 6. Bounded structural probe

### RESEARCH PROBE — NOT A DECISION

A small structural probe is allowed only to test whether different bounded windows exhibit materially different behavior in the same historical data stream.

The purpose is descriptive only.

### Probe design

Use a very small set of bounded windows, such as:

- a short window
- a medium window
- a longer window

This is not a parameter sweep and not a search for an optimum.

### What the probe is intended to measure

- tolerance stability
- adaptation speed
- outlier sensitivity
- outlier removal
- sparse-history behavior
- HIGH vs LOW differences
- chronological behavior
- membership sensitivity

### What the evidence already supports

- short windows adapt faster but are more sensitive to extreme outliers
- medium windows provide a better compromise between stability and responsiveness
- longer windows smooth more but can become stale and under-reactive
- the exact crossover point is not uniquely justified by the dataset alone

### Required interpretation

All results are only descriptive and must remain labeled:

`RESEARCH PROBE — NOT A DECISION`

The probe does not establish a unique W. It only demonstrates that different W values produce materially different behavior, which is exactly why the project must not invent one without evidence or human approval.

## 7. Minimum-history analysis

The problem is to determine the correct behavior for early legal gap history.

### State 0 — no prior legal gap

- mathematically impossible to compute a median over prior legal gaps
- tolerance is not defined
- this state is causally valid and should not be treated as a numerical tolerance

### State 1 — one prior legal gap

- the median is mathematically defined
- but the tolerance is not statistically robust
- using a single observed gap as a tolerance is too weak to justify a stable operational rule

### State 2 — two prior legal gaps

- median is defined
- still highly sensitive to a single extreme gap
- still not enough to claim a stable local scale estimate

### State 3+ — increasing prior history

- median becomes more meaningful as the set grows
- robustness improves as local legal history accumulates
- but the evidence still does not justify an exact minimum threshold

### Policy options

#### Policy A: use whatever legal prior history exists until W is reached

Mathematical validity:

- valid

Causal validity:

- valid as a historical state update rule

Determinism:

- valid

Stability:

- weak at early stages

Risk of arbitrary early behavior:

- moderate, because early tolerance values may be driven by a tiny sample

Assessment:

- mathematically valid but not statistically adequate in the early-sample range

#### Policy B: no tolerance exists until W legal gaps exist

Mathematical validity:

- valid as a design gate

Causal validity:

- valid

Determinism:

- valid

Stability:

- stronger because it avoids premature tolerance values

Risk of arbitrary early behavior:

- low

Assessment:

- cleaner governance but may delay tolerance availability unnecessarily

#### Policy C: another policy

Not supported by current evidence.

### Final classification

`MINIMUM-HISTORY POLICY = HUMAN DECISION REQUIRED`

The evidence supports the principle that the early-history case must be handled explicitly. It does not uniquely justify a specific policy.

## 8. Mathematical definability vs statistical adequacy

This distinction is essential.

### Mathematical definability

- a median of one value is mathematically defined
- a median of two values is mathematically defined
- a median of three or more values is mathematically defined

### Statistical adequacy

- a single value is not a robust estimate of local gap scale
- a very small sample is highly sensitive to outliers
- a bounded W may be more structurally meaningful than a tiny sample, but the evidence does not say which threshold is objectively correct

This means:

- mathematical definability does not imply operational adequacy
- a minimum-history rule is not merely an implementation detail; it is a decision about when the tolerance becomes sufficiently representative
- the project evidence supports the need for a gate, but not the exact threshold

## 9. Human decision boundary

The unresolved items must be classified by whether the evidence can support a clear decision or whether a human choice is needed.

### A. Agent can decide from evidence

None of the final W or minimum-history semantics are uniquely determined by the existing evidence.

### B. Agent can recommend but human must approve

The agent can recommend:

- fixed-count rolling median remains the strongest bounded-memory architecture
- median remains the strongest supported statistic
- a time-based window remains under-justified
- W should remain a bounded historical-memory parameter, not a free-form ad hoc choice

These are recommendations only. They do not constitute final numeric freeze decisions.

### C. Human must decide

The following require explicit human decision:

1. exact W value
2. whether W is interpreted as a recent structural memory, adaptation horizon, or robust local scale estimate
3. whether the project wants a conservative minimum-history gate
4. whether early same-direction tolerance should be withheld until W observations exist
5. whether different W values are acceptable for HIGH and LOW streams
6. whether the chosen W should be treated as a later human-approved tuning parameter or a separately justified data-derived rule

### Why this matters

- without this decision, the system would be forced to invent a tolerance rule without evidence
- the project’s governance explicitly rejects that path
- the current evidence supports the architecture, not the exact parameter

## 10. Recommendation

### Recommended mathematical architecture

`T_i(W) = median(last W legal prior same-direction absolute gaps)`

This architecture remains the strongest supported bounded-memory design.

### Recommended W

`NO UNIQUE W JUSTIFIED`

The current evidence does not uniquely determine a W. A specific value would be a human-approved design decision, not an evidence-derived fact.

### Recommended minimum-history policy

`HUMAN DECISION REQUIRED`

The evidence supports the need for an explicit early-history policy, but not a unique threshold or rule.

### Why

- the same-direction gap process is structurally real and long-tailed
- median is more robust than mean in that process
- fixed-count rolling history is the strongest supported bounded-memory architecture
- however, the data does not establish a unique objective W or a unique minimum-history policy
- a specific numeric choice would be tuning, not evidence

## 11. Downstream freeze implications

If the human chooses W later, the choice must become a documented and frozen specification before downstream strategy evaluation.

This is required because:

- later backtest or clustering outcomes can appear attractive even when a W is selected by hindsight
- tuning W after seeing downstream results would create hidden parameter optimization
- the project’s governance forbids silent changes after the fact

Therefore:

- any future W decision must be recorded as a human-approved design decision
- any future minimum-history decision must be recorded with the same discipline
- the current evidence does not justify silent adoption of a numeric W

## 12. Remaining Group B blockers

The unresolved blockers remain:

- exact W
- exact minimum-history policy
- exact historical snapshot semantics for the tolerance used at evaluation time
- exact update timing for appending newly available gaps after decision
- whether the system should eventually use a different bounded-memory rule or an expanding rule
- whether the project will accept different W values for HIGH and LOW streams

These blockers remain unresolved and therefore prevent a Group B freeze.

## 13. Governance status

- Group A: FROZEN / HUMAN APPROVED
- 15-minute bar contract: FROZEN / HUMAN APPROVED
- Group B: NOT FROZEN
- Phase 2: NOT STARTED
- Production implementation: UNCHANGED
- Production tests: UNCHANGED
- W: NOT FROZEN unless explicitly and independently justified
- Minimum-history policy: NOT FROZEN unless explicitly and independently justified
- Numerical tolerance parameters: NOT FROZEN

## Final conclusion

The project evidence is sufficient to support the architecture, but not sufficient to determine a unique W or a unique minimum-history rule.

The correct bounded outcome is:

> The existing evidence supports the rolling prior-gap median architecture and the bounded-memory concept, but it does not uniquely determine W or minimum-history behavior. Those decisions therefore require explicit human approval.

This is the correct result under the project’s NO ASSUMPTIONS governance and the requirement to stop the decision when the evidence no longer uniquely determines it.
