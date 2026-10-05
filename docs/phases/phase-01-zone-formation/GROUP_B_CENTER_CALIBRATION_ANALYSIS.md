# Group B Center Calibration Analysis

## 1. Objective

This document addresses the narrow question:

> Does the existing Phase 1 evidence provide meaningful support for using MEDIAN or MEAN as the center statistic for Candidate A — Point-Center Zone?

This is a research-only audit. It does not freeze the center decision, does not implement production code, does not modify executable tests, does not start Phase 2, and does not change the frozen Group A or Group B tolerance contract.

The project must not mistake the frozen tolerance median for evidence that the center statistic must also be median. The frozen tolerance is a prior-gap statistic; the center statistic is a distinct root decision.

## 2. Frozen Inputs

FROZEN — HUMAN APPROVED

- Group A swing definition
- 15-minute UTC bar contract
- canonical replay ordering
- causal eligibility
- HIGH and LOW remain separate
- only prior legal same-direction gaps influence tolerance
- current swing excluded from its own tolerance history
- W = 5 prior legal same-direction gaps
- minimum history = 1
- 0 prior legal gaps => no tolerance available
- 1–4 prior legal gaps => use all available
- 5+ prior legal gaps => use the five most recent
- tolerance = median of the selected prior legal absolute gaps

These remain unchanged and are binding for this analysis.

## 3. Repository Evidence

Repository evidence reviewed:

- [docs/ROADMAP.md](../../ROADMAP.md)
- [docs/phases/phase-01-zone-formation/DECISIONS.md](DECISIONS.md)
- [docs/phases/phase-01-zone-formation/SPEC.md](SPEC.md)
- [docs/phases/phase-01-zone-formation/AUDIT.md](AUDIT.md)
- [docs/phases/phase-01-zone-formation/TEST_REQUIREMENTS.md](TEST_REQUIREMENTS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md](GROUP_B_MEMBERSHIP_DISTANCE_ANALYSIS.md)
- [docs/phases/phase-01-zone-formation/GROUP_B_ZONE_GEOMETRY_COMPARISON.md](GROUP_B_ZONE_GEOMETRY_COMPARISON.md)
- [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py)

The project evidence supports the following:

- the same-direction structure is real
- HIGH and LOW must remain separate
- mixed-direction calibration is invalid for same-direction evidence
- the tolerance family is a valid causal prior-history rule
- the repo does not freeze a final zone object, zone lifecycle, or center rule
- the earlier geometry experiment was descriptive, not a full sequential zone-state simulation

The repository evidence does not yet show a complete direct comparison between median-center and mean-center under an otherwise identical candidate-zone model.

## 4. Experimental Method

The actual research tool used was [tools/research/research_15m_groupb.py](../../tools/research/research_15m_groupb.py).

This script reconstructs the canonical 15-minute bars and then applies a descriptive cluster analysis based on threshold-based grouping. It does not implement a sequential Candidate A zone-state model, does not maintain a live zone registry, and does not update a zone center as a function of sequential membership under a formal zone lifecycle.

Therefore, the experiment executed here is a controlled statistical comparison within the existing descriptive cluster representation only.

### What was executed exactly

1. reconstruct canonical 15-minute bars
2. extract eligible HIGH and LOW raw swing prices
3. reproduce the known counts:
   - HIGH = 78
   - LOW = 68
4. use the same cluster threshold sweeps already embedded in the research script
5. for every cluster candidate produced by the cluster routine, compute:
   - mean(cluster prices)
   - median(cluster prices)
   - abs(mean - median)
6. summarize the displacement distribution separately for HIGH and LOW

### What was not executed

The following were not executed as part of the repository experiment:

- a sequential Candidate A zone-state simulation
- per-zone center update over time
- membership-change comparison when only the center statistic changes
- center stability over a newly added member under a real zone lifecycle
- direct median-vs-mean comparison under a formal zone identity / tie-break model

This explicit limitation is required because the project cannot invent a sequential zone rule merely to force the comparison.

## 5. HIGH Results

The actual canonical dataset reproduced the known counts:

- HIGH = 78
- LOW = 68

Using the threshold-based cluster representation already implemented by the research tooling, the mean-vs-median center displacement for HIGH was:

| Metric | Value |
| --- | ---: |
| cluster_count | 143 |
| displacement count | 143 |
| median displacement | 2.02 |
| p75 displacement | 6.69 |
| p90 displacement | 12.16 |
| p95 displacement | 14.62 |
| max displacement | 123.06 |

This means that, within the descriptive cluster representation, the difference between mean and median centers for HIGH clusters is usually modest, but it can become very large in outlier-heavy or asymmetric clusters.

### Example HIGH cluster behavior

The script produced outlier-sensitive examples such as:

- cluster size = 3
- values approximately 6744.02, 6753.91, and 6752.33
- mean ≈ 6750.09
- median ≈ 6752.33
- absolute displacement ≈ 2.24

Another example:

- cluster size = 3
- values approximately 6456.86, 6465.70, and 6458.25
- mean ≈ 6460.27
- median ≈ 6458.25
- absolute displacement ≈ 2.02

These examples show that mean and median can differ materially even when the cluster is small, and that the difference is being driven by the skew in the member set rather than by a frozen zone rule.

## 6. LOW Results

Using the same descriptive cluster representation, the LOW displacement outcomes were:

| Metric | Value |
| --- | ---: |
| cluster_count | 139 |
| displacement count | 139 |
| median displacement | 2.66 |
| p75 displacement | 5.97 |
| p90 displacement | 13.19 |
| p95 displacement | 16.24 |
| max displacement | 95.31 |

This indicates a comparable pattern to HIGH: most LOW clusters show modest center differences, but a meaningful tail of asymmetric clusters can show large mean-versus-median divergence.

### Example LOW cluster behavior

Examples produced by the same measurement:

- cluster size = 3
- values approximately 6381.49, 6405.99, and 6397.73
- mean ≈ 6395.07
- median ≈ 6397.73
- absolute displacement ≈ 2.66

Another example:

- cluster size = 3
- values approximately 10081.21, 10089.13, and 10089.06
- mean ≈ 10086.47
- median ≈ 10089.06
- absolute displacement ≈ 2.59

This supports the interpretation that center differences are not uniformly large, but they are definitely real when a cluster is skewed or contains a sharp outlier-like member.

## 7. Mean vs Median Displacement

The actual measured displacement is summarized as follows:

| Direction | Median displacement | p75 | p90 | p95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| HIGH | 2.02 | 6.69 | 12.16 | 14.62 | 123.06 |
| LOW | 2.66 | 5.97 | 13.19 | 16.24 | 95.31 |

### Interpretation

This is a real statistical finding from the existing Phase 1 research data:

- mean and median differ within the same descriptive cluster representation;
- the median difference is usually small to moderate;
- the tail differences can be large, especially in skewed clusters.

However, this does not prove that median is the correct zone center. It only proves that the center choice affects the center value when the cluster member set is asymmetric or contains extreme values.

## 8. Outlier / Asymmetry Analysis

The repository experiment does not define a formal outlier threshold. Therefore, no arbitrary cutoff is introduced.

What can be measured from the actual data is the distribution of the mean-median displacement itself. This is the correct evidence-based way to describe the effect.

The measured tails were:

- HIGH p95 ≈ 14.62
- LOW p95 ≈ 16.24
- HIGH max ≈ 123.06
- LOW max ≈ 95.31

These tails show that a few clusters are highly asymmetric. In those clusters, the mean is more sensitive to the extreme member than the median.

### Important distinction

This is a mathematical property and a measured Phase 1 behavior:

- mean is more sensitive to extreme values;
- median is less sensitive to those extremes.

But it is not yet a proof that a zone center must be median. It only proves that the choice matters in asymmetric clusters.

## 9. Membership Sensitivity

The current repository experiment does not implement a sequential Candidate A zone-state simulation, so it cannot directly measure:

- matched membership count under median center vs mean center
- non-match count under median center vs mean center
- candidate cluster assignment under median vs mean
- distance-to-center change under median vs mean

This is not a missing metric because of under-sampling; it is a missing mechanism. The experiment only calculates cluster membership within a threshold-based grouping representation. It does not evaluate a current swing against an actual live zone center and then update the zone state.

Therefore the following conclusion is required:

> Membership sensitivity of median-vs-mean cannot yet be measured from the repository experiment without inventing a sequential zone lifecycle rule.

This means the membership sensitivity question remains unresolved.

## 10. Center Stability

The repository experiment does not model a live zone with sequential member updates. Therefore the following cannot be measured from the current experiment:

- median center movement after each new member
- mean center movement after each new member
- center drift under asymmetry
- stability difference between median and mean over a zone lifecycle

This means center stability is not yet supported by direct experimental evidence.

Any claim that one center is more stable must be treated as a mathematical property, not as a repository-validated dataset result.

## 11. Mathematical Properties vs Dataset Evidence

### Mathematical property

For a skewed or asymmetric cluster, mean is more sensitive to extreme values than median.

This is general mathematical fact.

### Measured Phase 1 behavior

The cluster-level displacement data from the actual Phase 1 research show that:

- the median displacement is small to moderate in most clusters;
- a subset of clusters show large displacement;
- HIGH and LOW both have long tails in the displacement distribution;
- the effect is real in the dataset, not merely theoretical.

### Architectural preference

The project may reasonably prefer median as the center statistic because it is less sensitive to extremes and because the existing frozen tolerance logic already uses a median. However, this remains a preference, not a proven requirement.

The project still lacks a direct, dataset-specific demonstration that the candidate center choice changes the final sequential zone behavior in a way that requires median selection.

## 12. Evidence Classification

DIRECTLY MEASURED

- HIGH = 78
- LOW = 68
- cluster displacement distribution between mean and median within the existing descriptive cluster representation
- mean-vs-median values for cluster-level center displacement across the actual Phase 1 data

DERIVED FROM MEASURED DATA

- the effect of asymmetry on center selection is real in the dataset
- the mean-vs-median differences are small in the bulk of clusters but large in the tail
- both HIGH and LOW show nontrivial tail behavior for center displacement

DESCRIPTIVE OBSERVATION

- mean and median differ materially under asymmetrical member sets
- large outlier-driven differences appear in a minority of clusters

ARCHITECTURAL INFERENCE

- median is a plausible leading center candidate because it is less sensitive to extreme values
- median is consistent with the already-frozen tolerance median logic
- Candidate A remains the leading architecture candidate, but center choice is not frozen

UNSUPPORTED / NOT DEMONSTRATED

- median is experimentally proven superior to mean for Candidate A
- median-vs-mean changes candidate membership counts in a live zone lifecycle
- median-vs-mean changes zone stability in a real sequential model
- there is a completely valid sequential center-selection experiment in the repository

## 13. Architectural Interpretation

The strongest evidence-based interpretation is:

- the repository does not yet contain a direct, fair, sequential proof that median is the correct center statistic for Candidate A;
- the existing descriptive cluster analysis does show that mean and median are not identical in real Phase 1 clusters and that the difference can be large when a cluster is asymmetric;
- median is therefore a plausible, conservative, and more robust default candidate,
  but the data currently support it as an architectural preference rather than as an empirically proven final rule.

This is the correct boundary between evidence and speculation.

## 14. Recommended Center Candidate

Recommended center candidate:

- Median is the better-supported candidate under the current evidence, but only as a leading candidate, not as a proven decision.

Rationale:

- it is less sensitive to extreme member values;
- it aligns with the project’s existing median-based tolerance logic;
- the measured cluster displacement distributions show meaningful differences between mean and median in asymmetric clusters;
- no direct sequential experiment yet proves mean is better.

Important caveat:

- this is not a frozen choice;
- the evidence does not yet justify a final center freeze;
- the project still lacks a valid sequential zone-state comparison for median vs mean.

## 15. Remaining Uncertainty

The following remain unresolved:

- whether a median center actually changes live zone membership outcomes under the real sequential rule set
- whether a mean center produces materially different sequential zone behavior
- whether the observed cluster-level differences matter once a formal zone lifecycle is defined
- whether the project should prefer median or mean in the asynchronous zone model

These unresolved points are not a reason to invent a rule. They are a reason to avoid freezing the center.

## 16. Human Decision Required

The following decisions still require human approval before center choice can be frozen:

- whether Candidate A remains the preferred architecture
- whether median or mean is the final center statistic
- whether the project is willing to proceed with a median-based center as the minimal default without a full sequential center comparison
- whether the current Phase 1 evidence is sufficient for a center freeze at this stage

## 17. Governance Status

- Group A FROZEN / HUMAN APPROVED
- 15-minute bar contract FROZEN / HUMAN APPROVED
- W = 5 FROZEN / HUMAN APPROVED
- minimum-history = 1 FROZEN / HUMAN APPROVED
- Candidate A is currently only the leading architectural candidate
- center is NOT FROZEN
- Group B NOT FROZEN
- Phase 2 NOT STARTED
- no production code changed
- no executable tests changed
- canonical dataset unchanged

## Final conclusion

The existing Phase 1 evidence does provide a meaningful statistical comparison of median and mean within the descriptive cluster representation:

- both centers differ in real data;
- average differences are modest but nonzero;
- the tail of asymmetric clusters shows substantial divergence;
- median is less outlier-sensitive and is therefore a reasonable leading candidate.

However, the repository does not yet provide a valid sequential zone-state experiment proving that median is the correct center statistic for Candidate A. The evidence supports median as the better-supported candidate, not as a proven final choice.
