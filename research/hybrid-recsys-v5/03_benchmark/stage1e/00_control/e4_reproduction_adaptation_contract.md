# Stage 1E E4 Reproduction and Adaptation Lock Contract

> Material Passport: `stage1e_rebaseline_v2_e4_contract` · status `UNVERIFIED`  
> Origin: `ars-codex:academic-research-suite/experiment-agent` · mode `plan` · date `2026-08-22`  
> Model policy: `gpt-5.6-sol` with reasoning `xhigh`.  
> Execution boundary: evidence synthesis and command design only. No clone, download, install, source edit, training, validation run, or TEST access.

## 1. Entry state

E1, E2, and E3 have been imported and have passed central **structural** validation. This authorizes E4 synthesis only. It does not verify their scientific claims and does not authorize execution.

The E4 agent must preserve these truth values:

- `ACCEPTED_RESULT_ROWS = 0`
- `RESULT_STATUS = NOT_RUN`
- `TEST_SET_OPENED = NO`
- every pre-existing project benchmark remains `INVALID_FOR_PAPER`
- Wave A evidence remains `UNVERIFIED` unless E4 records a successful primary-source replay for the exact field being promoted

All blockers in the three lane handoffs are mandatory inputs. E4 must resolve them with primary evidence, carry them forward unchanged, or reject the affected row. Silence is not resolution.

## 2. Objective

Produce the smallest defensible, auditable bridge from an authoritative implementation and public reference dataset to a future method-faithful v5 comparison:

1. bind repository, immutable revision, lawful dataset release, official preprocessing/split, command/config, metric semantics, reported center, tolerance, and environment;
2. design—but do not run—the unchanged official-protocol reproduction;
3. define acceptance receipts and fail-closed decisions;
4. define a method-faithful adapter from an accepted implementation to the v5 DatasetManifest and one shared evaluator;
5. separate official reproduction, harmonized v5 comparison, and harmonized external validation;
6. emit an exact-command packet for E5 audit and later explicit user confirmation.

E4 is not required to force every candidate into the selected bundle. A smaller bundle with complete provenance is preferred to broader coverage assembled from incompatible evidence.

## 3. Source and join rules

E4 must read every frozen input in the E4 manifest and verify its canonical-LF SHA-256 before synthesis. It may replay public web evidence, but should use primary sources in this order:

1. author-maintained repository, release, commit, config, README, or issue authored by maintainers;
2. official paper, supplementary material, or proceedings copy;
3. canonical dataset provider and its terms/license;
4. framework documentation or repository for framework-authoritative rows.

Search snippets, mirrors, aggregators, third-party forks, and uncited recollection cannot promote a row. Record URL, access date, exact locator, supported field, and any ambiguity for every replayed source.

Only joins already represented in E1–E3 may be accepted unless E4 adds primary-source evidence proving every join key. A join is exact only when all of the following match:

- method identity and implementation provenance class;
- immutable repository revision;
- dataset identity, release, raw-to-processed lineage, and artifact hash mechanism;
- preprocessing, filtering, split, candidate universe, and negative sampler;
- objective, command/config, seed policy, and checkpoint-selection policy;
- metric formula, cutoff, averaging unit, eligibility rule, relevance rule, and tie policy;
- reported benchmark center and its table/README/config locator;
- code and data rights needed for the planned action.

Published numbers must never be attached to a different framework command, dataset processing, sampler, layer count, batch size, checkpoint policy, or evaluator. Such rows are `INCOMPARABLE` or `REJECTED`, not approximate reproductions.

## 4. Row statuses

Every repo–dataset–metric row must receive exactly one status:

- `READY_FOR_E5_AUDIT`: all lock fields are evidenced; no unresolved legality, lineage, command, metric, or hardware gap remains.
- `ACQUISITION_GATE`: the exact lawful source and protocol are known, but a human-authenticated download, terms acceptance, or other user action is still required. This is not execution-ready.
- `EXTERNAL_COMPUTE_GATE`: the recipe is otherwise complete but cannot faithfully fit the local RTX 3060 6 GB envelope; no silent architecture or batch reduction is allowed.
- `PENDING_EVIDENCE`: at least one required lock field is unproven.
- `REJECTED`: the row is incompatible, non-authoritative, unlawful, unreproducible, or would change method identity.

No row may be labeled `EXECUTION_AUTHORIZED`; only E5 PASS plus later user confirmation of the exact command packet can authorize execution.

## 5. Minimum defensible bundle

The selected bundle must be justified against paper coverage and execution cost. It should contain only rows that can plausibly pass E5 and should, where evidence permits, cover:

- non-learned controls: Random, MostPop, ItemKNN/ItemCF, and Apriori;
- classical collaborative filtering: BPR-MF and LightGCN;
- sequential/deep recommendation: SASRec and BERT4Rec;
- relevant recent or specialized baselines: BTBR/Mask-Swap-NNBR, UniSRec, AlphaRec, SimGCL, XSimGCL, and LightGCL;
- local independent Deep and proposed Hybrid conditions.

Coverage does not override evidence. For each omitted family, record whether it is deferred, represented by a framework-authoritative implementation, or excluded, with a concrete blocker. A method without a compatible official benchmark center may still be planned for the future harmonized-v5 track, but it must not masquerade as an official reproduction row.

E4 must explicitly determine whether MovieLens 1M/10M can support any exact framework-authoritative reproduction center, and whether Amazon-M2 can satisfy the external-validation contract despite its session-only and authenticated-access limitations. Do not assume either conclusion.

## 6. Reproduction lock

For each selected official-protocol reproduction row, freeze:

- stable row ID and method family;
- provenance class and reason for selection;
- repository URL, full 40-character commit SHA, tag relationship, and code-license evidence;
- dataset provider, release/version, lawful access route, data-license/terms evidence, expected artifact, and post-download hash command;
- isolated environment name, Python/CUDA/framework versions, package lock or explicit unresolved dependency gate;
- exact working directory and commands for clone, revision checkout, environment creation, install, preprocessing, training, checkpoint selection, and evaluation;
- source-bound config path and every non-default override;
- deterministic seeds and run count;
- metric semantics and source locator;
- reported center, uncertainty/run count when available, and pre-run tolerance;
- expected artifacts, receipts, timeout, CPU/RAM/VRAM/disk envelope, and failure conditions;
- `NO_AUTO_RETRY` and no replacement of failed seeds.

Default tolerance is `max(0.005 absolute, 5% relative)` only where E3 has not justified a source-bound alternative. A tolerance cannot be chosen after observing a result.

The original recipe is reproduced unchanged. Hardware incompatibility creates a gate; it does not authorize hidden batch-size, layer, sampler, precision, epoch, or checkpoint changes.

## 7. Execution namespaces

Commands must use isolated, non-overlapping namespaces under a future Stage 1E runtime root. At minimum define:

- immutable repository checkout by repository ID and commit;
- one environment per incompatible framework/runtime family;
- dataset cache by provider, version, and verified artifact digest;
- official preprocessing output by source row and preprocessing-contract digest;
- official reproduction run by row ID, config digest, and seed;
- v5 adaptation run by method ID, shared-protocol digest, and seed;
- external-validation run under a separate dataset-specific namespace.

No command may overwrite source data, a previous run, or another method's artifacts. Credentials and tokens must not appear in commands or files.

## 8. Acceptance and receipts

Before any future run, define machine-readable receipts for:

- repository commit and clean checkout;
- environment and dependency lock;
- downloaded artifact and license/terms acknowledgment;
- raw-to-processed lineage and split statistics;
- command/config digest and hardware facts;
- seed, checkpoint choice, and complete run status;
- evaluator identity, metric semantics, and output artifact hash;
- comparison with the frozen reported center and tolerance.

The reproduction decision is one of `PASS`, `FAIL`, or `INCOMPARABLE`. Missing artifacts, crashes, partial seeds, altered recipes, ambiguous checkpoint selection, or metric drift cannot produce `PASS`.

## 9. Method-faithful v5 adaptation

Adaptation starts only after that implementation's official-protocol reproduction is accepted. The adapter contract must separate:

- method code that remains unchanged;
- data-schema mapping into the model's native input representation;
- bounded prediction/per-user-metric collector code;
- the shared v5 evaluator;
- any unavoidable method change, which must be preregistered as a separate variant rather than silently folded into the baseline.

All v5 methods must share the frozen DatasetManifest, cohort, split, candidate universe, masking, relevance rule, metric implementation, cutoff set, tuning budget, seed policy, checkpoint rule, and reporting unit. The proposed model cannot receive a larger search budget or different test access.

The current local Deep/Hybrid code cannot be an immutable condition until its dirty implementation state is sealed in a clean commit and all code/config/data hashes are recorded.

## 10. Cross-dataset reporting

Keep three evidence tracks in separate tables and namespaces:

1. `OFFICIAL_PROTOCOL_REPRODUCTION`: implementation-validity evidence against source-bound reported centers.
2. `HARMONIZED_V5_COMPARISON`: the primary same-dataset, same-pipeline model comparison.
3. `HARMONIZED_EXTERNAL_VALIDATION`: a separate public dataset evaluated with a harmonized model subset and dataset-specific table.

Never rank or claim superiority by directly comparing raw HR, Recall, NDCG, GAUC, latency, or coverage values across different datasets, splits, candidate policies, or evaluators. Cross-dataset synthesis may discuss within-dataset effect direction, uncertainty, robustness, and failure modes only after each dataset-specific analysis is valid.

If no external dataset satisfies access, rights, persistent-user/history, item, temporal/order/basket, and supported-model requirements, report `NO_DATASET_PASSES_CURRENT_EXTERNAL_CONTRACT` and retain the gate. Do not weaken the contract after seeing available data.

## 11. Required outputs

Write only under:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_b/E4_reproduction_adaptation/`

Required files:

1. `selected_reference_bundle.json`
   - every candidate row, exact join keys, status, evidence locators, blockers, and selection/exclusion rationale;
   - explicit counts by status;
   - no unsupported `VERIFIED` promotion.
2. `reproduction_execution_plan.md`
   - dependency-ordered official reproduction plan, isolated environments, local-resource scheduling, receipts, and fail-closed rules.
3. `v5_adapter_and_evaluator_contract.md`
   - method-identity boundary, adapter interface, shared evaluator contract, tuning/seed/checkpoint policy, and TEST seal.
4. `cross_dataset_reporting_contract.md`
   - external-dataset qualification result, separate-table schema, prohibited comparisons, and valid synthesis language.
5. `exact_command_confirmation_packet.json`
   - ordered command records with command ID, shell, working directory, exact command/argv, prerequisites, expected reads/writes, outputs, timeout, resource limits, network flag, destructive-risk flag, retry policy, and confirmation state;
   - `user_confirmation_required = true`, `confirmed = false`, `execution_authorized = false`.
6. `e4_handoff.json`
   - ARS Material Passport with required fields;
   - model/reasoning, frozen input-manifest SHA, output paths and canonical-LF SHA-256 values;
   - counts, unresolved blockers, `RESULT_STATUS = NOT_RUN`, `TEST_SET_OPENED = NO`, and one verdict: `READY_FOR_E5_AUDIT`, `PARTIAL_REVISE_BEFORE_E5`, or `FAIL_NOT_READY_FOR_E5`.

Every JSON file must parse in both a standard JSON parser and PowerShell `ConvertFrom-Json`; do not use duplicate or case-colliding keys.

## 12. E4 completion gate

E4 is complete only when:

- every frozen input hash is verified;
- every candidate and selected row has an explicit status;
- all Wave A blockers are resolved, carried, or tied to a rejection;
- selected joins are exact and source-replayable;
- no raw cross-dataset metric comparison exists;
- commands are complete but unexecuted;
- the command packet is explicitly unconfirmed and unauthorized;
- all output hashes and Material Passport fields validate;
- no empirical result, TEST access, clone, download, install, or run occurred.

E5 remains an independent audit. E4 must not self-authorize execution.
