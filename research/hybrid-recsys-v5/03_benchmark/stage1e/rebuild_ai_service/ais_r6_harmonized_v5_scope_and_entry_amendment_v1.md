## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: central-amendment
- Origin Date: 2026-09-04T00:53:11.1484422Z
- Verification Status: CENTRAL_VERIFIED_PENDING_FINAL_INDEPENDENT_AUDIT
- Version Label: ais-r6-harmonized-v5-scope-and-entry-amendment-v1.0.0
- Upstream Dependencies: ais-r4-official-reproduction-attempt001-disposition-v1.0.0, ais-r5-independent-static-audit-v1.0.0
- Repro Lock: repository HEAD `3e22ef7fee94235c62f4e2b1fc7a8675b9d8e08d`; v5.1 dataset SHA-256 `21f7b93bad51d6fa3c69ce849a1931f634539f4fc8f475b00c17de0b5d977194`
- Experiment Intake Declaration: experiments_declared by scholar

# AIS-R6 harmonized-v5 scope and entry amendment

## Decision

The official RecBole BPR/MovieLens-100K attempt is accepted as an end-to-end
implementation-integrity check, but its numeric row remains `INCOMPARABLE`.
The RecBole README presents `NDCG@10=0.2768` as example-like output and does not
publish a complete historical environment. Attempt-001 produced `0.2928`, which
is outside the preregistered interval `[0.26296, 0.29064]`. The tolerance is not
changed and the run is not repeated to target the README number.

AIS-R6 may proceed because source, provider dataset, configuration, split,
evaluator, seed, checkpoint, and output bindings were demonstrated. This does
not create an Accepted Result Row and does not authorize cross-dataset numerical
comparison.

## Frozen harmonized comparator scope

The required bounded comparison set is:

1. Random — deterministic sanity control;
2. MostPop — train-only non-learning control;
3. ItemKNN — conventional neighborhood collaborative-filtering baseline;
4. BPR-MF — conventional pairwise latent-factor baseline;
5. Independent Deep Two-Tower — content-aware deep ablation;
6. Wide/Rule-only — train-only Apriori ablation; and
7. Proposed Hybrid — additive Deep + Wide candidate.

LightGCN is an optional stronger graph baseline admitted only if its exact
RecBole adapter completes before the TEST-opening freeze. SASRec and BERT4Rec
are `NOT_TESTED` in this bounded study because a sequence-model-specific adapter
and sequence truncation contract are not yet present. They remain in Related
Work and limitations. This amendment narrows claims; it does not imply that the
Hybrid exceeds graph or sequential methods.

## Runtime and TEST sequence

1. Repair the score-export boundary so validation-selected checkpoints may be
   applied to a separately hash-bound TEST protocol without retraining or
   reopening selection.
2. Run focused static and fixture tests.
3. Complete validation-only evidence for every frozen comparator. Use the fixed
   configurations already registered; no TEST-driven tuning is allowed.
4. Select the strongest conventional comparator from validation NDCG@10 and
   freeze model/config/checkpoint hashes.
5. Run final seeds `42`, `2027`, and `31415` for stochastic methods. Deterministic
   methods may use one fitted artifact if byte identity is demonstrated.
6. Issue one TEST-opening receipt, export scores from frozen artifacts, and run
   the shared evaluator exactly once per admitted run.
7. Compute hierarchical paired bootstrap with 2,000 replicates and Holm-adjusted
   exploratory comparisons. Failed seeds remain failed and are not imputed.
8. Perform AIS-R7/E5 independent audit. Only a passing seal may update the Stage
   1E pipeline state or make paper-result claims.

## Claim boundary

The paper may report harmonized-v5 results only as an internally controlled
benchmark on generated/semi-synthetic behavior. It must separately report the
MovieLens run as a diagnostic reproduction attempt. It may not claim SOTA,
production effectiveness, public-dataset superiority, or superiority over any
method marked `NOT_TESTED`.
