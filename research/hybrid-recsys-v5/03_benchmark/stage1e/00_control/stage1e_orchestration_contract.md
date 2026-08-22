# Stage 1E Orchestration Contract

> Material Passport: `stage1e_plan_wave1_v1` · status `UNVERIFIED`  
> Model policy: every Stage 1E task uses `gpt-5.6-sol` with reasoning `high`.  
> Scope of Wave 1: planning, provenance verification, and preregistration inputs only. No training, TEST evaluation, dataset download, repository cloning, environment mutation, or benchmark execution is authorized in this wave.

## 1. Objective

Stage 1E converts the sealed Stage 1A/1B research design and the existing v5 artifacts into an executable, auditable experiment protocol. The stage is complete only after dataset lineage, adapter provenance, evaluator/statistics contracts, external-data compatibility, tuning/compute policy, official reproductions, harmonized runs, statistical validation, and final artifact sealing have passed their gates.

All empirical claims remain `NOT_RUN`. Existing v5 snapshot, feature, and rule files are inputs to audit, not accepted model results.

## 2. Dependency graph

```text
Wave 1 — independent planning lanes (parallel)
  E1 Dataset lineage + protocol/test seal ---------+
  E2 Baseline provenance + reproduction registry --+
  E3 Evaluator + statistics + registry contracts ---+--> E6 Central preregistration lock
  E4 External datasets + rights compatibility ------+
  E5 Compute + tuning + runtime protocol ------------+

E6 PASS
  -> exact-command confirmation checkpoint
  -> AR0 shared adapter/evaluator infrastructure
  -> AR1/AR2/AR3 isolated adapter preparation (parallel where write sets do not overlap)
  -> official-dataset smoke/reproduction (one GPU job at a time)
  -> accepted adapter registry lock
  -> harmonized v5 validation/tuning
  -> finalist and comparator lock
  -> three-seed final training
  -> single controlled TEST opening
  -> hierarchical paired inference
  -> full-contract external validation
  -> post-accuracy efficiency gate
  -> independent audit and seal
```

E6 must not start until all five Wave 1 handoffs are present and pass their lane validators. Adapt/Reproduce must not start until E6 freezes exact commands, working directories, inputs, outputs, tolerances, and stop rules. In accordance with the ARS experiment-agent safety contract, command execution requires explicit confirmation of those exact commands.

## 3. Wave 1 lane contracts

| Lane | Independent scope | Required outputs | Hard exclusions |
|---|---|---|---|
| `E1_dataset_protocol` | Audit v5 snapshot/feature/rule lineage; derive DatasetManifest; verify split/candidate/cold/rule contracts and design a fail-closed TEST seal. | `dataset_manifest_draft.json`, `protocol_lock_draft.md`, `test_seal_audit.md`, `lane_handoff.json` | Do not load TEST rows, compute TEST metrics, train, mutate artifacts, or silently reconcile hash differences. |
| `E2_baseline_provenance` | Verify official/primary repositories, immutable revisions, licenses, reference datasets/protocols, reported centers, software constraints, and method-faithful reproduction tolerances for all mandatory baselines. | `baseline_registry_draft.json`, `reference_reproduction_matrix.md`, `environment_isolation_matrix.md`, `exclusion_candidates.md`, `lane_handoff.json` | No cloning, package installation, code execution, or use of secondary blog/listicle claims as authority. |
| `E3_evaluator_statistics` | Audit shared evaluator seam and current gaps; freeze metric, per-user evidence, adapter/result schemas, registry/test-lock, hierarchical bootstrap, multiplicity, corruption/parity tests. | `evaluator_contract_draft.md`, `statistics_preregistration_draft.md`, `schema_contracts_draft.json`, `implementation_gap_register.md`, `lane_handoff.json` | No source-code modification and no metric computation on v5 TEST. |
| `E4_external_data` | Verify full-mechanism and Vietnamese-sensitivity dataset candidates against task/schema/history/text/basket/license/access/redistribution requirements using current primary sources. | `external_dataset_registry_draft.json`, `compatibility_and_rights_matrix.md`, `acquisition_plan.md`, `lane_handoff.json` | No dataset download/upload, acceptance by name alone, or raw cross-dataset score comparison. |
| `E5_compute_runtime` | Freeze tuning fairness, seed/stopping/failure policy, RTX 3060 6GB scheduling, resource tiers, runtime runner/workload/statistics/threshold rationale, exact-command template, and stall protocol. | `tuning_compute_protocol_draft.md`, `runtime_preregistration_draft.md`, `execution_dag.json`, `command_confirmation_template.md`, `lane_handoff.json` | No GPU job, benchmark, package installation, architecture shrinkage, or post-outcome threshold selection. |

Every lane must:

1. read the ARS Academic Research Suite skill and experiment-agent workflow;
2. consume the frozen input manifest by hash;
3. distinguish `CONTRACT`, `RECEIPT`, `TARGET`, and `RESULT`;
4. record unresolved items as blockers, never fill them by inference;
5. assign each conclusion an evidence pointer (local path plus line/JSON pointer, or current primary-source URL with access date);
6. keep outputs `UNVERIFIED` and emit a machine-readable handoff;
7. change only its assigned output directory and commit only those files.

## 4. Wave 1 acceptance gate

Central integration may begin only when:

- five `lane_handoff.json` files parse and report terminal status;
- no lane claims a benchmark/training/evaluation result;
- every mandatory baseline has provenance status, immutable revision status, reference-reproduction protocol status, license status, and a deterministic include/exclude gate;
- v5 TEST remains unopened for semantic inspection or evaluation;
- every dataset hash discrepancy is explained by a reproducible canonicalization rule or remains blocking;
- statistics specifies per-user vectors, three seeds `42/2027/31415`, hierarchical paired bootstrap with 2,000 replicates, CI decision rules, and Holm handling;
- tuning and runtime thresholds are frozen before outcome access;
- external candidates are classified `FULL_CONTRACT`, `REDUCED_METHOD_SENSITIVITY`, `INCOMPATIBLE`, or `PENDING`, with rights separated from access.

## 5. Post-Wave 1 stages

### E6 — Central preregistration lock

E6 merges and deduplicates the five lanes, resolves contradictions against the RQ/estimand matrix, generates immutable DatasetManifest/BaselineRegistry/adapter/evaluator/statistics/tuning/runtime contracts, and emits a fail-closed readiness verdict. E6 is a fresh Sol High task and cannot invent missing evidence.

### AR0 — Shared infrastructure

AR0 may begin only after E6 PASS and exact-command confirmation. It implements the deepest shared seams first: adapter protocol, run receipts, result bundle, evaluator import path, typed baseline registry, registry lock, TEST refusal, per-user artifact validation, and statistical utilities. Tests must prove wrong shape, NaN, candidate-order mismatch, split leakage, seen-item leakage, registry mismatch, and premature TEST access fail closed.

### AR1–AR3 — Adapter preparation

- `AR1`: local sanity/rule/neighborhood plus unified-framework BPR-MF, LightGCN, SASRec, BERT4Rec.
- `AR2`: BTBR/Mask-Swap, UniSRec, AlphaRec.
- `AR3`: SimGCL/QRec, XSimGCL/SELFRec, LightGCL.

Environment and adapter code preparation may be parallel when write sets and environments are isolated. GPU smoke tests and official reproductions are sequential on the local 6GB GPU. QRec/TensorFlow 1.14 is always isolated.

### HR — Harmonized and external runs

The run sequence is strict: official reproduction acceptance → adapter registry lock → v5 validation-only tuning (maximum 12 completed trials per comparable tier) → seed-42 diagnostic gate → lock configs/checkpoints → final seeds → finalist/comparator lock → one TEST opening → inference → external full-contract track → Vietnamese sensitivity track → efficiency after accuracy. Failed/null/negative runs are retained.

## 6. Safety and truth-state rules

- `TEST_SET_OPENED` stays `NO` through planning, adaptation, official reproduction, and v5 validation selection.
- File existence and cryptographic hashing do not authorize semantic inspection of TEST rows.
- Official-protocol reproduction validates an adapter; it is not evidence that one model beats another on v5.
- Raw metrics from different datasets or pipelines never enter one superiority table.
- Thresholds `.75/.15/.08` remain internal `TARGET` values, never observed results.
- No task may silently retry a crashed experiment, shrink an architecture, replace a seed, or modify a preregistered tolerance after seeing outcomes.
- External uploads are prohibited. Dataset/license access and redistribution rights are distinct fields.

