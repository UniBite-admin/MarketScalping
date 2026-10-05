# Group B Membership Decision Audit

## 1. Scope

This document is a governance/research audit only.

It addresses the final Group B root decision:

> Is Candidate A/D sufficiently supported to become the proposed membership rule?

This audit does not:

- modify production code
- modify tests
- modify canonical data
- start Phase 2
- freeze any decision
- invent missing rules
- optimize parameters
- run arbitrary new parameter sweeps

The purpose is to evaluate the structural semantics of the remaining membership candidates under the repository’s existing frozen rules and research-only sequential evidence.

Classification: REPOSITORY FACT

## 2. Existing frozen inputs

The following are the authoritative frozen inputs currently in effect and must be preserved exactly:

- 15-minute UTC bar contract
- HIGH/LOW streams are separate
- W = 5 prior legal same-direction gaps
- minimum tolerance history = 1
- tolerance = median of the latest available legal prior same-direction absolute gaps
- current swing is excluded from its own tolerance history
- zone center = median(member prices)

These are not a broader freeze of Group B. They are only the current frozen constraints for the tolerance-history and center-statistic boundary.

Classification: FROZEN

## 3. Candidate definitions

### 3.1 Candidate A / D

Candidate A / D is:

abs(incoming_price - current_zone_center) <= current_tolerance

Equivalent center-interval form:

current_zone_center - current_tolerance <= incoming_price <= current_zone_center + current_tolerance

Under the current frozen symmetric center definition, A and D are mathematically equivalent.

Classification: FROZEN / REPOSITORY FACT

### 3.2 Candidate B

Candidate B is:

min(abs(incoming_price - member_price)) <= current_tolerance

This uses the current tolerance and a member list, but introduces a different geometric reference: nearest-member proximity, not center displacement.

Classification: PROPOSAL ONLY

### 3.3 Candidate C

Candidate C remains blocked because the repository does not define an authoritative envelope expansion rule.

No valid member-envelope geometry is currently frozen, and the evidence does not permit a completion-by-assumption definition.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 4. Causal state analysis

### 4.1 Causal definition of A/D

A/D is causally well-defined if the following state is already known:

- current zone center
- current tolerance
- incoming eligible same-direction swing price
- same-direction stream ordering
- no future observation usage

This is the exact state already supported by the repository’s frozen rules and the minimal sequential research model.

A/D requires no new threshold, no new envelope expansion, and no additional geometry beyond the already-frozen center statistic and tolerance contract.

Classification: PROPOSAL ONLY

### 4.2 Does A/D preserve the frozen median-center semantics?

Yes, A/D preserves the frozen center semantics exactly because the center remains:

center = median(member prices)

The evaluation rule simply asks whether the incoming same-direction swing lies within the current tolerance radius of that median center.

This is consistent with the current frozen design and does not reinterpret the center statistic.

Classification: FROZEN

### 4.3 Does B require additional state semantics?

Yes. Candidate B depends on a member list and a nearest-member geometric interpretation, which implicitly assumes a more explicit Zone object than the repo currently freezes.

In particular, B requires:

- a current member set that is already defined and stable enough to compare against
- a deterministic choice of which member is nearest
- a clear member-update law once the Zone is created
- a clear understanding of whether the zone is center-based or member-based in its actual state representation

Those semantics are not frozen and not fully defined by repository evidence.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

### 4.4 What is the minimal causal state supported by the repo?

The repo supports a minimal causal state boundary consisting of:

- direction
- eligible same-direction observation sequence
- current member list (research assumption only)
- current center from member prices
- current tolerance from prior legal same-direction gaps
- no future lookahead

This is sufficient for A/D in a research-only model, but it is not yet sufficient to freeze the final Zone object or final membership law.

Classification: REPOSITORY FACT / PROPOSAL ONLY

## 5. A/D vs B evidence

The existing sequential evidence compares A/D and B under a research-only causal model using the frozen same-direction tolerance and the historical canonical stream. The raw comparison is not a final rule, but it does reveal the structural difference clearly.

Observed canonical comparisons:

- HIGH: 48 disagreements out of 76 opportunities
- LOW: 38 disagreements out of 66 opportunities
- total disagreements: 86 out of 142 opportunities

Disagreement pattern:

- A/D = false
- B = true

This means B is not merely a minor variant of A/D. It represents a different membership geometry.

Classification: EXPERIMENTAL EVIDENCE

### 5.1 Interpretation of the disagreement pattern

The disagreement pattern is structurally meaningful because the same incoming swing can be:

- far from the current center but still close to a nearest existing member

This exposes the actual semantic difference:

- A/D is center anchored
- B is member-proximate

These two are materially different geometries, not just different implementations of the same rule.

Classification: EXPERIMENTAL EVIDENCE

### 5.2 Are the 86 disagreements evidence against A/D?

No, not by themselves.

The 86 disagreements are evidence that B is a fundamentally different geometry. They are not evidence that A/D is invalid. They are evidence that the repository has not yet defined which geometry is authoritative.

The disagreement result is therefore a geometry comparison, not a rejection of A/D.

Classification: EXPERIMENTAL EVIDENCE

## 6. Interpretation of the 86 disagreements

The 86 disagreements are structurally important because they demonstrate that changing the membership reference changes the Zone membership regime materially.

This is not a parameter-optimization issue and not a profitability issue. It is a semantics question.

The disagreements are:

- common rather than isolated
- not tied to a single micro-case
- repeated across both directions
- consistent in direction: A/D rejects while B accepts

This suggests the core geometric issue is not random noise but the difference between center-based membership and member-nearest membership.

Classification: EXPERIMENTAL EVIDENCE

## 7. Repository evidence

### 7.1 Supporting evidence for A/D

The repo contains the following direct support for A/D:

- the center statistic is frozen as median(member prices)
- the tolerance contract is frozen and causal
- the same-direction sequence and canonical ordering are frozen
- the existing minimal sequential model can express A/D using only already-known state

This makes A/D the simplest rule consistent with the current repository evidence.

Classification: FROZEN / REPOSITORY FACT

### 7.2 Supporting evidence for B

The repo does not provide any authoritative requirement that nearest-member membership is the correct Zone semantics.

The repo supports a member list as a research construct, but it does not freeze nearest-member behavior as an authoritative rule.

There is therefore no repository evidence that requires B rather than A/D.

Classification: REPOSITORY FACT / UNRESOLVED

### 7.3 Supporting evidence for C

Candidate C is not supported because no authoritative envelope expansion rule exists in repository evidence.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 8. Decision readiness assessment

### 8.1 Is Candidate A/D sufficiently supported to become the proposed membership rule?

Yes, as a proposal only.

A/D is sufficiently supported to be the simplest defensible proposal under the project’s current frozen boundary because:

- it uses only already-known state
- it preserves the frozen median-center semantics
- it requires no new threshold or geometric assumption
- it is deterministic and causal
- it does not invent an envelope rule or nearest-member semantic that the repo does not authorize

However, this is not a final freeze-ready decision. It remains a proposed rule only.

Classification: PROPOSAL ONLY

### 8.2 Why not freeze it yet?

The repo still does not define the complete Zone object and lifecycle semantics. A final freeze would require more than a membership comparison. It would require:

- exact Zone creation semantics
- exact Zone object structure
- exact member-set update semantics
- exact state lifecycle
- exact overlap/merge behavior if applicable
- exact historical snapshot semantics

Without that, a membership freeze would be premature and would silently over-define the architecture.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 9. Remaining blockers

The remaining blockers before a final membership freeze are:

1. exact Zone creation trigger
2. exact Zone object semantics
3. exact member-set update law
4. exact lifecycle semantics for a Zone candidate vs valid Zone
5. exact treatment of membership state when center drifts
6. exact handling of multiple active zones or overlap if such behavior is allowed
7. exact invariant between center, tolerance, and member set over time

These blockers remain unresolved and prevent freezing the membership rule.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 10. Recommended next human decision

The recommended next human decision is not to freeze membership yet.

Instead, the next human decision should be:

- approve Candidate A/D as the simplest defensible membership proposal for continued research only
- explicitly keep Group B un-frozen
- require the Zone object + lifecycle contract to be resolved before any final membership freeze

This preserves the project’s cautious governance and avoids silently turning a proposal into a final rule.

Classification: PROPOSAL ONLY

## 11. Explicit governance statement

Group B remains NOT FROZEN.

Phase 2 remains NOT STARTED.

This audit is research-only and does not create a final Rule or architecture freeze.

Classification: REPOSITORY FACT

## 12. Final conclusion

Question: Is Candidate A/D sufficiently supported to become the proposed membership rule?

Answer: Yes, as a proposed rule under the current frozen boundary, but not as a frozen rule.

Reason:

- A/D is causally well-defined using already-known state.
- A/D preserves the frozen median-center semantics.
- B introduces materially different behavior and requires additional state semantics not currently frozen.
- The 86 observed A-vs-B disagreements are evidence that B represents a different geometry, not evidence that A/D is invalid.
- The repository does not require nearest-member membership.
- A/D is the simplest defensible rule under the project’s simplicity/correctness principles.
- A final membership freeze remains blocked by unresolved Zone object and lifecycle semantics.

Classification: PROPOSAL ONLY

## 13. Classification summary

- FROZEN: 15-minute bar contract; separated HIGH/LOW streams; W=5; minimum history=1; tolerance median rule; current swing excluded from its own history; center = median(member prices)
- REPOSITORY FACT: minimal causal sequential state is supported; no authoritative nearest-member requirement exists in repo evidence; Group B remains not frozen; Phase 2 remains not started
- EXPERIMENTAL EVIDENCE: A/D vs B disagreement structure; 86 disagreements across canonical sequential evaluation; B is materially different geometry
- PROPOSAL ONLY: A/D as simplest defensible proposal; B as research-only alternative; research-only seed/candidate/append-only baseline
- UNRESOLVED: final Zone object; final member-update law; final lifecycle semantics; final overlap semantics
- BLOCKED BY UNRESOLVED ROOT DECISION: Candidate C; any final membership freeze

## 14. Verification

The task was limited to creating this audit document. The verification step was:

```powershell
git diff --check
```

This passed with no diff-check errors.

The file created for this task is:

- docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DECISION_AUDIT.md

No production code, test files, or dataset files were modified by this task.

Classification: REPOSITORY FACT
