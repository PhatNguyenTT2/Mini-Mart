# Stage 1E Rebaseline v2 — Reproduction Acceptance Rules

> Material Passport: `stage1e_rebaseline_v2_wave_a_E3` · model `gpt-5.6-sol` · reasoning `xhigh` · status `UNVERIFIED`
> ARS experiment-agent state: evidence discovery/lock only; no command confirmation packet and no execution
> Access date `2026-08-22` · input manifest SHA-256 `107299c026434366ed6ddb18f4ee6e25fd790d9799fd81c1c1e87871ed60744d`
> `RESULT_STATUS=NOT_RUN` · `ACCEPTED_RESULT_ROWS=0` · `TEST_SET_OPENED=NO`

## 1. Scope and precedence

These rules judge only whether an implementation reproduces its own official or framework-authoritative result. They do not compare v5 to an official-dataset value. A raw metric from a different dataset, processed revision, split, candidate policy or evaluator is never converted into a PASS/FAIL judgment.

The decision order is fixed:

1. Establish that the repository revision, dataset artifact, preprocessing, split, objective, configuration, seed schedule, checkpoint selection, metric protocol and reported center belong to one source-bound row.
2. If an acceptance-critical field or required artifact is unresolved before execution, return `PENDING` and do not authorize the run.
3. If a proposed or completed run differs on any identity/protocol gate, return `INCOMPARABLE`; do not apply numeric tolerance.
4. If the gates match but the required run did not complete or lacks a complete receipt, return `PENDING`.
5. Only after all gates match and the run/aggregation is complete, compare every required metric to its frozen numeric interval. All required metrics inside their intervals is `PASS`; one or more outside is `FAIL`.

`FAIL` is reserved for a numeric miss under a fully comparable protocol. A crash, missing seed, missing checkpoint, unavailable data artifact or resource shortage is `PENDING`, not a scientific failure. A reduced model, substituted implementation, altered sampler or changed evaluator is `INCOMPARABLE`, not a retry.

## 2. Identity and protocol gate

Every field below is conjunctive. The execution receipt must record it before a numeric verdict is legal.

| Gate | Exact-match requirement | Missing before run | Mismatch |
|---|---|---|---|
| Implementation | Repository URL, full commit SHA, provenance class and entrypoint | `PENDING` | `INCOMPARABLE` |
| Dataset | Provider/artifact identity, processed revision/hash, model-visible files | `PENDING` | `INCOMPARABLE` |
| Preparation | Filtering, ordering/session/basket construction and feature/text generation | `PENDING` | `INCOMPARABLE` |
| Split | Unit, proportions/leave-one-out rule, validation treatment and fixed split receipt | `PENDING` | `INCOMPARABLE` |
| Training | Objective, architecture/config, negative count/sampler and dependency/runtime lock | `PENDING` | `INCOMPARABLE` |
| Stochastic schedule | Exact seed identities and required number of runs | `PENDING` | `INCOMPARABLE` |
| Selection | Validation metric, patience/evaluation cadence, checkpoint/result-row rule | `PENDING` | `INCOMPARABLE` |
| Metric | Name, formula, K, averaging unit, eligible users, relevance and tie policy | `PENDING` | `INCOMPARABLE` |
| Candidates | Full catalog or sampled, seen/repeat masking, evaluation negative count and sampler | `PENDING` | `INCOMPARABLE` |
| Target | Center, dispersion status/run aggregation and primary locator | `PENDING` | `INCOMPARABLE` |

Tie policy is part of the protocol. If the source merely delegates ties to `torch.topk` or another implementation primitive, E4 must pin the runtime and preserve that behavior. Adding v5’s `(-score, raw_item_id)` tiebreak to an official evaluator would create a harmonized result, not an official-protocol reproduction.

## 3. Frozen tolerance

For a reported center `c`, the pre-run tolerance is:

```text
t(c) = max(0.005, 0.05 × |c|)
PASS for metric m iff |m - c| <= t(c)
```

The boundary is inclusive. Arithmetic uses the unrounded reported center as printed by the primary artifact; no tolerance is tightened by unreported dispersion or widened after observing a run. This is the Stage 1E contract default; no candidate supplies a justified source-bound alternative.

For a row with multiple required metrics, the row passes only if every metric passes. Do not average normalized deviations, select the best seed, omit an inconvenient metric or replace a failed/missing seed. Where a paper reports a five-run mean, the observed value must be the mean of the exact five locked runs; per-run dispersion may be reported separately but cannot replace the required mean.

## 4. Frozen numeric intervals

These intervals are dormant until the identity/protocol gate passes.

| Pair | Metric | Center | Tolerance | Inclusive PASS interval |
|---|---|---:|---:|---:|
| `E3-LIGHTGCN-GOWALLA-PYTORCH-001` | Recall@20 | 0.182400 | 0.009120 | [0.173280, 0.191520] |
|  | NDCG@20 | 0.154700 | 0.007735 | [0.146965, 0.162435] |
|  | Precision@20 | 0.055890 | 0.005000 | [0.050890, 0.060890] |
| `E3-SIMGCL-YELP2018-QREC-001` | Recall@20 | 0.072100 | 0.005000 | [0.067100, 0.077100] |
|  | NDCG@20 | 0.060100 | 0.005000 | [0.055100, 0.065100] |
| `E3-XSIMGCL-YELP2018-SELFREC-001` | Recall@20 | 0.072300 | 0.005000 | [0.067300, 0.077300] |
|  | NDCG@20 | 0.060400 | 0.005000 | [0.055400, 0.065400] |
| `E3-LIGHTGCL-YELP-UPDATED-001` | Recall@20 | 0.098500 | 0.005000 | [0.093500, 0.103500] |
|  | NDCG@20 | 0.084200 | 0.005000 | [0.079200, 0.089200] |
|  | Recall@40 | 0.155300 | 0.007765 | [0.147535, 0.163065] |
|  | NDCG@40 | 0.105100 | 0.005255 | [0.099845, 0.110355] |
| `E3-UNISREC-SCIENTIFIC-TRANS-001` | Recall@10 | 0.123500 | 0.006175 | [0.117325, 0.129675] |
|  | NDCG@10 | 0.063400 | 0.005000 | [0.058400, 0.068400] |
|  | Recall@50 | 0.247300 | 0.012365 | [0.234935, 0.259665] |
|  | NDCG@50 | 0.090400 | 0.005000 | [0.085400, 0.095400] |
| `E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001` | Recall@10 | 0.108000 | 0.005400 | [0.102600, 0.113400] |
|  | NDCG@10 | 0.055300 | 0.005000 | [0.050300, 0.060300] |
|  | Recall@50 | 0.204200 | 0.010210 | [0.193990, 0.214410] |
|  | NDCG@50 | 0.076000 | 0.005000 | [0.071000, 0.081000] |
| `E3-BTBR-TAFENG-JOINT-001` | Recall@10 | 0.105700 | 0.005285 | [0.100415, 0.110985] |
|  | nDCG@10 | 0.087000 | 0.005000 | [0.082000, 0.092000] |
|  | Recall@20 | 0.135300 | 0.006765 | [0.128535, 0.142065] |
|  | nDCG@20 | 0.097300 | 0.005000 | [0.092300, 0.102300] |
| `E3-ALPHAREC-MOVIES-TV-001` | Recall@20 | 0.122100 | 0.006105 | [0.115995, 0.128205] |
|  | NDCG@20 | 0.114400 | 0.005720 | [0.108680, 0.120120] |
|  | HR@20 | 0.558700 | 0.027935 | [0.530765, 0.586635] |

## 5. Pair-specific fail-closed rules

### LightGCN PyTorch

- The acceptable target is the author PyTorch README’s own Gowalla layer-3 row, not a LightGCN paper table or a RecBole result.
- Seed must be exactly `2020`; K must be `20`; the repository’s full-catalog masking and macro evaluator must be preserved.
- Until raw-data lineage and the exact result-row/checkpoint selection are confirmed, the verdict remains `PENDING` even if a produced number falls inside the interval.

### SimGCL / QRec

- The target is the paper’s 3-layer Yelp2018 five-run mean.
- All five exact source-bound seeds are required. Because their identities are not published in the sources currently locked, the row remains `PENDING`.
- SELFRec or LightGCL implementations of SimGCL are different rows and cannot be substituted.

### XSimGCL / SELFRec

- The current repository target is `0.0723/0.0604`, layer 3.
- Paper Table 6 `0.0733/0.0606` is a separate best/layer result. Pairing it with layer 3 is `INCOMPARABLE`.
- A future E4 packet may instead build a distinct paper-table row only after pinning the correct layer, config, split, five seeds and implementation/runtime.

### LightGCL

- The current repository command uses the updated interaction-pair sampler and may be compared only to Appendix E Table 6.
- Comparing it with original Table 1 is always `INCOMPARABLE`, regardless of numerical closeness.
- Split, run count/seeds, checkpoint and evaluator semantics are unresolved, so the current verdict is `PENDING`.

### UniSRec and UniSRec-experiment SASRec

- `UniSRec_t+ID` must use the named `UniSRec-FHCKM-300.pth` transductive path; inductive (`UniSRec_t`) or scratch values are different rows.
- SASRec is framework-authoritative only for the UniSRec experiment. It must use the repository’s exact Scientific processed data and config stack.
- An unversioned Drive archive or checkpoint without a verified hash leaves the row `PENDING`.

### BTBR

- The target is the joint pretrain-finetune column averaged over five splits, not the README Method 1 command.
- The README’s batch 64/fold 0 item-select run is `INCOMPARABLE` with the paper’s batch 128/five-split/joint row.
- Without an exact joint command and data/split/seed receipts, no numeric comparison is authorized.

### AlphaRec

- The target requires `amazon_movie`, text-embeddings-3-large (`v3`), 2 graph layers, MLP mode, tau `0.15`, InfoNCE and 256 training negatives.
- Substituting an embedding model/revision, sampled evaluation, a different history split or another Amazon release is `INCOMPARABLE`.
- Unhashed data/embedding artifacts and absent seed/run/formula details keep the row `PENDING`.

## 6. Deterministic pseudocode

```text
function verdict(row, receipt, observed_metrics):
    if row.acceptance_critical_evidence_missing:
        return PENDING

    if receipt is absent or receipt.execution_incomplete:
        return PENDING

    if any identity_or_protocol_gate(receipt, row) != exact_match:
        return INCOMPARABLE

    if any required seed/checkpoint/metric output is absent:
        return PENDING

    for target in row.required_targets:
        tol = max(0.005, 0.05 * abs(target.center))
        if abs(observed_metrics[target.metric] - target.center) > tol:
            return FAIL

    return PASS
```

No automatic retry, seed replacement, post-run tolerance revision, test-guided tuning or architecture reduction is permitted. E4 may draft exact commands only from an E3 row whose missing fields have been resolved; E5 must independently replay the joins and arithmetic before the user is asked to confirm execution.
