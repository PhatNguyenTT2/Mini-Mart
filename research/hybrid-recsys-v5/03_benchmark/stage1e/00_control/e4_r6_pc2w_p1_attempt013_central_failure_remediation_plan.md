# Stage 1E / E4-R6-PC2W-P1 Attempt-013 central-failure remediation plan

## Material Passport

- Origin skill: `experiment-agent`
- Origin mode: `plan` / static fail-closed remediation
- Origin date: `2026-08-29T00:00:00+07:00`
- Verification status: `ANALYZED`
- Version label: `stage1e_e4_r6_pc2w_p1_attempt013_central_failure_remediation_plan_v1`
- Upstream dependency: `stage1e_e4_r6_pc2w_p1_attempt013_central_static_validation_receipt_v1`
- Upstream commit: `0ebd1145171f9f1289adc7e2ff7a019a7aec9c2e`
- Upstream receipt Git blob: `0b7bfa5369ec904adebfd9a67ad5f89ec03e35f6`
- Upstream receipt raw Git blob bytes: `35640`
- Upstream receipt raw SHA-256: `27778c4d05beaf43eebdcd2cd1af319158fe5325bc08ce8a28965e78e6cd2004`
- Experiment intake: `no_experiments_declared`
- Experiment provenance: none; this is a plan-only, static/offline artifact
- Repro lock: `null`; no experiment or runtime result exists
- ARS route: ARS-Codex `0.1.26` → `ars/experiment-agent/WORKFLOW.md` → `agents/code_runner_agent.md`
- Debugging route: `.agents/skills/diagnosing-bugs/SKILL.md`
- Context/ADR check: no `CONTEXT.md`, `ADR*.md`, `adr/`, `adrs/`, or `architecture/decisions/` artifact was found in the repository conventions searched before writing this plan

## Plan verdict

`PLAN_APPROVED_FOR_XHIGH_ATTEMPT013_IMMUTABLE_REVISION2_TDD_NO_RUNTIME`

Selected route: preserve Attempt-013 and issue a new immutable **Attempt-013 Revision 2** packet. Do not issue Attempt-014 at this gate. Attempt-013 has not launched a process, its output root is absent, and its one-shot budget remains `authorized=1`, `consumed=0`, `remaining=1`. A revision-specific packet and new revision-specific gate receipts preserve the failed R1 evidence without allocating a fictitious new runtime attempt.

This plan does not implement the fix, validate a repaired packet, open a fresh audit, confirm an execution command, invoke a runner, probe a host, create an output root, or execute an experiment. The benchmark remains closed.

## Current immutable state and scope boundary

Known ancestry at plan intake is:

```text
3c7fede9dc0c1ba0925593e72ed515dccec84fcb  START / Attempt-012 remediation plan
└─ ce6377c351625ed7e029f2883520583ca97fc2b8  Attempt-013 R0: 4 × A
   └─ 294422ca8557e4b55ae3863d853289e2232011b2  Attempt-013 R1: 6 × A
      └─ 0ebd1145171f9f1289adc7e2ff7a019a7aec9c2e  central HANDOFF_INCOMPLETE receipt
         └─ P  this plan commit, to be bound after commit
```

Pre-write state was exact: HEAD `0ebd1145171f9f1289adc7e2ff7a019a7aec9c2e`, parent `294422ca8557e4b55ae3863d853289e2232011b2`, clean worktree, target plan absent, and the Attempt-013 `wave_av` output root absent.

The following remain forbidden in this plan stage: implementation; import or invocation of any Attempt runner; Docker, WSL, Hyper-V, PowerShell host, process, executable, port, or network probes; materialization; preprocessing; training; evaluation; benchmark execution; scientific TEST access; output-root creation; retry; fallback; merge; rebase; amend; squash; cherry-pick; push; pipeline-state change; manuscript change; or modification of an old receipt or old commit.

## Deterministic RED loop already established

### Exact symptom

Attempt-013 R1 configures the retained main as follows:

- `PACKET_PARENT = ce6377c351625ed7e029f2883520583ca97fc2b8`
- `PACKET_RELATIVES =` the aggregate ten-file R0-plus-R1 packet roster
- retained `execute_e4_r6_pc2w_p1_attempt008_admission_observation.py` computes `expected_delta = sorted("M\\t<path>" for every PACKET_RELATIVES path)`
- the retained predicate compares that ten-row expectation with `git diff-tree --no-commit-id --name-status -r <packet_commit>`

The exact read-only Git command is:

```powershell
git diff-tree --no-commit-id --name-status -r 294422ca8557e4b55ae3863d853289e2232011b2
```

Its exact semantic result is six additions:

```text
A  e4_r6_pc2w_p1_attempt013_admission_observation_contract.json
A  e4_r6_pc2w_p1_attempt013_execution_authorization.json
A  e4_r6_pc2w_p1_attempt013_pre_runtime_authority.py
A  e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py
A  execute_e4_r6_pc2w_p1_attempt013_admission_observation.py
A  validate_e4_r6_pc2w_p1_attempt013_static_packet.py
```

Every path above is rooted at `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/`. The other four aggregate-roster artifacts are frozen additions in R0, not changes in R1:

1. `e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract.json`
2. `test_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py`
3. `e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract.json`
4. `test_e4_r6_pc2w_p1_attempt013_pre_runtime_gate.py`

Therefore the current predicate deterministically compares ten `M` rows with six `A` rows. It is false for every invocation whose `packet_commit` is R1. The raised message is `packet commit exact four-file revision delta mismatch`. This happens before gate-receipt validation, output-root creation, host probing, Docker dispatch, or initialization of a persistable runtime failure packet.

### RED-loop command contract

The implementation stage must preserve a source/Git-only reproducer before changing semantics:

1. Read the retained expectation from committed source with `rg`; do not import the runner.
2. obtain the R1 parent and delta only through `git rev-list` and `git diff-tree`;
3. assert equality between the retained ten-`M` expectation and the six-`A` observation;
4. require a deterministic nonzero result containing `expected_rows=10`, `expected_status=M`, `actual_rows=6`, `actual_status=A`, and `frozen_parent_rows=4`.

No runner import, runner invocation, synthetic PASS receipt, host call, or output write belongs to this RED loop. The future regression test converts the same facts into a pure-function fixture.

## Root cause and validation-coverage cause

### Root cause

The defect is a contract-authority conflation:

- **Aggregate artifact roster authority** answers which final packet blobs central validation and receipts must bind.
- **Single-commit sealing-delta authority** answers exactly which paths and statuses the final packet commit may change relative to its one parent.
- **Frozen-origin authority** answers which R0 blobs must remain byte-identical at the final packet commit.

Attempt-013 uses one variable, `PACKET_RELATIVES`, for the first two questions. The retained code interprets it only as a single-commit `M` delta, while Attempt-013 populates it as the aggregate R0-plus-R1 roster. Neither the total roster nor the R1 delta is intrinsically malformed; the wiring assigns the wrong authority to the retained predicate.

### Coverage and reporting cause

The committed validator's AST scan examines direct imports of only the validator module, then emits constant counters `runner_imports=0` and `runner_invocations=0`. It does not recursively resolve the eight child-suite import graphs. Four of those eight entrypoints transitively reach `execute_e4_r6_pc2w_p1_attempt007_admission_observation` through retained modules:

1. `test_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py`
2. `test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py`
3. `test_e4_r6_pc2w_p1_attempt008_probe_contract.py`
4. `test_e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py`

The observed `134/134` is therefore non-authoritative: it neither executes the retained packet-delta equality predicate nor supports the emitted direct-only import counter. It cannot open runtime authority.

## Ranked hypotheses and falsifiable fix routes

| Rank | Hypothesis / route | Falsifiable prediction | Decision |
|---|---|---|---|
| 1 | Split aggregate roster, frozen origins, support origins, and final sealing delta; publish Attempt-013 Revision 2 in a support commit followed by an exact four-`M` seal commit | A pure predicate accepts R1 when explicitly given its true six-`A` seal and accepts Revision 2 only when its final seal is exactly four `M` rows; the retained gate sees the same four rows; all four R0 hashes remain unchanged | **Selected** |
| 2 | Publish a completely new Attempt-014 packet | A correct new packet could pass, but it would require a new attempt ID, output root, confirmation token, schemas, budget owner, contracts, runner, validator, and receipts despite zero Attempt-013 launches | Rejected as unnecessary provenance and write-set expansion |
| 3 | Change the retained expectation from `M` to `A` for the existing R1 | Six `A` rows could be made to match only by also shrinking the compared set; the four R0 blobs would still be absent from the single-commit delta and aggregate lineage would remain unproved | Rejected; status substitution is not lineage proof |
| 4 | Touch all ten files in a new commit solely to manufacture ten `M` rows | The retained equality would become green while frozen R0 blob hashes change or meaningless byte churn is introduced | Rejected; violates frozen authority and provenance minimality |
| 5 | Use `START..HEAD` union diff, monkeypatch Git output, suppress the retained check, or catch and ignore its exception | A packet with an extra or missing final-seal path could pass because aggregate history is not an exact sealing-commit predicate | Rejected; bypasses the safety gate |

Route 1 is the smallest route that both retains the legacy safety check and gives it the authority it was designed to consume. It is not a relabeling of `M` as `A` and does not rewrite R0, R1, the central failure receipt, or this plan.

## Selected Attempt-013 Revision 2 topology

After this plan commit `P`, XHigh implementation TDD may create exactly two implementation commits:

```text
P
└─ R2a  lineage-support commit: exactly 3 × A
   └─ R2  final sealing commit / packet_commit: exactly 4 × M
      └─ C2  Ultra central PASS receipt commit: exactly 1 × A
         └─ A2  fresh Ultra audit PASS receipt commit: exactly 1 × A
```

The symbols `P`, `R2a`, `R2`, `C2`, and `A2` must be replaced only with full 40-hex committed IDs after each commit exists. Every commit must have exactly one parent. No history rewrite is permitted.

### R2a exact write set: three additions

1. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_packet_lineage.py`
2. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_packet_lineage_contract.json`
3. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/test_e4_r6_pc2w_p1_attempt013_packet_lineage.py`

### R2 exact final-sealing write set: four modifications

1. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_admission_observation_contract.json`
2. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt013_execution_authorization.json`
3. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_attempt013_admission_observation.py`
4. `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt013_static_packet.py`

The final runner must set the retained `PACKET_PARENT` to `R2a` and the retained `PACKET_RELATIVES` to only these four R2 sealing paths. Thus the retained main independently repeats an exact four-`M` check; it is not skipped, caught, monkeypatched, or fed fabricated Git output.

### Aggregate Revision 2 roster: thirteen final blobs

The aggregate roster used for raw-blob and receipt binding is the disjoint union of:

- four frozen R0 contract/test artifacts;
- two unchanged R1 helpers: `e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py` and `e4_r6_pc2w_p1_attempt013_pre_runtime_authority.py`;
- the three R2a lineage-support additions;
- the four R2 final-sealing modifications.

The original R1 versions of the last four paths remain permanently addressable at commit `294422ca8557e4b55ae3863d853289e2232011b2`. R2 creates new blobs at those paths; it does not rewrite R1. No old receipt is in the active packet roster, and no old receipt may be modified.

No other implementation file is allowed. In particular, do not modify the retained Attempt-008 main, the four R0 artifacts, the two reused R1 helper files, old plans or receipts, `pipeline_state_stage1e.json`, output artifacts, or manuscript files.

## Pure runner-independent packet-lineage seam

`e4_r6_pc2w_p1_attempt013_packet_lineage.py` must be a pure module: no subprocess, filesystem, Git invocation, runner import, dynamic import, environment read, clock, network, host probe, Docker/WSL/Hyper-V capability, or bytecode write. It receives immutable values and returns a structured verdict or raises a stable lineage error.

The input contract must separate:

1. `aggregate_roster`: normalized, casefold-unique final artifact paths;
2. `frozen_r0_bindings`: path, R0 origin commit, raw byte count, raw SHA-256, and observed final-commit blob fact;
3. `support_bindings`: unchanged R1 and R2a artifacts with origin commit and final-commit blob fact;
4. `sealing_parent`: the single required parent `R2a`;
5. `expected_sealing_delta`: the exact four `(M, path)` rows;
6. `observed_sealing_delta`: raw normalized rows obtained by the caller from `git diff-tree`;
7. `packet_commit` and a caller-provided `packet_is_ancestor_of_execution_head` fact;
8. final packet blob facts for every aggregate-roster path.

The predicate must fail closed unless all of the following hold:

- the three roster partitions are disjoint and their union equals the aggregate roster;
- all paths are repository-relative, normalized, unique under casefold, and inside `00_control`;
- the packet commit has exactly one parent and it equals `R2a`;
- the observed sealing delta exactly equals the four expected `M` rows, with no rename/copy, mode-only, extra, missing, duplicate, or out-of-roster row;
- every frozen R0 blob is byte-identical at R0 and R2 and matches its raw byte/SHA binding;
- every support artifact matches its committed origin binding at R2;
- every aggregate-roster path has an R2 raw Git blob binding;
- R2 is an ancestor of the later exact execution HEAD;
- no aggregate-roster expectation is derived from the sealing-delta expectation or vice versa.

The runner and validator may independently obtain facts from read-only Git, but both must call this exact pure predicate. Neither may reimplement or weaken its comparisons.

## TDD RED → GREEN protocol

### RED before semantic fix

In an uncommitted XHigh implementation worktree, first extract the current conflated comparison into the pure seam without changing its behavior. Add `test_e4_r6_pc2w_p1_attempt013_packet_lineage.py` with the actual R0/R1 fixture:

- aggregate roster: ten paths;
- frozen R0 partition: four paths;
- sealing parent: R0;
- expected correct R1 seal: six `A` rows;
- observed R1 seal: the same six `A` rows;
- all ten packet blobs present at R1.

The regression assertion expects valid separated lineage. The extracted legacy behavior must go RED because it derives ten `M` rows from the aggregate roster. Required command:

```powershell
& 'C:\Program Files\Python311\python.exe' -B research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/test_e4_r6_pc2w_p1_attempt013_packet_lineage.py -v
```

Required RED observation: nonzero exit and a lineage mismatch whose structured facts include `expected aggregate=10`, `derived legacy seal=10×M`, `observed seal=6×A`, and `frozen R0=4`. A missing-module error, syntax error, unrelated assertion, runner import, or host call is not an acceptable RED.

### GREEN pure seam

Change only the pure seam so aggregate roster and expected seal are independent authorities. The same R1 fixture must become GREEN. Add at least these falsifying negative cases:

1. wrong or multiple parent;
2. missing sealing path;
3. extra sealing path;
4. wrong status including `A`, `D`, `R`, or `C` where `M` is required for R2;
5. duplicate or casefold-colliding path;
6. path outside `00_control`;
7. frozen R0 byte drift;
8. frozen R0 SHA or byte-count mismatch;
9. support-origin blob drift;
10. roster partition overlap or incomplete union;
11. packet not ancestor of execution HEAD;
12. aggregate-roster manipulation that leaves the four-row seal unchanged.

Then wire the runner and validator to the same function. Re-run the pure suite, the safe pre-runtime suites, the validator's precommit mode at R2a plus exactly four modified R2 paths, and committed replay at R2. The final committed state must be GREEN without retry or fallback.

## Runner integration requirements

Before `legacy.main()` and before any output-root or host operation, the Revision 2 runner must:

1. bind exact cwd, interpreter, full original argv, expected execution HEAD, packet commit, central receipt, fresh audit receipt, and unused budget as already required;
2. obtain parent, exact delta, ancestry, and raw blob facts via unmodified read-only Git calls;
3. strict-parse the lineage contract and verify its raw blob binding from the revised admission/authorization documents;
4. call the pure lineage predicate;
5. configure the retained main with `PACKET_PARENT=R2a`, `PACKET_RELATIVES=<exact four R2 sealing paths>`, and the unchanged output root;
6. allow the retained main to repeat its four-`M` delta check and all later gates.

Any disagreement between the pure predicate and retained check is terminal. Do not translate statuses, use an aggregate diff as the seal, monkeypatch `legacy.git`, swallow the retained exception, or create a synthetic receipt.

## Validator remediation

The revised validator must validate the exact predicate that runtime will use:

- read the R2 parent, R2 exact delta, R0/R1/R2a origins, R2 ancestry, and all thirteen raw Git blobs;
- call `e4_r6_pc2w_p1_attempt013_packet_lineage` with those facts;
- assert statically that the Revision 2 runner calls the same helper before `legacy.main()`;
- assert that retained `PACKET_PARENT` and `PACKET_RELATIVES` are configured from the sealing authority, never the aggregate roster;
- replay strict JSON and raw byte/SHA bindings from committed blobs;
- retain direct-self/parent-union, TCP direct-self binding, BuildTime field comparator, single-snapshot, command binding, gate receipt, output absence, and budget checks.

The validator must also build a recursive AST import graph for every candidate child-suite entrypoint. Resolution is limited to repository-local Python modules, handles cycles deterministically, and executes no imports. The revised candidate set is nine suites: the existing eight plus the new lineage suite.

The four known runner-reaching suites must be identified exactly and excluded from the authoritative child-process aggregate. Their earlier `41/41` total may be recorded only as historical, observed, non-authoritative evidence. The five runner-free suites may execute as static/unit subprocesses under Python `-B`. Required output fields include:

- `candidate_suite_entrypoints=9`;
- `runner_reaching_candidate_entrypoints=4` with exact paths and reachable runner module;
- `authoritative_executed_runner_free_suites=5`;
- `excluded_runner_reaching_suites=4`;
- `executed_child_runner_imports=0`;
- `runner_main_invocations=0`;
- separate passed/total counts for the authoritative set.

The validator must never emit a bare `runner_imports=0` based on its own direct imports. If graph resolution is ambiguous, dynamic, outside scope, or cyclic without a deterministic closure, fail closed rather than classify the suite as runner-free.

## Contracts, receipt names, and schemas

R2 must bump the four modified documents/code paths to Revision 2 semantics while retaining stage ID `E4-R6-PC2W-P1-ATTEMPT013` and binding R2 as the packet commit.

Required new or revised schemas are:

- lineage contract: `stage1e-e4-r6-pc2w-p1-attempt013-revision2-packet-lineage-contract-1.0`;
- admission contract: `stage1e-e4-r6-pc2w-p1-attempt013-revision2-admission-observation-contract-1.0`;
- execution authorization: `stage1e-e4-r6-pc2w-p1-attempt013-revision2-execution-authorization-1.0`;
- validator result: `stage1e-e4-r6-pc2w-p1-attempt013-revision2-static-validation-result-1.0`.

The old central failure receipt remains at its existing path and remains authoritative only for R1. New gates must use new paths:

- central: `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt013_revision2_central_static_validation_receipt.json`
- central schema: `stage1e-e4-r6-pc2w-p1-attempt013-revision2-central-static-validation-receipt-1.0`
- central PASS verdict: `PASS_PC2W_P1_ATTEMPT013_REVISION2_CENTRAL_STATIC_VALIDATION`
- fresh audit: `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt013_revision2_fresh_independent_audit_receipt.json`
- fresh-audit schema: `stage1e-e4-r6-pc2w-p1-attempt013-revision2-fresh-independent-audit-receipt-1.0`
- fresh-audit PASS verdict: `PASS_PC2W_P1_ATTEMPT013_REVISION2_FRESH_INDEPENDENT_AUDIT_READY_FOR_EXACT_COMMAND`

Each receipt commit is an exact one-file addition. The fresh audit must bind the central receipt's raw Git blob bytes and SHA-256. Neither receipt may overwrite, supersede by path, or reinterpret the R1 HANDOFF_INCOMPLETE receipt.

## Output and budget truth

The only possible runtime output root remains:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_av/E4_R6PC2W_P1_attempt013_admission_observation`

It must remain absent throughout implementation, central validation, fresh audit, and exact-command adjudication. Its future exact file set remains `admission_observation.json`, `command_receipts.json`, `execution_receipt.json`, and `handoff.json`, with no extra file.

Until the exact locked process is invoked:

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- benchmark admission is closed
- budget is `authorized=1`, `consumed=0`, `remaining=1`
- automatic retry count is `0`
- fallback count is `0`

The first future runner process invocation consumes the one shot even if it fails before Docker start or output-root creation. A failed execution leaves `consumed=1`, `remaining=0`; no retry, fallback, deletion, repair, or output-root reuse is permitted.

## Static command and test matrix for future gates

All Python commands use exactly `C:\Program Files\Python311\python.exe -B` from the repository root. This matrix authorizes only future implementation/static gate work, not execution in this plan task.

| Gate | Command class | Required observation |
|---|---|---|
| Existing RED | `git rev-list`, `git diff-tree`, and `rg` against committed R1/retained source | parent R0; actual `6×A`; retained expected `10×M`; four frozen paths in R0; no runner import |
| Pure RED/GREEN | `python.exe -B ...test_e4_r6_pc2w_p1_attempt013_packet_lineage.py -v` | exact-symptom RED before fix; all positive and twelve negative cases GREEN after fix |
| Safe retained seams | direct Python `-B` execution of only AST-proven runner-free child suites | exact expected counts; no skip/xfail; no runtime/host command |
| Precommit R2 | revised validator `--precommit` at R2a | worktree contains exactly the four intended modifications; output absent; no pyc drift |
| Committed R2 | revised validator committed replay with R2 | R2 parent R2a; exact `4×M`; aggregate roster 13; frozen R0 `4/4`; helper predicate PASS |
| Negative lineage | pure suite fixtures | every malformed parent/delta/partition/hash/ancestry case fails with stable code |
| Import graph | validator AST graph | 9 candidates; 4 runner-reaching excluded; 5 runner-free executed; no false zero counter |
| JSON integrity | strict UTF-8 parse from raw Git blobs | no exact or casefold duplicate keys, non-finite numbers, wrong root type, or checkout-only substitution |
| Repository boundary | `git status`, `git diff-tree`, `git diff --name-status`, `git diff --check` | exact R2a and R2 write sets; clean final worktree; no old-file drift beyond four authorized R2 paths |
| Bytecode boundary | before/after inventory of `*.pyc` and `__pycache__` | identical inventories and zero new/modified bytecode artifacts |

Central and fresh audit must recompute raw Git blob OID, byte count, and SHA-256 for all thirteen packet artifacts, the lineage contract, the two gate receipts, and every frozen upstream dependency they accept. Checkout-normalized bytes are not a substitute for raw Git blob bytes.

## Mandatory gate sequence

1. **XHigh implementation TDD, no runtime.** Use `gpt-5.6-sol`, reasoning `xhigh`, requested service tier `default`, display `Standard`; Fast/Priority prohibited. Observe the exact RED, make the pure seam GREEN, create R2a then R2 with the exact write sets, and stop.
2. **Ultra central validation.** A fresh central validator begins at R2, replays raw blobs, lineage helper semantics, retained control flow, transitive import graph, tests, schemas, hashes, model policy, exact write sets, output absence, and zero runtime counters. Only its revision-specific PASS receipt can open the next gate.
3. **Fresh independent Ultra audit.** Start at C2 without using unsealed conclusions; bind C2's exact parent and central-receipt raw hash. Only a revision-specific fresh-audit PASS can open command adjudication.
4. **Deterministic exact-command adjudication.** Bind absolute cwd, exact `C:\Program Files\Python311\python.exe`, `-B`, absolute Revision 2 runner, full argv, `packet_commit=R2`, `expected_head=A2`, both receipt paths and raw SHA-256 values, confirmation token, output root, model role, and unused `1/0/1` budget.
5. **Standing authorization auto-execution.** Existing user standing authorization may activate automatically only if central PASS, fresh audit PASS, and the deterministic exact-command binding are all authoritative and simultaneously true. It never overrides a fail-closed gate, changed HEAD, dirty worktree, hash drift, output presence, model mismatch, positive Fast/Priority evidence, or spent budget.
6. **One-shot execution.** If activated, execute the exact command once under the locked XHigh role. No retry or fallback.

No fresh audit or runtime is opened by this plan.

## Model policy

This plan task is bound as:

- requested and actual model: `gpt-5.6-sol`
- requested and actual reasoning: `ultra`
- requested service tier: `default`
- requested display speed: `Standard`
- actual service tier: `UNOBSERVABLE`
- actual speed telemetry: `UNOBSERVABLE`
- positive Fast/Priority evidence: none
- Fast/Priority permitted: no
- model gate: PASS because model/reasoning match and no positive forbidden-tier evidence exists

Unavailable service-tier or speed telemetry is not inferred from latency and is not a failure. Any positive Fast/Priority evidence or model/reasoning mismatch is terminal.

## Failure handling and no-retry rule

- An expected TDD RED is evidence, not an implementation failure.
- If the selected implementation cannot reach GREEN within the exact seven-file/two-commit boundary, if R2a/R2 topology drifts, or if any static gate fails after the final implementation state is proposed, stop. Preserve commits/evidence and open a new Ultra remediation-plan stage; do not patch around the failure or silently retry.
- If central validation or fresh audit fails, preserve its one-file receipt and open a new Ultra plan stage. Do not amend or replace the failed receipt.
- If exact-command binding fails, do not invoke the runner; open a new plan stage if remediation is needed.
- If execution is invoked and fails anywhere, budget becomes `1/1/0`. Preserve every output byte and outer receipt; no second process invocation is authorized. Open a new plan stage.

## Plan-stage acceptance checklist

- [x] Central receipt and directly relevant source/control flow read statically.
- [x] Current `10×M` versus `6×A` plus four-parent-file RED is deterministic.
- [x] Aggregate roster, final seal, and frozen origins are separate authorities.
- [x] Five falsifiable routes are compared and one minimal route is selected.
- [x] Attempt-013 Revision 2 is chosen explicitly; Attempt-014 is rejected for this gate.
- [x] Pure runner-independent helper and correct-seam regression test are specified.
- [x] Validator must call the exact helper and use a transitive AST import graph.
- [x] Runner-reaching child suites cannot be counted as runner-free authority.
- [x] Exact R2a/R2 file boundaries, receipt paths/schemas, output root, and budget semantics are locked.
- [x] Gate sequence is XHigh TDD → Ultra central → fresh Ultra audit → deterministic exact command → conditional standing auto-execution.
- [x] Current truth remains `NOT_RUN/NO/0`, output absent, budget `1/0/1`.
- [x] This stage creates only this Markdown plan and opens neither audit nor runtime.

## Next gate

`XHIGH_ATTEMPT013_REVISION2_IMPLEMENTATION_TDD_NO_RUNTIME`
