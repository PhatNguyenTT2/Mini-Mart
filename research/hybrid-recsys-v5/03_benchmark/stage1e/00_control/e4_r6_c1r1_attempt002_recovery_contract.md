# R6-C1R1 / attempt-002 recovery contract

Date: 2026-08-23

## Purpose and authority

R6-M0/R6-M1 `attempt-001` stopped fail-closed before extraction, installation, conversion or any scientific execution because the packet used the ambient token `powershell.exe`. Under the central runner's sanitized environment, that token selected Windows PowerShell 5.1 and automatic discovery did not expose `Get-FileHash`. The immutable failure evidence is recorded in:

`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_m0_m1_attempt_001_failure_receipt.json`

This recovery does not repair, clean, promote or reuse either `attempt-001` root. It creates a new command packet and, only after a new central PASS, may create two new `attempt-002` roots under the same user-approved materialization scope.

## Context and model assignment

- Packet regeneration is bounded mechanical work: fresh worker, Sol High Fast.
- Exact packet validation, dispatch freeze and materialization custody remain in the current central context: Sol Max Standard.
- A later independent materialization audit remains Sol XHigh Fast.

The worker has no authority to execute commands, use the network, touch external attempt roots or decide scientific policy.

## Immutable inputs and outputs

The validated R6-C1 packet under `wave_ai/E4_R6C1_materialization_command_packet` remains unchanged evidence. R6-C1R1 writes exactly five new JSON files under:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_aj/E4_R6C1R1_attempt002_command_packet`

The recovery packet must preserve the validated command cardinalities:

- dataset lane: 8 commands;
- environment lane: 25 commands;
- bridge lane: 3 commands;
- total: 36 literal-argv commands.

Every `attempt-001` locator in executable commands, write sets, receipts and scan surfaces becomes the corresponding `attempt-002` locator. No path may point back to either failed root.

## Control-plane executable lock

Every command previously represented by `powershell.exe` must use this exact absolute executable in both `executable` and `argv[0]`:

`C:\Users\ACER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe`

The central preflight must verify, before either attempt root is created:

1. the executable is a regular non-reparse file;
2. byte count is `301368`;
3. SHA-256 is `db6dd81183fe57d22e03b911ec9a30a2fd7c40542e97743615355a6fb44f458f`;
4. engine version is exactly `7.6.4`;
5. `Get-FileHash` resolves from `Microsoft.PowerShell.Utility`;
6. `Get-AuthenticodeSignature` resolves from `Microsoft.PowerShell.Security`; and
7. the capability process exits zero under the same sanitized environment used for packet commands.

Failure of any item closes the gate before external root creation. No fallback to ambient `powershell.exe`, module-path editing, in-place packet repair or automatic retry is allowed.

## Central validation requirements

The R6-C1R1 validator must independently establish at least:

- exactly five strict JSON outputs and no extra file;
- output paths are `attempt-002`, while the failed `attempt-001` locators are absent from executable commands and write sets except explicit historical provenance;
- all 36 commands satisfy `argv == [executable, ...arguments]` with recomputed canonical argv hashes;
- every PowerShell command uses the exact locked `pwsh.exe` path;
- dataset/environment/bridge dependency order and counts remain unchanged;
- network hosts, URL pins, hash checks, source staging protections, timeout/resource bounds and zero-retry semantics remain no weaker than validated R6-C1;
- the attempt-001 failure receipt and all inherited scientific freeze artifacts replay byte-for-byte;
- no command or semantic scan surface contains Dataset construction/loading, preprocessing, training, evaluation, metric calculation, hyperparameter search, TEST access or benchmark admission; and
- both `attempt-002` roots are absent at validation and dispatch freeze.

The only execution-ready verdict is:

`PASS_R6_C1R1_ATTEMPT_002_PACKET_READY_FOR_BOUNDED_R6_M0_R6_M1`

Otherwise the verdict is:

`FAIL_R6_C1R1_REWORK_REQUIRED`

## New execution attempt

After central validation, a new immutable dispatch and runner must be created for:

- R6-M0: `E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6\official_source\grouplens_ml100k\attempt-002`
- R6-M1/R6-B0: `E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6\recbole_bpr_ml100k_py3119_cpu\attempt-002`

R6-M0 and R6-M1 may run in parallel only after one central preflight passes. Commands remain sequential within each lane, aggregate concurrency remains at most two, and retries remain zero. R6-B0 stays blocked until separate successful R6-M0 and R6-M1 receipts exist and pass central post-validation.

## Scientific boundary

This recovery authorizes no RecBole `Dataset` construction or load, preprocessing, training, evaluation, metric computation, TEST access, checkpoint acceptance or paper benchmark admission. It only recovers the already-approved dataset/environment materialization substrate.

Persistent truth remains:

```text
RESULT_STATUS = NOT_RUN
TEST_SET_OPENED = NO
ACCEPTED_RESULT_ROWS = 0
execution_authorized = false
project_benchmark_numbers = INVALID_FOR_PAPER
```

The failed attempt remains evidence, not a benchmark result and not a materialization success.
