# Stage 1E — R2-ER1 parallel-lane central validation contract

Date: `2026-08-22`  
Context: current central  
Runtime: `gpt-5.6-sol` / `max` / `priority` (`Sol Max Fast`)  
Execution authority: `DENIED`

## 1. Entry condition

Central validation may start only after all four independently dispatched stages report a terminal handoff:

- `R2-ER1-S`;
- `R2-ER1-A1`;
- `R2-ER1-A2`;
- `R2-ER1-A3`.

The central validator consumes immutable commits or an exact recovered write set. It does not repair a lane artifact. A failed lane returns to its owner under a new version; central control never edits it in place.

## 2. Mechanical validation

For every lane:

1. import only the declared commit and exact write root;
2. reject any write outside the assigned root;
3. require the exact file names and counts frozen by the R2-ER1 contract;
4. reject malformed UTF-8, invalid JSON, duplicate JSON keys and case-colliding keys;
5. verify `31/31` frozen inputs and the input-manifest SHA-256;
6. replay every non-handoff output byte count and canonical-LF SHA-256 from the handoff;
7. require `gpt-5.6-sol`, reasoning `max`, service tier `priority`, display `Sol Max Fast`;
8. require `UNVERIFIED` plus `no_experiments_declared`;
9. require `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, `execution_authorized=false`;
10. require every forbidden-operation flag to be `false`.

Any failure blocks fresh G1.

## 3. Schema-normalization validation

`R2-ER1-S` must contain seven rows per normalized carrier in the original frozen order. Central validation compares each sidecar with its source artifact and requires:

- exact preservation of `row_id`, method, dataset scope, authoritative locators, unresolved fields, dispositive mismatches, recommended disposition and evidence status;
- exact preservation of status counts and empirical truth;
- transformation provenance for every added/renamed carrier field;
- no source artifact modification;
- explicit closure of carrier findings `R2-CF-A1-001`, `R2-CF-A2-001`, `R2-CF-A3-001` as schema-only findings;
- zero scientific promotions.

Schema conformity does not count as evidence sufficiency.

## 4. Evidence-lane validation

Each A1/A2/A3 primary register must contain exactly one row, `E3-LIGHTGCN-GOWALLA-PYTORCH-001`, with the common row schema. Central validation requires:

- a legal evidence status enum;
- direct authoritative URLs with precise locators and bounded `supports[]` / `does_not_support[]`;
- no third-party source used to close a field;
- no cross-row, cross-repository, cross-config, cross-dataset or cross-evaluator join;
- explicit unresolved fields and retrieval failures;
- no silent candidate/dataset expansion;
- no benchmark number accepted for the paper.

The lane may validly finish `EVIDENCE_INCOMPLETE` or `DISPOSITIVE_REJECT`. Central lane validation assesses contract conformity, not whether the evidence is favorable.

## 5. Central verdict

If all checks pass, emit:

`PASS_R2_ER1_PARALLEL_LANES_READY_FOR_FRESH_G1`

This verdict authorizes only creation of a new G1 frozen manifest and central semantic intersection. It does not select LightGCN and does not authorize R2-M0.

If any check fails, emit:

`FAIL_R2_ER1_PARALLEL_LANES_BLOCKED_BEFORE_G1`

and list exact finding IDs. No partial positive selection is allowed.

## 6. Persistent boundary

Clone/fetch, archive or payload download, dataset/checkpoint acquisition, authentication/terms acceptance, install/environment creation, preprocessing, training, evaluation, TEST access and maintainer contact remain prohibited. Project benchmark numbers remain `INVALID_FOR_PAPER`.

