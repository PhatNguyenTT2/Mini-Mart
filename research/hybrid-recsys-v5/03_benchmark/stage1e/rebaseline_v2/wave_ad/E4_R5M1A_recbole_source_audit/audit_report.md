# R5-M1A RecBole BPR source-evidence audit

> Material Passport: `stage1e_rebaseline_v2_r5_m1a_recbole_source_audit` · ARS experiment-agent validation mode · source-only semantic audit · 2026-08-23

Candidate: `R5-CAND-RECBOLE-BPR-ML100K-001`
Pinned revision: `9a6f63d8d4a5b989fe27955a833f813a6d86041e`
Repository baseline: `b4944a9c1db6f88fe2222ade73b4231fb88ecd36`
Model profile: Sol XHigh Standard (`gpt-5.6-sol`, reasoning `xhigh`, service tier `standard`)

## Audit outcome

The candidate is `SOURCE_INCOMPLETE_CANDIDATE_FOR_R5_G1` with reproducibility status `SOURCE_INCOMPLETE_NOT_RUN`. The pinned tree is authentic and semantically rich enough for central R5-G1 comparison: all 265 selected blobs match the frozen raw-byte SHA-256 manifest, HEAD is detached at the required revision, the vendor worktree is clean, and the MIT-licensed BPR implementation, config resolution, seed handling, data path, training loop, full-sort scorer, masks, and metric formulae are traceable.

The source does not close environment, data-lineage, numeric-producer, TEST-isolation, deterministic top-k tie, or v5 parity requirements. No permanent license, repository-identity, or BPR-objective conflict was found. The conflicts below are non-dispositive only if stock tuning/top-k/GAUC surfaces are excluded from harmonized v5 and a separately frozen, TEST-sealed orchestration exports full scores to the standalone v5 evaluator.

This was not a reproduction run. `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, execution is unauthorized, and all project benchmark numbers remain `INVALID_FOR_PAPER`.

## Integrity and scope

- The repository commit requirement was met exactly at `b4944a9c1db6f88fe2222ade73b4231fb88ecd36`.
- The absolute read-only source root resolved to detached HEAD `9a6f63d8d4a5b989fe27955a833f813a6d86041e` with no vendor worktree modifications.
- Every one of the 265 selected candidate files was rehashed from raw bytes; mismatch count was zero.
- No network, dataset/checkpoint acquisition, package installation, environment creation, vendor import/execution, preprocessing, training, evaluation, tuning, test, or project v5 TEST access occurred.
- Every positive fact in `source_fact_matrix.json` is bound to one source-relative path, symbol/line locator, and the corresponding frozen `sha256_raw_bytes`.

## S01-S09 findings

| Dimension | Status | Finding |
|---|---|---|
| S01 revision/license/integrity | `PASS_SOURCE_ESTABLISHED` | RecBole 1.2.1, RecBoleTeam/RUCAIBox identity, MIT code license, detached revision, clean tree, and all selected hashes are established. |
| S02 environment declarations | `PARTIAL_SOURCE_BOUND` | Direct requirements exist, but mostly as lower bounds; `setup.py` and `requirements.txt` are not an exact lock, Python/platform are undeclared, and transitive/runtime/hardware identities are absent. |
| S03 entrypoint/config/defaults | `PASS_SOURCE_ESTABLISHED` | `run_recbole.py` defaults to BPR/ml-100k; current merge precedence, BPR method registration, source defaults, seed calls, validation early stopping, and tuning entrypoints are traceable. |
| S04 evaluator semantics | `FAIL_CONFLICT` | Full scores, padding/seen masking, HR/NDCG, user-mean aggregation, and GAUC tie ranks are explicit. `torch.topk` has no v5 raw-ID tie key, and RecBole GAUC is positive-count weighted rather than v5 macro. |
| S05 TEST isolation/leakage | `FAIL_CONFLICT` | Preprocessing/remapping precedes split; default split is random. Normal checkpoint selection is validation-based, but quick-start evaluates TEST and stock hyperparameter tuning opens TEST every trial; Ray selects TEST recall. |
| S06 numeric producer binding | `FAIL_MISSING` | README NDCG@10=0.2768 is illustrative documentation, not a revision/data/config/seed/environment/checkpoint/evaluator/run receipt. The `BPRMF` label also conflicts with pinned class `BPR`. |
| S07 dataset lineage | `DEFER_REQUIRES_DATA_OR_RUN` | URL, download/extract/rename code, and ml-100k field expectations are known. Provider release/rights, raw archive, atomic bytes, hashes, transformation, split, and ID-map receipts are absent. |
| S08 bounded v5 adaptation | `PARTIAL_SOURCE_BOUND` | Reversible IDs and `full_sort_predict` make a score-only adapter plausible. TEST-sealed data orchestration, complete catalog coverage, standalone evaluator implementation, and parity receipts remain absent. |
| S09 next gate/preconditions | `DEFER_REQUIRES_DATA_OR_RUN` | A finite closure plan exists, but data/environment materialization and all execution require a later user checkpoint and separate authority. |

## Configuration and training trace

The executable quick-start path is `run_recbole.py::__main__` → `recbole.quick_start.run` → `run_recbole`. The CLI script passes model `BPR` and dataset `ml-100k` explicitly by default. Those explicit identity arguments dominate external model/dataset values because `Config._get_model_and_dataset` consults external identity only when an argument is `None`.

For ordinary parameters, precedence is:

1. internal YAML, merged as `overall.yaml` → `model/BPR.yaml` → `dataset/sample.yaml` → `dataset/ml-100k.yaml`;
2. config files, where later files overwrite earlier files;
3. `config_dict`;
4. CLI tokens exactly shaped as `--name=value`.

The final external dictionary overwrites internal values. The current default surface uses seed 2020 with reproducibility true, BPR embedding size 64, Adam, learning rate 0.001, one uniformly sampled training negative, up to 300 epochs, validation every epoch, stopping threshold 10, and `MRR@10` for checkpoint selection. These are current source defaults, not historical producer facts for the README number.

`init_seed` sets Python, NumPy, Torch CPU, and Torch CUDA seeds and toggles cuDNN benchmark/deterministic flags. This is a source-established reproducibility attempt, not proof of deterministic output under an unresolved Torch build, platform, accelerator, and dependency graph.

The BPR objective is method-faithful: user, positive-item, and negative-item embedding dot products feed `-mean(log(1e-10 + sigmoid(pos_score - neg_score)))`. `full_sort_predict` emits each requested user's dot products against the complete internal item-embedding matrix.

## Evaluation semantics

The default evaluation mode is full sort. RecBole constructs a score row over its data-derived internal item cardinality, masks internal padding item 0, and masks history positions to `-inf`. Sampler used-item sets are cumulative by phase. `FullSortEvalDataLoader` then defines history as the cumulative used set minus current target positives.

That subtraction is not automatically v5 novel-truth logic. If a target item was already in history and is retained as a current positive, subtracting the positive removes it from the source history mask. v5 instead removes all historical items from truth and masks every seen item. A harmonized adapter must therefore use the frozen v5 truth/history artifacts rather than assume the source target set is equivalent.

For top-k metrics, `Collector.eval_batch_collect` calls `torch.topk` directly. There is no source-level stable flag or secondary comparison by raw product ID. Equal-score order for HR/NDCG is therefore unresolved and cannot satisfy the frozen v5 rule “score descending, then `raw_product_id` ascending.” By contrast, the GAUC collector explicitly assigns average ranks to equal sorted scores.

RecBole HR and binary NDCG formulae align in form with v5, and the shared top-k aggregator uses an unweighted arithmetic mean across users supplied by the dataloader. Equivalence still requires identical eligible users, novel truth, full 5,200-product universe, history masks, and deterministic ties.

RecBole GAUC is not v5 GAUC. It calculates per-user AUC with average score-tie ranks, then weights each user by positive count. v5 requires an unweighted macro mean over eligible-user AUCs. Source GAUC may appear only on the official-source seam with its own provenance; the standalone v5 evaluator must compute harmonized GAUC.

## TEST isolation findings

The source dataset loads and globally preprocesses interactions before `Dataset.build` performs ordering and splitting. Filtering, token factorization, ID maps, user/item cardinality, imputation, label conversion, and normalization can therefore depend on held-out rows. The stock default then shuffles and performs a user-grouped random 80/10/10 split, which conflicts with v5's fixed temporal boundaries.

The ordinary `Trainer.fit` chooses checkpoints from the configured validation metric. That positive fact is bounded by two larger access problems:

- `run_recbole` creates train, validation, and test loaders in one call and automatically evaluates test after fitting; there is no source-enforced project TEST seal.
- `objective_function` evaluates test on every hyperparameter trial and sends `test_result` to the tuning backend. The Ray path schedules and selects by `recall@10` from those reported test metrics. The non-Ray `HyperTuning` class chooses best parameters using `best_valid_score`, but it still evaluates and exports TEST for every trial.

Accordingly, neither stock tuning path is admissible for v5. A project-owned validation-only runner must fail closed on any TEST path before the later gate.

## Why README NDCG@10=0.2768 is not a same-surface producer-bound target

The positive, limited finding is that README lines 147–191 place `ndcg@10: 0.2768` inside a BPR/ml-100k example that displays user-grouped random 80/10/10 splitting and full evaluation. It belongs to the same broad method/dataset/evaluator family as this candidate.

It is not producer-bound for exact reproduction:

- the README says users will obtain output “like” the shown block;
- it does not identify the commit that produced the block;
- it binds no provider archive or processed atomic bytes;
- it supplies no canonical resolved configuration or complete literal argv;
- it does not state the producer seed, runtime, Torch build, platform, or hardware;
- it binds no checkpoint, prediction file, per-user metrics, stdout/stderr, or run receipt;
- its top-k equal-score behavior is unresolved because the Torch runtime is unresolved; and
- it prints model identity `BPRMF`, while the pinned executable class is `BPR` and no executable `BPRMF` symbol exists in the selected tree.

Current defaults must not be projected backward to fill those gaps. The value may remain a provisional documentation lead when a later official-source target policy is frozen, but it is not an accepted center, a v5 comparator, a result row, or a paper number.

## Dataset lineage required later

The selected tree contains no MovieLens bytes. It declares a RecBole-hosted processed `ml-100k.zip` URL and code that downloads, extracts, deletes the archive, and renames atomic files. The dataset YAML expects `user_id`, `item_id`, `rating`, and `timestamp`, with no default rating threshold. None of this proves exact provider release or transformed bytes.

A later, separately authorized materialization must record provider identity, exact release, rights/license, acquisition timestamp, literal command and redirect chain, raw archive byte count/SHA-256, extractor identity/version, complete extracted inventory, pre/post-rename paths and hashes, atomic headers/counts, duplicate and threshold policy, raw-to-internal ID maps, and split-index hashes. Official-source MovieLens lineage and project v5 six-field lineage must remain separate.

## Bounded v5 adapter finding

A representation-only score adapter is plausible but not ready. It can preserve BPR mathematics by exporting untruncated `full_sort_predict` scores and mapping RecBole internal IDs back to frozen raw IDs. The adapter must exclude `[PAD]` by identity, preserve score values/direction and counts, and pass full scores to the standalone frozen v5 evaluator before source top-k.

The adapter cannot itself solve training data isolation. RecBole's benchmark-file interface loads and concatenates every named split before global remapping, while `data_preparation` expects train, validation, and test datasets. Project TEST must not be placed in that process before authorization. A project-owned, hash-bound runner must expose only train and validation during model selection and must prove the full 5,200-product catalog—including 250 cold products—is represented without reading TEST behavior.

Required parity fixtures cover ID round-trip, padding exclusion, exact catalog/cold-item coverage, score/count preservation, missing/duplicate/unknown policy, seen/repeated-target handling, equal-score raw-ID ties, manual HR/NDCG, adversarial macro-versus-weighted GAUC, TEST-seal sentinels, and exact artifact-set equality.

## Remaining blockers and handoff

R5-G1 may compare this lane as a source-incomplete, non-dispositive candidate. It must not treat this recommendation as selection, benchmark admission, data/environment authority, or execution authority. Before any rerun proposal can execute, the following remain mandatory:

1. exact MovieLens provider-to-atomic byte lineage and rights receipt;
2. exact Python/platform/direct/transitive/Torch/hardware lock;
3. literal argv, canonical resolved-config hash, seed schedule, tuning budget, and validation-only selection rule;
4. a source-target policy and tolerance frozen without accepting README 0.2768 as producer-bound;
5. TEST-sealed source orchestration and immutable train/validation split/ID/catalog artifacts;
6. hash-bound adapter/evaluator implementations and all parity fixtures;
7. an authorized official-source rerun with checkpoint/prediction/per-user/evaluator/terminal receipts; and
8. a separately authorized harmonized v5 validation run, with TEST remaining sealed until its later gate.

Recommendation: advance this audit to `R5-G1` central comparison only as `SOURCE_INCOMPLETE_CANDIDATE_FOR_R5_G1`. No execution is authorized and no numeric result is accepted.
