# Stage 1E Rebaseline v2 Contract

> Material Passport: `stage1e_rebaseline_v2` · status `UNVERIFIED`  
> Model policy: every E1–E5 evidence-lock task uses `gpt-5.6-sol` with reasoning `xhigh`.  
> Truth reset: every pre-existing model benchmark is `INVALID_FOR_PAPER`; `ACCEPTED_RESULT_ROWS = 0`; `TEST_SET_OPENED = NO`.

## 1. Corrected objective

Stage 1E must establish a reproducible evidence bridge from author-official or framework-authoritative training pipelines to the current v5 dataset. Existing project metrics, historical figures, estimated values, and runs without immutable repo/dataset/config/evaluator receipts cannot be repaired by relabeling and are not inputs to model-effect claims.

The required order is:

1. identify authoritative GitHub repositories and their original training/evaluation pipelines;
2. bind each candidate to an exact public reference dataset, revision, official preprocessing/split, objective, config, metric semantics, reported benchmark center, and license;
3. lock immutable repository revision, isolated environment, reproduction command, expected outputs, tolerance, hardware allowance, and failure rule;
4. only after the evidence lock, clone and reproduce the original benchmark unchanged;
5. only after reproduction acceptance, create a method-faithful adapter for v5;
6. evaluate baselines and the proposed model on v5 through the same harmonized split, candidate, masking, tuning, seed, and evaluator contract;
7. where compatible, run the harmonized model set on a public external dataset and report a separate dataset-specific table.

Raw NDCG/HR/Recall/GAUC values from different datasets, candidate policies, splits, or evaluator implementations must never be compared as if they formed one league table. Cross-dataset evidence is based on dataset-specific effects, direction, uncertainty, and robustness under an explicitly harmonized protocol.

## 2. Dependency graph

```text
Wave A — independent evidence discovery, parallel, Sol XHigh
  E1 Official Repository & Training Pipeline Registry ----+
  E2 Reference Dataset & Rights Registry -----------------+--> Wave B
  E3 Official Metric & Benchmark Ground Truth ------------+

Wave B — dependent synthesis, Sol XHigh
  E4 Repo–Dataset–Metric Matching + Reproduction/Adaptation Lock
       -> exact-command confirmation checkpoint
       -> clone/install in isolated namespaces
       -> original benchmark reproduction
       -> adapter implementation plan for v5

Wave C — independent final audit, Sol XHigh
  E5 Independent Lock Audit
       -> PASS: execution may begin with confirmed exact commands
       -> REVISE/FAIL: return to the owning lane; no clone/training
```

E4 must not be dispatched before all three Wave A handoffs exist and pass structural validation. E5 must receive a frozen E4 packet and must not participate in E4 synthesis.

## 3. E1 — Official Repository & Training Pipeline Registry

Purpose: find the executable source authority for every required baseline family.

Required coverage:

- Random, MostPop, ItemCF/ItemKNN, Apriori;
- BPR-MF, LightGCN, SASRec, BERT4Rec;
- BTBR/Mask-Swap-NNBR, UniSRec, AlphaRec;
- SimGCL, XSimGCL, LightGCL;
- independent Deep and current Hybrid as project conditions.

For every candidate:

- author-official paper and repository identity;
- full immutable commit SHA and tag/release relationship;
- repository license and code/data license separation;
- official entrypoint, config, preprocessing, training, evaluation, checkpoint, and result artifact paths;
- native framework/runtime, dependency age, CUDA/Python constraints, and expected hardware;
- official dataset names and exact config references;
- whether code emits per-user scores/metrics or requires a bounded adapter;
- provenance class: `AUTHOR_OFFICIAL`, `FRAMEWORK_AUTHORITATIVE`, `INDEPENDENT`, or `REJECTED`.

Repository priority is author-official, then framework-authoritative, then independent only after a reference reproduction. RecBole must not be called author-official for algorithms authored elsewhere.

Outputs:

- `official_repo_registry.json`
- `training_pipeline_command_map.md`
- `implementation_provenance_matrix.md`
- `repo_exclusion_log.md`
- `lane_handoff.json`

## 4. E2 — Reference Dataset & Rights Registry

Purpose: establish the exact reference data on which each selected implementation can be reproduced.

For every candidate dataset:

- provider/canonical page, exact release/revision and immutable hash mechanism;
- download/access route, license/terms, research/commercial/redistribution and derivative-artifact rights as separate fields;
- task, interaction labels, timestamp/order/session/basket structure, item text, user history and cold-item support;
- official preprocessing, filtering, split, negative/candidate policy and supported model subset;
- size facts only from official artifacts or papers, with locator;
- PII/re-identification and release constraints;
- status: `REFERENCE_REPRODUCTION_READY`, `HARMONIZED_EXTERNAL_CANDIDATE`, `SENSITIVITY_ONLY`, `PENDING`, or `REJECTED`.

The registry must distinguish the official reproduction dataset from the public external dataset chosen for cross-dataset validation. One dataset may serve both roles only if both contracts independently pass.

Outputs:

- `reference_dataset_registry.json`
- `dataset_repo_compatibility_matrix.md`
- `rights_and_access_matrix.md`
- `dataset_exclusion_log.md`
- `lane_handoff.json`

## 5. E3 — Official Metric & Benchmark Ground Truth

Purpose: extract what the original repository/paper actually measured, so reproduction is judged against the same target.

For every repo–dataset candidate pair:

- exact metric names and formulas where specified;
- cutoff K, averaging unit, eligible-user rule, relevance definition and tie handling;
- full-catalog versus sampled candidates, negative-sampling count and sampler;
- split/preprocessing/objective/config/seed/checkpoint-selection semantics;
- reported benchmark center, uncertainty or number of runs, table/README/config locator;
- whether the published number can be reproduced from public artifacts;
- pre-run tolerance: default `max(0.005 absolute, 5% relative)` unless a source-bound alternative is justified;
- deterministic PASS/FAIL/INCOMPARABLE rule.

If metric semantics or the reported center cannot be proven, the row remains `PENDING` and cannot authorize reproduction acceptance.

Outputs:

- `official_benchmark_registry.json`
- `metric_protocol_matrix.md`
- `reported_result_locator_map.md`
- `reproduction_acceptance_rules.md`
- `lane_handoff.json`

## 6. E4 — Repo–Dataset–Metric Matching and Adaptation Lock

E4 consumes only validated E1–E3 handoffs. It must:

- select the minimum defensible bundle of official/framework repositories;
- bind each model to one immutable repo revision, reference dataset, official command/config, metric target, tolerance and environment;
- define exact clone/install/preprocess/train/evaluate commands without executing them;
- produce isolated environment and storage namespaces;
- schedule local RTX 3060 6GB jobs one at a time and mark unsupported faithful recipes for external-compute approval or exclusion;
- define original-reproduction receipts and fail-closed acceptance;
- map accepted implementations to the v5 DatasetManifest and shared evaluator without changing method identity;
- define the three evidence tracks:
  - `OFFICIAL_PROTOCOL_REPRODUCTION` — implementation validity only;
  - `HARMONIZED_V5_COMPARISON` — primary internal comparison;
  - `HARMONIZED_EXTERNAL_VALIDATION` — separate dataset-specific robustness;
- preserve `TEST_SET_OPENED = NO` through adaptation and validation selection;
- emit the exact-command confirmation packet required by ARS before execution.

Outputs:

- `selected_reference_bundle.json`
- `reproduction_execution_plan.md`
- `v5_adapter_and_evaluator_contract.md`
- `cross_dataset_reporting_contract.md`
- `exact_command_confirmation_packet.json`
- `e4_handoff.json`

## 7. E5 — Independent Lock Audit

E5 independently replays source URLs, local hashes, registry joins, reported result locators, tolerance arithmetic, licensing distinctions, command/config bindings and cross-dataset boundaries.

PASS requires:

- every selected learned baseline has an immutable source revision;
- every reproduction row has an accessible reference dataset or an explicit lawful acquisition gate;
- every benchmark center is tied to the same dataset/config/metric semantics used by the reproduction command;
- every tolerance is frozen before execution;
- no row compares raw metrics across incompatible datasets/pipelines;
- v5 adaptation happens only after official reproduction acceptance;
- exact commands, working directories, outputs, timeout, resource limits and no-auto-retry rules are complete;
- no TEST semantic access or empirical result claim occurred.

Outputs:

- `independent_lock_audit.md`
- `audit_findings.json`
- `replay_receipt.json`
- `stage1e_execution_authorization.json`
- `e5_handoff.json`

## 8. Current execution boundary

Wave A authorizes web verification and local read-only inspection only. It does not authorize cloning, downloading datasets, installing packages, modifying model code, running training, evaluating TEST, or uploading private artifacts.

After E5 PASS, clone/reproduction still starts only after the user confirms the exact command packet, as required by the ARS experiment-agent. No crash is auto-retried, no architecture is silently reduced, and no failed seed is replaced.

