# Stage 1E Attempt-012 fresh-audit invocation remediation plan

## Material Passport

- **Origin Skill:** `experiment-agent`
- **Origin Mode:** `plan / critical-static-diagnosis`
- **Origin Date:** `2026-08-28T00:00:00+07:00`
- **Origin Date Semantics:** configured current date and `Asia/Saigon` timezone marker; no ambient-clock or host probe was used
- **Verification Status:** `UNVERIFIED`
- **Version Label:** `stage1e_e4_r6_pc2w_p1_attempt012_fresh_audit_invocation_remediation_plan_v1`
- **Upstream Dependencies:**
  - `stage1e_e4_r6_pc2w_p1_attempt012_central_static_validation_receipt_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt012_pre_runtime_authority_contract_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt012_execution_authorization_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt012_admission_observation_contract_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt011_runtime_failure_remediation_plan_v1`
  - `ars_codex_academic_research_suite_0.1.26`
- **Repro Lock:** `null` — this is a diagnosis/plan artifact, not a reproducibility result
- **Experiment Intake Declaration:** `{status: no_experiments_declared, declared_at: 2026-08-28T00:00:00+07:00, declared_by: scholar}`
- **Experiment Provenance:** `[]`

The empty experiment ledger is intentional. ARS Schema 9 defines Experiment Provenance as scholar-entered intake/alignment for experiments executed externally; it is not a validator-invocation log. No experiment, runner, runtime, materialization, training, evaluation, benchmark, or test-set access occurred in this diagnosis.

## 1. Decision

**Disposition:** `PLAN_COMPLETE_CHOOSE_A_PRESERVE_ATTEMPT012`

Choose exactly **A**: keep the fresh-audit control context on the central lineage, but replay the existing validator exactly once in a separate clean detached checkout whose `HEAD` is immutable `R1`. Only after that replay passes may the auditor create the contracted fresh-audit receipt on the central lineage.

Do not modify the validator, Attempt-012 implementation, authority documents, central receipt, or scientific pipeline. Do not issue Attempt-013. The observed failure is an audit subject-selection error, not evidence that the R1 packet or scientific implementation failed.

This plan authorizes no command execution. In particular, it is not confirmation of either the future audit-validator command or the Attempt-012 one-shot runtime command.

## 2. Provenance, model, and evidence boundary

### 2.1 ARS and repository procedures read by the main context

The main authoring context read and applied:

- ARS-Codex `0.1.26` root `SKILL.md` in full;
- `ars/experiment-agent/WORKFLOW.md` in full;
- `ars/experiment-agent/agents/code_runner_agent.md` in full;
- `ars/experiment-agent/references/ars_integration_guide.md` in full;
- the code-plan Material Passport template;
- Material Passport Schema 9 and Experiment Provenance Intake sections in `ars/shared/handoff_schemas.md`;
- `experiment_provenance_entry.schema.json`; and
- repository procedure `E:/UIT/cv/backend/.agents/skills/diagnosing-bugs/SKILL.md` in full.

No relevant `CONTEXT.md` or ADR was found under the Stage 1E area.

### 2.2 Main-context attestation and collaboration exclusion

- **Critical diagnosis/plan owner:** this task's main context.
- **Task-routing model:** `gpt-5.6-sol`.
- **Task-routing reasoning effort:** `ultra`.
- **Requested display/service class:** `Standard/default`.
- **Fast/Priority:** forbidden; neither was observed.
- **Actual service tier:** `UNOBSERVABLE`.
- **Actual speed:** `UNOBSERVABLE`; it is not inferred from latency, duration, prose, or another receipt.

Before the supplemental provenance restriction arrived, three read-only collaboration agents had been started. Their independently attested actual model/reasoning/speed was unavailable. Two had completed and one was interrupted when the restriction arrived. **All collaboration-agent messages and conclusions are excluded from this plan's evidence and decision inputs.** They made no repository writes. Every fact cited below was independently reread or recomputed by the main `gpt-5.6-sol / ultra` context from raw Git objects, committed repository files, or the source/audit task log.

### 2.3 Current-task write boundary

This task may add and commit only this file. It must not run the validator, import or invoke the runner, create a fresh-audit receipt, modify `pipeline_state`, or change any Attempt-012 source, contract, authorization, receipt, output, or scientific artifact.

## 3. Authoritative evidence

### 3.1 Commit lineage and exact deltas

| Symbol | Full commit | Parent | Exact relevant delta |
|---|---|---|---|
| `R0` | `7209966f430dc75e790d574298e65aefbe082f31` | `20337b132635dfdc30eb0b56836f91fcb723ef46` | seven Attempt-012 files added |
| `R1` | `0eca3408b8fe7b5c5217e1c3b0a4a2f025a83be5` | `R0` | five packet files modified |
| `C` | `16ac10707ca351c05b7cdd66230e12e4b331de84` | `R1` | only the Attempt-012 central static-validation receipt added |

The current worktree began clean and detached at `C`. The central commit did not modify the validator or any R1 packet file.

### 3.2 Validator identity and contract

Validator path:

`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt012_static_packet.py`

The raw validator blob is identical at `R1` and `C`:

- Git blob OID: `4dabde842dd899d68528146c02eaec54b4093f53`
- raw bytes: `17373`
- raw-Git-blob SHA-256: `b5eeeef51e3cb69b2e1b89205e10af808a21ceb76c4a80d0e10d4ea930bba184`

Its decisive source behavior is:

1. `validate_commit_shape` checks `R0` parent/write set at lines 138-141;
2. it resolves the validation subject from ambient `git rev-parse HEAD` at line 142;
3. it requires `parent(HEAD) == R0` at line 143, otherwise raising `R1_PARENT_MISMATCH`;
4. it then requires that same ambient `HEAD` to have the exact five-file R1 delta at lines 144-145; and
5. the CLI exposes only `--repo-root` at line 347; it has no explicit subject-commit argument.

Therefore the validator's present contract is: **run from a clean checkout whose ambient `HEAD` is the R1 subject**. It is not a validator for an arbitrary descendant checkout.

### 3.3 Central receipt remains valid and immutable

Central receipt path:

`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt012_central_static_validation_receipt.json`

Binding at commit `C`:

- Git blob OID: `329a5d53885961364cb0945097bdb38c557358af`
- raw Git blob bytes: `31497`
- raw-Git-blob SHA-256: `7f4d0b45392520a88801ee731cb396027c83a6160c93b79fa9af97851d17170d`

These are raw Git blob facts. A Windows checkout may have CRLF-transformed bytes and must not replace this hash domain.

The central receipt records:

- `validation_start_head = R1` and `validation_start_parent = R0` at lines 61-62;
- `validated_revision = R1` at line 294;
- aggregate static tests `110/110` at lines 407-408;
- runner imports and invocations equal `0` at lines 413-414;
- runtime false and truth state `NOT_RUN / NO / 0 / closed` at lines 425-429; and
- `final_verdict = PASS_READY_FOR_FRESH_INDEPENDENT_AUDIT` and next gate `FRESH_INDEPENDENT_STATIC_AUDIT_NO_RUNTIME` at lines 660-662.

The receipt is not evidence of scientific reproduction. It is authoritative evidence that the same immutable validator already completed against its intended R1 subject.

### 3.4 Recorded failed fresh-audit invocation

The failure is preserved in the Codex app task log, not in a committed repository receipt:

- audit task: `01a046ab-a69d-79d1-981c-29988bec7e7b`;
- execution record: `exec-bd0f55cb-db7f-46db-aeab-e30583da679d`;
- working directory: `C:\Users\ACER\.codex\worktrees\84f2\backend`;
- ambient `HEAD`: `C`;
- observed command:

```text
python -B research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt012_static_packet.py --repo-root "C:\Users\ACER\.codex\worktrees\84f2\backend"
```

- invocation count: exactly `1`;
- exit code: `1`;
- decisive traceback: `main:355 -> validate_commit_shape:143 -> require:66`;
- terminal error: `RuntimeError: R1_PARENT_MISMATCH`;
- disposition: `HANDOFF_INCOMPLETE`;
- automatic repeats/workarounds: `0`;
- fresh-audit receipt writes/commits: `0`;
- runner imports/invocations and Attempt-012 runtime commands: `0`.

The task log does not provide separately authenticated raw stdout/stderr byte hashes or an exact resolved interpreter path. This plan does not invent them.

## 4. Diagnosis under the repository diagnosing-bugs procedure

### 4.1 Existing tight red signal; no new replay

The already-recorded invocation is the Phase-1/Phase-2 feedback loop. It drives the exact failing audit boundary, is deterministic for the recorded commit graph, and produced the user's exact symptom. The present plan-only restriction and ARS no-auto-retry rule prohibit rerunning it.

The minimized reproduction has only three load-bearing facts:

1. validator subject is ambient `HEAD`;
2. validator requires `parent(subject) == R0`; and
3. audit ambient `HEAD = C`, while `parent(C) = R1`, not `R0`.

Replacing only the subject with `R1` changes the predicate to `parent(R1) = R0`. The central receipt is prior committed evidence that this intended subject proceeded through all `110/110` checks.

### 4.2 Ranked falsifiable hypotheses

| Rank | Hypothesis and prediction | Direct evidence | Disposition |
|---|---|---|---|
| 1 | The audit supplied the wrong subject through ambient `HEAD`; changing only the checkout subject from `C` to `R1` makes the parent predicate true. | `parent(C)=R1`, `parent(R1)=R0`, and validator line 143 compares ambient-head parent to `R0`. | **Confirmed root cause.** |
| 2 | Central changed the validator, so fresh audit ran different logic. If true, R1 and C validator blobs differ. | Both revisions resolve to blob `4dabde...`. | Falsified. |
| 3 | R1 lineage is malformed. If true, `parent(R1) != R0` and the earlier R1 invocation could not pass commit shape. | Git graph gives `parent(R1)=R0`; central receipt records R1 PASS. | Falsified. |
| 4 | The R1 packet or static suites regressed. If true, execution reaches packet/source/test checks and reports their stable failure code. | Failure occurs at main line 355, before source checks at line 362 and tests at line 364. | Not reached; cannot be the direct cause. |
| 5 | Runner, Docker/WSL, output, or scientific runtime failed. If true, the runner/import/runtime path is reached and leaves corresponding evidence. | Validator imports only standard-library modules and fails before any runner path; all runner/runtime counters are zero and output root is absent. | Falsified as direct cause. |

### 4.3 Exact root cause and persistence mechanism

**Root cause:** the fresh-audit invocation conflated the audit-control revision with the validator subject revision. Gate 3 correctly needs the central receipt lineage as its control/evidence context, but the existing validator is deliberately coupled to an R1 checkout. Calling it in the central checkout passed `C` implicitly as the subject, making its R1-shape guard fail by construction.

**Persistence mechanism:** every descendant of R1 whose parent is not R0 will produce the same early failure when used as ambient `HEAD`, even if its packet blobs are byte-identical. Retrying the same command at `C`, at this plan commit, or at the future audit-receipt commit cannot repair the predicate.

**Confidence:** high for the direct cause and failure classification. The only provenance limitation is that the failed process capture is an app task record rather than a committed receipt.

## 5. Audit invocation versus Attempt-012 execution attempt

The failed call is one **fresh-audit validator invocation**, not an Attempt-012 execution attempt.

The governing design invariant in the prior remediation plan says: “Any runner process invocation consumes the sole Attempt-012 attempt,” including a pre-root runner failure. Gate 4 separately defines the one-shot launch as the Attempt-012 runner process after exact-command confirmation. The failed executable was the static validator, and failure occurred before importing or invoking the runner.

| Counter/state after the failure | Value |
|---|---:|
| recorded fresh-audit validator invocations | `1` |
| recorded failed fresh-audit validator invocations | `1` |
| automatic repeats of that invocation | `0` |
| Attempt-012 runner imports | `0` |
| Attempt-012 runner process invocations | `0` |
| Attempt-012 one-shot execution attempts consumed | `0 of 1` |
| runtime/host commands | `0` |
| output root creations | `0` |
| result/test/accepted rows | `NOT_RUN / NO / 0` |

The ARS rule “never auto-retry” means the failed audit task must not silently rerun the command, change checkout, add a workaround, or launch a capture replay. It did not. A later command under this committed remediation plan is a newly disclosed, separately confirmed audit invocation with a corrected subject; it is not an automatic experiment retry and does not consume the runtime one-shot. Nevertheless, that corrected validator command is itself limited to one call. If it fails, the new audit stops `HANDOFF_INCOMPLETE`; another call requires a new explicit diagnosis and user decision.

## 6. Required A/B/C evaluation

| Option | Required change | Consequence | Decision |
|---|---|---|---|
| **A. Central audit context + separate immutable R1 replay** | No Attempt-012 implementation change. Add only operational scratch for a detached R1 checkout, then one fresh-audit receipt after PASS. | Preserves the already-audited packet and central receipt; corrects only subject selection. | **Chosen.** |
| **B. Add explicit subject commit to a new validator revision** | Modify a packet file and redesign commit-shape semantics in a new revision. | The old R1 and central receipt no longer certify the changed validator; a new packet revision, central validation, hashes, and fresh audit would be required. | Rejected as unnecessary scope expansion. |
| **C. Issue Attempt-013** | Mint new attempt paths, schemas, authorization, packet, receipts, and later runtime command. | Treats an audit-invocation bug as a scientific/runtime attempt failure despite zero runner invocations. | Rejected as overengineering. |

Option B may be a future audit-interface hardening proposal only if policy later forbids separate subject checkouts. It is not a fallback in the selected remediation. Option C is appropriate only after a real Attempt-012 runner invocation or a proven semantic packet defect, neither of which occurred.

## 7. Selected minimal path A

### 7.1 Lineage symbols

- `R0 = 7209966f430dc75e790d574298e65aefbe082f31`
- `R1 = 0eca3408b8fe7b5c5217e1c3b0a4a2f025a83be5`
- `C = 16ac10707ca351c05b7cdd66230e12e4b331de84`
- `P =` the commit containing this plan; its full hash is externally resolved after commit because a commit cannot self-contain its own hash
- `A =` the future exact-one-file fresh-audit receipt commit

Required future chain:

```text
R0 <- R1 <- C <- P <- A
```

`P` is an interstitial documentation/remediation commit, not a packet revision. `A` must record `A^=P`, `P^=C`, `C^=R1`, and `R1^=R0` rather than pretending it is a direct child of `C`. The execution packet remains `R1`.

### 7.2 Fresh audit control context

Open one new, independent audit context at `P`:

- model `gpt-5.6-sol`;
- reasoning `ultra`;
- requested `Standard/default`;
- Fast/Priority forbidden;
- actual service tier/speed recorded as `UNOBSERVABLE` if no authoritative telemetry is exposed; and
- no collaboration agent may own or supply the critical diagnosis, replay adjudication, or receipt decision.

Before any process invocation, the audit owner must directly verify:

1. current central/control `HEAD == P` and the full chain above;
2. `P` has exactly one added file: this plan;
3. the central worktree is clean;
4. the central receipt at `P` is still exact blob `329a5d...`, `31497` raw bytes, SHA-256 `7f4d0b...`;
5. no fresh-audit receipt exists yet;
6. the Attempt-012 output root is absent; and
7. runtime authorization remains false and the exact runtime command remains unconfirmed.

### 7.3 Separate R1 subject checkout

Resolve an explicit empty scratch path `<ABS_R1_AUDIT_ROOT>` outside both the central tracked tree and the Attempt-012 output root. The planned materialization command shape is:

```text
git worktree add --detach <ABS_R1_AUDIT_ROOT> 0eca3408b8fe7b5c5217e1c3b0a4a2f025a83be5
```

This is operational scratch plus Git administrative metadata, not a tracked repository change. Before the validator call, verify in that checkout:

- `HEAD == R1` and `HEAD^ == R0`;
- exactly one parent for both R1 and R0;
- `git status --porcelain=v1 --untracked-files=all` is empty;
- Git top-level and process CWD both equal `<ABS_R1_AUDIT_ROOT>`;
- validator blob OID/bytes/SHA-256 equal the values in section 3.2;
- the exact R0 and R1 deltas match seven additions and five modifications;
- no central receipt or plan is treated as part of the R1 packet; and
- the Attempt-012 output root is absent in the R1 checkout.

Do not patch, copy, or synthesize a validator. Use the validator from the R1 checkout itself.

### 7.4 Exact validator command shape, plan only

Resolve `<ABS_PYTHON>` to the intended Python interpreter before execution. Show the fully substituted tuple `(cwd, argv)` to the user and obtain a new explicit confirmation for this audit invocation. That confirmation is not the Attempt-012 runtime token.

Planned direct-process tuple:

```text
cwd  = <ABS_R1_AUDIT_ROOT>
argv = [
  <ABS_PYTHON>,
  -B,
  research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt012_static_packet.py,
  --repo-root,
  <ABS_R1_AUDIT_ROOT>
]
```

No shell wrapper, `-c`, `-m`, alternate subject, supplemental harness, or modified argument order is allowed. Launch exactly once and capture exit code, stdout, and stderr in that same process call. A second “capture replay” is forbidden.

The central/control checkout remains at `P` and read-only while this child process runs in the R1 checkout.

### 7.5 PASS adjudication and receipt creation

Only an exit code `0` plus one strict JSON result satisfying every acceptance predicate in section 10 permits receipt authoring. The audit owner must then return to the central/control checkout, reverify `HEAD == P` and a clean worktree, and add only:

`research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt012_fresh_independent_audit_receipt.json`

The receipt must use the contracted values:

- schema `stage1e-e4-r6-pc2w-p1-attempt012-fresh-independent-audit-receipt-1.0`;
- stage `E4-R6-PC2W-P1-ATTEMPT012`;
- verdict `PASS_PC2W_P1_ATTEMPT012_FRESH_INDEPENDENT_AUDIT_READY_FOR_EXACT_COMMAND_CONFIRMATION`;
- packet commit `R1` and the exact five packet-artifact facts already bound by the central receipt;
- `central_validation_receipt_git_blob_sha256 = 7f4d0b45392520a88801ee731cb396027c83a6160c93b79fa9af97851d17170d`;
- `runtime_commands_executed = false`; and
- `write_set` containing only the fresh-audit receipt path.

It must additionally disclose both audit observations without conflation:

1. the historical central-HEAD invocation: one call, exit `1`, `R1_PARENT_MISMATCH`, no repeat; and
2. the remediated R1-subject invocation: one newly confirmed call and its exact captured result/hashes.

The historical failure belongs in audit-invocation provenance/counters, not `experiment_provenance` and not the Attempt-012 execution-attempt counter.

Commit the receipt as `A`, with `A^ == P` and exact delta `A <tab> <fresh-audit-receipt-path>`. Do not amend or rewrite `C` or `P`. After commit, return full `A`, full parent `P`, exact write set, audit receipt Git blob OID, raw bytes, and raw-Git-blob SHA-256.

## 8. Exact contexts and model policy

| Phase | Context | Model/reasoning | Authority and boundary |
|---|---|---|---|
| This critical diagnosis/plan | Current main task only | `gpt-5.6-sol / ultra`, requested Standard/default | Creates only this plan; collab outputs excluded. |
| Remediated fresh audit judgment | New independent central/control context at `P` | `gpt-5.6-sol / ultra`, requested Standard/default | Owns direct evidence reading, one R1 replay adjudication, and receipt decision. |
| Validator child | Direct Python process in detached R1 checkout | no LLM/model role | Mechanical static validation only; no runner/runtime. |
| Fresh-audit receipt author/committer | Same independent audit context after PASS | `gpt-5.6-sol / ultra`, requested Standard/default | Writes exactly one receipt file on central lineage. |
| Later exact runtime-command assembly | New central/user-owned judgment checkpoint at `A` | `gpt-5.6-sol / ultra`, requested Standard/default | Renders command only after both receipts pass and asks for exact confirmation. |
| Later one-shot mechanical execution | Existing locked execution role | `gpt-5.6-sol / xhigh`, requested Standard/default | May execute only after the separate exact-command confirmation; unchanged by this plan. |

For every LLM phase, an actual model or reasoning mismatch, or observed Fast/Priority routing, is terminal. Absence of authoritative service-tier/speed telemetry is recorded as `UNOBSERVABLE` and must never be promoted to proof of Standard speed.

## 9. Exact read/write boundary

| Location/context | Reads allowed | Writes allowed | Explicitly forbidden |
|---|---|---|---|
| Current plan task | Git metadata, raw committed blobs, repository procedures, source/audit task log | this plan file and its one-file commit only | validator/tests/runtime, receipt, source, state, output, merge/cherry-pick/push |
| Future central/control checkout at `P` before replay | lineage, raw R0/R1/C/P blobs, central receipt, contracts, absence predicates | none | running validator against `P`; any tracked mutation |
| Detached R1 checkout | R0/R1 packet/support/test files required by the unmodified validator | only operational checkout materialization; validator must create no tracked/untracked/bytecode/output file | source edits, receipt/plan writes, runner import/invocation, runtime/host/network actions |
| Future central/control checkout after replay PASS | same reads plus the single captured validator result | one fresh-audit receipt, followed by one exact-one-file commit | any other file, amendment of existing commits/receipts, runtime |

The detached worktree's directory and Git worktree metadata are the only pre-replay scratch writes. They must be outside the tracked write set and must not overlap the output root. No Docker/WSL/Hyper-V reset, service action, framework, dependency, network, installation, container, materialization, training, evaluation, benchmark, or test-set action is part of this plan.

## 10. Acceptance tests

### 10.1 Pre-invocation acceptance

All must pass before confirmation of the remediated validator command:

1. `P^=C`, `C^=R1`, `R1^=R0`, with exact full hashes and single-parent counts.
2. `P` adds only this plan; `C` adds only the central receipt; R1/R0 deltas remain exact.
3. Central receipt raw binding remains OID `329a5d...`, bytes `31497`, SHA-256 `7f4d0b...`.
4. Central/control and R1 worktrees are clean.
5. R1 checkout `HEAD=R1`, parent `R0`, validator blob `4dabde...` / `17373` / `b5eee...`.
6. Fresh-audit receipt and Attempt-012 output root are absent.
7. Runtime authorization is false, exact runtime command is unconfirmed, runner attempts consumed are zero.
8. Audit model/reasoning are `gpt-5.6-sol / ultra`; Fast/Priority is not observed; service tier/speed are recorded without inference.
9. Every command placeholder is resolved and the user confirms the exact audit `(cwd, argv)` tuple.

### 10.2 Single-invocation acceptance

The one captured validator result must prove:

- exit code `0` and strict JSON root object;
- `validated_revision == R1`;
- `r0_commit == R0`, `r1_parent == R0`, and exact R0/R1 write sets;
- exact frozen R0 fixture hashes and exact R1 packet-artifact hashes;
- all six named suites pass and aggregate is exactly `110/110`;
- strict JSON files `3/3`, required AST/source predicates, and no skip/xfail drift;
- `new_or_modified_python_bytecode_files == 0`;
- runner imports/invocations, runtime/host probes, automatic retries, and fallbacks all equal `0`;
- output root absent;
- `runtime_commands_executed == false`;
- `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, benchmark admission closed; and
- exact stdout/stderr byte counts and hashes captured from the single call.

### 10.3 Receipt and lineage acceptance

Before committing `A`:

1. recheck central/control `HEAD=P`, clean except for the one intended receipt;
2. strict-parse the receipt as UTF-8 JSON with no duplicate or case-fold duplicate keys and no non-finite numbers;
3. verify exact contracted schema, stage, expanded PASS verdict, packet commit/facts, central raw SHA link, runtime-false field, and one-path write set;
4. record Material Passport `experiment-agent / validate-static-fail-closed`, the actual Ultra context, `no_experiments_declared`, and `experiment_provenance=[]`;
5. record the failed and successful audit invocations separately and keep Attempt-012 runner attempts at zero;
6. prove central receipt bytes are unchanged and reachable at `A`;
7. prove `git diff --check` passes and no `.pyc`, `__pycache__`, output, or extra file exists; and
8. after commit, prove `A^=P` and `A` adds exactly the fresh-audit receipt.

## 11. Fail-closed conditions

Stop `HANDOFF_INCOMPLETE`, create no PASS audit receipt, request no runtime command confirmation, and do not switch to B or C in the same stage if any of the following occurs:

- any lineage, parent-count, delta, blob OID, raw byte count, or raw SHA-256 mismatch;
- central receipt drift, checkout-byte substitution for raw Git bytes, or missing central-link proof;
- dirty central or R1 checkout, unresolved path, overlapping scratch/output root, or pre-existing output/receipt;
- inability to pin the isolated checkout exactly to R1;
- unresolved exact interpreter/CWD/argv or absent user confirmation for the audit command;
- wrapper use, argument drift, missing `-B`, more than one validator call, capture replay, retry, or fallback;
- nonzero validator exit, malformed/non-strict output, wrong subject revision, any test count other than `110/110`, or any acceptance predicate mismatch;
- any source/contract/receipt mutation in R1 scratch, bytecode/cache/output write, or unexpected central write;
- any runner import/invocation, Attempt-012 runtime command, host probe, Docker/WSL/Hyper-V action, network/install/container action, materialization/training/evaluation/benchmark/TEST access;
- model/reasoning mismatch or observed Fast/Priority routing; or
- an attempt to treat plan approval or audit confirmation as runtime authorization.

If the isolated R1 mechanism is unavailable, stop and return for a new decision. Do not silently edit the validator or mint Attempt-013.

## 12. Preservation of the central receipt and one-shot runtime authorization

The central receipt remains exactly at `C`, immutable and hash-bound. `P` adds documentation only. `A` adds the contracted fresh-audit receipt only. Neither later commit changes packet commit `R1`, central receipt content, authority documents, runner, validator, output root, or scientific artifacts.

The failed validator call consumed no Attempt-012 runner attempt. The remediated R1 validator call also consumes no Attempt-012 runner attempt. The existing runtime budget therefore remains `0 of 1 consumed`, with automatic retry and fallback both zero.

Return to the exact-runtime-command confirmation checkpoint only after all of the following are true:

1. `A` is committed with the exact parent/write-set/blob facts above;
2. both contracted receipts are reachable as exact raw Git blobs at execution head `A` and their hashes are externally reported;
3. the central receipt is PASS and the fresh-audit receipt has the exact expanded PASS verdict;
4. execution checkout `HEAD == A`, Git top-level equals the proposed working directory, and the worktree is clean;
5. output root remains absent;
6. runtime authorization remains false/unconfirmed until the next checkpoint;
7. no prohibited counter has changed; and
8. a central/user-owned Ultra judgment context renders the fully resolved Attempt-012 runner command with `--packet-commit R1`, `--expected-head A`, both receipt paths/raw hashes, and the existing Attempt-012 confirmation token.

The user must then separately confirm that exact runtime `(working directory, argv)` tuple. The confirmation for this plan, the audit validator, any earlier attempt, or a placeholder command is invalid. Only the subsequent direct runner process invocation consumes the one-shot Attempt-012 execution attempt.

## 13. Final truth state

- Root cause: `AUDIT_CONTROL_HEAD_USED_AS_R1_VALIDATION_SUBJECT`.
- Selected remediation: `A_SEPARATE_IMMUTABLE_R1_SUBJECT_CHECKOUT`.
- Attempt-012 implementation status: unchanged from central static PASS; fresh audit still pending.
- Fresh-audit receipt: absent.
- Attempt-012 runner/runtime: not run.
- Experiment Provenance: no experiment declared or executed.
- `RESULT_STATUS`: `NOT_RUN`.
- `TEST_SET_OPENED`: `NO`.
- `ACCEPTED_RESULT_ROWS`: `0`.
- Benchmark admission: closed.
- Next permitted gate: a newly confirmed, exactly-once R1-subject fresh static audit under this plan.

No Docker/WSL reset, validator framework, new attempt, scientific implementation change, or runtime action is warranted by the observed failure.
