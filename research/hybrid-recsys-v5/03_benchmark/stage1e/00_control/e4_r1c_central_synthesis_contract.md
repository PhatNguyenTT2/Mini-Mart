# Stage 1E E4-R1C Central Synthesis Contract

> Material Passport: `stage1e_rebaseline_v2_e4_r1c_central_synthesis_contract` · status `UNVERIFIED`  
> Origin: `ars-codex:academic-research-suite/experiment-agent` · mode `central-synthesis/freeze-only` · date `2026-08-22`  
> Model policy: central synthesis uses `gpt-5.6-sol` with reasoning `high`. Independent lane evidence was produced with reasoning `xhigh`.  
> Empirical state: `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, `execution_authorized=false`.

## 1. Purpose and entry gate

E4-R1C is the only owner allowed to synthesize the accepted E4-R1A and E4-R1B proposals into a replacement E4 packet. The central lane-intake receipt must first equal `PASS_BOTH_LANES_READY_FOR_E4_R1C_SYNTHESIS` and must replay:

- 17/17 inputs from the E4-R1 parent manifest;
- exactly four E4-R1A files and four E4-R1B files;
- E4-R1A status: 0 ready, 7 pending, 6 rejected, with five prohibited joins preserved;
- E4-R1B status: ten null commands, seven closed receipt schemas, ten command-to-receipt mappings, and 15 unresolved prerequisites before central synthesis;
- no experiment, repository acquisition, dataset acquisition, environment creation, package installation, command execution, or TEST access.

Passing lane intake is a structural gate only. It does not promote a candidate, resolve evidence, materialize a command, confirm a packet, or authorize execution.

## 2. Authoritative synthesis inputs

The E4-R1C frozen input manifest must bind, by canonical-LF byte count and SHA-256:

1. this contract and the central lane-validation receipt;
2. the E5 findings and execution-denial record that caused remediation;
3. all four accepted E4-R1A artifacts;
4. all four accepted E4-R1B artifacts;
5. the six immutable historical E4 artifacts being replaced;
6. the one existing v5 benchmark specification at `backend/docs/chatbot/seed-product/benchmark-spec-v5.json`.

The historical Wave B packet remains immutable evidence. E4-R1C writes a new Wave E packet and never edits E1-E5, Wave A-D evidence, the benchmark specification, application code, inputs, or the master plan.

## 3. Required scientific synthesis

### 3.1 Provenance and candidate state

The replacement reference bundle must:

- reject `https://arxiv.org/abs/2207.09037` as a SimGCL source;
- bind SimGCL to `https://arxiv.org/abs/2112.08679`, revision `arXiv:2112.08679v4`, and the pinned QRec repository;
- bind the v5 benchmark specification only to `backend/docs/chatbot/seed-product/benchmark-spec-v5.json` with canonical-LF SHA-256 `acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d`;
- cryptographically bind the complete 13-row candidate registry and five prohibited joins from E4-R1A;
- preserve 0 ready, 7 pending, and 6 rejected rows;
- retain LightGCN/Gowalla only as the first evidence-resolution priority, never as an automatic selection or execution authority;
- preserve every unresolved source, rights, data-lineage, environment, run, checkpoint, evaluator, candidate-universe, and tie-policy blocker.

No row may be marked selected or ready merely because it is the least incomplete row.

### 3.2 Command and receipt controls

The replacement command packet must:

- be a central packet, not an executable lane draft;
- cryptographically bind the complete E4-R1B mechanical-control design and receipt-schema bundle;
- contain exactly ten ordered replacement command records corresponding to ordinals 0 through 90;
- keep every command string, shell, and working directory null while candidate and material bindings are unresolved;
- carry `user_confirmation_required=true`, `confirmed=false`, `execution_authorized=false`, `NO_AUTO_RETRY`, and `test_access_allowed=false` at packet and command level;
- retain literal path/namespace, GPU/resource, immutable source, environment/dependency, lawful dataset lineage, preprocessing, run monitoring, standalone evaluation, and final-manifest controls;
- mark only the central-packet creation prerequisite resolved after freeze; all evidence, materialization, independent-audit, user-confirmation, and authority prerequisites remain unresolved;
- treat the future E5-R1 lane as independent audit-only. E5-R1 may not create locks, argv, schemas, receipts, commands, confirmation, or authority.

Null commands are an intentional fail-closed state. They are not placeholders that a future executor may fill ad hoc.

### 3.3 Adapter, evaluator, and reporting seams

The replacement contracts must maintain three non-interchangeable result scopes:

1. official-source reproduction on the source dataset and source metric seam;
2. harmonized v5 evaluation using the one frozen v5 specification;
3. external validation on a separately eligible dataset and protocol.

Official-source metrics may be used only for within-row reproduction checks. They may not support a raw cross-dataset ranking, a v5 superiority claim, or an external-validation claim. MovieLens 1M/10M framework assessments and Amazon-M2 or other external-dataset assessments remain separate evidence tracks.

The adapter/evaluator contract must bind the corrected specification path and hash, keep adapter/evaluator identities and argv null until implemented and hashed by an E4 remediation owner, preserve TEST sealing, and require standalone evaluation receipts. E5-R1 must not be assigned implementation ownership.

## 4. Required Wave E outputs

Write only under:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_e/E4_R1C_reproduction_adaptation/`

Exactly six files are required:

1. `selected_reference_bundle.json`
   - corrected SimGCL and v5-spec bindings;
   - hash-bound authoritative candidate registry;
   - 13-row status index, five prohibited joins, status counts, and no selection.
2. `reproduction_execution_plan.md`
   - evidence-resolution sequence, phase ownership, mechanical gates, no-auto-retry, TEST seal, and future audit sequence.
3. `v5_adapter_and_evaluator_contract.md`
   - corrected path/hash, source-versus-v5 metric separation, adapter/evaluator materialization requirements, and audit-only E5 ownership.
4. `cross_dataset_reporting_contract.md`
   - allowed within-scope reporting, forbidden raw cross-dataset league tables, missingness rules, and paper-use gate.
5. `exact_command_confirmation_packet.json`
   - central replacement packet with ten null command records, immutable control/schema bindings, prerequisite ledger, denial state, and no execution authority.
6. `e4_r1c_handoff.json`
   - Material Passport Schema 9 fields, populated repro lock, frozen-input verification, output hashes for the first five files, finding dispositions, truth state, scope guards, and next gate.

The self-referential handoff hash is reported in the central validation receipt rather than embedded in the handoff.

## 5. Finding-disposition requirements

The replacement packet must state:

- `E5-F001`: corrected in the central source catalog and dependent SimGCL binding, with run/data/evaluator gaps retained;
- `E5-F002`: corrected in every central adapter/evaluator and packet binding to one existing path and digest;
- `E5-F003`: replaced by the hash-bound mechanical-control and closed-schema design, but still non-executable until candidate-specific controls are materialized;
- `E5-F004`: corrected so E4 owns remediation and packet production while future E5-R1 remains read-only audit.

The allowed central verdict is:

`COMPLETE_CORRECTED_FAIL_CLOSED_READY_FOR_E5_R1_AUDIT`

This verdict means the remediation packet is structurally ready for independent audit. It does not mean it is ready for execution, benchmark acceptance, manuscript use, or user confirmation.

## 6. Validation and freeze gate

Central validation must fail closed unless all of the following hold:

- every direct input matches its frozen byte count and hash;
- exactly six Wave E files exist and every JSON passes a standard parser, PowerShell `ConvertFrom-Json`, and duplicate/case-collision checks;
- all five non-handoff output hashes in the handoff replay;
- source/spec corrections are exact;
- the candidate registry contains exactly 13 rows, five prohibited joins, 0 ready, 7 pending, and 6 rejected;
- the command packet contains exactly ten null, unconfirmed, unauthorized, no-auto-retry records;
- the R1B control and schema hashes are exact;
- exactly 15 prerequisites remain in the ledger, with only `P13_NEW_FROZEN_CENTRAL_PACKET` resolved by E4-R1C freeze;
- `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, zero accepted rows, and no empirical claim are preserved;
- every scope guard remains false and no execution authorization is emitted.

After a successful central freeze, dispatch one fresh independent E5-R1 task using `gpt-5.6-sol` with reasoning `xhigh`. E5-R1 audits only the frozen Wave E packet. It may confirm remediation quality or demand another revision, but it must deny execution while any candidate/material/confirmation prerequisite remains unresolved.

## 7. Explicit execution boundary

Allowed:

- read-only inspection of frozen local evidence;
- hash, schema, consistency, and ownership checks;
- writing the contract, manifest, Wave E packet, validator, validation receipt, dispatch record, and pipeline-state update;
- independent audit-task creation after central validation passes.

Forbidden:

- clone/fetch, dataset download, authenticated access, package installation, environment creation, training, evaluation, smoke tests, benchmark execution, or TEST access;
- editing historical lane evidence, application code, benchmark specifications, inputs, or user work;
- guessing missing evidence or material identities;
- materializing or executing a command while any required binding is null;
- setting `confirmed=true`, `execution_authorized=true`, accepting a result row, or emitting `PASS_EXECUTION_AUTHORIZED`.

