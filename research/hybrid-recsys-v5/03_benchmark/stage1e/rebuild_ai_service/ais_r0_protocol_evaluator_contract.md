## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-01T16:38:56Z
- Verification Status: UNVERIFIED
- Version Label: ais-r0-protocol-evaluator-contract-v1.0.0
- Upstream Dependencies: ais-r0-architecture-decision-v1.0.0, ais-r0-model-scope-v1.0.0
- Repro Lock: null
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# Protocol and shared-evaluator contract

This contract defines the common evidence surface for AIS-R2 through AIS-R7.
It does not admit a dataset, comparator, run, or result by itself.

## Dataset and split binding

- Every Protocol binds one immutable Dataset Snapshot by SHA-256.
- The v5 snapshot must independently verify user/item/interaction counts,
  source provenance, mapping hashes, feature hashes, split hashes, timestamp
  order, duplicate policy, malformed-row policy, and cold-item definition.
- The historical claims of 5,000 users, 5,200 items, and 823,371 events are not
  protocol facts until the AIS-R2 lineage receipt passes.
- Validation and test are temporal. An interaction may not appear before its
  user's admitted history boundary.
- Association rules and all learned preprocessing are fit from train only.

## Candidate and relevance semantics

- Evaluation is full-catalog over the exact admitted item catalog. For the
  expected v5 lineage this is 5,200 items, subject to AIS-R2 verification.
- Seen train-history items are masked by the evaluator, not by the model.
- Eligible users must have at least one novel organic purchase in the evaluated
  split under the frozen relevance rule.
- Candidate order is hash-bound. A model may not reorder, drop, or append items.
- Ties are resolved deterministically by `(-score, raw_product_id)`.
- The default cutoff is `K=10`.

## Score boundary

A model or adapter emits scores only. Each Score Artifact must bind:

- run ID, Dataset Snapshot hash, Protocol hash, and model descriptor;
- exact user order and candidate-catalog order;
- contiguous score chunks, shape, dtype, and per-chunk SHA-256;
- finite-value validation and an immutable exact file set.

Wrong shape, NaN, infinity, missing/overlapping chunks, candidate-order drift,
unbound users, split leakage, or protocol mismatch fails closed.

## Metrics and aggregation

The independent evaluator computes:

- HR@10 per eligible user;
- NDCG@10 per eligible user;
- exact per-user AUC, aggregated as macro per-user GAUC.

Metric receipts include the evaluator implementation hash, cutoff, eligible-user
count, metric-specific denominator, per-user vector hash, and aggregate value.
GAUC is undefined when a user lacks either class; such a value remains undefined
and is excluded from the GAUC denominator. It must never be imputed as 0.5.
The evaluator recomputes aggregates from the persisted per-user vectors during
receipt replay.

## TEST seal and statistics

- TEST remains sealed during development, smoke checks, tuning, comparator
  selection, and checkpoint selection.
- Final learned-model seeds are `42`, `2027`, and `31415`.
- A failed seed is retained as failed and is not imputed.
- TEST opens once only after the comparator registry, configurations,
  checkpoints, and statistic plan are frozen.
- Hierarchical paired bootstrap uses 2,000 replicates and the same sampled seed
  and user indices for the method and comparator.
- Per-seed user vectors are not averaged before bootstrap.
- Holm correction applies to exploratory multiple comparisons.
- Efficiency measurement is downstream of accuracy and cannot rescue a failed
  accuracy gate.

## Evidence-surface separation

`OFFICIAL_PROTOCOL_REPRODUCTION` preserves the reference source protocol and
tests a source-bound center. `HARMONIZED_V5_COMPARISON` uses the v5 Dataset
Snapshot and shared evaluator. A number, split, checkpoint, or evaluator from
one surface may not be relabeled as belonging to the other.
