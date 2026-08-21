# E4 method-faithful v5 adapter and evaluator contract

## Material Passport

- `origin_skill`: `ars-codex:academic-research-suite`
- `mode`: `experiment-agent / planning-only`
- `date`: `2026-08-22`
- `status`: `UNVERIFIED`
- `version`: `0.1.26`

This is a design lock, not an implementation or result. `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, and `execution_authorized=false` remain fixed.

## Activation rule

An adapter may be implemented only after its official reproduction or, for a heuristic with no singular empirical center, its source-semantic lock is accepted. A successful harmonized v5 run cannot retroactively validate an official reproduction. A method whose official row is rejected must obtain a new evidence-complete official row; it cannot adapt the rejected join.

The frozen v5 benchmark specification is `research/hybrid-recsys-v5/03_benchmark/benchmark_spec_v5.json`, canonical-LF SHA-256 `acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d`. All adapter manifests must repeat that hash.

## Immutable method boundary

The adapter may translate identifiers, serialize source-native inputs, invoke a pinned method, expose scores, and collect per-user rows. It may not change the objective, architecture, layer count, representation dimension, sampler, negative ratio, regularization, optimizer, learning-rate schedule, batch semantics, augmentation, pretrained artifact, stopping rule, or scoring equation that defines the accepted method configuration.

If the source method cannot score the full v5 candidate universe without changing its mathematics, the adapter records `INCOMPATIBLE_WITH_V5_FULL_CATALOG` and the row does not run. It must not silently switch to sampled negatives, top-k candidate generation, a framework reimplementation, a different sequence truncation, or a lower-memory architecture.

## Required adapter interface

Each adapter is isolated under `C:\recsys_stage1e_runtime\e4_v1\v5_harmonized\<method_id>\<adapter_sha>` and exposes these logical operations. E5 must bind them to exact, hashed argv before execution.

```text
inspect(manifest) -> compatibility_receipt
prepare(train_events, val_events, item_catalog, id_map) -> prepared_hashes
fit(prepared_train, prepared_val, frozen_config, seed) -> checkpoint_receipt
score(users, all_catalog_items, checkpoint) -> score_blocks
collect(score_blocks, truth, seen_items) -> per_user_rows
```

Contract types:

- `manifest`: benchmark-spec hash, snapshot hash, embedding hash or explicit `NOT_USED`, rules hash or explicit `NOT_USED`, semantic-cohort hash, order-metadata hash, method repo SHA, adapter SHA, environment hash, and exact config hash.
- `id_map`: a bijection between stable raw user/product IDs and contiguous source IDs. The canonical map is sorted by UTF-8 raw identifier bytes. Missing or duplicate IDs are fatal.
- `score_blocks`: dense or losslessly sparse `(user_id, product_id, score)` blocks covering every eligible user and every one of the 5200 catalog products before masking. Scores must be finite IEEE-754 values; NaN/Inf, missing pairs, duplicate pairs, or implicit zero fill are fatal.
- `per_user_rows`: one row per eligible user with truth IDs, seen IDs hash, ordered top-10 IDs/scores, hit count, HR@10, Recall@10, NDCG@10, reciprocal rank, AUC numerator/denominator, cold-item hits, and exclusion reason if ineligible.

Adapters write data only; they never aggregate metrics. The shared evaluator owns masking, ordering, eligibility, formulas, and aggregation.

## Method registry and adaptation state

| Method | Authoritative surface | v5 method-faithful boundary | E4 state |
|---|---|---|---|
| Random | RecBole `Random` semantic reference | Seeded independent uniform score per eligible user–item pair; no popularity leakage | `SEMANTIC_LOCK_PENDING` |
| MostPop | RecBole `Pop` semantic reference | Train-only item counts; descending count, then raw product ID | `SEMANTIC_LOCK_PENDING` |
| ItemCF/ItemKNN | RecBole `ItemKNN` | Frozen similarity definition, neighborhood size, normalization, and train-only fit | `PENDING_EVIDENCE` |
| Apriori | Local `AprioriRuleMiner` plus raw-lift `WIDE_ONLY` comparator | Train-only directed pair rules; frozen support/confidence/lift and fallback; no deep score | `PENDING_CLEAN_LOCAL_COMMIT` |
| BPR-MF | RecBole `BPR` | Matrix factorization, pairwise BPR objective, sampler, dimension, and regularization frozen | `PENDING_EVIDENCE` |
| LightGCN | Author implementation/reproduction row | Propagation, layer aggregation, BPR sampler/objective, layers, dimension, and regularization frozen | `PENDING_EVIDENCE` |
| SASRec | Author TensorFlow implementation | Causal sequence construction, maximum length, attention blocks, sampled objective, and scoring frozen | `PENDING_EVIDENCE` |
| BERT4Rec | Author TensorFlow implementation | Masking scheme, bidirectional encoder, sequence length, objective, and checkpoint rule frozen | `PENDING_EVIDENCE` |
| BTBR/Mask-Swap-NNBR | Author implementation | Basket construction, mask/swap operations, dual task, batch semantics, and scoring frozen | `REJECTED_CURRENT_JOIN` |
| UniSRec | Author implementation | Text/item encoder, pretrained checkpoint, fine-tuning stage, dimensionality, and scoring frozen | `PENDING_EVIDENCE` |
| AlphaRec | Author implementation | Text/embedding artifacts, graph construction, propagation, objective, and scoring frozen | `PENDING_EVIDENCE` |
| SimGCL | QRec author framework | Graph augmentation/noise rule, contrastive loss, layer count, sampler, and scoring frozen | `PENDING_EVIDENCE` |
| XSimGCL | SELFRec author framework | Three-layer configuration center only; contrast layer/noise/objective and sampler frozen | `PENDING_EVIDENCE` |
| LightGCL | Author implementation | Appendix E interaction sampler only; SVD/global-local objectives and dimensions frozen | `PENDING_EVIDENCE` |
| Deep local condition | Local v5 two-tower `deep_only` | Exact project towers, features, loss, sampler, and deep score; rules disabled | `PENDING_CLEAN_LOCAL_COMMIT` |
| Hybrid local condition | Local v5 learned deep plus Apriori-wide | Same deep component plus frozen learned combiner and train-only rule features | `PENDING_CLEAN_LOCAL_COMMIT` |

The source identities and immutable SHAs for external methods are inherited from the frozen E1 registry. The center-bearing joins are restricted to `selected_reference_bundle.json`; no alternate framework may inherit a center.

## Frozen v5 seam

### Split and eligibility

- Train interval: `2026-01-01T00:00:00Z` through `2026-06-19T23:59:59.999999Z`.
- Validation interval: `2026-06-20T00:00:00Z` through `2026-07-10T23:59:59.999999Z`.
- Test interval: `2026-07-11T00:00:00Z` through `2026-08-01T23:59:59.999999Z`.
- E4 and all tuning stages may open train and validation only. TEST remains sealed until a separately authorized final evaluation.
- Truth is the set of organic purchased products in the evaluated interval minus products seen by that user in earlier allowed history. User `0` is excluded. A user is eligible only if at least one novel truth product remains.
- The frozen synthetic/catalog specification contains 5000 users, 5200 products, and 250 cold products. Counts must be proven again by the snapshot receipt; disagreement is fatal.

### Candidate universe and ordering

Every eligible user is scored against all 5200 catalog products. Products seen in permitted history are assigned negative infinity after the raw model score is materialized. Cold products remain candidates. Final ordering is descending score, then ascending stable raw product ID. Candidate truncation before this ordering is forbidden.

For a source model that cannot natively emit full-catalog scores in GPU memory, the adapter may block users or items, but block concatenation must be lossless and invariant to block size. A parity fixture must prove identical ordered top-10 output for at least two block sizes before a real run.

### Metric formulas

For eligible user `u`, let `T_u` be the novel truth set and `R_u^10` the first ten ranked products.

- `HR@10_u = 1` if `R_u^10 ∩ T_u` is non-empty, else `0`.
- `Recall@10_u = |R_u^10 ∩ T_u| / |T_u|`.
- `DCG@10_u = Σ_{i=1..10} rel_{ui} / log2(i+1)`, with binary relevance.
- `IDCG@10_u = Σ_{i=1..min(10, |T_u|)} 1 / log2(i+1)` and `NDCG@10_u = DCG/IDCG`.
- `MRR@10_u` is the reciprocal rank of the first relevant product, or zero. It is optional for the primary claim but must use the same ranking seam if reported.
- Per-user AUC uses all unmasked candidates, binary truth, and average ranks for exact score ties. Users without both a positive and a negative candidate are excluded from AUC only, with reason. `GAUC` is the macro mean of valid per-user AUCs; weighted or pair-pooled AUC is a different metric and is forbidden under this label.
- Coverage and cold-item metrics are descriptive secondary outputs and must use the same ordered predictions. They cannot replace primary metrics.

All primary aggregates are arithmetic means over their exact eligible-user set. The evaluator emits the denominator and an ordered hash of included user IDs for every metric.

## Checkpoint, tuning, and seed lock

- Frozen final seed schedule: `42`, `2027`, `31415`. Missing or failed seeds are reported; they are never replaced.
- Tuning uses validation only and seed `42`. All learned methods receive at most eight complete configurations and 32 aggregate GPU-hours per method, whichever occurs first. A timeout/failure consumes a trial. There is no adaptive extension.
- Random and MostPop receive one deterministic configuration. ItemKNN and Apriori receive at most eight validation configurations and 8 CPU-hours per method. The local Deep and Hybrid conditions each receive the same eight-trial/32-GPU-hour cap as learned reference methods.
- The search space, proposal order, and all eight configurations must be written and hashed before Trial 1. A method with a source-mandated single configuration uses one trial; unused trials are not reassigned.
- Primary checkpoint selection is maximum validation NDCG@10. Ties choose lower epoch, then lexicographically smaller canonical configuration SHA-256. Checkpoint evaluation cadence is frozen before training and identical across comparable v5 learned rows.
- After tuning, the chosen configuration is frozen and trained/evaluated on all three seeds. No test-derived configuration, epoch, early-stopping decision, feature, or threshold is permitted.

## Uncertainty and comparison

Each seed emits per-user rows. The primary point estimate is the arithmetic mean of the three seed-level metric means. Confidence intervals use 2000 hierarchical bootstrap replicates with NumPy `PCG64(42)`: resample the three seeds with replacement, then resample eligible users with replacement inside each selected seed. The 2.5th and 97.5th percentiles use linear interpolation. Pairwise comparisons reuse identical replicate indices across methods and report the distribution of paired differences.

Single-seed diagnostic intervals, if unavoidable before final completion, must be labelled `DIAGNOSTIC_SINGLE_SEED` and use fixed stream offsets `+11`, `+13`, and `+17`; they are not accepted result rows. Missing seeds prevent a final claim.

## Required v5 receipts

Before training, the following immutable receipts must exist and cross-reference one another:

1. Snapshot receipt: provider/database identity, extraction query/config, time bounds, byte hashes, row counts, catalog counts, semantic cohort, and order metadata.
2. Split receipt: ordered user/event hashes, boundary timestamps, truth/seen logic, exclusions, and TEST seal state.
3. Feature receipt: train-only fit interval, source hashes, embedding model/version/hash, missing-value policy, and product/user ID maps.
4. Method receipt: source repo SHA, accepted official reproduction row, adapter SHA, environment hash, exact config, seed, budget, and method-boundary declaration.
5. Checkpoint receipt: selection metric, validation user hash, epoch/step, checkpoint SHA-256, and all considered checkpoint rows.
6. Prediction receipt: checkpoint hash, evaluator SHA, score-block hashes, full-catalog coverage proof, mask hash, tie rule, and ordered top-k hash.
7. Metric receipt: formula version, per-user artifact hash, denominator/user hash, aggregate, seed, and bootstrap configuration.

Any lineage field that is not used must contain the explicit string `NOT_USED`; null or omission is not permitted.

## Local implementation gap

The frozen local inspection identified useful v5 surfaces in `ai-service/src/ai_service/contracts.py`, `data/snapshot.py`, `evaluation/full_catalog.py`, and `evaluation/metrics.py`. It also identified three execution-blocking gaps: no locked Recall@10 implementation, no hierarchical seed-plus-user bootstrap, and no frozen typed registry covering the mandatory baseline matrix. In addition, `ai-service/src/ai_service/cli.py` and `training/pipeline.py` differ from the observed repository HEAD. E4 preserves those inherited changes and does not assign them an immutable source SHA.

Implementation, modification, parity tests, smoke tests, and benchmark runs are outside E4. E5 must fail closed until a clean commit, evaluator unit proofs, adapter parity fixtures, and exact confirmation packet exist.

## Failure rules

NaN/Inf scores, absent full-catalog pairs, duplicated IDs, non-bijective mappings, candidate truncation, data outside the allowed split, TEST access, missing receipt hashes, environment drift, checkpoint drift, resource-limit breach, or parity disagreement invalidates the run. There is no automatic retry or silent fallback. A method that cannot meet the contract is reported as incompatible or pending; coverage never justifies a weakened evaluator.
