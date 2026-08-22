# E4-R1C v5 Adapter and Evaluator Contract

> Material Passport: `stage1e_rebaseline_v2_wave_e_e4_r1c_v5_adapter_evaluator_contract` · status `UNVERIFIED`  
> Origin: `ars-codex:academic-research-suite/experiment-agent` · mode `central-synthesis/freeze-only` · date `2026-08-22`  
> Empirical state: `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, no adapter or evaluator executed.

## 1. Frozen v5 specification identity

Every future adapter manifest, evaluator manifest, command packet, receipt, and reported v5 result must bind exactly:

- path: `backend/docs/chatbot/seed-product/benchmark-spec-v5.json`;
- canonical-LF bytes: `2629`;
- canonical-LF SHA-256: `acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d`;
- hash policy: strict UTF-8 decode, CRLF normalization to LF, then SHA-256.

The historical path `research/hybrid-recsys-v5/03_benchmark/benchmark_spec_v5.json` does not exist and is rejected as an active binding. A matching digest attached to a nonexistent or different path does not satisfy this contract.

This correction closes `E5-F002` at path-and-byte identity only. It does not validate an adapter, evaluator, dataset snapshot, split, run, or result.

## 2. Ownership

E4 remediation owns:

- adapter and evaluator implementation;
- immutable source paths, commits, and raw hashes;
- exact argv and configuration;
- input/output schemas and inventories;
- parity fixtures and receipts;
- materialized command records and packet freeze.

A future E5-R1 task is independent audit-only. It may replay paths, bytes, hashes, schemas, semantics, and command claims, but it must not create or repair implementation code, argv, locks, fixtures, receipts, commands, confirmation, or authority.

The user may confirm only exact commands in a separately frozen packet after a future independent audit pass. An executor may run only a packet that is both confirmed and separately authorized.

## 3. Current materialization state

The present packet intentionally leaves the following values null:

- adapter ID, path, source commit, raw SHA-256, and argv;
- evaluator ID, path, source commit, raw SHA-256, and argv;
- metric-contract ID and complete metric/cutoff/averaging definitions;
- evaluation input manifest and output schema;
- candidate-mask, exclusion, and deterministic tie contract;
- candidate-specific timeout and resource evidence.

Null means blocked. It must not be converted to a default, guessed from a framework, supplied by E5-R1, or completed by an executor at run time. Resolving any value creates a new E4 packet version and requires a new freeze and audit.

## 4. Two evaluator seams

### 4.1 Official-source reproduction seam

The official seam asks whether one exact source implementation reproduces its own source-bound center on the exact source dataset, split, candidate universe, checkpoint, and evaluator semantics.

Required bindings include:

- candidate row ID and source repository full commit;
- exact dataset provider/release/rights and raw-to-processed-to-split receipt;
- model argv/config/seed/checkpoint/sampler;
- source evaluator identity and exact metric semantics;
- reported center, cutoff, averaging unit, locator, and frozen tolerance;
- run, checkpoint, prediction, evaluator, and metric receipts.

An official-source result is comparable only to the center bound to that same row. It cannot be relabeled as a harmonized v5 result.

### 4.2 Harmonized v5 seam

The harmonized seam evaluates a frozen prediction or score artifact through a standalone adapter/evaluator that implements the exact v5 specification identified above.

Required bindings include:

- one immutable input snapshot and split manifest;
- subject/item identity maps and exclusions;
- candidate universe and masking rules;
- exact prediction/score artifact hashes;
- adapter/evaluator paths, raw hashes, commits, and literal argv;
- metric names, cutoffs, averaging units, denominator rules, empty-case behavior, and deterministic tie policy;
- output schema and receipt hash;
- parity fixtures demonstrating that the adapter preserves item IDs, ranking order, score direction, and missingness semantics.

Source-integrated printed metrics do not satisfy the harmonized seam. The standalone receipt must bind the exact v5 specification path and hash.

## 5. Method-preserving adapter boundary

An adapter may perform only representation-preserving work:

- bounded export of predictions or scores already produced by the source method;
- deterministic mapping from source IDs to frozen evaluator IDs;
- schema validation, type normalization, and explicitly specified sorting/tie handling;
- emission of immutable manifests and receipts.

It may not:

- change model mathematics, objective, negative sampling, candidate universe, checkpoint, or scoring function;
- retrain, tune, calibrate, impute, or rerank unless the frozen experiment contract explicitly defines that behavior as part of the method;
- silently drop users/items or convert missing predictions to zero;
- read TEST before an independently preregistered TEST gate opens;
- inherit an evaluator from another repository or dataset because its metric has the same name.

Any method-affecting change is a new method variant, not an adapter.

## 6. Required adapter manifest

A future materialized adapter manifest must be a closed JSON object containing at least:

- `adapter_id`, semantic version, source path, source full commit, raw SHA-256;
- exact interpreter/environment identity and dependency-lock hash;
- literal argv and working directory;
- source candidate row, source run ID, input files, byte hashes, schemas, and counts;
- frozen v5 specification path, canonical-LF byte count, and SHA-256;
- ID-map path/hash, unknown-ID policy, duplicate policy, score direction, ranking rule, and tie rule;
- output file inventory, schemas, counts, and byte hashes;
- parity-fixture inventory and expected/observed outcomes;
- `TEST_SET_OPENED`, `RESULT_STATUS`, confirmation, and authority fields.

The manifest must reject unknown fields, duplicate keys, case-colliding keys, invalid UTF-8, missing inputs, extra outputs, reparse paths, and hash mismatch.

## 7. Required evaluator manifest and receipt

A future evaluator manifest and receipt must bind:

- evaluator ID/path/full commit/raw SHA-256 and exact argv;
- adapter manifest hash and every evaluation-input hash;
- frozen v5 specification path and hash;
- dataset snapshot/split, candidate universe, masks/exclusions, tie rule, and coverage counts;
- metric name, cutoff, formula version, averaging unit, denominator, undefined/empty handling, and expected output schema;
- physical GPU/CPU/memory envelope if applicable, timeout, process-tree outcome, stdout/stderr hashes, and exit status;
- exact output inventory and hashes;
- sealed TEST state unless a separate preregistration explicitly authorizes access;
- `retry_policy=NO_AUTO_RETRY`, retry count zero, and no resumed/substituted run.

The evaluation receipt is valid only when it strict-validates against the closed E4-R1B schema bundle and cross-receipt rules, all prior receipts pass, and the final manifest proves exact set equality.

## 8. Parity and acceptance gates

Before any candidate may be described as ready for a harmonized v5 run, the following must pass:

1. byte/hash replay of source predictions and adapter inputs;
2. deterministic ID-map coverage with every dropped or unknown ID explicitly accounted for;
3. score-direction and rank-order preservation fixtures;
4. duplicate, mask, exclusion, and tie fixtures including adversarial equal-score cases;
5. count equality from source output through adapter output;
6. evaluator fixtures with manually checkable metric values at each cutoff;
7. dual JSON parsing, duplicate/case-collision scan, closed-schema validation, and no extra files;
8. no TEST read and no empirical acceptance claim.

A parity pass validates representation and metric implementation; it does not validate training reproduction or authorize TEST.

## 9. Current gate status

| Gate | State | Reason |
|---|---|---|
| v5 spec path/hash identity | corrected and frozen | one existing path and matching canonical-LF digest |
| source candidate | blocked | 0 ready rows |
| adapter identity/argv | blocked | null, not implemented or hash-bound |
| evaluator identity/argv | blocked | null, not implemented or hash-bound |
| metric/candidate/tie contract | blocked | candidate-specific material not frozen |
| parity receipts | blocked | no implementation or fixtures |
| TEST | sealed | no preregistered authorization |
| execution | denied | commands null; confirmation and authority false |

## 10. Reporting boundary

Official-source and harmonized-v5 outputs must use separate table sections, provenance columns, dataset/split/evaluator identifiers, and denominators. A source metric may be shown as a reproduction target only beside the corresponding source reproduction result. It may never be used as a raw comparator against a v5 metric from another dataset or evaluator.

Current paper-use status is `INVALID_FOR_PAPER`: there are no accepted empirical rows.

