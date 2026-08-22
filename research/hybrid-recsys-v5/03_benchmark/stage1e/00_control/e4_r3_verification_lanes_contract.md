# Stage 1E — R3-FD2/FD3/FD4 parallel verification contract

Date: `2026-08-22`  
Producer runtime: `Sol XHigh Standard` (`gpt-5.6-sol`, reasoning `xhigh`,
service tier `standard`)  
Entry dependency: centrally validated and hash-frozen R3-FD1 candidate seed set

## Shared rule

FD2, FD3 and FD4 receive the same ordered candidate IDs from
`candidate_bundle_seeds.json`. Every lane emits exactly one row per seed and may
only update its own evidence axis. It cannot add, rename, merge, rank or drop a
candidate. A missing or inaccessible source yields an incomplete/reject status,
not row deletion and not inferred evidence.

All decision-bearing evidence must be authoritative primary sources and carry a
direct locator plus replay status. Search snippets and third-party pages may be
logged as discovery aids but cannot close a field. No lane chooses a winner.

## FD2 — rights and lineage

Output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_q/E4_R3FD2_rights_lineage_verification`

Exact files:

1. `rights_lineage_verification.json`;
2. `rights_lineage_source_log.json`;
3. `fd2_report.md`;
4. `fd2_handoff.json`.

FD2 verifies repository ownership/revision, affirmative code-license text and
scope, canonical dataset provider/release, lawful-use basis, acquisition terms,
raw/source identity, preprocessing and split lineage, checksums when published,
and redistribution/authentication boundaries. Public accessibility does not
imply permission.

Closed statuses:

- `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`;
- `EVIDENCE_INCOMPLETE`;
- `DISPOSITIVE_REJECT`.

## FD3 — benchmark, training and evaluator

Output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_r/E4_R3FD3_benchmark_evaluator_verification`

Exact files:

1. `benchmark_evaluator_verification.json`;
2. `benchmark_source_log.json`;
3. `fd3_report.md`;
4. `fd3_handoff.json`.

FD3 verifies immutable repository revision, environment/dependency recipe,
source-owned preprocessing and split binding, train/evaluate entry points,
config/hyperparameters/seeds, evaluator metric/cutoff/candidate/masking/tie
semantics, and at least one numeric reference target tied to exactly the same
framework–dataset–protocol surface. A paper number without a reusable recipe or
a framework recipe without a same-surface target remains incomplete.

Closed statuses are the same as FD2.

## FD4 — v5 compatibility stress test

Output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_s/E4_R3FD4_v5_compatibility_stress_test`

Exact files:

1. `v5_compatibility_assessment.json`;
2. `adaptation_risk_register.json`;
3. `fd4_report.md`;
4. `fd4_handoff.json`.

FD4 binds each candidate to the frozen v5 spec and local adapter/reporting
contracts. It evaluates task/objective fit, input mapping, temporal split,
full-catalog candidates, seen-item masking, negative sampling, baseline coverage,
shared-evaluator seam, environment isolation, hardware feasibility and a bounded
patch plan. It must distinguish an adapter from a semantic rewrite.

Closed statuses:

- `COMPATIBLE_WITH_BOUNDED_ADAPTER`;
- `COMPATIBILITY_INCOMPLETE`;
- `DISPOSITIVE_REJECT`.

## Execution boundary

Only public web research, read-only local inspection, hashing and declared-root
writes are allowed. Clone/fetch/download, dataset/checkpoint acquisition, terms
acceptance, package installation, environment/container creation, preprocessing,
training, evaluation and TEST access remain forbidden. Each handoff records the
unchanged empirical truth.

