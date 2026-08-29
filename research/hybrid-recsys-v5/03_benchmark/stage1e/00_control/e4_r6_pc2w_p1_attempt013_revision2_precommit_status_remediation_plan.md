# Stage 1E / E4-R6-PC2W-P1 Attempt-013 Revision 2 precommit-status remediation plan

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-29T00:00:00+07:00
- Verification Status: UNVERIFIED
- Version Label: stage1e_e4_r6_pc2w_p1_attempt013_revision2_precommit_status_remediation_plan_v1
- Upstream Dependencies: [stage1e_e4_r6_pc2w_p1_attempt013_central_failure_remediation_plan_v1, stage1e_e4_r6_pc2w_p1_attempt013_revision2_packet_lineage_contract_v1, stage1e_e4_r6_pc2w_p1_attempt013_revision2_failed_precommit_evidence]
- Repro Lock: null
- Experiment Intake Declaration: `no_experiments_declared`, declared by `scholar`
- Experiment Provenance: `[]`

## Gate and scope

This is a new controlled static implementation revision after a validator precommit failure. It is not a runtime retry: no Attempt-013 process was invoked, no scientific TEST was opened, no output was created, and the one-shot runtime budget remains `authorized=1`, `consumed=0`, `remaining=1`, with `automatic_retry_count=0` and `fallback_count=0`.

The current truth remains:

- `RESULT_STATUS=NOT_RUN`;
- `TEST_SET_OPENED=NO`;
- `ACCEPTED_RESULT_ROWS=0`;
- benchmark admission closed;
- Attempt-013 output root absent;
- no central Revision 2 validation, fresh audit, exact-command adjudication, or runtime gate is opened by this plan.

This plan authorizes only a later XHigh static fix-and-seal stage. It does not authorize implementation in this plan task, runner import or invocation, host/process/port probing, Docker, WSL, Hyper-V, network access, materialization, preprocessing, training, evaluation, benchmark execution, scientific TEST access, retry, fallback, history rewrite, or modification of frozen evidence.

Model policy for this plan is `gpt-5.6-sol`, reasoning `ultra`, requested service tier `default` / display `Standard`. Actual service tier and speed are `UNOBSERVABLE`; no positive Fast/Priority evidence is present. Positive evidence of Fast/Priority, a different model, or different reasoning is terminal.

## Locked input state

The plan was entered only after the following source/Git-only preconditions matched:

- HEAD / R2a: `1a9ca21c5c8b1b08fdec788fbbf23e88473c117f`;
- R2a parent / original central-failure plan: `2efdcd73bb7f7e2b298ee12cdb5b09171a865d69`;
- R2a delta: exactly three `A` lineage-support paths;
- R2a pure public-seam suite: previously observed `19/19` GREEN;
- output root `research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_av/E4_R6PC2W_P1_attempt013_admission_observation`: absent;
- worktree: exactly the four intended R2 draft paths with porcelain status ` M`, and no other path;
- this plan target: absent before creation.

The inherited four draft paths and their pre-plan canonical clean-filter Git OIDs are evidence boundaries:

| Draft path | Canonical working OID |
|---|---|
| `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_admission_observation_contract.json` | `241a9f03a9640c84dddba69e8f0f35e2afe086e7` |
| `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_execution_authorization.json` | `c62be7219288587ca04431b7a41248d00b4fa2ef` |
| `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_attempt013_admission_observation.py` | `7a1f6debbabf3701dd3ff8504f3ca6e316eefd1a` |
| `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt013_static_packet.py` | `8b9da90e47079aba01e9530f679ec8e4e933522c` |

The plan commit must not stage, rewrite, normalize, restore, stash, or otherwise touch these drafts. Checkout EOL representation is not an authority; `git hash-object --path=<path> <path>` is the canonical comparison.

## Deterministic failure evidence

The already-run feedback-loop command was:

```powershell
& 'C:\Program Files\Python311\python.exe' -B `
  research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt013_static_packet.py `
  --repo-root C:\Users\ACER\.codex\worktrees\2428\backend `
  --precommit
```

It exited nonzero before child-suite execution with `PRECOMMIT_WRITE_SET_MISMATCH`. That is an acceptable deterministic RED for this defect: it reaches the exact status-boundary predicate, is source/Git-only, runs in seconds, and neither imports nor invokes an Attempt runner. It must not be rerun unchanged merely to reproduce already sealed evidence.

The relevant data flow is:

```text
four intended unstaged modifications
        |
        v
git status --porcelain=v1 --untracked-files=all
        |
        | raw first row begins with the XY column: " M <path>"
        v
generic git() UTF-8 decode
        |
        v
.strip() applied to the whole multi-line response
        |
        | removes the first row's leading XY-space only
        | later rows retain their leading spaces
        v
actual first parsed row becomes "M <path>"
        |
        +---- expected rows remain exact " M <path>"
        v
set comparison cannot match
        |
        v
PRECOMMIT_WRITE_SET_MISMATCH before import graph or tests
```

### Root cause

The generic `git()` helper conflates two output contracts:

1. ordinary scalar/text Git responses where surrounding whitespace is disposable; and
2. porcelain status, where the leading two-character `XY` columns are protocol data.

Calling `.strip()` on the complete porcelain response destroys the leading space of only the first row. With a valid unstaged modification, the first row therefore cannot equal its exact `" M "` expectation. The four-file draft itself is not the cause, and weakening the expected set would make the validator unable to distinguish staged, unstaged, untracked, deleted, renamed, or mixed-index state.

## Falsifiable remediation routes

| Rank | Route | Falsifiable prediction | Decision |
|---:|---|---|---|
| 1 | Add a dedicated porcelain-status reader that obtains raw bytes through the existing read-only Git transport, decodes strict UTF-8, and removes only terminal `CR`/`LF` characters with `.rstrip("\r\n")` | The first returned row remains exactly `" M <path>"`; all four exact rows match; an index-staged or extra row still fails; the precommit validator advances to the AST graph and finishes `112/112` | **Selected** |
| 2 | Change generic `git()` from `.strip()` to `.rstrip("\r\n")` for every text command | The status predicate passes, but all existing scalar consumers receive preserved leading/trailing spaces and require a wider regression audit | Rejected: unnecessary blast radius |
| 3 | Switch status to porcelain `-z` and add a NUL-record parser | Exact XY data can be preserved, but parser shape, tests, and command plumbing expand for a four-row deterministic defect | Rejected: correct but overengineered |
| 4 | Normalize or `lstrip()` both actual and expected rows, ignore the first row, or compare only paths | The current false negative disappears, but staged `M `, unstaged ` M`, `MM`, `??`, deletion, rename, and extra-path evidence can collapse into the same accepted shape | Rejected: weakens the safety predicate |
| 5 | Replace porcelain status with `git diff --name-only` | The four paths may appear, but index state and untracked files are not represented by the same authority | Rejected: loses required worktree semantics |

## Selected minimal fix

The next XHigh implementation stage must change only the already-modified static validator portion needed for the status reader and must keep the four-path draft boundary intact:

1. retain the generic `git()` behavior for its existing consumers;
2. add one narrowly named status function, for example `git_status_porcelain(repo)`, which requests binary output using the existing read-only Git subprocess path;
3. strict-decode the bytes as UTF-8 and remove only trailing line terminators with `.rstrip("\r\n")`;
4. replace only the precommit/committed worktree-status read with this dedicated function;
5. preserve the exact expected precommit set as four literal `" M <path>"` rows;
6. preserve the committed expectation as an empty status response;
7. do not sort away duplicates before validating uniqueness, translate XY codes, ignore the first row, accept a path-only projection, or catch/swallow `PRECOMMIT_WRITE_SET_MISMATCH`.

This is a locality fix at the protocol boundary. It does not alter packet-lineage semantics, raw blob binding, runner behavior, gate receipts, output behavior, or scientific logic.

## Revised immutable topology

The one-file commit produced by this plan task is symbolically `P1` and must become the immediate parent of the final seal:

```text
2efdcd73bb7f7e2b298ee12cdb5b09171a865d69  original central-failure plan
  |
  v
1a9ca21c5c8b1b08fdec788fbbf23e88473c117f  R2a: exactly 3 x A lineage support
  |
  v
P1                                             this plan: exactly 1 x A
  |
  v
R2                                             final seal: exactly 4 x M
  |
  v
C2                                             Ultra central receipt: exactly 1 x A
  |
  v
A2                                             fresh Ultra audit receipt: exactly 1 x A
```

After `P1` exists:

- `P1` replaces R2a as the required immediate `PACKET_PARENT` / sealing parent;
- R2a remains the immutable origin commit for the three lineage-support blobs;
- the admission contract's packet-parent checkpoint, the runner's retained `PACKET_PARENT`, the validator's R2 parent expectation, and the pure-lineage spec's `sealing_parent` must all bind the full 40-hex `P1` commit;
- the retained main must still independently see exactly the same four `M` seal rows;
- R2 must still contain exactly the same four modified paths and no fifth path;
- this plan path is historical provenance, not an active packet artifact and not part of the sealing delta.

No old commit, receipt, plan, R0 artifact, R1 helper, or R2a support artifact may be amended or rewritten.

## Active aggregate roster remains thirteen

The Revision 2 receipt/raw-blob roster remains the disjoint union below:

- four frozen R0 contract/test artifacts;
- two unchanged R1 helper artifacts;
- three R2a lineage-support artifacts;
- four final R2 sealing artifacts.

Total: `4 + 2 + 3 + 4 = 13` final blobs. `P1` and this Markdown plan are lineage/provenance inputs only; adding the plan to the packet roster would incorrectly change the total to fourteen and is forbidden.

## Next-stage RED/GREEN and verification contract

### Entry gate

Before implementation, the XHigh owner must verify:

- HEAD is full `P1` and its sole parent is R2a;
- the P1 commit delta is exactly this one plan file with status `A`;
- worktree status is exactly the inherited four ` M` draft paths;
- their four canonical OIDs still equal the locked values above;
- output root and Revision 2 central/audit receipt paths are absent;
- budget/truth remain `1/0/1`, `NOT_RUN/NO/0`.

Any mismatch is `HANDOFF_INCOMPLETE`; do not repair the worktree by checkout, reset, stash, normalization, or reconstruction.

### Controlled fix

Use the existing failed command as the sealed RED observation. Apply only the dedicated status-reader change within the already-authorized validator draft. Then bind every R2 sealing-parent consumer to full `P1` within the same four draft files. Do not introduce a new implementation or test file and do not change the active thirteen-artifact roster.

### Precommit GREEN

Run exactly once after the fix:

```powershell
& 'C:\Program Files\Python311\python.exe' -B `
  research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt013_static_packet.py `
  --repo-root <EXACT_WORKTREE_ROOT> `
  --precommit
```

Required observations:

- exact four ` M` rows are preserved and matched, including the first row's leading XY-space;
- any staged row, untracked row, missing path, extra path, or different XY code remains fail-closed;
- strict JSON passes for all five bound JSON contracts read by the validator;
- the same pure `validate_packet_lineage(...)` helper passes with aggregate roster `13`, frozen R0 `4`, support `5`, and exact seal `4 x M`;
- recursive cycle-safe repository-local AST graph classifies exactly nine candidate suites;
- exactly four runner-reaching suites are excluded;
- exactly five runner-free suites execute under Python 3.11 `-B`;
- authoritative tests are exactly `112/112`: lineage `19`, authority `9`, retained Attempt-012 `12`, retained Attempt-011 `62`, and command-interface `10`;
- `executed_child_runner_imports=0` and `runner_main_invocations=0` are graph-backed, not direct-only claims;
- no skip/xfail, `.pyc` drift, host/runtime command, output creation, retry, or fallback occurs.

An unexpected failure after the controlled fix is terminal. Preserve evidence and return to a new Ultra plan stage; do not patch iteratively or rerun as a fallback.

### Seal R2

Before committing R2:

1. strict-parse JSON and AST-parse Python without importing the runner;
2. require `git diff --check` clean;
3. require unstaged delta exactly four `M` paths;
4. stage exactly those four paths;
5. require cached delta exactly four `M` paths and no plan path;
6. create one non-amended R2 commit parented by `P1`.

After R2, verify its sole parent is `P1`, its exact delta is four `M`, and the worktree is clean. Recompute raw Git blob OID, byte count, and SHA-256 for all thirteen active artifacts. Raw Git blob bytes, not checkout-normalized bytes, are authoritative.

### Committed replay

Run the same validator once without `--precommit` at clean R2. It must independently observe:

- R2 parent exactly `P1`;
- R2 delta exactly four `M`;
- retained runner configuration uses `PACKET_PARENT=P1` and exactly four sealing relatives;
- aggregate roster remains thirteen and all frozen/support origins replay;
- strict JSON, pure helper, AST graph, and authoritative `112/112` tests remain GREEN;
- output absent; runtime counters zero; truth `NOT_RUN/NO/0`; budget `1/0/1`.

No synthetic PASS receipt may be created to test the runner, and no runner may be imported or invoked by either validation mode.

## Gate sequence after R2

1. **XHigh R2 status fix and seal, no runtime.** Apply the selected local fix, bind `P1`, pass precommit, commit exact four `M`, pass committed replay, and stop.
2. **Ultra central static validation.** A fresh validator replays topology, all thirteen raw blobs, exact helper semantics, retained control flow, status-reader regression, recursive import graph, contracts, hashes, output absence, budget, and zero runtime counters. Only a Revision 2 central PASS receipt opens the next gate.
3. **Fresh independent Ultra audit.** Bind the central receipt's raw bytes/SHA-256 and independently replay the packet. Only a fresh-audit PASS opens command adjudication.
4. **Deterministic exact-command binding.** Bind absolute cwd, exact `C:\Program Files\Python311\python.exe`, `-B`, absolute runner path, full argv, `packet_commit=R2`, exact execution HEAD, both receipt paths and raw SHA-256 values, confirmation token, output root, locked model role, and unused `1/0/1` budget.
5. **Standing user authorization.** Auto-execution may activate only when central PASS, fresh audit PASS, and deterministic exact-command binding are simultaneously authoritative. Standing authorization never overrides a failed/absent gate, changed HEAD, dirty worktree, hash drift, output presence, model mismatch, positive Fast/Priority evidence, or consumed budget.

If any implementation, central, audit, binding, or future execution stage fails, there is no automatic retry or fallback. Preserve the evidence and open the specifically authorized next plan stage. A future runtime failure consumes the sole attempt and changes the budget to `1/1/0`; this plan does not authorize such execution.

## Plan completion contract

This plan task is complete only if its commit:

- has R2a as its sole parent;
- adds exactly this one Markdown file;
- leaves all four R2 drafts unstaged and byte-canonically unchanged;
- leaves the output root absent;
- does not create, import, invoke, validate, audit, or execute any Attempt runner;
- reports `next_gate=XHIGH_R2_STATUS_FIX_AND_SEAL_NO_RUNTIME`.
