# Group B Tolerance Architecture Comparison

## Status

- Group B: NOT FROZEN
- architecture comparison only
- no production implementation
- no production behavior change
- no numerical parameter frozen
- no final tolerance family frozen

## 1. Objective

This document performs an evidence-based comparative architecture check of the current Group B tolerance candidates:

A. Static absolute tolerance
B. Static relative tolerance
C. Static mixed absolute + relative tolerance
D. Rolling prior-gap absolute tolerance

The purpose is to determine whether the currently recommended architecture:

- rolling tolerance derived from prior same-direction absolute price gaps

has measurable structural justification over simpler static alternatives.

This is not a profitability test, not a parameter optimization pass, and not a freeze decision. It is a structural comparison only.

The comparison is constrained by the frozen Phase 1 governance:

- Group A remains frozen.
- the 15-minute operational bar contract remains frozen.
- Group B remains not frozen.
- the current bar contract and local-extrema semantics remain authoritative.
- no future data or future knowledge may be used.
- no new timeframe or dataset is introduced.

## 2. Candidate Architectures

### A. Static absolute tolerance

A tolerance of the form:

- T = A

where A is a fixed price-unit width.

The candidate is evaluated against the same-direction observation stream using a deterministic fixed threshold.

### B. Static relative tolerance

A tolerance of the form:

- T = r * R

where R is a chosen reference price and r is a fixed relative ratio.

This introduces a reference-price assumption that must be made explicit.

### C. Static mixed absolute + relative tolerance

A tolerance of the form:

- T = max(A, r * R)

or a closely related fixed mixed family.

This preserves a fixed absolute floor while allowing a relative component to activate when the reference price is large enough.

### D. Rolling prior-gap absolute tolerance

A tolerance derived from the historical same-direction gap stream using only prior legal observations:

- legal prior observation = eligible confirmed swing of the same direction whose eligibility timestamp is earlier than the current swing being evaluated
- current swing excluded from the history used to evaluate itself
- tolerance computed from prior observed same-direction absolute gaps

This is the architecture currently recommended as the simplest causal foundation, but it remains a design direction rather than a final freeze.

## 3. Existing Evidence

### 3.1 Frozen project evidence

The authoritative Phase 1 decisions remain:

- Group A swing semantics are frozen.
- the 15-minute operational bar contract is frozen.
- exact bar_end semantics are frozen.
- a bar becomes closed as replay passes bar_end.
- closed bars are immutable.
- incomplete trailing bars are excluded from finalized evaluation.
- the final partial bar at dataset end is discarded.
- no look-ahead is allowed.

### 3.2 Repository research evidence already established

The previous Group B work established the following structural findings:

- same-direction highs and lows must be analyzed separately
- mixed high+low or mixed-direction calibration is not valid for same-direction tolerance evidence
- static A/r families are usable as a structural surface but are not uniquely justified by the data
- low A/r values fragment membership
- larger A/r values merge or broaden membership
- the family surface contains transition regions and trade-off zones
- some apparent stabilization is caused by one component being inactive over much of the observed range rather than by an intrinsically strong architecture
- the rolling prior-gap idea is structurally more defensible than a static pair because it adapts to realized spacing instead of imposing an arbitrary absolute or relative scale upfront

### 3.3 Descriptive dataset evidence

The canonical BTC-EUR research data provides descriptive statistics only, not calibration decisions.

HIGH sequence:
- count: 78
- median absolute same-direction gap ≈ 33.78
- p90 ≈ 553.87
- p95 ≈ 1532.47
- median relative gap ≈ 0.00354
- p90 relative gap ≈ 0.06728

LOW sequence:
- count: 68
- median absolute same-direction gap ≈ 35.85
- p90 ≈ 589.51
- p95 ≈ 1781.97
- median relative gap ≈ 0.00420
- p90 relative gap ≈ 0.07183

These values show that the gap process is highly skewed and scale-sensitive; they do not demonstrate that any single static parameter is superior.

## 4. Comparative Method

This comparison used the existing project evidence and the already-established research artifacts only.

The method was intentionally narrow:

- no new dataset introduced
- no new timeframe introduced
- no new parameter sweep introduced
- no optimization for profitability
- no numerical winner chosen from a fresh search surface
- only the existing canonical BTC-EUR research evidence was used
- the same-direction, prior-only, causal principle was preserved across all comparisons
- the comparison emphasized structural properties rather than strategy performance

This means the comparison is a structural check, not an optimization exercise.

## 5. Results

### 5.1 Descriptive evidence

The descriptive evidence supports the claim that there is real structure in the same-direction spacing process.

- the absolute same-direction gap distribution has a central mass but a long tail
- the high and low streams differ materially
- relative gap scale also differs materially between highs and lows
- the distribution is not flat or trivial
- the project research already showed that a mixed family can be structurally workable but is not uniquely justified

This means the tolerance architecture is not a random choice. But the evidence still does not determine a single final family.

### 5.2 Methodological evidence

The methodological evidence is more important than the raw numbers here.

A. Static absolute tolerance
- structurally simple and deterministic
- easy to audit
- but it has poor price-scale adaptability
- its meaning changes materially as the BTC price level changes across time
- it does not naturally reflect the observed same-direction gap scale, which changes across historical segments

B. Static relative tolerance
- better on price-scale invariance in theory
- but it requires an explicit reference-price assumption
- the reference-price choice is not justified by the current repo evidence
- without a justified denominator, this architecture introduces hidden assumptions before the tolerance itself is resolved

C. Static mixed absolute + relative tolerance
- structurally usable and reproducible
- but the evidence shows parameter inactivity and term dominance
- the family often appears stable only because one component is inactive or nearly inactive in large segments of the observed range
- this is not proof of a robust or uniquely meaningful architecture

D. Rolling prior-gap absolute tolerance
- naturally follows the historical same-direction scale without assuming a fixed price-level regime
- provides a causal adaptation to observed gap history
- is consistent with the frozen requirement that current swing cannot evaluate itself using its own value
- is the only candidate in the list that directly reflects realized prior same-direction spacing while remaining within the project’s causal rules

### 5.3 Calibration evidence

This section is intentionally limited to structural calibration evidence already established by project research.

- the mixed family is not invalid, but it is not uniquely justified
- the static families are easier to explain but weaker as a structural representation of the observed same-direction gap process
- the rolling architecture is the most directly connected to the actual data-generating structure of the same-direction spacing process
- however, there is still not enough evidence to freeze a final window, final statistic, or final minimum-depth threshold

This is the critical distinction:

- the rolling architecture is the strongest structural candidate
- the evidence is not yet sufficient to declare it the final frozen Group B architecture

## 6. Architecture Comparison Matrix

| Dimension | Static absolute | Static relative | Static mixed A+r | Rolling prior-gap absolute |
| --- | --- | --- | --- | --- |
| Causal validity | Strong if fixed before replay | Strong if reference is causal and explicit | Strong if fixed before replay | Strong if based only on legal prior observations |
| Determinism | Strong | Strong if reference is fixed | Strong | Strong if update order is explicit |
| Price-scale sensitivity | High | Medium if reference is appropriate | Medium | Low to medium because it follows historical spacing |
| Regime adaptability | Poor | Moderate if denominator is chosen well | Moderate | Stronger because it follows observed gap history |
| High/low symmetry | Poor unless treated separately | Weak without explicit direction-specific reference | Mixed and often term-dominant | Strongest if direction-specific histories are maintained |
| Parameter dependence | High for fixed value choice | High because reference rule is another decision | High because both A and r matter | Medium because window and minimum depth still matter |
| Hidden assumptions | Low, but scale assumption remains | High due to denominator choice | High due to two fixed assumptions plus reference logic | Moderate, mainly in window and update semantics |
| State complexity | Low | Low | Low | Medium due to rolling historical state |
| Historical immutability | Strong | Strong | Strong if static | Strong if append-only and prior-only |
| Replay reproducibility | Strong | Strong | Strong | Strong if update order is defined exactly |
| Stability under small perturbations | Can be pathologically brittle across price ranges | Can be unstable if reference is mismatched | Can create dead zones or inactive ranges | More stable structurally because it follows realized gap history |
| Meaningful variation | Often blunt; may be too generic or too brittle | Can create arbitrary meaning from chosen denominator | Can be weak or dominated by one term | Best candidate for meaningful variation from actual prior gaps |
| Calibration without arbitrary assumptions | Weak | Weak because reference is arbitrary unless justified | Moderate but not uniquely justified | Moderate; still requires window and minimum-depth governance |

## 7. Interpretation

The evidence does not support treating the static alternatives as categorically superior. But it does distinguish the architectures structurally.

### Static absolute tolerance

This is the simplest possible architecture, and it is deterministic and causally valid. However, it is not structurally rich enough to represent the actual same-direction gap process over a changing BTC price scale. It can have the same meaning in one regime and a very different meaning in another regime without any adaptive mechanism. That is a serious limitation for a zone-formation layer that must remain meaningful across historical periods.

### Static relative tolerance

This architecture is conceptually attractive because it addresses scale dependence, but it creates a new unresolved design question: what reference price is legally and structurally valid? The repository does not freeze a denominator. That means relative tolerance does not yet have a clean, repo-grounded implementation contract. In other words, it appears more adaptive on paper, but with a hidden assumption that the project has not actually approved.

### Static mixed absolute + relative tolerance

This architecture is the most research-familiar of the static choices and is structurally workable, but the evidence suggests it is not uniquely justified. The earlier research already showed that it can produce inactive or dominant components, which undermines the notion that it is a clean or robust representation of the underlying process. It is valid as a research family, but it is not the strongest candidate for the minimal root architecture.

### Rolling prior-gap absolute tolerance

This architecture has the clearest structural connection to the actual observed pattern: same-direction gaps historically change, and a causal tolerance that observes prior same-direction gap scale matches that structure more naturally than a static tolerance does. It also respects the project’s causal rules and the requirement that the current swing cannot use itself as evidence.

The evidence strongly supports this claim:

- it is grounded in the actual gap distribution of prior same-direction swings
- it does not require a reference-price assumption
- it has a clear causal update order
- it is consistent with same-direction separation
- it is the most directly responsive to the underlying spacing process without inventing a new timeframe or an arbitrary normalization scheme

That said, the evidence still does not justify selecting the final rolling statistic, the exact window, or the minimum history threshold. Those are unresolved design decisions, not evidence-free implementation details.

## 8. Recommendation

### Evidence-based ranking

The current evidence supports the following ranking, but only as a structural comparison and not as a frozen decision:

1. Rolling prior-gap absolute tolerance
2. Static mixed absolute + relative tolerance
3. Static absolute tolerance
4. Static relative tolerance

This ranking is not a claim that the rolling architecture is fully frozen. It is a claim that, among the candidate architectures considered, the rolling prior-gap architecture is the best-supported structural foundation from the current repository evidence.

### Important caveat

The evidence does not yet justify choosing the rolling architecture as a final Group B freeze. The unresolved items remain:

- exact rolling statistic
- exact window semantics
- minimum-history threshold
- insufficient-history fallback behavior
- tolerance update timing around creation and zone state
- exact definition of allowable historical mutation or append-only semantics

Therefore the appropriate conclusion is:

- moderate evidence supports rolling prior-gap absolute tolerance as the preferable structural foundation
- evidence is not yet sufficient to declare it the final Group B architecture or to freeze it

## 9. Remaining Unknowns

The comparison leaves the following unresolved and intentionally unchosen:

- exact rolling statistic (median, mean, other robust statistic)
- exact count-based or time-based window
- minimum number of prior observations needed for valid tolerance
- fallback behavior before enough history exists
- exact gap transform if a later relative or mixed layer is approved
- exact update timing of the tolerance state after a current decision
- exact zone membership rule beyond the same-direction causal principle
- exact center and geometry semantics downstream of tolerance

These remain unresolved because they are downstream of the architecture comparison and cannot be defensibly chosen without concrete governance or further evidence.

## 10. Human Decisions Required

These are genuine governance decisions, not technical details to invent:

- whether the final root gap representation remains absolute or whether a relative or mixed representation is later approved
- whether the final rolling tolerance uses a median or some other robust statistic
- what minimum prior-history requirement is acceptable for a valid tolerance calculation
- whether the tolerance state is append-only or can mutate earlier historical state
- whether a fallback strategy is allowed before sufficient prior history exists
- whether the project wants the simpler static family instead of the more adaptive rolling family

## 11. Governance Status

- Group A frozen
- 15-minute bar contract frozen
- Group B not frozen
- Phase 2 not started
- no production code changed
- no tests changed
- no trading behavior changed

## Final conclusion

Does the existing evidence justify choosing rolling prior-gap absolute tolerance as the Group B architecture, or is the evidence still insufficient?

The evidence supports rolling prior-gap absolute tolerance as the strongest structural foundation among the current candidate architectures. However, the evidence is still insufficient to freeze it as the final Group B architecture because the exact rolling statistic, window semantics, minimum-depth rule, and update timing are not yet finalized.

Therefore, the evidence supports recommending rolling prior-gap absolute tolerance as the best-supported candidate architecture, but not yet as a frozen decision.
