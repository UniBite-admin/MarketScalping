# Group B Proposal Audit

## 1. Executive result

AUDIT RESULT: REQUIRES SPECIFICATION DECISIONS

The proposed "prior-observations-only rolling-median tolerance" is not sufficiently defined to be implemented deterministically without inventing missing technical decisions.

This is not a failure of the concept itself. The concept is RESEARCH-SUPPORTED and directionally plausible. The problem is that the proposal mixes a defensible causal intent with several undefined implementation rules. The current text defines the high-level idea, but it does not define the exact technical contract needed for deterministic, replay-safe implementation.

The proposal is therefore:
- RESEARCH-SUPPORTED as a causal idea
- PROPOSED as an implementation direction
- UNDEFINED in the exact operational details required for deterministic execution
- not IMPLEMENTATION-READY
- not FROZEN

## 2. Proposal reviewed

Reviewed documents:
- [docs/phases/phase-01-zone-formation/GROUP_B_ARCHITECT_PROPOSAL.md](GROUP_B_ARCHITECT_PROPOSAL.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_CALIBRATION_AUDIT.md](GROUP_B_CALIBRATION_AUDIT.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_STRUCTURAL_CALIBRATION_RESEARCH.md](GROUP_B_STRUCTURAL_CALIBRATION_RESEARCH.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MINIMUM_VIABLE_SPEC.md](GROUP_B_MINIMUM_VIABLE_SPEC.md)
- [docs/phases/phase-01-zone-formation/BAR_CONTRACT_DECISION.md](BAR_CONTRACT_DECISION.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)
- [replay_runner.py](../../replay_runner.py)
- [data/canonical/tardis_btc_eur_20191201/metadata.json](../../data/canonical/tardis_btc_eur_20191201/metadata.json)

This audit preserves the governance posture:
- Group A is FROZEN.
- The 15-minute bar contract is FROZEN.
- Group B is NOT FROZEN.
- The rolling-median tolerance is NOT FROZEN.
- No production implementation is performed.
- No Phase 2 work begins.
- No profitability test is performed.

## 3. Frozen inputs

FROZEN

- Group A swing semantics remain frozen.
- The 15-minute operational bar contract is frozen as the authoritative input contract for Group B.
- Event exactly at bar_end belongs to the next bar.
- Closed bars are immutable.
- Trailing/incomplete bars are excluded from finalized evaluation.
- The final partial bar at dataset end is discarded.
- Group A causality and confirmation semantics remain authoritative.

RESEARCH-SUPPORTED

- Same-direction swing spacing contains structure.
- A rolling tolerance from prior same-direction gaps is a defensible research direction.
- Median is a reasonable robust statistic for a prior-observations-only rule.

PROPOSED

- The exact membership formula.
- The exact tolerance algorithm.
- The exact zone geometry.
- The exact overlap policy.
- The exact implementation semantics for updates after creation.

UNDEFINED

- Every missing rule below remains unresolved unless explicitly approved.

## 4. Tolerance audit

### A. Exact tolerance definition

The proposal currently prefers a rolling median of same-direction gaps, but it does not define the exact rule in enough detail to be directly implemented without inventing missing semantics.

1. What exact observations are used?
- PARTIALLY DEFINED
- The text says "prior same-direction gaps" and "same-direction observations", but it does not define the exact event set used in the rolling history.
- It does not specify whether the observation set is: eligible swings only, all same-direction swings, confirmed swings only, or bar-level values decoded into swing records.

2. High and low swings separately or together?
- PARTIALLY DEFINED
- The proposal says same-direction only and high/low separately in some sections, but the exact implementation contract remains inconsistent across the document set.
- It never resolves whether a single tolerance history can be shared across high and low streams or whether each direction maintains its own independent tolerance state.

3. What exact gap is measured?
- PARTIALLY DEFINED
- The proposal says gap between same-direction observations, but it does not define whether the gap is:
  - adjacent member gap
  - center-to-center gap
  - current swing price to last member price
  - current swing price to zone center
  - zone-center-to-zone-center gap

4. Absolute price gap or relative gap?
- PARTIALLY DEFINED
- The proposal leans toward absolute gaps in the preferred rule, but the research documents also discuss relative-gap statistics. The implementation choice is not uniquely specified.

5. If relative, what exact denominator/reference price is used?
- UNDEFINED
- No exact denominator is specified: previous member price, current candidate price, zone center, previous bar close, prior same-direction mean, or a rolling reference.

6. What history depth/window is used?
- UNDEFINED
- No exact count-based window or time-based window is defined.

7. Is the window count-based or time-based?
- UNDEFINED
- No semantics are given for a count window, time range window, or event-count threshold.

8. What happens when insufficient history exists?
- UNDEFINED
- The proposal says a tolerance may be computed only after prior observations are available, but it does not define the exact fallback behavior before history exists.

9. Is the current swing excluded from the tolerance calculation?
- PARTIALLY DEFINED
- The proposal says previous-observations-only is preferred, but the actual implementation sequence is not defined enough to enforce it deterministically.

10. Is the tolerance calculated before or after membership evaluation?
- PARTIALLY DEFINED
- The text suggests the tolerance is computed before membership decision, but it never states the exact ordering with respect to zone creation update and candidate evaluation.

11. Is the median taken over absolute gaps, relative gaps, or another quantity?
- PARTIALLY DEFINED
- The preferred rule nominally says median of same-direction absolute gaps, but the earlier research uses relative gaps and distributional statistics. The selected quantity is not uniquely fixed in the architecture proposal.

12. Is there a multiplier?
- UNDEFINED
- No multiplier is defined, no default multiplier is stated, and no reasoning is given for how a multiplier would be chosen.

13. Is there an absolute floor?
- UNDEFINED
- No floor is specified; no rule chooses whether A is used, whether floor applies only to absolute tolerance, or whether floor is optional.

14. Is there a relative floor/cap?
- UNDEFINED
- No ratio floor, cap, or normalization rule is defined.

15. Is there an upper cap?
- UNDEFINED
- No maximum tolerance, maximum relative multiplier, or clipping rule is described.

16. Is there a lower bound?
- UNDEFINED
- Nothing defines whether tolerance can reach zero, can be clipped at epsilon, or must be clipped away from zero.

17. What happens if the calculated tolerance is zero?
- UNDEFINED
- Zero tolerance would create an exact-match-only rule. The proposal does not say whether that is allowed, rejected, or smoothed.

18. What happens with duplicate prices / zero gaps?
- UNDEFINED
- Duplicate-price conditions are not resolved in the proposal.

19. What happens when there are fewer than the required historical observations?
- UNDEFINED
- There is no exact threshold for the minimum history required before a tolerance value can be trusted.

20. Can tolerance change between swings?
- PARTIALLY DEFINED
- The proposal says it may change over time, but it does not define exactly when it updates, whether updates are per candidate or per zone, and whether changes are applied to earlier historical states.

### B. Summary of tolerance status

- DEFINED: none of the exact implementation details are fully defined.
- PARTIALLY DEFINED: the overall idea of causal prior-only rolling median is partially defined.
- UNDEFINED: virtually all exact operational details remain unspecified.
- CONFLICTING: the proposal mixes absolute-gap, relative-gap, and research-defined statistics without a single final selection.

## 5. Causality audit

The required causal sequence is:

bar closes
→ swing observation
→ swing confirmation
→ swing eligibility
→ tolerance calculation
→ zone membership decision
→ zone creation/update

The proposal is intended to be causal, but the implementation semantics are not precise enough to guarantee it.

### Causal check

- S itself may enter tolerance if the code calculates tolerance after the current event has already been inserted into the same-direction history. This is not explicitly prevented.
- Later swings may enter tolerance if the implementation uses a rolling history that is updated before the membership decision for the current event. The proposal does not define whether current-event insertion happens before or after evaluation.
- Later bars may enter tolerance if the implementation uses bar-end or bar-close state that is not frozen at the moment the current swing becomes eligible.
- Later zone members may enter tolerance if the tolerance is re-derived from current zone membership or current zone geometry instead of from prior same-direction observations only.

This means:
- PROPOSED: tolerance should use only information known before the current swing becomes eligible
- UNDEFINED: whether the implementation actually enforces that rule in code order
- HUMAN DECISION REQUIRED: exactly how the candidate history and zone membership state are updated in the causal event sequence

### Explicit causal determination

The proposal does not clearly guarantee the following:
- current swing excluded from tolerance history
- later swings excluded from tolerance history
- later bars excluded from tolerance history
- later zone members excluded from tolerance history

Therefore, the proposal does not yet provide a fully causal implementation contract.

## 6. Zone membership audit

1. Which zones are eligible?
- PARTIALLY DEFINED
- The proposal says same-direction active zones only, but it does not define an operational active-zone state or whether a zone is considered active only while it remains open or while it remains valid under snapshot semantics.

2. Same-direction restriction?
- DEFINED in principle
- The proposal states same-direction restriction is required.
- However, the final rule is not operationalized in the exact zone-state machine.

3. Price distance calculation?
- PARTIALLY DEFINED
- It says absolute difference between candidate price and current zone center, but it does not define whether the candidate is compared to the creation center, current center, or a dynamically updated center.

4. Tolerance used?
- PARTIALLY DEFINED
- The idea is present, but the exact computed tolerance value and update sequence are undefined.

5. Reference price?
- PARTIALLY DEFINED
- There is a price reference concept, but it is not fully defined in the final algorithm.

6. Multiple qualifying zones?
- PARTIALLY DEFINED
- The nearest-center rule is proposed, but the policy for multiple zones remains incomplete because the zone center itself is not fully defined as immutable or mutable.

7. Tie-break order?
- PARTIALLY DEFINED
- The proposal identifies a tie-break order, but the exact stable zone identifier semantics are not specified, and the tie-break is not mapped to the actual zone state model.

8. What happens when no zone qualifies?
- UNDEFINED
- The proposal does not define whether a candidate is discarded, creates a new zone, or becomes a pending observation before becoming a valid zone.

9. Whether a new zone is immediately created?
- PARTIALLY DEFINED
- The proposal says a new zone may be created when the minimum evidence threshold is satisfied, but the exact creation time and exact trigger conditions are not formalized.

10. Minimum cluster size?
- PARTIALLY DEFINED
- A value of 2 is proposed as a reasonable minimum, but it is not frozen and not proven by the evidence.

11. Whether a one-swing candidate exists before becoming a valid zone?
- UNDEFINED
- The proposal does not formally define the lifecycle between a single swing and a valid zone.

12. Whether a new swing can cause multiple existing zones to merge?
- UNDEFINED
- No merge policy or merge trigger is defined.

13. Whether membership can ever be reassigned later?
- UNDEFINED
- The proposal declares no retroactive mutation, but not whether later events may reassign a current candidate to a different zone in a future replay state.

## 7. Zone center audit

The proposal says to use the median as the zone center.

- Is median calculated from all current members?
- PARTIALLY DEFINED
- The proposal uses the term "median" but does not define exactly from which member set the center is derived: all current members, only the latest N members, or only synchronized same-direction members.

- Does adding a later member move the center?
- UNDEFINED
- The proposal does not define whether the center is recomputed atomically or stored immutably.

- If center moves, does historical geometry change?
- UNDEFINED
- This is a direct historical immutability risk if not specified.

- Is the center stored as a historical snapshot?
- UNDEFINED
- No historical snapshot semantics are defined.

- Is membership evaluated against current center or immutable creation center?
- UNDEFINED
- This is the key unresolved design decision.

- What happens if a zone contains an even number of members?
- PARTIALLY DEFINED in research helper only
- The implementation helper computes the arithmetic mean of the two middle values, but the proposal itself does not declare this as the formal rule.

- Is the median definition deterministic for even member counts?
- PARTIALLY DEFINED
- In the research helper it is deterministic, but in the proposal it is not stated as the authoritative historical rule.

## 8. Zone geometry audit

The proposal says "center plus member-span geometry" but does not specify a single geometry formula.

Possible interpretations in the proposal:
- center ± tolerance
- min(member prices) / max(member prices)
- center plus explicit member span derived historically
- another interval not listed

The proposal does not settle which one is authoritative.

If center ± tolerance:
- Is tolerance frozen at creation?
- UNDEFINED
- Does it update?
- UNDEFINED
- Is geometry recalculated after new members?
- UNDEFINED
- Can later tolerance changes mutate old geometry?
- UNDEFINED

If min/max:
- Does geometry expand when new members arrive?
- UNDEFINED
- Can it shrink?
- UNDEFINED
- What is historical geometry?
- UNDEFINED

Therefore:
- GEOMETRY: UNDEFINED
- The proposal does not state an exact interval definition, storage semantics, or historical immutability semantics.

## 9. Overlap audit

The proposal says overlap is to be prevented or handled, but it does not define the actual operational rule.

- When can two same-direction zones overlap?
- UNDEFINED
- There is no definition of overlap in terms of center distance, interval intersection, or member membership.

- Is overlap detected using center distance or interval intersection?
- UNDEFINED
- This choice materially changes the geometry and historical result.

- Are zones merged?
- UNDEFINED
- No merge policy is defined.

- If merged, which ID survives?
- UNDEFINED
- No ID survival rule is declared.

- What is the merged center?
- UNDEFINED
- Not defined.

- What is the merged tolerance?
- UNDEFINED
- Not defined.

- What happens to creation timestamps?
- UNDEFINED
- Not defined.

- Can merging happen retroactively?
- UNDEFINED
- Not defined.

- Can later information change historical overlap?
- UNDEFINED
- Not defined.

This means overlap handling is not just incomplete; it is structurally undefined and therefore unsafe to implement under the current proposal.

## 10. Minimum cluster-size audit

The earlier proposal used a minimum of 2 swings.

Classification:
- RESEARCH-SUPPORTED: the value 2 is a plausible minimal threshold for research
- PROPOSED: the value 2 is explicitly proposed as a starting point
- not FROZEN: it is not approved as the final specification
- arbitrary parameter: not yet justified as a final rule

Important point:
- The project must not assume 2 is correct merely because it is convenient or appears stable in a sample.
- The project also must not treat 2 as a freeze without human approval.

## 11. Determinism audit

The implementation must be deterministic, but several nondeterministic edges are not defined.

Potential nondeterministic operations and missing tie-breaks:
- equal distances: UNDEFINED
- equal timestamps: PARTIALLY DEFINED by canonical replay, but not by zone resolution rule
- equal prices: UNDEFINED
- even-number median: PARTIALLY DEFINED in research helper only, not in proposal
- multiple qualifying zones: PARTIALLY DEFINED
- overlapping zones: UNDEFINED
- stable zone IDs: PARTIALLY DEFINED as a concept only
- dictionary/set iteration: UNDEFINED in the proposal; must be avoided in implementation
- floating-point comparisons: UNDEFINED in tolerance and membership logic

Missing tie-breaks include:
- nearest center distance tie
- same-distance equal values across multiple zones
- equal creation timestamps
- equal zone IDs under a replay restart
- even-length member-set median choice
- overlap resolution if two intervals intersect equally

The proposal does not provide a complete deterministic rule set.

## 12. Multi-asset audit

The proposal is not yet validated as asset-agnostic.

The current evidence is BTC-EUR-centric and the discussion includes multiple implicit price-scale assumptions:
- absolute-price assumptions: yes, implied by any fixed-price tolerance
- price-scale assumptions: yes, implied by any fixed tolerance or any relative scaling without explicit normalization
- volatility assumptions: yes, implied by any gap-derived or median-derived rule used without explicit market-wide normalization
- hidden asset-specific constants: yes, as soon as a rule depends on absolute price levels, local price scale, or a fixed tolerance that is not normalized
- future market configuration requirements: UNDEFINED

The current architecture does not justify a multi-asset rule; therefore, the proposal remains effectively BTC-EUR-local unless explicitly revalidated.

## 13. Historical immutability audit

This is a critical audit item.

For every historical timestamp t, the proposal must specify whether later events may change:
- zone membership at t
- zone center at t
- zone geometry at t
- zone creation timestamp
- zone ID
- zone overlap state
- tolerance used at t

Current status:
- PROPOSED: no retroactive mutation should occur
- UNDEFINED: the exact historical snapshot semantics for all post-creation state updates
- HIGH RISK: without an append-only snapshot contract, later events could change earlier zone state in ways that break replay determinism

This means the proposal does not yet guarantee historical immutability in a formal implementation sense.

## 14. Complete unresolved-decision list

The following decisions are still required before the proposal can be considered implementation-ready:

1. Exact same-direction observation set for tolerance history.
2. Whether high and low streams maintain independent tolerance states.
3. Exact gap definition: adjacent-gap, center-to-center, or current-price-to-zone-center.
4. Absolute-gap vs relative-gap final selection.
5. Exact relative denomiator if relative gap is used.
6. Final history window semantics: count-based or time-based.
7. Exact history depth threshold.
8. Minimum-history fallback behavior.
9. Exact event-order update sequence for tolerance state.
10. Whether current swing is excluded from tolerance calculation.
11. Whether tolerance is computed before or after membership evaluation.
12. Exact median input target: absolute gap, relative gap, or another quantity.
13. Multiplier rule, if any.
14. Absolute floor rule, if any.
15. Relative floor/cap rule, if any.
16. Upper-cap rule, if any.
17. Lower-bound rule, if any.
18. Rule for zero tolerance values.
19. Rule for duplicate price values and zero gaps.
20. Rule if available history is below the required minimum.
21. Whether tolerance can change between swings.
22. Exact update policy for tolerance after each accepted swing.
23. Exact zone eligibility rule for active zones.
24. Exact zone center definition under dynamic updates.
25. Exact center immutability or mutation rule.
26. Exact historical snapshot semantics for zone center.
27. Exact zone geometry formula.
28. Whether geometry is center ± tolerance or min/max spread or another rule.
29. Whether geometry can change over time.
30. Whether historical geometry can be mutated by later members.
31. Exact overlap detection rule.
32. Exact overlap resolution rule: reject, assign, or merge.
33. Exact merge policy if merging is allowed.
34. Exact merge ID and merge timestamp semantics.
35. Exact rules for candidate assignment when no zone qualifies.
36. Exact rules for immediate zone creation.
37. Exact one-swing versus multi-swing transitional state.
38. Exact minimum cluster size and proof for it beyond a research proposal.
39. Exact deterministic tie-breaks for nearest-zone comparisons.
40. Exact deterministic tie-breaks for even-length median updates.
41. Exact stable zone ID policy.
42. Exact handling of equal distances, equal timestamps, and equal prices.
43. Exact floating-point tolerance semantics for comparisons.
44. Exact historical immutability contract after zone creation.
45. Exact replay-safe mutation policy for zone state.
46. Asset-agnostic validity of the rule beyond BTC-EUR.

This is a minimum unresolved list. The number may grow if the project chooses a stricter formal model for zone creation or overlap resolution.

## 15. Implementation-readiness verdict

IMPLEMENTATION-READINESS: REQUIRES SPECIFICATION DECISIONS

Not ARCHITECTURALLY UNSOUND in concept, but not implementation-ready in the strict deterministic sense. The proposal is still a design hypothesis, not a complete implementation contract.

It should not be treated as a frozen rule or as a production-ready tolerance model.

## 16. Governance status

FROZEN
- Group A swing semantics
- 15-minute operational bar contract
- canonical ordering and deterministic historical replay semantics for the approved inputs

RESEARCH-SUPPORTED
- rolling median as a robust statistic candidate
- same-direction-only structural evidence
- prior-observations-only causal intent

PROPOSED
- Group B zone mechanisms
- median center rule
- tolerance family choice
- overlap handling
- minimum cluster threshold

UNDEFINED
- all exact technical details required to implement the proposal deterministically

HUMAN DECISION REQUIRED
- final tolerance algorithm
- final membership semantics
- final center mutation / snapshot behavior
- final overlap rule
- final minimum cluster threshold
- final historical immutability contract
- final multi-asset validity review

## 17. Final audit verdict

The current proposal is a useful direction but not a complete rule set.

It is not sufficiently defined to implement without inventing missing technical decisions.

The strongest safe classification is:
- RESEARCH-SUPPORTED concept
- PROPOSED architecture
- REQUIRES SPECIFICATION DECISIONS before implementation
- Group B remains NOT FROZEN

## 18. Governance summary

FROZEN
- Group A: FROZEN
- 15m bar contract: FROZEN
- Group B: NOT FROZEN
- Phase 2: NOT STARTED
- Production behavior: unchanged

CONCLUSION
- The proposal includes a causal intent that is directionally sound.
- It does not contain a complete deterministic rule set.
- Hidden assumptions are present.
- Causal/lookahead risks remain unless explicit historical-order semantics are enforced.
- Historical mutation risks remain unless zone creation and update semantics are frozen as snapshot-only append operations.
