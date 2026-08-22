# Stage 1E E5 Independent Lock Audit Contract

> Material Passport: `stage1e_rebaseline_v2_e5_contract` · status `UNVERIFIED`  
> Origin: `ars-codex:academic-research-suite/experiment-agent` · mode `validate/audit-only` · date `2026-08-22`  
> Model policy: `gpt-5.6-sol` with reasoning `xhigh`.  
> Independence: E5 runs in a fresh task/worktree and must not modify or collaborate with E4.

## 1. Entry state and non-negotiable consequence

The frozen E4 packet is structurally valid for audit but has this content state:

- E4 verdict: `FAIL_NOT_READY_FOR_E5`
- detail: `BLOCKED_NO_READY_REFERENCE_BUNDLE`
- 13 candidate rows: 0 ready, 7 pending, 6 rejected
- 26 Wave A blockers: 1 resolved, 18 carried, 7 rejected with row
- exact-command packet: `DRAFT_BLOCKED_NOT_EXECUTABLE`
- `ACCEPTED_RESULT_ROWS = 0`
- `RESULT_STATUS = NOT_RUN`
- `TEST_SET_OPENED = NO`
- execution authorization: `false`

E5 may independently audit this failed packet now. E5 **cannot** authorize execution from it, even if all E4 bookkeeping is internally consistent, because there is no `READY_FOR_E5_AUDIT` reference row and no executable command packet. The maximum valid outcome is an independently supported remediation/denial decision. Any future authorization requires blocker remediation, a new frozen E4 packet, a new independent E5 audit, and explicit user confirmation of the replacement exact-command packet.

## 2. Objective

Independently determine whether E4's fail-closed conclusion and evidence boundaries are correct, complete, and reproducible as an audit trail. E5 must:

1. verify every frozen local input and E4 output hash;
2. replay the primary-source evidence behind each promoted decision;
3. verify repo–dataset–command–metric joins and all explicit rejected joins;
4. verify reported-center locators and tolerance arithmetic without executing models;
5. verify code-license and dataset-rights distinctions;
6. audit all 26 blocker dispositions, especially every item E4 marked `RESOLVED`;
7. audit command packet completeness, path safety, resource controls, confirmation state, and no-auto-retry rules;
8. verify the official-reproduction → v5-adaptation → harmonized-v5 → external-validation sequence;
9. verify that no raw metric is compared across incompatible datasets/pipelines;
10. issue an explicit execution-denial artifact and remediation priorities.

E5 is an auditor, not a remediation owner. It must not edit E1–E4, invent missing evidence, fill null command fields, select a new dataset, or create a replacement command packet.

## 3. Independent replay rules

E5 must treat all E1–E4 statements as untrusted claims. Central validation proves only file/schema/hash consistency.

Use primary sources in this order:

1. immutable author-maintained repository files and commits;
2. official paper/supplement/proceedings copy;
3. canonical dataset provider, release, checksum, license, or terms page;
4. framework-owned repository/documentation/result page for framework-authoritative rows.

Search snippets, third-party mirrors, aggregators, forks, and uncited recollection cannot close a gate. Record for each replayed item:

- stable source ID;
- URL and access date;
- immutable revision where applicable;
- exact locator;
- field or claim tested;
- replay result: `CONFIRMED`, `CONTRADICTED`, `PARTIAL`, `UNAVAILABLE`, or `NOT_APPLICABLE`;
- residual ambiguity and impact.

Do not copy long source text. A short locator plus paraphrased finding is sufficient.

## 4. Required audit coverage

### 4.1 Candidate and join audit

Audit all 13 E4 candidate rows, not only the LightGCN priority row. For every row verify:

- method/repository identity and provenance class;
- full commit SHA and source-bound command/config;
- dataset provider/release/hash and raw-to-processed-to-split lineage;
- objective, seed/run count, checkpoint policy, sampler, candidate universe, and tie policy;
- metric definition, cutoff, averaging unit, reported center, locator, and frozen tolerance;
- code/data rights and lawful acquisition state;
- E4 status and reason.

Re-check all five prohibited E3 joins. A published center attached to a different framework, sampler, layer count, batch size, checkpoint rule, split, or evaluator remains rejected.

### 4.2 Required decision-point replay

Independently audit these E4 conclusions:

- MovieLens 1M: RecBole-GNN provides framework results but not an exact result-bound reproduction lock under the frozen contract.
- MovieLens 10M: no matching official framework-owned top-N center was established.
- Amazon-M2: anonymous session semantics and acquisition/hash constraints fail the full persistent-user/history/order/basket external contract; a reduced session study is separate and acquisition-gated.
- no current public dataset passes the full external-validation contract.
- the LightGCN/Gowalla row is a lock-resolution priority only, not selected for execution.

If a conclusion is contradicted by primary evidence, issue a finding and require E4 regeneration. Do not repair it within E5.

### 4.3 Blocker audit

Audit all 26 blocker-disposition rows for:

- one-to-one coverage of Wave A blockers;
- valid disposition enum;
- evidence for every `RESOLVED` disposition;
- no blocker hidden by row rejection;
- every carried blocker represented in E4 unresolved-blocker or row-level state;
- counts matching 1 resolved, 18 carried, and 7 rejected-with-row.

Any unsupported `RESOLVED` disposition is at least `MAJOR` and prevents a clean audit conclusion.

### 4.4 Command and safety audit

Audit all 10 command records without executing them. Verify:

- exact shell and working directory;
- repository revision and source binding;
- reads/writes/network behavior;
- expected receipts and outputs;
- timeout and local RTX 3060 6 GB resource envelope;
- path/namespace collision behavior;
- no credentials or secrets;
- `NO_AUTO_RETRY`;
- `user_confirmation_required = true`;
- `confirmed = false`;
- `execution_authorized = false`;
- blocked/null commands remain explicit and cannot be treated as executable.

The current packet must remain `DO_NOT_EXECUTE`. E5 must not rewrite command status, fill environment/dependency gaps, or confirm any row.

### 4.5 Adaptation and reporting audit

Verify that:

- official reproduction acceptance precedes v5 adaptation;
- adapters do not silently change method identity;
- all v5 methods would share one frozen split/candidate/masking/tuning/seed/checkpoint/evaluator contract;
- local Deep/Hybrid remain blocked until their dirty source state is sealed;
- official reproduction, harmonized v5 comparison, and external validation are separate evidence tracks;
- cross-dataset claims use within-dataset effects/uncertainty/robustness only, never raw metric league tables.

## 5. Finding severity and verdicts

Finding severity:

- `CRITICAL`: could falsely authorize execution, leak TEST, misrepresent a benchmark, violate rights, or compare incompatible metrics.
- `MAJOR`: missing/contradictory provenance, command, metric, blocker, or source evidence that requires E4 regeneration.
- `MINOR`: non-authorizing clarity or documentation defect.

E5 audit verdict is exactly one of:

- `CONFIRM_E4_FAIL_REMEDIATION_REQUIRED`: E4's fail-closed state is materially supported; remediation and a new E4/E5 cycle are required.
- `REVISE_E4_ADDITIONAL_FINDINGS`: E4 is correctly non-executable but its packet contains additional material defects or unsupported resolutions.
- `FAIL_AUDIT_PACKET_INVALID`: the packet cannot be audited reliably because hashes, schema, or essential evidence fail.

`PASS_EXECUTION_AUTHORIZED` is forbidden for this frozen packet.

## 6. Required outputs

Write only under:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_c/E5_independent_lock_audit/`

Required files:

1. `independent_lock_audit.md`
   - audit scope, methods, full criterion matrix, decision-point replay, blocker audit, command audit, adaptation/reporting audit, findings summary, verdict, and remediation order.
2. `audit_findings.json`
   - one row per finding with ID, severity, criterion, affected artifact/row, observed fact, primary evidence/locator, impact, disposition, and owner.
3. `replay_receipt.json`
   - frozen local-input hash replay plus all external source replay rows and unavailable/degraded states.
4. `stage1e_execution_authorization.json`
   - `authorized = false`;
   - decision `DENIED_E4_FAIL_NOT_READY` or a stricter denial;
   - exact reasons, required remediation, replacement-packet requirement, user-confirmation state, and truth state.
5. `e5_handoff.json`
   - ARS Schema 9 Material Passport including populated `repro_lock`;
   - model/reasoning, frozen E5 manifest hash, output paths and canonical-LF hashes;
   - source replay counts, finding counts, candidate/blocker/command audit counts;
   - `RESULT_STATUS = NOT_RUN`, `TEST_SET_OPENED = NO`, `ACCEPTED_RESULT_ROWS = 0`;
   - execution authorization false and one allowed E5 audit verdict.

Every JSON file must parse with both a standard JSON parser and PowerShell `ConvertFrom-Json`, with no duplicate or case-colliding keys.

## 7. Execution boundary

Allowed:

- local read-only inspection;
- primary-source web replay;
- hash/schema/consistency checks;
- writing only the five E5 audit outputs.

Forbidden:

- clone/fetch of candidate repositories;
- dataset download or authenticated access;
- package installation or environment creation;
- source/model/data modification;
- training, evaluation, smoke tests, benchmark execution, or TEST access;
- executing any E4 command;
- modifying E1–E4;
- external model/API upload;
- creating or confirming a replacement execution packet.

## 8. Completion gate

E5 is complete only when:

- every frozen input hash passes;
- all 13 candidate rows, all 26 blocker dispositions, all 10 commands, and all required decision points are audited;
- primary-source replay is explicit and fail-closed;
- unsupported or unavailable evidence remains visible;
- E4 files are byte-unchanged;
- authorization is explicitly denied;
- the replacement E4/E5 cycle requirement is explicit;
- no execution, TEST access, empirical result, or cross-dataset raw comparison occurred;
- all five outputs and their hashes validate.
