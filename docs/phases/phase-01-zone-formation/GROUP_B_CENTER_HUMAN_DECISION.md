# Group B Center Human Decision

## Objective

This document transfers the center-statistic decision for Candidate A — Point-Center Zone to the human decision-maker.

The only issue under review is the center statistic:

- MEDIAN(member prices)
- MEAN(member prices)

No other Group B design decision is part of this approval.

This document does not freeze the decision. It records the current proposal and the evidence available for human review.

## Evidence

The real Phase 1 dataset was verified:

- dataset: [data/canonical/tardis_btc_eur_20200101](../../data/canonical/tardis_btc_eur_20200101)
- HIGH swings: 78
- LOW swings: 68

The existing descriptive cluster analysis measured the absolute difference between mean and median center values within the actual cluster representation already used in the repository research tooling.

| Direction | Median | P75 | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| HIGH | 2.02 | 6.69 | 12.16 | 14.62 | 123.06 |
| LOW | 2.66 | 5.97 | 13.19 | 16.24 | 95.31 |

These numbers show that mean and median can materially differ in real Phase 1 clusters.

## Evidence limitations

The repository evidence is limited in the following ways:

- this is descriptive cluster analysis only
- it is not a full sequential zone-state simulation
- it does not prove better trading performance
- it does not prove superiority under a full live zone lifecycle
- it does not provide membership-lifecycle evidence for the center decision
- it does not prove that median is the optimal center in all zone conditions

The current experiment shows that the choice between median and mean is genuinely meaningful in real clusters, but it does not yet prove the final center choice in a full sequential zone model.

## Approved decision

FROZEN — HUMAN APPROVED

CENTER STATISTIC:
median(member prices)

This decision was explicitly approved by the human project authority.

## Scope boundary

This approval freezes only the center statistic for Candidate A.

It does not freeze:

- the membership rule
- zone creation rule
- zone update timing
- zone identity
- multiple-zone handling
- overlap behavior
- merge behavior
- zone width
- lifecycle semantics
- historical snapshot semantics

Those remain unresolved Group B decisions.

## Reason for the approval

The current repository evidence supports median as the leading candidate because:

1. it is deterministic;
2. it is simple;
3. it is robust to asymmetric and extreme members;
4. real Phase 1 clusters show meaningful mean-vs-median divergence;
5. it does not introduce additional parameters;
6. it preserves a clean separation between:
   - tolerance history
   - zone center
   - future membership semantics
7. no current evidence justifies a more complex center definition.

This is not a claim that median is mathematically or empirically proven to be the optimal trading center. It is a human-approved governance decision based on the documented evidence.

## Governance

- Group A FROZEN / HUMAN APPROVED
- 15-minute bar contract FROZEN / HUMAN APPROVED
- W = 5 FROZEN / HUMAN APPROVED
- minimum-history = 1 FROZEN / HUMAN APPROVED
- Candidate A center = median(member prices) FROZEN — HUMAN APPROVED
- Candidate A = leading architectural candidate
- center = FROZEN — HUMAN APPROVED
- Group B = NOT FROZEN
- Phase 2 = NOT STARTED
- production code unchanged
- executable tests unchanged
- canonical dataset unchanged

## Final status

The center statistic is now frozen as:

CENTER STATISTIC: median(member prices)
STATUS: FROZEN — HUMAN APPROVED

No production behavior is changed, no code is implemented, and no additional Group B decisions are frozen.
