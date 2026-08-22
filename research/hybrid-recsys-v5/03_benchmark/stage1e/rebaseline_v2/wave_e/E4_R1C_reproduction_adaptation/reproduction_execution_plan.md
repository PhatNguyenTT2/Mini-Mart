# E4-R1C Reproduction and Adaptation Plan

> Material Passport: `stage1e_rebaseline_v2_wave_e_e4_r1c_execution_plan` · status `UNVERIFIED`  
> Origin: `ars-codex:academic-research-suite/experiment-agent` · mode `central-synthesis/freeze-only` · date `2026-08-22`  
> Model: `gpt-5.6-sol`, reasoning `high`  
> Empirical state: `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, zero accepted rows, no command executed.

## 1. Current decision

The corrected E4 packet is structurally ready for a fresh independent E5-R1 audit, but it is not ready for reproduction execution.

- Candidate registry: 0 ready, 7 pending, 6 rejected.
- Minimum-resolution priority: LightGCN/Gowalla, priority only—not selected.
- Command packet: 10/10 command strings are null.
- Prerequisites after central freeze: 1 resolved (`P13_NEW_FROZEN_CENTRAL_PACKET`), 14 unresolved.
- Confirmation and authority: both false.
- TEST: sealed.

The next independent audit therefore checks whether the four E5 findings were honestly remediated and whether the packet remains fail-closed. It cannot authorize a benchmark run from the present packet.

## 2. Frozen evidence chain

The synthesis contract is `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r1c_central_synthesis_contract.md`, canonical-LF SHA-256 `192a49d4afec4e52d52515879ec28e4e58f8acf4f9038afe9ff0a3d06d7765c9`.

The direct input manifest is `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r1c_frozen_input_manifest.json`. It binds 20 direct inputs, including:

- the central lane-validation receipt;
- E5 findings and execution denial;
- all four R1A provenance/config artifacts;
- all four R1B command-control artifacts;
- the six immutable historical E4 artifacts;
- the one existing v5 benchmark specification.

The accepted R1A candidate registry is bound at `3d53f30e284edaefc02737fa7a7cad7326fb53cf2f3db0b218a93f3c1137fb32`. The accepted R1B mechanical-control design is bound at `6d9d00114fe1da84d8f6df312906ad82da408800523a66cc60423f38585dcdf7`; its command draft and receipt-schema hashes are `40b8a7e753c896cd19ec38c10764e8b073f158050e7452af3549292b85c5c41b` and `0d462872340130eeeadbf54eb41301c6e6675c2e7006384a85c36960ccf8fb32`.

## 3. Corrections now owned by the central packet

### 3.1 Source and configuration identity

`E5-F001` is corrected at the source-catalog and dependent-binding level:

- SimGCL record: `https://arxiv.org/abs/2112.08679`, revision `arXiv:2112.08679v4`;
- source-linked framework: QRec at full commit `a141bb37cb7706b2f53b2eed5843de3269f9f37f`;
- `https://arxiv.org/abs/2207.09037` is explicitly rejected as unrelated.

This correction does not close SimGCL's noninteractive argv, executed-config, dataset-byte, environment, seed, checkpoint, evaluator, or tie-policy gaps.

`E5-F002` is corrected everywhere in the central packet:

- path: `backend/docs/chatbot/seed-product/benchmark-spec-v5.json`;
- canonical-LF bytes: 2629;
- canonical-LF SHA-256: `acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d`.

The nonexistent historical path must never appear as an active binding.

### 3.2 Mechanical controls and ownership

`E5-F003` is replaced by a hash-bound control and schema design covering literal path containment, reparse and namespace rejection, GPU/resource identity, immutable source state, deterministic environment installation, lawful data lineage, generated preprocessing/run/evaluation receipts, standalone evaluation, final set equality, and no automatic retry.

The controls are not yet materialized because candidate-specific identities are absent. A null command is the only valid representation until those inputs are frozen.

`E5-F004` is corrected by phase ownership:

- E4 remediation owns evidence, controller/wrapper, locks, data lineage, adapter/evaluator implementation, exact argv, command materialization, and packet freeze.
- E5-R1 owns independent read-only audit only.
- The user may confirm only exact, hash-bound commands after a future audit pass.
- A future executor may run only a separately confirmed and authorized packet and may never retry automatically.

## 4. Evidence-resolution sequence before command materialization

No work below is authorized by this plan. Each item requires a later, explicitly scoped E4 remediation task and a new freeze.

### Gate A — candidate evidence closure

Resolve one candidate without weakening its source-bound center:

1. affirmative code-use decision at the pinned commit;
2. canonical dataset provider, release, lawful-use decision, acquired raw-byte manifest, and terms snapshot;
3. exact raw-to-processed-to-split transformation repository/commit, argv, configuration, schemas, counts, IDs, and artifact hashes;
4. source-bound model objective, noninteractive argv, configuration hash, seed identities, checkpoint rule and artifact, sampler, candidate universe, masking, and deterministic tie policy;
5. exact dependency/environment lock and compatible hardware declaration;
6. standalone evaluator/adapter identity, argv, metric/cutoff/averaging contract, and expected input/output inventories.

LightGCN/Gowalla is investigated first only because it has the strongest current command-seed-center link. Failure to close any field leaves it pending; it does not trigger automatic promotion of another row.

### Gate B — controller and resource implementation

After a candidate passes Gate A, an E4 implementation owner must create and freeze:

- one literal controller path and raw SHA-256;
- one literal resource-wrapper path and raw SHA-256;
- GPU physical index, UUID, exact model, exact total VRAM, free-VRAM threshold, process-tree enforcement, and telemetry behavior;
- create-once namespace and run identifiers with no symlink, junction, reparse, ADS, case-collision, or undeclared nesting escape;
- exact log, output, and receipt inventories.

The controller must reject any null, changed, or out-of-namespace binding before a write.

### Gate C — environment and data lineage materialization

An E4 owner must freeze an interpreter, environment builder, dependency lock, wheelhouse manifest, installer, and compatibility declaration. Installation must be offline, hash-required, deterministic, and receipt-producing.

The same packet must freeze provider/release/rights evidence, raw artifact hashes, lawful acquisition receipt, preprocessing code and argv, schema/count assertions, processed artifact hashes, split identity/hash, and candidate/sampler/tie semantics. Repository-bundled files or an E5 label cannot substitute for lineage.

### Gate D — model and evaluator materialization

An E4 owner must freeze exact model and evaluator/adapter argv, file hashes, seed, checkpoint rule, timeout, expected files, and metric semantics. Source-integrated printed metrics are not enough for harmonized v5 evaluation. The v5 seam requires a standalone receipt bound to the corrected benchmark-specification path and hash.

### Gate E — exact command freeze

Only when Gates A-D pass may E4 replace the ten null command strings with literal invocations of the exact hash-bound controller. Direct ad hoc invocation of source tools is forbidden. Every command retains:

- exact ordinal and phase;
- literal shell, working directory, argv, timeout, and network/write policy;
- required prerequisite IDs and receipt schema;
- `user_confirmation_required=true`;
- `confirmed=false` until explicit post-audit user action;
- `execution_authorized=false` until a separate authority receipt;
- `retry_policy=NO_AUTO_RETRY`.

Materialization creates a new packet version and invalidates this null-command version for execution.

## 5. Intended execution sequence after a future authorization

This section defines order only; it does not authorize an attempt.

1. `000 preflight` — validate exact packet, authority, root, namespace marker, controller/wrapper hashes, GPU/resource envelope, and TEST seal.
2. `010 source acquire` — create an absent target from the one allowed remote and emit an acquisition receipt.
3. `020 source checkout` — detach at the exact full commit and close submodule state.
4. `030 source verify` — reject dirty/untracked drift; replay remote, commit, submodules, links, and deterministic source-tree hash.
5. `040 environment create` — create an absent isolated environment with exact builder/interpreter identity.
6. `050 dependency install` — install offline from the exact lock and wheel set, then hash the resulting environment.
7. `060 preprocess` — replay lawful raw acquisition and exact raw-to-processed-to-split lineage; emit a generated preprocessing receipt.
8. `070 run` — invoke the model only through the resource wrapper; enforce process-alive telemetry, timeout, immutable logs/outputs, and no retry.
9. `080 evaluate` — run the standalone, hash-bound evaluator/adapter under the appropriate source or v5 metric seam while TEST remains sealed unless a separately preregistered gate opens it.
10. `090 finalize` — require exact receipt/log/output set equality, dual JSON parsing, closed-schema validation, collision checks, hash replay, and an atomic final manifest.

Failure at any ordinal blocks every later ordinal. A second attempt needs a new explicit packet and user decision; there is no automatic retry, parameter change, resume, or silent substitution.

## 6. Scope separation and reporting

The following outputs may never be merged into one raw leaderboard:

- official-source reproduction on the source dataset/evaluator;
- harmonized v5 metrics on the frozen v5 seam;
- external-validation results on a separately eligible dataset/protocol;
- framework-only MovieLens reference assessments.

Official centers are reproduction targets within their own row. They cannot establish superiority for the current v5 method. Missing or ineligible rows remain visibly missing; they are not zero-filled, imputed, or ranked.

## 7. Fresh E5-R1 audit gate

After the six Wave E outputs pass central validation and are frozen, dispatch a fresh task using `gpt-5.6-sol` with reasoning `xhigh`. The auditor must receive the immutable R1C manifest and output hashes, inspect all four finding dispositions, replay the 13-row/five-join counts and ten-command/fifteen-prerequisite ledger, and preserve the empirical denial state.

The audit may return a remediation-quality pass while still denying execution. It must not emit `PASS_EXECUTION_AUTHORIZED` while there is no ready candidate, any material binding is null, any command is null, user confirmation is false, or independent authority is absent.

## 8. Current verdict

`COMPLETE_CORRECTED_FAIL_CLOSED_READY_FOR_E5_R1_AUDIT`

This verdict is about packet integrity and audit readiness only. The benchmark remains not run, all project benchmark numbers remain invalid for the paper, and Stage 1E remains blocked from execution.

