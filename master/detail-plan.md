# Kế hoạch triển khai chi tiết cấp mã nguồn: Joint Hybrid Pipeline v5

Mọi đường dẫn dưới đây nằm trong `E:\UIT\cv\backend\ai-service`. Plan này thay thế toàn bộ plan trước.

## 1. Sơ đồ thay đổi theo file

### 1.1. Contracts và configuration

| File | Symbol hiện tại | Thay đổi chính xác |
|---|---|---|
| [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py) | `RunStatus` | Thêm `FAILED`; giữ `INTERRUPTED` riêng cho process/resource interruption. |
| [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py) | `ModelVariant` | Giữ variants hiện tại; sửa semantics của `NOISY_HYBRID` thành persona swap 10%, không còn Gaussian score noise. |
| [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py) | Mới: `TrainingVariant` | Enum chỉ có `DEEP_ONLY`, `HYBRID`; dùng để xác định model được train, không dùng `ModelVariant` cho lifecycle. |
| [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py) | `RuleManifest` | Thêm `feature_schema_version="2.0.0"` và `has_full_statistics=true`. |
| [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py) | `CheckpointManifest` | Thêm `training_variant`, `best_val_hr_at_k`, `comparison_signature_sha256`. |
| [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py) | `ModelBundleManifest` | Bump schema; bỏ metadata semantic override/cascade; thêm `training_variant="hybrid"` và `victory_matrix_sha256`. |
| [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py) | Mới | Thêm typed reports: `MetricGateResult`, `ColdParityReport`, `VictoryMatrix`. |
| [config.py](E:/UIT/cv/backend/ai-service/src/ai_service/config.py) | `MODEL_SCHEMA_VERSION` | Đổi từ `4.0.0` thành `5.0.0`. |
| [config.py](E:/UIT/cv/backend/ai-service/src/ai_service/config.py) | `ModelConfig` | Xóa `wide_logit_scale`, `wide_cascade_min_lift`, `wide_cascade_min_count`. |
| [config.py](E:/UIT/cv/backend/ai-service/src/ai_service/config.py) | `TrainConfig` | Thêm `training_variant`; đặt `early_stopping_patience=4`; bỏ `min_epochs`; giữ `min_delta=1e-4`. |
| [config.py](E:/UIT/cv/backend/ai-service/src/ai_service/config.py) | `TrainConfig` | Xóa toàn bộ `wide_calibration_*` và `enable_wide_calibration`. |
| [config.py](E:/UIT/cv/backend/ai-service/src/ai_service/config.py) | `EvalConfig` | Thêm `minimum_gauc=0.75`, `random_gauc_tolerance=0.02`, `cold_score_atol=1e-6`, `wide_zero_atol=1e-7`. |
| [config.py](E:/UIT/cv/backend/ai-service/src/ai_service/config.py) | `Settings` | Thêm `comparison_signature_sha256()`; hash giống experiment signature nhưng bỏ `seed` và `training_variant`. |
| [errors.py](E:/UIT/cv/backend/ai-service/src/ai_service/errors.py) | Mới | Thêm `CatastrophicTrainingError`, `TrainingGateError`, `VictoryGateError`. |

Không tạo compatibility shim cho checkpoint/bundle v4. Loader phải báo rõ schema không tương thích.

---

### 1.2. Model scoring

| File | Symbol | Thay đổi chính xác |
|---|---|---|
| [wide_layer.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/wide_layer.py) | `WideLayer.__init__` | Đổi network thành `Linear(3,16) → ReLU → Linear(16,1)`; bỏ `Softplus`. |
| [wide_layer.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/wide_layer.py) | `WideLayer.__init__` | `nn.init.zeros_()` cho cả weight và bias của final linear. |
| [wide_layer.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/wide_layer.py) | `score_unchecked` | Giữ `torch.where(rule_present, scores, 0)` để no-rule score chính xác bằng 0. |
| [two_tower_wide_deep.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/two_tower_wide_deep.py) | Mới: `ScoreBreakdown` | Dataclass chứa `deep_logits`, `wide_logits`, `hybrid_logits`. |
| [two_tower_wide_deep.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/two_tower_wide_deep.py) | `fuse_scores` | Chỉ còn `return deep + wide`; xóa Wide scale buffer. |
| [two_tower_wide_deep.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/two_tower_wide_deep.py) | Mới: `score_breakdown` | Tính ba nhóm logits tại một chỗ; đây là seam chung cho trainer/evaluator/export. |
| [two_tower_wide_deep.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/two_tower_wide_deep.py) | `score_cached` | Gọi `score_breakdown`, sau đó chọn tensor theo `ModelVariant`; không lặp fusion logic. |
| [two_tower_wide_deep.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/two_tower_wide_deep.py) | `forward` | Giữ tensor output để ONNX export; mặc định trả Hybrid logits. |
| [cascade.py](E:/UIT/cv/backend/ai-service/src/ai_service/models/cascade.py) | Toàn file | Xóa file sau khi mọi caller/test đã được loại bỏ. |

Bất biến bắt buộc:

```text
Initial WideLogit == 0
NoRule WideLogit == 0
HybridLogit == DeepLogit + WideLogit
Cold item không có scoring branch riêng
```

---

### 1.3. Rule artifact và dữ liệu batch

| File | Symbol | Thay đổi chính xác |
|---|---|---|
| [rules.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/rules.py) | `RuleStore.batch_promotion_strength` | Xóa method; không còn post-hoc promotion. |
| [rules.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/rules.py) | Mới: `batch_raw_lift` | Trả raw lift `[B,C]` và presence mask; chỉ dùng cho Apriori-only baseline. |
| [rules.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/rules.py) | `load_rule_artifact` | Nếu artifact thiếu năm statistics arrays, trả legacy capability chỉ cho audit; train Hybrid phải reject. |
| [rules.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/rules.py) | `AprioriRuleMiner.mine` | Ghi `feature_schema_version` và `has_full_statistics=true`. |
| [dataset.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/dataset.py) | `PurchaseTrainingIndex` | Thêm `context_items: np.ndarray[N]`. |
| [dataset.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/dataset.py) | `build_purchase_training_index` | Khi emit purchase target, lưu last strictly-earlier purchase làm context; first purchase dùng `-1`. |
| [dataset.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/dataset.py) | `PurchaseBatch` | Thêm bốn tensors Wide cho in-batch và explicit candidates. |
| [dataset.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/dataset.py) | `PurchaseBatchIterator.__init__` | Nhận thêm `rule_store`; iterator chịu trách nhiệm lookup Wide features. |
| [dataset.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/dataset.py) | `PurchaseBatchIterator.__iter__` | Tạo `[B,B,3]` features cho in-batch positives và `[B,R,3]` cho explicit negatives. |
| [dataset.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/dataset.py) | `HybridImplicitDataset` | Giữ cho legacy diagnostic; không dùng trong v4 finalist. |

Cấu trúc `PurchaseBatch` sau thay đổi:

```python
@dataclass(frozen=True)
class PurchaseBatch:
    user_idx: Tensor
    persona_idx: Tensor
    context_item_idx: Tensor
    positive_item_idx: Tensor
    explicit_negative_idx: Tensor
    positive_mask: Tensor
    denominator_mask: Tensor
    confidence: Tensor
    history_item_idx: Tensor
    history_mask: Tensor
    history_age_days: Tensor
    in_batch_wide_values: Tensor
    in_batch_rule_present: Tensor
    explicit_wide_values: Tensor
    explicit_rule_present: Tensor
```

Quy tắc context:

- Chỉ purchase mới cập nhật context.
- Event cùng timestamp không nhìn thấy nhau.
- View không trở thành Apriori context.
- Context không được lấy từ val/test khi train.

---

### 1.4. Objective và trainer

| File | Symbol | Thay đổi chính xác |
|---|---|---|
| [objectives.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/objectives.py) | `multi_positive_sampled_softmax` | Nhận `in_batch_wide_logits` và `explicit_wide_logits`; cộng vào Deep logits trước numerator/denominator. |
| [objectives.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/objectives.py) | `ObjectiveResult` | Thêm Deep/Wide/Hybrid RMS để trainer tích lũy diagnostics. |
| Mới: `training/stopping.py` | `EpochObservation` | Chứa epoch, GAUC, NDCG, HR, elapsed, non-finite reason. |
| Mới: `training/stopping.py` | `StoppingDecision` | Action: `CONTINUE`, `SAVE_BEST`, `STOP_PLATEAU`, `FAILED`, `INTERRUPTED`. |
| Mới: `training/stopping.py` | `EarlyStoppingController` | Sở hữu patience 4, GAUC min-delta, checkpoint tie-break và kill-switch. |
| [trainer.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py) | `Trainer.__init__` | Nhận `training_variant`; optimizer chỉ nhận parameters thực sự dùng. |
| [trainer.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py) | `ValidationEvaluator` | Đổi thành `evaluate_training_epoch(...) -> TrainingValidationPass`. |
| [trainer.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py) | `EpochMetrics` | Thêm Deep/Wide/Hybrid RMS, per-variant HR/NDCG/GAUC, patience và decision reason. |
| [trainer.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py) | `_refresh_model_hard_cache` | Xóa; hard cache được trả về từ validation pass. |
| [trainer.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py) | `fit` | Tách batch forward thành private `_train_purchase_batch`; không để một method gần 1.000 dòng. |
| [trainer.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py) | `fit` | Gọi `EarlyStoppingController.observe()` sau mỗi exact validation pass. |
| [wide_calibration.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/wide_calibration.py) | Toàn file | Xóa sau khi pipeline không còn import. |

Objective mới:

```python
in_batch_deep = user_vectors @ positive_vectors.T / temperature
explicit_deep = einsum(user_vectors, negative_vectors) / temperature

in_batch_hybrid = in_batch_deep + in_batch_wide_logits
explicit_hybrid = explicit_deep + explicit_wide_logits
```

Deep-only run:

```python
in_batch_wide_logits = zeros_like(in_batch_deep)
explicit_wide_logits = zeros_like(explicit_deep)
```

Hybrid run:

```python
in_batch_wide_logits = model.wide_layer(...)
explicit_wide_logits = model.wide_layer(...)
```

Auxiliary view loss:

- Gọi cùng objective với Wide tensors bằng 0.
- Không cập nhật Wide từ view-only events.

---

## 2. Early-stopping implementation chính xác

### 2.1. `EarlyStoppingController`

State:

```python
best_gauc = -inf
best_ndcg = -inf
best_hr = -inf
best_epoch = 0
epochs_without_gauc_improvement = 0
```

Thứ tự xử lý mỗi epoch:

1. Nếu có non-finite signal: trả `FAILED`.
2. Nếu `val_gauc < 0.50`: trả `FAILED_GAUC_BELOW_RANDOM`.
3. Nếu wall time vượt giới hạn: trả `INTERRUPTED_RESOURCE_LIMIT`.
4. Nếu `val_gauc > best_gauc + 1e-4`:
   - cập nhật toàn bộ best metrics;
   - reset patience về 0;
   - trả `SAVE_BEST`.
5. Nếu `abs(val_gauc-best_gauc) <= 1e-4`:
   - tăng patience;
   - nếu NDCG tốt hơn best, hoặc NDCG tie và HR tốt hơn, trả `SAVE_BEST_TIE`;
   - không reset patience.
6. Nếu GAUC giảm: tăng patience.
7. Khi patience đạt 4: trả `STOP_PLATEAU`.

Ví dụ bắt buộc:

```text
Best tại epoch 1
Epoch 2,3,4,5 không tăng GAUC >1e-4
→ stop sau validation epoch 5
```

### 2.2. Non-finite checks

Trong `Trainer` kiểm tra tại các điểm:

- Sau Deep/Wide/Hybrid logits.
- Sau objective loss.
- Sau backward và trước clipping.
- Sau optimizer step trên model parameters.
- Sau validation metrics.

Reason codes được ghi vào:

- `run-manifest.json`
- `training/summary.json`
- dòng cuối `training/history.jsonl`

### 2.3. Wall time

- Kiểm tra tại đầu mỗi batch.
- Không ghi checkpoint giữa batch.
- Nếu vượt giới hạn, giữ `last.pt` của epoch hoàn chỉnh trước đó.
- Chuyển lifecycle sang `INTERRUPTED`, không `FAILED`.
- Không cộng thời gian validation hai lần khi resume.

---

## 3. Evaluation và baseline thay đổi theo file

### 3.1. Exact streaming evaluator

Trong [full_catalog.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/full_catalog.py):

Tạo types:

```python
@dataclass(frozen=True)
class PreparedEvaluationSplit:
    user_ids: np.ndarray
    truth_by_user: dict[int, np.ndarray]
    seen_by_user: dict[int, np.ndarray]
    contexts: np.ndarray
    personas: np.ndarray
    raw_product_ids: np.ndarray

@dataclass(frozen=True)
class TrainingValidationPass:
    variants: dict[ModelVariant, EvaluationResult]
    model_hard_cache: np.ndarray
```

Thay đổi methods:

- `_history_and_truth` đổi thành `_prepare_split`, chạy một lần.
- `evaluate_variants`:
  - Không tạo `scores_by_variant: dict[user, score_vector]`.
  - Preallocate per-user HR/NDCG/GAUC arrays.
  - Xử lý `validation_user_batch_size` users/lần.
  - Với mỗi batch, tính `ScoreBreakdown` một lần.
  - Mask seen items trước metric.
  - Ghi top-k và per-user metrics ngay.
  - Trích top Deep negatives cho hard cache.
- `evaluate_scores` giữ lại cho non-neural baselines nhưng phải dùng cùng `PreparedEvaluationSplit`.

Cold override cần xóa chính xác đoạn:

```python
logits[row_index, cold_candidates] = semantic_similarity / tau
```

Noisy Hybrid cần thay đoạn Gaussian noise bằng:

1. Chọn đúng 10% eligible users qua deterministic hash của `(seed,user_id)`.
2. Chỉ các user được chọn mới đổi persona.
3. Persona mới luôn khác persona gốc.
4. Re-encode user bằng persona đã swap.
5. Không thêm Gaussian vào scores.

### 3.2. Baselines

Trong [baselines.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/baselines.py):

Đổi interface:

```python
run_seven_way_baselines(
    *,
    hybrid_model: HybridTwoTowerModel,
    deep_model: HybridTwoTowerModel,
    ...
) -> BaselineComparisonReport
```

Chi tiết từng baseline:

- **Apriori-only**
  - Context: latest strictly-earlier organic purchase.
  - Score: raw lift.
  - No rule: 0.
  - Không gọi learned Wide MLP.
- **SBERT centroid**
  - Chỉ organic purchase history.
  - Normalize từng item vector và centroid.
- **Item-Item CF**
  - Co-occurrence matrix chỉ từ organic train purchases.
  - Khi evaluate test, user profile có thể dùng organic train+val purchases.
- **Deep-only**
  - Dùng independent Deep checkpoint.
- **Hybrid**
  - Dùng independent Hybrid checkpoint.
- **Noisy Hybrid**
  - Dùng deterministic 10% persona swap.
- **Random**
  - 10 deterministic seeds, average theo user.

Không dùng `snapshot.train_df` thô ở baseline; mọi frame phải đi qua `filter_event_origin(..., "organic")`.

---

## 4. Cold parity và semantic-trap implementation

### 4.1. Cold parity

Trong [cold_start.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/cold_start.py):

Giữ `evaluate_cold_start` để báo HR/NDCG cohort, đồng thời thêm:

```python
evaluate_cold_parity(
    hybrid_model,
    snapshot,
    embeddings,
    rule_store,
    device,
) -> ColdParityReport
```

Quan trọng: parity so sánh hai variants trên cùng Hybrid checkpoint:

```text
Hybrid checkpoint + ModelVariant.HYBRID
Hybrid checkpoint + ModelVariant.DEEP_ONLY
```

Không dùng independent Deep checkpoint cho phép so sánh này vì Deep weights khác sau khi train độc lập.

Cách tính:

1. Lấy 250 cold product IDs từ snapshot partition.
2. Kiểm tra không có row hoặc column nào trong Apriori CSR.
3. Lấy 250 cold cohort users và history trước test.
4. Score toàn bộ cold candidates cho cohort users.
5. Tính:
   - `max_abs_wide_logit`
   - `max_abs_hybrid_minus_deep`
   - cold-only order equality
   - Deep/Hybrid cold-only HR/NDCG
6. Gate:
   - Wide `<=1e-7`
   - Hybrid–Deep `<=1e-6`
   - order equality `true`

### 4.2. Semantic traps

Trong [semantic_traps.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/semantic_traps.py):

Đổi interface:

```python
evaluate_semantic_traps(
    hybrid_model,
    deep_model,
    ...
) -> SemanticTrapReport
```

`TrapResult` đổi fields:

```python
deep_control_rank
hybrid_deep_ablation_rank
hybrid_rank
passed_top_k
improved_over_deep
passed
```

Cách score:

- `deep_control_rank`: independent Deep checkpoint.
- `hybrid_deep_ablation_rank`: Deep branch của Hybrid checkpoint, diagnostic.
- `hybrid_rank`: additive Hybrid score.
- Không gọi cascade promotion.

Một trap pass chỉ khi:

```text
hybrid_rank <= 10
hybrid_rank < deep_control_rank
```

Report toàn cục pass khi đúng 10/10.

---

## 5. Victory gate implementation cụ thể

Tạo file mới:

[ai_service/evaluation/gates.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/gates.py)

### 5.1. `evaluate_single_seed`

Inputs:

```python
@dataclass(frozen=True)
class SingleSeedGateInputs:
    comparison: BaselineComparisonReport
    cold_parity: ColdParityReport
    semantic_traps: SemanticTrapReport
```

Logic:

1. Random GAUC:
   - mean trong `[0.48,0.52]`
   - CI delta-from-0.5 chứa 0.
2. Hybrid GAUC:
   - `>=0.75`.
3. HR domination:
   - Tìm baseline có mean HR cao nhất trong sáu baseline còn lại.
   - `Hybrid mean HR > strongest mean HR`.
   - Paired-bootstrap HR lower bound `>0`.
4. Relative NDCG:
   - So với Apriori-only.
   - `Hybrid mean NDCG > Apriori mean NDCG`.
   - Paired-bootstrap lower bound `>0`.
5. Semantic traps 10/10.
6. Cold parity pass.

Output `VictoryMatrix` phải chứa từng gate, baseline name, mean, delta và CI. Không chỉ trả boolean.

### 5.2. `evaluate_three_seed`

Trong [release.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/release.py):

- Loại toàn bộ gate computation hiện tại.
- `release.py` chỉ:
  - load artifacts;
  - validate lineage/signatures;
  - gọi `evaluate_three_seed`;
  - ghi release artifact;
  - transition lifecycle.

Aggregate algorithm:

```text
per_user_mean = mean(metric_across_3_seeds, axis=seed)
bootstrap(per_user_mean_hybrid - per_user_mean_baseline)
```

Điều kiện:

- Đúng ba Hybrid runs và ba Deep runs.
- Seeds đúng `{42,2027,31415}`.
- Mỗi Hybrid run đã pass single-seed test matrix.
- Mỗi Hybrid run paired đúng Deep run cùng seed.
- Cùng comparison signature và lineage.
- Aggregate lặp lại GAUC, HR, NDCG gates.
- NDCG không yêu cầu hơn Deep.
- Chọn Hybrid run theo validation GAUC; tie bằng NDCG rồi HR.

---

## 6. Pipeline, CLI và lifecycle theo file

### 6.1. CLI

Trong [cli.py](E:/UIT/cv/backend/ai-service/src/ai_service/cli.py):

Sửa arguments:

```text
train:
  --run-id
  --variant deep_only|hybrid

evaluate:
  --split val|test
  --hybrid-run-id
  --deep-run-id

release-gate:
  --hybrid-run-ids H1 H2 H3
  --deep-run-ids D1 D2 D3
```

Bỏ `--run-id` khỏi `evaluate` để tránh nhầm single-model evaluation với paired benchmark.

`run-all`:

- Chỉ là smoke command.
- Không được test, seal hoặc export.
- Phải in cảnh báo đây không phải release workflow.

### 6.2. Pipeline state

Trong [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py):

`PipelineState` đổi thành:

```python
@dataclass(frozen=True)
class PipelineState:
    run_id: str
    training_variant: TrainingVariant
    snapshot_id: str
    embedding_path: str
    rule_path: str
    checkpoint_path: str | None = None
    paired_run_id: str | None = None
    validation_gate_passed: bool = False
    test_gate_passed: bool = False
    victory_matrix_path: str | None = None
    bundle_path: str | None = None
```

Refactor functions:

- `_train`: không chạy `WideCalibrator`; save checkpoint trực tiếp từ best Joint model.
- `_comparison_gates`: xóa; logic chuyển sang `evaluation/gates.py`.
- `_evaluate`: đổi thành `_evaluate_pair`.
- `_evaluate_pair`:
  1. Load Hybrid state/model.
  2. Load Deep state/model.
  3. Validate same seed/lineage/comparison signature.
  4. Chạy seven-way benchmark.
  5. Chạy cold parity.
  6. Chạy semantic traps.
  7. Chạy Victory Matrix.
  8. Ghi `evaluation/<split>/`.
- `_export`: chỉ nhận Hybrid run đã:
  - pass validation;
  - pass test;
  - được selected trong aggregate release gate;
  - có victory matrix SHA đúng.
- `_load_lineage`: instantiate model theo `training_variant`.

Artifacts cho mỗi split:

```text
runs/<run-id>/evaluation/val/report.json
runs/<run-id>/evaluation/val/per-user-metrics.npz
runs/<run-id>/evaluation/val/victory-matrix.json

runs/<run-id>/evaluation/test/report.json
runs/<run-id>/evaluation/test/per-user-metrics.npz
runs/<run-id>/evaluation/test/victory-matrix.json
```

### 6.3. Lifecycle

Trong [run.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/run.py):

Transitions mới:

```text
STAGING → TRAINING | INTERRUPTED | FAILED
TRAINING → INTERRUPTED | FAILED | EVALUATED
INTERRUPTED → TRAINING | FAILED
EVALUATED → FAILED | SEALED
FAILED → none
SEALED → none
```

- Plateau early stop vẫn là training thành công, không phải failure.
- Validation/test gate fail chuyển `FAILED`.
- Catastrophic kill chuyển `FAILED`.
- External/resource interruption chuyển `INTERRUPTED`.

---

## 7. Export và serving theo file

| File | Thay đổi |
|---|---|
| [onnx.py](E:/UIT/cv/backend/ai-service/src/ai_service/export/onnx.py) | `RankerGraph.forward` chỉ gọi additive scoring; không export cascade/cold logic. |
| [parity.py](E:/UIT/cv/backend/ai-service/src/ai_service/export/parity.py) | Xóa semantic overwrite và `promote_high_confidence_rules`; thêm cold/no-rule/strong-rule parity batches. |
| [bundle.py](E:/UIT/cv/backend/ai-service/src/ai_service/export/bundle.py) | Bỏ `semantic_vectors` argument/file; normalization chỉ còn `tau`; thêm victory matrix checksum. |
| [runtime.py](E:/UIT/cv/backend/ai-service/src/ai_service/serving/runtime.py) | Xóa `semantic_vectors`, `cold_items`, `cascade_min_*`, `promotion_strength`. |
| [runtime.py](E:/UIT/cv/backend/ai-service/src/ai_service/serving/runtime.py) | `recommend` chỉ lookup Wide features → ONNX ranker → deterministic sort. |
| [runtime.py](E:/UIT/cv/backend/ai-service/src/ai_service/serving/runtime.py) | Giữ HTTP response như cũ; `ai_score` là raw additive logit. |

`RecommenderRuntime.recommend` sau sửa:

```text
validate request
→ map IDs
→ lookup rule features
→ ONNX ranker
→ lexsort by (-logit, raw_product_id)
→ response
```

Không có bước chỉnh score sau ONNX.

---

## 8. Cấu hình ablation cụ thể

### `configs/ablations/v3.toml`

```toml
[model]
use_item_id_residual = true

[train]
training_variant = "deep_only"
objective = "sampled_softmax"
explicit_negative_ratio = 16
use_history_profiles = true
view_auxiliary_weight = 0.1
early_stopping_patience = 4
min_delta = 0.0001
```

### `configs/ablations/v4.toml`

```toml
[model]
use_item_id_residual = true

[train]
training_variant = "hybrid"
objective = "sampled_softmax"
explicit_negative_ratio = 16
use_history_profiles = true
view_auxiliary_weight = 0.1
early_stopping_patience = 4
min_delta = 0.0001
```

V3 và V4 phải giống nhau ở mọi field ngoại trừ `training_variant`.

V0–V2:

- Dùng `training_variant="deep_only"`.
- Giữ đúng thứ tự ablation item residual/history/view.

P0–P4:

- Di chuyển mô tả sang phần historical diagnostics trong README.
- Bỏ obsolete wide-calibration fields để config vẫn parse được.
- Không được dùng làm finalist hoặc paired Deep control.

---

## 9. Test change map cụ thể

| Test file | Test cần thêm/sửa |
|---|---|
| [test_model_metrics_contracts.py](E:/UIT/cv/backend/ai-service/tests/unit/test_model_metrics_contracts.py) | Wide initial output bằng 0; additive identity; no-rule mask; xóa cascade/scale tests. |
| [test_purchase_objective_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_purchase_objective_contract.py) | Strict context, Wide batch shapes, additive numerator/denominator, Deep-only zeros. |
| Mới: `tests/unit/test_stopping_contract.py` | GAUC patience 4, tie checkpoint, GAUC<0.5, non-finite, wall clock. |
| [test_trainer_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_trainer_contract.py) | Joint gradients, RMS logs, hard cache reuse, independent variants, stop reasons. |
| [test_full_catalog_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_full_catalog_contract.py) | Cold override reproducer, streaming/reference parity, exact ties, persona-swap 10%. |
| [test_release_gate_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_release_gate_contract.py) | HR strongest-baseline gate, NDCG-vs-Apriori gate, GAUC floor, 3+3 paired runs. |
| [test_pipeline_cli_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_pipeline_cli_contract.py) | New CLI arguments, paired evaluation, split directories, state transitions. |
| [test_checkpoint_report_and_trap_contracts.py](E:/UIT/cv/backend/ai-service/tests/unit/test_checkpoint_report_and_trap_contracts.py) | Independent Deep trap rank, Hybrid 10/10 contract. |
| [test_onnx_runtime_contract.py](E:/UIT/cv/backend/ai-service/tests/integration/test_onnx_runtime_contract.py) | Xóa assertion cold score `1/tau`; thay bằng PyTorch=ONNX=runtime additive parity. |
| [test_production_contracts.py](E:/UIT/cv/backend/ai-service/tests/acceptance/test_production_contracts.py) | Legacy rule reject, bundle schema v5, no post-ONNX score mutation. |

Bắt buộc viết regression test trước implementation của phase tương ứng.

---

## 10. Thứ tự triển khai không được đảo

### Phase A — Contracts và red tests

Files:

```text
contracts.py
config.py
errors.py
test_model_metrics_contracts.py
test_full_catalog_contract.py
test_stopping_contract.py
```

Exit gate:

- Regression tests đỏ vì cold override/zero-init/stopping chưa sửa.
- Config schema v5 parse thành công.

### Phase B — Model scoring

Files:

```text
wide_layer.py
two_tower_wide_deep.py
cascade.py (xóa)
wide_calibration.py (chưa xóa cho đến khi pipeline hết import)
```

Exit gate:

- Zero-init/additive/cold unit tests xanh.
- `rg` không còn caller của cascade.

### Phase C — Joint training data/objective

Files:

```text
rules.py
dataset.py
objectives.py
trainer.py
```

Exit gate:

- Joint Wide gradient test xanh.
- Deep-only không có Wide gradient.
- Purchase contexts không leak cùng timestamp/future.

### Phase D — Stopping và lifecycle

Files:

```text
training/stopping.py
trainer.py
run.py
errors.py
```

Exit gate:

- Patience 4 deterministic.
- Catastrophic failures chuyển `FAILED`.
- Wall limit chuyển `INTERRUPTED`.

### Phase E — Streaming evaluator và baselines

Files:

```text
full_catalog.py
baselines.py
sampling.py
trainer.py
```

Exit gate:

- Exact metric parity.
- Một validation pass/epoch.
- Không còn full-score dictionary hoặc second hard-cache forward.

### Phase F — Victory Matrix

Files:

```text
cold_start.py
semantic_traps.py
evaluation/gates.py
release.py
report.py
```

Exit gate:

- Tất cả single/three-seed gate tests xanh.
- Failure report chỉ rõ gate và CI.

### Phase G — Orchestration

Files:

```text
cli.py
pipeline.py
run.py
configs/ablations/*.toml
configs/ablations/README.md
```

Exit gate:

- Deep/Hybrid pair validation chạy bằng fixture.
- Test split không thể chạy trước validation pass.
- Export không thể chạy trước aggregate release.

### Phase H — ONNX và serving

Files:

```text
export/onnx.py
export/parity.py
export/bundle.py
serving/runtime.py
```

Sau khi pipeline hết import, xóa:

```text
training/wide_calibration.py
models/cascade.py
```

Exit gate:

- PyTorch/ONNX/runtime max error `<=1e-5`.
- Không có cold/cascade post-processing.

### Phase I — Thí nghiệm thật

1. Audit/probe frozen snapshot.
2. Train V3 Deep seed 42.
3. Train V4 Hybrid seed 42.
4. Validation Victory Matrix.
5. Nếu fail: dừng, không mở test.
6. Nếu pass: train V3/V4 seeds 2027 và 31415.
7. Aggregate validation.
8. Freeze signatures.
9. Mở test cho sáu runs.
10. Aggregate test.
11. Seal selected Hybrid.
12. Export/verify bundle.
13. Serving benchmark.
14. Cập nhật `report.md` và `experimental_log.md` từ artifacts.

---

## 11. Definition of done

Implementation chỉ hoàn thành khi đồng thời đúng:

- Joint Hybrid Wide bắt đầu bằng 0 và nhận gradient từ epoch 1.
- Không còn Softplus, Wide scale, separate calibration, cascade hoặc cold override.
- Deep baseline được train độc lập.
- Early stopping dùng GAUC, patience 4, không phụ thuộc learning rate.
- GAUC `<0.50` hoặc NaN/Inf dừng ngay và đặt `FAILED`.
- Random GAUC trong `0.50±0.02`.
- Hybrid GAUC `>=0.75`.
- Hybrid HR@10 cao nhất bảy variants với paired CI lower bound `>0`.
- Hybrid NDCG@10 cao hơn Apriori-only với paired CI lower bound `>0`.
- Semantic traps đạt 10/10 và Hybrid rank tốt hơn independent Deep từng trap.
- Cold Wide logit `<=1e-7`; Hybrid–Deep ablation difference `<=1e-6`.
- Full-catalog evaluation exact, streaming và không duplicate hard-cache pass.
- PyTorch/ONNX/runtime parity `<=1e-5`.
- Ruff, mypy, full pytest và coverage `>=85%` đều pass.
- Chỉ selected Hybrid run vượt aggregate three-seed test gate mới được seal/export.
