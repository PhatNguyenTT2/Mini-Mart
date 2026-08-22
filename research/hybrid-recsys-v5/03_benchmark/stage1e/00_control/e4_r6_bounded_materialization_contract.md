# E4 R6 Bounded Dataset, Environment and Command Materialization Contract

Date: 2026-08-23

## Entry authority

R5-G1 selected `R5-CAND-RECBOLE-BPR-ML100K-001` only for a data/environment proposal. At R5-M2 the user explicitly approved canonical GroupLens MovieLens 100K materialization, byte-verifiable lineage, an isolated RecBole environment, and an exact command proposal while prohibiting training, evaluation and TEST access.

The machine-readable authority is `e4_r5_m2_user_approval_receipt.json`. This contract must not widen it.

## Scientific purpose

R6 prepares a reproducible execution substrate. It does not execute the experiment and cannot verify a benchmark result. The selected source revision remains RecBole `9a6f63d8d4a5b989fe27955a833f813a6d86041e`; README NDCG@10 `0.2768` remains a provisional documentary lead rather than a producer-bound center.

Two evaluator seams remain separate:

1. Official-source seam: GroupLens MovieLens 100K, source protocol, source evaluator and a future same-surface rerun.
2. Harmonized-v5 seam: project TRAIN/VALIDATION, full 5,200-item catalog, frozen v5 masking/ties/metrics and a later separately authorized TEST gate.

No metric may cross these seams by relabeling.

## R6-D1 contract — dataset authority, rights and lineage

R6-D1 is a HIGH-importance judgment lane and uses Sol XHigh Fast. It must rely on current authoritative GroupLens surfaces for provider/release/terms/archive/checksum facts and may use the pinned RecBole source only for consumer/conversion behavior.

Exact output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ag/E4_R6D1_movielens100k_authority_lineage`

Exact files, no extras:

1. `provider_authority.json`
2. `rights_and_release_record.md`
3. `data_lineage_plan.json`
4. `materialization_command_proposal.json`
5. `audit_handoff.json`

The lane must establish or leave explicitly unresolved:

- canonical provider and exact release identity;
- rights/use/redistribution conditions and acknowledgment requirements;
- final and redirect URLs for README, archive and provider checksum when available;
- archive filename, expected checksum type/value only when replayed from provider bytes;
- extraction inventory and path-safety policy;
- raw GroupLens file identities and schemas;
- deterministic conversion into RecBole atomic files;
- raw-to-atomic row, field, ID and timestamp reconciliation;
- relationship to repository-carried `.inter`, `.item` and `.user` blobs without assuming equivalence;
- split/seed/config receipts needed later; and
- exact proposed commands without executing downloads, extraction or conversion in this lane.

Search snippets, mirrors, package caches and repository-carried data cannot be decision-bearing provider authority. If the official checksum cannot be replayed, record that limitation and require a locally computed SHA-256 after acquisition; do not infer a historical checksum.

## R6-E1 contract — current compatible environment closure

R6-E1 is a HIGH-importance judgment lane and uses Sol XHigh Fast. It must inspect the exact pinned RecBole setup/requirements/import surfaces and authoritative runtime/package compatibility sources.

Exact output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ah/E4_R6E1_recbole_environment_closure`

Exact files, no extras:

1. `compatibility_matrix.json`
2. `environment_lock_proposal.json`
3. `environment_command_proposal.json`
4. `risk_report.md`
5. `audit_handoff.json`

The lane must:

- distinguish source-declared lower bounds from an exact current compatible lock;
- avoid claiming an unknown historical producer environment;
- prefer a bounded CPU profile unless source evidence requires an accelerator;
- identify Python, PyTorch, NumPy, SciPy, pandas, scikit-learn, YAML and RecBole compatibility risks;
- separate minimum runtime packages from optional tuning/visualization packages;
- pin every proposed direct package and state how transitive artifacts will be captured with hashes;
- propose an isolated environment path, literal creation/install commands, verification imports and inventory commands;
- prohibit training, evaluation, TEST access and hyperparameter entrypoints; and
- fail closed if no high-confidence compatible profile can be proposed.

## R6-G0 and R6-C1

Central Sol Max Standard validates both lanes against the frozen manifest, resolves conflicts and freezes one dataset profile plus one environment profile. It cannot select based on a benchmark value.

Only after R6-G0 may R6-C1 use Sol High Fast for bounded command assembly. R6-C1 receives frozen scientific choices and may perform no new source interpretation. Ambiguity escalates to XHigh Fast or central.

R6-C1 must produce exact commands, expected write sets, network allowlists, timeout/resource limits, failure rules, and negative assertions proving that no training/evaluation/TEST command is present.

## R6-M0 and R6-M1

Materialization may begin only after central validation of the exact R6-C1 packet.

Allowed:

- retrieve canonical GroupLens MovieLens 100K provider metadata and archive;
- compute raw SHA-256 and byte counts;
- safely extract into a non-Git materialized-data root;
- materialize a deterministic RecBole atomic representation and lineage receipts;
- create an isolated environment and install only the frozen package set;
- capture package, interpreter, OS and hardware inventories; and
- run non-scientific import/version/syntax checks named by the command packet.

Forbidden:

- RecBole training or evaluation entrypoints;
- source or v5 metric computation;
- hyperparameter tuning;
- checkpoint or result asset download;
- project v5 TEST discovery, loading or access;
- benchmark admission or paper claims; and
- silent fallback to a mirror, alternate dataset release, different Python profile or different package resolution.

## R6-A1 and R6-G1

R6-A1 uses an independent Sol XHigh Fast context to replay dataset hashes, lineage, environment inventory, exact command receipts and the no-execution boundary. It may return PASS, FAIL or CANNOT_VERIFY; it cannot authorize execution.

Central R6-G1 may only admit the materialized substrate for construction of a separate experiment-execution proposal. Training, evaluation and TEST remain blocked until a new explicit user checkpoint.

## Persistent truth state

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- project benchmark numbers remain `INVALID_FOR_PAPER`
