# Stage 1E — R2-ER1-G1 fresh central evidence intersection contract

Date: `2026-08-22`
Context: current central
Runtime: `gpt-5.6-sol` / `max` / `priority` (`Sol Max Fast`)
Execution authority: `DENIED`

## 1. Entry gate

`R2-ER1-G1` may start only from:

`PASS_R2_ER1_PARALLEL_LANES_READY_FOR_FRESH_G1`

The central stage consumes the immutable schema sidecars, all three LightGCN evidence lanes, their handoffs, the central lane validator/receipt and the prior R2-G1 no-selection packet. It may not edit or repair an upstream artifact.

## 2. Candidate and decision rule

The only candidate is `E3-LIGHTGCN-GOWALLA-PYTORCH-001`.

The positive decision `PROVISIONAL_SINGLE_CANDIDATE_FOR_MATERIALIZATION` requires all of the following:

1. schema sidecars conform and preserve scientific truth;
2. A1, A2 and A3 are each exactly `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`;
3. every decision-bearing source is independently replayable at its direct authoritative locator;
4. repository/license, dataset/release/rights/lineage and result/config/run/checkpoint/evaluator fields join to one immutable surface;
5. no field is inferred from public visibility, a repository tree, repository-bundled data, printed metrics, popularity or third-party reproduction;
6. no dispositive mismatch or unresolved required field remains.

If any condition fails, the only valid decision is:

`NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`

Priority is not selection. Three `EVIDENCE_INCOMPLETE` lanes mechanically force `NO_SELECTION`; locator replay still runs to preserve a reviewable evidence delta and explain the remaining blockers.

## 3. Central work

G1 must:

- verify the exact LightGCN row and three lane statuses;
- use the schema sidecars only for carrier conformity, never as new evidence;
- deduplicate repeated URLs before evidence accounting;
- independently replay the decision-bearing official paper, immutable author repository/config/tree, canonical provider/terms metadata, processed-object metadata and source-owned result/evaluator surfaces;
- preserve `supports[]` versus `does_not_support[]` boundaries;
- identify evidence newly closed since prior R2-G1 and evidence still open;
- reject every prohibited cross-join;
- emit zero selected candidates when any lane remains incomplete;
- block R2-M0 and all downstream materialization/execution stages.

## 4. Exact outputs

Output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_o/E4_R2ER1G1_candidate_selection`

Exactly five files:

1. `lightgcn_evidence_intersection.json`;
2. `locator_replay_log.json`;
3. `selection_decision.json`;
4. `er1_g1_report.md`;
5. `er1_g1_handoff.json`.

The handoff hash-binds the other four files and reports its own finalized canonical-LF hash out of band through the central validation receipt.

## 5. Runtime and truth-state requirements

Every output records:

- display name `Sol Max Fast`;
- model `gpt-5.6-sol`;
- reasoning `max`;
- service tier `priority`;
- `Verification Status: UNVERIFIED`;
- `no_experiments_declared`;
- `RESULT_STATUS=NOT_RUN`;
- `TEST_SET_OPENED=NO`;
- `ACCEPTED_RESULT_ROWS=0`;
- `execution_authorized=false`;
- project benchmark numbers `INVALID_FOR_PAPER`.

## 6. Scope guards

Allowed: read-only local inspection, direct public authoritative locator replay without saving source/data payloads, deterministic validation/hash computation and the exact five output files.

Forbidden: clone/fetch/checkout/archive download, dataset/checkpoint/payload acquisition, authentication or terms acceptance, install/environment/container creation, preprocessing, training, evaluation, benchmark execution, TEST access, maintainer contact, new candidate/dataset creation, or paper-grade benchmark promotion.

## 7. Completion

G1 completes only after a deterministic central validator confirms the exact output set, frozen inputs, model profile, three-lane intersection, zero selected candidates when required, hashes, truth state and downstream blocks.
