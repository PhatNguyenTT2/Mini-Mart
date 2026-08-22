# Stage 1E — E4 R2-ER1 change-controlled evidence remediation contract

Date: `2026-08-22`  
Stage family: `R2-ER1`  
Entry verdict: `NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`  
User checkpoint: `CONFIRMED_CONTINUE_WITH_REMEDIATION`  
Execution authority: `DENIED`

## 1. Objective

This round may close only the evidence gaps that prevented the LightGCN/Gowalla priority row from passing `R2-G1`. It must also normalize the three prior lane carriers through immutable sidecars so that a fresh central gate can distinguish schema conformity from scientific sufficiency.

The only candidate in scope is:

- `row_id`: `E3-LIGHTGCN-GOWALLA-PYTORCH-001`;
- method: `LightGCN`;
- reference surface: the author-maintained LightGCN PyTorch repository and its repository-bundled Gowalla processed split;
- current status: evidence priority only, not selected and not execution-ready.

No additional repository, framework, dataset, candidate row or benchmark center may be silently substituted. Any scope expansion requires a new user checkpoint, contract and frozen manifest.

## 2. Runtime model policy

The user explicitly selected `Sol Max Fast` for every important stage in this round. The runtime mapping is frozen as:

- display name: `Sol Max Fast`;
- model ID: `gpt-5.6-sol`;
- reasoning effort: `max`;
- speed/service tier: `priority` (`Fast`);
- adapter: `ars-codex:academic-research-suite` `0.1.26`;
- ARS suite: `3.21.0`.

`Fast` changes the service tier, not the evidence threshold. No stage may lower reasoning to `high`/`xhigh`, inherit standard speed, or claim `Sol Max Fast` without recording all four runtime fields above. User-only checkpoints such as `R2-M0` do not have a model.

## 3. Stage topology

After `R2-ER1-0` passes, four disjoint stages may run concurrently:

1. `R2-ER1-S` — normalize the existing A1/A2/A3 schema carriers through sidecars only;
2. `R2-ER1-A1` — resolve repository, paper/config and affirmative code-license evidence for LightGCN;
3. `R2-ER1-A2` — resolve canonical provider/release/rights and exact raw-to-processed-to-split lineage evidence for Gowalla;
4. `R2-ER1-A3` — resolve the source-bound result center, config/seed/checkpoint/run and evaluator semantics.

`R2-ER1-G1` is sequential and central. It starts only after all four outputs pass exact-set, schema and hash validation.

The three evidence lanes use fresh independent contexts. Schema normalization and `G1` use central control context. Every substantive stage uses the model policy in Section 2.

## 4. Schema normalization boundary

`R2-ER1-S` must not edit any imported `R2-A1`, `R2-A2`, `R2-A3` or `R2-G1` artifact. It creates compatibility sidecars that:

- use the common row keys frozen by the original R2 evidence contract;
- preserve every source locator, unresolved field, mismatch, status and truth-state value;
- map `lane_evidence_status` to `evidence_status` only when the value is copied exactly;
- restore the canonical lane identifier only in the new sidecar;
- expand abbreviated status-count keys without changing counts;
- record every transformation and its source JSON pointer;
- never promote `EVIDENCE_INCOMPLETE` or remove a dispositive mismatch.

Normalization proves carrier conformity only. It cannot create evidence or make a candidate selectable.

Exact output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_m/E4_R2ER1S_schema_normalization`

Exact files:

1. `a1_normalized_carrier.json`;
2. `a2_normalized_carrier.json`;
3. `a3_normalized_carrier.json`;
4. `schema_normalization_report.md`;
5. `er1_s_handoff.json`.

## 5. Evidence-lane contracts

Only direct authoritative sources may close a field: the paper/proceedings record, author-maintained repository and immutable repository files, canonical provider/terms/release pages, and source-owned benchmark/config/log/checkpoint/evaluator artifacts. Search snippets, mirrors, blogs, forks, third-party reproductions and absence-of-a-license searches are locators only.

Each lane must use exactly one row with the common keys from the original R2 evidence contract and one of these statuses:

- `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`;
- `EVIDENCE_INCOMPLETE`;
- `DISPOSITIVE_REJECT`;
- `HANDOFF_INCOMPLETE`.

All uncertainty remains explicit. Missing evidence cannot be inferred from popularity, paper publication, public repository access or repository-bundled data.

### R2-ER1-A1 — repository and license

Must establish, at one immutable revision:

- paper-to-repository relationship;
- repository tree/config/command identity;
- affirmative code-use/license basis and its scope;
- submodule or external-code boundaries;
- any mismatch between the published center and pinned config.

Output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_n/E4_R2ER1A1_repo_license`

Exact files: `lightgcn_repo_license_evidence.json`, `paper_repo_config_binding.json`, `repo_license_report.md`, `er1_a1_handoff.json`.

### R2-ER1-A2 — dataset rights and lineage

Must establish:

- canonical provider/release identity where publicly supportable;
- lawful research-use terms and any authentication/acceptance/redistribution boundary;
- distinction between canonical raw data and repository-bundled processed files;
- exact, source-supported raw-to-filtered-to-ID-mapped-to-split lineage;
- checksums or explicit `NOT_ACQUIRED` states;
- every acquisition action that would later require `R2-M0`.

Output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_n/E4_R2ER1A2_dataset_lineage`

Exact files: `lightgcn_dataset_lineage_evidence.json`, `rights_release_matrix.json`, `processed_split_lineage_map.json`, `er1_a2_handoff.json`.

### R2-ER1-A3 — result center and evaluator

Must establish one non-cross-joined surface containing:

- exact reported LightGCN/Gowalla result cell and locator;
- implementation, config, layer count, seed/run schedule and checkpoint rule;
- metric/cutoff/averaging/relevance denominator;
- candidate universe, masking, sampling and deterministic tie semantics;
- source evaluator identity and an immutable source-owned run/checkpoint/evaluator receipt when available;
- an explicit list of fields that remain unknown or incompatible with the v5 shared evaluator.

Output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_n/E4_R2ER1A3_result_evaluator`

Exact files: `lightgcn_result_evaluator_evidence.json`, `center_run_checkpoint_binding.json`, `metric_evaluator_contract.json`, `er1_a3_handoff.json`.

## 6. Fresh central G1 rule

`R2-ER1-G1` may issue `PROVISIONAL_SINGLE_CANDIDATE_FOR_MATERIALIZATION` only when:

1. schema normalization passes without altering scientific truth;
2. A1, A2 and A3 are each exactly `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`;
3. all evidence joins by the exact LightGCN row, immutable implementation, dataset/split and result/evaluator identity;
4. there is an affirmative lawful basis for code and data use;
5. there is no dispositive mismatch or inferred missing field;
6. independent locator replay confirms every decision-bearing source.

Otherwise the only valid verdict is `NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`.

Exact output root:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_o/E4_R2ER1G1_candidate_selection`

Exact files: `lightgcn_evidence_intersection.json`, `locator_replay_log.json`, `selection_decision.json`, `er1_g1_report.md`, `er1_g1_handoff.json`.

Even a positive G1 decision is provisional. It does not authorize material acquisition or execution; the next mandatory boundary remains an exact user checkpoint at `R2-M0`.

## 7. Forbidden operations

Until a positive G1 decision and later explicit `R2-M0` approval, every stage is forbidden from:

- cloning, fetching, checking out or downloading repository/source archives;
- downloading datasets, processed splits, checkpoints or authenticated assets;
- accepting terms or credentials on the user's behalf;
- installing packages or creating environments/containers;
- preprocessing, training, evaluation or benchmark execution;
- opening the v5 TEST set;
- copying any current benchmark number into the paper as valid comparative evidence;
- contacting maintainers or creating a new candidate row without user authorization.

Allowed work is read-only local inspection, public authoritative web replay without saving payloads, deterministic validation/hash computation, and writes confined to the declared control/output roots.

## 8. Persistent truth state

All artifacts in this round must preserve:

- `RESULT_STATUS=NOT_RUN`;
- `TEST_SET_OPENED=NO`;
- `ACCEPTED_RESULT_ROWS=0`;
- `execution_authorized=false`;
- project benchmark numbers: `INVALID_FOR_PAPER`.

