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

## Data preparation

Stages 4 and later read three prepared inputs. They are built once from the TRAIN and VAL splits
and never from TEST. `tests/pipeline_fixture.py` builds a small synthetic copy of all three and is
the shortest working example.

### Snapshot (`snapshot_root`)

A canonical snapshot (`dataset-manifest/1.1`, loaded by `hybrid_recsys.data.io.load_canonical_snapshot`)
is a directory with exactly these files:

| File | One JSON object per line |
|------|--------------------------|
| `users.jsonl` | `user_id` (dense, 0-based), `raw_user_id` |
| `items.jsonl` | `item_id` (dense, 0-based), `raw_item_id`, `text`, `category`, `price` |
| `baskets.jsonl` | TRAIN baskets: `basket_id`, `user_id`, `timestamp`, `item_ids` (sorted, at least two distinct), `origin`; ordered by timestamp |
| `train.jsonl`, `val.jsonl` | Events: `event_id` (unique across splits), `raw_event_id`, `user_id`, `item_id`, `timestamp` (µs), `event_type` (`purchase`, `view`, ...), `basket_id`, `event_origin` (`organic` or a generator label), `session_id`, `cohort_id` |
| `manifest.json` | Counts and hashes of all of the above |

Every hash in the manifest is `hybrid_recsys.hashing.canonical_json_sha256` of a fixed payload, for
example `{"split": "train", "rows": [...]}` for `split_hashes.train`,
`{"raw_item_ids": [...]}` for `raw_item_map_sha256`, and `{"text": [{"item_id", "text"}, ...]}` for
`item_feature_hashes.text`. The loader checks each hash and refuses a mismatch. `test.jsonl` may be
missing: stages 4 and 5 never open it, and stage 6 reads TEST from the sealed custody file.

### Item features (`feature_root`)

Three NumPy arrays, aligned row by row. Their row order is the candidate order used by every stage:

- `raw_item_ids.npy`: int64 `[N]`, exactly the items observed in TRAIN, in ascending raw id.
- `text_embeddings.npy`: float32 `[N, 384]`. Item `text` encoded with
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` and stored as produced, without
  normalisation. The encoder stays frozen during training.
- `category_ids.npy`: int64 `[N]`. The position of the item's `category` string among the sorted
  distinct category strings.

The config key `feature_identity` records where the features came from: the model repository
revision, the SHA-256 of the materialised model files, and the SHA-256 of the category mapping. It
enters the model's feature-descriptor hash. When it is left out, placeholders computed from the
arrays are used.

### Pair rules (`rules_root`)

Pair rules are mined from TRAIN baskets only with `hybrid_recsys.data.pair_rules.materialize_pair_rules`:

```python
from hybrid_recsys.data.pair_rules import materialize_pair_rules

table = materialize_pair_rules(view, root=rules_root, min_support_fraction=0.0005)
table.close()
```

`view` provides `raw_item_ids` (in the feature order above), `manifest_sha256`,
`test_access_state == "LOCKED_NOT_ACCESSED"`, and `iter_train_baskets()`. That last method yields
baskets whose `item_ids` are sorted indices into that order. A rule `a -> b` is kept when the pair
occurs in at least `ceil(fraction x TRAIN baskets)` baskets, and its weight is the confidence
`count(a, b) / count(a)`. The allowed fractions are 0.0005, 0.001 and 0.002. The output directory
holds `manifest.json` (with per-file SHA-256) and the CSR arrays read by `load_pair_rule_table`.
At scoring time, a user's rule score for an item is the sum of confidences from the items in the
user's history.

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
