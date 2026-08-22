# Stage 1E — R3-G1 central bundle selection contract

Date: `2026-08-22`  
Runtime: `Sol Max Standard` (`gpt-5.6-sol`, reasoning `max`, service tier
`standard`)  
Context: current central orchestration context

## Entry gate

R3-G1 starts only after:

1. R3-FD1 is centrally schema/hash validated and frozen;
2. FD2, FD3 and FD4 each emit exactly one row for every frozen candidate ID;
3. their exact write sets, candidate-ID equality, source carriers, model profiles,
   truth states and seed hash bindings pass central validation; and
4. no lane artifact has been repaired by R3-G1.

A mechanically valid lane may still be scientifically incomplete. Validation
PASS never promotes its evidence status.

## Exact output

Root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_t/E4_R3G1_bundle_selection`

Files:

1. `bundle_evidence_intersection.json`;
2. `central_locator_replay_log.json`;
3. `bundle_decision_matrix.json`;
4. `selection_decision.json`;
5. `r3_g1_report.md`;
6. `r3_g1_handoff.json`.

## Join and deduplication

R3-G1 joins only by exact `candidate_id`. Repository revision, dataset release,
split/config, evaluator and numeric target identities must also agree within a
row. A conflict is retained as a mismatch; it is never resolved by choosing the
most convenient lane value.

Duplicate candidates are identified by the tuple of repository owner/name plus
immutable revision, dataset provider/release, protocol/config and benchmark
target surface. Duplicate rows are collapsed for ranking only after preserving
all original IDs and evidence conflicts. Deduplication cannot turn two partial
rows into one complete row.

## Central source replay

The central context independently opens every decision-bearing official locator
for any row that could otherwise pass. Replay records URL, expected scope,
access result, observed identity, agreement/mismatch and retrieval date. A failed
or blocked replay remains unresolved and cannot count as positive evidence.

## Selection rule

The gate may select at most one row. Positive selection requires, on the same
candidate and provenance surface:

- FD1 `PLAUSIBLE_COMPLETE_SEED`;
- FD2 `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`;
- FD3 `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`;
- FD4 `COMPATIBLE_WITH_BOUNDED_ADAPTER`;
- affirmative code and data rights;
- same-surface framework–dataset–recipe–result/evaluator join;
- zero dispositive mismatch;
- all decision-bearing central replays PASS.

If multiple rows satisfy the positive rule, apply this predeclared ranking order
without viewing any v5 result: provenance completeness, legal clarity, protocol
fit, evaluator-parity feasibility, adaptation cost, maintenance recency. Every
comparison and tie resolution is recorded. If a tie cannot be resolved from
frozen evidence, select none and request a user decision; do not add a criterion
post hoc.

Allowed verdicts:

- `PROVISIONAL_SINGLE_BUNDLE_FOR_MATERIALIZATION`;
- `NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`.

No fallback is automatic. A positive verdict is provisional and grants no
materialization or execution authority.

## Reporting boundary

The frozen numeric benchmark is a future reproduction target for the selected
framework on its reference dataset. It is not a v5 result and cannot be compared
directly against v5 to claim superiority. Harmonized v5 comparison remains a
later same-dataset, same-split, same-evaluator experiment.

## Mandatory checkpoint

After R3-G1 validation, stop. If one row is selected, present its exact repository
revision, license, dataset release/terms, acquisition actions and proposed local
paths for explicit `R3-M0` approval. If none is selected, present the remaining
evidence gaps and scope options. Clone, download, install, preprocess, train,
evaluate and TEST access remain denied until that checkpoint is answered.

Every output preserves `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`,
`ACCEPTED_RESULT_ROWS=0`, `execution_authorized=false`, and project benchmark
numbers `INVALID_FOR_PAPER`.
