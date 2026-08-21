# E4-R1B mechanical command/control specification

## Material Passport

- `origin_skill`: `ars-codex:academic-research-suite`
- `origin_mode`: `experiment-agent/plan/remediation-only`
- `origin_date`: `2026-08-22`
- `verification_status`: `UNVERIFIED`
- `version_label`: `stage1e_rebaseline_v2_wave_d_E4_R1B_controls_v1`

This artifact is a control proposal, not an execution packet, implementation, confirmation, authorization, or result. The immutable lane truth is `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, `execution_authorized=false`, and `confirmed=false`.

## Scope and frozen entry gate

The lane verified the frozen manifest at `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r1_frozen_input_manifest.json` before analysis. Its canonical-LF SHA-256 is `d0a5db377c36f7109b4b56089ac024bb8ddcd4b5badc5aeb464969aa2e13d817`. All 17 listed files matched their declared canonical-LF byte counts and hashes. The contract matched `b51c41a931ef88a1fcc356394600b3c2fcdafad68b5599477c9a894040d82538`. All 11 JSON documents in the entry set, including the manifest, passed a duplicate/case-collision-rejecting standard JSON parse and PowerShell `ConvertFrom-Json`.

All source material was treated as untrusted data. No repository was cloned or fetched, no dataset was accessed or downloaded, no package or environment was installed or created, no E4 command was executed, no smoke/training/evaluation/benchmark run occurred, and TEST remained sealed.

E4-R1B owns the mechanical-control proposal for `E5-F003` and the phase-ownership correction for `E5-F004`. It does not select or promote a candidate. Candidate, repository, dependency, dataset, preprocessing, model-argv, checkpoint, and evaluator values that are not frozen by the lane inputs remain null blocking prerequisites in the companion draft.

## Audit of all ten existing command records

| Existing command | Audit result | Exact defect or retained boundary | Replacement disposition |
|---|---|---|---|
| `E4-LGCN-000-PREFLIGHT` | `CONTRADICTED` | It checks only a literal root, marker existence, and whether `nvidia-smi` returns. It does not validate marker contents, resolved containment, reparse points, namespace collisions, GPU identity/capacity/free VRAM, or wrapper path/hash. It emits no declared receipt. | Replace with a controller-owned preflight that performs all checks before any write and atomically emits `000_preflight_receipt.json`; keep command null until the controller is hash-bound. |
| `E4-LGCN-010-CLONE` | `CONTRADICTED` | Its working directory is not created by an earlier command. Redirect, remote-identity, create-once target, containment, and receipt claims are not implemented. | Replace with exclusive namespace initialization plus source acquisition through the hash-bound controller. Exact URL/commit remain blocking and E4-owned. |
| `E4-LGCN-020-CHECKOUT` | `PARTIAL` | The detached full SHA is explicit, but submodule ambiguity, reparse/symlink escape, and out-of-namespace mutation are not rejected or receipted. | Require an exact commit, explicit submodule policy/state, containment checks before/after checkout, and a source-phase receipt. |
| `E4-LGCN-030-VERIFY-SOURCE` | `CONTRADICTED` | It asserts `HEAD` but only prints dirty-worktree and submodule output. It does not reject either condition or bind a canonical source-tree hash and remote identity. | Require empty porcelain output, exact remote URL, exact full commit, closed submodule state, no forbidden links, canonical source-tree hash, and atomic receipt. |
| `E4-LGCN-040-CREATE-ENV` | `CONFIRMED_FAIL_CLOSED` | Null command correctly refuses to invent an interpreter, but the text incorrectly assigns resolution to E5. | Keep null until E4 freezes interpreter and environment-builder identities. E4-R1 owns the runtime lock; future E5 is audit-only. |
| `E4-LGCN-050-INSTALL` | `PARTIAL` | Offline `--no-index --require-hashes` is sound, but the interpreter, lock, wheelhouse, and their hashes are absent; deterministic installation and receipt emission are not implemented. | Keep null until E4 freezes the interpreter, dependency lock, wheel manifest, installer behavior, and environment receipt contract. |
| `E4-LGCN-060-PREPROCESS-GATE` | `CONTRADICTED` | Property presence and an `E5` label do not validate types, hashes, rights, source binding, lineage, schema/counts, duplicate/case-colliding keys, or transformation semantics. It creates no preprocessing receipt. | E4 must supply or generate the raw-to-processed-to-split receipt using exact inputs/code/argv; the controller validates and binds it. E5 never supplies or verifies-by-label. |
| `E4-LGCN-070-TRAIN-AND-INTEGRATED-EVALUATE` | `PARTIAL` | It names GPU/resource arguments and an exact source argv, but the wrapper is absent/unhashed, process/telemetry enforcement is unproved, checkpoint/sampler/candidate/tie bindings are incomplete, and no declared run receipt is emitted. | Keep null until all run bindings and wrapper hash exist. A materialized command must run only through the wrapper and atomically emit `070_training_receipt.json`. |
| `E4-LGCN-080-STANDALONE-EVALUATE` | `CONFIRMED_FAIL_CLOSED` | Null command correctly avoids inventing a source evaluation mode. It does not satisfy the replacement requirement for a separately hash-bound evaluator and evaluation receipt. | Keep null until E4 freezes a standalone evaluator/validator identity, exact argv, metric contract, inputs, and TEST-seal policy. Source-integrated output never substitutes for the standalone receipt. |
| `E4-LGCN-090-FINALIZE-RECEIPTS` | `CONTRADICTED` | It lists and hashes existing files but does not enforce required-file set equality, JSON schema validity, duplicate/case-collision rejection, canonical text hashing, candidate-specific output equality, or atomic manifest emission. | Replace with a controller finalizer that validates exact receipt/log/output sets and emits `090_final_manifest_receipt.json`. |

Every existing record was also checked for shell/cwd, revision/source binding, read/write/network declarations, timeout, RTX 3060 resource envelope, namespace behavior, credentials, `NO_AUTO_RETRY`, confirmation state, authorization state, and explicit null semantics. No credential literal was found. All ten were unconfirmed, unauthorized, and marked no-auto-retry; those correct denial fields are preserved.

## Enforcement architecture

The replacement design has three layers:

1. **Immutable packet.** A future E4-R1C packet must be strict UTF-8 JSON with a canonical-LF SHA-256, closed schemas, exactly ten ordered command records, and no duplicate or case-colliding keys. This lane's draft is deliberately non-executable: all ten `command` values are null.
2. **Hash-bound controller and resource wrapper.** Every materialized command must invoke one controller at a literal absolute path and verified SHA-256. Training/evaluation must additionally invoke the resource wrapper at its literal path and verified SHA-256. The controller and wrapper identities are currently null blockers. Direct execution of a source interpreter, Git, installer, preprocessor, model, or evaluator outside the controller is forbidden.
3. **Atomic receipts.** The controller writes a receipt to a same-volume temporary regular file, flushes it, strict-parses and validates it, rejects duplicate/case-colliding keys, computes canonical hashes, then atomically renames it to its create-once final name. A pre-existing final receipt, output, log, run marker, or run namespace is a hard failure; nothing is overwritten.

The controller must refuse command materialization or launch unless packet validation, all preceding receipt validations, a future independent E5-R1 pass receipt, and a separate explicit user-confirmation/authorization receipt all hash-bind the same frozen packet. The present packet has `confirmed=false` and `execution_authorized=false`, so refusal is the only valid behavior.

## Global controls

### Path and namespace controls

- The proposed literal runtime root is `C:\recsys_stage1e_runtime\e4_v1`. The value is inherited from the frozen E4 packet; any future change requires a new packet and hash.
- Before any write, canonicalize with the Windows final-path API after opening the existing parent without following an unverified reparse target. Case-folded final paths must remain strictly beneath the literal runtime root and must not equal it unless the command is the exclusive root initializer.
- Inspect every existing component from drive root to target. Any symlink, junction, mount point, or other `FILE_ATTRIBUTE_REPARSE_POINT` in an ancestor or target is a hard failure. Recheck after each component is exclusively created to close check/create races.
- The controller derives a closed namespace set for `control`, `locks`, `wheelhouse`, `repos`, `envs`, `data_raw`, `data_processed`, `logs`, `outputs`, and `receipts`. After final-path and case normalization, no two namespaces may be equal and no namespace may contain another except the explicitly declared parent-child edges in the packet. Official-reproduction, harmonized-v5, and external-validation run roots are siblings and may never point into one another.
- `namespace_initialization_receipt.json` must be a regular create-once file containing the literal root, resolved final root, packet hash, namespace graph hash, creator/controller hash, created-at UTC, and a random-free packet-declared namespace ID. Marker existence alone never passes.
- `run_id` must be assigned and frozen by a future E4 packet before confirmation. The run directory is exclusively created once, contains `run_initialization_receipt.json` binding packet/candidate/config/data/environment/controller hashes, and is never reused. The current `run_id=null` is blocking.
- Every cwd, input, output, log, receipt, lock, wheel, repository, dataset, checkpoint, prediction, and manifest path must be an absolute literal carried by the packet or deterministically derived from a frozen packet field. Environment-variable expansion, globs, search-path resolution, relative paths, `..`, alternate data streams, device paths, and 8.3 aliases are forbidden.

### GPU and host-resource controls

- The planned device is physical GPU index `0`, exact model string `NVIDIA GeForce RTX 3060 Laptop GPU`, total memory `6144 MiB`, pre-launch free memory at least `5120 MiB`, and per-job ceiling `5120 MiB`. These are proposal values inherited from the frozen audit, not a fresh hardware observation.
- Preflight must parse structured `nvidia-smi` output and assert exactly one row for the requested physical index, exact normalized model identity, exact total memory, and free-memory threshold. Parse failure, multiple matches, MIG/virtualization ambiguity, or index remapping is fatal.
- The wrapper must set and verify the physical-device binding, launch one process tree through a Windows Job Object or equivalent, cap the tree at four logical CPU workers and `12288 MiB` host RAM, and prohibit a second packet-owned GPU process.
- Telemetry is append-only every 10 seconds and includes UTC, controller PID, complete child PID set, physical GPU UUID/index/model, per-PID GPU memory, GPU utilization, process-tree CPU, and process-tree resident/commit memory. The wrapper terminates the process tree and emits `INFRASTRUCTURE_FAILURE` when telemetry is absent for 60 seconds, a non-packet process appears in the controlled tree, the GPU binding changes, or observed job VRAM exceeds `5120 MiB`.
- Wrapper absence, raw-byte SHA-256 mismatch, signature/policy failure, inability to establish a Job Object, inability to enumerate the PID tree, or inability to prove telemetry ownership stops before model launch. Monitoring is not evidence of an enforceable limit unless these checks pass.

### Source-state controls

- A future packet must freeze one exact repository URL, full 40-hex commit, acquisition mode, expected remote URL after redirect normalization, submodule policy and per-submodule full commit, code-rights decision, and source-tree hash algorithm/value. R1B leaves these null because candidate promotion belongs to E4-R1A/E4-R1C.
- Source acquisition uses an exclusively absent target. The controller records transport start/end, tool version, resolved remote, redirect chain, network state, stdout/stderr hashes, exit code, and target final path.
- Checkout must be detached at the exact full commit. Verification requires `HEAD` equality, empty tracked/untracked porcelain output under the packet's policy, exact remote equality, closed submodule equality, no forbidden reparse/symlink entries, and a deterministic manifest/tree hash over path/type/mode/content. Printing state never counts as enforcement.
- Any source mutation after the source receipt is stale-by-definition and blocks every downstream stage.

### Environment and dependency controls

- A future E4 packet must freeze the environment-builder executable path/hash, interpreter distribution/version/path/hash, architecture, dependency-lock path/hash, wheelhouse manifest path/hash, every wheel filename/hash, installer version, CUDA/runtime compatibility declaration, and network state. All are currently explicit blockers.
- Environment creation must use an exclusively absent path and must not search `PATH`. Installation is offline, hash-required, build-from-source forbidden unless separately frozen, and package substitution/version relaxation forbidden.
- The environment receipt records interpreter and installer identities, the exact lock and wheel set, install argv, resolved installed distribution names/versions/file hashes, import checks, CUDA/framework identity, network disabled state, and an environment aggregate hash. A package-list printout without these bindings fails.

### Dataset lineage and preprocessing controls

- A future E4 packet must freeze provider URL, release/version, access/rights decision and terms snapshot hash, exact raw artifact names and hashes, lawful acquisition receipt, transformation repository/code hash, exact preprocessing argv/config, schema version, expected raw/processed/split counts, processed artifact hashes, and split identity/hash.
- Data rights and code license are separate gates. Public availability never implies reuse rights. An unknown right, provider release, raw hash, transformation, or count remains blocking.
- Preprocessing is an E4-owned operation/receipt. It must execute only from frozen raw bytes through frozen code/argv into an exclusively absent processed namespace. It must record raw-to-processed-to-split lineage, arguments, code identity, deterministic settings, schemas/counts, row/id integrity, split boundaries, candidate/sampler/tie semantics when applicable, and output hashes.
- A pre-existing receipt, mere property presence, free-form `VERIFIED_BY_E5` label, repository-bundled processed pack, or downstream auditor assertion cannot satisfy lineage.

### Run and evaluation controls

- The run record must freeze exact interpreter/model argv as an ordered array, canonical config bytes/hash, candidate row, seed, checkpoint rule/cadence, sampler, negative sampling, candidate universe, tie policy, timeout, log/output paths, and success/failure predicates. Null in any required identity blocks launch.
- Training runs only through the verified resource wrapper. The wrapper records process-alive checks, exit status, timeout, OOM/resource/telemetry events, checkpoint candidates and selected checkpoint hash, immutable logs, config dump, and artifact hashes. Every anomaly is fail-closed for this benchmark packet; no parameter is silently changed.
- A separately hash-bound evaluator/validator is mandatory. It must bind exact executable/source hash and argv, the frozen v5 specification at `backend/docs/chatbot/seed-product/benchmark-spec-v5.json` with canonical-LF SHA-256 `acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d`, input prediction/checkpoint hashes, metric formulas/cutoffs/averaging units, full candidate/mask/tie rules, and output schema. A source-integrated metric printout can be an input but is never the standalone evaluation receipt.
- TEST access is denied in this draft and in all preprocessing/training/tuning/validation commands. The controller must compare requested data paths and split IDs against the frozen split receipt and reject the TEST path/ID before opening it. Any TEST-access attempt emits a failed receipt with `TEST_SET_OPENED` remaining `NO` only when the open was prevented; if an open cannot be disproved, the state becomes an explicit blocking incident rather than a pass. A separate newly frozen final-evaluation packet is required for any future TEST gate.

### Receipts and final manifest

- Every command has exactly one create-once JSON receipt, including failed or unavailable-at-runtime attempts. Receipt schemas are closed and carried in `receipt_schema_bundle.json`.
- All JSON is strict UTF-8 and must pass two independent parsers. A streaming/token pass rejects duplicate keys and Unicode case-fold-colliding keys at every object depth before semantic validation. JSON schema/property/type/enum/format validation follows; malformed receipts never become evidence.
- Text hashes use strict UTF-8 decode, CRLF-to-LF normalization, then SHA-256. Binary hashes use exact bytes. Artifact paths are normalized UTF-8 forward-slash relative names sorted by ordinal byte order.
- The base receipt file set is exactly the ten filenames frozen in the draft. Candidate-specific log and output file sets must be non-null and frozen before command materialization. Finalization compares actual regular-file sets to all three expected sets with equality, not subset containment; rejects extras, missing files, reparse points, case collisions, and duplicates; revalidates every receipt; recomputes every hash; then atomically emits `090_final_manifest_receipt.json`.
- The final manifest lists and hashes the other nine command receipts plus the exact log/output inventories. It does not self-hash inside itself. Its canonical-LF hash is computed by the receiving validator and reported out of band, avoiding a self-reference fiction.

### Confirmation and no-auto-retry controls

- Packet and every command carry `user_confirmation_required=true`, `confirmed=false`, and `execution_authorized=false`. Those values are constants in this lane output.
- The controller must refuse all current commands because every `command` is null and because confirmation/authorization are false. A future E4-R1C packet remains unconfirmed and unauthorized until it passes a fresh independent E5-R1 audit and the user explicitly confirms the exact frozen packet.
- Future execution authority must be a separate create-once receipt binding the exact packet hash, future E5-R1 pass receipt hash, exact ten command strings/argv, user confirmation event ID/hash, scope, and expiry. E5 does not create this receipt and an E5 pass alone is not authorization.
- `retry_policy=NO_AUTO_RETRY` and `retry_count=0` are mandatory. Timeout, nonzero exit, hash/schema/path/resource/source/data/config/evaluator mismatch, TEST attempt, or missing receipt stops the packet. A manual retry requires a newly frozen packet and new `run_id`; the failed run and receipts remain immutable.

## Ten-stage control and receipt mapping

| Order / proposed ID | Objective | Mechanical enforcement | Hard-failure semantics | Receipt | Owner |
|---|---|---|---|---|---|
| `000 / E4-R1B-000-PREFLIGHT` | Prove packet, denial state, literal root, namespace graph, controller/wrapper, hardware, resources, and TEST seal before writes. | Strict packet parse; hash checks; final-path/reparse/collision checks; exact GPU assertions; wrapper/controller path/hash verification; confirmation/authorization refusal. | Any unknown/mismatch/null required binding stops before writes. | `000_preflight_receipt.json` / `preflight_receipt` | E4-R1 designs/fills; future E5-R1 audits. |
| `010 / E4-R1B-010-SOURCE-ACQUIRE` | Exclusively create source namespace and acquire the exact remote. | Controller-only network scope; absent-target exclusive creation; redirect/remote verification; containment checks; transport receipt. | Existing target, wrong remote/redirect, network-policy breach, or nonzero/timeout stops. | `010_source_acquisition_receipt.json` / `source_receipt` | E4-R1. |
| `020 / E4-R1B-020-SOURCE-CHECKOUT` | Materialize exact detached source/submodule state. | Full-commit equality; closed submodule map; post-write containment/reparse scan. | Missing/wrong commit, submodule ambiguity, link escape, or mutation stops. | `020_source_checkout_receipt.json` / `source_receipt` | E4-R1. |
| `030 / E4-R1B-030-SOURCE-VERIFY` | Freeze clean source identity. | Exact URL/commit; empty porcelain; deterministic tree hash; tool versions; no forbidden links. | Any dirty/untracked state under policy, remote/submodule/tree mismatch, or parse failure stops. | `030_source_verification_receipt.json` / `source_receipt` | E4-R1. |
| `040 / E4-R1B-040-ENVIRONMENT-CREATE` | Create isolated interpreter environment. | Hash-bound builder/interpreter; absent-target exclusive creation; no PATH search; network policy. | Unknown/mismatched interpreter/builder, existing env, network breach, or nonzero/timeout stops. | `040_environment_creation_receipt.json` / `environment_receipt` | E4-R1; never E5. |
| `050 / E4-R1B-050-DEPENDENCY-INSTALL` | Reproduce exact dependency set offline. | Lock/wheel equality and hashes; offline hash-required install; installed-file inventory/environment hash. | Missing/extra wheel, hash mismatch, resolver drift, source build, substitution, network attempt, or import failure stops. | `050_environment_install_receipt.json` / `environment_receipt` | E4-R1; never E5. |
| `060 / E4-R1B-060-PREPROCESS` | Generate and validate raw-to-processed-to-split lineage. | Rights/provider/raw checks; frozen transformation code/argv; exclusive outputs; schema/count/id/split checks; atomic receipt. | Any unknown rights/identity, missing raw hash, lineage/schema/count/split mismatch, extra output, or TEST access stops. | `060_preprocessing_receipt.json` / `preprocessing_receipt` | E4-R1; future E5 audits only. |
| `070 / E4-R1B-070-RUN` | Run exact model/config/seed once under the resource envelope. | Wrapper-only invocation; process-tree/telemetry monitoring; exact run/config/checkpoint/sampler/candidate/tie locks; immutable artifacts. | Timeout, nonzero/OOM, telemetry/resource breach, checkpoint ambiguity, missing artifact, or config drift stops with no retry. | `070_training_receipt.json` / `training_receipt` | E4-R1 designs packet; later executor runs only after gates. |
| `080 / E4-R1B-080-EVALUATE` | Apply separately hash-bound evaluator/validator without opening TEST. | Exact evaluator path/hash/argv; v5 spec path/hash; metric/cutoff/averaging and candidate/mask/tie checks; input/output hashes. | Evaluator/spec/input drift, incomplete candidate coverage, metric/schema ambiguity, TEST attempt, timeout, or nonzero exit stops. | `080_evaluation_receipt.json` / `evaluation_receipt` | E4-R1 owns evaluator/adapter argv; future E5 audits. |
| `090 / E4-R1B-090-FINALIZE` | Prove exact complete receipt/log/output inventory and emit manifest. | Independent strict parse/schema/hash replay; exact set equality; collision/reparse rejection; atomic create-once manifest. | Missing/extra/invalid/stale/colliding artifact or any hash mismatch prevents manifest emission and acceptance. | `090_final_manifest_receipt.json` / `final_manifest_receipt` | E4-R1 control; future E5 audits frozen output. |

## Phase ownership and gate sequence

1. **E4-R1A** supplies only evidence/source/candidate-readiness proposals under its lane contract.
2. **E4-R1B** supplies this mechanical-control proposal, command draft, and receipt schemas. It does not promote a candidate or materialize executable strings.
3. **E4-R1C** is the only current stage allowed to synthesize a central replacement E4 packet. All runtime/dependency locks, preprocessing receipt design and production plan, source/adapter/evaluator argv, command strings, and packet hashes remain E4 responsibilities.
4. A newly frozen central E4 packet is dispatched to a **fresh independent E5-R1**. E5-R1 performs read-only audit; it never supplies a runtime lock, dataset receipt, preprocessing output, adapter argv, command, packet, confirmation, or execution authority.
5. Only after a future E5-R1 pass may the user be asked to confirm the exact frozen commands. A separate central authority decision may then issue a hash-bound execution receipt. Neither this lane nor E5 authorizes execution.
6. An executor may run only the exact confirmed/authorized packet. Execution evidence then returns to an independent audit gate. Official reproduction acceptance must precede v5 adaptation, harmonized v5 comparison, and separate external validation.

## Finding dispositions and residual blockers

- `E5-F003`: `REMEDIATED_AT_DESIGN_SCOPE_BLOCKED_PENDING_MATERIALIZATION`. The proposal maps every contradicted/partial command to an enforceable controller, resource, path, source, lineage, run, evaluation, and receipt rule. It does not claim the missing controller, wrapper, bindings, schemas-as-code, or command strings exist.
- `E5-F004`: `REMEDIATED_AT_OWNERSHIP_CONTRACT_SCOPE`. Runtime/dependency locks, preprocessing, adapter/evaluator argv, and replacement packet construction are explicitly E4-R1/E4-R1C work. Future E5 is audit-only.

Blocking prerequisites remain: candidate selection; exact repository/license/commit/submodule/tree identity; controller and resource-wrapper path/hash/implementation proof; interpreter/environment/dependency/wheel identities; lawful dataset provider/release/rights/raw hashes; acquisition and raw-to-processed-to-split lineage; exact preprocessing code/argv/schema/counts; exact model/config/seed/checkpoint/sampler/candidate/tie bindings; standalone evaluator/adapter identity/hash/argv and metric implementation proof; candidate-specific expected log/output sets; a central frozen packet; a fresh independent E5-R1 pass; and explicit user confirmation plus separate authorization. No blocker is inferred closed.

Lane verdict: `R1B_COMPLETE_WITH_BLOCKING_PREREQUISITES`.
