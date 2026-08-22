# R4-D1C official framework complete-packet scout report

Date: 2026-08-22  
Stage: R4-D1C  
Lane: `official_framework_complete_packet_scout`  
Assigned profile: Sol XHigh Standard (`gpt-5.6-sol`, reasoning `xhigh`, service tier `standard`)

## Gate and decision

The read-only entry validator returned the exact required verdict:

`PASS_R4_S0_STRICT_GATE_20_OF_20_READY_FOR_R4_D1`

Eight official-framework leads were screened. Four were advanced to pinned-revision primary replay; four remained locator-only when discovery was time-boxed. Zero proposals are admitted. Six leads are `EXCLUDE_INCOMPLETE_BUNDLE`, and two are `DISPOSITIVE_REJECT`.

This is a conjunctive D01-D12 decision. Missing, partial, ambiguous, inaccessible, indirect, or conflicting evidence was treated as failure. No framework popularity, paper prestige, number of implemented models, or partial field coverage was used to compensate. Because there are no admitted proposals, there is no candidate for which all twelve dimensions can be explained as satisfied.

## Search coverage

The completed primary replay covered four distinct official framework release surfaces:

| Proposal | Official release identity | Dataset/protocol surface | Disposition | Main blocking dimensions |
|---|---|---|---|---|
| R4-D1C-PROP-001 | RecBole v1.2.1, `9a6f63d8d4a5b989fe27955a833f813a6d86041e` | BPR, MovieLens 100K, random 80/10/10, full-sort top-10 | `EXCLUDE_INCOMPLETE_BUNDLE` | D03, D05, D07-D11 |
| R4-D1C-PROP-002 | Recommenders 1.2.1, `5c862afa751f53559b5ad98b92e098760f530ad8` | Cornac BPR, MovieLens 100K, stratified 75/25, ranking metrics at 10 | `DISPOSITIVE_REJECT` | D03, D05, D08, D09, D11 |
| R4-D1C-PROP-003 | LightFM 1.17, `688feded0717f289933b95a0134bad6fbe547331` | WARP, MovieLens 100K ua split, minimum rating 5, precision at 5 | `DISPOSITIVE_REJECT` | D01, D03, D05, D07-D11 |
| R4-D1C-PROP-004 | TensorFlow Recommenders v0.7.7, `cf1dafa988f223ed5f30b68cb9aed518484b3a1d` | Basic retrieval, TFDS MovieLens 100K, random 80k/20k, FactorizedTopK | `EXCLUDE_INCOMPLETE_BUNDLE` | D02, D03, D05, D07-D09, D11 |

Four additional framework families were retained as locator-only exclusions: LensKit, RecPack, NVIDIA Merlin Models, and LibRecommender. They were not promoted to decision-bearing candidates because no exact official release packet and same-surface numeric target had been established when breadth expansion stopped. Their unresolved identities and all unverified D01-D12 fields therefore fail closed; no search snippet or repository popularity was treated as evidence.

Conference-artifact and benchmark-suite families were not searched as independent candidate families. The previously frozen R3 identities for Cornac/ML-100K, Elliot/ML-1M, and DaisyRec/ML-1M were read to prevent duplication and were not reconsidered. R4-D1C-PROP-002 is a Recommenders framework identity whose notebook delegates its BPR model to Cornac; it is not the frozen R3 Cornac repository/revision/protocol/config/evaluator/target tuple.

## Exclusion findings

### R4-D1C-PROP-001 — RecBole

The release binds an executable `run_recbole.py` path, seed 2020, a random 80/10/10 split, full evaluation, top-10 metrics, and history masking. It nevertheless fails the strict packet gate:

- Repository-carried `.inter`, `.item`, and `.user` blobs are not joined by a source-owned transformation receipt to a checksum-verified canonical GroupLens archive.
- `requirements.txt` uses broad lower bounds and is not a complete dependency/runtime lock.
- The exact BPR output-producing configuration and tuning boundary are not frozen as one receipt.
- Ranking calls `torch.topk` without an explicit deterministic item-id secondary key.
- The README says output is “like” the displayed values and does not bind the values to a replay receipt under the pinned environment.
- No primary proof establishes TEST-independent schema/cardinality or a bounded adapter to the frozen v5 data/evaluator contract.

These unresolved mandatory fields require `EXCLUDE_INCOMPLETE_BUNDLE` even though the framework is runnable.

### R4-D1C-PROP-002 — Recommenders

The pinned notebook is unusually complete about the split, seed, BPR hyperparameters, candidate generation, evaluator calls, and stored metrics. It is still a dispositive rejection:

- The notebook's stored environment output reports Cornac 1.14.2, while the same pinned revision's `setup.py` requires `cornac>=1.15.2,<3`. The stored BPR target therefore cannot be joined to an environment valid for release 1.2.1.
- The MovieLens loader downloads the canonical archive but does not enforce the provider checksum; its generic helper receives no cryptographic digest for this call.
- The complete repository tree contains no exact transitive environment lock.
- Top-k sorts by user and score only, with no item-level deterministic secondary tie key.
- No bounded v5 adapter proof exists.

The same-revision environment/target conflict makes the status `DISPOSITIVE_REJECT`; the remaining gaps independently prevent admission.

### R4-D1C-PROP-003 — LightFM

The quickstart provides an executable WARP example and rounded precision output, but the pinned revision contains a dispositive rights conflict: `LICENSE` is Apache License 2.0, while `setup.py` declares MIT and the MIT classifier. The scout does not choose between conflicting owner surfaces.

The packet also fails independently because its MovieLens loader uses a project-owner repackaged archive with no checksum verification or canonical transformation receipt, dependencies and the Docker recipe are unpinned, `random_state=None` is left unchanged, training requests two threads, tie handling is not explicitly deterministic, the numeric output is rounded without a producing environment receipt, matrix dimensions are derived from train plus test interactions, and no bounded v5 adapter is proven. Status: `DISPOSITIVE_REJECT`.

### R4-D1C-PROP-004 — TensorFlow Recommenders

The official tag resolves to a full immutable commit and the tutorial binds seed 42, a random 80k/20k split, a model, an optimizer, and FactorizedTopK evaluation. It remains incomplete:

- `tfds.load("movielens/100k-ratings")` and `tfds.load("movielens/100k-movies")` omit the TFDS builder version. The exact provider-side transformed release is therefore unresolved.
- The release does not bind provider bytes through a checksum and transformation chain to the TFDS examples.
- Dependencies are open ranges, `tensorflow-datasets` is not declared in the runtime requirements, and no transitive lock exists.
- The tutorial does not declare a tuning boundary, and the ranking implementation uses `tf.math.top_k` without an explicit identifier secondary key.
- The notebook's fit and evaluate cells have no stored execution count or output, so there is no same-surface numeric target.
- No bounded v5 adapter proof exists.

Status: `EXCLUDE_INCOMPLETE_BUNDLE`.

## Source replay and uncertainty

The source log contains 47 records. All successful decision-bearing records are project-owner release/commit/tree/blob material or canonical GroupLens provider material. The GroupLens `ml-100k.zip.md5` endpoint was opened but could not be replayed as text; binary retrieval was not attempted, and no checksum value was inferred. That inaccessibility is recorded rather than repaired with a mirror.

Search results and snippets were used only to locate candidate families. They are not source records and do not support any positive admission claim. Locator-only leads have empty evidence lists and fail D12 together with every other unverified dimension.

The requested model profile is recorded as assignment metadata. The worker interface did not expose an independent runtime-profile attestation, so the artifacts make no additional runtime identity claim beyond the frozen assignment.

## Operation boundary and persistent truth

Only public page-level and source-owned text/metadata replay was performed. No repository was cloned or fetched; no archive, dataset, checkpoint, binary, or asset was downloaded; no terms were accepted; no authentication, package installation, environment/container creation, preprocessing, training, evaluation, TEST access, or maintainer contact occurred. No candidate metric was written into the paper.

Persistent truth remains:

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- `project_benchmark_numbers=INVALID_FOR_PAPER`

The lane hands off zero admitted proposals to `R4_D1_CENTRAL_SCHEMA_HASH_VALIDATION`. A zero-candidate outcome is preferable to weakening any mandatory dimension.
