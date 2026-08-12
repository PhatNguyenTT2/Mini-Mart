# Detail plan cập nhật Phase R3–R4 sau code review

## Current implementation receipt (source-only)

The R3-C0 repair is implemented in the working tree and remains blocked on
the final source exit gate. The active path is `configs/diagnostics/r3-v5/`
with four Deep and five Hybrid H0–H3b configurations. Hybrid configs require a
verified Deep selection artifact. Six-field v5 lineage is propagated through
snapshot, run, checkpoint, evaluation, diagnostic and release boundaries;
organic-only rule-pair indexing and rule-hard sampling are enforced; semantic
traps use immutable serving-equivalent cohort replay; checkpoints before the
diagnostic warmup are ineligible; and `diagnostic-stop.json` is immutable.

Current validation receipt: 431 Python tests passed, 2 fixed-runner skips,
global branch coverage 85.01%; all six critical coverage thresholds pass.
Semantic cohort metadata is now snapshot-owned and rule-hard sampling rejects
organic-positive edges. No R3/R4 GPU run, selection artifact, production run,
release, seal or bundle exists. Keep `PRODUCTION_TRAINING_BLOCKED` and `Hybrid
victory not established` until the R3-C1 gate and source freeze pass.

## 1. Kết luận kiểm duyệt

Baseline đã push:

- Frozen HEAD: `ae3bba950e3340e744f59e2890888945ad9df7b0`.
- `HEAD == origin/main`, worktree sạch.
- Python: `399 passed, 2 skipped`.
- Branch coverage: `85.02%`.
- Critical coverage:
  - `checkpoint.py`: 97.24%
  - `report.py`: 90.79%
  - `bundle.py`: 98.79%
  - `release.py`: 90.22%
  - `trainer.py`: 85.21%
  - `pipeline.py`: 85.05%
- Node seed-product: `15 passed`.
- Ruff, mypy và `git diff --check`: PASS.
- Chưa có R3/R4 GPU run hoặc diagnostic artifact.

Trạng thái chính xác:

```text
SOURCE_TOOLING_PASS
R0_R2_DATA_RECEIPT_PASS
R3_R4_CONTRACT_REVIEW_FAIL
R3_GPU_BLOCKED
PRODUCTION_TRAINING_BLOCKED
```

### Standards review

Có 4 finding: 1 P0, 3 P1. Finding nghiêm trọng nhất là toàn bộ Hybrid H0–H3b không thể nhận Deep selection artifact.

- P0: năm Hybrid config thiếu `r3_feature_selection_mode="selection_artifact"`.
- P1: lineage v5 chưa được truyền fail-closed qua run/checkpoint/report/release/bundle.
- P1: `diagnostic-stop.json` có thể bị overwrite.
- P1: ablation README dẫn tới plan không tồn tại và mô tả sai R4 ladder.

### Spec review

Có 5 finding chính: 2 P0, 3 P1. Finding nghiêm trọng nhất là R4 hiện không thể pair selected Deep với Hybrid vì comparison signature không tương thích.

- P0: selection receipt và training-only knobs đang làm lệch comparison signature.
- P0: semantic gate có thể pass khi chỉ một target trong trap đạt top 10.
- P1: checkpoint trước warmup có thể được chọn làm best.
- P1: diagnostic đang hash source spec/fixture thay vì immutable snapshot lineage.
- P1: ablation caller không truyền guardrail thresholds từ resolved settings.

### Finding bổ sung bắt buộc sửa

`rule_hard` hiện đang lấy organic neighbors làm negative. Điều này đảo ngược contract: candidate có organic edge với anchor đang bị gán nhãn negative.

Không chạy R3 GPU job trước khi toàn bộ Phase R3-C0 và R3-C1 bên dưới xanh.

---

## 2. Phase R3-C0 — Đóng source blockers

### C0.1 — Selection artifact và comparison signature

Files:

- `ai-service/src/ai_service/config.py`
- `ai-service/src/ai_service/training/pipeline.py`
- `ai-service/src/ai_service/evaluation/ablation.py`
- `ai-service/configs/diagnostics/r3-v5/*.toml`

Thực hiện:

1. Chuyển thư mục config v5 chính thức về:

```text
configs/diagnostics/r3-v5/
```

2. Giữ đúng bốn Deep configs và năm Hybrid configs H0–H3b.

3. Tất cả Hybrid configs đặt:

```toml
r3_feature_selection_mode = "selection_artifact"
```

4. Pipeline verified-load selection report trước khi dựng model, sau đó materialize chính xác:

```text
include_user_id
include_price
selected_deep_run_id
selection_report_sha256
```

5. Không cho Hybrid config tự khai báo feature flags trái selection report.

6. Phân tách signature:

- Training signature tiếp tục bind toàn bộ config, selection SHA và objective settings.
- Comparison signature chỉ bind:
  - evaluation protocol;
  - model dimensions;
  - selected feature flags;
  - dataset/rule semantics;
  - metric thresholds.
- Loại khỏi comparison signature:
  - seed;
  - variant;
  - rule auxiliary weight;
  - rule-hard count;
  - view auxiliary weight;
  - selection path/SHA;
  - các training-only knobs.

7. `_evaluate_pair()` xác minh riêng:

- Hybrid selection report trỏ đúng Deep run;
- selected feature flags khớp cả hai models;
- lineage và source commit giống nhau;
- comparison signature giống nhau.

8. `compare_deep_ablations()` phải nhận guardrails từ `settings.eval`, không dùng default `0.0`.

9. Candidate catastrophic chỉ làm candidate đó ineligible. Chỉ publish diagnostic pause nếu control/random integrity fail hoặc không còn candidate eligible.

Validation:

- H0–H3b load được selection report.
- Selected Deep và cả năm Hybrid có cùng comparison signature.
- Năm Hybrid vẫn có training signatures khác nhau.
- Selection report sai run, SHA, flags hoặc lineage bị reject trước run creation.

---

### C0.2 — Sửa RulePairIndex và rule-hard sampling

Files:

- `ai-service/src/ai_service/data/dataset.py`
- `ai-service/src/ai_service/data/sampling.py`
- `ai-service/src/ai_service/training/objectives.py`
- `ai-service/src/ai_service/training/trainer.py`

Thực hiện:

1. `RulePairIndex` chỉ dựng positive edges từ `snapshot.order_baskets_df`:

```text
benchmark_kind == organic
group by order_id
exclude semantic-trap baskets
directed item pairs within each organic basket
```

Không dựng positive edges từ view/click hoặc nhóm sự kiện theo timestamp.

2. Tạo `RuleHardIndex`:

```text
RuleStore adjacency
- organic positive edges
- protected semantic-trap edges
- seen items
- cold items
```

3. Thêm typed contract:

```python
@dataclass(frozen=True)
class MixedNegativeBatch:
    item_ids: np.ndarray
    source_tags: np.ndarray
    rule_hard_mask: np.ndarray
```

4. `MixedNegativeSampler.sample()` trả `MixedNegativeBatch`, không giữ API production trả bare ndarray.

5. Khi config yêu cầu bốn rule-hard negatives:

- exact `4/16`;
- warm, unseen, unique;
- RuleStore có edge với context để tạo Wide pressure;
- tuyệt đối không có organic positive edge;
- không thuộc protected semantic pair;
- thiếu quota phải fail, không fallback random.

6. `PurchaseBatch` mang source tags/mask tới Trainer.

7. Rule auxiliary negative chỉ dùng:

```python
rule_hard_mask & rule_present
```

8. Diagnostics phải ghi:

- positive organic edge rate;
- rule-hard rate;
- false-negative count;
- rule-positive và rule-negative Wide quantiles;
- Wide margin;
- gradient norm riêng từ main loss và rule loss.

Validation:

- Regression test chứng minh organic neighbor không bao giờ xuất hiện dưới source `rule_hard`.
- View/click cùng timestamp không tạo positive RulePairIndex edge.
- Exact 4/16 quota.
- Không fallback khi quota thiếu.
- Rule loss chỉ truyền gradient vào Wide.
- Deep-only không forward hoặc thay đổi Wide.

---

### C0.3 — Strict v5 lineage xuyên suốt hệ thống

Files chính:

- `contracts.py`
- `data/snapshot.py`
- `training/run.py`
- `training/checkpoint.py`
- `evaluation/report.py`
- `evaluation/ablation.py`
- `evaluation/release.py`
- `export/bundle.py`

Thay lineage dictionary bằng strict immutable type:

```python
class ArtifactLineageV5(BaseModel):
    snapshot: str
    embedding: str
    rules: str
    benchmark_spec: str
    semantic_cohort: str
    order_metadata: str
```

Mọi field là SHA-256 lowercase bắt buộc; không optional và không compatibility shim v4.

`Snapshot` phải publish và verify:

```text
benchmark-spec.json
semantic-cohort.json
order-metadata receipt/hash
```

Snapshot CLI nhận explicit canonical v5 spec path. Trước publication:

1. Canonicalize JSON.
2. Require SHA bằng benchmark run metadata trong database.
3. Publish canonical document vào snapshot.
4. Loader recompute spec/cohort/order hashes.
5. Mutation hoặc missing file phải bị reject.

`ArtifactLineageV5` phải được truyền qua:

```text
RunLifecycle
Checkpoint payload + manifest
PipelineState
Deep ablation report
R3 diagnostic report
Paired evaluation report
Aggregate release
Bundle manifest
```

Không được tái dựng lineage bằng các `dict[str, str]` rời rạc.

Validation:

- Spec/cohort/order receipt tamper bị reject ở snapshot loader.
- Run và checkpoint lệch một trong sáu SHA bị reject.
- Deep selection report không bind đủ sáu SHA bị reject.
- Hybrid không thể dùng selection artifact từ lineage khác.
- Evaluation/release/bundle corruption tests bao phủ cả sáu fields.

---

### C0.4 — Semantic cohort serving-equivalent

Files:

- `evaluation/semantic_traps.py`
- `evaluation/full_catalog.py`
- `evaluation/r3_diagnostics.py`

Thêm typed case:

```python
@dataclass(frozen=True)
class SemanticCohortCase:
    trap_id: int
    user_id: int
    anchor_item_id: int
    target_item_id: int
    split: SplitName
```

Runtime evaluator chỉ đọc `snapshot/semantic-cohort.json`; không đọc source fixture.

Mỗi cohort row được đánh giá độc lập:

1. Build history tới anchor.
2. Target phải novel và thuộc target split.
3. Dùng cùng HistoryEncoder/UserTower/profile với full-catalog evaluator.
4. Áp cùng seen/cold masking.
5. Rank theo `(-score, raw_product_id)`.

Per-trap gate chỉ pass khi:

- mọi target case có Hybrid rank `<=10`;
- không case nào xấu hơn independent Deep;
- ít nhất một case cải thiện nghiêm ngặt;
- đủ chính xác 10 trap IDs.

Không collapse multi-target trap bằng `min(rank)` hoặc chọn một arbitrary user.

Item-as-query chỉ được giữ trong diagnostic evidence; không tham gia Victory gate.

`r3_diagnostics.py` phải:

- lấy spec/cohort hashes từ verified snapshot lineage;
- không hash tracked source fixture;
- validate các duplicate evidence hashes bằng exact lineage;
- dùng resolved `.75/.15/.08` cho alpha/oracle feasibility;
- không promote kết quả alpha sweep.

Validation:

- Trap 2/5/10 fail nếu bất kỳ target nào fail.
- Missing anchor, non-novel target hoặc duplicate cohort row bị reject.
- Mutation source fixture không ảnh hưởng runtime evaluation.
- Mutation snapshot cohort bị loader reject.
- Shared scorer parity với full-catalog evaluator.

---

### C0.5 — Checkpoint eligibility và immutable diagnostic stop

Files:

- `training/trainer.py`
- `training/stopping.py`
- `training/diagnostic_stop.py`
- `artifact_io.py`

Checkpoint trước warmup luôn ineligible:

```text
epoch < diagnostic_warmup_epochs → no best.pt
```

Sau warmup:

- Deep eligible khi pass diagnostic GAUC/HR/NDCG floors.
- Hybrid eligible khi pass floors và Deep/Wide checkpoint guardrails.
- Patience chỉ reset trên eligible improvement.
- Training kết thúc mà `selected_epoch < warmup` hoặc không có selected checkpoint → `DiagnosticQualityError`.

`Trainer.fit()` không tự publish raw JSON. Tách diagnostic quality controller/repository chịu trách nhiệm:

- maxima quan sát;
- eligibility;
- exact failure reasons;
- publication và verified load.

`diagnostic-stop.json`:

- publish bằng `immutable_write_json`;
- reject overwrite;
- chứa schema, canonical artifact SHA, thresholds, observed maxima, selected state, lineage và signatures;
- verified loader recompute canonical SHA.

Validation:

- Epoch 1–2 có GAUC cao không tạo `best.pt`.
- Epoch 3 eligible mới được chọn.
- Không eligible checkpoint tạo immutable stop và lifecycle `FAILED`.
- Concurrent/stale publication không overwrite.
- Tampered stop report bị reject.

---

### C0.6 — Đồng bộ runbook

Files:

- `ai-service/README.md`
- `ai-service/configs/ablations/README.md`
- `master/detail-plan-r3-r4.md`
- `walkthrough.md`

Thực hiện trước source freeze:

- Đánh dấu configs v3/v4 và R3 cũ là non-executable.
- Trỏ duy nhất tới `master/detail-plan-r3-r4.md`.
- Mô tả đầy đủ bốn Deep + H0–H3b.
- Ghi trạng thái:

```text
R3_R4_CONTRACT_REPAIR_IN_PROGRESS
PRODUCTION_TRAINING_BLOCKED
Hybrid victory not established
```

`master-plan.md` giữ nguyên; code/config phải tuân theo path `configs/diagnostics/r3-v5`.

---

## 3. Phase R3-C1 — Source exit gate

Targeted tests bắt buộc:

```text
test_config_contract.py
test_purchase_objective_contract.py
test_rule_readiness_contract.py
test_semantic_trap_contract.py
test_full_catalog_contract.py
test_r3_diagnostics_contract.py
test_ablation_contract.py
test_trainer_contract.py
test_checkpoint_report_and_trap_contracts.py
test_release_gate_contract.py
test_onnx_runtime_contract.py
```

Các scenario bắt buộc:

- Selection artifact materialization và comparison signature parity.
- Wrong selection run/SHA/feature flags/lineage.
- Rule-hard exact 4/16 và không false-negative organic edge.
- Strict six-field lineage corruption.
- Multi-target semantic traps.
- Pre-warmup checkpoint rejection.
- Immutable diagnostic-stop.
- GAUC-only candidate có top-k kém bị reject.
- Candidate riêng lẻ catastrophic không vô hiệu candidate hợp lệ khác.

Full gate:

```powershell
npm.cmd run test:seed-product

.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts

$coverageJson = Join-Path $env:TEMP "ai-service-r3-r4-ready.json"
.\.venv\Scripts\python.exe -m pytest `
  --cov=ai_service --cov-branch `
  --cov-report=term-missing `
  --cov-report=json:$coverageJson `
  --cov-fail-under=85 -q

.\.venv\Scripts\python.exe scripts\check_critical_coverage.py $coverageJson
git diff --check
```

Acceptance:

- Không failure.
- Chỉ đúng hai fixed-runner skips.
- Global branch coverage `>=85%`.
- Trainer/Pipeline `>=85%`.
- Checkpoint/report/release/bundle `>=90%`.
- Không thêm coverage exclusion hoặc giảm threshold.

Sau đó commit/push và require:

```text
worktree clean
HEAD == upstream
ahead/behind = 0/0
```

Chỉ khi đó đổi trạng thái thành:

```text
R3_SOURCE_READY
R4_DIAGNOSTIC_PENDING
PRODUCTION_TRAINING_BLOCKED
```

---

## 4. Phase R4 — Rebuild immutable Python lineage

Không reset/reseed database nếu verified v5 database receipt vẫn giữ:

```text
spec SHA   = 1ace202aaa8f54204ead66ceabe809b3c51795e097dd71c505f07b8367c80bd2
cohort SHA = da59e744fdb4e572be52a5fd1f76daae62fb61685fcc39fa53e0015c60ca30f7
TRAIN rate = 0.436589...
VAL rate   = 0.402146...
```

Do snapshot schema/lineage đã thay đổi, không reuse local snapshot cũ.

Trình tự:

1. Verify database receipt và `inspect-ml-storage`.
2. Purge toàn bộ local artifacts bằng approved purge utility; hiện chưa có R3 runs nên không mất GPU output.
3. Tạo snapshot ID mới:

```text
benchmark-v5-r3-s42-<spec-sha-prefix>-<frozen-commit-prefix>
```

4. Snapshot command phải nhận canonical `benchmark-spec-v5.json`.
5. Regenerate real SBERT features.
6. Regenerate full-stat RuleArtifact v3.
7. Chạy audit, probes và strict rule readiness.

Require:

```text
events                       = 823371
users                        = 5000
items                        = 5200
orders                       = 15000
strict TRAIN target rate     >= .40
strict VAL target rate       >= .40
non-trap directed rules      >= 5000
distinct organic rule items  >= 3000
all semantic target cases    present
six-field lineage verified
```

Không còn local artifact từ snapshot schema cũ.

---

## 5. Phase R4.1 — Deep ablation seed 42

Chạy tuần tự:

```text
diag-v5-deep-control-s42
diag-v5-deep-no-price-s42
diag-v5-deep-no-user-s42
diag-v5-deep-both-s42
```

Mỗi run require:

- same frozen commit và six-field lineage;
- pass target readiness;
- không pre-warmup best;
- có eligible post-warmup checkpoint;
- finite metrics/cache diagnostics;
- không diagnostic stop.

Sau bốn run:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli compare-deep-ablations `
  --control-run-id diag-v5-deep-control-s42 `
  --candidate-run-ids `
    diag-v5-deep-no-price-s42 `
    diag-v5-deep-no-user-s42 `
    diag-v5-deep-both-s42 `
  --device cuda
```

Verified selection report phải:

- bind cả bốn runs, checkpoints và six-field lineage;
- dùng configured guardrails;
- chọn đúng một eligible candidate;
- chứa HR/NDCG/GAUC per-user evidence.

Không eligible candidate → publish diagnostic pause và dừng R4.

---

## 6. Phase R4.2 — Hybrid falsification ladder

Chạy tuần tự với verified Deep selection report:

```text
diag-v5-hybrid-<feature>-h0-s42
diag-v5-hybrid-<feature>-h1-s42
diag-v5-hybrid-<feature>-h2-s42
diag-v5-hybrid-<feature>-h3a-s42
diag-v5-hybrid-<feature>-h3b-s42
```

Mỗi command truyền:

```text
--r3-selection-report <verified-selection-report>
```

Sau mỗi run, evaluate VAL với selected independent Deep.

Dừng toàn bộ R4 nếu:

- selection/lineage/signature mismatch;
- target readiness fail;
- semantic cohort corruption;
- non-finite hoặc GAUC `<.50`;
- epoch-1 Wide/cache invariant fail;
- staged diagnostic stop;
- không có eligible checkpoint.

H0–H3a được phép fail Victory Matrix nhưng phải publish immutable diagnostic evidence trước khi chuyển candidate tiếp theo.

H3b pass khi đồng thời:

```text
GAUC >= .75
HR@10 >= .15
NDCG@10 >= .08
paired CI lower > 0 so với strongest baseline cho cả ba metrics
semantic targets pass toàn bộ 10 traps
cold parity pass
strict target readiness pass
Wide readiness pass
```

Thiếu bất kỳ điều kiện nào:

- dừng R4;
- không train seeds 2027/31415;
- không materialize production configs;
- không seal/export;
- giữ `Hybrid victory not established`.

---

## 7. Phase R4.3 — Promotion và production handoff

Chỉ sau H3b pass:

1. Materialize selected feature flags và H3b objective settings vào:

```text
configs/production/deep.toml
configs/production/hybrid.toml
```

2. Production configs dùng fixed feature flags; không còn dynamic selection mode.

3. Ghi selection report SHA và six-field lineage receipt.

4. Xóa configs v3/v4 và diagnostic R3 cũ theo cleanup policy.

5. Chạy lại full quality gate, corruption tests và CUDA smoke.

6. Commit/push, source-freeze và xác minh production environment/TLS.

Chỉ chuyển trạng thái thành:

```text
READY_FOR_DEEP_42_TRAINING
```

khi:

- H3b pass toàn bộ gates.
- Production configs materialized.
- Worktree sạch và HEAD bằng upstream.
- Production database/TLS preflight pass.
- Sáu production run IDs chưa tồn tại.

Sau đó mới chạy:

```text
Deep 42 → Hybrid 42 → VAL 42
→ Deep/Hybrid 2027 → VAL
→ Deep/Hybrid 31415 → VAL
→ aggregate VAL 3+3
→ TEST cả ba pairs
→ aggregate TEST
→ seal selected Hybrid
→ export/verify bundle
→ ONNX parity
→ fixed-runner benchmark
```

## Assumptions khóa

- `master-plan.md` giữ nguyên và là authority.
- Database v5 không reset/reseed nếu immutable receipt vẫn đúng; chỉ rebuild local Python lineage.
- Hard floors `.75/.15/.08` không được hạ.
- Không compatibility shim v4.
- Không chạy R3/R4 jobs song song trên GPU 6 GB.
- Không sửa tracked files sau source freeze và giữa diagnostic runs.
- Không tuyên bố Hybrid victory trước H3b, aggregate release, bundle và runtime gates.
