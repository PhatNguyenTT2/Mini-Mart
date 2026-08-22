# R6-M0/R6-M1 central materialization execution contract

Date: 2026-08-23

## Authority and entry gate

This contract implements only the materialization scope explicitly approved at R5-M2 and frozen at R6-G0. Execution may start only after the central R6-C1 validator returns:

`PASS_R6_C1_EXACT_COMMAND_PACKET_READY_FOR_BOUNDED_R6_M0_R6_M1`

The dispatch created after that PASS must freeze the raw and canonical-LF byte count and SHA-256 of all five R6-C1 artifacts, this contract, the validator, and the C1 validation receipt. Any byte change closes the gate.

## Context and model

R6-M0 and R6-M1 are central mechanical execution stages. They run in the current central context with Sol Max Standard. They are not delegated because the stage map assigns command admission and execution custody to central.

R6-M0 and R6-M1 may run concurrently, but each packet is strictly sequential and the aggregate active command count is at most two. R6-B0, the installed-package data bridge, is sequential and remains blocked until both materialization lanes have successful central receipts.

## Exact external roots

- R6-M0: `E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6\official_source\grouplens_ml100k\attempt-001`
- R6-M1/R6-B0: `E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6\recbole_bpr_ml100k_py3119_cpu\attempt-001`

Both roots must be absent before execution. Existing attempts are never repaired, merged, overwritten, cleaned or reused. Every existing ancestor from `E:\UIT\cv` down to the first absent component must be a real directory and not a link, junction or reparse point.

No materialized dataset or environment byte is copied into Git. Repository artifacts contain only small control records, output fingerprints and external locators; they never vendor the dataset archive, raw release, atomic interaction file, installer, wheelhouse, environment or bridge bytes.

## Literal command runner

The central runner must:

1. replay the frozen R6-C1 packet hashes before creating either attempt root;
2. pass each command as a literal argv array with `shell=false` and the packet's exact working directory;
3. use only packet-declared environment overrides and a centrally sanitized base environment;
4. remove ambient `PYTHONPATH`, `PYTHONHOME`, `VIRTUAL_ENV`, Conda, CUDA, pip index/config/trusted-host and HTTP(S)/ALL proxy variables;
5. set deterministic non-scientific process controls such as `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, noninteractive pip, and UTF-8 mode only where they do not alter a packet-frozen artifact identity;
6. enforce the per-command timeout and stop the packet on the first nonzero exit, timeout, resource breach, reparse point, unexpected write-root escape or receipt mismatch;
7. execute no automatic retry. Zero retries is within the packet's maximum; any failed attempt remains immutable evidence;
8. capture command ID, exact argv hash, start/end UTC, elapsed seconds, exit code, stdout/stderr byte count and SHA-256, timeout state and observed attempt-root bytes without treating stdout as scientific evidence; and
9. never execute a command that fails the independent forbidden-execution scanner.

The runner must not invoke a shell to reconstruct commands. PowerShell is allowed only where it is itself the literal packet executable with a frozen `-Command` token.

## Ambient-state and installer limitation

The packet itself disables curl configuration/proxy inheritance and uses pip isolated mode. The runner repeats environment sanitization as defense in depth.

The official CPython full installer may create Windows-managed installer or registry state that is not a research artifact. The central receipt must distinguish the external environment tree from OS-managed state and must not claim full machine hermeticity unless a pre/post observation proves it. Any observed pipeline-controlled filesystem write outside the two exact external roots fails closed. Unobservable Windows-managed state is carried to R6-A1 as an explicit reproducibility limitation rather than silently labeled verified.

## R6-M0 success conditions

R6-M0 succeeds only if all eight dataset commands return zero and central post-validation independently replays:

- exact official archive URL, current provider sidecar body and MD5;
- archive byte count `4,924,029` and locally computed archive SHA-256;
- exact 23-member safe extraction inventory, regular-file and containment rules;
- exact `u.data` row/user/item cardinalities;
- one and only one canonical `ml-100k.inter` with 100,000 data rows;
- ordinal raw-to-atomic field equality and projection digest equality;
- first-occurrence user/item mapping receipt hashes; and
- no repository, harmonized-v5, RecBole S3, Dataset, split, metric, training, evaluation or TEST access.

## R6-M1 success conditions

R6-M1 succeeds only if all 25 environment commands return zero and central post-validation independently replays:

- official installer MD5, local installer/Sigstore SHA-256 and Authenticode `Valid`;
- exact local CPython 3.11.9 AMD64 and venv interpreter identity;
- exact source revision/tree and immutable 265-file source-staging hash replay;
- the verified ephemeral build copy and post-build unchanged staging proof;
- binary-only CPU wheelhouse, exact URLs/hosts/tags/sizes/SHA-256 and hash-locked offline install;
- exact twenty direct requirements, locally built RecBole 1.2.1 wheel source binding, `pip check`, inventory and import/version/CPU assertions;
- read-only in-memory syntax checks with no source-staging bytecode/build additions; and
- no PyPI RecBole, sdist, editable/VCS fallback, CUDA, Hyperopt, worker, training, evaluation or TEST execution.

## R6-B0 bridge conditions

R6-B0 remains closed until separate R6-M0 and R6-M1 central receipts both pass. It then runs the exact three-command bridge packet sequentially. It may create only one byte-identical `ml-100k.inter` in the previously absent installed-package target plus the two external receipts. The config check may instantiate `Config`; it may not construct or load `Dataset`, read interaction rows, trigger S3 or calculate any metric.

## Failure and next gate

Any failed lane remains a failed immutable attempt. Central records the failure and stops; it does not clean or retry in place. R6-A1 opens only after R6-M0, R6-M1 and, when executed, R6-B0 have passed central post-validation.

R6-A1 uses a fresh Sol XHigh Fast context and may return PASS, FAIL or CANNOT_VERIFY. Only central R6-G1 can decide whether the substrate is ready for a separate experiment-execution proposal. R6-G1 still cannot authorize training, evaluation or TEST without a new explicit user checkpoint.

Persistent truth remains:

```text
RESULT_STATUS = NOT_RUN
TEST_SET_OPENED = NO
ACCEPTED_RESULT_ROWS = 0
execution_authorized = false
project_benchmark_numbers = INVALID_FOR_PAPER
```
