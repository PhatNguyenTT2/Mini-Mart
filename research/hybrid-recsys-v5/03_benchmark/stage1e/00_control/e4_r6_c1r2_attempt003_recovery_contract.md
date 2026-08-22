# E4 R6-C1R2 attempt-003 recovery contract

## Objective

Produce a new, proposal-only five-file command packet for bounded R6 dataset and environment materialization after attempt-002 failed closed. The packet must create only new `attempt-003` roots. It must not execute materialization, construct or load a RecBole Dataset, train, evaluate, open TEST, calculate metrics, or admit benchmark rows.

## Entry evidence

- Attempt-002 failure receipt: `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_m0_m1_attempt_002_failure_receipt.json`.
- Independent recovery audit: `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_c1r2_recovery_audit_receipt.json`.
- Prior attempt-002 packet is historical evidence only. Do not edit or reuse its roots.
- Retain both attempt-001 and attempt-002 roots immutable.

## Exact outputs

Write exactly these five strict-JSON files under:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/E4_R6C1R2_attempt003_command_packet/`

1. `dataset_materialization_packet.json`
2. `environment_materialization_packet.json`
3. `recbole_dataset_bridge_packet.json`
4. `execution_boundary_and_negative_assertions.json`
5. `audit_handoff.json`

Do not modify any other path.

## Attempt roots and pairing

- Dataset root: `E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6\official_source\grouplens_ml100k\attempt-003`
- Environment root: `E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6\recbole_bpr_ml100k_py3119_cpu\attempt-003`
- Runtime: `<environment-root>\runtime\python.exe`
- Venv: `<environment-root>\venv`
- Bridge: dataset attempt-003 to environment attempt-003 only. Cross-attempt pairing is forbidden.

Every root-creation command must require the exact target to be absent, reject repository-contained roots, and reject reparse-point ancestors. No cleanup, overwrite, retry-in-place, or fallback path is allowed.

## Dataset correction

Preserve the official GroupLens MovieLens 100K URLs, checksums, safe ZIP-name checks, extraction bounds, byte-level conversion contract, and reconciliation logic from C1R1, changing all roots to attempt-003.

In M05, do not call `HashSet[string]::new($names, comparer)`. Construct each HashSet with `[StringComparer]::Ordinal` only and add every explicitly cast string with `Add()`. Include a proposal-time isolated capability assertion showing that the selected pattern works under the exact pinned PowerShell 7.6.4 executable. Extraction must remain fail-closed on traversal, rooted paths, drive-qualified paths, alternate-data-stream colons, symlink entries, reparse points, duplicate names, case collisions, unexpected inventory, per-member size, and aggregate uncompressed size.

## Environment source lock

Replace the Windows installer EXE flow entirely with inert direct acquisition and safe extraction of the official CPython NuGet package:

- Package ID: `python`
- Version: `3.11.9`
- URL: `https://api.nuget.org/v3-flatcontainer/python/3.11.9/python.3.11.9.nupkg`
- Registration leaf: `https://api.nuget.org/v3/registration5-semver1/python/3.11.9.json`
- Catalog leaf: `https://api.nuget.org/v3/catalog0/data/2024.04.02.13.14.51/python.3.11.9.json`
- Publisher: `Python Software Foundation`
- Published: `2024-04-02T13:09:41.627Z`
- Bytes: `17478009`
- MD5: `0deb9c5d73bc95ca7b66dd72b0f8d8a2`
- SHA-256: `9283876d58c017e0e846f95b490da3bca0fc0a6ee1134b2870677cfb7eec3c67`
- Catalog SHA-512, Base64: `41On79FZ75irnOEBGFSjDV13j1nZb8m7EbB87SmQs1XwMEhrBwf3mMc8RCAXOrERh2qW6tWYFxi2BMTN1xxVjQ==`

Fetch registration and catalog metadata as separately retained provenance. Require their identity fields, package URL, ID, version, author, package size, and package SHA-512 before promoting the `.nupkg.partial` bytes. Independently verify byte count, MD5, SHA-256, and SHA-512.

Treat `.nupkg` as ZIP data only. Safe-scan all entries before extraction. Reject traversal, rooted or drive-qualified names, backslashes when the archive contract requires forward slashes, ADS colons, symlink or unsupported Unix file types, duplicate/case-colliding entries, reparse points, per-member or total expansion-limit breaches, and missing required anchors. Required anchors include `python.nuspec`, `.signature.p7s`, `tools/python.exe`, `tools/python311.dll`, `tools/Lib/venv/__init__.py`, and pip under `tools/Lib/site-packages/`.

Extract to a staging directory, verify a deterministic complete inventory, then promote only the verified `tools` tree to `runtime`. Preserve the package, registration metadata, catalog metadata, nuspec, signature entry, and inventory receipts. Do not execute any downloaded executable during acquisition or extraction.

## Prohibited runtime mechanisms

The packet and later runner must reject or contain no invocation of:

- the CPython Windows installer, Burn, MSI or `msiexec`;
- ambient `python`, `python3`, `py`, or Python resolved from PATH;
- `nuget.exe`, `winget`, Microsoft Store installation, `uv python install`, Conda, or an embeddable ZIP bootstrap;
- downloaded executable tools during source acquisition or safe extraction.

Only the hash-verified `<environment-root>\runtime\python.exe` may execute after runtime promotion and identity verification.

## Runtime, venv, and package invariants

Before venv creation, prove CPython 3.11.9, 64-bit Windows, `cp311-cp311-win_amd64`, exact `sys.executable`, exact `sys.prefix == sys.base_prefix == runtime`, and pip plus venv availability from the promoted runtime. Create the venv only with that runtime.

After venv creation, prove the venv executable, `sys.prefix`, `sys.base_prefix`, `pyvenv.cfg home`, package paths, wheelhouse, build staging, and receipts resolve under the exact attempt-003 environment root. Preserve all prior C1R1 package pins, source-commit locks, wheel-only constraints, deterministic build inputs, local RecBole wheel provenance, and package inventory checks unless the NuGet runtime requires a mechanically justified path adjustment.

No package command may read ambient pip configuration, proxy settings, cache, user site, `PYTHONPATH`, `PYTHONHOME`, or another interpreter. Network hosts must remain explicit and minimal.

## Runner contract recorded in the packet

The handoff and boundary files must require the later central runner to:

1. execute literal argv without shell reconstruction;
2. catch process-launch `OSError` and `FileNotFoundError`;
3. persist an append-only command journal after every command;
4. verify declared required outputs and postconditions before advancing;
5. enforce the command and lane write sets;
6. snapshot and hash specified ambient Python registry keys and known system/user Python filesystem sentinels before and after every environment command;
7. fail closed on any sentinel change, any write outside the attempt root, repository mutation, timeout, memory/disk bound, unexpected network host, or missing output;
8. perform no automatic retry, cleanup, rollback, or fallback.

## Bridge and scientific boundary

Bridge commands remain blocked until separate central PASS receipts exist for both attempt-003 lanes. The bridge may byte-copy only the canonical `.inter` file into the exact installed RecBole example-data path and perform a Config-only path resolution check. It may not instantiate or load a Dataset or read data rows for scientific evaluation.

The packet must preserve these negative assertions:

- `RESULT_STATUS = NOT_RUN`
- `TEST_SET_OPENED = NO`
- `ACCEPTED_RESULT_ROWS = 0`
- no training, evaluation, metrics, comparison, or benchmark admission;
- project benchmark numbers remain invalid for paper use.

## Model and review gate

- Packet assembler: Sol High Fast (`gpt-5.6-sol`, high, priority).
- Central validator and dispatch: Sol Max Standard.
- No attempt-003 root may be created until all five outputs pass strict JSON, path/pairing, command-order, literal-argv, source-lock, syntax, prohibited-token, postcondition, write-set, sentinel, and scientific-boundary validation and a new central receipt and dispatch are committed.
