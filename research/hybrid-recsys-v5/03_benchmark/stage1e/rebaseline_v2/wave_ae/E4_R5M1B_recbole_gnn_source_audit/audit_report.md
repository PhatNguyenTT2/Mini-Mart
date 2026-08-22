# R5-M1B RecBole-GNN LightGCN Source-Evidence Audit

## Material Passport

- Origin Skill: `ars-codex:academic-research-suite/experiment-agent`
- Origin Mode: `validate/source-evidence-audit`
- Origin Date: `2026-08-23`
- Verification Status: `ANALYZED`
- Version Label: `stage1e_r5_m1b_source_audit_v1`
- Candidate: `R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001`
- Source Revision: `632ef888589944c190ad8f449b49ca559618d4df`
- Audit Model Profile: `Sol XHigh Standard` / `gpt-5.6-sol` / reasoning `xhigh` / service tier `standard`

## Outcome

`CANDIDATE_STATUS=SOURCE_INCOMPLETE_CANDIDATE_FOR_R5_G1` and `REPRODUCIBILITY_STATUS=SOURCE_INCOMPLETE_NOT_RUN`.

The pinned source establishes a real RecBole-GNN LightGCN implementation, its MIT license, local model defaults, pairwise BPR objective, normalized user-item graph, and all-item dot-product score surface. It does not establish a reproducible producer for the displayed MovieLens-1M `NDCG@10=0.2538`: the exact environment, complete resolved configuration, seed, dataset bytes and transformations, RecBole evaluator semantics, checkpoint, run receipt and metric artifact are missing.

A representation-only v5 adapter is plausible but not ready. Immediate R5-G1 selection, execution, benchmark admission and paper use should remain on hold.

## Audit Boundary and Integrity

This was a semantic source audit, not a reproduction run. No network was used; no package, environment or container was created; no vendor module was imported; no test, preprocessing, training, evaluation or tuning command was run; no dataset or checkpoint was acquired; and project v5 TEST was not opened.

The repository checkout is exactly `b4944a9c1db6f88fe2222ade73b4231fb88ecd36`, satisfying the required baseline. The materialization receipt binds the candidate to detached revision `632ef888589944c190ad8f449b49ca559618d4df`. All 65 candidate files matched their `sha256_raw_bytes` values in the frozen selected-blob manifest. Six mandatory inputs listed by the frozen manifest matched their canonical-LF byte counts and hashes. The frozen manifest does not list itself, so its own bytes were read but had no declared self-digest to replay; this is not treated as a mismatch.

## Dimension Results

| Dimension | Status | Finding |
|---|---|---|
| S01 revision/license/source integrity | `PASS_SOURCE_ESTABLISHED` | Detached revision and 65 selected hashes are control-bound; `LICENSE` is MIT and names RUCAIBox. |
| S02 environment declarations | `PARTIAL_SOURCE_BOUND` | README claims `recbole==1.1.1`, `pyg>=2.0.4`, `pytorch>=1.7.0`, `python>=3.7.0`; there is no exact environment lock. |
| S03 entrypoint/config/defaults | `PARTIAL_SOURCE_BOUND` | Wrapper, local merge and model defaults are visible; RecBole precedence/defaults, exact seed and complete resolved config are absent. |
| S04 evaluator/mask/aggregation/ties | `PARTIAL_SOURCE_BOUND` | LightGCN emits all-item scores, but general data preparation, training and evaluation delegate to unmaterialized RecBole code. |
| S05 TEST isolation/leakage | `FAIL_CONFLICT` | `objective_function` evaluates TEST on every hyperparameter trial; source ratio split also conflicts with v5 temporal isolation. |
| S06 numeric producer binding | `FAIL_MISSING` | `0.2538` is source-located but lacks revision-to-run, data, seed, environment, evaluator, checkpoint and receipt bindings. |
| S07 dataset lineage | `DEFER_REQUIRES_DATA_OR_RUN` | MovieLens-1M provider bytes, rights/release, extraction, rating filter, ID map and split receipts require later acquisition. |
| S08 bounded v5 adapter | `PARTIAL_SOURCE_BOUND` | Raw score export is plausible; no adapter/evaluator, ID map, frozen score artifact or parity receipt exists. |
| S09 next gate | `DEFER_REQUIRES_DATA_OR_RUN` | Environment, datasets, contracts, parity, tolerance, command packet, confirmation, authorization and actual rerun remain future work. |

Dimension counts are pass `1`, partial `4`, fail `2`, defer `2`. The fact matrix contains `35` source facts: `22` source-established, `6` partial, `1` missing, `4` conflict and `2` deferred.

## Source-Established LightGCN Surface

The model is registered locally and selected before RecBole fallback (`recbole_gnn/utils.py`, `get_model`, lines 62-85, SHA-256 `c6b4e2fe...b50fb60`). `LightGCN` declares pairwise input, initializes user/item embeddings, applies BPR and embedding regularization, averages ego and propagated embeddings, and scores by user-item dot product (`recbole_gnn/model/general_recommender/lightgcn.py`, lines 26-133, SHA-256 `e07285de...70c214d`). The graph builder makes symmetric normalized user-item edges without self loops from `dataset.inter_feat` (`recbole_gnn/data/dataset.py`, lines 49-79, SHA-256 `076872db...bd5916`).

The local model YAML contains `embedding_size: 64`, `n_layers: 2`, `reg_weight: 1e-05`, and `require_pow: True` (`recbole_gnn/properties/model/LightGCN.yaml`, lines 1-4, SHA-256 `546152cc...25d036`). The leaderboard instead reports tuned LightGCN values `learning_rate=0.002`, `n_layers=3`, and `reg_weight=0.0001`, showing that the local YAML alone is not the producer configuration.

## Environment Finding: RecBole 1.1.1 Is a Claim, Not a Lock

`README.md` lines 35-44 declares exactly `recbole==1.1.1` but only lower bounds for Python, PyTorch and PyG. `recbole_gnn/config.py` lines 20-33 applies NumPy compatibility aliases only when `recbole.__version__ == "1.1.1"`; it does not reject other versions or record the effective environment. The LightGCN import path also reaches `torch_sparse` directly through `recbole_gnn/model/layers.py` line 5, but no version or ABI binding is supplied.

The full pinned 78-entry repository tree contains no requirements file, `setup.py`, `pyproject.toml`, lockfile, environment file or container recipe. Exact Python patch, PyTorch build/CUDA ABI, PyG and `torch_sparse` pair, NumPy/pandas/tqdm versions, platform, driver, hardware and RecBole transitive dependencies are unresolved and were not inferred.

## Configuration Composition

The CLI wrapper defaults to `BPR` and `ml-100k`; a LightGCN/MovieLens-1M run therefore requires explicit overrides (`run_recbole_gnn.py`, lines 6-15). The local `Config` first invokes RecBole's internal loader and then merges `properties/model/<model>.yaml` (`recbole_gnn/config.py`, lines 65-80). The quick-start function then constructs data, initializes the seed routine twice, creates the model from `train_data.dataset`, fits against validation and evaluates test (`recbole_gnn/quick_start.py`, lines 19-63).

The exact external-file/config-dict/CLI precedence is implemented by the absent RecBole dependency. The source does not bind the leaderboard to a literal argv, seed, reproducibility flag, negative sampler, optimizer, stopping settings, sparse mode, device, precision, complete override set or resolved-config hash.

## Evaluator Delegation

`LightGCN.full_sort_predict` returns flattened user-by-all-item dot-product scores (`lightgcn.py`, lines 123-133). It does not mask seen items, remove reserved IDs, sort, break ties, build truth or aggregate metrics.

For general models, `recbole_gnn/utils.py` lines 99-156 delegates data preparation to `recbole_data_preparation` and trainer lookup to `get_recbole_trainer`. The local `CustomizedFullSortEvalDataLoader` only calls its RecBole superclass and optionally attaches a graph transform (`recbole_gnn/data/dataloader.py`, lines 55-59). Consequently, RecBole's metric formulas, full/sampled candidate construction, seen-item masking, averaging denominator, empty-case behavior and tie policy are not established by this candidate tree. Facts from the separate RecBole candidate were not joined into this audit.

## TEST Isolation Conflict

The ordinary quick-start call fits on train/validation and then evaluates test, but the three split loaders are constructed together. More seriously, the hyperparameter `objective_function` fits a trial, evaluates `test_data`, and returns `test_result` every time (`recbole_gnn/quick_start.py`, lines 66-95). `run_hyper.py` lines 7-22 runs exhaustive `HyperTuning` over that objective.

This does not prove that the historical producer selected parameters on TEST, because no producer receipt exists. It does prove that the provided tuning path opens and exposes TEST during tuning. That path is incompatible with the preregistered v5 boundary and must not appear unchanged in a future command packet.

## Numeric Target Audit: NDCG@10 = 0.2538

`results/general/ml-1m.md` line 54 displays LightGCN `NDCG@10=0.2538`. The same document establishes:

- MovieLens-1M via a provider hyperlink;
- rating filtering at `rating >= 3`;
- ratio-based `8:1:1`, full-sort evaluation;
- selected interaction fields;
- 500 epochs, train batch size 4096, validation metric MRR@10, evaluation batch size 4096000 and embedding size 64;
- best LightGCN values and finite tuning ranges for learning rate, layers and regularization.

It does not establish the raw archive/release/hash, transformation and split receipts, exact revision that produced the row, seed, full resolved config, environment, RecBole evaluator bytes, candidate mask, tie policy, trial log, run ID, checkpoint, predictions or metric receipt. The settings list also spells the metric `NGCG@10` while the table spells `NDCG@10`; this is preserved as a documentary conflict, not silently corrected.

Therefore `0.2538` is `PROVISIONAL_SOURCE_LOCATED_NOT_PRODUCER_BOUND`. It may become a source-reproduction center only after a complete pre-run producer freeze and authorized rerun. It is prohibited as a harmonized v5 comparator and invalid for paper use now.

## Dataset Lineage

The source says RecBole-GNN shares RecBole atomic-file inputs, and the result page names `user_id`, `item_id`, and `rating`. It supplies a rating threshold and post-filter counts but no byte-verifiable lineage.

A later authorized MovieLens acquisition must record provider/release identity and rights, raw archive and extracted-file hashes, the exact rating-filter implementation/config, transformed atomic-file hash, raw/internal ID maps, deterministic split algorithm/order/seed, per-split hashes and cardinality reconciliation. None of these values were acquired or inferred here.

For harmonized v5 work, `inputs/experimental_log.md` still marks the snapshot and six lineage hashes PENDING. No v5 adapter can run before the snapshot, embedding, rules, benchmark-spec, semantic-cohort and order-metadata hashes and their associated source/license audits are complete.

## Bounded v5 Adapter Feasibility

The viable seam is raw score export, not source-integrated metrics:

1. A separately frozen preprocessor emits train-only organic-purchase interactions in a RecBole-compatible representation and binds every raw/internal user and product ID.
2. The source LightGCN objective, graph propagation, negative sampling and dot-product scoring remain unchanged.
3. A hash-bound exporter captures per-user all-catalog scores with explicit user/item order, shape, dtype, missingness and score direction.
4. A standalone v5 evaluator applies frozen eligibility, novel truth, full-catalog coverage, seen-item masks, score-descending/raw-product-ID-ascending ties, HR@10, NDCG@10 and GAUC, retaining per-user vectors.

The adapter may map IDs, normalize representation, validate schemas and emit receipts. It may not retrain differently, change the objective or sampler, calibrate/impute/rerank, silently drop entities, inherit RecBole metrics as v5 semantics, use the source ratio split, or call the provided TEST-evaluating orchestration before authorization.

No implementation or parity fixture currently exists, so the feasibility verdict is `BOUNDED_REPRESENTATION_ADAPTER_PLAUSIBLE_NOT_READY`.

## R5-G1 Recommendation

Recommendation: `HOLD_NOT_READY_FOR_SELECTION_OR_EXECUTION`.

There is no candidate-dispositive source conflict: the TEST-opening and protocol mismatches are bounded to orchestration/evaluator seams and can in principle be replaced without changing LightGCN mathematics. Nevertheless, R5-G1 should not admit this candidate as ready until the environment and RecBole evaluator are hash-bound, the MovieLens producer and v5 dataset lineages are complete, a validation-only no-TEST-read path exists, the adapter/evaluator and parity receipts pass, and a source-reproduction tolerance is frozen before any authorized run.

## Truth State

```text
RESULT_STATUS=NOT_RUN
TEST_SET_OPENED=NO
ACCEPTED_RESULT_ROWS=0
execution_authorized=false
project_benchmark_numbers=INVALID_FOR_PAPER
```

No project number or source leaderboard number is accepted as a result, and this audit makes no VERIFIED reproducibility claim.
