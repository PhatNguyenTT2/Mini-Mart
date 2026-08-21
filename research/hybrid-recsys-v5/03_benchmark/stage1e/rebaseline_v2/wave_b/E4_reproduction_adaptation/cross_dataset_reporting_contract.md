# E4 cross-dataset reporting contract

## Material Passport

- `origin_skill`: `ars-codex:academic-research-suite`
- `mode`: `experiment-agent / planning-only`
- `date`: `2026-08-22`
- `status`: `UNVERIFIED`
- `version`: `0.1.26`

This contract contains no empirical result. `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, and all inherited project benchmark numbers remain `INVALID_FOR_PAPER`.

## Reporting invariant

An official reproduction, a harmonized v5 comparison, and an external validation answer different questions and must live in different tables, namespaces, artifacts, captions, and claims. Raw metric values may be compared only when dataset bytes/processing, split, candidate universe, masking, sampler, checkpoint policy, metric formula/aggregation, evaluator, and run protocol are identical or when the comparison is the frozen source-center acceptance test inside one official row.

No normalization, percentage change, rank, color scale, or narrative may make incompatible raw metrics appear comparable. A paper may say that a method reproduced its source center and separately report its v5 performance; it may not subtract or ratio those values.

## Table O — official reproduction acceptance

Required columns:

| Field | Rule |
|---|---|
| `official_row_id` | Immutable E4/E5 row identity |
| `method` | Exact source method/configuration identity |
| `repo_url`, `repo_sha` | Official or framework-authoritative repository and immutable commit |
| `dataset_provider`, `dataset_version`, `raw_hashes` | Lawful canonical source and acquired-byte identity |
| `processing_receipt_sha` | Exact raw-to-split transformation and output hashes |
| `command_config_sha` | Source-bound argv/config/environment |
| `sampler_layers_batch` | Explicit; never inherited from another row |
| `checkpoint_policy`, `checkpoint_sha` | Result-bound checkpoint decision and artifact |
| `candidate_evaluator` | Candidate universe, masks, tie rule, formulas, aggregation |
| `source_locator` | Primary URL, access date, exact table/line/config locator |
| `source_center`, `frozen_tolerance` | One metric per row or unambiguous metric object |
| `observed_value` | Null until an authorized run completes |
| `acceptance` | `NOT_RUN`, `PASS`, or `FAIL`; no partial promotion |

Current planning ledger — not a result table:

| Row | Dataset/pipeline | E4 status | Reason |
|---|---|---|---|
| LightGCN author-PyTorch | Gowalla bundled processed pipeline | `PENDING_EVIDENCE` | Strong command/center binding, but lineage, rights, license, dependency, tie, and checkpoint receipts remain |
| SimGCL QRec | Yelp2018 | `PENDING_EVIDENCE` | Interactive command and data/config/run locks incomplete |
| XSimGCL SELFRec | Yelp2018, three-layer | `PENDING_EVIDENCE` | Kept separate from four-layer paper center; environment/data/run locks incomplete |
| LightGCL author | Yelp, Appendix E interaction sampler | `PENDING_EVIDENCE` | Only updated Appendix E centers may bind; data/run/tie/license gates remain |
| UniSRec author | Scientific | `PENDING_EVIDENCE` | Processed/text/checkpoint artifacts and run locks incomplete |
| SASRec in UniSRec framework | Scientific | `PENDING_EVIDENCE` | Framework-specific baseline; artifact/config/run locks incomplete |
| BTBR | Ta-Feng joint task | `REJECTED` | Public command changes task/batch and lawful canonical dataset identity is absent |
| AlphaRec | Amazon Movies and TV | `PENDING_EVIDENCE` | Dataset/text/embedding rights and hashes plus run semantics incomplete |

The source-bound values and tolerances remain only in `selected_reference_bundle.json`. They must not appear in Table H or Table X.

## Table H — harmonized v5 comparison

Table H may be created only after official reproduction/source-semantic acceptance and method-faithful adapter audit. Every row uses the same benchmark-spec hash, snapshot/split hashes, full 5200-item catalog, seen-item mask, raw-ID tie break, seed schedule, checkpoint selection rule, and shared evaluator from `v5_adapter_and_evaluator_contract.md`.

Required columns:

| Field | Rule |
|---|---|
| `method_id`, `condition` | Exact baseline or project condition; ablations separately named |
| `official_acceptance_row` | Passed Table O row, or source-semantic receipt for a heuristic |
| `adapter_sha`, `environment_sha`, `config_sha` | Immutable v5 implementation identity |
| `snapshot_sha`, `split_sha`, `candidate_sha`, `evaluator_sha` | Must be identical across comparable rows |
| `seed_set` | Exactly `42,2027,31415`; missing seed prevents final claim |
| `HR@10`, `Recall@10`, `NDCG@10`, `GAUC` | Mean plus hierarchical 95% interval and denominator |
| `paired_difference` | Optional, but only from shared hierarchical replicate indices |
| `cold_metrics`, `coverage` | Secondary and labelled; same prediction seam |
| `result_status` | `NOT_RUN`, `COMPLETE`, or `FAILED_INCOMPLETE` |

Current Table H state is a single administrative row: `NOT_RUN — no adapter is activated`. No source-reported metric may populate it. The current local evaluator is not contract-complete, and the local Deep/Hybrid sources are not at a clean immutable commit.

## Table X — separate external validation

Table X must use a dataset with independently locked rights, persistent user identity, history, order/basket semantics, event time, catalog identity, release/version/hash, acquisition receipt, split, candidate universe, and evaluator. It is never pooled with Table H, and Table H tuning cannot continue after external results are opened.

Required columns:

| Field | Rule |
|---|---|
| `external_dataset_id`, `provider`, `version`, `terms_sha` | Canonical lawful identity |
| `raw_hashes`, `processing_receipt_sha`, `split_sha` | Acquired bytes through exact split |
| `identity_semantics`, `basket_semantics`, `time_semantics` | Explicit contract match |
| `method_id`, `adapter_sha`, `config_transfer_rule` | Frozen before external access; no external retuning unless separately declared |
| `candidate_evaluator_sha` | External evaluator contract; never assumed equal to v5 |
| metrics | Dataset-specific, fully defined; values compared only within Table X |
| `result_status` | `NOT_RUN`, `COMPLETE`, or `FAILED_INCOMPLETE` |

Current external eligibility ledger:

| Dataset | Full-contract status | Permitted reporting |
|---|---|---|
| Amazon-M2 | `REJECTED` | Not Table X. The primary paper defines anonymous 30-minute sessions, not persistent users with cross-order history, and the canonical provider route is authenticated with no unauthenticated provider digest. |
| Amazon-M2 reduced session study | `ACQUISITION_GATE` | At most a separately titled anonymous-session sensitivity table after terms/version/hash/task gates; never called full external validation and never substituted for Table X. |
| Complete Journey | `PENDING_EVIDENCE` | No result; current route/schema/version/hash/terms unresolved. |
| Instacart | `PENDING_EVIDENCE` | No result; original official competition route unavailable and mirrors excluded. |
| Tenrec | `PENDING_EVIDENCE` | No result; license/files/hash/task/config not locked. |
| Ta-Feng | `REJECTED` | No result; canonical provider/rights/version absent. |
| ViFoodRec | `REJECTED` | No result; task/identity/time/basket/license mismatch. |
| ViEcomRec / ViHoRec | `SENSITIVITY_ONLY_PENDING` | Cannot satisfy the frozen full external contract without an independently proven identity/order/basket match. |

Primary Amazon-M2 sources were replayed on 2026-08-22: the [NeurIPS dataset paper](https://papers.nips.cc/paper_files/paper/2023/file/193df57a2366d032fb18dcac0698d09a-Paper-Datasets_and_Benchmarks.pdf), anonymous-session/product description at PDF text lines 55–60, 30-minute sessionization and chronological split at lines 869–902, and release statement at lines 1005–1009; the [canonical AIcrowd challenge route](https://www.aicrowd.com/challenges/amazon-kdd-cup-23-multilingual-recommendation-challenge), which redirected to authenticated sign-in and exposed no unauthenticated digest; and the [official author repository](https://github.com/amazon-science/amazon-m2). This evidence supports rejection for the frozen identity contract, not an empirical performance claim.

Current Table X state: `NOT_RUN — NO_DATASET_PASSES_CURRENT_EXTERNAL_CONTRACT`.

## MovieLens scope lock

MovieLens 1M and 10M are reference/reproduction datasets, not full external retail-basket validation datasets. The canonical GroupLens provider makes stable archives and terms available. Provider MD5 values replayed on 2026-08-22 are `c4d9eecfca2ab87c1945afe126590906` for [MovieLens 1M](https://files.grouplens.org/datasets/movielens/ml-1m.zip.md5) and `ce571fd55effeba0271552578f2648bd` for [MovieLens 10M](https://files.grouplens.org/datasets/movielens/ml-10m.zip.md5).

The [official RecBole-GNN ML-1M results page](https://github.com/RUCAIBox/RecBole-GNN/blob/818babfe03268c78a01215376f7ceea48df159f8/results/general/ml-1m.md), accessed 2026-08-22, provides documented framework centers. Under the E4 contract it is still not exact reproduction-ready because result-bound seeds/runs, checkpoint selection/artifact, dependency lock, raw-byte-to-split receipt, and tie handling are not locked. MovieLens 10M provider fold scripts are for rating prediction, not an exact framework-owned top-N reproduction center. Neither finding permits a raw comparison to v5.

## Caption and claim rules

- Every table caption names dataset/version, processing/split receipt, candidate protocol, evaluator hash, seed count, and verification status.
- `UNVERIFIED`, `NOT_RUN`, `PENDING_EVIDENCE`, `ACQUISITION_GATE`, and `REJECTED` are printed, not hidden in notes.
- Failure rows stay visible with failure class and missing seed/run count; they are not omitted from a planned matrix after execution starts.
- A cross-dataset narrative may compare qualitative transportability, resource cost, or whether a method passed its own reproduction gate. It may not compare raw HR, Recall, NDCG, MRR, AUC/GAUC, or rank positions across Table O, H, and X.
- Reported source centers are historical targets. They are never labelled project results, and their frozen tolerance is never interpreted as a confidence interval.
- A session sensitivity study is not external validation of persistent-user retail recommendation.

## Fail-closed publication gate

A paper table remains prohibited until its rows have `VERIFIED` E5 receipts, the relevant result status is complete, TEST access is authorized and receipted where applicable, and all compared rows share the table's frozen seam. At E4, every numeric manuscript claim is prohibited.
