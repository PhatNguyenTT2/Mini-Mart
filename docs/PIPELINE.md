# Pipeline

Every stage reads one configuration file (`--config`, see `configs/pipeline/example.json`). Relative
paths are resolved against the configuration file. Run the stages from the `pipeline/` directory
with the package installed (`pip install -e .`).

```
01 generate ─► 02 check ─► 03 seal TEST ─► 04 train/validate ─► 05 freeze ─► 06 open TEST ─► 07 groups ─► 08 verify
   (data)                     (custody)        (VALIDATION only)    (selection)   (exactly once)   (descriptive)  (independent)
```

## Inputs

| Config key | Content |
|------------|---------|
| `snapshot_root` | Canonical snapshot: `manifest.json`, `items.jsonl`, `train.jsonl`, `val.jsonl` (hash-bound by the manifest). The TEST split is not read from here. |
| `feature_root` | `raw_item_ids.npy` (int64), `text_embeddings.npy` (float32, `[items, 384]`), `category_ids.npy` (int64), aligned row by row. The catalog must equal the set of items seen in TRAIN. |
| `rules_root` | Pair-rule table mined from TRAIN baskets (`manifest.json` plus arrays), loaded by `hybrid_recsys.data.pair_rules`. |
| `work_root` | Output directory for every stage. |

## Stages

| Stage | Script | Reads | Writes |
|-------|--------|-------|--------|
| 1 | `01_generate_split.cjs` | Mini-Mart data generator (`backend/docs/chatbot` on `main`), seed, optional `--test-reseed` | A generated bundle (`events.jsonl`, `baskets.jsonl`, `items.jsonl`, `users.jsonl`) |
| 2 | `02_check_splits.py` | Generated bundle, reference export | Pass/fail: TRAIN and VAL must be byte-identical |
| 3 | `03_seal_test.py` | Generated bundle | `custody/test_source_events.jsonl`, `custody/custody_receipt.json`; deletes the bundle |
| 4 | `04_train_validate.py` | Snapshot, features, rules | `validation/<unit>/result.json`, `per_user_metrics.npz`, `best.pt` |
| 5 | `05_freeze.py` | Validation results | `freeze.json`: selected λ and W&D learning rate, checkpoint hashes, cohort gates |
| 6 | `06_score_test.py --open` | Freeze, sealed TEST, `open_authorized.json` | `test/per_user_metrics.npz`, `test/test_results.json` |
| 7 | `07_group_analysis.py` | Opened TEST results, raw split files | `test/results_groups.json` |
| 8 | `08_verify_numbers.py` | Frozen checkpoints, opened TEST | `test/results_final.json` |

## Evaluation rules

- **Task.** For every eligible user, rank the full TRAIN-observed catalog. Items the user has already
  interacted with are masked. Ties are broken by raw product id.
- **Positives.** Organic purchases in the evaluated split, minus the user's history.
- **Metrics.** NDCG@10, HR@10 and per-user AUC (GAUC), averaged over users, then over seeds.
- **History.** VALIDATION uses TRAIN history. TEST uses TRAIN + VALIDATION history and the same
  catalog.
- **Selection happens on VALIDATION only.** Stage 5 fixes λ (mean NDCG@10 over seeds) and the
  Wide&Deep wide learning rate (first seed) before TEST is opened. Nothing after stage 5 selects
  anything.
- **TEST is opened once.** Stage 6 refuses to run without the freeze, a sealed TEST file that
  matches its custody receipt, and an `open_authorized.json` written by a person after reviewing
  the freeze. It also refuses when `test/` already exists. Every contrast is reported, favourable
  or not.
- **Statistics.** Hybrid is compared with each comparator by a crossed paired bootstrap that
  resamples users and seeds (2,000 replicates; one schedule shared by all contrasts). The primary
  contrast is Hybrid vs ItemKNN on NDCG@10. The remaining contrasts are Holm-adjusted. Analyses in
  stages 7 and 8 are descriptive or exploratory.
- **Independent check.** Stage 8 re-scores every model from its frozen checkpoint and recomputes
  the metrics with a separate implementation. Differences are reported per method.

## Determinism

`hybrid_recsys.training.runtime.deterministic` seeds Python, NumPy and PyTorch and enables
deterministic kernels. Deep and Wide&Deep shuffle the training examples with a seed derived from
(seed, epoch). Negative samples are drawn from a seed derived from (epoch, batch position).
