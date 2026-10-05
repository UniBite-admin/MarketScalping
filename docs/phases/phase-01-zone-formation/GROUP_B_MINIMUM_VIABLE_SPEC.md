# Phase 1 — Group B Minimum Viable Specification

STATUS: NOT FROZEN

This document records the minimum viable specification that is defensible from the current evidence.

It is intentionally limited to what can be stated rigorously today. It does not freeze Group B, does not freeze a tolerance value, and does not authorize implementation or Phase 2. It distinguishes:
- evidence-supported
- proposed but not yet frozen
- blocked / unknown

## Classification legend

- A. EVIDENCE-SUPPORTED
- B. PROPOSED BUT NOT YET FROZEN
- C. BLOCKED / UNKNOWN

## 1. Minimum Viable Group B Specification

### 1. Input eligibility

A. EVIDENCE-SUPPORTED
- Only confirmed, eligible Group A swings may enter any Group B clustering process.
- Group A confirmation and eligibility semantics remain authoritative.
- Group B must operate on same-direction sequences only.
- Swing highs and swing lows are separate streams and must not be merged into one same-direction calibration or clustering sequence.

B. PROPOSED BUT NOT YET FROZEN
- A direction-neutral implementation is possible only if the project later decides to define a common ranking or normalization rule; no such rule is currently justified.

C. BLOCKED / UNKNOWN
- No final statement can yet be made about which specific subset of eligible swings should be used for a production zone family beyond the Group A eligibility gate.

### 2. Cluster membership semantics

A. EVIDENCE-SUPPORTED
- A swing becomes eligible only when the Group A required evidence is available in canonical time order.
- A swing may be evaluated against an existing same-direction zone only if both the candidate swing and the existing zone are based on the same direction.
- A swing joins an existing same-direction zone only by explicitly satisfying the cluster membership rule that is eventually selected.
- Creating a new zone requires a deterministic rule that is causal and uses only already-available prior evidence.
- No future information may be required for zone membership.

B. PROPOSED BUT NOT YET FROZEN
- The current evidence supports the idea that a zone member should be determined by a deterministic same-direction comparison against the current zone state, but the exact membership formula is not yet frozen.
- A candidate may be assigned to the nearest same-direction zone center if such a rule is later approved, but this is not yet a frozen requirement.

C. BLOCKED / UNKNOWN
- No final cluster membership formula is justified.
- No final zone assignment semantics are justified beyond the requirement that they must be same-direction and causal.

### 3. Minimum cluster size

A. EVIDENCE-SUPPORTED
- The current evidence does not justify any frozen minimum cluster size beyond the fact that single-swing clusters are structurally weak and highly fragmented.
- The historical descriptive evidence shows that very small tolerance rules create a large number of singleton-style structures.

B. PROPOSED BUT NOT YET FROZEN
- A minimum cluster size of 2 eligible swings is a reasonable structural proposal, but it remains a proposal only.
- It is not justified by profitability or by any final tolerance rule.
- It is structurally defensible because a single swing does not constitute a stable zone in the same way that a multi-swing cluster does.

C. BLOCKED / UNKNOWN
- The minimum cluster size is not yet frozen.
- No final value is justified beyond the weak proposal that 2 eligible swings is a reasonable starting point for research.

### 4. Zone center

A. EVIDENCE-SUPPORTED
- The median of cluster member prices is the clearest simple center candidate that is not obviously sensitive to a single outlier.
- It can be specified independently of the final tolerance rule, as a center estimator once the member set is known.
- The median center remains deterministic and replayable.

B. PROPOSED BUT NOT YET FROZEN
- Median center remains a proposed zone-center definition rather than a frozen Group B rule.
- It is not yet tied to an approved cluster membership formula or an approved tolerance model.

C. BLOCKED / UNKNOWN
- No final zone center is justified if the cluster membership rule remains unresolved.
- No historical mutation issue is yet frozen, but a causal append-only historical state must remain the governing invariant.

### 5. Zone geometry

A. EVIDENCE-SUPPORTED
- The project can specify that zone geometry is separate from the final tolerance rule only after the cluster membership model is defined.
- A zone has a center and a price domain, but the exact geometry is not yet justified.

B. PROPOSED BUT NOT YET FROZEN
- A simple geometric interpretation based on member spread and a deterministic tolerance margin is conceptually possible, but it is not yet a frozen rule.

C. BLOCKED / UNKNOWN
- Exact lower/upper bounds remain blocked because they depend on the unresolved tolerance rule.
- Any formula that depends on a final tolerance is not yet valid as a specification.

### 6. Assignment rule

A. EVIDENCE-SUPPORTED
- Same-direction assignment is a natural and minimal requirement.
- A candidate must be evaluated only against same-direction candidate zones.
- Nearest-center assignment is a simple deterministic concept and is consistent with the Phase 1 simplicity principle.
- A tie-break is required for determinism.

B. PROPOSED BUT NOT YET FROZEN
- The specific tie-break ordering is a proposal only: earliest-created zone, then stable identifier order, or another deterministic ordering if later approved.
- Nearest-center assignment is plausible, but not yet frozen.

C. BLOCKED / UNKNOWN
- No final assignment algorithm is justified because the final cluster geometry and tolerance rule remain unresolved.

### 7. Zone creation timing

A. EVIDENCE-SUPPORTED
- Zone creation must be causal and must not rely on future information.
- A zone cannot be backdated.
- The creation event must reflect the moment the cluster first satisfies the relevant membership rule.
- For Group A, the confirmation and eligibility times are anchored in the canonical time order and cannot be retroactively altered.

B. PROPOSED BUT NOT YET FROZEN
- A minimal creation semantics could be: zone is created when the second eligible swing of a same-direction cluster satisfies the relevant membership criteria.
- This is a viable proposal, but it is not yet accepted as a frozen rule.

C. BLOCKED / UNKNOWN
- No final creation rule is justified without a final cluster membership and tolerance policy.

### 8. Overlap handling

A. EVIDENCE-SUPPORTED
- Overlap must remain deterministic and causally ordered.
- The project cannot permit ambiguous same-direction overlap without a deterministic rule.

B. PROPOSED BUT NOT YET FROZEN
- A same-direction overlap policy could be solved by nearest-center assignment or explicit merge rules, but neither is frozen.

C. BLOCKED / UNKNOWN
- No final overlap policy is justified today.
- The current evidence does not support a final merge rule, and the tolerance dependence means the exact behavior remains unresolved.

### 9. Historical immutability

A. EVIDENCE-SUPPORTED
- Historical state must remain append-only and ordered by canonical eligibility time.
- Once a zone has been created, earlier history must not be mutated by later swings.
- This is consistent with deterministic replay and the repository architecture.

B. PROPOSED BUT NOT YET FROZEN
- The exact mechanism for zone evolution after creation remains a proposal.

C. BLOCKED / UNKNOWN
- No final historical-evolution policy is justified for non-trivial zone updates once the cluster membership and tolerance rule remain unresolved.

### 10. Deterministic replay

A. EVIDENCE-SUPPORTED
- Canonical order, stable index, and explicit tie-breaking are required.
- The same stream under the same canonical ordering must produce the same zone evolution.
- Equality must remain non-eligible and non-ambiguous.

B. PROPOSED BUT NOT YET FROZEN
- A final deterministic tie-break ordering remains proposed rather than frozen.

C. BLOCKED / UNKNOWN
- No complete deterministic Group B replay contract is justified until the cluster geometry, membership rule, and tolerance rule are frozen.

### 11. Multi-asset boundary

A. EVIDENCE-SUPPORTED
- The existing evidence does not justify a final multi-asset clustering contract.
- Market-local clustering may be considered, but it is not a Group B freeze item yet.

B. PROPOSED BUT NOT YET FROZEN
- A market-local, asset-specific calibration could be a later design direction, but it is not a current specification.

C. BLOCKED / UNKNOWN
- Multi-asset behavior remains blocked because no final tolerance or geometry rule has been justified.

### 12. Tolerance

A. EVIDENCE-SUPPORTED
- The corrected same-direction research shows that swing highs and swing lows each have observable structural spacing.
- For swing highs, the same-direction gap distribution is approximately:
  - median absolute gap = 33.78
  - p90 absolute gap = 553.87
  - p95 absolute gap = 1532.47
  - median relative gap = 0.00354
  - p90 relative gap = 0.06728
- For swing lows, the same-direction gap distribution is approximately:
  - median absolute gap = 35.85
  - p90 absolute gap = 589.51
  - p95 absolute gap = 1781.97
  - median relative gap = 0.00420
  - p90 relative gap = 0.07183
- This is strong evidence that same-direction swing spacing contains real structure.
- The spacing has a strong central concentration near a small median gap and a larger long tail. That long tail is exactly why a final tolerance cannot be chosen simply from a single statistic without understanding the geometry of the distribution.
- The static mixed A/r family is only a research direction, not a justified specification, because the effective tolerance often becomes A-dominant and therefore fails to express a meaningful control parameter across the observed price range.
- Static A/r sweeps contain parameter-inactivity problems: many candidate pairs appear stable only because the absolute floor dominates the max() rule, not because the rule is genuinely sensitive to the relative component.

B. PROPOSED BUT NOT YET FROZEN
- A simple causal tolerance derived from prior same-direction swing observations is a defensible research direction.
- A rolling prior-observations-only median or robust percentile is a better research candidate than an arbitrary A/r pair, but it is not yet a frozen method.
- A direction-specific prior-observations-only rule remains a proposal only.

C. BLOCKED / UNKNOWN
- No exact A/r pair is justified.
- No final tolerance method is justified.
- No final parameter value is justified.
- No final mixed-family calibration is justified as a specification.

### 13. 15m / OHLC dependency

A. EVIDENCE-SUPPORTED
- The human project authority has now approved the deterministic 15-minute `[bar_start, bar_end)` bucket contract as the authoritative operational input contract for Group B.
- This approval does not freeze Group B itself, and it does not reinterpret the frozen Group A swing semantics.
- The approved contract is: 15-minute UTC-aligned buckets, event exactly at `bar_end` belongs to the next bar, bars close when replay passes `bar_end`, closed bars are immutable, trailing/incomplete bars are excluded from finalized Group A and Group B evaluation, and the final partial bar at dataset end is discarded.
- The research reconstruction remains the evidence basis that supported the approved contract, but it is now governing only insofar as the human-approved operational rule is explicitly recorded.

B. PROPOSED BUT NOT YET FROZEN
- The earlier research pathway using reconstructed 15-minute bars was a valid evidence-generating proposal before governance approval.
- That proposal is now superseded by the human-approved operational contract and must not be treated as unresolved or open for silent reinterpretation.

C. BLOCKED / UNKNOWN
- No additional bar contract uncertainty remains for the approved Phase 1 operational rule.
- Group B remains NOT FROZEN because the approved bar contract is an input contract but not a full Group B freeze.

---

## SECTION 2 — Remaining Blockers

The smallest unresolved blockers required before Group B can be frozen are:

1. Final same-direction cluster membership rule
2. Final tolerance rule or explicit rejection of tolerance-based clustering as not yet justified
3. Final minimum cluster size requirement, if a value beyond the current proposal is required
4. Final zone geometry formula linked to the approved cluster rule
5. Final overlap handling policy
6. Final deterministic creation time semantics and tied assignment rule
7. Authoritative bar/timeframe/OHLC contract that feeds the zone pipeline
8. Confirmation that the chosen rule remains causal under the frozen Group A timing model
9. Sufficient replay evidence that the method is stable and not just a descriptive artifact

These blockers remain unresolved and therefore prevent a Group B freeze review.

---

## SECTION 3 — What Must Not Be Decided Yet

These decisions are currently unsupported by the evidence and must not be frozen:

- any exact A/r pair
- any exact A/r sweep result presented as final
- any final tolerance value
- any final formula that depends on an unresolved tolerance model
- any final lower/upper bound formula for zone geometry
- any final overlap or merge rule without a formal causal policy
- any final minimum cluster size beyond the weak proposal that 2 eligible swings is a reasonable research starting point
- any final multi-asset rule
- any production OHLC contract based only on research reconstruction
- any requirement to optimize around profitability, P&L, win rate, or trade count
- any rule requiring future information or look-ahead

---

## SECTION 4 — Recommended Next Research Step

RECOMMENDED NEXT RESEARCH STEP

Perform one constrained research check: a prior-observations-only rolling same-direction tolerance test, evaluated separately for swing highs and swing lows, using exactly the same historical replay evidence already used by the research script, and comparing only a small set of simple candidate rules (for example, rolling median and rolling robust percentile) without freezing a value.

This is the minimal next step because it addresses the single largest remaining blocker: whether a simple causal same-direction tolerance rule is supportable from the observed structural spacing without moving into arbitrary tuning or final specification.

It does not implement production logic, does not freeze any rule, and does not create a final tolerance value.

---

## Architect Decision

ARCHITECT DECISION: NOT READY FOR GROUP B FREEZE REVIEW

Reason:
The current evidence supports a limited research direction: same-direction swing spacing contains enough observable structure to justify further causal calibration research. It does not yet support a final Group B freeze because the key specification components remain unresolved: final cluster membership semantics, final tolerance rule, final geometry, overlap handling, bar contract, and implementation timing remain blocked or unapproved.

---

## Final governance status

- Group A: FROZEN
- Group B: NOT FROZEN
- 15m timeframe: NOT FROZEN
- OHLC contract: NOT FROZEN
- exact tolerance: NOT FROZEN
- calibration method: NOT FROZEN
- Phase 2: NOT STARTED
- production behavior: UNCHANGED
- profitability optimization: NOT USED
- look-ahead: NOT INTRODUCED

## ROOT BLOCKER ANALYSIS

### Dependency chain

The dependency chain for Group B is:

OHLC/bar contract -> timeframe -> Group A eligible swings -> clustering membership -> tolerance -> minimum cluster size -> zone center -> zone geometry -> overlap handling -> zone creation timing -> historical immutability -> deterministic replay

This chain is the minimum structural ordering supported by the repository evidence and by the analysis in the Group B research artifacts.

### Dependency map

- OHLC/bar contract
  - depends on: deterministic canonical event ordering and an explicit source-of-truth price series
  - does not depend on: clustering membership, tolerance, minimum cluster size, zone center, overlap handling, historical immutability, or deterministic replay
  - why: it defines the observational unit and the price series that all later Group B rules are evaluated against. It is the underlying input contract, not a downstream clustering rule.

- timeframe
  - depends on: the chosen OHLC/bar contract and the canonical replay chronology
  - does not depend on: final tolerance or final zone geometry
  - why: it fixes how raw events are bucketed into bars or time slices. It governs the resolution of the observation stream, not the cluster behavior itself.

- Group A eligible swings
  - depends on: the frozen Group A swing semantics and the chosen bar/timeframe contract that produces the price series used for local extremum detection
  - does not depend on: final tolerance, minimum cluster size, overlap handling, or final zone geometry
  - why: these are the confirmed and eligible swing anchors. They are the input population for Group B and remain frozen under the approved Group A semantics.

- clustering membership
  - depends on: Group A eligible swings, same-direction sequencing, and a policy for deciding when a candidate swing joins a cluster
  - does not depend on: final overlap handling, final zone center, or final historical mutation semantics as a prerequisite to the rule itself
  - why: membership is the process of deciding whether a swing should be attached to a current cluster. It is a structural rule, but the exact membership function still depends on the chosen tolerance model.

- tolerance
  - depends on: the same-direction swing spacing distribution, the chosen bar/timeframe contract, and Group A eligible swings
  - does not depend on: final minimum cluster size, final geometry, or final historical immutability rule
  - why: tolerance defines the maximum allowed distance for cluster membership. It is the central distance rule but it is not itself a full zone specification.

- minimum cluster size
  - depends on: clustering membership and the chosen tolerance structure
  - does not depend on: final zone overlap policy or final deterministic replay tie-break specifics
  - why: once the cluster membership rule exists, the minimum number of members needed to consider a cluster valid can be specified. It does not define the price geometry itself.

- zone center
  - depends on: the final cluster membership rule and the member set of the cluster
  - does not depend on: overlap handling or final historical mutation semantics as a prerequisite
  - why: center is a derived value once the cluster is known.

- zone geometry
  - depends on: zone center, cluster membership, and tolerance
  - does not depend on: historical immutability as a prerequisite
  - why: geometry is a representation of the price domain once the cluster and center are defined.

- overlap handling
  - depends on: cluster membership, zone geometry, zone center, and creation timing
  - does not depend on: profitability or trade performance
  - why: overlap is a structural conflict rule among same-direction clusters. It is downstream of the actual cluster definitions.

- zone creation timing
  - depends on: cluster membership, minimum cluster size, and canonical eligibility time ordering
  - does not depend on: final overlap resolution as a prerequisite to creation time
  - why: creation timing is when a cluster first becomes valid and should be recorded; it is downstream of membership and size but upstream of historical record semantics.

- historical immutability
  - depends on: zone creation timing and canonical ordering
  - does not depend on: profitability optimization or strategy outcomes
  - why: once a zone is created, earlier history must remain append-only and cannot be retroactively rewritten by later swings.

- deterministic replay
  - depends on: canonical order, historical immutability, zone creation timing, and final tie-breaks
  - does not depend on: any P&L or profitability target
  - why: replay determinism is the final safety property that ensures identical inputs produce identical outputs under the same canonical order.

### Single root blocker

The single earliest unresolved decision is:

AUTHORITATIVE OHLC/BAR CONTRACT AND TIMEFRAME FOR GROUP B

This is the root blocker because it is the first unresolved dependency in the chain and it constrains the definition of the underlying price series used for Group A and Group B. Without an explicit bar contract, every later decision is being defined over an unapproved observational model.

This is not merely an important item. It is the earliest dependency that logically blocks downstream specification because it determines what the raw price series is, what a same-direction swing means in the actual Group B pipeline, and which tolerance surface is even being evaluated.

### Minimum evidence required

The smallest evidence package that could resolve the root blocker is a single controlled audit using the repository’s existing canonical data, without freezing any tolerance or strategy behavior:

1. Reproduce the canonical-to-bar construction currently used for research using the repository’s deterministic event history.
2. Define the exact bar contract explicitly: bucket start time, price aggregation rule, open/high/low/close semantics, and why the chosen rule is valid under the project’s canonical replay model.
3. Preserve Group A semantics exactly: only eligible frozen Group A swings are used as inputs; no change to the swing rule itself.
4. Compute the same-direction high and low spacing on that bar contract using prior-observations-only logic only.
5. Show that the bar contract is deterministic, causal, and reproducible from repository artifacts with no future information, no parameter sweep, and no profitability optimization.
6. Report whether the same-direction spacing remains structurally coherent under the chosen contract without relying on a final tolerance value.

This is the minimum meaningful evidence because it directly tests the source-of-truth price layer instead of jumping ahead into tolerance tuning.

### Acceptance criteria

The root blocker is resolved only if all of the following are true:

- The bar construction is explicitly documented and reproducible from repository artifacts.
- The same data source and canonical ordering produce the same bars on repeated replay.
- Group A eligible swings are computed using the exact same frozen semantics and remain unchanged by the bar contract decision.
- The bar contract is causal: each bar is built from information available by the relevant time boundary, with no future data used.
- The same-direction spacing evidence remains structurally coherent under the chosen contract and does not require hidden assumptions.
- The chosen bar contract is stated as the operational input for Group B and is distinguishable from a research-only exploratory artifact.
- The audit result is deterministic and mechanically checkable; no subjective judgment such as “looks stable” is used as acceptance.

### Downstream impact

If the root blocker is resolved, the following Group B rules become specifiable in order:

- clustering membership
- tolerance model
- minimum cluster size
- zone center
- zone geometry
- overlap handling
- zone creation timing
- historical immutability
- deterministic replay

The following would still remain unresolved even after this blocker is resolved:

- exact final tolerance value
- exact final cluster membership formula if the chosen rule is still open
- exact final zone center policy if a different center estimator is preferred
- exact overlap merge semantics if the chosen geometry still requires a decision
- final human freeze approval for the full Group B design

### Human decision requirement

A human decision is required only at the governance boundary of accepting the bar contract as the operational Group B input definition.

What the human must decide:
- whether the deterministic 15-minute reconstructed bar contract is accepted as the operational Group B input model, or whether a different explicit bar contract must be required before Group B may be considered for freeze review.

Why evidence cannot decide it alone:
- the repository evidence supports the deterministic 15-minute reconstruction as a valid research contract, but it does not yet establish it as the authoritative production input contract without human approval.
- this is a specification-assignment decision at the architecture boundary, not a mathematical tuning decision.

Alternatives that exist:
- accept the deterministic 15-minute reconstructed bar contract as the operational Group B input contract
- continue research-only analysis and postpone any Group B freeze review
- require a different explicit OHLC/bar contract and re-run the minimal evidence check before any freeze review

### Exactly one recommended next step

Run one minimal deterministic bar-contract audit using the existing canonical data and the frozen Group A swings only:

Audit the exact canonical-to-15m reconstructed-bar contract and verify that it is the smallest reproducible causal input model for Group B without selecting any final tolerance or creating any new production logic.

This is the smallest controlled step that resolves the true root blocker without broad tuning, without implementation, and without a Group B freeze.

---

## ARCHITECT DECISION

ARCHITECT DECISION:
NOT READY FOR GROUP B FREEZE REVIEW

Status remains:
STATUS: NOT FROZEN
