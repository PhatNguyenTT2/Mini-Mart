# Detailed Source-Level Remediation Plan cho `ai-service`

## 1. Mục tiêu, quyết định đã khóa và hiệu chỉnh audit sơ bộ

Kế hoạch chính thức sẽ được tạo tại:

`master-plan/ai-service-remediation-plan.md`

Phạm vi gồm toàn bộ `ai-service/` và các seam tích hợp bắt buộc ở chatbot, Docker Compose, CI và seed/data contract. Python codebase được chuyển sang layout chuẩn `src/ai_service/`; artifact/checkpoint hiện tại thuộc schema v1, không được xem là tương thích với model v2 và phải retrain/re-export.

Ground Truth được khóa như sau:

- Training signal: cả `view` và `order/purchase` là positive; `sample_weight=0.5` cho view, `1.0` cho purchase.
- Validation target:

\[
G_u^{val}=Purchase_u^{val}\setminus Interacted_u^{train}
\]

- Test target:

\[
G_u^{test}=Purchase_u^{test}\setminus
(Interacted_u^{train}\cup Interacted_u^{val})
\]

- Masking phải dùng mọi historical interaction, gồm cả view và purchase.
- Cold invariant:

\[
C\cap Train=C\cap Val=C\cap Rules=C\cap NegativePool=\varnothing
\]

và mỗi cold SKU phải có ít nhất một purchase positive trong Test.

Các patch sơ bộ trong `audit_report.md` không được áp dụng trực tiếp:

- Không đổi `context_idx > 0` thành `>= 0`; cách đó làm “no context” bị hiểu thành item index 0. Fix đúng là `context_item_idx=-1` kèm `context_present: bool`.
- Không thay fabricated GAUC bằng `train_loss`; hai đại lượng khác ngữ nghĩa. `Trainer.fit()` phải bắt buộc nhận evaluator thật.
- Không đơn thuần xóa auto-load `rule_store`; phải dùng `ModelVariant`/`RuleMode` tường minh.
- Không tạo FastAPI endpoint trả score giả `0.95`; API chỉ ready khi model bundle thật đã được kiểm tra checksum và load thành công.
- Random GAUC gần 0.5 không được dùng để tuyên bố “zero leakage”.
- Maturity data trong health score hiện tại phải đánh giá lại vì PostgreSQL ingestion có query sai và silent synthetic fallback.

## 2. Kiến trúc đích và các interface chính

### 2.1 Chuẩn hóa package

Chuyển mã nguồn sang:

```text
ai-service/
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── .dockerignore
├── src/ai_service/
│   ├── config.py
│   ├── contracts.py
│   ├── errors.py
│   ├── data/
│   │   ├── sources.py
│   │   ├── snapshot.py
│   │   ├── features.py
│   │   ├── rules.py
│   │   └── dataset.py
│   ├── models/
│   ├── training/
│   │   ├── trainer.py
│   │   └── pipeline.py
│   ├── evaluation/
│   │   ├── metrics.py
│   │   ├── full_catalog.py
│   │   ├── baselines.py
│   │   ├── semantic_traps.py
│   │   └── cold_start.py
│   ├── export/
│   │   ├── onnx.py
│   │   └── bundle.py
│   ├── serving/
│   │   ├── schemas.py
│   │   ├── runtime.py
│   │   └── app.py
│   └── reporting.py
└── tests/
```

Không giữ compatibility wrapper ở các module top-level cũ. Sau khi import được chuyển hoàn tất, xóa implementation cũ để tránh hai nguồn sự thật.

Chuẩn mã nguồn:

- Import tuyệt đối `from ai_service...`.
- Python 3.11, `uv.lock` là dependency lock duy nhất.
- Ruff format/lint, mypy typed public interfaces, pytest coverage tối thiểu 85%.
- Không `print()` trong module; dùng structured logging.
- Không broad `except Exception` để đổi sang synthetic/mock.
- Không I/O hoặc tạo thư mục trong `get_settings()`.
- Không hardcode `5,200`, `5,000`, `250`, `13,046`, `0.42` trong report/runtime.
- Secret DSN dùng `SecretStr` và không xuất hiện trong log.

### 2.2 Deep modules và seam

```python
class DatasetSource(Protocol):
    def load(self, store_id: int) -> RawDataset: ...

class SnapshotBuilder:
    def build(
        self,
        source: DatasetSource,
        split_policy: TemporalSplitPolicy,
        cold_partition: ColdPartition,
        output_dir: Path,
    ) -> Snapshot: ...

class ValidationEvaluator(Protocol):
    def evaluate(self, model: HybridTwoTowerModel) -> EvaluationReport: ...

class FullCatalogEvaluator:
    def evaluate(
        self,
        model: HybridTwoTowerModel,
        split: SplitName,
        variant: ModelVariant,
    ) -> EvaluationReport: ...

class RecommenderRuntime:
    def rank(self, request: RankRequest) -> RankResponse: ...
```

`DatasetSource` có hai adapter thật sự:

- `PostgresDatasetSource`: production, fail-closed.
- `SyntheticDatasetSource`: test/benchmark khi được chọn rõ bằng CLI.

`EmbeddingProvider` có:

- `SentenceTransformerProvider`: production, model revision được pin.
- `DeterministicFakeEmbedder`: tests; manifest bắt buộc ghi `source_kind="mock"`.

Các contract trung tâm trong `contracts.py`:

- `SplitName = TRAIN | VAL | TEST`.
- `ModelVariant = HYBRID | DEEP_ONLY | WIDE_ONLY | SBERT_CENTROID | ITEM_CF | NOISY_HYBRID | RANDOM`.
- `EmbeddingSource = REAL | MOCK`.
- `RelevancePolicy`.
- `SnapshotManifestV2`, `EmbeddingManifestV2`, `RuleManifestV2`, `RunManifestV2`, `ModelBundleManifestV2`.
- `ContextRef(item_idx: int, present: bool)` hoặc tensor tương đương `item_idx=-1`, `present=False`.

## 3. Các wave triển khai ở mức mã nguồn

### Wave 0 — Regression harness và package migration

Target hiện tại:

- `ai-service/pyproject.toml`
- Toàn bộ import trong `ai-service/*.py` và tests.
- `.github/workflows/ci.yml`

Thực hiện:

- Thêm các regression test ban đầu để tái hiện từng lỗi trước khi sửa:

  - `test_missing_context_is_not_product_zero`.
  - `test_negative_samples_are_unique_and_not_known_positives`.
  - `test_trainer_rejects_missing_validation_evaluator`.
  - `test_real_embedding_failure_does_not_fallback_to_mock`.
  - `test_empty_cold_ground_truth_is_invalid`.
  - `test_deep_only_never_resolves_rule_artifact`.
  - `test_pipeline_report_contains_measured_values_only`.
  - `test_postgres_queries_match_schema`.
  - `test_api_request_requires_store_id`.

- Di chuyển code cơ học sang `src/ai_service` trước, không đổi hành vi trong cùng commit.
- Cấu hình `uv`, Ruff, mypy, pytest-cov và console entrypoint:

```toml
[project.scripts]
ai-pipeline = "ai_service.training.pipeline:main"
ai-service = "ai_service.serving.app:run"
```

- Bổ sung job CI cho `ai-service/**`; workflow hiện tại không theo dõi thư mục này.
- Sau khi tests chạy qua interface mới, xóa tests cũ chỉ kiểm tra implementation nông hoặc “không crash”.

Acceptance:

```powershell
uv sync --frozen --extra dev
uv run python -c "import ai_service"
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src
```

### Wave 1 — PostgreSQL ingestion, temporal split và cold contract

Target:

- Legacy `data/ingestion.py:199-284,287-415`.
- Mới `src/ai_service/data/sources.py`, `snapshot.py`, `contracts.py`.
- `backend/services/chatbot/src/db/init.sql`.
- Các seed v2 liên quan.

Sửa ingestion:

- Catalog query dùng `p.vendor`, không dùng `p.vendor_name`; join leaf/root category đúng hierarchy.
- Order query dùng `o.order_date`, thêm `o.store_id=$1`, `status='delivered'`, `payment_status='paid'`.
- Mỗi DB connection chạy transaction read-only; bỏ `SET default_transaction_read_only=off`.
- Dùng cursor/chunk thay vì `fetchall()` cho 823k events.
- Không fallback synthetic khi PostgreSQL query lỗi. `--source postgres` phải raise typed `SourceReadError`; `--source synthetic` mới tạo mock.
- Snapshot manifest ghi `source_kind`, query fingerprint, extraction window, row counts trước split, DB snapshot metadata, store ID và mọi checksum.
- Mapping validation phải fail nếu event chứa user/product không tồn tại.

Temporal split:

- Sort theo `(event_ts, event_id)`.
- Chọn cutoff trên nhóm timestamp, không chia cùng timestamp qua hai split.
- Bất biến bắt buộc:

```python
train.event_ts.max() < val.event_ts.min()
val.event_ts.max() < test.event_ts.min()
```

- Không “sửa leakage” bằng cách xóa cold rows khỏi train/val. Nếu cold xuất hiện trước test cutoff, snapshot build phải fail.
- Ground-truth builder tạo novel purchase targets theo chính sách đã khóa; ghi số users bị loại vì không có novel purchase.

Cold partition:

- Thêm bảng versioned `ml_benchmark_item_partition_v1` hoặc migration tương đương gồm `store_id`, `product_id`, `partition`, `seed_version`.
- `seed-ml-events-v2.js` sinh purchase event xác định cho đủ 250 cold SKUs sau test cutoff.
- `mock-orders-v2.js` không cho cold SKU vào train-period delivered baskets.
- Seed dùng seeded PRNG, normalized numeric BIGINT handling và staging transaction; không `DROP ... CASCADE`.

Acceptance:

- Không overlap event ID giữa splits.
- Không timestamp equality qua split.
- 250/250 cold SKUs có test purchase.
- Cold không xuất hiện trong train, val, rules hoặc negative pool.
- Tổng row count trong manifest khớp source; không có sự kiện bị silently dropped.
- Chạy hai lần cùng seed tạo checksum giống nhau.

### Wave 2 — Feature artifacts, Apriori và dataset sampling

Target:

- Legacy `data/precompute_sbert.py`, `apriori_rules.py`, `dataset.py`.
- Mới `data/features.py`, `rules.py`, `dataset.py`.

SBERT:

- Production pipeline bắt buộc `EmbeddingSource.REAL`.
- Pin cả model name và revision.
- Mọi lỗi download/load/encode phải fail; không tạo random vectors.
- Manifest ghi `source_kind`, model revision, input text hash, product-map hash, dtype, shape, normalization và file checksum.
- Dùng `np.load(..., mmap_mode="r")` khi training/evaluation.

Apriori:

- Chỉ dùng train-period, delivered/paid baskets của đúng store.
- Dùng một basket universe nhất quán:

\[
support=c_{AB}/N,\quad confidence=c_{AB}/c_A,\quad
lift=c_{AB}N/(c_Ac_B)
\]

- `min_count >= 3`, cold items bị reject trước khi lưu.
- Phân biệt rõ `num_undirected_pairs` và `num_directed_rules`.
- Lưu CSR artifact và `RuleManifestV2`.
- Chuẩn hóa Wide input:

\[
x_w=\operatorname{clip}\left(
\frac{\log(1+lift)}{q_{0.99}^{train}},0,1
\right)
\]

- Chuyển CSR sang `torch.sparse_csr_tensor`. Full-catalog Wide scoring áp dụng MLP lên sparse values rồi dùng sparse matrix multiplication cho batch contexts; bỏ Python loop 5,200 lookups/user.

Dataset:

- Product indices vẫn là `0..N-1`; no-context dùng `-1` và mask riêng.
- Context Wide là purchase gần nhất có timestamp nhỏ hơn nghiêm ngặt; view không cập nhật Apriori context, các events cùng timestamp không nhìn thấy nhau.
- Dynamic negative sampling dùng:

```python
rng = np.random.default_rng(
    np.random.SeedSequence([base_seed, epoch, sample_index])
)
```

- Với ratio \(R\):

```python
hard_count = R // 2
uniform_count = R - hard_count
```

- Sample không replacement và loại:

  - target positive;
  - mọi train positive của user;
  - duplicates trong candidate group;
  - toàn bộ cold partition.

- Nếu pool không đủ, raise `NegativeSamplingError`, không silently duplicate.
- Dùng `interaction_weight` thật làm `sample_weight`.
- Candidate tensors có shape `[B, 1+R]`; không hardcode `[B,5]`.
- DataLoader nhận seeded `torch.Generator`, worker seed, `pin_memory` theo device.

### Wave 3 — Model, numerical stability và training lifecycle

Target:

- `models/user_tower.py`, `item_tower.py`, `wide_layer.py`, `two_tower_wide_deep.py`.
- `training/trainer.py`, `training/pipeline.py`.

Model contracts:

- User output `[B,64]`.
- Item output `[...,64]` từ SBERT `[...,768]`.
- Deep logits:

\[
S_{deep}=\frac{UV^\top}{\tau}
\]

- Persona `None` map vào dedicated UNK row 8; không map sang persona 0.
- Validate `tau >= 10^{-3}` để giảm FP16 overflow.
- Validate shape/dtype/finite tại data/runtime interface; model không silently clamp NaN/Inf.
- Wide zero mask dùng explicit `rule_present`; NaN lift phải bị reject trước MLP.
- Theo dõi `deep_rms`, `wide_rms`, tỷ lệ hai nhánh và gradient norms. Wide normalization dùng train manifest thay vì hardcoded scale.

Trainer:

- `ValidationEvaluator` là tham số bắt buộc.
- Xóa hoàn toàn công thức GAUC giả.
- Validation checkpoint selection dùng full-catalog purchase-only GAUC.
- `val_loss` và `val_gauc` là hai fields riêng, không thay thế lẫn nhau.
- Missing snapshot/features hoặc sai batch type phải raise typed error, không `continue`.
- Không chuyển candidate IDs CPU → GPU → CPU; giữ IDs CPU để index memmap, rồi chuyển feature tensor một lần.
- Missing SBERT artifact là fatal.
- Kiểm tra `torch.isfinite(loss/logits/grad_norm)` trước optimizer step.
- Average loss theo số sample, không theo số batch.
- Atomic checkpoint dùng unique temporary file và `os.replace`.
- Checkpoint lưu Python/NumPy/Torch RNG, config hash, snapshot/embedding/rule hashes và model schema version.
- Sau early stopping, reload `best.pt` vào model trước evaluation/export.

Pipeline:

- Gọi `set_seed()` ngay khi khởi động.
- CLI dùng `--source postgres|synthetic`, `--embedding-source real|mock`.
- Production defaults: `postgres` và `real`.
- `--export-onnx/--no-export-onnx` dùng boolean optional action.
- Không bắt broad exception để rebuild corrupted snapshot/rules.
- Tạo immutable `run_id`; không ghi đè `artifacts/runs/main`.

### Wave 4 — Evaluation, baselines, semantic traps và reports

Target:

- Toàn bộ `evaluation/`.
- `reports/generate_report.py`.

Full-catalog evaluator:

- `split` là enum, typo phải fail.
- Variant tường minh; evaluator không tự load artifact.
- Validation mask mọi train view/order.
- Test mask mọi train+val view/order.
- Ground truth chỉ gồm novel purchases.
- Báo `num_total_users`, `num_eligible_users`, `num_users_without_novel_purchase`.
- Stable top-K: score giảm dần, product ID tăng dần khi tie.
- GAUC dùng rank-based \(O(N\log N)\), không cấp phát ma trận pairwise \(P\times N\).
- Kiểm tra `1 <= k <= num_items`.
- GPU latency dùng `perf_counter_ns()` và `torch.cuda.synchronize()`; tách model kernel, feature/rule scoring và total evaluation time.

Bảy baselines phải có đủ:

1. Apriori Wide-only.
2. SBERT user centroid.
3. Item-Item CF.
4. Deep-only Two-Tower.
5. Hybrid.
6. Noisy 10% Hybrid.
7. Stateless seeded Random.

Random scores phải phụ thuộc xác định vào `(seed,user_id,item_id)`; chạy nhiều seeds và báo confidence interval quanh 0.5.

Semantic traps:

- Deep score là cosine giữa anchor item embedding và catalog embeddings, không dùng một UNK-user vector chung.
- Missing anchor/target ID phải fail fixture validation, không map về item 0.
- Item internal index 0 là anchor hợp lệ.
- Trap chỉ `PASS` khi ít nhất một approved target vào top 10; rank tăng một bậc ở vị trí hàng nghìn không được tính “resolved”.
- Báo Deep, Wide-only và Hybrid ranks cho mọi alternative target.

Cold-start:

- Không có cold purchase ground truth là invalid benchmark, không trả coverage `1.0`.
- Tách:

  - `ground_truth_coverage = cold SKUs có test purchase / 250`;
  - `recommendation_coverage = cold SKUs xuất hiện trong top-K / 250`.

- Mask train+val histories và assert cold rules bằng zero.

Reporting:

- Mọi số liệu lấy từ manifests/results.
- Không hardcode catalog/rule count, leakage, parity hoặc latency.
- Report không được sinh nếu provenance hoặc benchmark validity gate fail.
- Ghi snapshot, checkpoint, embedding, rules, ONNX hashes và hardware/runtime metadata.
- Sau khi revalidate, cập nhật lại `audit_report.md`; không giữ health score 54 nếu evidence mới không hỗ trợ.

### Wave 5 — ONNX bundle và FastAPI serving

Target:

- `export/onnx.py`, `export/bundle.py`.
- Mới `serving/schemas.py`, `runtime.py`, `app.py`.
- `Dockerfile`, `.dockerignore`.

Export:

- Load best checkpoint trên CPU trước export; không dùng in-memory final epoch.
- Dummy tensors cùng device với model.
- Export bốn graphs với opset 18 và dynamic batch/candidate axes.
- Parity dùng checkpoint thật, nhiều shapes gồm `B=1`, `C=1`, `C=256`; yêu cầu:

\[
\max |y_{torch}-y_{onnx}| \le 10^{-5}
\]

- Bundle gồm graphs, raw↔internal mappings, cached item vectors `[N,64]`, CSR rules, normalization metadata và `ModelBundleManifestV2`.
- Bundle verification kiểm tra mọi checksum trước khi publish.

Serving interface:

```python
class RecommendRequest(BaseModel):
    store_id: int
    user_id: int | None
    persona_cluster: int | None
    candidate_product_ids: list[int]  # 1..256, unique
    context_product_id: int | None

class ProductRanking(BaseModel):
    product_id: int
    rank: int
    ai_score: float

class RecommendResponse(BaseModel):
    rankings: list[ProductRanking]
    inference_ms: float
    model_version: str
    bundle_id: str
```

`RecommenderRuntime`:

- Load toàn bộ immutable bundle một lần trong FastAPI lifespan.
- Không truy vấn DB trên request path.
- Validate store ID khớp bundle.
- Unknown user map 0; missing persona map UNK persona 8.
- Unknown/duplicate candidate IDs trả 422.
- Response phải chứa đúng toàn bộ candidate set; không default score giả.
- Context null dùng zero Wide contribution; product index 0 vẫn hợp lệ.
- Stable sort theo `(-score, product_id)`.
- ORT session cấu hình provider/thread rõ ràng, immutable arrays và giới hạn request 256.

Endpoints:

- `/health/live`
- `/health/ready`
- `/health` làm alias của readiness để tương thích chatbot.
- `/recommend`
- `/metrics`

Docker:

- Python 3.11 slim, non-root user, read-only model mount, no compiler trong runtime stage.
- `MODEL_BUNDLE_PATH=/models/current`.
- Container không ready nếu bundle thiếu/sai checksum.
- Giữ memory dưới Compose limit 1 GB.
- Benchmark riêng kernel p50/p95/p99 và HTTP end-to-end; chỉ kernel p95 mới dùng gate `<1 ms`, không đánh tráo với HTTP latency.

### Wave 6 — Chatbot, Compose, CI và rollout

Chatbot integration:

- Đổi `AIClient.scoreProducts` sang object parameter để tránh positional drift:

```javascript
scoreProducts({
  storeId,
  userId,
  personaCluster,
  candidateProductIds,
  contextProductId
})
```

- Gửi `store_id`; không đổi unknown user thành user 1.
- Dùng nullish semantics cho persona/context, không dùng `||`.
- Validate response có đủ candidates, unique IDs và finite scores; sai contract kích hoạt fallback.
- `HybridRecommendationService` dùng `options.contextProductId`; không tự lấy candidate đầu tiên làm context.
- Không chèn score mặc định `0.5` cho candidate bị thiếu.
- Thêm Jest tests cho timeout, 422/503, malformed response, store propagation và circuit-breaker recovery.

Compose/CI:

- Bật `ai-service` trong development Compose.
- Mount `${AI_MODEL_BUNDLE_PATH}` read-only và khai báo biến bắt buộc trong production Compose.
- Chatbot chỉ depend on health-ready service; circuit breaker vẫn là rollback path.
- CI chạy unit, type, lint, artifact contract tests, ONNX parity và Docker smoke test.
- Sub-millisecond benchmark chạy trên runner/hardware cố định, không gate trên shared GitHub runner.

Rollout:

1. Đánh dấu artifacts v1 là `legacy-invalid`; không xóa để giữ khả năng điều tra.
2. Build lại snapshot v2 từ PostgreSQL thật và cold partition versioned.
3. Train model v2, reload best checkpoint, chạy đủ evaluation gates.
4. Export bundle v2 và kiểm tra checksum/parity.
5. Deploy service với AI fast path disabled; xác nhận readiness và shadow comparison.
6. Bật fast path thủ công sau khi response completeness, latency và fallback đạt.
7. Rollback bằng cách disable AI client hoặc mount lại bundle version trước; không cần rollback database.

## 4. Test matrix và acceptance commands

Bắt buộc có test qua interface của các deep module, không test xuyên implementation riêng lẻ.

```powershell
cd E:\UIT\cv\backend\ai-service
uv sync --frozen --extra dev
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src
uv run pytest -m "not integration and not benchmark" --cov=ai_service --cov-fail-under=85
uv run pytest -m integration
uv run pytest -m benchmark
```

```powershell
cd E:\UIT\cv\backend\backend
npm run test:chatbot
docker compose config
```

```powershell
docker build -t posmart-ai-service:test E:\UIT\cv\backend\ai-service
docker run --rm --read-only `
  -v "${env:AI_MODEL_BUNDLE_PATH}:/models/current:ro" `
  -p 8000:8000 posmart-ai-service:test
```

Release gates:

- Không còn fabricated/mock metric trong production path.
- Snapshot provenance là PostgreSQL và strict temporal assertions đạt.
- Purchase-only novel ground truth và double-history masking được test.
- Cold invariant đạt đủ 250/250.
- Negative sampler không false-negative/duplicate qua tối thiểu 10,000 samples.
- Bảy baseline chạy qua các variant tách biệt.
- Real SBERT artifact và best checkpoint hashes xuất hiện trong report/bundle.
- PyTorch–ONNX parity \(\le10^{-5}\).
- ONNX kernel p95 `<1 ms` trên hardware được ghi lại; API p95 có SLA riêng.
- `/recommend` khớp contract chatbot, multi-tenant `store_id` bắt buộc.
- Docker readiness, memory limit, circuit-breaker fallback và rollback đều được kiểm chứng.

## 5. Giả định và giới hạn

- Python package v2 và model bundle v2 là breaking change; không hỗ trợ checkpoint v1.
- Training dùng cả view/order với sample weights; validation/test chỉ novel purchases.
- Mọi train/validation interaction đều được mask tại test, kể cả views.
- Không tự chạy seed hoặc migration trên database production trong quá trình sửa code; chỉ tạo mã migration/script và test chúng trên môi trường kiểm thử.
- Model bundle được cung cấp qua read-only mount; image không chứa secrets hoặc kết nối DB.
- Các artifact hiện tại không được dùng làm production evidence cho đến khi lineage v2 được tái tạo đầy đủ.
