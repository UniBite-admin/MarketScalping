# Group B Membership Final Candidate Audit

## Status

RESEARCH ONLY

- Group B remains NOT FROZEN.
- Phase 2 remains NOT STARTED.
- No production code was modified.
- No production tests were modified.
- No canonical data was modified.
- No frozen decision was created or changed.
- This document is an audit only.

## 1. Objective

This audit addresses the next Group B root decision:

> Zone Membership Rule

The objective is not to freeze a rule. The objective is to determine whether the repository evidence and actual canonical data are sufficient to distinguish the surviving membership candidates under a minimal causal sequential model.

This audit uses only the frozen infrastructure already approved, plus a research-only sequential simulation that is explicitly labeled non-frozen.

## 2. Current evidence boundary

### 2.1 FROZEN

- Phase 1 Group A swing definition
- 15-minute UTC bar contract
- HIGH/LOW streams are separate
- W = 5
- minimum tolerance history = 1
- tolerance = median of selected legal prior same-direction gaps
- current swing excluded from its own tolerance history
- center = median(member prices)

### 2.2 PROPOSAL ONLY

These remain proposals only and are not frozen:

- first eligible same-direction swing → candidate/seed
- second qualifying same-direction observation → valid Zone
- append-only member-set update

### 2.3 Previously established

- Candidate A and D were already identified as mathematically equivalent under the current symmetric center definition.
- current clustering research is descriptive, not a live sequential Zone engine
- membership cannot be inferred from descriptive cluster counts
- the minimal Zone state boundary is now understood sufficiently for a research-only sequential model
- member-set update semantics have a simplest defensible proposal: append-only
- exact membership remains unresolved

## 3. Research-only assumptions for this audit

This section is intentionally explicit:

The following are research assumptions used only for this audit. They are NOT frozen and do not become part of the repo’s final architecture.

- a Zone candidate exists after the second same-direction observation in the same-direction stream
- the emerging Zone is represented by a current append-only member list
- current center = median(current member prices)
- current tolerance = median of the last valid same-direction prior legal gaps, using the frozen same-direction / W=5 / minimum-history=1 contract
- the incoming swing is evaluated only using already-observed data
- the current swing is excluded from its own tolerance history
- no future observations are used

This is a causal sequential research model only. It is not a production rule and cannot be treated as a final freeze.

## 4. Candidate definitions under evaluation

### 4.1 Candidate A / D — center-distance

An incoming eligible same-direction swing is a member if:

abs(price - current_center) <= current_tolerance

This is mathematically equivalent to the center interval form:

current_center - current_tolerance <= price <= current_center + current_tolerance

So Candidate A and Candidate D are treated as one candidate for this audit.

Classification: RESEARCH PROPOSAL / NOT FROZEN

### 4.2 Candidate B — nearest-member

An incoming swing is a member if its distance to the nearest existing member price satisfies the current tolerance condition:

min(|price - member_j|) <= current_tolerance

This uses only the frozen tolerance and a member list. It does not introduce another threshold.

Classification: RESEARCH PROPOSAL / NOT FROZEN

### 4.3 Candidate C — member-envelope

This candidate depends on an envelope defined by the existing member set.

The repository evidence does not define the envelope, its expansion law, or its update semantics. The repo does not freeze a rule such as:

- min/max of members
- center ± tolerance
- expanded envelope
- adaptive envelope

Any such formula would be an invented assumption.

Therefore Candidate C is not fully definable from the current evidence.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 5. Canonical verification before analysis

The existing canonical 15-minute reconstruction was verified before the sequential comparison.

Command used:

```powershell
.\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"
```

Observed output:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

These are the baseline counts used for this audit.

Classification: REPOSITORY FACT

## 6. Sequential data model used for the comparison

For each direction separately:

1. process eligible swings in chronological order
2. maintain a research-only candidate/seed state
3. use the two-observation Zone baseline as a research assumption only
4. use append-only member update as a research assumption only
5. calculate current median center from current members
6. calculate current causal tolerance from prior same-direction legal gaps only
7. evaluate the incoming swing against Candidate A/D and Candidate B
8. record accept / reject outcomes
9. never use future observations

Candidate C was not numerically evaluated because it lacks a valid repository-defined envelope rule.

This is a strict causal evaluation, not a descriptive cluster summary.

## 7. Actual-data results

### 7.1 HIGH stream

Research assumption: 78 eligible HIGH swings

Observed sequential results:

- membership opportunities: 76
- Candidate A / D accepted: 3
- Candidate A / D rejected: 73
- Candidate A / D acceptance rate: 0.0395 = 3.95%
- Candidate B accepted: 51
- Candidate B rejected: 25
- Candidate B acceptance rate: 0.6711 = 67.11%
- disagreements between A/D and B: 48
- all disagreements were A/D = false, B = true

### 7.2 LOW stream

Research assumption: 68 eligible LOW swings

Observed sequential results:

- membership opportunities: 66
- Candidate A / D accepted: 3
- Candidate A / D rejected: 63
- Candidate A / D acceptance rate: 0.0455 = 4.55%
- Candidate B accepted: 41
- Candidate B rejected: 25
- Candidate B acceptance rate: 0.6212 = 62.12%
- disagreements between A/D and B: 38
- all disagreements were A/D = false, B = true

### 7.3 Structural interpretation

These are not minor differences; they are large structural differences.

Under the minimal causal sequential model:

- Candidate A / D is very strict
- Candidate B is materially more permissive
- A and B disagree in a large fraction of opportunities
- every observed disagreement in this model is of the form:
  - A/D rejects
  - B accepts

That means Candidate B is not merely a different tie-breaker; it is a different membership regime.

Classification: EXPERIMENTAL EVIDENCE

## 8. First concrete disagreement cases

The data contains many disagreements. The first case is enough to show the structural reason.

### 8.1 First HIGH disagreement

Time: 2020-01-01 15:45:00 UTC

Incoming swing price: 6443.76

Current member set:

- 6406.00
- 6450.00
- 6667.22
- 6736.36
- 6744.02
- 6752.33
- 6753.91

Current center:

- median(member prices) = 6736.36

Current tolerance:

- median of prior same-direction legal gaps = 17.55

Distances:

- distance to center = |6443.76 - 6736.36| = 292.60
- nearest member distance = min(|6443.76 - 6406.00|, |6443.76 - 6450.00|, ...) = 6.24

Candidate decisions:

- Candidate A / D: false, because 292.60 > 17.55
- Candidate B: true, because 6.24 <= 17.55

Interpretation:

This is the essence of the disagreement. The current center has drifted away from the incoming swing, but the new price is still close to the nearest existing member. The member-centered model accepts it; the center-centered model rejects it.

This is not a data anomaly. It is the dominant pattern across the disagreement set.

### 8.2 First LOW disagreement

Time: 2020-01-01 13:00:00 UTC

Incoming swing price: 6397.73

Current member set:

- 6405.99
- 6601.00
- 6620.00
- 6681.00
- 6718.60

Current center:

- median(member prices) = 6620.00

Current tolerance:

- median of prior same-direction legal gaps = 98.80

Distances:

- distance to center = |6397.73 - 6620.00| = 222.27
- nearest member distance = min(|6397.73 - 6405.99|, |6397.73 - 6601.00|, ...) = 8.26

Candidate decisions:

- Candidate A / D: false, because 222.27 > 98.80
- Candidate B: true, because 8.26 <= 98.80

Interpretation:

The same structural pattern occurs in the LOW stream: a center-displaced candidate is still close to the nearest member and is therefore accepted by nearest-member logic but rejected by center-distance logic.

## 9. Why Candidate C is blocked

Candidate C — member-envelope — cannot be evaluated in a valid way without an envelope rule that the repo does not define.

The repo evidence supports:

- member set exists as a historical collection of observations
- center = median(member prices)
- tolerance = median of selected prior same-direction legal gaps

But it does not freeze:

- the envelope definition
- the envelope expansion rule
- the update rule for the envelope as members accumulate
- the geometric meaning of “inside the envelope”

Therefore, Candidate C cannot be evaluated as a final comparison without inventing a new geometry.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 10. Is A / D fully equivalent?

Yes, under the frozen symmetric center definition.

Candidate A / D is the same rule written in two forms:

- A: abs(price - center) <= tolerance
- D: center - tolerance <= price <= center + tolerance

The equivalence is exact:

abs(price - center) <= tolerance
iff
-center - tolerance <= ???

More precisely:

|x - c| <= T
iff
c - T <= x <= c + T

So A and D are mathematically identical under the current frozen symmetric definition.

Classification: FROZEN / REPOSITORY FACT

## 11. Is Candidate B fully definable?

Yes, under the minimal research model it is fully definable.

It requires only:

- a current member list
- current tolerance
- nearest distance to an existing member

No extra threshold is introduced.

This makes Candidate B a valid causal sequential research candidate under the current freeze boundary.

Classification: RESEARCH PROPOSAL / NOT FROZEN

## 12. Is Candidate C fully definable?

No.

It is not fully definable from current evidence because its envelope geometry and envelope update rule are not frozen and not otherwise supported by authoritative repo evidence.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 13. How often do the candidates disagree?

Across the minimal research model:

- HIGH: 48 disagreements out of 76 opportunities
- LOW: 38 disagreements out of 66 opportunities

These disagreements are common rather than rare.

They are not concentrated in only one or two isolated incidents; they appear repeatedly across both directions.

Classification: EXPERIMENTAL EVIDENCE

## 14. Are disagreements structurally meaningful?

Yes.

The disagreement pattern is structurally meaningful because the current center may drift away from the incoming price while the nearest member remains close enough to satisfy the tolerance. This creates a systematic difference between center-based and member-based membership logic.

The observed disagreement pattern was:

- A / D false
- B true

This is not random or tied to a single edge case. It is the repeated pattern of a center-displaced but member-proximate swing.

The disagreements are therefore meaningful for structural comparison because they expose the core difference between:

- center anchoring
- nearest-member coverage

Classification: EXPERIMENTAL EVIDENCE

## 15. Does the actual data favor one candidate descriptively?

Descriptively, the canonical data favors Candidate B under the minimal research model because it accepts far more swings than Candidate A / D:

- HIGH: B accepts 51 vs A/D 3
- LOW: B accepts 41 vs A/D 3

However, this descriptive preference is not enough to freeze the rule, because the repository does not authorize B as the final membership geometry.

So the answer is:

- descriptive evidence: B is more permissive and more active
- authoritative repository support: none yet for B
- final rule status: still not frozen

Classification: EXPERIMENTAL EVIDENCE / PROPOSAL ONLY

## 16. Does any authoritative repository evidence support one candidate?

No final authoritative evidence supports freezing a membership rule.

The repo supports the following facts:

- the center statistic is frozen
- the tolerance-history contract is frozen
- a candidate/seed and append-only member state are proposal only
- the Zone object and member-set state model remain unresolved

This means there is no authoritative repository evidence that directly supports freezing Candidate A / D or B as the final membership rule.

Classification: REPOSITORY FACT / UNRESOLVED

## 17. Simplest defensible membership proposal

The simplest defensible proposal, under the current frozen rules and minimal causal state, is:

Candidate A / D — center-distance

Reason:

- it is directly implied by the frozen center statistic
- it is mathematically symmetric and deterministic
- it is the lowest-complexity membership rule that uses the current center and current tolerance
- it does not require inventing a member-envelope or a new zone geometry
- it remains fully consistent with the frozen historical tolerance contract

However, this recommendation is only:

PROPOSAL ONLY — NOT FROZEN

It is not authoritative and not final.

Classification: PROPOSAL ONLY

## 18. What exact decision remains before membership can be frozen?

The remaining decision is not the mathematical form alone. The remaining root decision is the structural contract for Zone membership itself.

The repo still does not define:

- the Zone creation trigger
- whether a valid Zone is created after 1 or 2 observations
- the full causal Zone state model
- the exact lifecycle of the member set
- whether a member set can be append-only or must be recomputed
- whether the center is fixed or recomputed as members accumulate
- how multiple candidate zones or overlap are handled
- which geometry is authoritative for the Zone object

Without those, membership cannot be frozen.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 19. After membership is resolved, what is the next remaining root decision for Group B?

After membership is resolved, the next remaining root decision is the exact Zone geometry / Zone lifecycle contract.

That includes:

- whether a Zone is represented by center-only, member list, member envelope, interval, or all three
- whether the geometry is fixed once created or mutable as members append
- how zone identity and overlap are tracked
- how changes in member set affect center and tolerance history
- whether a historical snapshot or a live evolving state is the correct model

This is the next unresolved Group B root boundary after membership.

Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 20. Required conclusions

1. Can membership now be evaluated causally?
   - Yes, in a research-only minimal sequential model.
   - Classification: PROPOSAL ONLY

2. Is A/D fully equivalent?
   - Yes, under the frozen symmetric center definition.
   - Classification: FROZEN / REPOSITORY FACT

3. Is Candidate B fully definable?
   - Yes, under the minimal research model.
   - Classification: PROPOSAL ONLY

4. Is Candidate C fully definable?
   - No.
   - Classification: BLOCKED BY UNRESOLVED ROOT DECISION

5. How often do the candidates disagree?
   - HIGH: 48 / 76 opportunities
   - LOW: 38 / 66 opportunities
   - Classification: EXPERIMENTAL EVIDENCE

6. Are disagreements structurally meaningful?
   - Yes. The dominant pattern is A/D false and B true when the center drifts away from the incoming swing but a nearest member remains within tolerance.
   - Classification: EXPERIMENTAL EVIDENCE

7. Does the actual data favor one candidate descriptively?
   - Descriptively, B is far more permissive and therefore appears favored in the canonical sequence.
   - Classification: EXPERIMENTAL EVIDENCE

8. Does any authoritative repository evidence support one candidate?
   - No final authoritative evidence supports freezing one candidate.
   - Classification: REPOSITORY FACT / UNRESOLVED

9. What is the simplest defensible membership proposal?
   - Candidate A / D as a minimal center-distance proposal.
   - Classification: PROPOSAL ONLY — NOT FROZEN

10. What exact decision remains before membership can be frozen?
   - The full Zone state contract and the exact creation / lifecycle semantics for membership.
   - Classification: BLOCKED BY UNRESOLVED ROOT DECISION

11. After membership is resolved, what is the next remaining ROOT decision for Group B?
   - Exact Zone geometry / lifecycle semantics.
   - Classification: BLOCKED BY UNRESOLVED ROOT DECISION

## 21. Evidence classification summary

- FROZEN: swing definition; 15-minute bar contract; same-direction stream separation; W=5; minimum tolerance history=1; tolerance median; current swing excluded; center = median(member prices)
- REPOSITORY FACT: canonical 15-minute reconstruction; eligible HIGH/LOW counts; no authoritative live Zone state machine in repo
- EXPERIMENTAL EVIDENCE: sequential A/D vs B disagreement pattern; large structural differences in acceptance rates
- PROPOSAL ONLY: Candidate A / D as simplest defensible proposal; Candidate B as research-only nearest-member proposal; append-only member update under the minimal model; seed/2-member creation baseline
- UNRESOLVED: final Zone creation semantics; final membership rule; final member-set state contract; final Zone geometry
- BLOCKED BY UNRESOLVED ROOT DECISION: Candidate C; final Zone geometry freeze; any final membership freeze

## 22. Governance verification

The following verification actions were performed:

### 22.1 Actual-data verification command

```powershell
.\.venv\Scripts\python.exe -c "import json, sys; sys.path.insert(0, '.'); from tools.research.research_15m_groupb import build_reconstructed_bars; bars, highs, lows = build_reconstructed_bars(); print(json.dumps({'reconstructed_bar_count': len(bars), 'eligible_high_swings': len(highs), 'eligible_low_swings': len(lows)}, indent=2))"
```

Observed output:

- reconstructed_bar_count = 1146
- eligible_high_swings = 78
- eligible_low_swings = 68

### 22.2 Sequential comparison command

A temporary research script was executed in the terminal to compare Candidate A / D vs Candidate B under the minimal causal sequential model. The script was not saved into the repository.

Observed output from the comparison:

- HIGH: A/D accepted 3 / 76 opportunities; B accepted 51 / 76 opportunities; disagreements = 48
- LOW: A/D accepted 3 / 66 opportunities; B accepted 41 / 66 opportunities; disagreements = 38

### 22.3 Repository integrity check

```powershell
git diff --check; Write-Host '---'; git status --short --untracked-files=all
```

Observed result:

- git diff --check produced no errors
- no production code files were modified by this audit
- no production tests were modified by this audit
- no canonical data files were modified by this audit
- the repo contains existing unrelated modified files, but this audit did not alter them

### 22.4 Governance status

- production code unchanged: YES
- production tests unchanged: YES
- canonical data unchanged: YES
- frozen decisions unchanged: YES
- Group B remains NOT FROZEN: YES
- Phase 2 remains NOT STARTED: YES
- git diff --check passes: YES

## Final conclusion

The current evidence is sufficient to say that the surviving membership candidates are not equivalent under the causal sequential model.

- Candidate A / D and Candidate B are materially different.
- The difference is not a trivial edge case: it is repeated and structured.
- Candidate C is not fully definable from current evidence and remains blocked.

The repository evidence supports a conservative, minimal, and direct membership proposal:

Candidate A / D — center-distance

But that remains:

PROPOSAL ONLY — NOT FROZEN

Membership itself is still not frozen, and the repo has not yet reached the point where a final membership decision is authoritatively justified.
