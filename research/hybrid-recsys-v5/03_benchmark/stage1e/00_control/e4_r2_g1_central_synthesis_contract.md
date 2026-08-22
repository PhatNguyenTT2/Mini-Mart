# Stage 1E — R2-G1 central evidence intersection contract

Contract status: `FROZEN_FOR_FAIL_CLOSED_NO_SELECTION_SYNTHESIS`  
Created: `2026-08-22`  
Workflow: `ars-codex:academic-research-suite / academic-pipeline + experiment-agent evidence discipline`  
Context: current central task  
Model: `gpt-5.6-sol`  
Reasoning: `high`  
Execution authority: `DENIED`

## 1. Entry condition

R2-A1, R2-A2 and R2-A3 have been imported with their original provenance commits. Central mechanical replay established:

- exact four-file sets for all three lanes;
- 11/11 strict JSON parses with duplicate and case-collision rejection;
- all handoff and declared output hashes match;
- all three Material Passports remain `UNVERIFIED` and declare no experiment;
- `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, and execution is not authorized;
- no candidate is sufficient across A1 × A2 × A3.

The central intake receipt is contract-nonconformant because of `R2-CF-A1-001`, `R2-CF-A2-001`, and `R2-CF-A3-001`. Therefore this gate may issue only the negative decision:

`NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`

It may not issue `PROVISIONAL_SINGLE_CANDIDATE_FOR_MATERIALIZATION`.

## 2. Inputs

The frozen manifest must bind:

1. the R2 evidence-track contract, plan, stage map, entry manifest, entry-gate receipt and dispatch record;
2. the central lane validator and lane-validation receipt;
3. all twelve imported lane artifacts;
4. this contract.

Any missing byte, hash mismatch, duplicate/case-colliding JSON key, candidate-order drift or positive-selection attempt fails closed.

## 3. Required work

Central G1 must:

1. join candidates only by exact `row_id` in the frozen seven-row order;
2. preserve the three lane statuses separately;
3. deduplicate source locators without converting repeated mentions into independent evidence;
4. replay the high-impact primary locators for the LightGCN priority row, XSimGCL dispositive mismatch, Gowalla provider boundary and UniSRec code-license boundary;
5. distinguish repository code license from dataset rights, external assets, checkpoint/run receipts and evaluator parity;
6. record every schema nonconformance without repairing a lane-owned artifact;
7. return zero selected candidates and block R2-M0, R2-B1, R2-B2, R2-B3 and all execution stages.

## 4. Exact output set

Output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_h/E4_R2G1_candidate_selection`

Exactly five files are required:

1. `central_evidence_intersection.json`;
2. `candidate_decision_matrix.json`;
3. `primary_locator_replay_log.json`;
4. `r2_g1_no_selection_report.md`;
5. `r2_g1_handoff.json`.

The handoff self-hash is reported by the central validation receipt after the file is finalized. The handoff must hash-bind the other four files.

## 5. Decision rule

A row is eligible for provisional materialization only if all three lane statuses are exactly `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`, no dispositive mismatch exists, every common row contract is conformant, and the source/dataset/result/evaluator identities form one lawful exact join.

Current evidence has zero such rows. Consequently the only valid output is:

`NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`

Priority is not selection. A positive code license is not dataset authorization. A printed source result is not a run receipt. Repository-bundled processed data is not canonical raw-to-split lineage.

## 6. Scope guards

Forbidden:

- cloning, fetching, checking out or downloading source archives;
- downloading or authenticating to datasets, accepting terms or opening TEST;
- package installation, environment/container creation, preprocessing, training, evaluation or benchmark execution;
- editing lane-owned artifacts to conceal nonconformance;
- creating an acquisition/materialization approval packet;
- carrying any benchmark number into the paper as valid evidence.

Allowed:

- read-only local inspection;
- public primary-source locator replay without saving source/dataset payloads;
- deterministic validation and hash computation;
- creation of the five bounded G1 outputs and central control receipts.

## 7. Completion state

G1 completes fail-closed when the five-file packet validates, selected candidate count is zero, the verdict is `NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`, and all downstream materialization/execution gates remain blocked.

The next stage is not R2-M0. It is a change-controlled evidence-remediation decision at a user checkpoint.
