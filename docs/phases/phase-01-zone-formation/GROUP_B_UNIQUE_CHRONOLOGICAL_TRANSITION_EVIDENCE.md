# Group B Unique Chronological Transition Evidence

## 1. Objective

This document is a final methodology gate for Phase 1 Group B. It is research-only and does not modify production code, executable tests, frozen decisions, or authoritative specifications. It does not start Phase 2, does not freeze lifecycle behavior, and does not choose a Zone lifecycle model.

The governing question is:

> Can more than the FIRST lifecycle-independent valid Zone creation be established from the currently frozen rules?

The required answer is: not unless the repository explicitly freezes the lifecycle semantics after creation.

This audit therefore stops at the first authorized valid Zone creation and the immediate next unique same-direction swing. After that point, the path to any further Zone creation, persistence, replacement, or retirement requires a separate lifecycle decision and is therefore blocked.

## 2. Frozen evidence

The following are the only frozen evidentiary inputs used here:

- Group A swing definition: FROZEN
- 15-minute UTC bar contract: FROZEN
- canonical replay ordering: FROZEN
- causal / no-lookahead eligibility: FROZEN
- HIGH and LOW remain separate: FROZEN
- W = 5 prior same-direction legal gaps: FROZEN
- minimum history = 1: FROZEN
- tolerance = median of selected prior same-direction absolute legal gaps: FROZEN
- current swing excluded from its own tolerance history: FROZEN
- center = median(member prices): FROZEN
- membership predicate: abs(incoming_swing_price - current_zone_center) <= current_tolerance : FROZEN narrow rule
- Zone creation rule: first eligible same-direction swing = candidate/seed; the first later same-direction swing that satisfies the membership predicate = valid Zone creation : FROZEN narrow rule

These are the only authoritative statements in scope. They do not authorize any of the following after the first Zone is created:

- retiring the valid Zone
- replacing the valid Zone
- creating a new candidate while the previous Zone still remains valid
- allowing multiple Zones
- resetting Zone state after creation
- discarding the previous Zone
- continuing Zone formation after a non-member
- member-set update semantics

## 3. Authoritative sequential logic

The earliest authorized sequence is:

1. first eligible same-direction swing → candidate / seed
2. first subsequent same-direction swing that satisfies the membership predicate → valid Zone creation

This is the only lifecycle-independent creation sequence currently established by the frozen rules.

After that first valid Zone exists, the next step is not a new Zone creation. The next step is only the immediate next eligible same-direction swing, which must be classified mathematically as one of the following under the then-current Zone state:

- MEMBER
- NON_MEMBER
- UNCLASSIFIABLE

This classification is a mathematical fact about the current Zone state. It is not a Zone lifecycle transition.

## 4. Mathematical membership classification is separate from Zone state transition

The frozen membership predicate is:

abs(incoming_price - current_zone_center) <= current_tolerance

This expression may be evaluated for the immediate next historical swing after the first valid Zone creation.

However, the following must not be inferred unless explicitly frozen:

- the Zone persists
- the Zone updates its member set
- the Zone is retired
- the Zone is replaced
- a new candidate is created while the Zone remains valid
- another Zone is started
- previous Zone state is reset

The first is evidence-supported. The second is unresolved unless explicitly frozen.

## 5. Lifecycle-independent evidence

The lifecycle-independent evidence boundary is reached at the first valid Zone creation and the immediate next unique same-direction swing.

At this boundary, the following is valid evidence:

- the first eligible same-direction swing does become a candidate/seed
- the first later qualifying same-direction swing does create a valid Zone under the frozen rule
- the immediate next unique same-direction swing can be classified as MEMBER, NON_MEMBER, or UNCLASSIFIABLE using the frozen membership predicate for the current Zone

Anything beyond this boundary is not lifecycle-independent evidence.

## 6. Lifecycle-dependent research

The following are lifecycle-dependent research questions and are not evidence-supported as current frozen behavior:

- whether the Zone persists after the immediate next swing
- whether a non-member causes the Zone to remain unchanged, update, retire, or be replaced
- whether a new candidate may be started after a valid Zone already exists
- whether multiple Zones may coexist
- whether the Zone may be invalidated and restarted
- whether the member set continues to update without a separate lifecycle decision
- whether continued Zone formation after a non-member is permitted

These are not frozen facts. They are candidate research behaviors only.

## 7. Blocked evidence

The following evidence is blocked and must be marked exactly as:

BLOCKED BY UNRESOLVED LIFECYCLE SEMANTICS

- any claim that more than the first valid Zone creation is lifecycle-independent evidence
- any count of repeated Zone creation events after the first valid Zone without explicit lifecycle authorization
- any count depending on candidate = None reset/restart semantics
- any count that assumes a previous Zone can be discarded, replaced, or superseded without being frozen
- any state-machine semantics that continue after the immediate next swing without a frozen lifecycle rule

## 8. Final conclusion on 27 / 23 creation counts

The previous figures:

- HIGH: 27 valid Zone creations
- LOW: 23 valid Zone creations

are not valid lifecycle-independent evidence under the currently frozen rules.

They are rejected as lifecycle-independent evidence if they depend on any of the following post-creation semantics:

- resetting the candidate state after a valid Zone creation
- treating the prior Zone as no longer active
- continuing Zone formation in a new historical Zone context
- creating another valid Zone from the same direction without explicit lifecycle authorization
- inferring repeated valid Zone creation from sequential continuation logic that is not frozen

This is the required explicit statement:

REJECTED AS LIFECYCLE-INDEPENDENT EVIDENCE

The repository currently authorizes only the earliest valid Zone creation event and the immediate next swing classification under the frozen predicate. It does not authorize additional Zone creation counts as lifecycle-independent evidence.

## 9. Required boundary

The maximum valid research result under the frozen rules is therefore:

- first eligible same-direction swing → candidate/seed
- first subsequent qualifying same-direction swing → valid Zone creation
- immediate subsequent same-direction swing → MEMBER / NON_MEMBER / UNCLASSIFIABLE under the frozen predicate

After that point, the correct research behavior is:

BLOCKED BY UNRESOLVED LIFECYCLE SEMANTICS

No reset of candidate.
No new Zone creation.
No continuation into another historical Zone context.
No state transition beyond the mathematically classified immediate next swing.

This is the valid evidence boundary and the correct final methodology result.

These are blocked because the repository does not freeze the lifecycle semantics required to define them.

The immediate next swing is the last point at which the frozen creation and membership rules alone are sufficient to assign evidence without requiring a lifecycle decision.

# 11. Causality / No-Lookahead Audit

The unique immediate-next evidence was inspected against the frozen causal contract.

For every measured calculation:

- swing confirmation precedes use: yes, the swing is only used after it is in canonical replay order and eligible under the frozen rule
- swing eligibility precedes use: yes, the immediate next swing is only evaluated if it is an eligible same-direction swing
- only prior information is used: yes, current and earlier information is used; future data is not
- current swing is excluded from its own tolerance history: yes, this matches the frozen rule
- no future swing is used: yes, the metric uses the immediate next unique swing only
- canonical ordering is preserved: yes, the historical sequence is processed in canonical order
- no later Zone behavior is used to classify the current transition: yes, this is a key control of the audit

This means the unique immediate-next evidence is causally valid. It is not a lifecycle simulation.

# 12. Duplicate Evaluation Audit

This audit explicitly enforces zero duplicate counts.

The strict rule is:

- each historical eligible swing is represented once by its unique identity
- the same future swing is never reused as a separate observation across multiple Zone contexts
- no repeated historical window is restarted from each creation event

The strict unique-pass implementation produced:

| Direction | Duplicate evaluations |
|---|---:|
| HIGH | 0 |
| LOW | 0 |

This is the required result. Any non-zero duplicate count would invalidate the evidence as a lifecycle comparison and would require the research implementation to be fixed before conclusions are reported.

# 13. Evidence Classification

The following are classified as FROZEN:

- Group A swing definition
- 15-minute UTC bar contract
- W = 5 prior same-direction legal gaps
- minimum history = 1
- tolerance rule = median of selected prior gaps
- center = median(member prices)
- membership rule for valid Zone
- creation rule for valid Zone

The following are classified as EVIDENCE-SUPPORTED:

- there are 78 eligible HIGH swings and 68 eligible LOW swings
- there are 27 valid HIGH creation events and 23 valid LOW creation events under the frozen creation rule
- the immediate next unique swing after each creation event can be classified as MEMBER or NON_MEMBER for most cases
- the immediate next EU evidence is one-pass and unique

The following are classified as DESCRIPTIVE:

- the immediate next transition counts
- the immediate member / non-member counts
- the median / p75 / p90 / p95 statistics for absolute distance, tolerance, and ratio

The following are classified as BLOCKED BY UNRESOLVED LIFECYCLE SEMANTICS:

- any metric requiring Zone persistence after the immediate next swing
- any metric requiring candidate coexistence
- any metric requiring Zone retirement / invalidation / replacement / stale-zone handling
- repeated counts against multiple historical Zone contexts
- anything beyond the immediate next unique swing after a creation event

The following are classified as UNRESOLVED:

- single-active-zone semantics
- multiple-active-zone semantics
- non-member lifecycle semantics
- candidate lifetime semantics

# 14. Unresolved Questions

The following remain unresolved and outside the evidence established by the frozen rules:

1. What happens after a valid Zone sees a non-member immediate next swing?
2. Does the existing Zone persist, retire, or remain active?
3. Can a new candidate coexist with a valid Zone?
4. Can a valid Zone be replaced or invalidated?
5. Can multiple Zones coexist in the same direction?
6. What is the state transition law after a non-member?
7. What is the lifecycle semantics for stale or inactive Zones?

These questions remain governance questions and are outside the boundary of this research-only evidence audit.

# 15. Governance Status

- Group A: FROZEN
- 15-minute bar contract: FROZEN
- W=5/minimum history=1: FROZEN
- tolerance rule: FROZEN
- center=median(member prices): FROZEN
- membership rule: FROZEN narrow rule
- creation rule: FROZEN narrow rule
- Group B as a whole: NOT FROZEN
- Single Active Zone: RESEARCH CANDIDATE ONLY
- Non-member lifecycle: UNRESOLVED
- Phase 2: NOT STARTED
- Production behavior: UNCHANGED

# 16. Final Conclusion

The unique chronological evidence established by the existing historical data before a lifecycle decision becomes necessary is this:

- the canonical same-direction sequence contains 78 eligible HIGH swings and 68 eligible LOW swings
- under the frozen creation rule, the one-pass chronology identifies 27 valid HIGH Zone creation events and 23 valid LOW Zone creation events
- for each valid Zone creation event, the immediate next unique eligible same-direction swing can be classified once without repeating the same historical swing across multiple Zone contexts
- in HIGH, 13 immediate next swings are MEMBERS and 14 are NON_MEMBERS, with 0 unclassifiable cases
- in LOW, 11 immediate next swings are MEMBERS, 11 are NON_MEMBERS, and 1 is UNCLASSIFIABLE because the frozen tolerance state is not available
- duplicate evaluation count is ZERO under the strict unique-swing counting contract

This is the strongest valid evidence available before any lifecycle decision becomes necessary.

It does not establish which lifecycle model should be selected. It does not establish Zone persistence, retirement, replacement, candidate coexistence, or a single-active-zone rule. Those remain unresolved and outside this research-only evidence gate.
