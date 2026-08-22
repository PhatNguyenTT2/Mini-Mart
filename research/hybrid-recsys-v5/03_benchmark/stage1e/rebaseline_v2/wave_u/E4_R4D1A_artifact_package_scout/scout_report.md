# R4-D1A official artifact/reproduction-package scout

## Gate and scope

The read-only entry validator returned `PASS_R4_S0_STRICT_GATE_20_OF_20_READY_FOR_R4_D1`. Discovery was confined to official conference artifact/proceedings pages, author- or proceedings-linked reproduction repositories, and source-owned archival/data locators. No benchmark-suite or framework-release family was searched as a discovery source.

The lane was time-boxed after five leads had been taken beyond locator-only screening. The prior R3 Cornac/MovieLens-100K, Elliot/MovieLens-1M, and DaisyRec/MovieLens-1M identities were not reconsidered or silently reused.

## Search coverage

The replay covered official RecSys 2022 and 2023 accepted-contribution pages, official SIGIR 2022 and 2023 proceedings, SIGIR's official artifact-badging policy, and the project-owner package surfaces for:

1. the BERT4Rec systematic review and replicability study;
2. Repetition and Exploration in Sequential Recommendation;
3. State Encoders in Reinforcement Learning for Recommendation;
4. Experiments on Generalizability of User-Oriented Fairness; and
5. Challenging the Myth of Graph Collaborative Filtering.

Where available, full repository SHAs and revision-pinned README or environment text blobs were replayed. No archive, dataset, result zip, checkpoint, binary, or other asset was downloaded. A GroupLens checksum sidecar and the RL4Rec shared-data page were attempted and recorded as inaccessible; their contents were not inferred.

## Admission result

Zero proposals were admitted. This is the strict outcome: no examined package established all D01-D12 as `PASS_PRIMARY_REPLAYED` on one exact identity tuple with an empty unresolved-field list and no dispositive conflict.

Because `admitted_candidates` is empty, there is no admitted proposal for which an all-12 PASS explanation can truthfully be supplied. The absence is substantive, not a missing report section: each screened lead failed at least one mandatory dimension, and every incomplete or conflicting lead was excluded.

## Exclusion findings

- **R4-D1A-PROP-001 — BERT4Rec package:** immutable code and executable examples were present, but an affirmative code license, byte-verifiable dataset lineage, complete environment lock, full evaluator semantics, no-TEST proof, bounded v5 adapter, and a single same-surface target tuple were not all replayed. The attempted checksum locator failed.
- **R4-D1A-PROP-002 — Repetition/exploration package:** the official paper/package provenance and full SHA were replayed, but the package exposes unversioned dependencies, an externally configured experiment-tracking workflow, a sweep rather than one exact protocol, no canonical dataset release/checksum chain, and no replayed same-surface numeric target.
- **R4-D1A-PROP-003 — RL4Rec:** the package has strong license, revision, environment, command, and seed evidence. It still fails strict dataset-lineage, evaluator, target, TEST, and source-replay requirements, and its interactive simulator/reward objective cannot be adapted to frozen v5 without changing the task. It is a dispositive reject.
- **R4-D1A-PROP-004 — FairRecSys:** the package provides notebooks, processed data, result tables, and named metrics, but not a replayed license, deterministic environment, canonical byte lineage, exact evaluator/seed/target tuple, or no-TEST proof. Its fairness re-ranking objective and grouping policy also conflict with an objective-preserving v5 adapter. It is a dispositive reject.
- **R4-D1A-PROP-005 — Graph-RSs-Reproducibility:** canonical dataset rights and checksums are replaced by links to processed splits in other model repositories, while the pinned requirements contradict the README's PyTorch/CUDA environment. License, evaluator, target, TEST, and adapter requirements remain incomplete. The environment contradiction makes it a dispositive reject.

## Uncertainty handling

Unknown, partial, mutable-only, inaccessible, indirect, or conflicting evidence was treated as failure for the affected dimension. Conference acceptance, reproducibility-track placement, apparent repository completeness, and reported result availability were not used as substitutes for missing identity fields. No license, checksum, seed, evaluator rule, target binding, or adapter property was inferred from adjacent projects or revisions.

## Preserved truth state

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- `project_benchmark_numbers=INVALID_FOR_PAPER`

The next gate is `R4_D1_CENTRAL_SCHEMA_HASH_VALIDATION` with zero admitted candidates.
