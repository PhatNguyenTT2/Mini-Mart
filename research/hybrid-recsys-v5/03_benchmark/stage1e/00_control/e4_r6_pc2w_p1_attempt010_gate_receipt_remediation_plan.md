# Stage 1E / E4-R6-PC2W-P1 Attempt-010 gate-receipt remediation plan

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-26T12:31:08.6603299+07:00
- Verification Status: UNVERIFIED
- Version Label: stage1e_e4_r6_pc2w_p1_attempt010_gate_receipt_remediation_plan_v1
- Upstream Dependencies:
  - stage1e_e4_r6_pc2w_p1_attempt010_admission_observation_contract_v1
  - stage1e_e4_r6_pc2w_p1_attempt010_central_static_validation_receipt_v1
  - stage1e_e4_r6_pc2w_p1_attempt010_fresh_independent_audit_receipt_v1
  - stage1e_e4_r6_pc2w_p1_attempt009_pre_runtime_failure_receipt_v1
- Repro Lock: null
- Experiment Intake Declaration:
  - status: no_experiments_declared
  - declared_at: 2026-08-26T12:31:08.6603299+07:00
  - declared_by: scholar

## 1. Plan verdict and non-execution boundary

`PLAN_READY`

The remediation MUST be issued as a new immutable **Attempt-011**, not as an in-place edit or revision of Attempt-010. Attempt-010 already has a packet commit, a central static-validation receipt, and a fresh independent audit receipt whose terminal verdict is `HANDOFF_INCOMPLETE`. Rewriting any of those artifacts would destroy the evidence chain that explains why no runtime observation occurred. Attempt-011 MUST cite Attempt-010 as failed upstream evidence and use a new stage ID, schemas, verdicts, confirmation token, packet commit, receipts, and output root.

This document is planning evidence only. It does not authorize importing or invoking an admission runner, querying the host, Docker or WSL, starting or stopping Docker Desktop, materializing data or repositories, preprocessing, training, evaluation, benchmarking, opening the test set, or retrying any prior attempt.

## 2. Verified start state and evidence baseline

The plan was prepared from a clean detached worktree whose `HEAD` and local `refs/heads/main` both resolved to:

- audited main commit: `04e4f865d523230cdd57f5bcb87543b5034dcff1`
- parent: `c404b8be82ef67ababa7100729fc4a8cea3e53ea`
- subject: `audit(stage1e): record Attempt-010 handoff incomplete`
- start write set: empty

The local object database also contains sibling commit `5ab654664219ba58864724dc13f7e20271ecaeac`, but `main` selects `04e4f865d523230cdd57f5bcb87543b5034dcff1`; both sibling commits contain the same fresh-audit receipt blob. No sibling ref is used as authority by this plan.

The locked Attempt-010 chain is:

| Evidence | Immutable binding |
|---|---|
| path-reservation parent | `fe9f334e555639ed61781388421e8f8f7c228b46` |
| dormant packet commit | `b7f8f9de028017b14fcc4357d34f3b03b705884d` |
| central receipt commit | `c404b8be82ef67ababa7100729fc4a8cea3e53ea` |
| central receipt raw-Git-blob SHA-256 | `d3dcd2f7624b7350db21eb6f7c10f863c631d829e23d577e7137e2d97b9f994d` |
| fresh-audit receipt commit on `main` | `04e4f865d523230cdd57f5bcb87543b5034dcff1` |
| fresh-audit receipt raw-Git-blob SHA-256 | `cb0eacbbb96fd4ca7832eaf7c18aa9ee6886891e19cadbcb13336058de45163b` |
| fresh-audit verdict | `HANDOFF_INCOMPLETE` |
| runtime commands executed | `false` |
| truth state | `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0` |

Attempt-010 packet artifact bindings from the central receipt are:

| Path suffix | Raw Git blob bytes | Raw Git blob SHA-256 |
|---|---:|---|
| `e4_r6_pc2w_p1_attempt010_admission_observation_contract.json` | 6420 | `a04896393389631b411c416e40ec0f7f1777c0b6fe1e1fb9a058681f2f4cbd66` |
| `e4_r6_pc2w_p1_attempt010_execution_authorization.json` | 3180 | `c156fbfc959f14e4247bb5ac370b47e315a7679940ed838912968be124affd44` |
| `execute_e4_r6_pc2w_p1_attempt010_admission_observation.py` | 9023 | `437fffce0c0a8b459920ae12808692d37c07b1e63dc4704d2efdc6306ffe76f9` |
| `validate_e4_r6_pc2w_p1_attempt010_static_packet.py` | 9013 | `bff260bc23d4bb52459d3ed1cb56c3572cf269991c1db50d7c3d96c337f9da64` |

## 3. Root cause

The defect is a composition error at the Attempt-009-to-Attempt-010 adapter seam, not a bad Attempt-010 receipt.

1. `execute_e4_r6_pc2w_p1_attempt010_admission_observation.py` rebinds the central and fresh-audit schema and verdict globals to Attempt-010 values.
2. It then calls `previous.configure_legacy_runner()` from Attempt-009 without replacing `previous._validate_gate_receipts`.
3. Attempt-009 installs that function as `legacy.validate_gate_receipts`.
4. The installed predicate reads the rebound schema/verdict globals but independently contains two literal checks for `E4-R6-PC2W-P1-ATTEMPT009`, one for the central receipt and one for the fresh-audit receipt.
5. Therefore a correctly formed Attempt-010 receipt passes schema and verdict binding but necessarily fails stage binding before output-root creation and before the first runtime command.

The existing tests covered the Attempt-010 `python -B` command interface and retained runtime compatibility but never exercised the gate-receipt stage binding. The independent audit correctly classified this as a major `INHERITED_GATE_RECEIPT_STAGE_BINDING_MISMATCH` and refused exact-command confirmation.

## 4. Immutable decision: publish Attempt-011

Attempt-010 MUST remain permanently non-runnable under its recorded receipt chain. The next implementation MUST:

- use stage ID `E4-R6-PC2W-P1-ATTEMPT011`;
- preserve every Attempt-009 and Attempt-010 source, contract, test, receipt, output path, commit, and verdict byte-for-byte;
- reuse the already validated Attempt-009 runtime compatibility seam and Attempt-010 command-interface seam only as frozen dependencies;
- replace only the gate-receipt validation seam with a new attempt-agnostic interface;
- allocate a never-before-used output root at `research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_at/E4_R6PC2W_P1_attempt011_admission_observation`;
- require a new central receipt, a new fresh audit, and a later user-owned exact-command confirmation; and
- permit at most one runtime process invocation and zero automatic retry or fallback.

An Attempt-010 “revision 2” is rejected because its existing stage identity and receipts already describe a complete audited failure. A new revision under the same attempt number would make consumers decide which Attempt-010 receipt family is authoritative and would weaken immutable provenance.

## 5. Exact future file and change boundary

All paths below are under `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/` unless an absolute subtree is shown. No file that exists before `R0` may be edited; the only later modifications are the four explicitly reserved Attempt-011 placeholders in `R1`.

### 5.1 Support-and-reservation commit `R0`

Starting from a clean worktree at the then-current `main` with this plan commit as an ancestor, create one commit whose exact delta is seven added files:

1. `e4_r6_pc2w_p1_gate_receipt_binding.py` — complete attempt-agnostic strict receipt-binding implementation.
2. `e4_r6_pc2w_p1_gate_receipt_binding_contract.json` — versioned interface, invariant, and stable-error-code contract.
3. `test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py` — the complete synthetic test matrix in Section 7.
4. `e4_r6_pc2w_p1_attempt011_admission_observation_contract.json` — reserved, explicitly dormant placeholder.
5. `e4_r6_pc2w_p1_attempt011_execution_authorization.json` — reserved, explicitly dormant placeholder.
6. `execute_e4_r6_pc2w_p1_attempt011_admission_observation.py` — reserved, non-executable placeholder with no imports or side effects.
7. `validate_e4_r6_pc2w_p1_attempt011_static_packet.py` — reserved, non-executable placeholder with no imports or side effects.

The four placeholders MUST NOT be invoked, imported, or merged independently. `R0` becomes the exact `PACKET_PARENT` and freezes the raw Git blob SHA-256 of the generic binding module, its contract, and the test file.

### 5.2 Dormant packet implementation commit `R1`

From clean `R0`, create one commit whose exact delta is four `M` entries and nothing else:

1. `e4_r6_pc2w_p1_attempt011_admission_observation_contract.json`
2. `e4_r6_pc2w_p1_attempt011_execution_authorization.json`
3. `execute_e4_r6_pc2w_p1_attempt011_admission_observation.py`
4. `validate_e4_r6_pc2w_p1_attempt011_static_packet.py`

The `R1` contract MUST state that runtime is denied, the exact command is unconfirmed, the output root must not pre-exist, one process invocation is the maximum, and retry/fallback counts are zero. The validator MUST accept only either the exact four-file dirty draft at `R0` or the exact four-file committed delta whose sole parent is `R0`; committed validation also requires a clean worktree and no post-commit packet drift.

### 5.3 Gate receipt commits

After all static and synthetic tests pass at clean `R1`:

- central static validation creates and commits only `rebaseline_v2_e4_r6_pc2w_p1_attempt011_central_static_validation_receipt.json`;
- a fresh independent context starts from that exact central-receipt commit and creates and commits only `rebaseline_v2_e4_r6_pc2w_p1_attempt011_fresh_independent_audit_receipt.json`;
- exact-command confirmation creates or modifies no file; and
- the runtime process may write only the following four files under the new immutable Attempt-011 output root:
  - `admission_observation.json`
  - `command_receipts.json`
  - `execution_receipt.json`
  - `handoff.json`

No phase may modify `pipeline_state`, an Attempt-009/010 artifact, any dataset, any model artifact, or any path outside its stated write set.

## 6. Attempt-agnostic gate-receipt interface

`e4_r6_pc2w_p1_gate_receipt_binding.py` MUST expose immutable value objects equivalent to the following logical contract; names may not be changed without updating the contract and all named tests:

- `GateReceiptSpec`
  - `stage_id`
  - `packet_files`
  - `central_schema`
  - `central_verdict`
  - `central_validator_verdict`
  - `fresh_audit_schema`
  - `fresh_audit_verdict`
- `ReceiptLocator`
  - canonical repository-relative `path`
  - lowercase 64-hex raw-Git-blob `sha256`
- `validate_bound_gate_receipts(...)`
  - keyword-only inputs for repository root, execution head, packet commit, `GateReceiptSpec`, central locator, and fresh-audit locator;
  - explicit injected/read-only Git blob reader for exact bytes;
  - no import of any `attemptNNN` runner or module;
  - no module-global mutable attempt configuration; and
  - a deterministic two-entry binding record only after every predicate passes.

The implementation MUST parse the exact receipt bytes read from Git at `execution_head`, not a separately read working-tree copy. Its JSON parser MUST reject invalid UTF-8, non-object roots, exact duplicate keys, case-fold duplicate keys, and `NaN`, `Infinity`, or `-Infinity`. It MUST compute raw-byte SHA-256 itself and compare it to each locator before parsing.

The validator MUST derive expected packet facts from `spec.packet_files` at `packet_commit`; it MUST NOT read a mutable global such as inherited `PACKET_RELATIVES`. Both receipt predicates MUST compare `receipt.stage_id` only to `spec.stage_id`. The generic module and its contract MUST contain no literal matching `ATTEMPT[0-9]+`, and the module MUST not import Attempt-008, Attempt-009, Attempt-010, or Attempt-011 code.

The Attempt-011 runner is the only place that constructs the Attempt-011 spec. It may reuse the frozen Attempt-009 runtime compatibility adapter and Attempt-010 command-interface module, but after configuring the retained runtime it MUST install the generic Attempt-011-bound receipt validator before calling the inherited main function. A static test MUST prove there is no reachable call to the Attempt-009 `_validate_gate_receipts` predicate. Schema, verdict, stage, and packet roster are passed together as one immutable object so they cannot be partially rebound.

Stable failure codes MUST distinguish at least locator, raw hash, JSON, schema, stage, verdict, packet-commit, packet-artifact, validator-verdict, central-link, runtime-boundary, and write-set failures. No failure code or persisted error needs to contain raw host data or exception text.

## 7. Mandatory test-first matrix

The test file MUST implement the following 62 named synthetic cases as separate tests. All Git/blob readers, filesystem creation, clock, subprocess, Docker, WSL, PowerShell, sleeps, and inherited runner calls MUST be faked or patched. Any unexpected process-spawn call MUST raise a test failure immediately.

### 7.1 Positive and decoupling cases — 4

- `GR-POS-01`: a valid Attempt-011 central receipt matches schema, stage, verdict, packet commit, exact packet facts, validator verdict, runtime false, path, hash, and one-file write set.
- `GR-POS-02`: a valid Attempt-011 fresh-audit receipt matches its schema, stage, verdict, packet commit, exact packet facts, central raw-blob SHA-256, runtime false, path, hash, and one-file write set.
- `GR-POS-03`: a valid pair returns exactly two sanitized binding records and no source document mutation.
- `GR-POS-04`: the same generic function accepts a synthetic different stage when spec and both receipts agree, proving no Attempt-011 or prior-attempt literal controls the predicate.

### 7.2 Central receipt negative bindings — 10

- `GR-C-01` schema mismatch.
- `GR-C-02` verdict mismatch.
- `GR-C-03` stage mismatch.
- `GR-C-04` packet-commit mismatch, including uppercase or abbreviated commit values.
- `GR-C-05` packet-artifact path or order mismatch.
- `GR-C-06` packet-artifact byte-count mismatch.
- `GR-C-07` packet-artifact SHA-256 mismatch.
- `GR-C-08` supplied central receipt raw-blob SHA-256 mismatch.
- `GR-C-09` central one-file write-set mismatch, including an extra path.
- `GR-C-10` central validator verdict mismatch.

### 7.3 Fresh-audit receipt negative bindings — 10

- `GR-A-01` schema mismatch.
- `GR-A-02` verdict mismatch.
- `GR-A-03` stage mismatch.
- `GR-A-04` packet-commit mismatch.
- `GR-A-05` packet-artifact path or order mismatch.
- `GR-A-06` packet-artifact byte-count mismatch.
- `GR-A-07` packet-artifact SHA-256 mismatch.
- `GR-A-08` supplied fresh-audit receipt raw-blob SHA-256 mismatch.
- `GR-A-09` fresh-audit one-file write-set mismatch, including an extra path.
- `GR-A-10` `central_validation_receipt_git_blob_sha256` mismatch.

### 7.4 Strict JSON cases — 7

- `GR-J-01` exact duplicate key in central receipt.
- `GR-J-02` case-fold duplicate key in central receipt.
- `GR-J-03` `NaN` in central receipt.
- `GR-J-04` exact duplicate key in fresh-audit receipt.
- `GR-J-05` case-fold duplicate key in fresh-audit receipt.
- `GR-J-06` `Infinity` in fresh-audit receipt.
- `GR-J-07` `-Infinity` in either receipt.

### 7.5 Locator and hash-shape cases — 4

- `GR-L-01` central and fresh-audit paths are identical.
- `GR-L-02` an absolute receipt path is supplied.
- `GR-L-03` traversal, non-canonical, outside-`00_control`, packet-alias, or non-JSON path is supplied; each subcase must fail closed.
- `GR-L-04` a non-64-lowercase-hex receipt hash is supplied, including uppercase hex.

### 7.6 Exact process-command cases — 13

- `GR-CMD-01` exact `PYTHON_EXECUTABLE -B ABSOLUTE_ATTEMPT011_RUNNER EXACT_ORDERED_ARGUMENTS` passes and normalizes only `-B`.
- `GR-CMD-02` missing `-B` fails.
- `GR-CMD-03` unknown interpreter flag fails.
- `GR-CMD-04` duplicate `-B` fails.
- `GR-CMD-05` `python -c` fails.
- `GR-CMD-06` `python -m` fails.
- `GR-CMD-07` Python executable drift fails.
- `GR-CMD-08` runner path drift fails.
- `GR-CMD-09` argument order drift fails.
- `GR-CMD-10` argument value drift fails.
- `GR-CMD-11` any required argument missing fails.
- `GR-CMD-12` any receipt argument duplicated fails.
- `GR-CMD-13` central and fresh-audit locators or hashes swapped fails.

### 7.7 No-runtime-before-gate cases — 5

- `GR-NR-01` central receipt failure occurs before output-root creation and before any command dispatch.
- `GR-NR-02` fresh-audit receipt failure occurs before output-root creation and before any command dispatch.
- `GR-NR-03` process-command mismatch occurs before receipt parsing, output-root creation, or command dispatch.
- `GR-NR-04` any frozen dependency hash mismatch occurs before output-root creation or command dispatch.
- `GR-NR-05` a pre-existing Attempt-011 output root fails before any command dispatch and is never deleted or reused.

Each case MUST assert zero calls to the host-command wrapper, Docker, WSL, PowerShell, sleep, output writer, and cleanup command builder. Source/AST validation MUST also prove that receipt validation precedes `output_root.mkdir` and the definition or first use of `invoke`.

### 7.8 Cleanup and final-state cases — 9

- `GR-CL-01` failed P04 prevents S00.
- `GR-CL-02` an S00 exception attempts F00 once and then F01 once, in that order.
- `GR-CL-03` an exception in any D00-D06 lane attempts F00 once and F01 once.
- `GR-CL-04` an F00 exception still attempts F01 once through the nested `finally`.
- `GR-CL-05` successful admitted flow requires snapshots exactly `A`, `B`, and `C`.
- `GR-CL-06` any missing or unstable closure snapshot yields the fail-closed runtime verdict.
- `GR-CL-07` final state differing from pre-start yields the fail-closed runtime verdict.
- `GR-CL-08` the complete command ID sequence is exact, with each ID occurring once, `automatic_retry_count=0`, and `fallback_count=0`.
- `GR-CL-09` the output manifest contains exactly four allowed filenames and rejects extras; failure evidence is durable before the first mocked runtime command and refreshed after every mocked receipt.

### 7.9 Retained tests and static checks

The central validator MUST additionally run the frozen suites already used by Attempt-010:

- 10 Attempt-010 command-interface tests;
- 9 Attempt-009 runtime-compatibility tests;
- 8 Attempt-008 probe-contract tests; and
- 9 Attempt-008 safe-envelope tests.

Acceptance is all 62 new named cases plus all 36 retained tests passing, for an aggregate of exactly 98 tests when each named case is implemented as one test method. The receipt MUST list counts by suite and all 62 case IDs; a matching total without the ID roster is insufficient. Python must run with `-B`, and pre/post `.pyc` inventories must be identical.

## 8. Versioning, artifact identities, and hashes to regenerate

Attempt-011 uses these new identities:

| Artifact | Required identity |
|---|---|
| stage | `E4-R6-PC2W-P1-ATTEMPT011` |
| admission contract schema | `stage1e-e4-r6-pc2w-p1-attempt011-admission-observation-contract-1.0` |
| execution authorization schema | `stage1e-e4-r6-pc2w-p1-attempt011-execution-authorization-1.0` |
| central receipt schema | `stage1e-e4-r6-pc2w-p1-attempt011-central-static-validation-receipt-1.0` |
| central receipt verdict | `PASS_PC2W_P1_ATTEMPT011_CENTRAL_STATIC_VALIDATION` |
| fresh-audit receipt schema | `stage1e-e4-r6-pc2w-p1-attempt011-fresh-independent-audit-receipt-1.0` |
| fresh-audit PASS verdict | `PASS_PC2W_P1_ATTEMPT011_FRESH_INDEPENDENT_AUDIT_READY_FOR_EXACT_COMMAND_CONFIRMATION` |
| runtime PASS verdict | `PASS_PC2W_P1_ATTEMPT011_ADMISSION_OBSERVATION_COMPLETE_FOR_CENTRAL_EVALUATION` |
| runtime host-inadmissible verdict | `FAIL_CLOSED_PC2W_P1_ATTEMPT011_CURRENT_HOST_NOT_ADMISSIBLE` |
| confirmation token | `USER_CONFIRMED_EXACT_ATTEMPT011_PROCESS_COMMAND_AFTER_CENTRAL_VALIDATION_AND_FRESH_AUDIT` |
| output schemas | Attempt-011 `command-receipts-1.0`, `admission-observation-1.0`, `execution-receipt-1.0`, and `handoff-1.0` |

Do not copy any future SHA from Attempt-010. Generate and bind the following after the corresponding commit exists, always from exact raw Git blob bytes with SHA-256 and with no checkout newline normalization:

1. At `R0`: byte count and SHA-256 for the generic binding module, binding contract, test file, and every other frozen inherited dependency named by the Attempt-011 validator.
2. At `R1`: full 40-hex packet commit, its sole parent `R0`, and ordered path/byte-count/SHA-256 facts for the exact four packet files.
3. At the central-receipt commit: the central receipt's path, commit, raw byte count, and raw-Git-blob SHA-256.
4. At the fresh-audit commit: the audit receipt's path, commit, raw byte count, and raw-Git-blob SHA-256.
5. At exact-command confirmation: bind the exact `R1` packet commit, exact execution head equal to the fresh-audit receipt commit, both receipt paths, and both receipt raw-Git-blob SHA-256 values.

Material Passport version labels MUST be new Attempt-011 `v1` labels. The Attempt-011 contract and receipts MUST list the Attempt-010 fresh-audit `HANDOFF_INCOMPLETE` receipt and this remediation-plan version as upstream dependencies; this records supersession without changing the old artifacts.

## 9. Sequential gates and context/model assignment

Every task in this chain MUST use the Standard/default service tier. Only `gpt-5.6-sol` with reasoning `high` or `xhigh` is allowed. Fast and priority are forbidden. A gate MUST stop if its task configuration cannot demonstrate the requested model, reasoning effort, and Standard/default tier; no model or tier may be inferred from prose.

| Order | Gate | Context owner | Required model configuration | Required output before next gate |
|---:|---|---|---|---|
| 1 | Implementation | new implementation worktree/context from clean `main` | Sol High, Standard | exact `R0`, then exact four-file `R1`; no runtime |
| 2 | Synthetic/static tests | same implementation context, all external calls patched | Sol High, Standard | all 98 tests and static checks pass; clean checkout; output root absent |
| 3 | Central static validation | central context distinct from the implementation writer | Sol XHigh, Standard | one-file central receipt commit with PASS |
| 4 | Fresh independent audit | fresh context with no reliance on implementation conclusions; read all bound bytes independently | Sol XHigh, Standard | one-file audit receipt commit with PASS; any major finding produces `HANDOFF_INCOMPLETE` |
| 5 | Exact command confirmation | central/user-owned confirmation context after reading both committed receipts | Sol XHigh, Standard | exact fully substituted command displayed and explicitly confirmed; no file write and no execution |
| 6 | Single runtime observation | dedicated execution context routed through experiment-agent/code-runner safety rules | Sol High, Standard | exactly one runner process observation, then stop regardless of outcome |

No gate may be combined with the next gate. The fresh auditor must not author or repair the implementation or central receipt. Exact command confirmation is invalid if requested before both PASS receipts are immutable and hash-bound.

## 10. Exact-command construction rule

Only after Gate 4 passes, the central context may render a command in this exact argument order, replacing every angle-bracket token with a directly observed value:

```text
<ABS_PYTHON_3_11_9> -B <ABS_REPO_ROOT>\research\hybrid-recsys-v5\03_benchmark\stage1e\00_control\execute_e4_r6_pc2w_p1_attempt011_admission_observation.py --repo-root <ABS_REPO_ROOT> --packet-commit <R1_FULL_SHA> --expected-head <FRESH_AUDIT_COMMIT_FULL_SHA> --central-validation-receipt research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt011_central_static_validation_receipt.json --central-validation-receipt-sha256 <CENTRAL_RAW_GIT_BLOB_SHA256> --fresh-audit-receipt research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt011_fresh_independent_audit_receipt.json --fresh-audit-receipt-sha256 <AUDIT_RAW_GIT_BLOB_SHA256> --execution-confirmation USER_CONFIRMED_EXACT_ATTEMPT011_PROCESS_COMMAND_AFTER_CENTRAL_VALIDATION_AND_FRESH_AUDIT
```

The central context MUST show the fully substituted command to the user and receive a separate explicit confirmation of that exact string. Confirmation of this plan, an earlier attempt, a template containing placeholders, or a differently ordered command is not execution authorization.

## 11. Stop conditions

Stop immediately with no runner invocation if any of the following is true:

- implementation start is not clean `main`, this plan is not an ancestor, or unexpected tracked/untracked files exist;
- any phase's exact write set or single-parent commit shape differs from Section 5;
- any existing Attempt-009/010 artifact differs from its frozen raw-Git-blob fact;
- the generic module contains an Attempt-number literal/import or uses mutable global attempt configuration;
- any required test ID is missing, skipped, xfailed, flaky, or fails;
- a validator or audit uses working-tree bytes in place of the exact Git blob for a receipt binding;
- any JSON is malformed, duplicate-keyed, case-fold duplicate-keyed, non-finite, or not a root object;
- any schema, verdict, stage, commit, blob fact, central-link, runtime boundary, or write set mismatches;
- the central receipt is not PASS, or the fresh audit reports any major finding or a non-PASS verdict;
- model/reasoning/tier is not demonstrably one of the allowed Standard configurations;
- the execution head differs from the fresh-audit commit, the worktree is dirty, or either receipt is not an ancestor-bound blob at that head;
- the output root already exists;
- the exact command has not been separately confirmed after both receipts;
- a runner process has already been invoked once for Attempt-011; or
- any request asks for retry, fallback, materialization, preprocessing, training, evaluation, benchmark, test-set access, forced kill, service restart, or settings mutation without a new explicit authorization and a new audited attempt.

At every stop, preserve `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, and `benchmark_admission_opened=false` unless a later single runtime observation legitimately changes only the observation-specific fields.

## 12. Cleanup, rollback, and recovery

- Before any runtime command, rollback means aborting the gate and preserving the dirty worktree or rejected commit for inspection; do not amend, rebase, force-push, or rewrite prior commits or receipts.
- After `R1` or either receipt is committed, repair is additive. Publish a new corrective attempt if semantics change; never edit an old receipt to turn a failure into PASS.
- Once the Attempt-011 output root is created, it is immutable. A partial or failed output packet is preserved as evidence and the same root is never deleted, cleaned, or reused.
- If S00 is attempted, F00 is attempted at most once in the outer `finally`, and F01 is attempted at most once in its nested `finally`. No force-kill, service restart, settings change, or second cleanup attempt is automatic.
- Cleanup failure, unstable closure snapshots, or final-state mismatch yields the fail-closed runtime verdict and stops. Manual recovery requires a separate user decision and cannot authorize a rerun of Attempt-011.
- Any pre-runtime failure after exact confirmation produces no automatic retry. If a durable failure receipt is later required, it must be created in a separate receipt-only commit that preserves the original error hash and zero runtime-command counts.

## 13. Acceptance criteria for the central context

The central context may advance to exact-command confirmation only when every item below is evidenced, not inferred:

1. `R0` and `R1` have the exact path/status deltas in Section 5, full SHAs are recorded, and both commits have exactly one parent.
2. All pre-existing Attempt-009/010 files and receipts are unchanged; Attempt-010 remains `HANDOFF_INCOMPLETE`.
3. The generic gate validator has one immutable spec input, parses exact raw Git blobs strictly, derives packet facts from the explicit packet roster, and contains no Attempt-number literal/import.
4. The Attempt-011 runner installs the generic validator after retained-runtime configuration and before inherited `main`; the Attempt-009 predicate is unreachable.
5. All 62 named new tests and all 36 retained tests pass with zero new/modified Python bytecode and zero external/runtime command calls.
6. Static source analysis proves command binding, frozen artifacts, both receipts, authorization, and output-root absence are validated before `mkdir`, `invoke`, Docker, WSL, PowerShell, or sleep.
7. The central receipt is strict JSON, binds `R1` and the exact packet facts, records the required test IDs/counts and no-runtime truth, has a one-file write set, and is committed alone.
8. The fresh auditor independently rereads all mandatory blobs, replays the complete matrix, verifies the central receipt raw hash and commit/delta, records no major finding, emits the required PASS verdict, and commits only its receipt.
9. The execution head equals the fresh-audit commit, is clean, contains both exact receipt blobs, and the new output root is absent.
10. Task metadata at every future gate proves `gpt-5.6-sol`, reasoning `high` or `xhigh` as assigned, and Standard/default tier; Fast/priority is false.
11. The fully substituted command exactly matches Section 10 and is separately confirmed by the user after Gates 3 and 4.
12. The execution context invokes the command once, never retries, monitors only the declared output root, performs the mandated one-pass cleanup, and stops after the single observation regardless of PASS, host-inadmissible, or incomplete outcome.

If any item is absent or ambiguous, the only valid disposition is `PLAN_BLOCKED` for implementation handoff or `HANDOFF_INCOMPLETE` for a later validation/audit gate. No exact command may be confirmed or run.

## 14. Current plan-task provenance

- Requested policy for this plan task: Standard only; Sol High or Sol XHigh; no Fast/priority.
- Actual model observed by this context: `UNOBSERVABLE`.
- Actual reasoning effort observed by this context: `UNOBSERVABLE`.
- Actual service tier observed by this context: `UNOBSERVABLE`.
- Runtime commands, Docker commands, WSL commands, host probes, preprocessing, training, evaluation, and benchmark executions performed while preparing this plan: `0`.
- Plan-task verdict: `PLAN_READY`.
