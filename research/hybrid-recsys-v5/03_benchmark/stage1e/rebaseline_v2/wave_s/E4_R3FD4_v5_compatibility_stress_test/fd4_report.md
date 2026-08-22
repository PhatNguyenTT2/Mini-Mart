# R3-FD4 — v5 compatibility stress-test report

Date: `2026-08-22`  
Stage: `R3-FD4`  
Runtime profile: `Sol XHigh Standard` (`gpt-5.6-sol`, reasoning `xhigh`, service tier `standard`)  
Lane verdict: `COMPLETE_FAIL_CLOSED_NO_POSITIVE_COMPATIBILITY_ROWS`

## Empirical and authority state

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- project benchmark numbers: `INVALID_FOR_PAPER`
- selection performed: `false`
- selected candidate: `null`

This lane performed read-only local contract inspection and bounded public owner-source replay. It did not clone or fetch a repository, acquire a repository archive or dataset, install packages, create an environment, preprocess data, train, evaluate, benchmark, open TEST, contact maintainers, accept terms, select a candidate, or materialize an adapter.

## Frozen binding and method

The ordered seed set was rechecked at `23034` canonical-LF bytes with SHA-256 `dce058850afb537f062531d1b128a1c36685bc878a3761e35a22db3d72db8781`:

1. `R3-BUNDLE-CORNAC-ML100K-001`
2. `R3-BUNDLE-ELLIOT-ML1M-001`
3. `R3-BUNDLE-DAISYREC-ML1M-001`

The current v5 binding was hash-replayed against the frozen benchmark spec, adapter/evaluator contract, cross-dataset reporting contract, experimental log and methodology blueprint. Current evaluator and snapshot implementation files were inspected read-only and hash-recorded, but they are explicitly labeled as current local source rather than FD0-frozen inputs.

Decision-bearing external claims use only exact-commit files from the project owners. The frozen GitHub HTML commit/blob locators that returned cache misses were not promoted: each locator-specific failure remains `UNRESOLVED`. Separate exact-commit raw owner files replayed successfully and support only the bounded feasibility observations attached to those URLs.

## v5 invariants used for the stress test

- temporal train/validation/test boundaries, with TEST sealed;
- organic novel-purchase truth and eligible-user filtering;
- the complete 5,200-item catalog, including train-unseen cold items;
- seen-item masking by the shared evaluator;
- deterministic rank order by descending score and ascending raw product ID;
- batched external scores shaped `[batch_users, 5200]`;
- per-user HR@10, NDCG@10 and macro GAUC from one shared evaluator;
- method-faithful objectives and negative sampling;
- official-source reproduction and harmonized-v5 reporting kept separate;
- isolated per-framework environments and immutable receipts before any execution.

## Closed row statuses

| Frozen candidate | FD4 status | Reason positive status is withheld |
|---|---|---|
| `R3-BUNDLE-CORNAC-ML100K-001` | `COMPATIBILITY_INCOMPLETE` | BPR and all-item scoring seams replayed, but event folding, full-catalog cold-ID parity, adapter/environment identities and exact frozen HTML locator replay are unresolved. |
| `R3-BUNDLE-ELLIOT-ML1M-001` | `COMPATIBILITY_INCOMPLETE` | BPRMF, fixed tabular input and pre-mask factor scores replayed, but training-derived item identity omits cold items without an unimplemented patch; the legacy environment and failed HTML locators remain unresolved. |
| `R3-BUNDLE-DAISYREC-ML1M-001` | `COMPATIBILITY_INCOMPLETE` | Pairwise MF score export is plausible, but the pinned native pipeline derives cardinality after train+TEST concatenation; a no-TEST manifest driver, parity evidence, environment and failed HTML locators remain unresolved. |

These equal status labels are not a ranking. No candidate is selected, preferred, merged, dropped or repaired with evidence from another row.

## Candidate findings

### Cornac 2.6.0 / MovieLens 100K

The pinned owner source documents BPR, UIR/UIRT datasets, caller-supplied global ID maps, pre-split construction and an all-known-item `score` method. Those surfaces make a representation-only v5 score exporter plausible. The source MovieLens shuffled ratio split, threshold, candidate construction and printed metrics remain confined to official reproduction.

The central blocker is not BPR task family; it is missing project closure. The v5 baseline policy does not yet freeze which event types become BPR positives or how repeated weighted events collapse. The complete catalog map and 250 cold items have not been materialized or parity-tested. No adapter, environment, argv, score artifact or receipt exists. Therefore a positive compatibility status would be inferred rather than verified.

Bounded future patch perimeter: freeze event folding; predeclare frozen user/item maps without synthetic interactions; export unmasked BPR scores; delegate candidates/masks/ties/metrics to v5; then strict-validate manifests and parity fixtures. BPR mathematics, sampling and score function must remain unchanged.

### Elliot v0.3.1 / MovieLens 1M

The pinned owner source confirms a four-column user/item/rating/timestamp loader, a fixed data strategy, BPRMF pairwise updates and dense factor-dot-product scores before Elliot's own mask/top-k. A bounded score exporter is therefore plausible in architecture.

The pinned dataset object derives its item map from training interactions. That does not by itself cover the v5 cold catalog. A future patch would have to predeclare all item identities and allocate untouched factors without synthetic positives, TEST reads or score imputation. The v5 event-folding rule is also unfrozen. The dependency set is legacy and has no tested isolated lock. No parity or runtime receipt exists, and failed frozen HTML locators remain unresolved. Status stays incomplete.

### DaisyRec 2.0 / MovieLens 1M

The pinned owner source confirms top-N benchmarking, BPR loss for pairwise MF, uniform negative sampling, time-aware split implementations and vectorized user-item prediction. Source time-aware semantics are not identical to the frozen v5 cutoffs and do not transfer automatically.

The pinned native main pipeline concatenates train and test before deriving `item_num`. That path is impermissible for sealed v5 TEST. A future bounded driver would have to take user/item cardinalities from the frozen manifest, consume only frozen train/validation inputs, allocate the full catalog, export scores before `torch.topk`, and route them through the shared evaluator. That driver and all parity/environment receipts are absent. Frozen HTML/result locator failures also remain unresolved, so status stays incomplete.

## Dispositive-mismatch result

No dispositive mismatch was positively established from the verified evidence. This is not a positive compatibility finding. Each row remains incomplete because decision-bearing adapter details and replay/parity/runtime evidence are missing. If any future patch requires synthetic interactions, TEST-derived identity discovery, candidate dropping, missing-score imputation, sampled harmonized evaluation, objective changes or evaluator substitution, that row must become `DISPOSITIVE_REJECT`.

## Baseline coverage boundary

All three rows plausibly address the mandatory BPR-MF role. Framework inventories mention additional models, but no additional model is independently bound here to a revision, method-faithful config, v5 adapter and parity receipt. None of these rows establishes complete mandatory-baseline registry coverage.

## Handoff

FD4 returns three `COMPATIBILITY_INCOMPLETE` rows in frozen order. R3-G1 may join them by exact candidate ID only after central validation and must not interpret architectural plausibility as materialization readiness. Execution and selection remain outside this lane.

