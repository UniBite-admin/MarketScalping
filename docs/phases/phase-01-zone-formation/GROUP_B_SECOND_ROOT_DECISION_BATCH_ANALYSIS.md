# Group B Second Root-Decision Batch Analysis

## Status

- Group B: NOT FROZEN
- analysis-only
- no production implementation
- no production behavior change
- no Group B numerical parameter is frozen
- this document addresses the second root-decision batch only

## 1. Objective

This analysis addresses the second root-decision batch for Group B:

1. gap representation
2. tolerance family
3. history/window semantics
4. minimum-history requirement
5. insufficient-history behavior
6. tolerance update timing
7. causal stability of the proposed tolerance architecture

This is not a final Group B freeze. It is a repository-grounded design audit of the next technical layer after the semantics analysis already established:

- only eligible confirmed swings are observations
- highs and lows are separate sequences
- prior observations are ordered by eligibility time in canonical replay order
- the current swing is excluded from the history used to evaluate itself
- Group B stays not frozen

The analysis therefore does not ask, "Which parameter makes the strategy profitable?" It asks the narrower and more relevant question:

"Which tolerance model is the simplest defensible foundation that can be defined causally, deterministically, reproducibly, and without arbitrary assumptions?"

## 2. Governing Evidence

Frozen and governing:

- Group A swing definition remains frozen.
- 15-minute operational bar contract remains frozen and human-approved.
- event exactly at bar_end belongs to the next bar.
- closed bars are immutable.
- incomplete trailing bars are excluded from finalized evaluation.
- final partial bar at dataset end is discarded.
- causality remains no look-ahead.

Research-supported and non-frozen:

- same-direction highs and lows are structurally distinct
- a mixed same-direction + cross-direction or high+low calibration is not a valid basis for same-direction tolerance design
- low A/r values fragment membership, larger A/r values broaden membership
- the stability surface is transitional, not unique
- some apparent 100% stability is often a byproduct of an inactive component rather than a meaningful structural result

Descriptive dataset evidence (not calibration decisions):

- HIGH: count 78; median absolute same-direction gap ≈ 33.78; p90 ≈ 553.87; p95 ≈ 1532.47; median relative gap ≈ 0.00354; p90 relative gap ≈ 0.06728
- LOW: count 68; median absolute same-direction gap ≈ 35.85; p90 ≈ 589.51; p95 ≈ 1781.97; median relative gap ≈ 0.00420; p90 relative gap ≈ 0.07183

This evidence shows the sequence has structure, but it does not justify a final parameter or a final tolerance family.

## 3. Gap Representation Analysis

### A. Absolute price gap

Definition:

- for two same-direction eligible swings with prices P_i and P_j:
  - gap_abs = |P_i - P_j|
- when applied natively to the same-direction prior-history stream, this is the difference between historical eligible swing prices in absolute price units

Units:

- price units of the asset (for BTC-EUR: EUR)

Dependence on price level:

- directly scale-dependent on BTC price level
- highly sensitive to price regime and absolute market value

Sensitivity to BTC regime:

- a fixed absolute tolerance is not regime-adaptive
- it can become too tight in a high-price regime and too loose in a low-price regime

Comparability between highs and lows:

- good within a single direction stream because all values are in the same price space
- cross-direction comparability is limited unless a common normalized reference is chosen

Causal availability:

- directly available when both relevant swings are already eligible in canonical replay order

Deterministic replay compatibility:

- strong
- no hidden state, no dependence on future information, no ambiguous pricing source beyond the frozen bar contract

Advantages:

- simplest and clearest representation
- easy to reason about
- easy to test and audit
- mathematically transparent
- compatible with a later tolerance threshold defined in the same price units

Limitations:

- not scale-adaptive
- can unfairly favor or penalize different price regimes
- may be too blunt if the project expects a single tolerance across a large historical span

Assessment:

- simplest defensible root representation
- best foundation when the team wants no hidden normalization assumptions

### B. Relative price gap

Definition:

- gap_rel = |P_i - P_j| / R
- where R must be explicitly defined: previous price, current price, zone center, previous mean, or some other reference

Units:

- dimensionless ratio if R is in the same price units

Dependence on price level:

- reduced dependence on raw price level if R is chosen appropriately
- but the rule depends entirely on the chosen denominator and thus carries hidden design assumptions

Sensitivity to BTC regime:

- can adapt across price regimes if R is robust
- but the dependence on denominator selection is not justified by repository evidence alone

Comparability between highs and lows:

- potentially better for scale normalization
- but only if the denominator is consistently defined and directionally neutral

Causal availability:

- available when the numerator and the chosen reference are both causal and already known to the system

Deterministic replay compatibility:

- possible, but only if the reference price is explicitly defined and stable

Advantages:

- more scale-normalized than absolute gaps
- can be useful when a price-level-independent representation is required

Limitations:

- denominator is arbitrary unless the project explicitly defines it
- introduces a second design choice before the tolerance family is even approved
- can become confusing or inconsistent when used with same-direction historical windows

Assessment:

- a valid mathematical representation, but not the simplest defensible foundation because the denominator itself is an unresolved design decision

### C. Mixed representation

Definition:

- a common pattern is distance <= max(A, r * reference_price)
- this mixes an absolute floor A and a relative term r * reference_price

Units:

- mixed; absolute units plus a relative multiplier applied to a reference price

Dependence on price level:

- more stable than absolute-only, but the absolute term may dominate in practice
- the effective tolerance can become piecewise and regime-sensitive

Sensitivity to BTC regime:

- can respond to high-price regimes, but the absolute term often makes the family blunt
- structural behavior may become dominated by one term

Comparability between highs and lows:

- possible, but the chosen absolute and relative terms may behave differently by direction

Causal availability:

- available provided both terms are defined using only prior legal observations or fixed reference inputs

Deterministic replay compatibility:

- strong if the reference and trigger sequence are fixed

Advantages:

- flexible and easy to tune superficially
- can approximate a dynamic band with relatively few parameters

Limitations:

- the fixed-pair surface is blunt and often inactive in one regime
- the literature of mixed families does not prove a uniquely justified pair
- the research already showed the family is structurally workable but not uniquely justified
- there is real risk of false precision: the pair looks specific while it is merely a chosen static abstraction

Assessment:

- useful as a research family, not as the smallest defensible root contract
- not recommended as the primary design foundation because it composes two unresolved modeling assumptions into one rule

### D. Other representation supported by repository evidence

Unsupported by the current evidence:

- ATR-normalized distance
- percentile residual tolerance
- z-score of observed gaps
- regime-conditioned scaling
- any representation that depends on a future value or a non-causal reference state

These are not justified as the smallest defensible root contract because they add complexity without clarifying the underlying root means.

### E. Recommended gap representation

The simplest defensible root representation is:

- same-direction absolute price gap measured between two eligible confirmed swings in the same direction
- or, at minimum, a gap defined in a clearly stated price domain with no hidden normalization assumptions

This is the most conservative and repository-grounded basis because it does not invent a reference price or a non-obvious normalization scheme before the tolerance family is approved.

When more scale normalization is later desired, the project may add a relative or mixed layer deliberately and with explicit human approval. That is a downstream design decision, not a root contract.

## 4. Tolerance Family Analysis

### A. Fixed absolute tolerance

Required inputs:

- a single fixed tolerance value in price units
- direction-specific stream or shared stream, depending on design intent

Causal availability:

- fully causal if fixed before replay

Determinism:

- very strong

Scale adaptation:

- poor

Hyperparameters:

- one tolerance value, not necessarily a family of parameters

Hidden state:

- none

Historical zones changing due to future observations:

- not by design, unless the algorithm reassigns by a future state machine that is not frozen

Testability on current dataset:

- fully testable

Evidence support:

- simple, but not structurally strong enough to justify being the default foundation for a same-direction zone architecture

Assessment:

- easy and valid but too brittle as the primary architecture for BTC over a long regime span

### B. Fixed relative tolerance

Required inputs:

- a fixed ratio and an explicit reference price policy

Causal availability:

- possible if the reference is causal and fixed

Determinism:

- strong if the reference is explicit

Scale adaptation:

- better than absolute-only if the reference is well-defined

Hyperparameters:

- at least a ratio and an explicit reference rule

Hidden state:

- low, unless the reference is derived from nontrivial history

Historical zones changing because future observations arrive:

- possible if the zone geometry or center is mutable

Testability on the current dataset:

- testable, but the reference rule is not justified by the repo evidence

Evidence support:

- weak as a first-principles foundation because a denominator is not already frozen by the project

Assessment:

- mathematically valid but not the simplest defensible root choice

### C. Mixed absolute + relative tolerance

Required inputs:

- absolute floor A
- relative multiplier r
- explicit reference rule for the relative component

Causal availability:

- fully causal if all inputs are fixed prior to evaluation

Determinism:

- strong

Scale adaptation:

- moderate

Hyperparameters:

- at least two structural parameters plus a reference rule

Hidden state:

- low if static, but a hidden dependence on active range can still creep in

Historical zones changing because future observations arrive:

- possible if applied to evolving zone state or if the state is mutable

Testability on the current dataset:

- good

Evidence support:

- moderate; research shows structural usability but not unique justification

Assessment:

- acceptable as a secondary family for research, not the simplest defensible foundation for the first root batch

### D. Rolling or adaptive tolerance derived from prior observed gaps

Required inputs:

- the same-direction observation stream
- the gap set from legal prior observations
- a statistic such as median, mean, or other robust central measure
- an explicit history/window rule

Causal availability:

- strong if based only on legally prior observations and updated only after the current swing is evaluated

Determinism:

- strong if state update ordering is explicit

Scale adaptation:

- good, because it derives from observed spacing rather than an exogenous price regime assumption

Hyperparameters:

- window size, minimum depth, and update rule if any

Hidden state:

- yes, but this is not a flaw by itself; it is the nature of a rolling statistic

Historical zones changing because future observations arrive:

- yes, if the tolerance state is updated from future observations or if the historical zone state is mutable

Testability on the current dataset:

- strong, if implemented in a deterministic, append-only state machine

Evidence support:

- this is the best-supported architecture from the repo’s research posture because it reflects actual same-direction spacing without forcing an arbitrary reference price or static pair

Assessment:

- the best candidate for a minimal causal foundation, but only if the update-order semantics are made explicit and kept prior-only

### E. ATR-based tolerance

Required inputs:

- a bar or price series from the frozen 15-minute bar contract
- a time period for ATR calculation
- a valid prior-price reference series

Causal availability:

- possible, but only if all of the above are explicitly frozen and causal

Determinism:

- strong if the ATR definition is frozen

Scale adaptation:

- good

Hyperparameters:

- timeframe, smoothing method, initial seed, and interpretation of prior close data

Hidden state:

- definite moving-state requirement, more than the minimal root contract calls for

Historical zones changing because future observations arrive:

- yes, by design

Testability on the current dataset:

- possible, but not with the project’s current Phase 1 requirements

Evidence support:

- weak as a Phase 1 root architecture because the project has not frozen a specific ATR definition or timeframe semantics from authoritative project rules

Assessment:

- not recommended as the simplest defensible foundation because it introduces more moving parts than the root problem warrants

### F. Best-supported family recommendation

The simplest defensible family is not a static A/r pair and not an ATR-based rule. It is:

- a same-direction rolling tolerance derived from prior observed same-direction gaps
- with the base statistic chosen from a robust central measure and evaluated only on legal prior observations
- implemented in a deterministic, prior-only update model

This remains not frozen, but it is the simplest foundation that is conceptually grounded in the repo evidence.

## 5. History / Window Semantics

### A. Preferred semantics

The legally valid historical observation set for the tolerance state is:

- all eligible confirmed swings of the same direction
- sorted by eligibility timestamp in canonical replay order
- with the current swing excluded from the set used to evaluate itself
- with future values excluded from the current evaluation

This is the causal principle that makes the tolerance architecture reproducible.

### B. Window semantics

A window can be defined in one of two ways:

- count-based: keep the last N legal same-direction gaps
- time-based: keep legal gaps whose observation time falls within some defined interval

Both are mathematically valid, but the project must not choose either casually. A count-based window is the cleaner root semantics because it is simpler to reason about and easier to test deterministically.

The repository evidence does not justify a final count or time horizon. Therefore the right conclusion is:

- a window is required,
- the exact window is unresolved,
- the minimal root decision is to define the window as a legal prior-observation stream, not to pick a final N or time bucket before the architecture is approved

### C. Minimum-history requirement

This is an unavoidable design question, but it is not a parameter to invent prematurely.

A tolerance based on historical gaps is not legally meaningful before there is at least one legal prior same-direction observation. The exact threshold for a useful tolerance statistic remains unresolved.

Minimal safe statement:

- 0 prior observations: no same-direction tolerance is valid
- 1 prior observation: a single gap exists, but this is a minimal and potentially unstable basis
- 2 or more prior observations: data becomes more robust, but still not enough evidence to freeze a final threshold

The correct design treatment is therefore:

- define a minimum-history gate as an architectural requirement
- do not pick a final integer threshold without further evidence or explicit human approval

### D. Insufficient-history behavior

Across all tolerance families, the correct root behavior is:

- do not fabricate a tolerance value from empty or insufficient history
- do not use future observations
- do not silently use a static fallback if the fallback is not explicitly approved as part of the architecture
- a conservative default is to hold the tolerance invalid until enough legal prior observations exist

This is the cleanest and least arbitrary behavior because it preserves causality and leaves all numerical choices for a later, explicitly governed stage.

## 6. Tolerance Update Timing

### A. Correct causal ordering

The simplest defensible update ordering is:

1. current swing becomes eligible in canonical replay order
2. the tolerance state is evaluated using only prior legal observations
3. the membership decision is made using that prior-only tolerance
4. the current swing is appended to the same-direction history only after the decision is completed

This ordering avoids self-reference and preserves no-look-ahead semantics.

### B. Forbidden update ordering

The following must be rejected unless explicitly approved later:

- inserting the current swing into history before evaluating its own membership decision
- using future swings to set the tolerance used for the present swing
- updating zone geometry or site center from a value that depends on the current candidate before the decision is finalized
- changing the historical tolerance state retroactively in a way that reinterprets already-committed earlier decisions

### C. Stability requirement

A tolerance architecture is causally stable only if:

- the same legal event sequence yields the same tolerance history
- the update semantics are append-only, not retroactive
- the same-direction state remains ordered by eligibility time
- a later observation cannot reclassify the current swing as using future knowledge

This is the practical meaning of “causal stability” in a replay-safe system.

## 7. Causal Stability of the Proposed Tolerance Architecture

### A. Best candidate architecture

The best-supported candidate is:

- same-direction prior-observations-only rolling tolerance derived from prior gap history
- no mixed-direction or cross-direction state
- explicit append-only update after each current decision
- separate high and low state machines
- no future-value contamination

This architecture is the simplest one that preserves the frozen causal rules and the repo’s evidence about same-direction separation.

### B. Why it is stable

It is stable because:

- the observation stream is deterministic and ordered by eligibility time
- the gap object is defined on legal prior observations only
- historical membership does not depend on events that were not yet eligible
- the current swing does not evaluate itself against its own value
- the system does not need hidden market-state assumptions

### C. Why more complex variants are weaker

More complex alternatives are weaker because they add assumptions without being clearly justified by the repo evidence:

- ATR: adds time-window and smoothing assumptions beyond the current phase requirements
- relative denominator: requires an explicit denominator policy that is not already frozen
- mixed A/r pair: appears precise but often hides a blunt floor or a dead region that is not structurally informative
- adaptive rules with hidden state: can appear robust but often become difficult to reason about during replay and audit

### D. The principle to preserve

The architecture must not be measured by how adaptive it seems. It must be measured by whether it is:

- reproducible
- deterministic
- causal
- simple enough to audit
- supported by project evidence without inventing missing semantics

This is why the minimal, prior-only, same-direction rolling tolerance remains the strongest candidate: it is adaptive enough to reflect actual spacing, but not so complex that it requires a large hidden state machine or arbitrary reference rules.

## 8. Decision Status

### A. Proven / strongly supported

- same-direction-only observation streams are required
- highs and lows should remain separate
- prior observations must be ordered by eligibility time in canonical replay order
- the current swing must not evaluate itself using its own value
- tolerance derived from legal prior same-direction gaps is the strongest root candidate

### B. Research evidence / design direction

- absolute gap is the simplest sensible root representation
- rolling prior-gap tolerance is the strongest candidate family
- count-based window semantics are simpler than time-based semantics for the first implementation contract
- minimum-history behavior must be explicit and conservative, but the final threshold is not proven

### C. Unknown / requires human approval or further evidence

- exact tolerance statistic to use (median, mean, robust central measure, or another rule)
- exact history window size or minimum count
- exact insufficient-history fallback policy
- exact update timing for state mutation after each decision
- exact relative or mixed representation if the team chooses to normalize later
- exact final tolerance family to freeze
- final zone membership and geometry rules downstream of the tolerance model

## 9. Recommended Minimal Foundation

The simplest defensible foundation for Group B is:

1. same-direction observations only
2. separate high and low histories
3. absolute price-gap basis as the default root representation unless a relative or mixed representation is explicitly chosen later
4. rolling tolerance computed from prior legal same-direction gaps only
5. prior-only causal update ordering
6. no tolerance value before enough legal history exists
7. no final parameter or numerical threshold frozen in this phase

This is the smallest architecture that fits the repository evidence without inventing a hidden reference rule, arbitrary multiplier, or ungrounded ATR definition.

## 10. Final Conclusion

The second root-decision batch does not support freezing a final tolerance formula. It does support narrowing the design to a minimal, causal, replay-safe architecture:

- same-direction historical gap state
- separate high and low streams
- prior-observations-only update ordering
- absolute price-gap as the simplest root representation unless explicit normalization is later approved
- rolling tolerance derived from the same-direction gap stream
- insufficient-history behavior that refuses to fabricate a tolerance value

This is the simplest defensible foundation for further Group B work, and it remains a design direction rather than a final freeze.
