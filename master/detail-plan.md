# Detail plan codebase R1–R4: sửa Wide signal và mở production training

## Trạng thái thực thi — 2026-08-11

```text
R1 source/contracts/tests:                 PASS
R2 seed code + database seed + readiness:  PASS
R3 source/tests:                           PASS
R3 diagnostic execution: COMPLETED — SELECTED HYBRID VAL FAILED
R4 lineage/audit/probes/ai-service/CUDA:    PASS
Backend monorepo legacy Jest gate:          FAIL_OUTSIDE_R2_SCOPE
R4 documentation/final source freeze:      BLOCKED_BY_MODEL_QUALITY
PRODUCTION TRAINING:                       BLOCKED_UNTIL_REMEDIATION
HYBRID VICTORY:                            NOT ESTABLISHED
```

R3 executed on frozen commit `15860af0d5002297baf38e0df20f761332897700`.
The immutable Deep ablation receipt is
`12dcf8cbd6fe6f4bbcaf1a038e77d280484f94e34eca5db7d5544ef45d80ebd5` and
selects `deep-no-price-no-user-id`. The selected Deep reached
GAUC `0.772305854`, HR@10 `0.051477981`, NDCG@10 `0.010313758`; the paired
Hybrid reached GAUC `0.775218972`, HR@10 `0.054092097`, NDCG@10 `0.011513037`.
The Hybrid VAL artifact failed GAUC/HR/NDCG dominance and semantic traps
(`0/10`), so no production config promotion or seed run is authorized.

Final two-axis source re-review: **Standards PASS / Spec PASS**. Các finding về
archived runbook, R3 NPZ integrity, settings-aware capability, selector coverage,
epoch reset và immutable affinity đều đã được đóng bằng regression tests.

R2/R4 đã tạo và kiểm chứng lineage thực tế sau:

| Thành phần | Evidence canonical |
|---|---|
| Benchmark run | `benchmark-v4-s42-7f40639b0d-ca692e71b3` (`ready`) |
| Seed spec SHA-256 | `ca692e71b3fa166dd9c5ae59405e3edb15efc554c19ac8b0b136e892cad0d7ce` |
| Seed digest | `49b2cdb902b1da8a0456e2814f3edd0a9630f9a3e8749625d2e556f1b495ddf3` |
| Snapshot | `benchmark-v4-20260811-49b2cdb902b1` |
| Snapshot SHA-256 | `1eb1d07759a9e1ca6521794673e761b10bfc2919eb5018fa897d0a31f4b53fa6` |
| Embedding | `benchmark-v4-20260811-49b2cdb902b1-real-f0453078fd58` |
| RuleArtifact training-capable | `benchmark-v4-20260811-49b2cdb902b1-rules-v3-d7ba48f8b8b5` |
| Rule content SHA-256 | `a0f05df9ebafaaabdd833d3fa85cbbe537c85071b8c7231eae32bbed10dda6ba` |
| Coverage semantics | `semantic-trap-purchase-v2` |

Rule evidence canonical khớp giữa database và Python: `14,106` directed rules,
`14,086` non-trap, `20` trap-anchored, `4,143` organic items, VAL context
`4,156/4,975 = 0.8353768844221106` và novel VAL target alignment
`380/4,975 = 0.07638190954773869`. Epoch-1 sampler scan kiểm tra `136,518`
rows và đạt `rows_with_any_rule_rate=0.69097115398702` so với floor `0.40`;
in-batch/explicit rule density lần lượt là `0.0012234062155234186` và
`0.0015117054161356011`.
Semantic readiness pass `10/10`; mỗi trap có đúng `75` baskets,
`co_purchase_count=75` và lift `200`. Database chỉ có một benchmark run v4 và
run đó ở trạng thái `ready` với `823,371` events/`5,200` partition rows.
Các artifact v4 cũ trên filesystem được giữ audit-only và selector bỏ qua nếu
lineage/coverage semantics không khớp. Database từng bị script reclaim cũ xóa
event lineage trước khi lỗi này được phát hiện; vì vậy chỉ run canonical mới ở
trên còn đầy đủ trong database. Source mới đã fail-before-mutation khi run ID
trùng, chỉ terminalize `staging`, không xóa benchmark event/order lineage và có
regression tests bảo vệ contract này.

Probe v4 canonical:

| Probe | GAUC | HR@10 | NDCG@10 |
|---|---:|---:|---:|
| Label permutation | `0.497918259645826` | `0.005630404182585964` | `0.0008282526229445643` |
| Persona-only | `0.786681251542651` | `0.08083651719284134` | `0.013031762846767202` |
| ItemCF | `0.827843070099922` | `0.03317916750452443` | `0.0072545901348188965` |
| SBERT centroid | `0.6514863054947796` | `0.05087472350693746` | `0.012887701021567116` |
| Apriori-only | `0.5141621087395152` | `0.07721697164689323` | `0.02820988600329229` |

Apriori-vs-Random paired bootstrap pass: GAUC delta `0.01624384909368924`,
CI `[0.01114156795970724, 0.021473641098241035]`; NDCG delta
`0.027381633380347725`, CI `[0.024328941012233856, 0.030515071440077722]`.

Quality gate hiện tại: Ruff/mypy pass, seed-product Node `9/9`, Python
`377 passed, 2 fixed-runner skips`, branch coverage `88.24%`; Pipeline `85.03%`,
Trainer `86.68%`, Checkpoint `97.24%`, Report `90.79%`, Release `90.22%`, Bundle
`98.79%`. Root `backend npm test` vẫn fail ở các Jest suites Catalog/Chatbot cũ;
đây không phải regression của R2 nhưng phải được đóng hoặc waiving có chủ đích
trước khi gọi toàn monorepo xanh. CUDA smoke `smoke-r4-readiness-20260811-2042`
hoàn tất một epoch, có strict `best.pt`/`last.pt` và không tạo
evaluation/release/bundle.

Không được chạy production IDs. Bước thực thi kế tiếp là commit/push/freeze
source hiện tại, sau đó chạy R3 diagnostics. Chỉ khi R3 chọn được một Deep
ablation, Hybrid diagnostic pass seven-gate matrix và tạo được cặp config
promotion v5/v6 thì R3/R4 mới được đánh dấu hoàn tất.

### Trình tự R3 bắt buộc sau source freeze

Chạy tuần tự trên snapshot v4, không song song trên GPU 6 GB:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id diag-r3-deep-control-s42 --variant deep_only `
  --config configs\diagnostics\r3\deep-control.toml `
  --snapshot-id benchmark-v4-20260811-49b2cdb902b1 --seed 42 --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id diag-r3-deep-no-price-s42 --variant deep_only `
  --config configs\diagnostics\r3\deep-no-price.toml `
  --snapshot-id benchmark-v4-20260811-49b2cdb902b1 --seed 42 --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id diag-r3-deep-no-user-s42 --variant deep_only `
  --config configs\diagnostics\r3\deep-no-user-id.toml `
  --snapshot-id benchmark-v4-20260811-49b2cdb902b1 --seed 42 --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id diag-r3-deep-no-price-no-user-s42 --variant deep_only `
  --config configs\diagnostics\r3\deep-no-price-no-user-id.toml `
  --snapshot-id benchmark-v4-20260811-49b2cdb902b1 --seed 42 --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli compare-deep-ablations `
  --control-run-id diag-r3-deep-control-s42 `
  --candidate-run-ids diag-r3-deep-no-price-s42 `
    diag-r3-deep-no-user-s42 diag-r3-deep-no-price-no-user-s42 `
  --device cuda
```

Nếu report trả `diagnostic_pause=true` hoặc không có `selected_run_id`, dừng và
không train Hybrid. Nếu có selected run, dùng đúng Hybrid config có hai feature
flags tương ứng, run ID `diag-r3-hybrid-selected-s42`, rồi evaluate VAL với
selected Deep. Pipeline sẽ fail-closed nếu Wide gradient, rule-row coverage,
Wide/Deep RMS hoặc top-10 change rate không đạt contract.

## 1. Mục tiêu và quyết định đã khóa

Hiện trạng theo [report.md](E:/UIT/cv/backend/master/report.md): source/data integrity đạt, nhưng model quality thất bại; chưa được production training.

Các quyết định bắt buộc:

- Hybrid chỉ pass khi:
  - GAUC `>= 0.75`;
  - GAUC, HR@10 và NDCG@10 đều thắng competitor mạnh nhất bằng paired bootstrap CI lower `> 0`;
  - competitor set gồm Persona, ItemCF, SBERT, Apriori, Deep, Noisy Hybrid và Random.
- Deep-only là control:
  - catastrophic kill-switch duy nhất trong epoch là GAUC `< 0.50` hoặc non-finite;
  - seed 42 bị `DIAGNOSTIC_PAUSE` nếu không vượt random rõ ràng hoặc ablation không cải thiện control.
- R2 tạo benchmark lineage v4 hoàn toàn mới. Lineage v3 chỉ giữ audit-only.
- Không đổi `MODEL_SCHEMA_VERSION=5.0.0`.
- Thêm:
  - `EVALUATION_SCHEMA_VERSION=5.1.0`;
  - Rule feature schema `3.0.0`.
- Không bắt đầu sáu production runs cho tới khi R1–R4 đều pass.

Các readiness thresholds cho Wide:

```text
non-trap directed rules              >= 5,000
distinct organic rule items          >= 3,000
VAL context users with organic rule  >= 60%
training rows with any rule          >= 40%
trap-anchored rule fraction          <= 10%
Wide/Deep logit RMS ratio             >= 1%
Hybrid/Deep top-10 changed-user rate  >= 5%
```

Full-catalog pair coverage vẫn được ghi nhận nhưng không dùng làm absolute gate vì rule graph có bản chất sparse.

---

# Phase R1 — Sửa observability và Victory Gate contract

## R1.1. Chuẩn hóa contracts

### [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py)

1. Thêm:

```python
EVALUATION_SCHEMA_VERSION = "5.1.0"
```

2. Mở rộng `ModelVariant`:

```python
PERSONA_ONLY = "persona_only"
```

3. Thêm typed model:

```python
class MetricBaselineSelection(BaseModel):
    gauc: str
    hr_at_k: str
    ndcg_at_k: str
```

Ba tên phải non-empty và thuộc competitor set đã publish.

4. Sửa `VictoryMatrix`:

```python
schema_version: Literal["5.1.0"]
random_gauc_passed: bool
hybrid_minimum_gauc_passed: bool
gauc_domination_passed: bool
hr_domination_passed: bool
ndcg_domination_passed: bool
semantic_traps_passed: bool
cold_parity_passed: bool
strongest_baselines: MetricBaselineSelection
```

Exact gate names:

```text
random_gauc
hybrid_minimum_gauc
gauc_domination
hr_domination
ndcg_domination
semantic_traps
cold_parity
```

Không giữ `relative_ndcg` hoặc `strongest_hr_baseline` legacy.

5. Sửa `AggregateReleaseReport` sang evaluation schema `5.1.0` và require sáu aggregate gates:

```text
aggregate_gauc_domination
aggregate_hr_domination
aggregate_ndcg_domination
aggregate_gauc_vs_deep
aggregate_hr_vs_deep
aggregate_ndcg_vs_deep
```

Evaluation artifact v5.0 cũ không được dùng cho release mới.

## R1.2. Settings cho dominance và Wide signal

### [config.py](E:/UIT/cv/backend/ai-service/src/ai_service/config.py)

Trong `EvalConfig`:

- Giữ `minimum_gauc=0.75`.
- Thay ba negative guardrails bằng:

```python
aggregate_gauc_min_delta: float = Field(default=0.0, ge=0.0)
aggregate_hr_min_delta: float = Field(default=0.0, ge=0.0)
aggregate_ndcg_min_delta: float = Field(default=0.0, ge=0.0)
deep_clear_random_gauc: float = Field(default=0.55, ge=0.5, le=1.0)
minimum_wide_to_deep_rms_ratio: float = Field(default=0.01, gt=0.0)
minimum_hybrid_deep_top_k_change_rate: float = Field(default=0.05, gt=0.0, le=1.0)
```

Các field phải có mặt trong resolved document và comparison signature. Không migrate resolved config cũ.

## R1.3. Sửa instrumentation trong Trainer

### [trainer.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py)

Thay `rule_present_rate` trong `EpochMetrics` và `_TrainingEpochPass` bằng:

```python
in_batch_rule_present_rate: float
explicit_rule_present_rate: float
rows_with_any_rule_rate: float
wide_to_deep_logit_rms_ratio: float
hybrid_deep_top_k_change_rate: float
```

Trong nhánh `PurchaseBatch` của `_train_epoch()`:

```python
valid_in_batch_present = in_batch_rule_present & denominator_mask
row_has_rule = (
    valid_in_batch_present.any(dim=1)
    | explicit_rule_present.any(dim=1)
)
```

Tích lũy riêng:

- `valid_in_batch_present.sum()` / `denominator_mask.sum()`;
- `explicit_rule_present.sum()` / `explicit_rule_present.numel()`;
- `row_has_rule.sum()` / số purchase rows.

Nhánh `TrainingBatch` cũng quy đổi về ba accumulator tương tự để history có cùng schema.

Không dùng default `0` để che trường hợp denominator rỗng; denominator không hợp lệ phải raise `ModelTrainingError`.

`_build_epoch_metrics()`:

- tính `wide_to_deep_logit_rms_ratio = wide_rms / max(deep_rms, eps)`;
- lấy `hybrid_deep_top_k_change_rate` từ validation pass;
- validate tất cả là finite và trong miền hợp lệ;
- Deep-only không áp Wide signal gate;
- Hybrid epoch 1 tiếp tục require Wide gradient `>0`.

History JSONL mới phải chứa các field mới và không còn `rule_present_rate`.

## R1.4. Đo ranking impact của Wide

### [full_catalog.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/full_catalog.py)

Mở rộng `TrainingValidationPass`:

```python
hybrid_deep_top_k_change_rate: float
```

Trong `evaluate_training_epoch()`:

- giữ top-10 Deep và Hybrid cho eligible validation users;
- một user được tính “changed” nếu ordered top-10 Hybrid khác ordered top-10 Deep;
- rate = số changed users / eligible users;
- không giữ full-catalog score matrices sau batch;
- xác nhận rate finite, `[0,1]`.

## R1.5. Dùng chung Persona baseline

### File mới: [persona.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/persona.py)

Tạo deep module:

```python
@dataclass(frozen=True)
class PreparedPersonaBaseline:
    score_vectors: np.ndarray

def prepare_persona_baseline(
    snapshot: Snapshot,
    prepared_split: PreparedEvaluationSplit,
) -> PreparedPersonaBaseline

def score_persona_batch(
    prepared: PreparedPersonaBaseline,
    users: np.ndarray,
    candidates: np.ndarray,
) -> np.ndarray
```

Semantics phải đúng với Persona probe hiện tại:

- chỉ organic history;
- category counts theo persona;
- popularity chỉ dùng deterministic tie-break;
- không `.loc` theo từng user;
- chỉ giữ `num_personas + 1` vectors.

### [probes.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/probes.py)

Xóa implementation Persona cục bộ và dùng module mới. Numerical parity trên fixture cũ phải `atol <= 1e-6`.

### [baselines.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/baselines.py)

- Thêm `persona_only: EvaluationResult` vào `BaselineComparisonReport`.
- Đổi `run_seven_way_baselines()` thành:

```python
run_full_catalog_comparison(...)
```

- Persona phải dùng đúng `PreparedEvaluationSplit` đang dùng bởi neural, SBERT, ItemCF và Apriori.
- `baselines` property trả đủ tám nhóm model/baseline, Random vẫn là mean của 10 seeds.

Không giữ alias production cho tên `run_seven_way_baselines`.

## R1.6. Strengthened gates

### [gates.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/gates.py)

Tạo helper:

```python
_select_strongest_competitor(
    comparison: BaselineComparisonReport,
    *,
    metric: Literal["gauc", "hr_at_k", "ndcg_at_k"],
) -> tuple[str, EvaluationResult]
```

Competitor set không chứa Hybrid, nhưng chứa Persona, ItemCF, SBERT, Apriori, Deep, Noisy Hybrid và Random mean.

Gate algorithm:

1. Random sanity giữ nguyên.
2. `hybrid_minimum_gauc`: Hybrid `>=0.75`.
3. `gauc_domination`: Hybrid mean lớn hơn strongest GAUC và paired CI lower `>0`.
4. `hr_domination`: tương tự với HR@10.
5. `ndcg_domination`: tương tự với NDCG@10.
6. Semantic traps `10/10`.
7. Cold parity pass.

Mỗi metric tự chọn strongest competitor; không tái sử dụng HR winner cho GAUC/NDCG.

Canonical SHA chỉ tính sau khi điền đủ schema, baseline selections và bảy gates.

## R1.7. Evaluation artifacts và aggregate release

### [report.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/report.py)

Thêm exact NPZ keys:

```text
persona_hr
persona_ndcg
persona_gauc
```

Manifest dùng schema `5.1.0`. Loader reject:

- artifact v5.0;
- thiếu Persona arrays;
- extra keys;
- wrong dtype/shape/hash.

### [release.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/release.py)

`_build_aggregate_gates()`:

- average aligned per-user arrays qua ba seeds;
- tìm strongest aggregate competitor riêng cho GAUC/HR/NDCG;
- paired CI lower phải `>0`;
- đồng thời dựng ba paired Hybrid-vs-Deep gates riêng;
- không dùng negative deltas để tuyên bố victory.

### [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py)

Trong `_evaluate_pair()`:

- thay call bằng `run_full_catalog_comparison()`;
- đưa Persona arrays vào `publish_evaluation_artifacts()`;
- không thay lifecycle ownership: artifact vẫn Hybrid-owned;
- không refactor `execute_command()` ở R1.

## Validate R1

Tests cần cập nhật:

- `test_trainer_contract.py`: sampled-softmax fixture có rule phải cho ba coverage fields khác zero.
- `test_full_catalog_contract.py`: top-10 change rate đúng và Persona streaming/reference parity.
- `test_probe_streaming_contract.py`: Persona probe parity `<=1e-6`.
- `test_v5_artifact_and_gate_contracts.py`: exact bảy gates.
- `test_checkpoint_report_and_trap_contracts.py`: Persona arrays, schema/hash corruption.
- `test_release_gate_contract.py`: six aggregate gates và strongest competitor khác nhau theo metric.
- `test_pipeline_evaluation_lifecycle.py`: paired evaluation publish Persona arrays.

Critical scenarios:

- Hybrid GAUC `0.76` nhưng thua ItemCF GAUC → fail.
- Hybrid thắng Apriori NDCG nhưng thua SBERT → fail.
- Hybrid HR thấp hơn Persona → fail.
- Hybrid thắng strongest mean nhưng CI lower `<=0` → fail.
- Artifact v5.0 → reject.

Exit gate:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_trainer_contract.py `
  tests\unit\test_full_catalog_contract.py `
  tests\unit\test_probe_streaming_contract.py `
  tests\unit\test_v5_artifact_and_gate_contracts.py `
  tests\unit\test_checkpoint_report_and_trap_contracts.py `
  tests\unit\test_release_gate_contract.py -q
```

---

# Phase R2 — Tạo Wide signal hữu ích và lineage v4

## R2.1. Chia sẻ affinity giữa events và orders

### File mới: [benchmark-affinity.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/benchmark-affinity.js)

Chuyển từ `seed-ml-events.js`:

```javascript
buildPersonaAssignments(...)
buildUserAffinities(...)
```

Thêm:

```javascript
buildOrganicBundleTemplates({
  products,
  warmProducts,
  fixtureProducts,
  personaByUser,
  affinityByUser,
  preferredProducts,
  spec
})
```

Kết quả immutable:

```javascript
{
  templates,
  personaByUser,
  affinityByUser,
  preferredProducts
}
```

Template phải chứa persona, product IDs, repeat count và deterministic template ID.

### [seed-ml-events.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/seed-ml-events.js)

`seedMlEvents()` nhận precomputed `affinityModel`; không tự sinh persona/affinity lần hai. Event và order generator vì vậy dùng đúng cùng user preference.

## R2.2. Sinh organic order graph có support thật

### [mock-orders.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/mock-orders.js)

Tách pure generator:

```javascript
generateOrderPlan({
  spec,
  users,
  products,
  coldProducts,
  affinityModel
})
```

`seedOrders()` chỉ persist plan.

Benchmark v4 sinh đúng:

```text
14,250 organic orders
750 semantic-trap orders
2,375 organic templates
mỗi organic template lặp 6 lần
organic basket size 3 hoặc 4
trap fraction 5%
```

Rules:

- organic template loại cold items và toàn bộ semantic-trap endpoints;
- template items phải thuộc persona/category affinity;
- ít nhất 3,000 distinct organic products xuất hiện;
- organic orders phân phối deterministic trên 5,000 users, mỗi user nhận 2–3 organic orders;
- semantic traps được phân đều 75 orders/trap;
- không uniform-fill warm catalog;
- cùng seed/spec/catalog phải tạo cùng SHA.

## R2.3. Benchmark spec v4

### File mới: [benchmark-spec-v4.json](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/benchmark-spec-v4.json)

Giữ v3 file audit-only. V4:

```json
{
  "schema_version": "2.1.0",
  "generator_version": "4.0.0",
  "organic_order_count": 14250,
  "semantic_order_count": 750,
  "organic_bundle_template_count": 2375,
  "organic_bundle_repeats": 6,
  "minimum_non_trap_directed_rules": 5000,
  "minimum_distinct_organic_rule_items": 3000,
  "minimum_val_context_rule_coverage": 0.60,
  "minimum_val_rule_target_rate": 0.04,
  "minimum_training_rows_with_any_rule": 0.40,
  "maximum_trap_anchored_rule_fraction": 0.10
}
```

Giữ event count, users, products, cold items và temporal split counts hiện tại.

## R2.4. Rule summary và DB validation

### [populate-copurchase.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/populate-copurchase.js)

Return typed document:

```javascript
{
  totalOrders,
  storedPairCount,
  totalDirectedRules,
  nonTrapDirectedRules,
  trapAnchoredDirectedRules,
  trapAnchoredRuleFraction,
  distinctOrganicRuleItems,
  fullCatalogOrganicPairCoverage
}
```

Phân loại trap bằng exact endpoint set từ spec, không dựa vào product ID range.

### [seed-ml-benchmark.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/seed-ml-benchmark.js)

- Nhận `--spec` bắt buộc.
- Run ID prefix lấy từ generator major: `benchmark-v4-...`.
- Dựng affinity model đúng một lần rồi truyền cho events/orders.
- `validateRun()` query latest organic train purchase theo stable `(event_ts,event_id)` và tính:
  - eligible context users;
  - users có ít nhất một outgoing non-trap rule;
  - context coverage fraction.
- Event generator chuyển một phần novel VAL purchases sang unseen bundle
  neighbors của latest train purchase; `validateRun()` đo exact aligned target
  rate và reject nếu `<0.04`.
- Run ID đã tồn tại bị reject trước mọi mutation; chỉ run `staging` được resume
  hoặc chuyển `failed`. Ready/failed lineage không bị xóa hay reuse.
- Fail trước `ready` nếu một threshold không đạt.
- Persist evidence vào `ml_benchmark_run_v1.rule_coverage JSONB`.
- Failed seed run giữ status `failed`; không overwrite run cũ.

## R2.5. Python RuleArtifact coverage contract

### [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py)

Thêm:

```python
class RuleCoverageEvidence(BaseModel):
    total_directed_rules: int
    non_trap_directed_rules: int
    trap_anchored_directed_rules: int
    trap_anchored_rule_fraction: float
    distinct_organic_rule_items: int
    eligible_val_context_users: int
    val_context_users_with_rule: int
    val_context_rule_coverage: float
    full_catalog_organic_pair_coverage: float
```

`RuleManifest` thêm optional `coverage`. Artifact v2 có thể load audit-only; training require:

```text
feature_schema_version == 3.0.0
coverage != None
```

### [rules.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/rules.py)

Khi mine artifact mới:

- tự tính lại coverage từ numerical arrays và snapshot;
- không tin trực tiếp JSON từ seed database;
- bind coverage document vào canonical artifact identity;
- artifact kind đổi thành `rule-v3-organic-coverage`;
- `require_training_capability(settings)` kiểm tra full statistics và toàn bộ coverage thresholds.

Không overwrite RuleArtifact v2.

## R2.6. Training-candidate readiness module

### File mới: [rule_readiness.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/rule_readiness.py)

Thêm:

```python
class TrainingRuleReadiness(BaseModel):
    in_batch_rule_present_rate: float
    explicit_rule_present_rate: float
    rows_with_any_rule_rate: float
    examined_rows: int
    passed: bool
    failure_reasons: tuple[str, ...]

def assess_training_rule_readiness(
    train_loader: PurchaseBatchIterator,
    *,
    minimum_rows_with_any_rule: float,
) -> TrainingRuleReadiness
```

- scan deterministic epoch 1 trước GPU training;
- không model forward;
- dùng cùng masks/denominators với Trainer;
- scan xong reset loader về epoch 1;
- fail nếu rows-with-rule `<0.40`.

## R2.7. Thay đổi cụ thể trong pipeline

### [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py)

`_find_training_rule_artifact()` phải require:

```text
snapshot SHA exact
has_full_statistics = true
feature_schema_version = 3.0.0
min_count/min_lift match config
coverage thresholds pass
```

Zero/multiple match tiếp tục fail, liệt kê mismatch reasons.

Trong `_train()`:

```text
load snapshot/embedding/rules
→ rules.require_training_capability(settings)
→ build purchase index/sampler/loader
→ assess_training_rule_readiness(loader)
→ nếu fail: raise trước RunLifecycle.create()
→ nếu pass: create lifecycle
→ atomic-write training/preflight-rule-readiness.json
→ Trainer.fit()
```

Coverage fail không được tạo run directory.

Trong `probe-data` branch:

- load exact v3 RuleArtifact matching snapshot;
- dùng cùng `PreparedEvaluationSplit`;
- chạy Apriori per-user metrics;
- emit RuleCoverageEvidence và Apriori-vs-Random paired evidence;
- không fallback sang legacy rules.

### [probes.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/probes.py)

Mở rộng probe report:

- Apriori HR/NDCG/GAUC;
- paired Apriori–Random CI cho GAUC và NDCG;
- RuleCoverageEvidence.

## Validate R2

JS tests mới:

```text
seed-product/tests/benchmark-affinity.test.js
seed-product/tests/mock-orders.test.js
seed-product/tests/rule-readiness.test.js
seed-product/tests/seed-ml-events.test.js
seed-product/tests/seed-ml-benchmark.test.js
```

Kiểm tra:

- reproducibility hash;
- exact 15,000 orders;
- exact organic/trap allocation;
- no cold/fixture leakage trong organic templates;
- template support `>=6`;
- thresholds fail-closed.

Python tests:

```text
test_feature_rule_dataset_contracts.py
test_rule_readiness_contract.py
test_pipeline_preflight_contracts.py
test_probe_streaming_contract.py
```

Exit gate:

```powershell
cd backend
npm run test:seed-product

.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_feature_rule_dataset_contracts.py `
  tests\unit\test_rule_readiness_contract.py `
  tests\unit\test_pipeline_preflight_contracts.py `
  tests\unit\test_probe_streaming_contract.py -q
```

Sau khi seed DB:

- tạo snapshot, embedding và RuleArtifact IDs mới;
- old v3 lineage vẫn load audit-only;
- Apriori GAUC và NDCG phải thắng Random bằng paired CI lower `>0`;
- tất cả coverage thresholds phải pass;
- reference probe values v3 không được tái sử dụng cho v4.

---

# Phase R3 — Neural ablation và diagnostic pause

## R3.1. Typed feature flags

### [config.py](E:/UIT/cv/backend/ai-service/src/ai_service/config.py)

Trong `ModelConfig`:

```python
use_user_id_embedding: bool = True
use_price_features: bool = True
```

Hai flags phải đi vào training, experiment và comparison signatures.

## R3.2. User tower

### [user_tower.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/user_tower.py)

- `use_user_id_embedding=False`:
  - không instantiate `nn.Embedding` cho user ID;
  - input dimension loại `user_emb_dim`;
  - forward vẫn nhận `user_idx` để giữ interface model ổn định, nhưng không dùng làm learned identity feature.
- Không zero parameter post-hoc.
- Checkpoint strict load dựa trên resolved config tương ứng.

## R3.3. Item tower

### [item_tower.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/item_tower.py)

- `use_price_features=False`:
  - không instantiate price embedding;
  - input dimension loại `price_emb_dim`;
  - forward giữ `price_bucket` argument nhưng bỏ qua khi flag false.
- Giữ category, SBERT và item-ID residual trong R3.
- Không sửa scoring formula hoặc temperature.

### [two_tower_wide_deep.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/two_tower_wide_deep.py)

Chỉ truyền flags vào towers; public forward signature không đổi. Deep-only tiếp tục không forward Wide branch.

## R3.4. Diagnostic configs

Tạo:

```text
configs/diagnostics/r3/deep-control.toml
configs/diagnostics/r3/deep-no-price.toml
configs/diagnostics/r3/deep-no-user-id.toml
configs/diagnostics/r3/deep-no-price-no-user-id.toml
configs/diagnostics/r3/hybrid-no-price.toml
configs/diagnostics/r3/hybrid-no-user-id.toml
configs/diagnostics/r3/hybrid-no-price-no-user-id.toml
```

Mỗi Deep/Hybrid pair chỉ khác `training_variant`. Không sửa `v3.toml`/`v4.toml`.

Diagnostic run IDs:

```text
diag-r3-deep-control-s42
diag-r3-deep-no-price-s42
diag-r3-deep-no-user-s42
diag-r3-deep-no-price-no-user-s42
diag-r3-hybrid-selected-s42
```

## R3.5. Immutable ablation comparison

### File mới: [ablation.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/ablation.py)

Thêm typed report:

```python
class DeepAblationCandidate(BaseModel):
    run_id: str
    config_name: str
    gauc: float
    hr_at_k: float
    ndcg_at_k: float
    gauc_delta_vs_control: float
    gauc_ci_lower_vs_control: float
    gauc_ci_upper_vs_control: float
    gauc_ci_lower_vs_random: float
    eligible: bool

class DeepAblationReport(BaseModel):
    control_run_id: str
    minimum_control_gauc: float
    candidates: tuple[DeepAblationCandidate, ...]
    selected_run_id: str | None
    diagnostic_pause: bool
    pause_reasons: tuple[str, ...]
    per_user_metrics_sha256: str
    artifact_sha256: str
```

Selection:

1. Any GAUC `<0.50`/non-finite → candidate catastrophic.
2. Control Deep phải có:
   - GAUC `>=0.55`;
   - paired CI lower `(Deep - Random) >0`.
3. Ít nhất một ablation phải có paired GAUC CI lower `>0` so với control.
4. Eligible candidates xếp lexicographic:
   - GAUC;
   - NDCG@10;
   - HR@10;
   - config name.
5. Không candidate cải thiện → `DIAGNOSTIC_PAUSE`, chưa train Hybrid.

Publish immutable JSON và per-user NPZ dưới:

```text
artifacts/diagnostics/r3/<comparison-signature>/
```

Publisher/loader bắt buộc:

- exact file allowlist `report.json` + `per-user-metrics.npz`;
- NPZ exact keys cho user IDs, control, Random và ba candidates;
- sorted unique `int64` user IDs; mọi metric exact `float64`, finite, `[0,1]`
  và cùng shape;
- report bind SHA-256 của NPZ; canonical report SHA bao gồm metrics SHA;
- verify temporary directory trước atomic rename; selection chỉ đọc qua verified
  loader và reject corruption/extra keys.

## R3.6. CLI và pipeline diagnostics

### [cli.py](E:/UIT/cv/backend/ai-service/src/ai_service/cli.py)

Thêm command:

```text
compare-deep-ablations
  --control-run-id
  --candidate-run-ids <exactly 3>
  --device
```

### [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py)

Thêm `_compare_deep_ablations()`:

- strict-load bốn Deep runs;
- require same v4 lineage, seed 42, Git commit và evaluation settings;
- prepare VAL split một lần;
- evaluate Deep variant cho từng checkpoint;
- publish `DeepAblationReport`;
- không đổi lifecycle, không seal/export.

`execute_command()` chỉ thêm một dispatch branch; không refactor các command khác.

## R3.7. Hybrid diagnostic gate

Train đúng một Hybrid config tương ứng selected Deep flags.

Trước strengthened Victory Matrix, require:

```text
rows_with_any_rule_rate             >= 0.40
epoch-1 Wide gradient                > 0
Wide/Deep RMS ratio                 >= 0.01
Hybrid/Deep top-10 changed users    >= 0.05
all diagnostics finite
```

Sau đó Hybrid phải pass toàn bộ seven-gate matrix R1. Nếu Wide signal thresholds pass nhưng Victory Matrix fail, dừng và deep-scan objective/data alignment; không promote config.

## R3.8. Promote config

Chỉ sau diagnostic Hybrid pass:

- tạo `configs/ablations/v5.toml` từ selected Deep config;
- tạo `configs/ablations/v6.toml` từ cùng config, chỉ đổi variant thành Hybrid;
- recompute và ghi training/comparison signatures;
- không thay model schema 5.0.0;
- archived diagnostic checkpoints chỉ load với resolved config tương ứng.

## Validate R3

Tests:

- `test_config_contract.py`: flags đổi signatures.
- `test_model_contracts.py`: disabled module thực sự không có parameters.
- `test_trainer_contract.py`: optimizer parameter sets và Wide invariants.
- `test_ablation_contract.py`: deterministic selection và mọi diagnostic pause path.
- `test_pipeline_cli_contract.py`: parser → real ablation dispatch.
- `test_pipeline_preflight_recovery.py`: mismatched lineage/seed/commit reject.
- `test_onnx_runtime_contract.py`: export/parity với selected feature flags.

R3 exit gate:

- control Deep rõ ràng hơn random;
- ít nhất một ablation cải thiện control bằng positive paired GAUC CI;
- selected Hybrid có Wide signal hữu hình;
- selected Hybrid pass strict single-seed VAL;
- chưa tạo production run IDs.

---

# Phase R4 — Full readiness và mở production training

## R4.1. Tạo lineage v4 — COMPLETED

Canonical evidence đã publish; không chạy rebuild lại cùng spec/run ID. Chỉ
preflight read-only bằng lệnh sau từ repository root:

```powershell
node backend\docs\chatbot\seed-product\seed-ml-benchmark.js `
  --spec backend\docs\chatbot\seed-product\benchmark-spec-v4.json `
  --store-id 1 --seed 42 --preflight-only
```

Evidence immutable:

```text
benchmark run: benchmark-v4-s42-7f40639b0d-ca692e71b3
snapshot:      benchmark-v4-20260811-49b2cdb902b1
embedding:     benchmark-v4-20260811-49b2cdb902b1-real-f0453078fd58
rules:         benchmark-v4-20260811-49b2cdb902b1-rules-v3-d7ba48f8b8b5
```

Các lệnh bootstrap dưới đây đã hoàn thành và chỉ là provenance record, không
phải runbook để chạy lại:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli snapshot `
  --source postgres --benchmark-run-id $seedResult.runId `
  --snapshot-id $snapshotId --store-id 1

.\.venv\Scripts\python.exe -m ai_service.cli features `
  --snapshot-id $snapshotId --embedding-source real --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli rules `
  --config configs\diagnostics\r2-v4.toml --snapshot-id $snapshotId

.\.venv\Scripts\python.exe -m ai_service.cli audit-data `
  --config configs\diagnostics\r2-v4.toml --snapshot-id $snapshotId --device cpu

.\.venv\Scripts\python.exe -m ai_service.cli probe-data `
  --config configs\diagnostics\r2-v4.toml --snapshot-id $snapshotId --device cpu
```

Không overwrite/xóa lineage v3.

## R4.2. Full quality gate

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts

node --test ..\backend\docs\chatbot\seed-product\tests\*.test.js

$coverageJson = Join-Path $env:TEMP "ai-service-r4-ready.json"
.\.venv\Scripts\python.exe -m pytest `
  --cov=ai_service --cov-branch `
  --cov-report=term-missing `
  --cov-report=json:$coverageJson `
  --cov-fail-under=85 -q

.\.venv\Scripts\python.exe scripts\check_critical_coverage.py $coverageJson
git diff --check
```

Acceptance:

- toàn bộ tests pass;
- chỉ hai fixed-runner skips;
- branch coverage tổng `>=85%`;
- Trainer/Pipeline `>=85%`;
- Checkpoint/Report/Release/Bundle `>=90%`;
- không coverage exclusions hoặc threshold reduction.

## R4.3. Documentation và source freeze

Cập nhật trước freeze:

- [report.md](E:/UIT/cv/backend/master/report.md):
  - thay metrics v3 bằng v4;
  - ghi coverage evidence;
  - ghi diagnostic selection;
  - chưa tuyên bố Hybrid victory production.
- [walkthrough.md](E:/UIT/cv/backend/walkthrough.md):
  - exact quality results;
  - new artifact IDs;
  - diagnostic run IDs;
  - readiness status.
- [detail-plan.md](E:/UIT/cv/backend/master/detail-plan.md):
  - mark R1–R4;
  - ghi selected v5/v6 signatures;
  - ghi production commands.

Commit/push rồi require:

```text
worktree clean
HEAD == upstream
ahead/behind 0/0
production environment pass
CUDA smoke pass
new lineage audit/probes/rules pass
all diagnostic IDs separated from production IDs
```

Status chỉ chuyển thành:

```text
READY_FOR_DEEP_R4_42_TRAINING
```

Production IDs mới:

```text
deep-r4-42-v5
hybrid-r4-42-v5
deep-r4-2027-v5
hybrid-r4-2027-v5
deep-r4-31415-v5
hybrid-r4-31415-v5
```

Không dùng lại planned IDs `deep-42-v5`/`hybrid-42-v5` vì lineage và comparison contract đã thay đổi.

---

# 5. Trình tự production training sau R4

```text
Deep seed 42
→ Deep safety + diagnostic-pause check
→ Hybrid seed 42
→ strict single-seed VAL
→ chỉ khi pass mới chạy seeds 2027/31415
→ aggregate VAL
→ TEST cả ba pairs
→ aggregate TEST
→ seal selected Hybrid
→ export/verify bundle
→ ONNX parity/fixed-runner benchmark
```

Deep seed 42:

- GAUC `<0.50` hoặc non-finite → `FAILED`.
- GAUC `<0.55` hoặc CI lower so với Random `<=0` → `DIAGNOSTIC_PAUSE`.
- Không áp Hybrid floor `0.75` hoặc Persona/ItemCF dominance lên Deep.

Hybrid seed 42:

- non-finite, GAUC `<0.50`, Wide gradient không hợp lệ → `FAILED`;
- Wide coverage/RMS/ranking-impact fail → dừng deep scan;
- GAUC `<0.75` hoặc thua bất kỳ strongest competitor metric nào → single-seed gate fail;
- không tạo seed 2027.

Chỉ tuyên bố Hybrid thành công khi cả ba single-seed matrices, aggregate VAL/TEST, seal, bundle verification, ONNX parity và serving benchmark đều pass.

## R3 remediation plan after the 2026-08-12 VAL failure

Production training remains forbidden. The failed Hybrid artifact is evidence,
not a candidate for promotion. Do not delete or overwrite the four Deep runs,
the selected Hybrid run, or the R3 receipt.

### R3.1 — Reproduce and localize each failed gate

Files:

- `ai-service/src/ai_service/evaluation/gates.py`
- `ai-service/src/ai_service/evaluation/semantic_traps.py`
- `ai-service/src/ai_service/evaluation/full_catalog.py`
- `ai-service/src/ai_service/evaluation/report.py`
- `ai-service/tests/unit/test_release_gate_contract.py`
- `ai-service/tests/unit/test_checkpoint_report_and_trap_contracts.py`

Actions:

1. Add diagnostic-only per-user evidence for Hybrid/Deep/ItemCF/Persona/
   Apriori top-10 IDs and paired deltas. Do not weaken the Victory Matrix.
2. Record exact anchor/target scores, ranks and seen/cold masks for all ten
   semantic-trap failures; reject raw/internal ID mismatches.
3. Preserve strongest-baseline selection and negative CI evidence. Failed
   gates remain `passed=false` with a non-empty reason.
4. Add corruption tests for a mutated user row, trap target and baseline
   vector; verified loading must reject each before publication.

Validation:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_release_gate_contract.py `
  tests\unit\test_checkpoint_report_and_trap_contracts.py -q
```

The current failed matrix must reproduce before any model/data change.

### R3.2 — Trace data-to-objective alignment

Files:

- `backend/docs/chatbot/seed-product/benchmark-affinity.js`
- `backend/docs/chatbot/seed-product/mock-orders.js`
- `backend/docs/chatbot/seed-product/populate-copurchase.js`
- `backend/docs/chatbot/seed-product/inspect-ml-storage.js`
- `ai-service/src/ai_service/data/snapshot.py`
- `ai-service/src/ai_service/data/rules.py`
- `ai-service/src/ai_service/evaluation/baselines.py`
- `ai-service/tests/unit/test_data_quality_contract.py`

Actions:

1. Reconcile organic templates, affinity assignments, latest purchase
   contexts and RuleArtifact edges for the failed VAL users/items. Report
   truth novelty, seen masking, persona and rule-hit counts.
2. Verify all non-trap rules are reachable from organic contexts. The current
   in-batch density `0.001223` is evidence to inspect, not a reason to lower
   the readiness floor.
3. Compare Apriori/Persona/ItemCF IDs with Hybrid IDs. Fix shared split/context
   or mapping code only when the evidence proves a defect; never patch gates.
4. Keep the v4 database run immutable. Any seed rebuild uses new run,
   snapshot, RuleArtifact and source revision IDs.

Validation:

```powershell
npm.cmd run test:seed-product
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_data_quality_contract.py `
  tests\unit\test_full_catalog_contract.py -q
```

Require audit/probe parity and exact organic/trap counts before rebuilding.

### R3.3 — Validate Wide signal and objective changes in isolation

Files:

- `ai-service/src/ai_service/training/trainer.py`
- `ai-service/src/ai_service/models/wide_layer.py`
- `ai-service/src/ai_service/models/two_tower_wide_deep.py`
- `ai-service/src/ai_service/config.py`
- `ai-service/configs/diagnostics/r3/*.toml`
- `ai-service/tests/unit/test_trainer_contract.py`
- `ai-service/tests/unit/test_trainer_recovery_contract.py`

Actions:

1. Use the failed Hybrid as baseline. Record epoch-1/selected Wide gradient,
   Wide/Deep RMS, top-k change and Hybrid-minus-Deep/Wide deltas.
2. Test one objective/feature change per new diagnostic config. Do not change
   schema, early stopping or Victory thresholds.
3. Require epoch-1 Wide gradient `>0`, finite tensors, hard-cache refreshes,
   and unchanged Wide parameters in Deep-only.
4. A candidate is eligible for paired VAL only when failed metric gates also
   improve; Wide RMS alone is insufficient.

Validation:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_trainer_contract.py `
  tests\unit\test_trainer_recovery_contract.py -q
```

Stop on GAUC `<0.50`, non-finite values, missing cache, Wide-gradient failure,
or semantic-trap regression.

### R3.4 — New immutable diagnostic campaign and promotion

Only after R3.1–R3.3 pass:

1. Commit/push remediation source/config; verify clean worktree and
   `HEAD == origin/main`.
2. Generate a new snapshot/rules lineage only if R3.2 proves data misalignment;
   otherwise reuse the verified v4 lineage unchanged.
3. Train four Deep ablations on seed 42, publish one receipt, train selected
   Hybrid and run paired VAL.
4. Require all seven gates, semantic traps `10/10`, cold parity and the Wide
   signal contract. Any failure keeps production blocked and prevents seeds
   2027/31415.
5. Promote v5/v6 only after the new receipt and paired VAL artifact are
   immutable and verified; then rerun readiness before production Deep 42.

Earliest permissible sequence:

```text
new R3 receipt + paired VAL pass
  -> v5/v6 promotion and source freeze
  -> Deep seed 42 -> Hybrid seed 42 -> VAL pass
  -> seeds 2027/31415 -> aggregate VAL -> TEST all three pairs
  -> aggregate TEST -> seal/export/verify/benchmark
```

## Assumptions

- Threshold R2 là readiness floors, không phải target metric của model.
- Deep remains a control; diagnostic pause không chuyển lifecycle sang `FAILED`.
- Diagnostic runs được phép trước production campaign nhưng không được seal/export.
- Mọi artifact v3/v2 được giữ audit-only; không dọn hoặc overwrite trong R1–R4.
- `Trainer.fit()` tiếp tục là training test seam chính.
- Không refactor toàn bộ `execute_command()` trong lộ trình này.
