# Stage 1E — E4-R2 evidence and materialization plan

Status: `PLAN_PREPARED_NOT_DISPATCHED`  
Created: `2026-08-22`  
Pipeline: `stage1e / rebaseline_v2`  
Execution authorization: `DENIED`

## 1. Entry state from E5-R1

E4-R2 starts only from the centrally validated E5-R1 receipt:

- verdict: `PASS_E5_R1_REMEDIATION_INTEGRITY_EXECUTION_DENIED`;
- frozen inputs: `19/19` verified;
- Wave F outputs: `5/5` verified;
- mechanical assertions: `28/28` passed;
- new findings: `0 CRITICAL / 0 MAJOR / 0 MINOR`;
- original findings closed for remediation integrity: `4/4`;
- original findings closed for execution readiness: `0/4`;
- candidate state: `0 READY / 7 PENDING / 6 REJECTED`;
- command state: `10/10` command strings are null;
- prerequisite state: only old-packet `P13_NEW_FROZEN_CENTRAL_PACKET` is resolved; fourteen are unresolved;
- empirical truth: `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`;
- project benchmark numbers remain `INVALID_FOR_PAPER`.

E5-R1 therefore validates fail-closed remediation integrity. It does not validate reproducibility and does not authorize cloning, acquisition, installation, preprocessing, training, evaluation, or TEST access.

## 2. Objective and non-objectives

E4-R2 must produce one exact, source-bound, lawful, materialized official-reproduction packet. The packet may become confirmable only after a fresh independent audit.

E4-R2 does not:

- execute a benchmark;
- open the v5 TEST set;
- accept or report any project result;
- compare raw metrics across datasets, splits, candidate universes, implementations, or evaluators;
- promote a repository merely because its README command runs;
- infer missing licenses, dataset rights, lineage, seeds, checkpoints, evaluator semantics, or result centers;
- treat framework-only MovieLens evidence as an official-reproduction result;
- reuse old `P13` as the freeze receipt for the future materialized packet.

## 3. Candidate scope and selection rule

The evidence round is frozen to the seven `PENDING_EVIDENCE` rows in `selected_reference_bundle.json`:

1. `E3-LIGHTGCN-GOWALLA-PYTORCH-001`;
2. `E3-SIMGCL-YELP2018-QREC-001`;
3. `E3-XSIMGCL-YELP2018-SELFREC-001`;
4. `E3-LIGHTGCL-YELP-UPDATED-001`;
5. `E3-UNISREC-SCIENTIFIC-TRANS-001`;
6. `E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001`;
7. `E3-ALPHAREC-MOVIES-TV-001`.

`E3-LIGHTGCN-GOWALLA-PYTORCH-001` remains the first evidence-resolution priority because its command/seed/center binding is currently strongest. Priority is not selection, readiness, or execution authority.

The five prohibited joins and the rejected BTBR row remain rejected. RecBole/RecBole-GNN with MovieLens may be assessed only as a separately labelled framework/reference route unless a change-controlled source-bound benchmark row is created; it cannot silently replace one of the seven rows above.

The central gate may select at most one provisional materialization target. It must return `NO_SELECTION` if no row has authoritative repo/config/license, dataset provider/release/rights, source-bound result center, metric/evaluator semantics, and a feasible path to close every material binding. There is no automatic fallback or row promotion.

## 4. Stage map, dependencies, contexts, and models

| Stage | Scope | Dependency | Context | Model | Exit gate |
|---|---|---|---|---|---|
| `R2-0` | Freeze this plan, entry receipt, candidate scope, evidence rules, output schemas, and execution boundary | E5-R1 central PASS | current central context | `gpt-5.6-sol`, `high` | plan and machine map hash-valid; no task dispatched |
| `R2-A1` | Official repository, paper-to-repo/config binding, immutable revision, license, submodule/tree and executable-interface evidence for all seven pending rows | R2-0 frozen input manifest | fresh independent evidence context | `gpt-5.6-sol`, `xhigh` | one closed evidence row per candidate; uncertainty remains explicit |
| `R2-A2` | Canonical dataset provider, release/version, lawful-use terms, stable locator/checksum evidence, and raw-to-split lineage requirements for all seven rows | R2-0 frozen input manifest | fresh independent evidence context | `gpt-5.6-sol`, `xhigh` | rights/release/lineage decision per row; no dataset downloaded |
| `R2-A3` | Source-bound benchmark center, exact config/seed/checkpoint/run identity, metric/cutoff/averaging, candidate/mask/tie, and evaluator evidence for all seven rows | R2-0 frozen input manifest | fresh independent evidence context | `gpt-5.6-sol`, `xhigh` | no center is joined across implementation/config/evaluator boundaries |
| `R2-G1` | Central verification, locator replay, deduplication, three-lane synthesis, blocker intersection, and at-most-one provisional materialization decision | A1+A2+A3 centrally validated | current central context | `gpt-5.6-sol`, `high` | `PROVISIONAL_SINGLE_CANDIDATE` or `NO_SELECTION`; never execution-ready |
| `R2-M0` | Exact user approval for any non-benchmark source/data acquisition or environment-building operation needed to materialize evidence | G1 provisional target | user + central control | n/a | approval receipt names exact target, paths, network/write scope, and commands |
| `R2-B1` | Implement and hash controller/resource wrapper; acquire and pin source only if M0 permits; close source tree, runtime, dependency and resource identities | G1 + applicable M0 approval | isolated implementation context/worktree | `gpt-5.6-sol`, `high` | P02–P07 evidence complete; no model run |
| `R2-B2` | Lawful dataset acquisition only if M0 permits; freeze raw bytes, terms snapshot, preprocessing argv/code, schemas/counts/IDs, processed bytes and split identity | G1 + applicable M0 approval | isolated data-materialization context/worktree | `gpt-5.6-sol`, `high` | P08–P09 evidence complete; v5 TEST remains sealed |
| `R2-B3` | Materialize model config, seed/checkpoint/sampler/candidate/tie contract, adapter, standalone evaluator, metric seam, parity fixtures, and exact log/output inventories | B1+B2 | isolated adapter/evaluator context/worktree | `gpt-5.6-sol`, `high` | P10–P12 evidence complete; no training/evaluation run |
| `R2-G2` | Central closed-schema validation and exact command-packet freeze; bind literal controller invocations and all hashes | B1+B2+B3 validated | current central context | `gpt-5.6-sol`, `high` | future packet P01–P13 resolved; commands materialized but unconfirmed and unauthorized |
| `E5-R2` | Read-only independent audit of the new frozen materialized packet | G2 central PASS | fresh independent audit context | `gpt-5.6-sol`, `high` | resolves P14 only on a full pass; auditor cannot repair packet |
| `R2-U` | User confirms the exact audited packet and central control emits separate authority receipt | E5-R2 PASS | user + central control | n/a | P15 resolved for one immutable packet only |
| `R2-D` | Official reproduction on the source dataset/protocol through the approved controller; no automatic retry | R2-U confirmation + authority | isolated execution context | `gpt-5.6-sol`, `high` | immutable receipts and official-center tolerance decision |
| `R2-G3` | Central receipt replay and accept/exclude decision | R2-D completed | current central context | `gpt-5.6-sol`, `high` | `OFFICIAL_REPRODUCTION_ACCEPTED` or exclusion with failure report |

A1, A2, and A3 may run concurrently because they receive the same immutable candidate registry but own disjoint evidence dimensions. B1 and B2 may run concurrently only after G1 and the applicable M0 approval. B3 is sequential because it consumes the exact source and dataset interfaces. G1, G2, E5-R2, R2-U, R2-D, and G3 are sequential gates.

## 5. Required evidence outputs

Proposed roots are reserved by the machine map; they are created only when the corresponding stage is dispatched.

### R2-A1 — repository lane

- `repo_evidence_register.json`;
- `paper_repo_config_binding.json`;
- `source_license_decisions.md`;
- `a1_handoff.json`.

Each row must carry primary-source locators, immutable revision, repository full commit, config/command identity, license decision, submodule/tree/link implications, evidence excerpts limited to locators, and unresolved fields. Repository popularity, stars, forks, or a runnable README are not readiness evidence.

### R2-A2 — dataset lane

- `dataset_evidence_register.json`;
- `provider_release_rights_matrix.json`;
- `lineage_requirement_map.json`;
- `a2_handoff.json`.

Each row must separate published provider evidence from locally acquired-byte evidence. Before M0, raw hashes may remain `NOT_ACQUIRED`; they must not be guessed from repository-bundled processed files. Rights ambiguity is dispositive and fail-closed.

### R2-A3 — benchmark/metric lane

- `result_center_register.json`;
- `center_config_seed_checkpoint_binding.json`;
- `metric_evaluator_contracts.json`;
- `a3_handoff.json`.

Every reported center must be bound to the same source implementation, dataset release/split, model/config, seed/run surface, checkpoint rule, candidate/masking/tie semantics, evaluator and metric aggregation. A paper center and a different implementation command cannot be joined.

### R2-G1 — central synthesis

- deduplicated source/dataset/metric identity registry;
- locator replay receipt;
- candidate blocker intersection matrix;
- provisional target decision with explicit alternatives and rejected joins;
- frozen manifest for materialization or a `NO_SELECTION` failure report.

### R2-B1/B2/B3 — materialization

- raw SHA-256 identities for every controller, wrapper, source, environment, lock, data, preprocessing, adapter, evaluator, fixture, config, expected log and expected output;
- literal paths under declared isolated roots;
- closed-schema receipts and exact file inventories;
- no null required binding;
- no training, benchmark evaluation, TEST access, or accepted result row.

### R2-G2 and E5-R2

G2 creates a new versioned selected bundle, reproduction plan, adapter/evaluator contract, reporting contract, exact command confirmation packet and handoff. The old Wave E `P13` does not carry forward: G2 must issue a new packet-specific P13.

E5-R2 receives only the frozen G2 manifest and read-only artifacts. It must independently replay hashes, schemas, candidate identity, rights/lineage, source-center binding, all P01–P13 closures, command literalness, path/resource controls, TEST denial, no-auto-retry and empirical truth.

## 6. Prerequisite ownership for the future packet

| Prerequisite | Closure owner |
|---|---|
| P01 candidate selection | G1 proposes; G2 resolves only after all material evidence passes |
| P02 controller identity | B1 |
| P03 resource-wrapper identity | B1 |
| P04 source identity | A1 + B1 |
| P05 source rights/submodule/tree lock | A1 + B1 |
| P06 interpreter/environment lock | B1 |
| P07 dependency/wheel lock | B1 |
| P08 provider/release/rights/raw hashes | A2 + B2 |
| P09 preprocessing lineage/argv/schema/counts | A2 + B2 |
| P10 model/config/seed/checkpoint/sampler/candidate/tie | A3 + B3 |
| P11 evaluator/adapter/metric identity | A3 + B3 |
| P12 exact log/output inventories | B1 + B2 + B3, consolidated by G2 |
| P13 new frozen central packet | G2 only; version-scoped |
| P14 independent audit pass | E5-R2 only |
| P15 explicit confirmation and authority | user + central control only |

At R2 start, all P01–P15 are unresolved for the future packet. The P13 value in Wave E applies only to that null-command packet.

## 7. Verification protocol

Every dispatched stage must be verified centrally before its downstream gate opens:

1. freeze a canonical-LF input manifest with SHA-256 and exact file count;
2. reject duplicate JSON keys, case-colliding keys/paths, undeclared files, path escape and mutable-only locators;
3. parse every JSON artifact with two independent parsers where the existing control protocol requires it;
4. replay primary source-of-record locators and immutable revisions;
5. deduplicate by full repository commit, dataset provider/release/raw hash, result-center identity and evaluator identity;
6. preserve row-level source/config/dataset/metric coupling; reject all cross-row joins;
7. validate exact output file set and hashes before import;
8. use fast-forward or exact-write-set import while preserving unrelated user changes;
9. record actual model, reasoning, context, commit and incident state in every dispatch/handoff;
10. fail closed on any mismatch, missing authority, ambiguity or unverifiable claim.

## 8. Stop conditions

Return to central control with no selection or no authorization when any of the following holds:

- no affirmative code-use basis at the pinned revision;
- dataset provider, release, rights or lawful acquisition cannot be established;
- raw-to-split lineage cannot be reproduced and hash-bound;
- the reported center cannot be tied to the exact implementation/config/seed/checkpoint/evaluator surface;
- candidate, mask, tie or metric semantics remain ambiguous;
- deterministic environment/dependency lock cannot be produced;
- any required material or command field remains null;
- any artifact/hash/schema/input/output inventory check fails;
- a fresh auditor requests revision;
- the user has not confirmed the exact post-audit packet or separate authority is absent.

No failed candidate, acquisition, install, preprocessing or run may trigger an automatic fallback, retry, hyperparameter change, resume or silent substitution.

## 9. Reporting boundary after official reproduction

An accepted official reproduction proves only that the selected source pipeline, adapter and environment reproduce the source-bound center within a preregistered tolerance. It does not show that the current hybrid model is superior.

Only after R2-G3 accepts official reproduction may Stage 1E prepare the harmonized v5 run. All baselines must then train and evaluate on the same frozen v5 split and shared evaluator. Official-source, harmonized-v5 and external-dataset results remain in separate tables; raw cross-dataset ranking is forbidden.

## 10. Immediate next gate

`R2_A1_A2_A3_DISPATCH_REQUIRES_FROZEN_R2_INPUT_MANIFEST`

The immediate next action is to generate the R2 evidence contract and frozen input manifest, then explicitly dispatch three fresh evidence tasks. It is not clone, download, install, preprocess, train, evaluate, or TEST access.
