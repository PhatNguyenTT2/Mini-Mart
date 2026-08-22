# E4 R6-PC0 MXC containment feasibility contract

Date: 2026-08-23  
Status: FROZEN PROPOSAL — execution requires a committed runner and dispatch  
ARS workflow: `experiment-agent`, fail closed

## Purpose

R6-C1R2 passed static packet validation but failed a later packet-to-runner compatibility audit. Before revising the attempt-003 packet, R6-PC0 must determine whether this Windows host has a containment backend capable of enforcing process-tree filesystem and network boundaries without silently falling back to host DACL mutation, firewall mutation, permissive learning mode, or argv-only observation.

This is control-plane feasibility work only. It must not construct or load a Dataset, train, evaluate, compute metrics, access TEST, admit a benchmark, or create either attempt-003 data/environment root.

## Frozen Microsoft source

- Repository: `https://github.com/microsoft/mxc`
- Tag: `v0.7.0-rc1`
- Annotated tag object: `d1ed7f29b5e0574602c2cf289db7144e49a4de36`
- Commit: `0e02a720e32416b151dbcb0a00e3d4ac2b891559`
- Commit signature reported valid by GitHub; annotated tag is unsigned.
- Release ID: `338912027`; prerelease: `true`; immutable flag: `false`.
- Asset ID: `446369484`
- Asset: `mxc-release-binaries.zip`
- URL: `https://github.com/microsoft/mxc/releases/download/v0.7.0-rc1/mxc-release-binaries.zip`
- Bytes: `180948670`
- SHA-256: `450ad608bd2268a8cbe126597be209601c51fbfe36141cec08abb017e828aba5`

The release metadata is mutable at the provider level, so identity is anchored to the exact asset bytes and commit. A changed asset is a hard failure; it is not accepted as an update.

Primary documentation:

- `https://github.com/microsoft/mxc`
- `https://github.com/microsoft/mxc/blob/main/docs/process-container/os-version-support.md`
- `https://github.com/microsoft/mxc/blob/main/docs/host-prep.md`
- `https://learn.microsoft.com/en-us/windows/win32/secauthz/createprocessinsandbox`

MXC is an early preview. Its README warns that current profiles may be overly permissive and should not yet be treated as security boundaries. R6-PC0 therefore admits only an exact host-specific capability result with no policy weakening; source reputation alone is insufficient.

## Immutable external root

Only this root may be created:

`E:\UIT\cv\materialized-tools\hybrid-recsys-v5\stage1e\r6\mxc_v0_7_0_rc1\attempt-001`

The exact root must be absent. Existing ancestors from `E:\UIT\cv` downward must be ordinary non-reparse directories. Repository-contained roots, cleanup, overwrite, retry in place, fallback roots and reuse are forbidden. A failed root is retained immutable with a failure receipt.

Permitted children are `download`, `extract-staging`, `package`, `receipts`, and `probe`. No other root is writable.

## PC0-S0 preflight

Before root creation, the runner must:

1. replay raw bytes and SHA-256 for this contract, the C1R2 static receipt, compatibility audit receipt, all five packet files and the active Standard model policy;
2. require a clean repository and preserve its exact status before/after;
3. prove the dataset and environment attempt-003 roots remain absent;
4. verify free disk space against the declared archive and extraction bounds;
5. verify exact external-root absence and non-reparse ancestry;
6. use no ambient Python for any downloaded executable;
7. record Windows build `10.0.26200.0` and the read-only presence/export facts for `processmodel.dll`.

## PC0-M0 inert materialization

The runner may then execute a sequential, no-retry source-materialization lane:

1. create the exact external root and declared ordinary directories;
2. download the exact release asset to `download/mxc-release-binaries.zip.partial`, allowing HTTPS only and retaining response headers and final URL;
3. require exact byte count and SHA-256 before promoting to `download/mxc-release-binaries.zip`;
4. safe-scan the complete ZIP before extraction, rejecting rooted, drive-qualified, traversal, backslash, ADS-colon, NUL, duplicate/case-colliding, symlink, reparse, unsupported file-type, unexpected directory, member-size, total-size and entry-count violations;
5. extract with create-new semantics to `extract-staging`, verify a deterministic complete inventory, and locate exactly one x64 `wxc-exec.exe` payload plus its required sibling runtime files;
6. require valid Windows Authenticode status for every executable or DLL in the selected runtime payload and retain signer, certificate thumbprint, timestamp status, byte count and SHA-256;
7. promote only the verified selected runtime subtree to `package` and retain archive, inventory, signature and source-provenance receipts.

Downloaded executables must not run during acquisition, scan, extraction, hashing or signature verification.

Bounds:

- archive bytes exactly `180948670`;
- at most `50000` ZIP entries;
- at most `536870912` bytes per entry;
- at most `4294967296` aggregate uncompressed bytes;
- hard materialization timeout `1800` seconds;
- parent-process resident-memory bound `1073741824` bytes;
- no automatic retry.

## PC0-P0 read-only capability probe

Only after PC0-M0 passes may the exact hash-verified, Authenticode-valid x64 `wxc-exec.exe` run with its documented `--probe` detection-only path. Microsoft documents this probe as read-only. No sandbox workload, audit/permissive mode, host preparation, DACL mutation, firewall mutation, WPR, PktMon, cleanup helper or UAC-elevated helper may run.

Before and after the probe, retain canonical hashes for:

- repository status;
- both absent attempt-003 roots;
- the external tool root inventory;
- security descriptors of the external tool root and declared repository inputs;
- ambient Python registry/filesystem sentinels from the C1R2 packet;
- processmodel DLL bytes and relevant exported-symbol facts.

Capture stdout, stderr, exit code, elapsed time and binary argv hash. An `OSError` or `FileNotFoundError` must be journaled and stops the stage.

## Admission gate

`PASS_R6_PC0_NATIVE_CONTAINMENT_CANDIDATE` requires all of the following:

- exact source bytes and valid signatures;
- `wxc-exec --probe` exit code zero and parseable capability evidence;
- a native BaseContainer/PSEC/T1-equivalent tier, not AppContainer+DACL T3 or BFS T2;
- no recommendation or requirement for `wxc-host-prep`, DACL ACE changes, firewall changes, elevation, permissive learning mode, or cleanup;
- filesystem read-write/read-only policy support and default-deny outside explicit grants;
- kernel default-deny network for network-disabled commands;
- a supported fail-closed mechanism for the required outbound host allowlist/proxy, with no allow-all degradation;
- no sentinel, ACL, repository or attempt-root mutation caused by the probe.

Symbol presence alone is not a pass. Unknown, unavailable, fallback, degraded, warning-only or unparseable capability states fail closed.

If generic probe output cannot prove policy-specific filesystem and host-filter controls, the result is `INCOMPLETE_REQUIRES_SEPARATE_EXPLICITLY_AUTHORIZED_NONSCIENTIFIC_TOY_CONTAINMENT_TEST`, not PASS. That later test may create an AppContainer profile or other durable control-plane state and therefore requires a separate authority checkpoint.

## Gate effects

On PASS or INCOMPLETE, central validation records a receipt before any C1R3 packet work. On failure, the external PC0 root is retained immutable and attempt-003 remains blocked.

R6-C1R3 may begin only after PC0 establishes a feasible containment mechanism. C1R3 must add a typed mutation schema, per-command temp roots, a separate runner-control journal root, machine-verifiable postcondition adapters, explicit E18 preparation command, canonical sentinels and network policy evidence.

## Model policy

- PC0 bounded implementation: Sol High Standard.
- PC0 independent admission audit: Sol XHigh Standard.
- Central validation and state transition: Sol Max Standard.
- Fast/priority profiles are forbidden for newly created agents.

## Locked truth state

- `RESULT_STATUS = NOT_RUN`
- `TEST_SET_OPENED = NO`
- `ACCEPTED_RESULT_ROWS = 0`
- project benchmark numbers remain invalid for the paper.
