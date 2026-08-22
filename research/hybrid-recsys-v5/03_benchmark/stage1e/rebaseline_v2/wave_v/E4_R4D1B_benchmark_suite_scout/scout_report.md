# R4-D1B official benchmark-suite scout report

Created: `2026-08-22`  
Stage: `R4-D1B`  
Lane: official benchmark suites and project-owned immutable result packages  
Model profile required by dispatch: `Sol XHigh Standard` / `gpt-5.6-sol` / `xhigh` / `standard`

## Gate and operating boundary

The read-only entry validator returned the exact verdict `PASS_R4_S0_STRICT_GATE_20_OF_20_READY_FOR_R4_D1`. The frozen change-control contract, strict admission contract, input manifest, benchmark specification, adapter/evaluator and cross-dataset contracts, R3 selection decision, and manifest-frozen R3 FD2/FD3/FD4 records were read before discovery.

Research stayed within page-level public source replay. No repository or archive was cloned, fetched, or downloaded. No dataset, checkpoint, binary, or asset was downloaded. No terms were accepted, authentication used, package installed, environment or container created, preprocessing run, training run, evaluation run, or TEST surface opened. No maintainer was contacted and no candidate metric was written into the paper.

## Search coverage and stopping rule

The time-boxed search examined five official-owner surfaces discovered as benchmark, reproducibility, or project-owned comparison packages:

1. BARS MF-BPR on Gowalla_m1.
2. Amazon Science RecArena on MovieLens 20M.
3. RecBole-GNN general recommendation on MovieLens 1M.
4. ORBIT / `cxcscmu/RecSys-Benchmark`, including its hidden-test leaderboard.
5. Linux Foundation Recommenders' MovieLens 100K benchmark notebook.

Search snippets were locator aids only. The replay log records the direct project-owner pages/blobs and canonical dataset-provider pages that were actually inspected. Discovery stopped when requested; unresolved fields were not repaired by inference, source substitution, or cross-joining.

The exact R3 Cornac/MovieLens-100K, Elliot/MovieLens-1M, and DaisyRec/MovieLens-1M identity tuples were not reconsidered. RecBole-GNN/MovieLens-1M is a different repository/protocol/result identity and was independently excluded rather than merged with either R3 MovieLens-1M tuple.

## Admission result

Admitted proposals: **0**.

No proposal had all twelve dimensions at `PASS_PRIMARY_REPLAYED`; consequently no proposal was marked `ADMIT_COMPLETE_BUNDLE_FOR_INDEPENDENT_AUDIT`. There are no admitted candidates for which a D01-D12 admission rationale can be given. Zero admission is the required fail-closed outcome for this evidence set.

## Exclusions

### R4-D1B-PROP-001 — BARS MF-BPR / Gowalla_m1

Status: `DISPOSITIVE_REJECT`.

The immutable result README contains numeric logs, but its configuration link resolves to a SimpleX/Yelp18 tuner file rather than MF-BPR/Gowalla. That is a direct same-surface identity conflict in D07 and D09, not a missing detail that may be patched from another repository or revision. The processed dataset page is mutable and does not provide an immutable raw-to-processed checksum chain; the environment is also not locked.

### R4-D1B-PROP-002 — Amazon Science RecArena / MovieLens 20M

Status: `EXCLUDE_INCOMPLETE_BUNDLE`.

RecArena provides an unusually strong exact transitive requirements file and source-owned dataset preparation. However, the pinned repository tree inspected by the scout does not publish a numeric result package. Its acquisition script does not verify provider checksums or publish derived-file hashes, and the remaining protocol/evaluator/TEST-isolation/v5-adapter fields are incomplete. Environment quality cannot compensate for D03 and D09.

### R4-D1B-PROP-003 — RecBole-GNN / MovieLens 1M

Status: `EXCLUDE_INCOMPLETE_BUNDLE`.

The owner result page reports an 8:1:1 full-sort protocol, common settings, tuned hyperparameters, and numeric rows. It does not bind those rows to complete producer configs and seeds, a deterministic dependency lock, provider-to-atomic-file hashes, full evaluator candidate/mask/aggregation/tie semantics, proof of no TEST derivation, or a bounded v5 adapter. The mutable result page cannot become an immutable numeric target by combining it with separately inferred defaults.

### R4-D1B-PROP-004 — ORBIT / RecSys-Benchmark

Status: `EXCLUDE_INCOMPLETE_BUNDLE`.

ORBIT is an official benchmark with public and hidden-test tracks, code, configs, scripts, and evaluator entrypoints. The replayed root nevertheless lacks an affirmative license surface, relies in part on externally preprocessed data, instructs users to edit paths and variables, and does not bind a selected leaderboard row to one immutable code/config/environment/evaluator/dataset tuple. A dynamic leaderboard is not a same-surface numeric result package.

### R4-D1B-PROP-005 — Recommenders MovieLens notebook

Status: `EXCLUDE_INCOMPLETE_BUNDLE`.

The project is owner-maintained, and the comparison table is linked to a source-owned notebook. The repository describes the material as examples and best practices, and this artifact is a generic illustrative benchmark. It lacks the exact per-row producer config/seed/environment, byte-verified processed input, complete shared evaluator semantics, immutable result binding, TEST-isolation proof, and bounded v5 adapter required for this lane.

## Uncertainty and evidentiary limit

Some excluded projects may contain additional files outside the time-boxed pages. Under the strict contract, that possibility is not evidence: inaccessible, uninspected, ambiguous, mutable-only, or merely inferable fields fail their dimensions. No score, suite reputation, publication venue, or number of partially documented fields was used as compensation.

All source-native numbers mentioned in the exclusion analysis are identity diagnostics only. They are not accepted project results and remain invalid for the paper.

## Persistent truth state

```text
RESULT_STATUS=NOT_RUN
TEST_SET_OPENED=NO
ACCEPTED_RESULT_ROWS=0
execution_authorized=false
project_benchmark_numbers=INVALID_FOR_PAPER
```
