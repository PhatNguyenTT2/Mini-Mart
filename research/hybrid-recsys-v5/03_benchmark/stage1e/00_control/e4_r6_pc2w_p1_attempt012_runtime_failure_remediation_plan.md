# Stage 1E Critical — Attempt-012 runtime failure remediation plan

## Material Passport

- Origin Skill: `experiment-agent`
- Origin Mode: `plan` (static audit and remediation design only)
- Origin Date: `2026-08-28T00:00:00+07:00`
- Origin Date Semantics: session date with the configured `Asia/Saigon` timezone; no ambient-clock or host probe was used
- Verification Status: `UNVERIFIED`
- Version Label: `stage1e_e4_r6_pc2w_p1_attempt012_runtime_failure_remediation_plan_v1`
- Upstream Dependencies:
  - `stage1e_e4_r6_pc2w_p1_attempt012_admission_observation_execution_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt012_admission_observation_contract_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt012_pre_runtime_authority_contract_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt009_runtime_compatibility_contract_v3`
  - `stage1e_e4_r6_pc2w_p1_attempt008_safe_probe_envelope_contract_v1`
- Repro Lock: `null` — this is a planning artifact, not an execution or replay guarantee
- Experiment Intake Declaration: `no_experiments_declared`; this stage ran no experiment and opened no scientific TEST set
- Requested/Routed Model: `gpt-5.6-sol`
- Requested/Routed Reasoning Effort: `ultra`
- Actual Model / Reasoning: `gpt-5.6-sol` / `ultra` (current task-routing identity)
- Required Service Tier / Display Speed: `default` / Standard
- Observed Service Tier / Speed: `UNOBSERVABLE` / `UNOBSERVABLE`; neither is inferred from latency, prose, or prior receipts
- Fast/Priority Policy: forbidden. No absence-of-telemetry claim is promoted into a positive Standard/default observation; any authoritative later evidence of Fast/Priority makes this handoff `HANDOFF_INCOMPLETE`.
- Central Pre-commit Adjudication: the central context corrected the four raw-Git-blob byte/SHA-256 bindings and restored the user-authorized role split: Ultra Standard for critical diagnosis, adjudication, and independent audits; XHigh Standard for bounded implementation and one-shot execution. The causal graph and remediation seams were not changed.
- Content Hash: external to this self-referential document; the final Git commit binds the exact bytes

## Plan verdict

`REMEDIATION_PLAN_READY_FOR_CENTRAL_ADJUDICATION`

This verdict means that the committed Attempt-012 evidence supports a bounded, fail-closed remediation plan. It does **not** repair or rerun Attempt-012, approve Attempt-013, admit a benchmark, validate Docker/WSL/Hyper-V health, or authorize materialization, training, evaluation, or scientific TEST access.

## Scope, lineage, and immutable truth

The audit base is branch `codex/stage1e-attempt012-runtime-failure` at:

- Audited commit: `e28d6b69fb53c871903a523e07da4ae0086e925a`
- Audited parent: `314d7c85c5a905d3951658745505e8dc685bb182`
- Audited commit delta: exactly the four Attempt-012 runtime receipts listed below
- Worktree state before this plan was created: clean, including untracked files

Attempt-012 is consumed and immutable:

- Runtime launches: exactly `1`
- Docker Desktop start attempts: `1`, PASS
- Docker Desktop stop attempts: `1`, PASS
- WSL shutdown attempts: `1`, PASS
- Closure snapshots: `3` (`A`, `B`, `C`), all lanes PASS
- Closure stability: PASS
- Final closure equals pre-start baseline: PASS
- Automatic retries: `0`
- Fallbacks: `0`
- Verdict: `FAIL_CLOSED_PC2W_P1_ATTEMPT012_CURRENT_HOST_NOT_ADMISSIBLE`
- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- Benchmark admission: closed

No receipt supports a RAM, virtual-memory, daemon-start, daemon-health, Hyper-V, disk-threshold, or cleanup-failure attribution. Such attributions are prohibited in this plan.

This stage performed only committed-file/Git reads, static text inspection, and deterministic hashing of a known exception type name. It did not import or invoke any runner, call Docker/WSL/Hyper-V/PowerShell host probes, use the network, run materialization/preprocessing/training/evaluation/benchmark work, open TEST, or modify any implementation, contract, test, receipt, pipeline state, scientific artifact, or runtime output.

## Runtime receipt byte bindings

All four receipts were read in full. The byte bindings below are for the blobs committed at the audited commit.

| Receipt | Git blob OID | Bytes | SHA-256 |
|---|---|---:|---|
| `rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/admission_observation.json` | `692cd0aec615a107029f34e54a7f1b4069b52318` | 24,292 | `7295f026d57e497dfce68f768e4153b94e27436361c6e18ffe4818709ab72459` |
| `rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/command_receipts.json` | `ee90f0ba8761feb82dbb715c5f9de6c84e47c736` | 22,369 | `1b722165dfed8c8ba27832636fd7917f899786239d507e839cf9c7d1820d5098` |
| `rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/execution_receipt.json` | `da8f87ac3dac7136c0d617b8e9605817b9243f7b` | 5,189 | `a35bcd4d70e0028a54eb6da3ace9a3da083dca15ae7100d8638e74a334c1973f` |
| `rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/handoff.json` | `0c979486b03801f14b01ad9c283dad3efcc64536` | 1,488 | `1da3715ac0752fcc5e967791f4a0c8561b98128283088f87b1f0ed24c5fee6a4` |

All repository paths below are relative to `research/hybrid-recsys-v5/03_benchmark/stage1e/` unless stated otherwise.

## Evidence table

| ID | Specific locator | Observation | Evidentiary use |
|---|---|---|---|
| E01 | `rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/execution_receipt.json#/verdict` | Exact fail-closed verdict for the consumed attempt | Establishes terminal Attempt-012 state; never a repair claim |
| E02 | Same receipt `#/identity_failures/0` | D01: `PROCESS_PROBE_RESOLVE_PARENT`, target `com.docker.backend`, error-type hash `386c08bd...70f7fc` | Primary failure on the process/TCP branch |
| E03 | `00_control/e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py:73-74` | The probe indexes the one process snapshot by `ParentProcessId` and deliberately throws `System.InvalidOperationException` when the parent row is absent | Proves the immediate D01 mechanism; does not prove why the parent was absent |
| E04 | Deterministic UTF-8 SHA-256 of `System.InvalidOperationException` | `386c08bd726234e4c428a6fad9def307ff47345970145cc613b1cff9736707fc`, exactly E02 | Falsifies a claim that E02 proves an unrelated raw PowerShell exception; it is the probe's own closed null-parent throw |
| E05 | `00_control/e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py:243-269` | Any unavailable process envelope becomes a D01 `IdentityContractError`; the entire validated process object remains unavailable | Explains `during_process_identity_complete=false` |
| E06 | Same source `:271-280` and execution receipt `#/identity_failures/1` | `validate_tcp_probe_envelope(..., processes=None)` raises `TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE` before validating D02's own envelope | Proves D02 is a dependent failure, not an independently demonstrated TCP failure |
| E07 | `command_receipts.json#/commands/7` and `#/commands/8` | D01 and D02 each exited `0`; D01 stdout was 297 bytes and D02 stdout was 3,563 bytes; raw streams were not persisted | Command transport succeeded. Semantic content beyond the persisted closed locators is `UNKNOWN` |
| E08 | Execution receipt `#/identity_failures/2` | Independent Docker server failure: `DOCKER_SERVER_FIELD_CONFLICT`, field `BuildTime` | Primary failure on the Docker identity branch |
| E09 | `00_control/e4_r6_pc2w_p1_attempt009_runtime_compatibility.py:323-359` | For every server field, root and Engine values are normalized only by type, then compared with raw Python `!=`; unequal `BuildTime` strings fail before the Attempt-008 format classifier | Proves a representation-sensitive schema assumption |
| E10 | `00_control/e4_r6_pc2w_p1_attempt008_probe_contract.py:59-98` and `:236-272` | The retained classifier already recognizes Docker CLI human and RFC3339-UTC families without inventing a timezone, but the Attempt-009 root/Engine equality gate precedes it | Identifies the minimal field-aware comparator seam |
| E11 | `command_receipts.json#/commands/9`, `/10`, `/11` | D03 Docker version, D04 Docker info, and D05 context inspect all exited `0` with empty stderr | Falsifies a direct daemon-query transport failure as the recorded cause |
| E12 | `admission_observation.json#/during/docker_desktop_file_identity` and execution receipt `#/pass_conditions/docker_desktop_executable_identity_complete` | Docker Desktop executable identity, signature, version, and file hash completed | Independent positive identity evidence; not proof of server-field consistency |
| E13 | Execution receipt `#/pass_conditions` | Start, stop, shutdown, all three closure snapshots, stability, final/baseline equality, exact command order, and zero retry/fallback are all true | Separates successful lifecycle/closure from identity rejection |
| E14 | `admission_observation.json#/sanitization` and `command_receipts.json#/raw_argv_stdout_stderr_persisted` | Raw process paths, command lines, network addresses, proxy values, Docker root, stdout/stderr, and argv were not persisted | Defines the legitimate limit on root-cause resolution and the privacy floor for remediation |
| E15 | `handoff.json#/next_gate` and `#/truth_state` | `FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY`; benchmark remains closed and scientific truth is unchanged | Prohibits Attempt-012 retry or implicit continuation |
| E16 | `00_control/execute_e4_r6_pc2w_p1_attempt008_admission_observation.py:842-956` | D01, D02, and Docker identity failures feed separate completeness predicates and the common `identity_failures_absent` predicate | Confirms the two-branch causal graph and fail-closed aggregation |
| E17 | `00_control/e4_r6_pc2w_p1_attempt012_pre_runtime_authority_contract.json#/model_policy` | Frozen Attempt-012 policy is XHigh-oriented | It is historical and immutable; Attempt-013 must define a new role-separated policy rather than restating or editing Attempt-012 |

## Fail-closed causal graph

```text
PRIMARY ROOT A — process snapshot/parent-lineage contract
  D01 sees com.docker.backend
    -> ParentProcessId is not resolvable in the single enumerated process map
    -> deliberate InvalidOperationException
    -> PROCESS_PROBE_RESOLVE_PARENT
    -> validated process identity object = None
       -> DEPENDENT D02 rejects before inspecting its own envelope
       -> TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE
       -> process_complete=false; tcp_complete=false

INDEPENDENT ROOT B — Docker server schema comparison
  root BuildTime and Engine Details BuildTime are both present, non-empty, unequal strings
    -> generic raw equality gate
    -> DOCKER_SERVER_FIELD_CONFLICT(field=BuildTime)
    -> docker_identity=None; cross_consistency=false

ROOT A + dependent D02 + ROOT B
  -> identity_failures_absent=false
  -> FAIL_CLOSED_PC2W_P1_ATTEMPT012_CURRENT_HOST_NOT_ADMISSIBLE
  -> benchmark remains closed; RESULT_STATUS=NOT_RUN; TEST_SET_OPENED=NO

INDEPENDENT SUCCESS BRANCH
  start PASS -> stop PASS -> WSL shutdown PASS -> A/B/C closure PASS
  -> final state equals pre-start baseline
  -> does not override either identity root
```

## Root-cause classification and confidence

| Finding | Classification | Confidence | Exact limit |
|---|---|---:|---|
| The frozen Attempt-012 contract rejects this exact host observation | **Proven host/contract incompatibility** | Very high (`0.99`) | This proves only non-admissibility under the frozen contract, not intrinsic host or Docker failure |
| D01's immediate trigger is an unresolved parent row in the one enumerated process map | **Proven immediate root** | Very high (`0.99`) | Why the parent row was absent—parent exit, snapshot race, PID lifecycle, provider behavior, or another cause—is `UNKNOWN` |
| Requiring every target's parent to exist in the same non-atomic snapshot before accepting otherwise complete self identity | **Over-strict probe/schema assumption** | High (`0.95`) | Central must adjudicate whether parent lineage is supplementary to direct self identity; no name-specific bypass is permitted |
| D02 is caused by the unavailable validated D01 object | **Proven dependent failure** | Certain (`1.00`) | D02 raw envelope was not retained, so its own semantic success/failure is `UNKNOWN` despite exit code `0` |
| `BuildTime` fails because two present server surfaces contain unequal strings | **Proven independent immediate root** | Certain (`1.00`) | The exact strings are not stored |
| Generic raw string equality is too strong for a field with already-supported human/RFC3339 representations | **Over-strict schema assumption** | High (`0.95`) | Whether the two Attempt-012 values denote the same civil second or genuinely different builds is `UNKNOWN` |
| RAM/vmem pressure, Docker daemon failure, WSL failure, Hyper-V failure, disk shortage, or cleanup failure caused the verdict | **Unsupported** | No admissible evidence | Must remain `UNKNOWN`, not converted into a diagnosis |

The important distinction is: the current host is demonstrably incompatible with the **frozen observation contract**, while the receipts do not show that the host is incapable of satisfying a corrected, equally fail-closed identity contract.

## Minimal remediation design

### Attempt-numbering decision

Any future runtime process is **Attempt-013**, not an Attempt-012 retry, revision, replay, or fallback. The proposed new runtime root is:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_av/E4_R6PC2W_P1_attempt013_admission_observation`

That path is absent at plan time. Attempt-013 receives a new stage ID, schemas, packet commit, two gate receipts, confirmation token, output root, command binding, attempt budget, and role-separated model policy. No Attempt-012 token, receipt, output path, authorization, or model-policy byte may be reused.

### Seam A — direct process identity versus parent lineage

Create a new versioned process-envelope seam; do not edit Attempt-008/009/012 source.

1. Keep every direct self-identity requirement for every target row: canonical target name, positive unique PID, executable-path hash, executable-file SHA-256, valid Authenticode status, signer-subject hash, non-empty file version, creation time, and command-line hash.
2. Replace the all-or-nothing parent lookup with an exact per-row `ParentResolution` union:
   - `RESOLVED`: positive parent PID plus valid parent-name and parent-path hashes are required.
   - `UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT`: the positive observed `ParentProcessId` is retained, parent hashes are explicitly `null`, and all direct self-identity fields remain mandatory.
3. Any missing/malformed status, missing direct identity, invalid signature/hash, missing required process name, duplicate PID, unknown enum, or inconsistent nullability fails closed.
4. Do not special-case `com.docker.backend`, add sleeps, repeat the process query, or issue a second parent lookup. The new state records a bounded snapshot limitation; it does not mask it with timing-dependent retries.
5. Admission uses a validated self-identity index for required target processes. Parent lineage remains visible and schema-checked, but an explicitly unresolved parent cannot erase otherwise complete direct process identity.

This is not permission to bypass identity checks. The direct identity evidence becomes the ownership authority; parent lineage becomes a separately explicit evidence dimension instead of a prerequisite that destroys the whole identity object.

### Seam B — TCP ownership dependency

1. D02 must consume only the validated self-identity index produced by Seam A.
2. Every TCP row must still bind exactly to an observed `(ProcessName, ProcessId)` in that index, with canonical rows, valid hashed addresses, ports, and state.
3. If the process envelope itself is unavailable or any required self identity is incomplete, retain `TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE` and fail closed.
4. If the D02 envelope is malformed or unavailable, emit its own D02 failure; never convert it into a D01 dependency or assume success from exit code `0`.

This removes only the accidental dependency on parent-lineage completeness. It does not relax TCP ownership identity.

### Seam C — field-aware `BuildTime` comparison

Keep exact root/Engine equality for every server field except `BuildTime`. For `BuildTime`:

1. Validate each present value against the existing closed Docker-human or RFC3339-UTC families before comparison.
2. Accept `EXACT_RAW` when strings match exactly.
3. Accept `FORMAT_EQUIVALENT_CIVIL_SECOND` only when:
   - one value is the validated Docker-human family and the other is validated RFC3339 UTC;
   - year, month, day, hour, minute, and second match exactly;
   - the RFC3339 fractional component is absent or all zero; and
   - the Docker-human weekday is valid.
4. This classification compares representations from the same Docker server record; it does not invent a timezone for the human form and must not be described as proof of instant-time equivalence.
5. Two RFC3339 values compare as normalized UTC values with their represented fractional precision. Different civil components, a nonzero fraction hidden by the human form, invalid/unsupported formats, missing-both, or ambiguous values retain a field-specific fail-closed conflict/missing/format error.
6. Preserve root and Engine source attribution and a deterministic comparison profile. Do not relax conflicts for `Version`, API versions, commit, Go version, OS, architecture, kernel, or `Experimental`.

### Privacy, sanitization, and deterministic receipts

The new seam must preserve or strengthen the current privacy floor:

- Never persist raw process paths, parent paths, command lines, local/remote addresses, proxy values, Docker root, daemon ID, full stdout/stderr, or full argv.
- Persist only allowlisted process names, numeric PIDs already in the existing schema, closed enums, safe counts, stable error codes, and SHA-256 values.
- For parent lineage, persist the exact resolution enum and nullability state; never persist a raw parent path or name.
- For `BuildTime` comparison, persist source labels, format labels, `comparison_profile`, `civil_second_equal`, `fraction_zero_or_absent`, and separate value SHA-256 digests. Do not persist the complete Docker command output.
- Sort process and TCP rows canonically and serialize strict UTF-8 JSON with duplicate/case-fold-duplicate keys and non-finite values rejected.
- A failure packet must retain D01, D02, and Docker server findings as separate records; no deduplication may erase the causal relationship.
- Raw-output absence remains explicit. Unknown raw values must never be reconstructed from hashes or guessed from tests.

## Red tests before implementation

Central must first write these pure/synthetic fixtures and demonstrate that the relevant positive-remediation fixtures are RED against the frozen Attempt-012 seam. No runner import/invocation or host/runtime command is allowed in this phase.

| Test ID | Fixture and expected pre-fix result | Required post-fix result |
|---|---|---|
| RED-P01 | Complete signed/hashes-valid `com.docker.backend` self row whose positive parent PID is absent from the enumerated map | Old seam fails; new seam returns `UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT` while retaining complete self identity |
| RED-P02 | Same as RED-P01 but one self hash/signature/version field missing or invalid | Must remain fail-closed; unresolved parent cannot legalize incomplete self identity |
| RED-P03 | Unknown parent-resolution enum, resolved status with null hashes, or unresolved status with populated raw parent fields | Must fail with stable schema/nullability codes |
| RED-P04 | Required `docker desktop` or `com.docker.backend` self row absent | Must fail `PROCESS_REQUIRED_IDENTITIES_MISSING` or its new stable equivalent |
| RED-T01 | Valid TCP owner bound to a complete self row whose parent status is explicitly unresolved | Old dependency path is RED; new D02 validates the exact owner binding |
| RED-T02 | Entire D01 envelope unavailable | D02 remains `TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE` |
| RED-T03 | TCP PID/name pair not present in the validated self index | Must fail closed as ambiguous/unbound owner |
| RED-B01 | Server root Docker-human `BuildTime` and Engine RFC3339 `BuildTime` with the same civil second and zero fraction | Old generic comparator emits field conflict; new comparator emits `FORMAT_EQUIVALENT_CIVIL_SECOND` |
| RED-B02 | Same recognized families with different civil seconds | Must retain `DOCKER_SERVER_FIELD_CONFLICT` |
| RED-B03 | Human seconds paired with a nonzero RFC3339 fraction | Must fail closed because the human surface cannot verify that precision |
| RED-B04 | Invalid weekday, unsupported offset/format, missing-both, duplicate Engine component, or conflicting API alias | Existing field-specific fail-closed behavior remains |
| RED-S01 | Every positive and negative fixture scanned for raw path, command line, address, proxy, daemon ID, stdout/stderr, and argv leakage | Zero forbidden fields/tokens; only closed enums and hashes persist |
| RED-D01 | Permuted input row order and repeated serialization | Canonical output bytes and failure ordering are deterministic |

If any proposed positive fixture is already GREEN on frozen bytes, or any negative fixture becomes GREEN, stop with `HANDOFF_INCOMPLETE`; the assumed seam or remediation is wrong.

## Green acceptance criteria

The dormant Attempt-013 packet is eligible for central validation only when all of the following are true:

1. The RED observations above were captured before implementation and the intended fixtures turn GREEN only through the new versioned seam.
2. Every negative/mutation fixture remains fail-closed with a stable, non-sensitive locator.
3. Frozen Attempt-008, Attempt-009, Attempt-010, Attempt-012, and all four Attempt-012 runtime receipts are byte-identical and unmodified.
4. The retained offline suites pass unchanged; the new suites contain no skip, xfail, expected-failure, network call, runner import/invocation, Docker/WSL/Hyper-V command, or host PowerShell probe.
5. Strict JSON, Python AST, exact schema/field sets, canonical ordering, duplicate-key rejection, non-finite rejection, and privacy scans all pass.
6. D01 parent-unresolved success still requires complete direct identity for both required process names.
7. D02 success still requires exact TCP owner binding to the validated direct-identity index.
8. `BuildTime` equivalence is limited to the closed rules above; every other cross-surface conflict still fails.
9. The Attempt-013 model predicate requires `gpt-5.6-sol` with requested default-Standard throughout: `ultra` for critical central adjudication, central validation, fresh audit, exact-command adjudication, and post-execution adjudication; `xhigh` for bounded implementation/static regression and the one-shot execution. Positive Fast/Priority evidence is terminal; service tier/speed telemetry that is unavailable is recorded exactly as `UNOBSERVABLE`.
10. The candidate output root is absent, the worktree is clean, the exact packet write set matches, and runtime/host command count remains zero.
11. `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, and benchmark admission remains closed in every static artifact.

Passing these criteria proves only that the dormant remediation packet is internally consistent. It does not prove the current host admissible.

## Exact write sets for central

### This planning stage

Exactly one added file and no other write:

`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt012_runtime_failure_remediation_plan.md`

### Proposed Attempt-013 implementation packet

After central adjudicates this plan, the implementation packet may add exactly these ten files; names are reserved here to prevent Attempt-012 reuse or parallel schema authorities:

1. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py`
2. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract.json`
3. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/test_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py`
4. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_pre_runtime_authority.py`
5. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract.json`
6. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/test_e4_r6_pc2w_p1_attempt013_pre_runtime_gate.py`
7. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_admission_observation_contract.json`
8. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_execution_authorization.json`
9. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_attempt013_admission_observation.py`
10. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt013_static_packet.py`

The new runner may adapt the retained implementation only through the new compatibility and authority seams. It must not edit an old module or duplicate a second unbound policy source inside the runner.

### Gate receipt commits

After a complete central static replay, add exactly one file:

`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt013_central_static_validation_receipt.json`

After the fresh Ultra audit, add exactly one file:

`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt013_fresh_independent_audit_receipt.json`

### One-shot runtime write set

Only after all gates and exact-command confirmation, the process may create the previously absent `wave_av/E4_R6PC2W_P1_attempt013_admission_observation/` root with exactly:

1. `admission_observation.json`
2. `command_receipts.json`
3. `execution_receipt.json`
4. `handoff.json`

No `pipeline_state_stage1e.json`, scientific artifact, old receipt, old output root, or fifth runtime file belongs to these write sets. Any later pipeline-state adjudication is a separate central stage outside this plan.

## Mandatory gate sequence and handoff to central

### Gate 0 — Central adjudication and dormant implementation

- Adjudication owner: `gpt-5.6-sol` / `ultra`, requested Standard/default.
- Bounded implementation/static-regression owner after explicit adjudication: `gpt-5.6-sol` / `xhigh`, requested Standard/default.
- Start from the audited Attempt-012 receipt commit and this plan commit; verify single-parent lineage and clean state.
- Independently replay the four receipt blobs, source locators, exception-type hash, causal graph, and UNKNOWN boundaries.
- Accept or reject the parent-lineage and `BuildTime` comparison policies explicitly. Silence is not approval.
- Write and observe the RED fixtures before implementing the ten-file packet.
- Implement only the exact packet write set, then require the GREEN criteria.
- Failure disposition: `HANDOFF_INCOMPLETE`; no central validation receipt and no command proposal.

### Gate 1 — Central validation

- Owner: a central `gpt-5.6-sol` / `ultra` Standard/default context.
- Validate raw Git blobs, exact packet write set, schemas, model predicate, frozen hashes, RED-to-GREEN record, all negative fixtures, privacy scan, deterministic serialization, output-root absence, clean worktree, and zero runtime/host commands.
- Bind the packet commit and every packet/support blob by path, byte count, and SHA-256.
- Commit the central validation receipt as the sole file in its commit.
- Failure disposition: `HANDOFF_INCOMPLETE`; no fresh audit.

### Gate 2 — Fresh Ultra audit

- Owner: a fresh `gpt-5.6-sol` / `ultra` Standard/default context that treats implementer and central conclusions as claims to replay, not authority.
- Start at the central-receipt commit; verify its exact parent/packet ancestry and one-file delta.
- Recompute the causal, schema, test, privacy, model, command, frozen-byte, and exact-write-set checks from raw blobs.
- Record service tier/speed as `UNOBSERVABLE` when telemetry is unavailable; never infer Standard from latency. Any positive Fast/Priority signal fails.
- Commit the fresh audit receipt as the sole file in its commit and link the central receipt's raw SHA-256.
- Failure disposition: `HANDOFF_INCOMPLETE`; no confirmation request.

### Gate 3 — Exact command confirmation

- Owner: `gpt-5.6-sol` / `ultra` Standard/default.
- Recheck audit HEAD, clean worktree, absent Attempt-013 output root, exact interpreter identity, packet/receipt raw hashes, root containment, and unused Attempt-013 budget.
- Render a non-executable proposal with all placeholders resolved only at this gate:

```text
<ABSOLUTE_PYTHON> -B <ABSOLUTE_ATTEMPT013_RUNNER> --repo-root <AUTHORIZED_ROOT> --packet-commit <PACKET_COMMIT> --expected-head <FRESH_AUDIT_COMMIT> --central-validation-receipt <CENTRAL_RECEIPT_PATH> --central-validation-receipt-sha256 <CENTRAL_RAW_SHA256> --fresh-audit-receipt <AUDIT_RECEIPT_PATH> --fresh-audit-receipt-sha256 <AUDIT_RAW_SHA256> --execution-confirmation <NEW_ATTEMPT013_TOKEN>
```

- The user must newly confirm the exact tuple `(working directory, full argv)` after seeing the resolved values. No Attempt-012 confirmation or token transfers.
- Any post-confirmation byte, HEAD, path, hash, model, root, or argv change invalidates confirmation and returns to Gate 1 with a superseding packet; it does not authorize an execution.

### Gate 4 — One-shot execution

- Owner: `gpt-5.6-sol` / `xhigh`, requested Standard/default. Max, Fast, and Priority are not permitted by this plan.
- Invoke direct Python exactly once, without a shell wrapper, `-c`, `-m`, changed flags, alternate root, or modified arguments.
- The first process invocation consumes Attempt-013 even if it fails before Docker start or output-root creation.
- No retry, fallback, second interpreter, alternate compatibility profile, extra sleep, manual identity bypass, or second cleanup attempt is authorized.
- Preserve raw child versus outer-tool exit provenance separately, but persist sensitive streams only according to the sanitization contract.

### Gate 5 — Read-only post-execution adjudication

- Owner: a fresh `gpt-5.6-sol` / `ultra` Standard/default context; never the execution context acting as sole judge.
- Do not rerun or repair anything. Read only the immutable output packet and outer process receipt.
- Require exact four-file output, strict schemas, expected command IDs/counts, zero retry/fallback, independent identity completeness, stop/shutdown closure, stable A/B/C snapshots, final/baseline equality, privacy fields, and unchanged scientific truth.
- A PASS means only “admission observation complete for central evaluation.” Benchmark admission, materialization, training, evaluation, and TEST remain closed pending a separate central decision.

## Rejected alternatives

| Alternative | Rejection reason |
|---|---|
| Retry/replay Attempt-012 or reuse its output root/token | Attempt-012 ran once and consumed its entire budget; receipts explicitly require no automatic retry |
| Ignore D01, D02, or Docker identity to obtain PASS | Violates fail-closed identity admission and the explicit no-bypass requirement |
| Drop parent fields silently | Erases observed lineage uncertainty; the remediation instead uses an explicit closed union with strict self identity |
| Special-case `com.docker.backend` | Name-specific exception is brittle, hides the general snapshot assumption, and is indistinguishable from pass-seeking |
| Add sleeps, repeat process enumeration, or query the parent repeatedly | Timing-dependent, nondeterministic, expands runtime commands, and can mask rather than classify process churn |
| Treat D02 exit code `0` as semantic PASS | Raw D02 envelope is not retained and its validator was not reached; transport success is not identity success |
| Accept either `BuildTime` source without cross-check | Discards cross-surface integrity rather than repairing representation comparison |
| Relax all Docker root/Engine conflicts | Overbroad; only the representation-bearing `BuildTime` field has evidence for a field-aware comparator |
| Infer the missing `BuildTime` values from current tests or Docker examples | Raw values were intentionally not persisted; fixtures are not observations |
| Change RAM/vmem, restart services, reinstall/downgrade Docker, or alter daemon settings | No receipt supports those diagnoses; actions are out of scope and materially expand risk |
| Persist full raw stdout/stderr, paths, command lines, addresses, or daemon data | Violates the established privacy boundary; closed enums, facts, and hashes are sufficient for deterministic adjudication |
| Edit Attempt-008/009/012 implementation or receipts in place | Breaks frozen provenance and makes the consumed run non-auditable; remediation must be additive |

## Residual risks

1. The exact OS/provider reason for the absent parent row remains unknown; the new union classifies the observation but cannot prove parent lifecycle history.
2. Accepting complete self identity with unavailable parent lineage reduces lineage completeness. This is bounded by mandatory executable/signature/hash/creation/command-line evidence and must be explicitly adjudicated by central.
3. Docker-human time has no explicit timezone. `FORMAT_EQUIVALENT_CIVIL_SECOND` is representation equivalence only, not instant equivalence; a nonzero hidden fraction or different civil field remains fatal.
4. After fixing `BuildTime`, a different Docker server field may expose a genuine conflict. The new comparator must fail closed rather than generalize the exception.
5. D02's historical raw envelope cannot be recovered. Attempt-013 can provide better sanitized classification, but cannot retroactively upgrade Attempt-012 evidence.
6. The inherited wrapper chain is complex. Static order checks must prove the Attempt-013 compatibility and role-aware authority seams are installed before the retained legacy main and cannot be bypassed.
7. Service tier/speed may remain unobservable. This plan permits the literal `UNOBSERVABLE` record but forbids inferring it as positive Standard/default evidence.
8. A future host observation can still fail for legitimate identity, lifecycle, or closure reasons. Remediation readiness is not host-admissibility prediction.

## Rollback and no-retry policy

- Before Gate 4, any failed static gate stops the chain. Preserve the failed packet/receipt commits for audit and create a superseding packet only after a new central decision; do not rewrite historical bytes.
- No host cleanup is needed for Gates 0-3 because they must execute zero host/runtime commands.
- Once Gate 4 invokes the process, Attempt-013 is consumed. Preserve any output root byte-for-byte, including partial/failure receipts; never delete, overwrite, repair, or reuse it.
- The locked runner may perform only its one planned Docker stop and one WSL shutdown path. If either fails, do not issue an automatic second cleanup command; escalate to a separately authorized user-owned recovery stage.
- No failure authorizes retry, fallback, alternate root/interpreter, identity-check bypass, settings change, installation, or scientific work.
- `pipeline_state_stage1e.json` remains untouched by this plan and by the proposed packet/receipt commits. Any later state transition requires a separate, exact central adjudication after read-only post-execution review.

## Central handoff checklist

Central should accept this handoff only if it can independently confirm all of the following:

- [ ] Audited base `e28d6b69fb53c871903a523e07da4ae0086e925a` has parent `314d7c85c5a905d3951658745505e8dc685bb182` and exactly four added runtime receipts.
- [ ] All four receipt blob OIDs, byte counts, and SHA-256 values match this plan.
- [ ] Attempt-012 is consumed; no retry/fallback or benchmark/TEST continuation is proposed.
- [ ] D01 is the root of the D02 dependency edge; D02 is not mislabeled as an independent observed TCP failure.
- [ ] `BuildTime` is an independent root and its raw semantic relationship remains `UNKNOWN`.
- [ ] No RAM/vmem/daemon/Hyper-V/cleanup diagnosis is inferred.
- [ ] Parent-unavailable acceptance requires complete direct identity and a closed enum; it is not a name-specific bypass.
- [ ] TCP ownership binding remains exact and independently validated.
- [ ] `BuildTime` relaxation is field-specific, format-validated, zero-fraction bounded, source-attributed, and fail-closed on ambiguity.
- [ ] Privacy, deterministic-receipt, exact-write-set, and immutable-old-artifact rules are enforceable.
- [ ] The new runtime is numbered Attempt-013 with `wave_av`, new schemas/receipts/token/budget, and a role-separated model policy: Ultra for critical judgment/audit, XHigh for bounded implementation and one-shot execution.
- [ ] Gate order is central validation → fresh Ultra audit → exact command confirmation → one-shot execution.
- [ ] Requested service tier/display speed is default/Standard; unobservable telemetry is recorded as `UNOBSERVABLE`, and any positive Fast/Priority evidence is terminal.
- [ ] Current-stage exact write set contains only this plan file.

If any checkbox cannot be established from authoritative bytes, central must use `HANDOFF_INCOMPLETE` and keep execution and benchmark admission closed.

## Final truth state

- Plan verdict: `REMEDIATION_PLAN_READY_FOR_CENTRAL_ADJUDICATION`
- Attempt-012 verdict: `FAIL_CLOSED_PC2W_P1_ATTEMPT012_CURRENT_HOST_NOT_ADMISSIBLE`
- Attempt-012 retry/replay: forbidden and not performed
- Attempt-013: proposed only; not created, authorized, confirmed, or executed
- Docker/WSL/Hyper-V/host probes in this stage: `0`
- Network operations in this stage: `0`
- Materialization/preprocessing/training/evaluation/benchmark/TEST operations in this stage: `0`
- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- Benchmark admission: closed
- Current-stage exact write set: one Markdown plan file
