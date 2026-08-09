# `ai-service` Four-Sprint Production Execution Plan

## 1. Summary and Locked Decisions

Build `ai-service/` as four deep modules with small interfaces: immutable data artifacts, hybrid model scoring, reproducible evaluation, and artifact-only ONNX serving.

Key decisions:

- Require a timestamped PostgreSQL relation `ml_interaction_event_v1`; the current aggregated `user_product_interaction` table cannot support leakage-safe temporal splitting.
- Preserve `/recommend` as bounded candidate reranking. Full-catalog ranking remains an offline evaluation path.
- Include Chatbot contract, Compose, and CI/CD integration work.
- Use the repository’s actual catalog cardinality: 14 roots and 40 leaves. Category embedding is therefore `[41,16]`, with row `0` reserved for unknown.
- Pin v1 artifacts to `store_id=1`; add backward-compatible `store_id` support to the HTTP contract.
- Define “sub-millisecond” as warmed ONNX Runtime execution for 100 candidates, not HTTP or full-catalog latency.
- Treat 823,371 interactions, 5,200 SKUs, 5,000 users, 250 cold items, and 13,046 raw Apriori pairs as named-snapshot validations, not tensor-index assumptions.
- Use raw-ID vocabularies because product IDs are sparse; never clamp external IDs.

### Canonical tensor contract

| Tensor | Shape | Contract |
|---|---:|---|
| User indices | `[B]` | `0=UNK`, known users `1..5000` |
| User ID embedding | `[5001,64]` | UNK row replaced with mean known embedding before evaluation/export |
| Persona embedding | `[8,8]` | Invalid/missing persona falls back to train-majority cluster; ties resolve to cluster `0` |
| User concatenation | `[B,72]` | `64+8` |
| User vector | `[B,64]` | L2-normalized |
| Frozen SBERT cache | `[5200,768]` | Float32, ordered by persisted product map |
| Category embedding | `[41,16]` | 40 known leaf categories plus UNK |
| Price embedding | `[9,8]` | Eight buckets plus UNK |
| Item concatenation | `[B,C,88]` | `64+16+8` |
| Item vector | `[B,C,64]` | L2-normalized |
| Training candidates | `[B,5]` | One positive plus four dynamic negatives |
| Training pair count | `5B` | Default `B=2048`, effective 10,240 pairs |
| Full-catalog users/items | `[5000,64]`, `[5200,64]` | GPU matrix multiplication |
| Full-catalog deep logits | `[5000,5200]` | 26,000,000 float32 scores, about 104 MB decimal |

### Scoring and loss

For normalized user and item vectors:

\[
S_{\text{deep}}(u,i)=\frac{\mathbf u^\top\mathbf v_i}{\tau},
\qquad \tau=0.1,
\qquad S_{\text{deep}}\in[-10,10].
\]

For one context anchor \(a\):

\[
r(a,i)=
\begin{cases}
\log(1+L_{a,i}) & \text{if a valid train-only rule exists}\\
0 & \text{otherwise.}
\end{cases}
\]

Training uses the most recent prior positive item as \(a\); serving uses `context_product_id`; no context means an exact zero Wide contribution.

\[
S_{\text{wide}}(a,i)=
\mathbf 1[r(a,i)>0]\left(
W_2\operatorname{ReLU}(W_1r(a,i)+b_1)+b_2
\right).
\]

\[
z(u,a,i)=S_{\text{deep}}(u,i)+S_{\text{wide}}(a,i),
\qquad P(y=1)=\sigma(z).
\]

Use `BCEWithLogitsLoss`, not a model-level sigmoid. With positive-event weights \(w_b\):

\[
\mathcal L=
\frac{\sum_{b=1}^{B}\sum_{c=1}^{5}
w_b\,\operatorname{BCEWithLogits}(z_{bc},y_{bc})}
{5\sum_{b=1}^{B}w_b}.
\]

`log1p(822.67)≈6.713`; zero exclusively represents “no rule.” For active `lift>1`, the smallest positive value is greater than `log(2)≈0.693`.

## 2. Sprint 1 — Infrastructure and Data Pipeline

### Sprint 1 entry gate: timestamped data contract

**Companion targets outside `ai-service/`:**

- `backend/services/chatbot/src/db/init.sql`
- `backend/docs/chatbot/seed-product/mock-interactions-v2.js`
- `backend/docs/chatbot/seed-product/mock-orders-v2.js`

**Required relation:**

```text
ml_interaction_event_v1(
  event_id            TEXT PRIMARY KEY,
  store_id            BIGINT NOT NULL,
  user_id             BIGINT NOT NULL,
  product_id          BIGINT NOT NULL,
  persona_cluster     SMALLINT NOT NULL,
  event_type          TEXT NOT NULL,
  event_ts            TIMESTAMPTZ NOT NULL,
  interaction_weight  REAL NOT NULL
)
```

Implementation requirements:

- Make the relation append-only and index `(store_id,event_ts,event_id)` and `(store_id,user_id,event_ts)`.
- Generate the synthetic benchmark with a fixed seed and stable event IDs; production data must use genuine event timestamps rather than fabricated backfill timestamps.
- Ensure the 250 designated cold products have test-period positive ground truth but no train/validation events.
- Preserve delivered/paid order baskets for train-cutoff Apriori mining.
- Fail the Sprint 1 gate if event timestamps, personas, cold truth, or deterministic snapshot counts are absent.

Verification:

```bash
psql "$CHATBOT_DATABASE_URL" -c \
  "SELECT COUNT(*), COUNT(DISTINCT user_id), COUNT(DISTINCT product_id)
   FROM ml_interaction_event_v1 WHERE store_id=1;"

psql "$CHATBOT_DATABASE_URL" -c \
  "SELECT COUNT(*) FROM ml_interaction_event_v1
   WHERE event_ts IS NULL OR interaction_weight <= 0
      OR persona_cluster NOT BETWEEN 0 AND 7;"
```

### Task 1.1 — Python foundation and configuration

**Target paths:**

- `ai-service/config.py`
- `ai-service/pyproject.toml`
- `ai-service/requirements.txt`
- `ai-service/requirements-serve.txt`
- `ai-service/{data,models,training,evaluation,export,service}/__init__.py`
- `ai-service/tests/`

**Technical specifications:**

- Python 3.11.
- Typed immutable settings groups: `DataConfig`, `ModelConfig`, `TrainConfig`, `EvalConfig`, `ServingConfig`.
- Defaults:
  - `NUM_USERS=5000`, `NUM_ITEMS=5200`, `NUM_PERSONAS=8`
  - `NUM_LEAF_CATEGORIES=40`, `NUM_PRICE_BUCKETS=8`
  - dimensions `64/8/16/8/768/64`
  - `TAU=0.1`, `BATCH_SIZE=2048`, `NEGATIVE_RATIO=4`
  - `LR=1e-3`, `WEIGHT_DECAY=1e-5`
  - `MAX_EPOCHS=30`, `EARLY_STOPPING_PATIENCE=4`
  - `MIN_DELTA=1e-4`, `SEED=42`
  - `MIN_RULE_COUNT=3`, `MIN_RULE_LIFT=1.0`
  - `MAX_CANDIDATES=256`, `STORE_ID=1`.
- Database credentials come only from environment variables and are never serialized into manifests.
- `requirements.txt` contains training/evaluation dependencies; `requirements-serve.txt` contains only FastAPI, NumPy, ONNX Runtime, Pydantic settings, Prometheus client, and Uvicorn.
- Introduce Ruff, mypy, pytest, and markers for `integration`, `gpu`, and `benchmark`.

**Optimizations and gotchas:**

- Cardinalities validate snapshots but never serve as raw-ID bounds.
- Resolve all filesystem paths relative to `ai-service/`, not the process working directory.
- Reject invalid dimensions, nonpositive temperature, invalid negative ratios, and missing DB URLs at startup.
- Serving configuration must not import PyTorch or Transformers.

**Implementation checklist:**

- [ ] Implement cached `get_settings()` and environment overrides.
- [ ] Separate offline DB settings from runtime serving settings.
- [ ] Add deterministic seed helpers for Python, NumPy, PyTorch, CUDA, and DataLoader workers.
- [ ] Establish artifact directories under `artifacts/data/`, `artifacts/runs/`, and `artifacts/model/`.
- [ ] Add unit tests for defaults, overrides, validation, secret redaction, and path resolution.

**Verification:**

```bash
cd ai-service
python -m pytest tests/unit/test_config.py -q
python -m ruff check .
python -m mypy config.py data models training evaluation export service
```

### Task 1.2 — PostgreSQL extraction, vocabularies, and temporal isolation

**Target path:** `ai-service/data/ingestion.py`

**Public interface:**

```python
build_snapshot(settings: Settings, snapshot_id: str) -> SnapshotManifest
load_snapshot(path: Path) -> SnapshotArtifacts
```

**Technical specifications:**

- Read `ml_interaction_event_v1` with a server-side cursor in 50,000-row batches.
- Separately snapshot:
  - products and categories from Catalog DB;
  - users/personas from the event relation;
  - delivered/paid order baskets from Order DB;
  - the existing 13,046-row `co_purchase_stats` table for audit comparison only.
- Persist contiguous maps:
  - `user_id → 1..5000`, reserving `0=UNK`;
  - `product_id → 0..5199`;
  - 40 raw leaf-category IDs → `1..40`, reserving `0=UNK`.
- Fit seven price boundaries on `log1p(unit_price)` from warm training items:

\[
q_k=Q_{k/8}(\log(1+\text{price})),\qquad k=1,\ldots,7.
\]

Bucket `0` is unknown; valid prices map to buckets `1..8`.

**Temporal split:**

- Sort by timestamp groups, with event ID as deterministic secondary order.
- Choose boundaries nearest the 80% and 90% cumulative row positions without splitting equal timestamps.
- Enforce:

\[
\max(t_{\text{train}})<\min(t_{\text{val}})
<\min(t_{\text{test}}).
\]

- Select/freeze the current 250 highest-ID products as the cold manifest.
- Require at least one test positive per cold item.
- Remove cold-item events from train and validation, remove cold items from negative pools and rule mining, and preserve their test events.

**Artifacts:**

```text
artifacts/data/<snapshot_id>/
  manifest.json
  catalog.parquet
  users.parquet
  splits/train.parquet
  splits/val.parquet
  splits/test.parquet
  order_baskets.parquet
  mappings.json
  cold_item_ids.npy
  price_boundaries.npy
```

`manifest.json` records schema version, UTC cutoffs, counts, source relation, store ID, mappings, configuration, and SHA-256 checksums.

**Optimizations and gotchas:**

- Never load all PostgreSQL rows into a Python list or Pandas frame.
- Do not use current all-time Apriori rules, popularity, or validation/test positives to create train features.
- Keep guest/null users out of the known embedding map; they resolve to UNK during serving.
- Product names/categories have no historical change log, so the benchmark treats the catalog snapshot as static and records its extraction time.
- The stale 1,128,450/79,631 figures in `inputs/experimental_log2.md` must not enter configuration.

**Implementation checklist:**

- [ ] Implement chunked extraction and incremental Parquet row groups.
- [ ] Validate IDs against product/user snapshots.
- [ ] Detect duplicate event IDs and invalid weights.
- [ ] Create strict split assertions and leakage reports.
- [ ] Persist cold, mapping, price-bin, and cutoff manifests atomically.
- [ ] Fail the named benchmark if interaction count differs from 823,371.
- [ ] Record, but do not require, the all-time raw rule count of 13,046.
- [ ] Add synthetic integration fixtures covering equal timestamps and sparse raw IDs.

**Verification:**

```bash
python -m data.ingestion \
  --snapshot-id scaled-v1 \
  --store-id 1 \
  --validate-only

python -m pytest \
  tests/unit/test_ingestion.py \
  tests/integration/test_postgres_snapshot.py -q
```

### Task 1.3 — Frozen Vietnamese SBERT precomputation

**Target path:** `ai-service/data/precompute_sbert.py`

**Public interface:**

```python
precompute_embeddings(snapshot: SnapshotArtifacts) -> EmbeddingManifest
```

**Technical specifications:**

- Model: `keepitreal/vietnamese-sbert`.
- Resolve and persist the exact model/tokenizer revision.
- Canonical text:

```text
{name}. Thương hiệu: {vendor_or_unknown}.
Danh mục: {root_category} > {leaf_category}.
```

- Exclude live price, stock, interaction counts, popularity, and Apriori data.
- Encode in product-map order:
  - input: 5,200 text records;
  - output: `float32 [5200,768]`;
  - use normalized SentenceTransformer pooling;
  - default GPU batch size 128 with configurable fallback.
- Persist `sbert_embeddings.npy` plus model revision, text-template hash, product-map checksum, dtype, and normalization policy.

**Optimizations and gotchas:**

- Run once per catalog/text/model revision, not per training run.
- Use `torch.inference_mode()`, automatic device selection, pinned batches, and atomic output replacement.
- Resume only if partial-artifact metadata matches the same snapshot and model revision.
- Reject NaN/Inf rows, duplicate product IDs, shape mismatch, or norms outside tolerance.
- Cold items are included because text-only inference is the intended zero-shot path.

**Implementation checklist:**

- [ ] Load only catalog fields from the immutable snapshot.
- [ ] Pin the model revision and tokenizer settings.
- [ ] Produce normalized float32 embeddings in deterministic product order.
- [ ] Hash inputs and outputs.
- [ ] Add a small fixture-mode CLI for CI.
- [ ] Verify that no user/interaction columns enter the text template.

**Verification:**

```bash
python -m data.precompute_sbert \
  --snapshot-dir artifacts/data/scaled-v1 \
  --limit 32 \
  --verify

python -m pytest tests/unit/test_precompute_sbert.py -q
```

### Task 1.4 — Leakage-safe Apriori rule artifact

**Target path:** `ai-service/data/apriori_rules.py`

**Public interface:**

```python
build_rule_store(snapshot: SnapshotArtifacts) -> RuleStore
RuleStore.lookup(context_item_idx, candidate_item_idx) -> float
```

**Technical specifications:**

Mine only delivered/paid baskets whose `order_date < validation_cutoff`, after removing cold products.

For \(N\) train baskets:

\[
\operatorname{support}(A,B)=\frac{c_{AB}}{N},
\]

\[
\operatorname{confidence}(A\to B)=\frac{c_{AB}}{c_A},
\]

\[
\operatorname{lift}(A,B)=\frac{c_{AB}N}{c_Ac_B}.
\]

Use all valid baskets in \(N\), not only multi-item baskets. Retain rules with `co_purchase_count>=3`, finite `lift>1`, and known warm items.

- Materialize both directions of each unordered pair.
- Store `log1p(lift)` in a coalesced sparse matrix of size `[5200,5200]`.
- Expected scale: at most 13,046 raw pairs and about 26,092 directed edges before leakage and stability filters.
- Persist sorted CSR arrays for constant-time serving lookup:

```text
apriori_rules.npz:
  indptr[int64, 5201]
  indices[int32, E]
  log_lift[float32, E]
  count[int32, E]
```

**Optimizations and gotchas:**

- `torch.sparse.mm` would sum rule values and is not the required single-context lookup.
- `nn.Linear` cannot consume sparse tensors directly; evaluate the Wide MLP only on nonzero values, then scatter results.
- `.coalesce()` sums duplicates, so deduplicate pairs with maximum lift before sparse construction.
- The current `co_purchase_stats` table is all-time and may leak future orders; use it only for audit deltas.
- Do not assert that the leakage-safe active-rule count remains exactly 13,046.

**Implementation checklist:**

- [ ] Extract train-cutoff baskets.
- [ ] Compute frequency, support, directional confidence, and lift.
- [ ] Filter unstable/invalid/cold rules.
- [ ] Materialize directed sparse edges.
- [ ] Persist CSR and PyTorch sparse forms with checksums.
- [ ] Compare counts/distributions with current DB rules and emit an audit report.
- [ ] Add hand-calculated basket fixtures.

**Verification:**

```bash
python -m data.apriori_rules \
  --snapshot-dir artifacts/data/scaled-v1 \
  --verify

python -m pytest tests/unit/test_apriori_rules.py -q
```

### Task 1.5 — Dynamic 1:4 negative-sampling dataset

**Target path:** `ai-service/data/dataset.py`

**Public interface:**

```python
HybridImplicitDataset(snapshot, rule_store, split="train")
HybridImplicitDataset.set_epoch(epoch: int) -> None
collate_candidate_groups(samples) -> TrainingBatch
```

**Technical specifications:**

For every positive anchor, generate exactly four distinct warm negatives:

- two from the top 20% of warm items by train-only event count;
- two uniformly from the warm catalog.

With 250 cold items excluded, the popularity pool contains the top 990 of 4,950 warm items.

Return grouped tensors:

```text
user_idx             [B]
persona_idx          [B]
candidate_item_idx   [B,5]
context_item_idx     [B]
log_lift             [B,5,1]
labels               [B,5] = [1,0,0,0,0]
sample_weight        [B]
```

For each positive, `context_item_idx` is the most recent different positive item strictly before the event timestamp; missing context produces zero Wide features.

**Optimizations and gotchas:**

- Exclude the target, duplicate negatives, every train-positive item for the user, and all cold items.
- Never inspect validation/test positives when constructing exclusion sets.
- Use a stable RNG derived from `(seed, epoch, event_id)`; do not use Python’s randomized `hash()`.
- Keep ID arrays memory-mapped and create tensors in the collator, not inside every `__getitem__`.
- Use `num_workers=2`, pinned memory, prefetching, and persistent workers when CUDA is active.
- Fail explicitly for a pathologically dense user with fewer than four available negatives.

**Implementation checklist:**

- [ ] Build train-only popularity and exclusion structures.
- [ ] Implement deterministic 2+2 sampling without replacement.
- [ ] Compute context and rule features without temporal leakage.
- [ ] Vectorize feature gathering in the collator.
- [ ] Add multi-worker reproducibility tests.
- [ ] Verify that negatives change between epochs but reproduce for the same epoch/seed.

**Verification:**

```bash
python -m pytest tests/unit/test_dataset.py -q
python -m pytest tests/integration/test_dataloader_reproducibility.py -q
```

## 3. Sprint 2 — Model Architecture

### Task 2.1 — User tower

**Target path:** `ai-service/models/user_tower.py`

**Interface:**

```python
UserTower.forward(user_idx: Tensor[B], persona_idx: Tensor[B]) -> Tensor[B,64]
UserTower.refresh_unknown_embedding() -> None
```

**Architecture:**

\[
\operatorname{Embedding}(5001,64)
\oplus \operatorname{Embedding}(8,8)
\to [B,72]
\]

\[
\operatorname{Linear}(72,128)
\to \operatorname{ReLU}
\to \operatorname{LayerNorm}(128)
\to \operatorname{Linear}(128,64)
\to \operatorname{L2Norm}.
\]

**Optimizations and gotchas:**

- User row `0` is UNK and must not learn from known-user samples.
- Before validation, checkpointing, and export, replace row `0` with the mean of rows `1:`.
- Unknown users must never be clamped to user 5000 or converted to user 1.
- Missing personas map to cluster `0`; known explicit personas remain `0..7`.

**Implementation checklist:**

- [ ] Add shape/range validation.
- [ ] Initialize embeddings with small normal weights and linear layers with Xavier initialization.
- [ ] Implement L2 normalization with epsilon protection.
- [ ] Implement deterministic UNK refresh.
- [ ] Test gradients, norms, invalid IDs, and cold-user behavior.

**Verification:**

```bash
python -m pytest tests/unit/models/test_user_tower.py -q
```

### Task 2.2 — Item tower

**Target path:** `ai-service/models/item_tower.py`

**Interface:**

```python
ItemTower.forward(
    sbert: Tensor[...,768],
    category_idx: Tensor[...],
    price_idx: Tensor[...],
) -> Tensor[...,64]
```

**Architecture:**

\[
[\,\ldots,768\,]\xrightarrow{\operatorname{Linear}(768,64)}
[\,\ldots,64\,].
\]

Category and price features:

\[
\operatorname{Embedding}(41,16),\qquad
\operatorname{Embedding}(9,8).
\]

Concatenate:

\[
64+16+8=88.
\]

Final item MLP:

\[
\operatorname{Linear}(88,64)
\to\operatorname{ReLU}
\to\operatorname{Linear}(64,64)
\to\operatorname{L2Norm}.
\]

**Optimizations and gotchas:**

- The 768-dimensional SBERT cache is frozen; only the 768→64 projection is trainable.
- Support arbitrary leading dimensions by flattening, encoding once, and restoring the shape.
- Category/price row `0` is unknown.
- Cold products use the same text/category/price path and must not access ID interaction embeddings.

**Implementation checklist:**

- [ ] Implement projection, lookup, concatenation, and MLP.
- [ ] Validate embedding dtype and final dimension.
- [ ] Add cold-item and unknown-feature fixtures.
- [ ] Test batch and grouped-candidate leading dimensions.
- [ ] Ensure all output vectors have norm approximately one.

**Verification:**

```bash
python -m pytest tests/unit/models/test_item_tower.py -q
```

### Task 2.3 — Masked Wide MLP

**Target path:** `ai-service/models/wide_layer.py`

**Interface:**

```python
WideLayer.forward(log_lift: Tensor[...,1]) -> Tensor[...]
```

**Architecture:**

\[
\operatorname{Linear}(1,16)
\to\operatorname{ReLU}
\to\operatorname{Linear}(16,1).
\]

Apply an explicit presence mask so `WideLayer(0)=0` despite layer biases.

**Scale balancing:**

- Zero-initialize the final linear weight and bias so training starts as a Deep-only model.
- Record Wide/Deep logit RMS and gradient norms during training.
- Do not add another sigmoid, temperature, or arbitrary lift multiplier.

**Optimizations and gotchas:**

- Execute the MLP only for nonzero sparse rule values in full-catalog evaluation.
- Reject negative, NaN, or infinite `log_lift`.
- Avoid turning “no rule” into a learned global bias.

**Implementation checklist:**

- [ ] Implement masked dense forward.
- [ ] Implement nonzero-value forward for sparse evaluation.
- [ ] Add initialization and serialization tests.
- [ ] Test exact zero output for missing rules.
- [ ] Test values up to `log1p(822.67)`.

**Verification:**

```bash
python -m pytest tests/unit/models/test_wide_layer.py -q
```

### Task 2.4 — Unified Wide + Deep scorer

**Target path:** `ai-service/models/two_tower_wide_deep.py`

**Interface:**

```python
encode_users(...) -> Tensor[B,64]
encode_items(...) -> Tensor[...,64]
score_candidates(
    user_vectors: Tensor[B,64],
    item_vectors: Tensor[B,C,64],
    log_lift: Tensor[B,C,1],
    use_wide: bool = True,
) -> HybridScores
```

`HybridScores` contains `logits`, and optionally detached `deep_logits` and `wide_logits` for diagnostics.

**Technical specifications:**

\[
S_{\text{deep}}=
\frac{\operatorname{einsum}("bd,bcd\to bc",U,V)}{0.1}.
\]

\[
Z=S_{\text{deep}}+S_{\text{wide}}.
\]

- Output logits `[B,C]`.
- No sigmoid inside the trainable model.
- `use_wide=False` provides the Deep-only ablation without a separate architecture.

**Optimizations and gotchas:**

- Encode each user once per five-candidate training group.
- Precompute item vectors once for full-catalog evaluation.
- Checkpoint configuration and artifact-map checksums alongside weights.
- Reject incompatible user/item dimensionalities before implicit broadcasting.

**Implementation checklist:**

- [ ] Compose the three model modules.
- [ ] Add grouped candidate scoring.
- [ ] Add Deep-only switch and branch diagnostics.
- [ ] Test hand-calculated dot products and temperature scaling.
- [ ] Test serialization and deterministic reload.

**Verification:**

```bash
python -m pytest tests/unit/models/test_two_tower_wide_deep.py -q
python -m pytest tests/integration/test_model_forward_backward.py -q
```

## 4. Sprint 3 — Training and Evaluation Harness

### Task 3.1 — Trainer and checkpoint lifecycle

**Target path:** `ai-service/training/trainer.py`

**Interface:**

```python
Trainer.fit(train_loader, validation_evaluator) -> TrainingResult
Trainer.resume(checkpoint_path) -> None
```

**Technical specifications:**

- `BCEWithLogitsLoss(reduction="none")`.
- Adam: `lr=1e-3`, `weight_decay=1e-5`.
- Maximum 30 epochs.
- Full-catalog validation macro-GAUC.
- Early stopping: patience 4, `min_delta=1e-4`.
- Gradient clipping: global norm 5.
- CUDA AMP enabled by default: BF16 when supported, otherwise FP16 with `GradScaler`.
- Refresh the UNK user row before every validation and checkpoint save.

**Optimizations and gotchas:**

- Call `dataset.set_epoch(epoch)` before each epoch.
- Transfer grouped batches with `non_blocking=True`.
- Persist model, optimizer, scaler, epoch, best metric, RNG states, configuration, and all input checksums.
- Save to a temporary checkpoint and atomically rename.
- Refuse resume if snapshot, mappings, SBERT, or rule checksums differ.
- Log Deep/Wide RMS and gradient norms to detect Wide scale domination.

**Implementation checklist:**

- [ ] Implement train/validation state machine.
- [ ] Implement AMP and deterministic resume.
- [ ] Implement atomic `last.pt` and `best.pt`.
- [ ] Emit JSONL metrics and final training summary.
- [ ] Add NaN/Inf and exploding-gradient guards.
- [ ] Run a 20-step CPU/CUDA smoke training path.

**Verification:**

```bash
python -m training.trainer \
  --snapshot-dir artifacts/data/scaled-v1 \
  --run-dir artifacts/runs/smoke \
  --max-steps 20

python -m pytest tests/integration/test_training_smoke.py -q
python -m pytest tests/integration/test_checkpoint_resume.py -q
```

### Task 3.2 — Full-catalog GPU evaluator

**Target path:** `ai-service/evaluation/full_catalog_eval.py`

**Interface:**

```python
evaluate_full_catalog(model, snapshot, split, k=10) -> EvaluationReport
```

**Technical specifications:**

Precompute:

\[
U\in\mathbb R^{5000\times64},
\qquad
V\in\mathbb R^{5200\times64}.
\]

Score user chunks of 512:

\[
S_{\text{deep}}=\frac{UV^\top}{0.1}.
\]

For each user, use the latest prior positive as the evaluation context. Gather outgoing sparse rule edges, evaluate the Wide MLP only on nonzero values, and scatter-add them to the dense score chunk.

Metrics:

\[
HR@10=\frac1{|Q|}\sum_u
\mathbf1[\operatorname{Top10}_u\cap G_u\ne\varnothing].
\]

\[
DCG@10=\sum_{r=1}^{10}
\frac{\operatorname{rel}_r}{\log_2(r+1)}.
\]

\[
IDCG@10=\sum_{r=1}^{\min(10,|G_u|)}
\frac1{\log_2(r+1)}.
\]

GAUC is the macro mean of exact per-user AUC, omitting and counting users that lack either a positive or negative class.

**Optimizations and gotchas:**

- Use `torch.inference_mode()` and float32 metrics.
- Mask previously seen items except an item that is also a current split positive.
- Use `torch.topk` row-wise; make final result serialization deterministic by product ID.
- Do not densify the Apriori item-item matrix.
- Compare sparse Wide construction against a small dense reference.
- Record peak VRAM, users/sec, and metric-eligible user counts.

**Implementation checklist:**

- [ ] Encode catalog/users once per run.
- [ ] Implement chunked CUDA matmul.
- [ ] Implement sparse Wide scatter.
- [ ] Implement seen-item masking.
- [ ] Implement HR, NDCG, and macro-GAUC.
- [ ] Persist JSON and CSV reports.

**Verification:**

```bash
python -m evaluation.full_catalog_eval \
  --checkpoint artifacts/runs/main/best.pt \
  --snapshot-dir artifacts/data/scaled-v1 \
  --split test

python -m pytest tests/unit/evaluation/test_full_catalog_metrics.py -q
python -m pytest tests/integration/test_sparse_wide_dense_parity.py -q
```

### Task 3.3 — Ten semantic-trap benchmark

**Target paths:**

- `ai-service/evaluation/semantic_traps.py`
- `ai-service/evaluation/fixtures/semantic_traps.json`

The fixture contains all ten anchor-to-target sets, including the alternative targets for traps 2, 5, and 10.

**Protocol:**

- Use UNK user plus default persona `0`.
- Set the trap anchor as the explicit context item.
- Score all 5,200 items.
- Report every target’s raw product ID, rank, score, HR@10, NDCG@10, Deep-only rank, Hybrid rank, and rank delta.
- Validate train-only Apriori count/lift for every trap before model scoring.

**Gotchas:**

- Do not silently collapse multi-target traps to only one target.
- A database rule-quality pass is distinct from a model-ranking pass.
- SBERT-only similarity should remain separately visible to demonstrate the semantic gap.
- Cold-item manifests and trap fixtures must not overlap unless deliberately declared.

**Implementation checklist:**

- [ ] Move trap definitions into one canonical versioned fixture.
- [ ] Validate raw IDs against the product map.
- [ ] Run SBERT-only, Deep-only, and Hybrid comparisons.
- [ ] Produce per-trap and aggregate reports.
- [ ] Release-gate the seeded benchmark on 10/10 valid rules, Hybrid HR@10 of 1.0, and improved median target rank versus Deep-only.

**Verification:**

```bash
python -m evaluation.semantic_traps \
  --checkpoint artifacts/runs/main/best.pt \
  --snapshot-dir artifacts/data/scaled-v1

python -m pytest tests/unit/evaluation/test_semantic_traps.py -q
```

### Task 3.4 — Cold-start zero-shot evaluator

**Target path:** `ai-service/evaluation/cold_start_eval.py`

**Protocol:**

- Validate exactly 250 cold products.
- Assert no cold product occurs in train, validation, train rules, popularity pools, or sampled negatives.
- Require at least one test positive for every evaluated cold product.
- Score against all 5,200 products using normal user vectors and frozen cold-item content features.
- Wide score must be zero for cold candidates because train rules exclude them.
- Report HR@10, NDCG@10, coverage, score finiteness, per-item support, and comparisons with Random and popularity baselines.

**Gotchas:**

- Zero-interaction items without held-out positives support only a “scoreability” check, not HR/NDCG.
- Do not select cold products after observing model scores.
- Missing text/category/price maps to UNK features, not dropped rows.

**Implementation checklist:**

- [ ] Implement isolation assertions.
- [ ] Extract cold test truth.
- [ ] Run full-catalog ranking.
- [ ] Report metric confidence intervals or bootstrap intervals.
- [ ] Require 100% cold-item cache coverage and performance above Random.

**Verification:**

```bash
python -m evaluation.cold_start_eval \
  --checkpoint artifacts/runs/main/best.pt \
  --snapshot-dir artifacts/data/scaled-v1

python -m pytest tests/unit/evaluation/test_cold_start_eval.py -q
```

### Task 3.5 — Seven-way baseline harness

**Target path:** `ai-service/evaluation/baselines.py`

**Required baselines:**

1. **Apriori-only:** context-rule `log1p(lift)`, with deterministic product-ID tie break.
2. **SBERT-only:** cosine between each user’s train-history SBERT centroid and catalog embeddings.
3. **Item-CF:** train-only sparse user-item matrix with plain cosine and normalized weighted-sum scoring.
4. **Deep-only:** independently trained or explicitly Wide-disabled Two-Tower checkpoint.
5. **Proposed Hybrid:** full Wide + Deep model.
6. **Noisy 10% Hybrid:** unchanged checkpoint; deterministically replace persona with a different cluster for exactly 10% of test users.
7. **Random:** stateless seeded uniform score keyed by `(seed,user,item)`.

**Optimizations and gotchas:**

- All methods use the same product map, split, ground truth, masks, metric implementation, and catalog.
- Fit every baseline using train-only data.
- Random is not an untrained neural network.
- Require Random GAUC in `0.50±0.02`; the stale recorded value `0.6923` is not an acceptable sanity result.
- Record latency separately because CPU and GPU baselines use different execution paths.

**Implementation checklist:**

- [ ] Implement a common scorer interface.
- [ ] Reuse `full_catalog_eval` for metrics.
- [ ] Add deterministic noisy-persona selection.
- [ ] Produce a single CSV/JSON comparison table.
- [ ] Include model/data/checkpoint hashes in the report.

**Verification:**

```bash
python -m evaluation.baselines \
  --snapshot-dir artifacts/data/scaled-v1 \
  --hybrid-checkpoint artifacts/runs/main/best.pt \
  --deep-checkpoint artifacts/runs/deep-only/best.pt

python -m pytest tests/unit/evaluation/test_baselines.py -q
```

## 5. Sprint 4 — ONNX Export and FastAPI Serving

### Task 4.1 — ONNX export, optimization, and parity

**Target path:** `ai-service/export/onnx_exporter.py`

**Exported graphs:**

1. `item_encoder.onnx`

```text
Inputs:
  sbert          [N,768] float32
  category_idx   [N]     int64
  price_idx      [N]     int64
Output:
  item_vectors   [N,64]  float32
```

2. `ranker.onnx`

```text
Inputs:
  user_idx          [B]       int64
  persona_idx       [B]       int64
  candidate_vectors [B,C,64]  float32
  log_lift          [B,C,1]   float32
Output:
  logits            [B,C]     float32
```

- Use ONNX opset 17 and dynamic axes for `N`, `B`, and `C`.
- Refresh the UNK user row before export.
- Run `onnx.checker`.
- Enable exporter constant folding and ONNX Runtime `ORT_ENABLE_ALL` graph optimization.
- Generate the serving item-vector cache through the exported item encoder.

**Serving artifact:**

```text
artifacts/model/<model_version>/
  ranker.onnx
  item_encoder.onnx
  item_vectors.npy
  product_ids.npy
  user_map.json
  user_personas.npy
  apriori_rules.npz
  serving_manifest.json
```

**Parity and latency gates:**

- PyTorch versus ONNX maximum absolute logit error `<=1e-5`.
- Test known user, unknown user, warm item, cold item, rule, and no-rule paths.
- Benchmark one user with 100 candidates:
  - 50 warmups;
  - 1,000 measured `session.run` calls;
  - target-hardware warmed p95 `<1.0 ms`;
  - report p50/p95/p99.
- HTTP latency is measured separately.

**Implementation checklist:**

- [ ] Load and validate the best checkpoint.
- [ ] Export both graphs.
- [ ] Run graph validation and ORT parity.
- [ ] Produce the item cache and manifest checksums.
- [ ] Fail export on incompatible snapshot/checkpoint metadata.
- [ ] Emit machine-readable benchmark results.

**Verification:**

```bash
python -m export.onnx_exporter \
  --checkpoint artifacts/runs/main/best.pt \
  --snapshot-dir artifacts/data/scaled-v1 \
  --output-dir artifacts/model/two_tower_v1 \
  --benchmark

python -m pytest tests/integration/test_onnx_parity.py -q
```

### Task 4.2 — Pydantic HTTP contracts

**Target path:** `ai-service/service/schemas.py`

**Request:**

```json
{
  "store_id": 1,
  "user_id": 42,
  "persona_cluster": 2,
  "candidate_product_ids": [101, 102, 103],
  "context_product_id": 101
}
```

Rules:

- `store_id` defaults to `1` for backward compatibility.
- `user_id` and `persona_cluster` are nullable.
- Candidate list contains `1..256` entries.
- Duplicate candidates are deduplicated in first-occurrence order.
- Raw product IDs remain external IDs.
- Invalid non-null persona values outside `0..7` return 422.

**Response:**

```json
{
  "rankings": [
    {"product_id": 103, "ai_score": 0.8954}
  ],
  "inference_ms": 0.845,
  "model_version": "two_tower_v1"
}
```

- Return every unique requested candidate exactly once.
- Sort by `(ai_score descending, product_id ascending)`.
- `ai_score=σ(logit)` preserves compatibility but is documented as a ranking score, not a calibrated purchase probability.

**Health response:**

```json
{
  "status": "ok",
  "service": "ai-service",
  "model_version": "two_tower_v1",
  "cached_products": 5200,
  "onnx_ready": true
}
```

**Gotchas:**

- Unknown users are valid and map to UNK.
- Unknown candidate products are not valid; fail the complete request rather than return partial rankings.
- A cached cold product is valid and receives a Deep-only score.
- A missing/unknown context returns a validation error; a known context with no rule produces zero Wide score.

**Implementation checklist:**

- [ ] Define strict request/response/health models.
- [ ] Add candidate bounds and deduplication.
- [ ] Preserve existing field names.
- [ ] Add OpenAPI examples and error schemas.
- [ ] Add serialization and validation tests.

**Verification:**

```bash
python -m pytest tests/unit/service/test_schemas.py -q
```

### Task 4.3 — FastAPI inference module

**Target path:** `ai-service/service/api.py`

**Endpoints:**

- `GET /health`
- `POST /recommend`
- `GET /metrics`

**Startup lifecycle:**

- Load `serving_manifest.json`.
- Verify every checksum before accepting traffic.
- Load one CPU ONNX Runtime session with full graph optimization.
- Memory-map `[5200,64]` item vectors and load raw-ID maps and compact rule CSR arrays.
- Validate exactly 5,200 cached products.
- Return 503 from readiness until initialization succeeds.

**Request flow:**

1. Validate `store_id` against the single-store artifact.
2. Map raw user ID to internal index; unknown maps to `0`.
3. Use a supplied valid persona or artifact persona; unknown users default to cluster `0`.
4. Map candidate IDs and gather `[1,C,64]` item vectors.
5. If context exists, gather corresponding rule values; otherwise use all-zero `[1,C,1]`.
6. Run `ranker.onnx`.
7. Apply sigmoid, stable ordering, and response serialization.

**Optimizations and gotchas:**

- Serving performs no PostgreSQL queries and loads no 768-dimensional SBERT cache.
- Preallocate/reuse NumPy buffers where safe.
- Use one Uvicorn process to avoid duplicating caches under the 1 GB limit; ONNX Runtime sessions are thread-safe.
- Any artifact corruption, missing candidate, ORT failure, or cardinality mismatch returns non-2xx so the existing circuit breaker activates.
- Expose Prometheus counters and histograms for request totals, error type, candidate count, ORT latency, total latency, and model version.
- Do not log raw user IDs or full candidate payloads.
- Target local-container `/recommend` p95 `<20 ms`, well below the Chatbot’s 300 ms timeout.

**Implementation checklist:**

- [ ] Implement lifespan-based initialization.
- [ ] Implement artifact checksum and version validation.
- [ ] Implement vectorized candidate/rule gathering.
- [ ] Add health/readiness and Prometheus metrics.
- [ ] Add structured request IDs and safe logging.
- [ ] Test concurrent requests and failure propagation.

**Verification:**

```bash
python -m pytest tests/integration/test_api.py -q

uvicorn service.api:app --host 0.0.0.0 --port 8000

curl --fail http://localhost:8000/health
curl --fail -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"store_id":1,"user_id":42,"persona_cluster":2,"candidate_product_ids":[1001,1002,1003],"context_product_id":1001}'
```

### Task 4.4 — Production container

**Target paths:**

- `ai-service/Dockerfile`
- `ai-service/.dockerignore`
- `ai-service/requirements-serve.txt`

**Technical specifications:**

- Base: `python:3.11-slim`.
- Runtime installs only serving dependencies; exclude PyTorch, Transformers, SentenceTransformers, Pandas, and training tools.
- Run as a non-root user.
- Copy `service/`, `config.py`, and the promoted model artifact.
- Set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`.
- Expose port 8000.
- Use one Uvicorn worker.
- Add `/health` Docker health check with 15-second start period.

**Optimizations and gotchas:**

- Do not download models or regenerate vectors during container startup.
- Artifact promotion occurs before image build.
- Include model version and source revision as OCI labels.
- Keep the serving image independent from training CUDA libraries.
- Preserve the existing 1 GB Compose memory limit.

**Implementation checklist:**

- [ ] Build a minimal deterministic image.
- [ ] Add non-root ownership and read-only artifacts.
- [ ] Validate health and recommendation calls inside the container.
- [ ] Record image size and cold-start time.
- [ ] Add a startup failure test for corrupt manifests.

**Verification:**

```bash
docker build -t posmart-ai-service:test ai-service
docker run --rm -p 8000:8000 posmart-ai-service:test

docker compose -f backend/docker-compose.yml config --quiet
docker compose -f backend/docker-compose.yml build ai-service
docker compose -f backend/docker-compose.yml up -d ai-service chatbot
docker compose -f backend/docker-compose.yml ps ai-service chatbot
```

### Task 4.5 — Chatbot, Compose, and CI/CD integration

**Companion targets outside `ai-service/`:**

- `backend/services/chatbot/src/services/ai.client.js`
- `backend/services/chatbot/src/services/hybrid.service.js`
- `backend/docker-compose.yml`
- `backend/docker-compose.prod.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-backend.yml`

**Required changes:**

- Preserve null/zero unknown users; remove coercion to user `1`.
- Pass `store_id`.
- Pass persona only when an explicit valid `0..7` value exists; otherwise let `ai-service` use its artifact mapping.
- Keep the 300 ms timeout, three-failure threshold, and 30-second recovery probe.
- Contract-test response cardinality, sort order, non-2xx fallback, timeout, and circuit transitions.
- Preserve the existing user WIP Compose additions and validate them rather than replacing unrelated changes.
- Add `ai-service/**` to CI/deployment path filters.
- Add Python 3.11 lint, type-check, and pytest jobs.
- Add `ai-service` to the GHCR build matrix with build context `./ai-service`.
- Keep AI service internal; do not expose a new Nginx public route.

**Verification:**

```bash
cd backend
npm run test:unit --workspace=@posmart/chatbot-service
npm run test:integration --workspace=@posmart/chatbot-service

cd ..
docker compose -f backend/docker-compose.yml config --quiet
docker compose -f backend/docker-compose.prod.yml config --quiet
```

## 6. Release Acceptance and Rollout

### Mandatory acceptance gates

- Data:
  - Named snapshot has 823,371 valid timestamped interactions.
  - Exactly 5,000 mapped users, 5,200 products, 40 mapped leaves, and 250 cold items.
  - Strict temporal inequalities pass.
  - No cold item appears in train, validation, rules, popularity, or negative pools.
  - All artifacts and sources have recorded checksums.
- Sampling:
  - Every positive has exactly two popularity and two uniform negatives.
  - No false-negative collision with train positives.
  - Same seed/epoch reproduces the same negatives across workers.
- Model:
  - All tower shapes and L2 norms pass.
  - `WideLayer(0)=0`.
  - Deep logits remain bounded by normalized dot product and temperature.
  - Sparse and dense reference scores agree.
- Evaluation:
  - HR@10, NDCG@10, and macro-GAUC pass hand-calculated fixtures.
  - Random GAUC lies in `0.50±0.02`.
  - Ten semantic traps and 250 cold items are all reported.
  - Hybrid, Deep-only, and seven-way baseline reports share one protocol.
- Export/serving:
  - PyTorch/ONNX maximum absolute error `<=1e-5`.
  - Warm ORT p95 for 100 candidates `<1 ms` on declared target hardware.
  - Local-container `/recommend` p95 `<20 ms`.
  - Unknown-user, cold-item, no-rule, missing-artifact, and malformed-request paths pass.
  - `/health` becomes ready only after complete cache initialization.

### Rollout

1. Promote an immutable snapshot and `best.pt` only after all offline gates pass.
2. Export and checksum the ONNX serving bundle.
3. Build the versioned container and run contract/load tests.
4. Deploy behind the existing Chatbot circuit breaker.
5. Monitor ORT p95/p99, HTTP p95, error rate, circuit openings, cache cardinality, and model version.
6. Roll back by restoring the previous image/artifact pair; serving performs no database migration or online model mutation.

### Explicit assumptions

- V1 is single-store and pinned to `store_id=1`.
- Candidate generation and stock filtering remain the Chatbot’s responsibility.
- The catalog is treated as static for this benchmark because product/category history is incomplete.
- The category requirement is corrected to the repository’s actual 40 leaves.
- Persona fallback is cluster `0`, resolving the 0/1 majority tie deterministically.
- Current all-time `co_purchase_stats` is diagnostic only; train-cutoff rules are authoritative.
- The implementation does not claim zero temporal leakage or cold-start HR/NDCG until the timestamped event and cold-ground-truth entry gate is satisfied.
