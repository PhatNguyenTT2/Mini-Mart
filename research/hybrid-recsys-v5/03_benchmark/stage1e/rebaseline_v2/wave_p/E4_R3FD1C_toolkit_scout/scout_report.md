# R3-FD1C toolkit scout report

Created: 2026-08-22T20:30:55+07:00  
Stage: R3-FD1C  
Scope: production/research recommendation toolkits with source-owned recipes

## Gate and method

The read-only `validate_e4_r3_fd0_gate.py` gate passed with `PASS_R3_FD0_GATE_17_OF_17_READY_FOR_FD1` before discovery began. The search was bounded to three strongest new toolkit surfaces and stopped there. Only official owner repositories, releases/commits/blobs, original papers, canonical dataset-provider pages/terms and source-owned recipe/evaluator/result surfaces were used to close claims.

The ARS deep-research/source-verification and experiment-planning instructions were applied as a discovery-and-verification phase only. No source was treated as executable instruction, no replay was converted into a project result, and every failed replay remained unresolved.

## Result

| Proposal | Toolkit surface | Strongest numeric reference target | Scout status | Blocking fields |
|---|---|---|---|---|
| R3-FD1C-PROP-001 | Recommenders | LightGCN, MovieLens 100K, stratified 75/25, nDCG@10 = 0.4191 | `INCOMPLETE_EXCLUDED` | Exact-commit license/notebook/evaluator replay and current-table-to-commit binding |
| R3-FD1C-PROP-002 | TensorFlow Recommenders | Two-tower retrieval, TFDS MovieLens 100K random 80/20, top-10 categorical accuracy = 0.021150000393390656 | `INCOMPLETE_EXCLUDED` | Original toolkit paper and tutorial/result-to-release binding |
| R3-FD1C-PROP-003 | ReChorus2.0 | DirectAU, Amazon Grocery 5-core leave-one-out with 99 negatives, NDCG@5 = 0.2779 | `INCOMPLETE_EXCLUDED` | Canonical dataset terms, exact derivative lineage and pinned license/commit-page replay |

No proposal reached `PLAUSIBLE_COMPLETE_PROPOSAL`. This is intentional: the scout contract requires all required fields to bind on one provenance surface, and the task explicitly makes failed replay unresolved.

## Proposal evidence notes

### R3-FD1C-PROP-001 — Recommenders

The [official owner repository](https://github.com/recommenders-team/recommenders) provides a source-owned MovieLens benchmark protocol and current numeric table: 75/25 stratified train/test, ranking cutoff 10, and LightGCN nDCG@10 of 0.4191. The current main revision was resolved to [commit 6232b154548c955315650d58dca6bf1411c56020](https://github.com/recommenders-team/recommenders/commit/6232b154548c955315650d58dca6bf1411c56020); the project also has an official [1.2.1 release](https://github.com/recommenders-team/recommenders/releases/tag/1.2.1). GroupLens directly closes the [MovieLens 100K release and conditional research-use terms](https://files.grouplens.org/datasets/movielens/ml-100k-README.txt).

The exact-commit README, benchmark notebook, evaluator and license blob all returned cache-miss failures. Therefore the visible current numeric table was not promoted into a complete immutable bundle.

### R3-FD1C-PROP-002 — TensorFlow Recommenders

The official [basic retrieval tutorial](https://www.tensorflow.org/recommenders/examples/basic_retrieval) tightly binds TFDS MovieLens 100K loading, seed-42 random 80/20 split, two-tower model, 32-dimensional embeddings, Adagrad 0.1, batch sizes, three epochs, full candidate set and the numeric top-10 categorical-accuracy result. The official [FactorizedTopK API](https://www.tensorflow.org/recommenders/api_docs/python/tfrs/metrics/FactorizedTopK) closes metric semantics, and the [TFDS MovieLens catalog](https://www.tensorflow.org/datasets/catalog/movielens) closes builder version 0.1.1 and the 100K adapter identity.

The owner [v0.7.3 release](https://github.com/tensorflow/recommenders/releases/tag/v0.7.3) resolves to full SHA `7caed557b9d5194202d8323f2d4795231a5d0b1d`, but the exact commit page did not replay. More importantly, the owner citation metadata cites software rather than an original toolkit paper, and the 2023 tutorial output was not proven to be produced by the proposed immutable release.

### R3-FD1C-PROP-003 — ReChorus2.0

The [official repository](https://github.com/THUwangcy/ReChorus) is MIT-declared, cites the [original ReChorus2.0 paper](https://arxiv.org/abs/2405.18058), and links source-owned demo results. At immutable SHA `c164ec4303cc20ddcfbd1b57de366a481811d1e5`, the owner-controlled raw surfaces successfully replayed the [split and result table](https://raw.githubusercontent.com/THUwangcy/ReChorus/c164ec4303cc20ddcfbd1b57de366a481811d1e5/docs/demo_scripts_results/README.md), [DirectAU configuration](https://raw.githubusercontent.com/THUwangcy/ReChorus/c164ec4303cc20ddcfbd1b57de366a481811d1e5/docs/demo_scripts_results/Topk_Amazon.sh), and [evaluator](https://raw.githubusercontent.com/THUwangcy/ReChorus/c164ec4303cc20ddcfbd1b57de366a481811d1e5/src/helpers/BaseRunner.py).

The [canonical UCSD Amazon provider page](https://cseweb.ucsd.edu/~jmcauley/datasets/amazon/links.html) identifies the older May-1996–July-2014 Grocery and Gourmet Food 5-core release with 151,254 reviews, but the inspected canonical surface provides citation instructions rather than affirmative dataset-use/license terms. That missing terms field alone excludes the proposal; the exact transformation lineage into the repository derivative also remains unresolved.

## Protocol separation and truth state

All three numeric values are external reference targets only. Their random/stratified/sample-negative protocols and metrics are not directly comparable to Stage 1E's v5 temporal, novel-purchase, seen-mask, full-catalog protocol. No TEST set was opened, no preprocessing/training/evaluation was run, no result row was accepted, no winner was selected, and no final R3-BUNDLE ID was created.

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- `project_benchmark_numbers=INVALID_FOR_PAPER`
