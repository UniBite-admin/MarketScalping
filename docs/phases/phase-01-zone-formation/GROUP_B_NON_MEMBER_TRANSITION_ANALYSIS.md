# Group B Non-Member Transition Analysis

## 1. Objective

This research analyzes the consequence of a single-active-zone baseline when a valid same-direction Zone already exists and a new eligible same-direction swing does not satisfy the frozen membership rule.

The question is:

> Given the currently frozen Phase 1 Group B rules, what are the measurable consequences of different candidate behaviors when a valid same-direction Zone already exists and a new eligible same-direction swing does not satisfy the frozen membership rule?

This is a research-only historical analysis. It does not implement production logic, does not freeze a lifecycle rule, does not start Phase 2, and does not alter any authoritative specification.

## 2. Frozen Inputs

The following are already FROZEN and authoritative for this analysis:

- Group A swing definition: FROZEN — HUMAN APPROVED
- 15-minute UTC bar contract: FROZEN — HUMAN APPROVED
- canonical replay ordering: FROZEN — HUMAN APPROVED
- causal / no-lookahead eligibility: FROZEN — HUMAN APPROVED
- HIGH and LOW streams remain separate: FROZEN — HUMAN APPROVED
- W = 5 prior same-direction legal gaps: FROZEN — HUMAN APPROVED
- minimum history = 1: FROZEN — HUMAN APPROVED
- tolerance = median of selected prior same-direction absolute legal gaps: FROZEN — HUMAN APPROVED
- center = median(member prices): FROZEN — HUMAN APPROVED
- valid-Zone membership rule:
  abs(incoming_swing_price - current_zone_center) <= current_tolerance
  FROZEN — narrow rule
- Zone creation rule:
  - first eligible same-direction swing = candidate/seed
  - a later same-direction swing that qualifies as a member creates the valid Zone
  FROZEN — narrow rule

Important governance boundary:

- Group B as a whole remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- production behavior remains unchanged.

## 3. Historical Dataset and Method

This analysis uses the repository’s existing canonical historical reconstruction and the already-established 15-minute bar logic.

Authoritative sources used:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/BAR_CONTRACT_DECISION.md](BAR_CONTRACT_DECISION.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

Method discipline:

- Use real eligible HIGH and LOW swing sequences only.
- Preserve canonical chronological order.
- Evaluate each swing using only information available at that replay point.
- Never inject a new tolerance parameter, new dataset, or synthetic sequence.
- Keep the experiment strictly as a comparison of candidate transition behaviors under a single-active-zone baseline.

This analysis is a measurement of historical consequences, not a frozen rule.

## 4. Historical Swing Transition Evidence

The repository’s real reconstructed 15-minute data gives the following baseline counts under the frozen rules when a minimal sequential creation model is applied to the same-direction eligible swing stream.

For the real eligible swing sequences:

- HIGH: 78 eligible swings
- LOW: 68 eligible swings

Under the minimal historical creation rule, using only the already-frozen candidate/seed and valid-Zone creation logic:

- HIGH: 27 valid Zone creation events were observed in the minimal historical pass.
- LOW: 23 valid Zone creation events were observed in the minimal historical pass.

Post-creation follow-up under the frozen membership rule, measured using the same real historical sequence and the current zone-members state, produced the following descriptive numbers:

- HIGH: 46 subsequent member swings vs 968 subsequent non-member swings after a valid Zone creation event
- LOW: 23 subsequent member swings vs 767 subsequent non-member swings after a valid Zone creation event

This is a descriptive measurement of the real data, not a lifecycle rule.

Classification:

- EVIDENCE-SUPPORTED: the real historical sequences are dominated by non-member outcomes after a valid Zone has already been created.
- EVIDENCE-SUPPORTED: the frozen rule does not itself define what to do with those non-member observations.
- UNRESOLVED: which non-member response should be adopted as a lifecycle rule.

## 5. Model A — Persist + Ignore

MODEL A — PERSIST + IGNORE

When a valid Zone exists and an eligible same-direction swing is a non-member:

- keep the existing valid Zone unchanged
- do not create a new candidate from that swing
- continue processing future eligible swings against the existing Zone

This model is a RESEARCH CANDIDATE only.

### Measurable historical consequence

Under the real historical sequence, after a valid Zone has already formed, the subsequent same-direction sequence is overwhelmingly non-member rather than member.

The measurement shows:

- HIGH: 968 non-members vs 46 members after zone creation in the minimal sequential measurement
- LOW: 767 non-members vs 23 members after zone creation in the minimal sequential measurement

This means that if Model A were used, the historical record would frequently contain many observed non-member swings that are simply ignored for zone formation.

### Consequences to report

- how many non-member swings would be ignored: RESEARCH CANDIDATE measurement from historical sequence
- how often later swings return to the existing Zone: UNRESOLVED under the current frozen rules, because the repo does not define return logic or zone persistence semantics
- how long the existing Zone would continue receiving observations: UNRESOLVED, because ongoing lifecycle is not frozen
- how many historical sequences would remain attached to the original Zone: UNRESOLVED unless a later lifecycle rule is specified

### Classification

- RESEARCH CANDIDATE: Model A is a candidate behavior under a single-active-zone baseline.
- UNRESOLVED: whether the model is operationally safe or desirable.
- ASSUMPTION: any claim that ignored non-members are harmless without a freeze decision.

## 6. Model B — Persist + New Candidate

MODEL B — PERSIST + NEW CANDIDATE

When a valid Zone exists and an eligible same-direction swing is a non-member:

- keep the existing valid Zone
- create a new pending candidate/seed from the non-member swing
- investigate what would happen if later swings qualify against that candidate

This model is a RESEARCH CANDIDATE only.

### What the repository currently allows

The repo provides evidence for:

- candidate/seed state
- valid Zone state
- same-direction causality
- no-lookahead evaluation

What the repo does not provide:

- an explicit rule defining coexistence of a valid Zone and a pending candidate in the same direction
- a rule for candidate lifetime
- a rule for whether a candidate can be created while a valid Zone remains active
- a rule for multiple pending candidates
- a rule for selecting among multiple candidates

### Measurable historical consequence

The historical record naturally contains many non-member swings after a Zone is formed. That means a pending candidate could be created repeatedly under this model.

However, the repo does not define how that candidate would be evaluated under the already-frozen membership rules when a valid Zone is still active.

This is not a frozen rule and not a repository-supported model.

### Specific limitations

- UNRESOLVED: one valid Zone plus one pending seed
- UNRESOLVED: one valid Zone plus multiple pending seeds
- UNRESOLVED: whether the candidate must be abandoned if the valid Zone remains active
- UNRESOLVED: whether candidate creation should be suppressed when the existing Zone is still the active one
- ASSUMPTION: any requirement that a pending candidate should be evaluated against the same tolerance rules without a frozen rule for candidate/valid coexistence

### Classification

- RESEARCH CANDIDATE: Model B is an analytical comparison model only.
- UNRESOLVED: whether it is even legal under the current frozen decision set.
- ASSUMPTION: any candidate/valid coexistence rule is not repository evidence.

## 7. Model C — Retire + New Candidate

MODEL C — RETIRE + NEW CANDIDATE

When a valid Zone exists and an eligible same-direction swing is a non-member:

- retire / invalidate the existing Zone
- use the non-member swing as a new candidate/seed

This behavior is a RESEARCH CANDIDATE only.

Retirement / invalidation is NOT currently frozen.

### Historical consequence

This model would create a large number of destructive state transitions if applied to the real sequence, because the historical data contains many non-member swings after the original Zone formation.

It is especially consequential because:

- the repo does not define expiration, invalidation, or replacement semantics
- the repository explicitly does not freeze lifecycle / stale-Zone handling
- the data shows a very large proportion of non-member observations after Zone creation, which would produce many retirements in a naive implementation

Under the minimal historical measurement, the non-member rate is extremely high in both directions:

- HIGH: 968 non-member swings after zone creation
- LOW: 767 non-member swings after zone creation

This does not prove the model is correct; it only shows the potentially destructive operational consequence of applying a retirement rule without a governance decision.

### Classification

- RESEARCH CANDIDATE: Model C is a comparison model only.
- UNRESOLVED: whether retirement/invalidation is permitted at all.
- UNRESOLVED: whether a new candidate should replace the active Zone immediately after a single non-member event.
- ASSUMPTION: any retirement rule would be an unapproved design assumption.

## 8. HIGH vs LOW Comparison

The repo treats HIGH and LOW as separate streams and the frozen rules preserve that separation.

Under the historical measurement:

- HIGH produced 78 eligible swings and 27 minimal valid Zone creation events.
- LOW produced 68 eligible swings and 23 minimal valid Zone creation events.

Following valid Zone creation, the raw non-member dominance was similar in both directions:

- HIGH: 968 non-members vs 46 members
- LOW: 767 non-members vs 23 members

This suggests that the problem is not direction-specific in a way that would justify a separate lifecycle rule by itself. However, the repo does not define a final rule for handling the non-member outcome in either direction.

Classification:

- EVIDENCE-SUPPORTED: the same qualitative pattern appears in both HIGH and LOW sequences.
- UNRESOLVED: whether the same transition policy should apply to both directions.
- ASSUMPTION: any single policy choice across directions would still require explicit approval.

## 9. Causality / No-Lookahead Audit

The analysis preserves the existing Phase 1 causal contract.

For every transition under the historical measurement:

- the swing was confirmed before use: EVIDENCE-SUPPORTED by the frozen Group A rule and the canonical replay process
- the swing was eligible before use: EVIDENCE-SUPPORTED by the same canonical selection rule
- only prior information was used: EVIDENCE-SUPPORTED by the frozen no-lookahead rule
- the current swing was not used in its own tolerance history: FROZEN — HUMAN APPROVED
- no future swing was used to decide the current transition: EVIDENCE-SUPPORTED under the canonical replay discipline
- canonical chronological ordering was preserved: EVIDENCE-SUPPORTED

What this means:

- the historical measurement itself is causally valid under the current Phase 1 contract,
- but it does not prove the correct lifecycle response after a non-member swing,
- the data only demonstrates the downstream frequency of non-member events after a valid Zone exists.

## 10. Evidence Classification

The main conclusions are classified as follows:

- FROZEN: the Group A swing rule, 15-minute bar contract, causal ordering, and the existing membership / creation rules
- EVIDENCE-SUPPORTED: the real historical data contains a very large proportion of non-member swings after a valid Zone exists
- EVIDENCE-SUPPORTED: the repository does not define a valid lifecycle response to those non-member swings
- RESEARCH CANDIDATE: Model A, Model B, and Model C are analytical counterfactuals only
- UNRESOLVED: which non-member transition should be permitted by governance
- ASSUMPTION: any lifecycle interpretation not explicitly approved by human decision

## 11. Unresolved Questions

The following questions remain UNRESOLVED and cannot be answered by the repo alone:

1. When a valid Zone exists and a new same-direction eligible swing is a non-member, is the existing Zone kept, ignored, replaced, or invalidated?
2. Is a pending candidate allowed to coexist with a valid Zone in the same direction?
3. Can more than one pending candidate exist at a time?
4. Is a non-member swing discarded silently, or is it recorded as an event for later reevaluation?
5. Can a valid Zone be retired or invalidated?
6. Is the active Zone identity persistent or ephemeral?
7. Is the decision same for HIGH and LOW or direction-specific?
8. Are non-member swings allowed to trigger a new seed at the same moment a valid Zone still exists?
9. What exact transition law is required to preserve causal replay determinism under single-active-zone semantics?

## 12. Recommended Human Decision Gate

The required human decision gate is operational and narrow:

> When a valid Zone exists and a new eligible same-direction swing is a non-member, what transition is permitted?

This is the smallest concrete governance decision required before the project can safely define single-active-zone lifecycle semantics.

The historical evidence does not justify freezing a lifecycle rule yet. It only demonstrates that the real sequence produces many non-member transitions after valid Zone creation.

The next required research, if the human wants a stronger evidence base, is limited to the following:

- define the allowed transition state after a valid Zone and a same-direction non-member
- decide whether candidate coexistence is legal
- decide whether a valid Zone may be kept, invalidated, or retired
- define the exact causal ordering of any such transition

This is still a research gate, not an implementation gate.

## 13. Governance Status

- Group A swing definition: FROZEN — HUMAN APPROVED
- 15-minute UTC bar contract: FROZEN — HUMAN APPROVED
- canonical replay ordering: FROZEN — HUMAN APPROVED
- causal / no-lookahead eligibility: FROZEN — HUMAN APPROVED
- HIGH and LOW streams remain separate: FROZEN — HUMAN APPROVED
- W = 5 prior same-direction legal gaps: FROZEN — HUMAN APPROVED
- minimum tolerance history = 1: FROZEN — HUMAN APPROVED
- tolerance = median of selected prior same-direction absolute legal gaps: FROZEN — HUMAN APPROVED
- center = median(member prices): FROZEN — HUMAN APPROVED
- valid-Zone membership rule: FROZEN — narrow rule
- Zone creation rule: FROZEN — narrow rule
- Group B as a whole: NOT FROZEN
- single-active-zone baseline: RESEARCH CANDIDATE ONLY
- non-member lifecycle behavior: UNRESOLVED
- Phase 2: NOT STARTED
- production behavior: unchanged

## 14. Final Conclusion

The historical data demonstrates the following:

- under the real canonical sequence, valid Zone creation is followed by a large number of non-member same-direction swings in both HIGH and LOW
- the frozen rules determine whether a swing is a member or non-member, but they do not define what the system must do after a valid Zone already exists and a non-member arrives
- all three candidate behaviors — Model A, Model B, and Model C — are useful for comparison but remain RESEARCH CANDIDATES, not frozen semantics

The historical data does NOT demonstrate:

- that any lifecycle model is correct
- that a valid Zone should be ignored, replaced, retired, or left active while a new candidate is created
- that a single-active-zone policy is appropriately justified without explicit human governance

Therefore:

- The repo does not justify freezing a non-member transition lifecycle rule.
- The historical evidence supports a human decision gate, not a final rule.
- Another research gate is required before implementation, but it is limited to the operational decision: when a valid Zone exists and a new eligible same-direction swing is a non-member, what transition is permitted?

This is the required next governance question.
