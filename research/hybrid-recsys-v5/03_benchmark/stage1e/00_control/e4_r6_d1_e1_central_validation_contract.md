# E4 R6-D1 / R6-E1 Central Validation Contract

Date: 2026-08-23

## Purpose

This contract defines the central checks applied after the two Sol XHigh Fast lanes finish. It does not modify the frozen R6-S0 inputs, authorize materialization, select a benchmark result, or open scientific execution.

The only possible successful transition is:

`R6-D1 + R6-E1 -> central validation -> R6-G0 input freeze`

Dataset download, extraction, atomic conversion, environment creation and package installation remain blocked until R6-G0 freezes one coherent profile and a later R6-C1 command packet passes central validation. Training, evaluation and project v5 TEST access remain prohibited.

## Immutable upstream identities

- Candidate: `R5-CAND-RECBOLE-BPR-ML100K-001`
- Source: RecBole `9a6f63d8d4a5b989fe27955a833f813a6d86041e`
- Canonical reference provider: GroupLens
- Canonical reference release: MovieLens 100K
- Worker profile: `gpt-5.6-sol`, `xhigh`, `priority` — Sol XHigh Fast
- Central profile: `gpt-5.6-sol`, `max`, `standard` — Sol Max Standard
- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- Project benchmark numbers remain `INVALID_FOR_PAPER`.

## Mechanical output gate

R6-D1 must contain exactly, and only:

1. `provider_authority.json`
2. `rights_and_release_record.md`
3. `data_lineage_plan.json`
4. `materialization_command_proposal.json`
5. `audit_handoff.json`

R6-E1 must contain exactly, and only:

1. `compatibility_matrix.json`
2. `environment_lock_proposal.json`
3. `environment_command_proposal.json`
4. `risk_report.md`
5. `audit_handoff.json`

All eight JSON files must parse as strict UTF-8 objects with duplicate and case-colliding keys rejected. Every output receives canonical-LF byte count and SHA-256. Extra files, missing files or edits outside the two assigned roots fail the gate.

## R6-D1 semantic gate

The dataset lane passes only if all of the following hold:

1. Provider authority is GroupLens, supported by current official `grouplens.org` or `files.grouplens.org` surfaces.
2. The stable MovieLens 100K release is distinguished from `ml-latest-small` and from any RecBole-processed copy.
3. Official page, README, archive, provider checksum and unzipped-index locators are recorded with retrieval results. A checksum value is accepted only if the provider bytes were replayed; otherwise the field remains explicitly unresolved.
4. The rights record does not relabel usage terms as a permissive software/data license. It must preserve the no-endorsement, publication acknowledgment, no-redistribution-without-permission and non-commercial-without-permission conditions reported by the official README.
5. The proposed Git boundary excludes archive, extracted raw files and derived atomic data. Only commands, hashes, inventories and lineage receipts may be versioned.
6. Safe extraction rejects absolute paths, traversal, alternate streams, reparse points/symlinks and unexpected archive members before writing the raw snapshot.
7. `u.data` is the authoritative interaction source. Its user, item, rating and Unix timestamp fields map deterministically into a RecBole atomic interaction file with a declared header and delimiter.
8. Row count, distinct user/item counts, rating range, timestamp preservation, duplicate-key policy, ID preservation and deterministic output hash are proposed as reconciliation checks.
9. Any comparison to repository-carried atomic blobs is a non-authoritative diagnostic and cannot replace the GroupLens raw-to-atomic transformation join.
10. Official-source and harmonized-v5 data namespaces remain physically and semantically separate.
11. The command proposal is unexecuted, names an official-host network allowlist and contains no training, evaluator, hyperparameter, checkpoint or project v5 TEST action.

## R6-E1 semantic gate

The environment lane passes only if all of the following hold:

1. It distinguishes RecBole source-declared lower bounds from an exact current compatibility proposal.
2. It proposes a CPU profile and never claims to recover the unknown historical environment behind README NDCG@10 `0.2768`.
3. Python, PyTorch, NumPy, SciPy, pandas, scikit-learn, PyYAML and the pinned RecBole source are covered by decision-bearing compatibility rows.
4. Every exact version proposal has a local pinned-source locator or an authoritative runtime/package-distribution locator. Unsupported compatibility guesses fail closed.
5. Minimum BPR/runtime packages are separated from optional tuning, distributed, visualization, TensorBoard and accelerator packages.
6. Optional `ray`, `hyperopt`, `tensorboard`, `thop` and plotting surfaces cannot silently enter the minimum closure unless evidence and an explicit reason are recorded.
7. The RecBole installation strategy is tied to the pinned local source revision and cannot resolve a different RecBole release from an index.
8. Direct package pins are exact. Transitive wheel filenames, byte counts and hashes are explicitly deferred to materialization rather than fabricated.
9. Platform and interpreter assumptions are explicit. Missing compatible Windows wheels, Python ABI conflicts or build-from-source fallback stop materialization and return to central review.
10. The command proposal is unexecuted, uses an isolated non-Git environment root, records package-host allowlists and produces interpreter/package/frozen-inventory receipts.
11. Proposed smoke checks are non-scientific import/version/syntax checks only. No RecBole run, data preparation, training, evaluation, tuning, checkpoint or project v5 TEST action is present.

## Cross-lane coherence gate

Central validation must confirm:

- both lanes use the same candidate and exact source revision;
- the dataset output location proposed by R6-D1 can be consumed through an explicit `data_path` by the environment/command layer without triggering RecBole's S3 processed-dataset downloader;
- the environment does not install or fetch data implicitly;
- neither lane treats the README number as reproduced or paper-valid;
- unresolved provider checksum, package wheel or compatibility facts are carried forward as preconditions rather than silently defaulted;
- neither lane authorizes materialization or scientific execution; and
- no claim, metric or data artifact crosses from the official-source seam into the harmonized-v5 seam.

## Verdicts

- `PASS_R6_D1_E1_READY_FOR_R6_G0_FREEZE`: exact outputs and all semantic/coherence gates pass; unresolved items are bounded materialization-time receipts with explicit stop rules.
- `FAIL_R6_D1_E1_REWORK_REQUIRED`: a correctable output, source, schema, command or coherence defect exists. R6-G0 remains closed.
- `CANNOT_VERIFY_R6_D1_E1_STOP`: provider rights, canonical lineage or current environment compatibility cannot be established without new authority or a material scope change. R6-G0 remains closed and the user checkpoint reopens.

No verdict from this contract authorizes dataset/environment materialization by itself. That authority becomes operational only through a separate validated R6-G0 and R6-C1 packet.
