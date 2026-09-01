# Phase 1E Minimal Execution Rebaseline

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-01T00:00:00+07:00
- Verification Status: UNVERIFIED
- Version Label: stage1e_minimal_execution_rebaseline_v1
- Upstream Dependencies: [stage1e_e4_r6_c1r3_linux_packet_v1, stage1e_e4_r6_c1r3_linux_materialization_runner_v2, ars_codex_academic_research_suite_0.1.26]
- Repro Lock: null
- Experiment Intake Declaration: experiments_declared; declared_by=scholar; declared_at=2026-09-01T00:00:00+07:00

## 1. Decision and objective

Phase 1E is rebaselined at the execution layer only. Existing source, dataset,
metric, packet, failure, and audit evidence remains immutable and is not deleted.
The previous pre-runtime receipt chain is retained as history but no longer gates
this lane.

The immediate objective is to obtain, in order:

1. a live Docker daemon PASS on the current host;
2. a complete GroupLens ML-100K and Linux/CPU RecBole environment materialization;
3. one audited official RecBole BPR/ML-100K reproduction row;
4. only then, admission to the harmonized project-dataset benchmark.

This rebaseline does not weaken scientific comparability. It removes redundant
pre-execution orchestration while preserving source, dataset, evaluator, seed,
split, metric, and artifact provenance.

## 2. Frozen scientific inputs

The following inputs remain authoritative:

- implementation: RecBole v1.2.1 at commit
  `9a6f63d8d4a5b989fe27955a833f813a6d86041e`;
- official dataset: GroupLens MovieLens 100K from the provider-bound source;
- official reference target: BPR on ML-100K, README NDCG@10 `0.2768`;
- reference tolerance: `max(0.005, 5%) = 0.01384`, giving the preregistered
  interval `[0.26296, 0.29064]`;
- scientific truth before execution:
  `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`,
  `ACCEPTED_RESULT_ROWS=0`, and `phase_1e_complete=false`.

The existing project dataset is not modified during this lane. Its approximately
5,000 users, 5,200 items, and 1.37% density are evaluated only after the official
reproduction proves that the implementation and evaluator can run correctly.

## 3. Minimal gate policy

Only three gates are permitted before an official reproduction result:

1. **Static preflight**: exact Git HEAD, clean tracked state, required files,
   hashes, absent destination root, disk capacity, and the existing unit/packet
   validators.
2. **One runtime attempt**: literal command execution, no fallback, no retry,
   bounded timeout, process-alive monitoring, and append-only output.
3. **Post-run validation**: required output set, strict JSON parsing, hashes,
   negative scientific assertions, and result verdict.

A fresh independent audit is performed after runtime output exists. It is not a
prerequisite for creating a smoke or materialization attempt. This prevents an
audit/provider failure from blocking the experiment before any scientific code
has run.

## 4. Execution sequence

### X0 — Docker daemon smoke

Context: separate runtime task, Sol XHigh Standard. No repository edits.

Scope:

1. record the initial Docker API, WSL-running, and Docker-process state;
2. run Docker Desktop start exactly once;
3. poll `docker version --format '{{json .Server}}'` for at most 180 seconds;
4. when the server becomes available, record server identity;
5. stop Docker Desktop once and run `wsl --shutdown` once;
6. verify the Docker API is unavailable and no Docker process remains.

PASS requires a live server response before timeout and a clean final shutdown.
No image pull, container run, dataset access, training, evaluation, or benchmark is
allowed. Smoke evidence is returned to central; it does not create
`attempt-004-linux`.

If X0 fails, the task stops without retry. Central classifies the error from the
captured command output. A second smoke may be authorized only after a concrete
fix. Two materially identical Docker Desktop failures trigger migration to Docker
Engine inside WSL2 or a Linux host; they do not trigger another runner redesign.

### X1 — Runner simplification and static preflight

Context: central, Sol Max Standard.

After X0 PASS, revise the existing Linux materialization runner only enough to:

- remove the fresh-audit-receipt prerequisite;
- preserve exact-head, clean-tree, confirmation, absent-root, disk-capacity,
  literal-argv, `shell=False`, timeout, no-retry, and cleanup checks;
- accept one central static-validation receipt bound to the final runner bytes;
- retain fail-closed final-result publication;
- keep training, evaluation, metrics, bridge, and TEST access forbidden.

Run the focused runner tests and packet validator once. Any failure is fixed in
central and rechecked at the same seam. No new worktree is created for planning or
remediation.

### X2 — M0/M1 materialization

Context: separate runtime task, Sol XHigh Standard.

Execute the exact final command from the X1 contract against a fresh root:
`attempt-004-linux`. Monitor process liveness every 30 seconds and enforce the
runner's per-command timeouts. Do not retry, fall back, or reuse partial roots.

PASS requires:

- GroupLens archive identity and extraction inventory;
- exactly 100,000 interactions, 943 users, and 1,682 items;
- raw-to-RecBole reconciliation;
- CPython 3.11.9, PyTorch 2.2.2 CPU, and RecBole 1.2.1 import checks;
- immutable command journal and final result receipt;
- Docker/WSL closure; and
- explicit negative assertions for training, evaluation, metrics, and TEST.

If X2 fails, the attempt is closed and retained. Central fixes only the observed
failure and creates a new numbered attempt; the failed root is never retried.

### X3 — Official RecBole reproduction

Context: separate runtime task after X2 PASS.

Freeze one BPR/ML-100K run packet using source seed 2020, the source split and
full-sort top-10 evaluator, and the source checkpoint rule. Run CPU-only once with
no tuning and no access to the project TEST set.

The official row is accepted only when source, config, data, split, evaluator,
checkpoint, and metric bindings match and NDCG@10 lies in `[0.26296, 0.29064]`.
Otherwise the result is stored as FAIL or INCOMPARABLE and cannot be cited as a
paper benchmark.

### X4 — Harmonized project benchmark and E5

Only after X3 PASS:

1. activate the shared evaluator and mandatory comparator adapters;
2. tune on validation only;
3. lock configs and run final seeds `42/2027/31415`;
4. open project TEST once after registry lock;
5. compute per-user metrics, paired bootstrap, and Holm correction;
6. perform the final E5 audit and seal Phase 1E.

## 5. Runtime failure routing

| Failure surface | Immediate action | Next action |
|---|---|---|
| Docker Desktop cannot initialize | Stop X0; preserve output | Central fixes exact service/socket error; one new smoke |
| Docker API unavailable after 180 s | Stop X0 | Collect Docker/WSL diagnostics; no materialization |
| Same Docker failure twice | Stop Docker Desktop path | Move execution to WSL2 Docker Engine or Linux host |
| Packet/static validator fails | No runtime | Fix at central; rerun focused validator |
| Materialization command fails | Close attempt | Fix exact seam; create next numbered attempt |
| OOM/commit pressure | Close attempt | Apply 8 GB/4 CPU/4 GB swap profile, then new attempt |
| Official metric outside tolerance | Preserve negative result | Mark FAIL/INCOMPARABLE; do not tune to the target |

## 6. Completion checkpoints

- X0 PASS: Docker runtime is usable; Phase 1E remains `NOT_RUN` scientifically.
- X2 PASS: dataset/environment are materialized; benchmark still not run.
- X3 PASS: first accepted official reproduction row exists.
- X4/E5 PASS: Phase 1E is complete and Stage 2 paper writing may use measured
  benchmark claims.

The next executable checkpoint is **X0 — Docker daemon smoke**.
