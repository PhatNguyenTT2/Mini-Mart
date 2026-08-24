# E4-R6-PC2W-P1 prospective residual-process admission policy

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: validate
- Origin Date: 2026-08-25T00:00:00+07:00
- Verification Status: ANALYZED
- Version Label: stage1e_e4_r6_pc2w_p1_prospective_residual_process_admission_policy_v1
- Upstream Dependencies: stage1e_e4_r6_pc2w_p1_attempt004_failure_receipt_v1; stage1e_e4_r6_pc2w_p1_official_source_evidence_register_v1
- Repro Lock: null
- Experiment Intake Declaration: no_experiments_declared by scholar at 2026-08-25T00:00:00+07:00

## Decision

`POLICY_RELAXATION_DENIED_ATTEMPT004_REMAINS_FAIL_CLOSED`.

Attempt-004 is immutable and remains non-admissible. The two post-stop snapshots record only the unique base name `wslrelay`; they do not record process count, PID, parentage, executable identity, signature, age, socket ownership, or PID continuity. A later observation cannot repair that evidence gap.

Microsoft's official documentation establishes that `wslrelay.exe` is a legitimate WSL component created by `wslservice.exe` and can participate in port forwarding. It does not establish that a surviving process is healthy, unrelated to the just-stopped runtime, or permitted to remain for a documented interval. Docker documents synchronous `docker desktop stop` behavior but does not define a Windows WSL process-closure SLA. User-filed WSL issues are risk signals, not normative specifications; they nevertheless make a name-only allowlist unsafe.

## Normative rules for a future current-host attempt

This policy does not authorize Attempt-005. A new attempt requires an explicit user decision, a fresh immutable output root, a frozen command contract, and an independent static audit before execution.

1. `wslrelay.exe` MUST NOT be allowlisted solely by name.
2. The pre-start native gate MUST pass before Docker Desktop is started: all WSL distributions stopped, running inventory empty, Docker Desktop Linux named pipe absent, and target runtime process population empty.
3. Docker Desktop start MUST occur at most once and `docker desktop stop` MUST occur exactly once in `finally`, synchronously, without `--detach`.
4. After Docker Desktop stop, a separately authorized `wsl --shutdown` MUST occur exactly once. It is a runtime mutation and therefore cannot be inferred from this policy review.
5. The final closure gate MUST use at least three fixed snapshots after the shutdown command, with frozen settling and barrier intervals.
6. Every target process row MUST record PID, PPID, executable path hash, file SHA-256, Authenticode signer/status, creation time, command-line hash, and redacted TCP ownership. Raw command lines, remote addresses, proxy values, and secrets MUST NOT be persisted.
7. WSL verbose inventory MUST show all distributions stopped; WSL running inventory MUST be empty; the Docker Desktop Linux named pipe MUST be absent with the exact accepted Win32 absence code; container and image inventories MUST remain unchanged; container/image events MUST remain absent.
8. Final target runtime process population MUST be empty. A signed Microsoft binary, an expected path, or no visible TCP listener is supporting evidence only and MUST NOT override a non-zero final process population.
9. Any parser ambiguity, missing field, process turnover, non-zero residual target process population, unexpected event, inventory mutation, timeout, or command failure MUST yield fail-closed.
10. There MUST be no automatic retry, fallback, force-kill, service restart, settings change, install, download, image pull/build, container create/run, materialization, training, evaluation, benchmark admission, or TEST access.

## Why `wsl --shutdown` is proposed

Microsoft documents `wsl --shutdown` as immediately terminating all running distributions and the WSL 2 lightweight utility virtual machine. Attempt-004 only stopped Docker Desktop and then observed WSL state; it did not execute this explicit WSL utility-VM shutdown. A future attempt can therefore test a stronger, documented closure operation without weakening the zero-residual gate.

This is not a guarantee that the current host will pass. It is a bounded method to distinguish a Docker-stop-only residual from a residual that survives the documented WSL shutdown boundary.

## Required decision checkpoint

The user must choose one of the following before any runtime command is created or executed:

- authorize one new instrumented Attempt-005 on the current host, including exactly one synchronous Docker Desktop stop and exactly one `wsl --shutdown` after stop;
- select a changed host and commission a fresh read-only preflight;
- pause Phase 1E.

Until that decision, R6 materialization, official RecBole/BPR reproduction on MovieLens 100K, harmonized v5 training, external validation, benchmark admission, and TEST access remain blocked.

## Truth state

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- Project benchmark numbers remain `INVALID_FOR_PAPER`.
