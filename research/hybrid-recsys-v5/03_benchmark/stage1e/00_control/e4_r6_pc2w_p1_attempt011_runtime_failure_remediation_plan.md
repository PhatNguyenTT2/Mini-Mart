# Stage 1E Critical — Attempt-011 runtime failure remediation plan

## Verdict

`COMPLETE_FAIL_CLOSED_READY_FOR_CENTRAL_IMPLEMENTATION`

This verdict means that the direct pre-output failure site is proven from committed bytes and that a fail-closed implementation plan is ready for central. It does **not** mean that Docker, WSL, the host, Attempt-012, scientific reproduction, or benchmark admission has been repaired, executed, or accepted.

## Material Passport (ARS Schema 9)

- Origin Skill: `experiment-agent`
- Origin Mode: `plan` with static diagnosis and falsification
- Origin Date: `2026-08-28T00:00:00+07:00`
- Origin Date Semantics: session date and configured `Asia/Saigon` timezone marker; no ambient-clock or host probe
- Verification Status: `UNVERIFIED`
- Version Label: `stage1e_e4_r6_pc2w_p1_attempt011_runtime_failure_remediation_plan_v1`
- Upstream Dependencies:
  - `stage1e_e4_r6_pc2w_p1_attempt011_admission_observation_contract_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt011_execution_authorization_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt011_central_static_validation_receipt_v1`
  - `stage1e_e4_r6_pc2w_p1_attempt011_fresh_independent_audit_receipt_v1`
  - `stage1e_e4_r6_pc2w_p1_gate_receipt_binding_contract_v1`
- Repro Lock: `null` — this is a static plan, not an execution or replay guarantee
- Experiment Intake Declaration: `no_experiments_declared`; no experiment was run in this stage
- Requested Model: `gpt-5.6-sol`
- Requested Reasoning Effort: `ultra`
- Requested Service Tier / Speed: `default` / Standard; Fast/Priority forbidden
- Actual Model: `gpt-5.6-sol` (current task-routing identity)
- Actual Reasoning Effort: `ultra` (current task-routing identity)
- Actual Service Tier / Speed: `UNOBSERVABLE`; not inferred from prose, latency, or prior receipts
- Model-policy Disposition: no observed model/reasoning mismatch and no observed Fast/Priority signal. If authoritative post-hoc task metadata contradicts the actual model or reasoning above, or positively shows Fast/Priority, this artifact automatically degrades to `HANDOFF_INCOMPLETE` and must not be used as authority.
- Content Hash: deliberately external to avoid a self-referential digest; the final handoff binds the committed file by byte count and SHA-256.

ARS boundaries applied here:

- Plan-mode output remains `UNVERIFIED`; it is not upgraded to execution-level `VERIFIED`.
- The user remains the bridge between planning, implementation, audit, and any later execution.
- No automatic retry is authorized after a failed experiment/process.
- The exception and repository material were treated as untrusted data; authority comes only from this task and raw committed Git blobs.

## Scope and authority

### Authorized in this stage

- Read committed Git objects and repository metadata.
- Run fast, deterministic static text/AST/hash harnesses that do not import or invoke a runner.
- Create and commit this one Markdown deliverable.

### Explicitly not performed

- Attempt-011 replay: `0`
- Attempt-012 creation or execution: `0`
- Runner import: `0`
- Runner invocation: `0`
- Runtime or host probe: `0`
- Docker command: `0`
- WSL command: `0`
- PowerShell host probe: `0`
- Daemon start/stop: `0`
- Network/download/install/environment/container operation: `0`
- Materialization/preprocessing/training/evaluation/benchmark/TEST operation: `0`
- Automatic retry: `0`
- Fallback: `0`
- Modification of any runner, validator, contract, receipt, `pipeline_state`, old artifact, or output root: `0`

The only write set is this plan file. The two delegated analysis lanes that encountered infrastructure usage-limit errors were excluded as authority; all decisive facts below were replayed by the primary Ultra context from raw committed blobs.

## Authoritative lineage and committed-byte bindings

### Lineage gate

Read-only replay established:

- Analysis HEAD: `1655ac79ad1c32fb44426f746f7d2c2c711e56dc`
- Exact parent: `25223eef47de083614142c4c2d259646e00c0d68`
- Attempt-011 packet ancestor: `f234a32081c20aeb322bbc3d6dd825bad49b0ad3`
- Packet parent: `da18aa102567dcfef7296fafa223bcaef065e934`
- `git merge-base --is-ancestor f234a32081c20aeb322bbc3d6dd825bad49b0ad3 HEAD`: exit `0`
- Worktree before writing: clean, including untracked files
- Deliverable before writing: absent
- Committed `CONTEXT.md`: none found
- Committed ADR/architecture-decision record: none found
- Analysis domain: `HEAD:<path>` raw committed blobs. Working-tree copies were not used as evidence for source contents.

### Key blob bindings

| Artifact | Git blob OID | Raw bytes | Raw SHA-256 |
|---|---:|---:|---|
| `e4_r6_pc2w_p1_attempt011_admission_observation_contract.json` | `c8396ea7de73196decf8c14599558d096645e187` | 6,615 | `7a5143eeae7ef29cb82899316591808a625ed6359e0365e4444fe9140e96d75e` |
| `e4_r6_pc2w_p1_attempt011_execution_authorization.json` | `590d5430c83bd5a473dca419412cf32387a1ebce` | 3,419 | `948f66c52e8cda1e3c4f8db8780dd803747f74f53e1f3e04dbf8a9d786f297ca` |
| `execute_e4_r6_pc2w_p1_attempt011_admission_observation.py` | `da57f2f70046951eede1044fcc013ece30fb6564` | 10,339 | `f24aed180bab11a96781a8c1a33b6b2bb5a1f09e68fada83d27eabea2fa58c96` |
| `execute_e4_r6_pc2w_p1_attempt010_admission_observation.py` | `9e9988560a3a420d63a75121cf5b9e741099c836` | 9,023 | `437fffce0c0a8b459920ae12808692d37c07b1e63dc4704d2efdc6306ffe76f9` |
| `execute_e4_r6_pc2w_p1_attempt008_admission_observation.py` | `ab73c9fbb9d4096d0f4ee21723ec37bc0fbda60c` | 50,611 | `c51c0fc6b0e089bb478fdc391979cfa0add8051f4723ff067ed81dd4c6630a89` |
| `execute_e4_r6_pc2w_p1_attempt004_query_only.py` | `24471d05cf4880cf3acc91399d63254a349766de` | 52,528 | `66c964e40cc23cee0bda59b8afc949c6fd3189c3c821e2eb98ffd4323c3c0e13` |
| `e4_r6_pc2w_p1_attempt010_command_interface.py` | `352ff2eee5f7ed095fba633328a822b0da798444` | 4,159 | `970f5b5269c36dc3f2e0e1639db591adbd4623aeb6f97b86e049957dde1a9559` |
| `e4_r6_pc2w_p1_gate_receipt_binding.py` | `96caf3c56ae99bd6578bfca624566bca1c036ad2` | 10,298 | `8a1ea9f854fbe81c4873b326db4a1a82b31c6557c4efb92c0e3332ecdddaa526` |
| `test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py` | `38cc5a9987629cf901aea0fc84303ad23693548a` | 28,206 | `41e1c30a784368b713532899a86feec3fe538a1b85388621f7431a8c9eaa8c51` |
| Attempt-011 central static receipt | `cf399a3e015c5eeee6c9f8e67159bb8b202a869a` | 16,495 | `efcb7bb05b2159ff3ff8468a4ed14e4b821f4d6e634d434ad710cb8089aac66d` |
| Attempt-011 fresh independent audit receipt | `e318c22fa9505a00e02e45ac7ff4f901dcca690d` | 26,886 | `bb9dd0c7c3dbd80bbb80bf881c53027c1e002d052b83adc7d1e631418710713e` |

The Attempt-011 central and audit receipts are evidence subjects, not conclusions accepted on trust. Their raw packet bindings are useful, but their prior PASS verdicts do not override the now-observed runtime failure.

## Supplied observation and static reconciliation

### User-supplied, single observation

- Attempt-011 was confirmed and launched exactly once; no retry/fallback.
- Reported process/tool exit code: `1`; elapsed about `0.31 s`.
- Emitted verdict: `HANDOFF_INCOMPLETE`.
- `error_type=RuntimeError`.
- `error_sha256=8bd399659a57c2a6bbf009029c132a6720f7fdd15367a3de3e77dde4dcc1c402`.
- `exception_message_persisted=false`.
- `failure_packet_persisted=false`.
- `automatic_retry_count=0`, `fallback_count=0`.
- `benchmark_admission_opened=false`.
- `result_status=NOT_RUN`, `test_set_opened=NO`, `accepted_result_rows=0`.
- Attempt-011 output root remained absent; Git remained clean.

No conclusion from an earlier remediation task was accepted. The supplied hash and symptom were independently mapped to committed source below.

### Exit-code limitation

The committed Attempt-011 catch block emits the observed envelope and then executes `raise SystemExit(2)` at line 279. Therefore the supplied exit code `1` is not the raw Python exit predicted by that catch path. An outer shell/tool may have normalized it, but there is no committed exact-launch receipt that proves the transport. The observed `1` is preserved as a fact; raw-child-versus-wrapper exit provenance remains unresolved. This does not weaken the exact exception-hash/site binding.

## Static feedback loop

### Feedback-loop goal

Catch the exact supplied error hash, prove that its reachable throw occurs before output-root initialization, and do so without importing/invoking the runner or touching the host/runtime.

### Commands run

Lineage and cleanliness:

```powershell
git status --porcelain=v1 --untracked-files=all
git show -s --format=HEAD=%H%nPARENTS=%P HEAD
git merge-base --is-ancestor f234a32081c20aeb322bbc3d6dd825bad49b0ad3 HEAD
git ls-tree -r --name-only HEAD | rg -i '(^|/)CONTEXT\.md$|(^|/)(adr|adrs)(/|$)|architecture.*decision|decision.*record'
```

Broad literal-hash scanner, using only committed grep output and SHA-256:

```powershell
$targetHash='8bd399659a57c2a6bbf009029c132a6720f7fdd15367a3de3e77dde4dcc1c402'
$candidateRows=git grep -n -F 'raise RuntimeError(' HEAD -- 'research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/*.py'
$hitRows=@()
foreach($candidateRow in $candidateRows){
  if($candidateRow -match 'raise RuntimeError\("([^"]*)"\)'){
    $messageText=$Matches[1]
    $candidateHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($messageText))).ToLowerInvariant()
    if($candidateHash -eq $targetHash){
      $hitRows += [pscustomobject]@{signal='RED';error_sha256=$candidateHash;source=$candidateRow;exception_message='<REDACTED:sha256-bound>'}
    }
  }
}
```

The tightened reachability harness read five raw `HEAD:<path>` sources with `git show`, followed the Attempt-011 -> Attempt-010 -> Attempt-009 -> Attempt-008 import chain, extracted the root-guard literal, hashed it, and asserted ordering/state predicates. It did not import Python modules.

### Redacted output

```json
{
  "signal": "RED",
  "target_error_sha256": "8bd399659a57c2a6bbf009029c132a6720f7fdd15367a3de3e77dde4dcc1c402",
  "derived_error_sha256": "8bd399659a57c2a6bbf009029c132a6720f7fdd15367a3de3e77dde4dcc1c402",
  "derived_message": "<REDACTED:sha256-bound>",
  "checks": {
    "import_chain_reaches_attempt008": true,
    "legacy_root_is_absolute_literal": true,
    "root_guard_precedes_output_root": true,
    "failure_context_unavailable_at_guard": true,
    "attempt011_does_not_rebind_root": true,
    "exact_error_hash": true
  },
  "runtime_or_host_probe_count": 0,
  "runner_import_or_invocation_count": 0
}
```

Properties of the loop:

- Red-capable: it asserts the supplied `RuntimeError` hash, not merely a nonzero outcome.
- Deterministic: all inputs are exact blobs at one fixed commit.
- Fast: the tightened run completed in approximately `1.4 s`.
- Agent-runnable: no human step, external service, runtime process, or working-tree source read.
- Minimal: the load-bearing facts are the reachable import chain, the inherited root literal, the combined root/CWD guard, and its position before output initialization.
- Green criterion for Attempt-012: its candidate packet must bind one explicit committed root/working-directory authority, derive expected argv from immutable facts rather than the actual argv, and rebind or replace the inherited singleton before calling `legacy.main()`. Historical Attempt-011 remains immutably RED and is retained as the regression fixture.

## Ranked hypotheses and falsification

| Rank | Hypothesis | Prediction | Falsification probe/result | Disposition |
|---:|---|---|---|---|
| 1 | The inherited singleton execution-root / ambient-CWD predicate rejected the launched tuple before output-root creation. | A reachable literal `RuntimeError` before `output_root.mkdir` hashes exactly to the supplied digest; Attempt-011 reaches that legacy function without rebinding the root. | Tightened committed-blob harness satisfies every prediction and derives the exact digest. | **Confirmed direct cause.** |
| 2 | The Attempt-010 command interface rejected `-B`, runner path, argument order, or duplicates. | `type(exc).__name__` would be `CommandInterfaceError`, or its stable code would hash to a different value, before `legacy.main()`. | Supplied type is exactly `RuntimeError`; the target digest maps to the later legacy root guard. | Falsified as direct cause. Command semantics remain a latent blocker. |
| 3 | Central/fresh-audit receipt binding or frozen-input validation failed. | Failure would be `GateReceiptBindingError` or one of the frozen-hash `RuntimeError` messages, after root/HEAD/command predicates; hash would differ. | Exact target is thrown at the earlier root guard; receipt/frozen branches are not reached. | Falsified as direct cause. New receipts/hashes are still mandatory for Attempt-012. |
| 4 | The retained model-policy predicate failed. | After root succeeds, legacy lines 756-766 reject the current authorization shape with SHA-256 `305f5e7fa496d5b5b016e54210a3f7584d606ad3c88426b1b431d2ea9d691350`. | Supplied digest is different and control stops at line 670. | Falsified as direct cause; **confirmed latent blocker** by static schema comparison. |
| 5 | The immutable output root already existed or a host probe failed. | Output-root error would hash to `32e5d559b196e68649c8b962cb7173256c0eadac2cfdb0f06e311d66b23b1792`, or a probe receipt/context would exist after line 776. | Supplied root is absent; exact target occurs at line 670, before root computation/creation or any probe. | Falsified. |

## Proven direct cause

Attempt-011 line 19 aliases `legacy = previous.previous.legacy`; line 245 calls `legacy.main()`. Attempt-010 imports Attempt-009 as `previous`; Attempt-009 imports Attempt-008 as `legacy`. The reachable runtime body is therefore `execute_e4_r6_pc2w_p1_attempt008_admission_observation.py::main`.

In that committed blob:

1. Line 668 resolves `args.repo_root`.
2. Lines 669-670 evaluate a combined predicate:
   - resolved `repo_root` must equal inherited `EXPECTED_EXECUTION_ROOT`; and
   - resolved ambient `Path.cwd()` must equal resolved `repo_root`.
3. Failure raises the statically recovered literal `"execution root or working directory mismatch"`; its UTF-8 SHA-256 is exactly the supplied `8bd399...c402`.
4. Attempt-008 inherits `EXPECTED_EXECUTION_ROOT` through Attempt-006 from Attempt-004 line 33, where it is the absolute singleton `E:\UIT\cv\backend`.
5. Attempt-011 configuration lines 208-228 rebind packet, receipt, output, and command identifiers, but never rebind or replace `EXPECTED_EXECUTION_ROOT`.
6. Attempt-011 constructs `expected_normalized` from ambient `Path.cwd()` and the already supplied `sys.argv` at lines 233-240. This checks process shape but does not establish a semantic root authority.

**Unique direct cause:** the inherited singleton execution-root / ambient-CWD binding guard failed before output-root initialization. The hash proves that combined predicate, not a receipt, model, Docker, WSL, or cleanup failure.

Because the runtime envelope stored only the hash and did not persist `repo_root` or `cwd`, static evidence cannot distinguish which operand was unequal. It would be an overclaim to state that a particular operand or a particular worktree path was the actual runtime value. The central receipt's validator command in another Codex worktree proves only that static validation was worktree-portable; it is not evidence of Attempt-011's runtime CWD.

### Why prior static gates missed it

- `test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py` builds synthetic ordered arguments with `Path.cwd()` but has no test for `EXPECTED_EXECUTION_ROOT` or the combined root predicate.
- The Attempt-011 validator checks receipt order, packet hashes, model-policy document equality, AST syntax, and retained suites, but has no root-authority predicate.
- The command interface derives its expected tail from `sys.argv[1:]`; it detects flag/order drift but is tautological with respect to semantic values already present in the actual command.
- Consequently, 98 synthetic/static tests could pass while the first reachable legacy root guard remained incompatible with the launched tuple.

## Persistence mechanism

The two `false` persistence fields are mechanically explained and are not evidence of a Docker/WSL cleanup failure:

1. Attempt-008 initializes `_FAILURE_CONTEXT = None` at line 181.
2. The root/CWD guard raises at line 670.
3. `output_root` is computed only at line 729, created at line 776, and `_FAILURE_CONTEXT` is populated at lines 777-785.
4. Attempt-011 catches the exception and calls `legacy.persist_failure_packet(...)` at lines 254-257.
5. Attempt-008 `persist_failure_packet` lines 572-575 immediately returns `False` when `_FAILURE_CONTEXT is None`; it has no trusted output root on which to write.
6. Attempt-011 hard-codes `"exception_message_persisted": False` at line 266 and emits only `SHA256(str(exc))` at line 265.

Thus:

- `exception_message_persisted=false` is an intentional redaction property of the outer envelope.
- `failure_packet_persisted=false` follows from safe pre-root ordering, not from a failed attempt to write four files.
- Moving output creation ahead of root authority would be unsafe and is **not** the remediation. Attempt-012 should retain zero output writes on an untrusted-root failure and use an explicitly authorized outer control receipt to record any pre-root failure after the one-shot process ends.

## Latent blockers after the direct fix

These are separate from the direct cause. None may be used to rewrite the Attempt-011 diagnosis.

| Area | Static status | Evidence and risk | Attempt-012 requirement |
|---|---|---|---|
| Authority/root binding | **FAIL; direct and still latent** | Fixed absolute root is inherited while the wrapper derives runner path from ambient CWD and actual argv. No committed semantic root authority is consumed before `legacy.main()`. | One committed root-authority record must bind absolute root, CWD, Git top-level, runner containment, output containment, packet commit and expected HEAD. Rebind/replace the legacy singleton only from that record, never solely from `--repo-root`. |
| Central/fresh-audit receipt binding | **PASS for immutable Attempt-011 bytes, non-transferable** | Generic binding uses raw blobs at execution HEAD and binds stage/schema/verdict/packet facts plus central-link SHA. Any Attempt-012 change invalidates the old packet and verdict scope. | Mint new Attempt-012 schemas, packet facts, central receipt and fresh audit receipt. Old Attempt-011 receipts are historical evidence only. Verify exact one-file receipt commits and ancestry in addition to document predicates. |
| Model-policy schema/predicate | **FAIL after root fix** | Attempt-011 auth/contract use `requested_reasoning_effort=high`, split `actual_*` fields and no fresh-audit keys. Retained Attempt-008 expects `max`, `requested_display_name`, fresh-audit fields and combined `actual_model_reasoning_and_service_tier`. The next reachable branch will fail with the distinct hash in Hypothesis 4. | Define one canonical role-aware schema and one pure predicate. Plan/judgment/audits require Sol Ultra Standard; locked execution may require Sol XHigh Standard. Actual model/reasoning mismatch or observed Fast/Priority must stop. Speed `UNOBSERVABLE` is recorded, never inferred. |
| Frozen-input hashes | **PASS only for current immutable set; blocked on any change** | Attempt-010 and Attempt-011 adapters freeze exact SHA-256 values. Editing a frozen old helper would intentionally trip validation. | Add new Attempt-012 support files instead of mutating old ones; freeze raw bytes/SHA-256 and explicit roster at the new packet commit. Recompute through raw Git blobs, never checkout-normalized content. |
| Command interface | **PARTIAL / FAIL semantically** | `-B`, Python executable, script form and order are checked, but Attempt-011's expected arguments include `*sys.argv[1:]`, so root/head/receipt values are not independently derived authority. Raw child exit versus wrapper exit is also unbound. | Derive the complete expected argv from committed authority plus freshly hash-bound receipt locators. Confirm the tuple `(working_directory, exact argv)`. Record raw-child and outer-tool exit separately. Reject shell wrappers, `-c`, `-m`, unknown/duplicate/reordered args and value drift. |
| Output immutability | **PASS with a documented pre-root gap** | Exists check and `mkdir(..., exist_ok=False)` precede all probes; no `rmtree` path. Pre-root failures intentionally cannot persist inside an untrusted root. | Preserve no-write pre-root behavior; once created, output root is immutable and exactly four files. Add a separately authorized control failure receipt for a pre-root failure; never reuse/delete the attempt root. |
| Cleanup closure | **STATIC PASS, runtime unverified** | Retained source has one `F00` then one nested-finally `F01`, followed by A/B/C snapshots, stability and pre-start equality conditions. Existing tests are largely structural/faked. | Retain exact command IDs and nested-finally semantics; add pure state-machine mutation tests. A cleanup failure closes admission and permits no automatic second cleanup or retry. No claim that host cleanup presently works. |

## Attempt-012 central implementation plan

### Design invariants

1. Attempt-011 and every old artifact remain byte-for-byte immutable.
2. Any runner process invocation consumes the sole Attempt-012 attempt, including a pre-root failure.
3. Root authority is explicit, committed and independent of actual argv. The selected root may be the central checkout or a worktree only after central records that choice and proves exact HEAD/packet/receipt availability there; this plan does not choose by inference.
4. `cwd == authorized_root == git rev-parse --show-toplevel` and the absolute runner/output paths remain under that root.
5. The legacy `EXPECTED_EXECUTION_ROOT` is replaced/rebound before `legacy.main()` only after the explicit authority record validates.
6. Expected argv is generated from authority; it is never constructed by copying `sys.argv[1:]`.
7. Root, command, model, lineage, packet, frozen hashes and both receipt gates all pass before output creation or any host command.
8. Pre-root failure writes nothing under the proposed root. Post-root failure refreshes exactly four immutable failure documents.
9. Start count is at most one; automatic retry and fallback remain zero.
10. Cleanup retains exactly one F00 and one F01 attempt in nested `finally`; no automatic extra cleanup attempt.
11. A successful observation remains `result_status=NOT_RUN`, `test_set_opened=NO`, `accepted_result_rows=0`. It is only evidence for a later central decision and does not open benchmark admission.

### Proposed file/change sets

Central should use additive Attempt-012 paths and a four-commit pre-execution chain:

**R0 — reservation/support commit, exact seven added files**

1. `e4_r6_pc2w_p1_attempt012_pre_runtime_authority.py` — pure root/argv/model authority dataclasses and predicates; no I/O at import.
2. `e4_r6_pc2w_p1_attempt012_pre_runtime_authority_contract.json` — canonical schemas, stable failure codes and role model matrix.
3. `test_e4_r6_pc2w_p1_attempt012_pre_runtime_gate.py` — pure/synthetic regression and mutation suite; never imports/invokes a runner.
4. `e4_r6_pc2w_p1_attempt012_admission_observation_contract.json` — reserved/dormant stub.
5. `e4_r6_pc2w_p1_attempt012_execution_authorization.json` — reserved/runtime-denied stub.
6. `execute_e4_r6_pc2w_p1_attempt012_admission_observation.py` — reserved/dormant stub.
7. `validate_e4_r6_pc2w_p1_attempt012_static_packet.py` — reserved static validator stub.

**R1 — packet commit, exact four modified files**

- Modify only files 4-7 above.
- Bind `PACKET_PARENT=R0`, exact four-file roster, new output root under a new wave/attempt path, new confirmation token, new receipt schemas/verdicts and raw support hashes.
- Keep runtime authorization false and exact command unconfirmed in the committed authorization.

**R2 — central static validation receipt commit, exact one added file**

- Add `rebaseline_v2_e4_r6_pc2w_p1_attempt012_central_static_validation_receipt.json` only.
- Bind R0/R1 lineage, all packet/support raw hashes, test roster/results, model matrix, root authority choice, zero runner/runtime counts, and output-root absence.

**R3 — fresh independent audit receipt commit, exact one added file**

- Add `rebaseline_v2_e4_r6_pc2w_p1_attempt012_fresh_independent_audit_receipt.json` only.
- Bind R2 receipt raw SHA-256, R1 packet facts, exact ancestry, independent replay results, model passport, zero runner/runtime counts, and an exact next-gate disposition.

No `pipeline_state`, old runner, old validator, old contract, old receipt, Attempt-011 output path, or scientific artifact belongs to these change sets.

### Root-authority contract

The new pure helper must consume, and the packet/receipts must freeze:

- `authority_schema_version`
- canonical absolute `execution_root`
- `execution_root_kind` chosen explicitly by central
- `working_directory_must_equal_execution_root=true`
- `git_toplevel_must_equal_execution_root=true`
- absolute/canonical runner path and required containment
- repository-relative output path and required containment
- packet commit and expected execution HEAD
- packet/support raw blob roster and SHA-256
- central and audit receipt paths/SHA-256
- exact Python executable/version and required `-B`
- exact ordered arguments and confirmation token
- role-specific model policy

The helper may return a normalized value only after all inputs validate. It must never accept `--repo-root` itself as authority and must never read or mutate host state at import.

### Regression test before fix

Before implementing the Attempt-012 adapter, central must run the committed-blob RED harness from this plan against Attempt-011 and record:

- exact target hash matched;
- reachable throw is Attempt-008 line 670;
- throw precedes output creation/context;
- no root rebind exists;
- runner import/invocation and host probe counts are zero.

If the historical fixture is not RED, stop with `HANDOFF_INCOMPLETE`: the seam or authoritative bytes changed.

After implementation, historical Attempt-011 remains RED, while the Attempt-012 positive authority fixture must be GREEN. Mutation fixtures must remain RED with stable codes.

### Test matrix

| Lane | Required tests | Pass condition |
|---|---|---|
| Strict source/JSON | AST parse new Python sources; strict UTF-8 JSON; reject duplicate/casefold-duplicate keys and non-finite values. | Exact roster; zero skip/xfail; no runner import/invocation. |
| Root authority | Exact authorized tuple accepts; mutate root, CWD, Git top-level, root kind, runner containment, output containment, HEAD and packet individually. | Positive fixture GREEN; every single mutation fails with its stable code before output/probe boundary. |
| Legacy handoff | Static control-flow proof that validated root rebind/replacement occurs before `legacy.main()` and that the old singleton is not reachable unbound. | No path calls legacy main with stale root authority. |
| Command interface | Retain exact Python/`-B` tests; reject missing/duplicate/unknown flags, `-c`, `-m`, wrapper shell, changed runner, extra/missing/reordered/duplicated args and changed values. | Expected vector is derived from committed facts, never actual argv. |
| Model policy | Positive rows for Ultra planning/implementation/audit and XHigh locked execution; negative rows for other model/reasoning and observed Fast/Priority; `UNOBSERVABLE` speed preserved. | One canonical schema and predicate agree in contract, auth, validator and runtime passport. |
| Gate receipts | Positive new central/audit chain; mutate stage, schema, verdict, packet commit/facts, raw hash, central link, write set, receipt commit ancestry and runtime boundary. | All mutations fail before output/probe; old Attempt-011 receipts rejected for Attempt-012. |
| Frozen inputs | Recompute every support/packet fact from raw Git blobs; mutate one byte/path/order/count. | Exact raw facts pass; any mutation fails closed. |
| Persistence/output | Root failure keeps context `None`, output absent and outer failure disposition explicit; post-root synthetic failure produces exactly four files; preexisting root rejects; no reuse/delete path. | No unsafe early mkdir; exact immutable file set. |
| Cleanup state machine | Synthetic/faked S00 exception, D-lane failure, F00 exception, F01 exception, missing/unstable A/B/C, final-state difference. | F00/F01 each at most once; F01 survives F00 exception; any closure defect closes admission. |
| Exit provenance | Validate envelope's intended raw child code and separately modeled wrapper/tool code. | Receipt never conflates raw child exit with transport exit. |
| Retained compatibility | Existing Attempt-010 command, Attempt-009 compatibility, Attempt-008 parser/envelope and cleanup invariants from frozen blobs. | Exact retained suites pass without modifying their sources. |
| Boundary trap | Count output writers, sleeps, host commands, Docker, WSL and PowerShell probes across every pre-runtime test. | All counts zero; bytecode inventory unchanged (`-B`). |

### Model matrix

| Phase | Required model/reasoning | Service tier/speed | Authority |
|---|---|---|---|
| This diagnosis and plan | `gpt-5.6-sol` / `ultra` | requested Standard/default; actual speed may be `UNOBSERVABLE` | Judgment authority only |
| R0/R1 design, implementation choices and regression adjudication | `gpt-5.6-sol` / `ultra` | Standard/default; no Fast/Priority | Central implementation authority |
| R2 central static validation | `gpt-5.6-sol` / `ultra` | Standard/default; no Fast/Priority | Central validation authority |
| R3 fresh independent audit | `gpt-5.6-sol` / `ultra`, fresh context | Standard/default; no Fast/Priority | Independent pre-execution audit authority |
| Exact command assembly and gate judgment | `gpt-5.6-sol` / `ultra` | Standard/default; no Fast/Priority | Judgment authority |
| One locked Attempt-012 process execution only | `gpt-5.6-sol` / `xhigh` | Standard/default; no Fast/Priority | Mechanical execution authority only |
| Post-execution acceptance audit | `gpt-5.6-sol` / `ultra`, fresh context | Standard/default; no Fast/Priority | Acceptance judgment authority |
| Any diagnosis after any failure | `gpt-5.6-sol` / `ultra`, new diagnosis stage | Standard/default; no Fast/Priority | Diagnosis authority; never delegated to the XHigh executor |

For every phase, record requested and actual model/reasoning/speed. An observed mismatch or observed Fast/Priority is terminal. If speed is not observable, record exactly `UNOBSERVABLE`; do not infer it. The execution phase may be XHigh only after all Ultra gates lock the packet; XHigh may not redesign, reinterpret a failure, modify the command, retry, or fall back.

## Gate 1-5 protocol

### Gate 1 — Central implementation and RED-to-GREEN regression

- Owner: Sol Ultra Standard.
- Verify starting lineage and clean worktree.
- Run the historical static RED harness before changes.
- Create R0/R1 only with the exact change sets above.
- Run the full synthetic/static matrix with `-B`, zero runner import/invocation and zero host/runtime commands.
- Require exact four-file R1 delta, frozen raw hashes and a GREEN Attempt-012 positive authority fixture.
- Failure: stop; do not create R2, do not execute, do not widen authorization.

### Gate 2 — Central static validation

- Owner: a Sol Ultra Standard central validation context.
- Replay R0/R1 from raw Git blobs; do not trust implementer prose or checkout-normalized bytes.
- Re-run strict JSON/AST, root/argv/model/receipt/frozen/output/cleanup tests.
- Confirm output root absent, worktree clean, and all prohibited counts zero.
- Commit R2 as exactly one receipt file.
- Failure: `HANDOFF_INCOMPLETE`; no R3 and no command proposal.

### Gate 3 — Fresh independent audit

- Owner: fresh Sol Ultra Standard context with no implementation conclusion as authority.
- Start exactly at R2, prove its parent R1 and R1 parent R0.
- Independently replay raw packet/support/central-receipt bytes and the RED/GREEN/mutation predicates.
- Verify actual task model/reasoning and record speed without inference.
- Commit R3 as exactly one audit receipt file.
- Failure: `HANDOFF_INCOMPLETE`; no execution confirmation request.

### Gate 4 — New exact-command confirmation and one-shot execution

- Judgment/assembly owner: Sol Ultra Standard. Mechanical executor: Sol XHigh Standard only.
- Recheck R3 HEAD, clean worktree, output-root absence, exact root choice, interpreter identity, receipt raw hashes and the role model gate.
- Render a **non-executable proposal** first. The eventual process must be direct Python with `-B`; no shell wrapper:

```text
<ABSOLUTE_PYTHON> -B <ABSOLUTE_ATTEMPT012_RUNNER> --repo-root <AUTHORIZED_ABSOLUTE_ROOT> --packet-commit <R1> --expected-head <R3> --central-validation-receipt <R2_PATH> --central-validation-receipt-sha256 <R2_RAW_SHA256> --fresh-audit-receipt <R3_PATH> --fresh-audit-receipt-sha256 <R3_RAW_SHA256> --execution-confirmation <ATTEMPT012_TOKEN>
```

- The user must newly confirm the tuple `(exact working directory, exact argv)` after seeing all resolved values. Attempt-011 confirmation/token is invalid and cannot be reused.
- Launch exactly once. Any invocation consumes Attempt-012. No edit, retry, fallback, alternate root, alternate interpreter or wrapper is allowed.
- Failure: preserve stdout/stderr hashes and raw-child/outer-tool exit separately; do not rerun. Return diagnosis to a new Sol Ultra Standard stage.

### Gate 5 — Fresh post-execution acceptance, not benchmark admission

- Owner: fresh Sol Ultra Standard context; never the XHigh executor acting as judge.
- Do not rerun anything. Read only the immutable output packet and process capture.
- Require exact output file set, strict schemas, all expected command IDs exactly once, start at most once, retry/fallback zero, F00/F01 closure attempts exact, stable A/B/C snapshots, final state matching pre-start, and consistent model/provenance fields.
- A pre-root failure with no output root is evaluated from the separately authorized outer control failure receipt; absence must never be repaired by fabricating an output packet.
- Even on PASS, keep `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, and `benchmark_admission_opened=false`. The result is only eligible for a separately authorized central admission decision.
- Any mismatch: `HANDOFF_INCOMPLETE`; benchmark remains closed.

## Stop conditions and fail branches

Stop immediately and do not execute when any of the following holds:

- lineage, parent count, packet ancestry, worktree cleanliness or exact change set differs;
- historical Attempt-011 fixture is not RED or Attempt-012 positive fixture is not GREEN;
- actual model/reasoning differs, or Fast/Priority is positively observed;
- root authority is absent, ambiguous, derived only from argv, or disagrees with CWD/Git top-level;
- expected argv is copied from actual argv rather than independently derived;
- frozen path/byte/hash roster differs;
- central or audit receipt is missing, stale, malformed, not one-file committed, or not bound to the new packet;
- exact working-directory plus argv confirmation is missing or predates R3;
- output root already exists;
- any pre-runtime test crosses a runner/host/runtime boundary;
- any runtime invocation has already occurred for Attempt-012.

After an execution failure:

- consume the attempt; never retry or fall back;
- keep benchmark admission closed and scientific truth unchanged;
- if the trusted root was never established, keep output root absent and persist only a separately authorized outer failure receipt;
- if the root was created, preserve it byte-for-byte; never delete, overwrite, repair or reuse it;
- if cleanup is incomplete, do not issue an automatic second cleanup command; escalate to an explicit user-owned recovery stage;
- return all diagnosis to Sol Ultra Standard.

## Rollback and cleanup plan

- Before R1: stop on the implementation branch; do not reset, cherry-pick, merge or push. Any removal of newly reserved files requires explicit central authorization and exact-path verification.
- After R1/R2/R3: preserve commits and use a new superseding attempt if a gate fails; do not mutate historical receipts or packets.
- Tests must use `-B` and temporary directories outside the repository. Before every commit, require no `__pycache__`, `.pyc`, cache, log, or untracked residue.
- Remove any tagged debug instrumentation before R1; the committed runner must contain none.
- Before execution, no host cleanup is needed because no host command has run.
- During the one shot, only the already locked nested `finally` closure may issue F00/F01. No post-failure automatic cleanup is permitted.
- Attempt-011 output root remains absent and is never backfilled.

## Provenance and admission record requirements

Every central receipt/audit/output must record:

- full commit and parent SHA for R0-R3 and execution HEAD;
- exact write set/change status for each commit;
- each bound file's Git blob OID, raw byte count and raw SHA-256;
- selected root kind, canonical root, CWD, Git top-level and containment decisions;
- exact direct Python argv, separately confirmed working directory and confirmation provenance;
- requested/actual model, reasoning and speed per phase, with `UNOBSERVABLE` preserved;
- raw child exit code separately from wrapper/tool exit code;
- stdout/stderr byte counts and SHA-256 with sensitive text redacted;
- output-root existence transition and exact immutable file roster;
- start/stop/shutdown, retry, fallback, host/runtime and runner-import/invocation counts;
- `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, and benchmark admission closed.

Admission to execute requires Gates 1-3 plus a fresh Gate-4 confirmation. Admission to central evaluation requires Gate 5. Nothing in this plan authorizes or opens benchmark admission.

## Limitations

1. The exact hash proves the combined root/CWD guard, but the persisted evidence cannot identify which operand was unequal.
2. The supplied exit code `1` conflicts with the committed catch's raw `SystemExit(2)`; outer transport is unbound.
3. No committed exact Attempt-011 launch/confirmation receipt exists, so actual argv and CWD cannot be reconstructed without forbidden uncommitted context.
4. Cleanup closure is statically present but was never reached and was not runtime-validated here.
5. Model service-tier/speed telemetry is not visible to this context and is recorded `UNOBSERVABLE`; no latency-based inference is made.
6. No claim is made that Docker, WSL, Hyper-V, a daemon, the host, Attempt-012, or any scientific result has been repaired or validated.

## Final fail-closed truth state

- Direct failure site: proven.
- Direct compound predicate: proven false at runtime by exact hash.
- Individual false operand: unresolved and not guessed.
- Attempt-011 rerun: forbidden and not performed.
- Attempt-012: not created or run.
- Benchmark admission: closed.
- Result status: `NOT_RUN`.
- TEST opened: `NO`.
- Accepted result rows: `0`.
- Automatic retry/fallback: `0/0`.
- Ready next action: central Sol Ultra Standard implementation of the additive Attempt-012 R0/R1 packet, beginning with the historical static RED regression.
