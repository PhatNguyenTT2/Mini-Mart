# Stage R2-ER1-S immutable schema-carrier normalization report

## Material Passport

- Origin Skill: `ars-codex:academic-research-suite/experiment-agent`
- Origin Mode: `evidence-only/schema-normalization/reproducibility-validation/fail-closed`
- Origin Date: `2026-08-22T18:37:27+07:00`
- Verification Status: `UNVERIFIED`
- Version Label: `stage1e_rebaseline_v2_wave_m_E4_R2ER1S_schema_normalization_v1`
- Experiment Intake Declaration: `no_experiments_declared`

## Outcome

`RESULT_STATUS=NOT_RUN`. The three known carrier findings are represented by immutable sidecars, with all 21 candidate-row instances retained in the frozen seven-row order. The sidecars establish schema conformity only. They do not add evidence, promote a status, remove a mismatch, select a candidate, authorize acquisition, or authorize execution.

Stage verdict: `COMPLETE_SCHEMA_NORMALIZATION_TRUTH_PRESERVED_READY_FOR_CENTRAL_VALIDATION`.

## Frozen entry gate

The existing deterministic validator
`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r2_er1_gate.py`
was run read-only with bytecode writes disabled. It exited `0` with
`PASS_R2_ER1_GATE_31_OF_31_READY_FOR_PARALLEL_DISPATCH`: 31 of 31 frozen inputs matched, 24 strict-JSON inputs parsed, and no failure was reported.

The governing finding carrier is
`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r2_evidence_lanes_validation_receipt.json`
(canonical-LF SHA-256 `1335836553caa160d93fe3cc8baee041afbbe9846f0e18fd2b4eb68d4c3607b8`).

## Exact candidate order

1. `E3-LIGHTGCN-GOWALLA-PYTORCH-001`
2. `E3-SIMGCL-YELP2018-QREC-001`
3. `E3-XSIMGCL-YELP2018-SELFREC-001`
4. `E3-LIGHTGCL-YELP-UPDATED-001`
5. `E3-UNISREC-SCIENTIFIC-TRANS-001`
6. `E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001`
7. `E3-ALPHAREC-MOVIES-TV-001`

## Finding-normalization map

| Finding | Immutable source and JSON pointer | Sidecar transformation | Value class |
|---|---|---|---|
| `R2-CF-A1-001` | `.../E4_R2A1_repo_evidence/a1_handoff.json#/coverage/status_counts/EVIDENCE_SUFFICIENT` | Copy value `0` under `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`; retain the source `OTHER=0` auxiliary count separately; copy all seven A1 rows exactly. | Copied value; key expansion only |
| `R2-CF-A2-001` | `.../E4_R2A2_dataset_evidence/dataset_evidence_register.json#/candidate_rows/0` through `/candidate_rows/6` | Copy `lane_evidence_status` to `evidence_status`, `confirmed_dataset_layers` to `confirmed_fields`, document `lane_id` and truth guards into each common row; retain every existing scientific member. | Copied values plus one explicit structural default per row |
| `R2-CF-A3-001` | `.../E4_R2A3_metric_evidence/a3_handoff.json#/lane_id`, register `#/lane_id`, and register `#/rows/0/lane_id` through `/rows/6/lane_id` | Replace only the structural carrier identifier with canonical `R2-A3` in the sidecar; copy all non-lane row members exactly. | Structural default for lane identity; scientific values copied |

The full machine-readable transformation ledgers are embedded in the three normalized carriers. Every ledger row supplies a source file and RFC 6901 JSON pointer. Entries are explicitly classified as `COPIED_VALUE` or `STRUCTURAL_DEFAULT`.

## Structural defaults

Seven A2 rows lacked `inferences_forbidden`. Each normalized row therefore carries `inferences_forbidden: []` solely to satisfy the frozen common-row shape. The ledger cites the exact source row, the finding pointer, and Section 7 of the frozen evidence-track contract. The empty array is carrier metadata: it does not assert that no inference prohibition exists and creates no scientific content.

The nine A3 lane-identifier replacements comprise the sidecar top-level carrier, normalized handoff field, and seven rows. Their canonical value comes from
`rebaseline_v2_e4_r2_evidence_lanes_validation_receipt.json#/contract_findings/2/lane_id`.
The original files remain immutable.

A1 uses no scientific structural default. Its sufficient-status value is copied exactly while only the abbreviated key is expanded.

## Truth-preservation replay

| Lane | Rows | Status counts preserved | Dispositive mismatches preserved | Dispositions preserved |
|---|---:|---|---:|---|
| R2-A1 | 7 | sufficient 0; incomplete 6; reject 1; handoff-incomplete 0 | 1 | 7/7 |
| R2-A2 | 7 | sufficient 0; incomplete 7; reject 0 | 0 | 7/7 |
| R2-A3 | 7 | sufficient 0; incomplete 7; reject 0 | 3 mismatch statements across two rows | 7/7 |

The semantic replay strict-parsed eight JSON documents (three sources, two source handoffs, and three sidecars), rejected duplicate or case-colliding keys, and passed:

- frozen order: 7 of 7 in each lane;
- common row keys: 21 of 21 normalized rows;
- copied scientific values: deep-equal after reversible structural-key mapping;
- status promotions: 0;
- mismatches removed: 0;
- truth-state changes: 0;
- candidate selections: 0;
- evidence creations: 0.

## Persistent truth state

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- project benchmark numbers remain `INVALID_FOR_PAPER`

## Boundaries and limitations

No web research, clone, fetch, download, installation, environment/container creation, preprocessing, training, evaluation, benchmark execution, TEST access, candidate selection, or original-artifact edit occurred. All sidecar scientific content is copied from frozen inputs; the only defaults are the explicitly identified common-row carrier fields.

`UNVERIFIED` is mandatory: this work normalizes carriers and does not reproduce or validate an experiment. Central validation remains the next gate. No incident occurred during normalization.
