# Group B Root Decision Dependency Analysis

## Status

- Group B: NOT FROZEN
- Analysis-only
- No production implementation
- No production behavior change
- No Group B decision is frozen by this document
- This document does not authorize Phase 2

## 1. Objective

This analysis is limited to the dependency structure of the unresolved Group B decisions identified in the current Phase 1 review documents.

The objective is not to solve Group B. It is to separate:
- true root decisions that must be chosen before anything else can be implemented deterministically
- downstream decisions that are consequences of those roots
- decisions that can be derived mechanically once a root is fixed
- decisions that require real dataset evidence before a recommendation
- decisions that must be settled by explicit human governance because evidence cannot determine them

This analysis respects the frozen Phase 1 state and does not re-open any frozen decision.

## 2. Authority and Frozen Inputs

FROZEN

1. Phase 1 Group A is frozen and human-approved.
2. The 15-minute OHLC/bar contract is frozen and human-approved.
3. Group A swing observation, confirmation, and eligibility semantics remain authoritative.
4. Group B remains not frozen.
5. Phase 2 has not started.
6. The authoritative roadmap is [docs/ROADMAP.md](../../ROADMAP.md).

RESEARCH-SUPPORTED

- Same-direction sequence structure exists in the canonical dataset.
- Mixed static A/r calibration is structurally usable but weak/blunt.
- High and low behavior differ materially.
- A causal rolling-history approach remains a reasonable research direction.

PROPOSED

- The current Group B proposal is a design direction, not a freeze.

UNDEFINED

- The exact technical contract required for deterministic Group B implementation.

## 3. Unresolved Decision Inventory

The table below consolidates the unresolved Group B decisions identified in the Phase 1 review on the basis of dependency, evidence, and governance requirement.

| ID | Decision | Classification | Current state | Why it matters |
| --- | --- | --- | --- | --- |
| GBD-01 | Same-direction observation set | ROOT | UNDEFINED | Defines what enters the tolerance and membership history. |
| GBD-02 | Gap definition | ROOT | UNDEFINED | Without a gap definition, all tolerance math is ambiguous. |
| GBD-03 | Current swing inclusion in history | ROOT | UNDEFINED | Determines whether the rule is causal or may embed look-ahead. |
| GBD-04 | Causal availability window | ROOT | UNDEFINED | Determines whether data is available at the exact moment the swing becomes eligible. |
| GBD-05 | Tolerance family (absolute / relative / mixed / adaptive) | ROOT | PROPOSED | Determines the entire mathematical model. |
| GBD-06 | Relative denominator / reference price | ROOT | UNDEFINED | Required if relative or mixed forms are used. |
| GBD-07 | Rolling history window semantics | ROOT | UNDEFINED | Necessary before any tolerance can be computed. |
| GBD-08 | Count-based vs time-based history | ROOT | UNDEFINED | Changes the meaning of the historical state materially. |
| GBD-09 | Minimum historical depth before tolerance is valid | EMPIRICAL | UNDEFINED | Determines when a tolerance becomes usable and when a fallback is required. |
| GBD-10 | Fallback behavior before sufficient history | ROOT | UNDEFINED | Must be explicit to avoid silent assumptions. |
| GBD-11 | Tolerance update timing | ROOT | UNDEFINED | Defines whether the algorithm is replay-safe and causal. |
| GBD-12 | Tolerance formula and units | ROOT | PARTIALLY DEFINED | The proposal names median but leaves formula and units unspecified. |
| GBD-13 | Multiplier / scale factor | ROOT | UNDEFINED | A multiplier is a major mathematical choice. |
| GBD-14 | Absolute floor or lower bound | ROOT | UNDEFINED | Can create dead zones and parameter inactivity. |
| GBD-15 | Relative floor / cap / upper bound | ROOT | UNDEFINED | Important for normalization and stability. |
| GBD-16 | Upper cap | ROOT | UNDEFINED | Affects maximum radius and merge risk. |
| GBD-17 | Lower bound for tolerance | ROOT | UNDEFINED | Prevents zero or near-zero tolerance ambiguity. |
| GBD-18 | Zero-tolerance / duplicate-price handling | DERIVED | UNDEFINED | Follows from the tolerance formula and history rules. |
| GBD-19 | Candidate-to-zone distance metric | ROOT | PARTIALLY DEFINED | Defines how membership is evaluated. |
| GBD-20 | Zone reference point for distance | ROOT | PARTIALLY DEFINED | Must be specified before membership can be evaluated. |
| GBD-21 | Same-direction restriction | ROOT | RESEARCH-SUPPORTED | The design direction is clear, but the execution rule is not yet formalized. |
| GBD-22 | Nearest-zone selection | DERIVED | PROPOSED | A direct consequence of zone eligibility and distance function. |
| GBD-23 | Tie-break rule | DERIVED | PARTIALLY DEFINED | Necessary for deterministic replay. |
| GBD-24 | No-zone-qualified behavior | ROOT | UNDEFINED | Must decide discard vs create vs defer. |
| GBD-25 | New-zone creation trigger | ROOT | PARTIALLY DEFINED | Defines the earliest time a cluster becomes a zone. |
| GBD-26 | Triggering swing membership semantics | ROOT | UNDEFINED | Determines whether the swing that triggers creation becomes a member immediately. |
| GBD-27 | Minimum cluster size | EMPIRICAL / GOVERNANCE | PROPOSED (2) | Research does not justify a final value; it is a proposal only. |
| GBD-28 | Zone center statistic | ROOT | PROPOSED | Median is proposed, but not formally frozen as the final rule. |
| GBD-29 | Center immutability vs mutation | ROOT | UNDEFINED | Defines whether historical geometry can change. |
| GBD-30 | Even-member median behavior | DERIVED | PARTIALLY DEFINED in helper code only | Deterministic behavior must be fixed by design, not by code accident. |
| GBD-31 | Zone geometry definition | ROOT | UNDEFINED | Defines upper/lower bounds and historical zone shape. |
| GBD-32 | Geometry fixed or evolving | ROOT | UNDEFINED | Determines whether historical interpretation is mutable. |
| GBD-33 | Overlap detection semantics | ROOT | UNDEFINED | Must define what overlap means before resolution. |
| GBD-34 | Overlap resolution semantics | ROOT | UNDEFINED | Decide reject / assign / merge / coexist. |
| GBD-35 | Merge policy and identity survival | ROOT | UNDEFINED | A merge rule requires exact state transitions. |
| GBD-36 | Historical snapshot semantics | ROOT | UNDEFINED | Controls immutability and deterministic replay. |
| GBD-37 | Zone identity and creation timestamp | DERIVED | PARTIALLY DEFINED | Follows from creation and historical state rules. |
| GBD-38 | Membership reassignment policy | ROOT | UNDEFINED | Defines whether a later swing may reshape earlier membership. |
| GBD-39 | Deterministic replay ordering | ROOT | FROZEN for inputs, UNDEFINED for zone state | Requires stable ordering for all equal-distance and equal-time situations. |
| GBD-40 | Equal-distance tie handling | DERIVED | UNDEFINED | Follows from deterministic ordering and zone selection. |
| GBD-41 | Equal-timestamp tie handling | REDUNDANT | FROZEN by canonical ordering | Already fixed by authoritative replay semantics. |
| GBD-42 | Stable zone ID generation | DERIVED | UNDEFINED | Must be deterministic and replay-safe. |
| GBD-43 | Multi-asset portability | EMPIRICAL / GOVERNANCE | UNKNOWN | The present evidence is BTC-EUR-specific. |
| GBD-44 | Historical mutation risk | ROOT | UNDEFINED | This is a core system correctness question. |
| GBD-45 | Future-information prevention | REDUNDANT | FROZEN by causality requirements | Already required by the frozen Group A and bar contract. |

## 4. Root Decision Set

The smallest practical root set is the following.

1. GBD-01 — Same-direction observation set
2. GBD-02 — Gap definition
3. GBD-03 — Current swing inclusion in tolerance history
4. GBD-05 — Tolerance family and formula
5. GBD-07 — Rolling-history semantics and window definition
6. GBD-19 — Candidate-to-zone distance metric
7. GBD-25 — Zone creation trigger and minimum evidence
8. GBD-28 — Zone center statistic and center lifecycle
9. GBD-31 — Zone geometry definition
10. GBD-33 — Overlap detection and resolution semantics
11. GBD-36 — Historical snapshot and immutability semantics
12. GBD-39 — Deterministic replay and tie-break semantics

This is the smallest set that is genuinely independent in the repository-grounded sense. Several additional items are mechanically derived after these roots are frozen, but they are not root decisions themselves.

## 5. Dependency Graph

The dependency graph supported by repository evidence and frozen Phase 1 decisions is:

bar contract
→ swing sequence semantics
→ causal availability of observations
→ tolerance observation set
→ tolerance family + formula + history window
→ tolerance update timing
→ candidate-to-zone distance
→ zone reference / center definition
→ zone creation trigger and minimum cluster size
→ center / geometry / overlap semantics
→ historical state / identity / snapshot immutability
→ deterministic replay and tie-breaks
→ empirical validation on canonical BTC-EUR dataset
→ multi-asset extension review

A more explicit dependency order is:

1. Frozen bar contract
2. Frozen Group A swing semantics
3. Same-direction observation set
4. Gap definition and causal observation history
5. Tolerance family + formula + window + minimum history
6. Tolerance update timing and fallback
7. Member distance + zone center definition
8. Zone creation and cluster-size rules
9. Zone geometry and overlap resolution
10. Historical snapshot and immutability
11. Deterministic replay and stable identity
12. Empirical validation and multi-asset review

Important distinction:
- Some decisions are root and must be frozen first.
- Others are downstream consequences and should not be treated as root decisions even though they are major design items.

## 6. Evidence Matrix

| Root decision | Repository evidence | Dataset evidence | Evidence limitations | Recommendation possible? | Human approval required? |
| --- | --- | --- | --- | --- | --- |
| Same-direction observation set | Group A freeze; Group B research docs | 78 highs, 68 lows; direction separation in research | Data supports separation but not final implementation rule | YES, direction separation is recommended | NO, if it is just formalizing existing evidence |
| Gap definition | Group A and bar contract; research docs | Structural spacing evidence | The exact gap used at implementation time is not frozen | NO | YES, unless the team chooses a rule explicitly |
| Current swing exclusion | Frozen causal model | Existing research implies prior-only behavior but does not encode it | Implementation semantics are not yet specified | YES for the causal principle | NO, if the causal principle is accepted |
| Tolerance family | Existing research docs | Mixed-family evidence, structural spacing data | No single final value or family proves superiority | NO | YES |
| History window semantics | Research docs only | Distributional evidence is descriptive, not final | The right window is not determined by evidence alone | NO | YES |
| Candidate-to-zone distance | Proposal text | Same-direction spacing evidence | Distance interpretation is not yet formally specified | YES, nearest-center absolute distance is a reasonable design choice | NO, unless team wants a different geometry |
| Zone creation trigger | Proposal text and research | Structural evidence supports cluster existence but not final trigger | Cluster threshold is not proven | NO | YES |
| Zone center definition | Proposal text | Median is consistent with robust-statistics reasoning | The center lifecycle is unresolved | YES, as a design baseline | NO, unless the team prefers a different statistic |
| Zone geometry | Proposal text only | No final geometry evidence | Geometry remains a root design decision | NO | YES |
| Overlap resolution | Proposal text only | No overlap evidence in authoritative dataset analysis | Cannot be decided from data alone in the current state | NO | YES |
| Historical state / immutability | Frozen deterministic replay requirements | Implicit replay semantics exist | Historical mutation policy is not formalized in Group B | YES, append-only snapshot semantics is recommended | NO, if accepted as a design principle |
| Deterministic replay and tie-breaks | Canonical metadata and replay_runner | Dataset ordering is deterministic | Zone-specific tie-breaks are not yet formalized | YES, as a generic rule set | NO, unless the team prefers a different consistent ordering |
| Multi-asset portability | Current BTC-EUR evidence only | No multi-asset evidence | Not enough to support a general rule | NO | YES |

## 7. Minimum Decision Sequence

The minimum sequential process to make Group B fully deterministic without unnecessary complexity is:

1. Freeze the same-direction observation set and causal availability rules.
2. Freeze the gap definition and the historical observation set used to compute tolerance.
3. Select the tolerance family and formula.
4. Freeze the rolling-history semantics, insufficient-history fallback, and update timing.
5. Freeze member-to-zone distance and the zone reference point.
6. Freeze the zone creation rule, minimum evidence threshold, and trigger semantics.
7. Freeze the zone center statistic and the center lifecycle.
8. Freeze the zone geometry and overlap resolution policy.
9. Freeze historical snapshot semantics and immutable historical state.
10. Freeze deterministic replay ties and stable zone identity.
11. Run the canonical BTC-EUR empirical checks.
12. Only then decide whether the rule is acceptable for a wider asset scope.

This sequence is the shortest practical route to a deterministic Group B spec without introducing unnecessary earlier parameter decisions.

## 8. Decisions Architect Can Recommend

The Architect can recommend a rule or baseline only where the evidence is strong enough to support it as a design direction without pretending it is final.

1. Same-direction-only observation set
- State: RECOMMENDATION ONLY
- Evidence: existing Group B research, diagnostics, and structural separation of highs/lows
- Why: avoids the invalid mixed-direction calibration artifact
- Human approval: not required if it is treated as a design baseline, but it must not be treated as a final freeze

2. Causal prior-observations-only philosophy
- State: RECOMMENDATION ONLY
- Evidence: frozen causal requirement and existing research direction
- Why: protects against look-ahead and future-state contamination
- Human approval: not required as a design principle, but final implementation must still follow it

3. Append-only historical snapshots for zone state
- State: RECOMMENDATION ONLY
- Evidence: deterministic replay semantics and frozen bar contract
- Why: avoids hidden re-interpretation of historical states
- Human approval: not required if the design choice is treated as a default system rule

4. Deterministic ordering policy for equal values and equal distances
- State: RECOMMENDATION ONLY
- Evidence: canonical ordering and replay metadata already define deterministic handling for equal timestamps
- Why: avoids set-order nondeterminism
- Human approval: not required for the ordering principle itself

5. Median as a baseline center statistic
- State: RECOMMENDATION ONLY
- Evidence: robust-statistics reasoning and proposal text
- Why: median is more stable than mean under outliers
- Human approval: required only if the team prefers a different center definition or wants a final freeze

These are baseline architectural recommendations, not final Group B policy.

## 9. Decisions Requiring Human Approval

These are items that cannot be determined from repository evidence alone and therefore require explicit human governance decisions.

1. Tolerance family selection
- Why: the evidence supports several valid families but does not prove which one is the correct final model.

2. Window semantics and minimum depth
- Why: evidence can describe a distribution but cannot pick a single legal window without design intent.

3. Minimum cluster size
- Why: the current evidence supports a proposal but does not prove the final threshold.

4. Zone geometry definition
- Why: there is no authoritative requirement for center ± tolerance, min/max span, or another interval model.

5. Overlap resolution policy
- Why: choosing between reject, assign, merge, or coexist is a design policy choice, not a technical necessity.

6. Historical mutation policy for center and geometry
- Why: a team must choose whether zone state is mutable or snapshot-only before implementation.

7. Multi-asset extension policy
- Why: current evidence is BTC-EUR-specific and does not justify a universal rule.

8. Final formal freeze of Group B
- Why: by definition, a specification freeze is a governance decision, not a data-derived fact.

## 10. Research Needed Before Decision

Only concrete, bounded research tasks are listed here.

1. Direction-separated same-direction sweep audit
- Purpose: confirm the structure of highs and lows independently under the frozen bar contract.
- Output: same-direction gap distributions and their time-order behavior.

2. Causal-history simulation for candidate rolling rules
- Purpose: test whether the tolerance statistic can be computed strictly from prior same-direction observations.
- Output: a comparison of prior-only vs current-inclusive behavior.

3. Window-depth analysis for stability
- Purpose: determine whether a small count window, larger count window, or time-based rule has a stable distribution.
- Output: tolerance stability summary without parameter freezing.

4. Center-stability analysis under historic mutation assumptions
- Purpose: evaluate the effect of median updates on historical interpretations.
- Output: design impact of mutable vs immutable center semantics.

5. Overlap prevalence analysis under same-direction constraints
- Purpose: estimate whether overlap is structurally common or rare under candidate rules.
- Output: whether overlap is a central design issue or a rare case.

6. Minimum-cluster threshold stress test
- Purpose: compare 1, 2, 3, and higher cluster minima under same-direction structure without selecting a final value.
- Output: evidence about whether the threshold changes the zone family materially.

7. Multi-asset portability review
- Purpose: determine whether the current same-direction structural approach is likely to transfer across other assets.
- Output: only a feasibility review; not a freeze decision.

## 11. Governance Status

- Group A remains frozen.
- 15-minute bar contract remains frozen.
- Group B remains NOT FROZEN.
- No production behavior changed.
- No tests were changed.
- This document does not authorize implementation.
- This document does not freeze any Group B rule.

## Appendix: Dependency Classification Summary

| Classification | Count |
| --- | ---: |
| ROOT | 19 |
| DERIVED | 9 |
| EMPIRICAL | 3 |
| GOVERNANCE | 6 |
| REDUNDANT | 4 |
| Total unresolved decisions analyzed | 41 |

This total is based on the distinct unresolved items in the Group B audit inventory and the existing frozen/derived decisions that are explicitly not unresolved.

## Final Architectural Conclusion

The current Group B proposal is not blocked because it is conceptually wrong. It is blocked because the unresolved root decisions are not yet formalized. The repository evidence is sufficient to say that same-direction analysis and causal prior-only behavior are directionally appropriate, but it is not sufficient to choose a final tolerance family, a final overlap rule, or a final minimum cluster size.

The correct architecture posture is:
- define the root decisions
- decide the root sequence
- derive the downstream consequences mechanically
- use the canonical BTC-EUR data to test the implied behavior
- require human approval for any non-evident design choice

This is the minimum rigorous path to a deterministic Group B spec without unnecessary complexity or premature freezing.
