# R5-G1 Central Source-Evidence Selection Report

Date: 2026-08-23
Context: current central
Model: Sol Max Standard (`gpt-5.6-sol`, reasoning `max`, service tier `standard`)

## Decision

`PROVISIONAL_SINGLE_CANDIDATE_FOR_DATA_ENVIRONMENT_PROPOSAL`

R5-G1 selects `R5-CAND-RECBOLE-BPR-ML100K-001` at RecBole revision `9a6f63d8d4a5b989fe27955a833f813a6d86041e` for an R5-M2 proposal only.

This is not benchmark admission, does not verify reproducibility, does not accept README NDCG@10 `0.2768`, and does not authorize a dataset download, environment creation, package installation, preprocessing, training, evaluation, or TEST access.

## Frozen-input verification

- R5-G1 manifest: `research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r5_g1_frozen_input_manifest.json`
- Canonical-LF SHA-256: `8ef3d2ef000051fdb69edea75297e1a6a5d5434d6abce5e7693ae506f0f38400`
- Inputs verified: 23/23
- Strict JSON inputs verified: 18/18
- R5-M1 outputs verified: 10/10
- Source facts: 75 total; 56 positive facts hash-bound; 0 hash-binding failures
- Dispositive source conflicts: 0

No cross-candidate fact borrowing or numeric-target ranking was used.

## Candidate comparison

### Selected for proposal: RecBole BPR / MovieLens 100K

The exact locked RecBole tree contains the relevant entrypoint, configuration precedence, current defaults, seed behavior, trainer/evaluator surfaces, history masking, BPR objective, and complete per-user score seam. Its remaining eight handoff blockers are substantial but finite and explicitly located:

1. deterministic environment closure;
2. canonical MovieLens 100K provider and byte lineage;
3. producer-bound numeric-target policy;
4. TEST-safe validation-only orchestration;
5. v5 dataset/catalog lineage;
6. representation adapter and standalone evaluator parity;
7. official-source rerun receipts; and
8. harmonized-v5 validation plus a later separate TEST gate.

The source top-k tie behavior, weighted source GAUC, random source split, stock tuning paths, and README `BPRMF` label are explicit bounded conflicts. They require separate official-source and harmonized-v5 namespaces; none may be silently relabeled as v5 parity.

### Deferred: RecBole-GNN LightGCN / MovieLens 1M

The exact LightGCN model and all-item score seam are source-bound, and no permanent conflict was found. It is not selected in this wave because the locked tree delegates inherited configuration, training, data loading, candidate construction, masking and evaluator semantics to RecBole 1.1.1, whose exact source/package artifact is not materialized for this candidate. Its next scope therefore begins with an additional dependency-source and PyTorch/PyG/`torch_sparse` ABI closure before it can reach the same bounded data/environment checkpoint.

This is a deferral, not a scientific rejection of LightGCN.

## Numeric evidence boundary

- RecBole BPR README NDCG@10 `0.2768`: provisional documentation only, not producer-bound, invalid for paper use.
- RecBole-GNN LightGCN NDCG@10 `0.2538`: source-located but not producer-bound, invalid for paper use.
- Neither value was used to rank the candidates.
- Both require a preregistered same-surface rerun and immutable receipts before any reproducibility claim.

## R5-M2 mandatory checkpoint

R5-M2 is now `OPEN_AWAITING_EXPLICIT_USER_SCOPE_APPROVAL`. A proposal for the selected BPR candidate must freeze:

- the canonical MovieLens 100K provider/release and rights record;
- archive, extraction, conversion, atomic-file, split and ID-map hash lineage;
- a deterministic environment-closure procedure without guessing historical producer versions;
- an exact source-reproduction command/config receipt and TEST-safe validation-only wrapper;
- target statistic, seed schedule, tolerance and fail rule before seeing output;
- a full-score representation adapter and standalone v5 evaluator with tie/mask/metric parity fixtures; and
- separate later approvals for materialization, execution, and one-time TEST access.

Until that checkpoint is explicitly approved: `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, `execution_authorized=false`, and all current project benchmark numbers remain `INVALID_FOR_PAPER`.

## Model-policy change control

Future subagents follow `e4_r5_future_subagent_model_policy.json`:

- High/critical semantic audits: Sol XHigh Fast (`xhigh`, service tier `priority`).
- Bounded mechanical work with frozen contracts: Sol High Fast (`high`, service tier `priority`).
- Central selection/admission/authorization gates: Sol Max Standard.

The policy was recorded after the R5-G1 scientific input freeze and changes dispatch latency only. It does not rewrite the completed R5-M1 profiles or alter any scientific criterion.
