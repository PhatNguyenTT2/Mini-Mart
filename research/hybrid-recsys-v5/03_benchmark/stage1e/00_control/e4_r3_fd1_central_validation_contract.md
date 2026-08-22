# Stage 1E — R3-FD1 central import/validation contract

Date: `2026-08-22`  
Validator context: `Sol Max Standard` (`gpt-5.6-sol`, reasoning `max`, service
tier `standard`)  
Producer context: `Sol XHigh Standard` (`gpt-5.6-sol`, reasoning `xhigh`,
service tier `standard`)

## Purpose

This gate validates the exact FD1 write set and freezes one common candidate-ID
set before FD2, FD3 and FD4 run. It proves carrier integrity and seed-contract
conformity only. It does not verify every source claim, rank candidates, select
a bundle, authorize downloads or establish that any benchmark is reproducible.

## Exact producer write set

Root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p/E4_R3FD1_bundle_seed_discovery`

Files:

1. `candidate_bundle_seeds.json`;
2. `source_search_log.json`;
3. `excluded_candidate_log.json`;
4. `fd1_report.md`;
5. `fd1_handoff.json`.

No other file is importable as FD1 output.

## Mechanical gate

The central validator requires:

- strict UTF-8 and strict JSON without duplicate or case-colliding keys;
- exactly five files and no undeclared files in the output root;
- three to five unique `R3-BUNDLE-*` candidates;
- all required seed and source-record fields from
  `e4_r3_candidate_bundle_contract.json`;
- `FRAMEWORK_REPRODUCTION_REFERENCE` labeling and
  `PLAUSIBLE_COMPLETE_SEED` status on every admitted row;
- direct HTTPS locators for repository, immutable revision, license, paper,
  dataset provider/terms, preprocessing/split, training, config, evaluator and
  benchmark target;
- source inventories with decision-bearing locators and explicit access state;
- no old R2 row ID reuse;
- producer runtime recorded as Sol XHigh Standard;
- unchanged empirical truth and explicit forbidden-operation assertions.

The validator prints a bounded JSON result and does not rewrite producer files.
The central context then records exact canonical-LF hashes in a frozen FD1
manifest. Any validation or hash failure blocks FD2–FD4.

## Scientific boundary

Mechanical PASS means only that all verification lanes can inspect the same
candidate set. FD2 verifies rights/lineage, FD3 verifies benchmark/evaluator
same-surface provenance, FD4 stress-tests adaptation compatibility, and R3-G1
performs final authoritative locator replay. No FD1 metric is a project result.

