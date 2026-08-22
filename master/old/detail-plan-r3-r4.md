# Detail plan còn lại — đóng lỗi Lineage v5 và mở R4 an toàn

## 1. Kết luận kiểm duyệt

Trạng thái thực tế:

```text
SOURCE_IMPLEMENTATION_IN_PROGRESS
SOURCE_QUALITY_GATE_FAIL
SNAPSHOT_LINEAGE_V5_FAIL
R4_DIAGNOSTIC_BLOCKED
PRODUCTION_TRAINING_BLOCKED
Hybrid victory not established
```

Validation hiện tại:

| Gate | Kết quả |
|---|---:|
| HEAD/upstream | `31d8092554119aa7d1ba22db2e094d701ba83c29`, đồng bộ `0/0` |
| Worktree | Dirty, 22 modified + 7 untracked |
| Node seed-product | 15 passed |
| Targeted R3/Snapshot tests | 92 passed |
| Full Python suite | 482 passed, 2 skipped, **1 failed** |
| Ruff format | **FAIL**, 9 files |
| Ruff lint | **FAIL**, 17 lỗi |
| Mypy | **FAIL**, 26 lỗi trong 3 files |
| `git diff --check` | PASS, chỉ cảnh báo line ending |
| Branch coverage | Chưa hợp lệ để nghiệm thu vì full suite fail |

### Quyết định rollback

Không rollback về `31d8092` hoặc `f96a247`.

Các thay đổi hiện tại đã đóng đúng nhiều vấn đề quan trọng:

- Canonical benchmark spec tương thích Node/Python.
- Snapshot temporary directory được verify trước atomic rename.
- Typed semantic cohort và all-target aggregation đã hình thành.
- Promotion bắt đầu derive evidence thay vì nhận SHA tự khai.
- Deep candidate `FAILED` có đường đi riêng.
- Preflight dùng shared prepared inputs.

Rollback sẽ mất các cải tiến này nhưng không đưa codebase tới trạng thái R4-ready. Tiếp tục sửa trên nhánh riêng là phương án ít rủi ro hơn.

Trước khi sửa tiếp:

```powershell
git switch -c codex/r3-lineage-repair
```

Giữ nguyên worktree hiện tại; không reset, checkout hoặc xóa thay đổi. Chỉ source-freeze sau khi full gate xanh.

### Hai trục review

Standards: 3 findings; nghiêm trọng nhất là production train chưa bind config hiện hành với promotion receipt.

Spec: 5 findings; nghiêm trọng nhất là semantic cohort builder không thể pair dữ liệu thật và durable artifacts vẫn cho phép lineage legacy/null.

---

## 2. Hardcode audit

### Không phát hiện campaign hardcode trong runtime

Không có các giá trị sau trong `ai-service/src` hoặc `scripts`:

- Snapshot/run ID chiến dịch.
- Commit `f96a247`, `31d8092`.
- Spec/cohort/order SHA chiến dịch.
- Absolute path `E:\UIT\...`.
- Production run IDs `deep-42-v5`/`hybrid-42-v5`.

Các SHA artifact phải tiếp tục được lấy từ manifest/receipt, không bổ sung literal runtime.

### Hardcode hợp lệ nhưng cần gom một chỗ

SBERT revision `a9467ef...` đang lặp tại:

- `config.py`;
- `data/features.py`;
- default của `ModelConfig`.

Giữ đây là pinned dependency, nhưng chỉ để literal một lần trong `config.py`. `features.py` phải dùng `PINNED_SBERT_NAME` và `PINNED_SBERT_REVISION`.

Golden spec SHA `1ace202...` chỉ được phép nằm trong test/documentation, không trong runtime.

### Hardcode policy phải loại bỏ

Các giá trị đang bị lặp ngoài resolved config/spec:

- Dataset transition: `2500`, `.50`, `.40`.
- Absolute metric floors: `.75`, `.15`, `.08`.
- Deep selection floor `.55`.
- Catastrophic floor `.50`.

Quy tắc cuối:

- Dataset values lấy từ `VerifiedBenchmarkSpec`.
- Evaluation/selection values lấy từ resolved `Settings`.
- Catastrophic GAUC `.50` là invariant cố định nhưng phải là một named constant dùng chung, không lặp literal.
- Production APIs không có fallback threshold khi thiếu `Settings`.

Thêm AST contract test để reject trong `src/scripts`:

- Campaign ID hoặc campaign SHA literal.
- Absolute workspace path.
- SHA literal ngoài duy nhất `PINNED_SBERT_REVISION`.
- Không scan fixtures/tests vì golden SHA là evidence hợp lệ.

---

## 3. Phase Q1 — Sửa Snapshot và semantic cohort

### `data/benchmark_spec.py`

Mở rộng `VerifiedBenchmarkSpec` với:

```python
transition_user_count: int
transition_fraction: float
minimum_training_target_rule_rate: float
minimum_val_rule_target_rate: float
num_events: int
num_users: int
num_products: int
split_counts: dict[str, int]
```

Thêm:

```python
def validate_alignment(
    self,
    evidence: DatasetAlignmentEvidence,
) -> None: ...
```

Method đối chiếu evidence với spec; không hard-code `2500/.50/.40`.

Giữ canonicalization hiện tại:

- recursive sorted keys;
- integral float → integer;
- compact UTF-8;
- finite values only.

Golden test phải yêu cầu exact SHA `1ace202...`.

### `contracts.py`

`DatasetAlignmentEvidence` chỉ validate:

- counters/rates có miền hợp lệ;
- aligned không vượt eligible;
- rate khớp numerator/denominator.

Chuyển transition count/fraction/minimum floors sang `VerifiedBenchmarkSpec.validate_alignment()`.

Thêm named constant dùng chung:

```python
CATASTROPHIC_GAUC_FLOOR = 0.50
```

Không lặp literal này trong trainer, stopping, verifier hoặc ablation.

### `data/semantic_cohort.py`

Sửa parser session ID để nhận:

```text
train | val | test
```

Hiện regex chỉ nhận `val|test`, nên TRAIN anchor không bao giờ được lưu và VAL target luôn thiếu anchor.

Pairing cuối:

```text
TRAIN semantic anchor[index] → VAL semantic target[index]
VAL semantic anchor[index]   → TEST semantic target[index]
```

Thêm typed `SemanticSessionIdentity` thay tuple/string parsing rời rạc:

```python
split: Literal["train", "val", "test"]
phase: Literal["anchor", "target"]
index: int
```

Require thêm:

- `event_type == "purchase"`;
- `event_origin == "semantic_trap"`;
- `cohort_id` map đúng trap;
- anchor/target cùng user và trap;
- anchor timestamp trước target;
- target novel trước split;
- exact users/trap lấy từ spec;
- mọi target direction trong spec xuất hiện.

Dùng typed row conversion hoặc `itertuples()` để loại toàn bộ lỗi mypy từ `dict[Hashable, Any]` và `int(object)`.

### `data/snapshot.py`

Trước tạo manifest:

1. Load verified spec.
2. Validate database alignment evidence bằng spec.
3. Build typed semantic cohort.
4. Validate cohort với train/val/test splits.
5. Tính canonical cohort/order hashes.

Giữ publication flow hiện có nhưng bổ sung test crash:

```text
write files
→ fsync files/directory
→ strict-load temporary snapshot
→ verify all hashes/contracts
→ atomic rename
```

Không reuse hoặc sửa snapshot cũ tại chỗ.

### Tests

Cập nhật `test_semantic_cohort_v5.py`:

- Tạo session IDs thực tế giống Node.
- Fixture nhỏ: 10 traps × 1 VAL × 1 TEST.
- Chứng minh TRAIN anchor được pair với VAL target.
- Chứng minh VAL anchor được pair với TEST target.
- Regex cũ phải làm regression test đỏ nếu quay lại.
- Reject wrong event type/origin, unpaired event, wrong trap, missing target direction.

Cập nhật `test_snapshot_contract.py` và `test_snapshot_validation_edges.py`:

- Spec/alignment mismatch.
- Cohort build failure không tạo destination.
- Temporary strict-load failure cleanup.
- Old 8.000-row raw cohort bị reject.
- Exact schema-3 file allowlist.

Exit gate Q1:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_benchmark_spec.py `
  tests\unit\test_semantic_cohort_v5.py `
  tests\unit\test_snapshot_contract.py `
  tests\unit\test_snapshot_validation_edges.py -q
```

---

## 4. Phase Q2 — Strict lineage và loại compatibility paths

### `contracts.py`

Active model/checkpoint/evaluation contracts phải bắt buộc:

```python
lineage: ArtifactLineageV5
```

Áp dụng cho:

- `PipelineState`;
- `CheckpointManifest`;
- `ModelBundleManifest`;
- `AggregateReleaseReport`;
- `DeepAblationReport`;
- `R3DiagnosticReport`;
- paired evaluation manifest;
- promotion report.

`CheckpointManifest.parent_sha256` phải exact sáu keys và bằng `lineage.as_mapping()`.

Xóa duplicate optional fields:

```text
benchmark_spec_sha256
semantic_cohort_sha256
order_metadata_sha256
```

khỏi checkpoint/diagnostic nếu cùng dữ liệu đã nằm trong typed lineage.

`ArtifactLineage` ba field chỉ được tồn tại trong legacy data-audit reader; không được đi vào Trainer, evaluation, release hoặc export.

Synthetic smoke phải tạo deterministic six-field lineage thay vì dùng `None`.

### Các boundary liên quan

Cập nhật:

- `lineage.py`;
- `training/run.py`;
- `training/checkpoint.py`;
- `evaluation/report.py`;
- `evaluation/release.py`;
- `export/bundle.py`.

Mỗi boundary nhận domain object `ArtifactLineageV5`, không nhận generic mapping rồi tự dựng lại.

TEST release phải đối chiếu exact lineage với aggregate VAL trước publication.

### Tests

- PipelineState thiếu lineage bị reject.
- Checkpoint thiếu một trong sáu SHA bị reject.
- Evaluation, release, promotion và bundle tamper từng field.
- Synthetic smoke vẫn strict-load bằng deterministic six-field lineage.
- Static scan không còn active durable model dùng `ArtifactLineage | ArtifactLineageV5 | None`.

---

## 5. Phase Q3 — Promotion, config binding và verifier

### `evaluation/promotion.py`

Thay generic dictionaries bằng typed records:

```python
class PromotionFeatureSelection(BaseModel):
    use_user_id_embedding: bool
    use_price_features: bool

class PromotionTrainingSettings(BaseModel):
    # exact training-only fields được ký
    objective: str
    negative_ratio: int
    explicit_negative_ratio: int
    learning_rate: float
    minimum_learning_rate: float
    weight_decay: float
    max_epochs: int
    early_stopping_patience: int
    min_delta: float
    warmup_fraction: float
    view_auxiliary_weight: float
    rule_auxiliary_weight: float
    rule_hard_negative_count: int
    use_history_profiles: bool
    max_grad_norm: float
    max_history_items: int
    validation_user_batch_size: int
```

Promotion report lưu riêng:

```text
deep_training_settings
hybrid_training_settings
```

Không yêu cầu Deep giống H3b ở training-only knobs:

- Deep production config phải khớp selected Deep diagnostic.
- Hybrid production config phải khớp H3b.
- Hai config chỉ bắt buộc giống data/model/eval semantics, selected feature flags và comparison signature.
- Production mode phải là `r3_feature_selection_mode="fixed"`.
- Selection SHA/run ID vẫn bắt buộc được ghi trong cả hai config.

`deep_selection_report_sha256` phải mang canonical artifact SHA trong report, không dùng file-byte hash với cùng tên field.

### `training/pipeline.py`

Truyền config source path hoặc config file SHA vào `_train()`.

Trước `RunLifecycle.create()`, production train phải đối chiếu:

- current commit;
- exact six-field lineage;
- variant-specific config file SHA;
- typed feature selection;
- variant-specific training settings;
- selected Deep run ID;
- canonical selection artifact SHA;
- comparison signature;
- promotion report path nằm trong artifact root;
- promotion receipt immutable và verified.

Không chỉ kiểm tra commit và lineage như hiện tại.

### `training/run_verifier.py`

Sửa eligibility replay để tính độc lập:

```text
epoch >= diagnostic_warmup_epochs
GAUC >= diagnostic_minimum_gauc
HR >= diagnostic_minimum_hr_at_k
NDCG >= diagnostic_minimum_ndcg_at_k
Hybrid additionally requires checkpoint_guardrails_passed
```

Sau đó mới so với persisted `is_best`. Không được dùng `is_best` làm đầu vào eligibility.

Để chứng minh Deep Wide byte-identical:

- `trainer.py` tính `wide_initial_sha256` trước epoch 1.
- Summary ghi `wide_initial_sha256` và `wide_final_sha256`.
- Verifier tính lại Wide hash từ strict-loaded checkpoint.
- Deep require initial = best = last = final.
- Hybrid require epoch-one gradient `>0` và final hash khác initial.

`verify_training_run.py` chỉ parse CLI và gọi verifier module.

### Tests

- Production config khác đúng một training knob bị reject.
- Deep config không được bị ép dùng H3b rule auxiliary.
- Wrong config file SHA, selection SHA, selected run, feature flags hoặc comparison signature bị reject trước run creation.
- Eligibility replay bắt được `is_best=True` giả.
- Deep Wide thay đổi trước cả best/last bị phát hiện.

---

## 6. Phase Q4 — Cleanup APIs, hardcodes và quality gate

### `evaluation/r3_diagnostics.py`

- Xóa `_target_requests()` compatibility adapter.
- Production và tests gọi `semantic_replay_requests()` với typed snapshot.
- Alpha feasibility dùng:
  - `settings.eval.minimum_gauc`;
  - `settings.eval.minimum_hr_at_k`;
  - `settings.eval.minimum_ndcg_at_k`.
- Không literal `.15/.08`.

Việc này cũng sửa full-suite failure hiện tại trong `test_r3_diagnostics_contract.py`.

### `evaluation/semantic_traps.py`

- `settings` bắt buộc khi chạy serving-equivalent gate.
- Xóa `settings or Settings()`.
- Fixture item-as-query chỉ còn API diagnostic riêng, không chung signature với production gate.

### `evaluation/gates.py`

- `evaluate_single_seed()` bắt buộc `Settings`.
- Xóa fallback `.75/.15/.08/.02/2000`.
- Test phải chứng minh thay đổi resolved threshold làm thay đổi gate evidence.

### `evaluation/ablation.py`

Thêm typed threshold record:

```python
class DeepAblationThresholds(BaseModel):
    minimum_candidate_gauc: float
    selection_gauc_floor: float
    selection_hr_floor: float
    selection_ndcg_floor: float
    gauc_guardrail_delta: float
    hr_guardrail_delta: float
    ndcg_guardrail_delta: float
    bootstrap_samples: int
```

Caller dựng từ resolved `settings.eval`; xóa default `.55/.75/.15/.08`.

Thêm type alias rõ ràng:

```python
DeepAblationCandidate = DeepAblationRun | DeepAblationFailure
```

Không dùng heterogeneous tuple bị mypy suy ra `object`.

### `config.py` và `data/features.py`

- Chỉ để SBERT revision literal tại `PINNED_SBERT_REVISION`.
- Encoder dùng constant/injected config.
- Thêm test đảm bảo manifest ghi đúng resolved model name/revision.

### Static hardcode contract

Tạo `test_no_runtime_campaign_hardcodes.py`:

- AST scan `src` và `scripts`.
- Reject 40/64-hex literal ngoài named pinned dependency.
- Reject `benchmark-v*`, production/diagnostic run IDs và absolute workspace paths.
- Golden artifact SHA trong tests được phép.
- Threshold behavior được kiểm tra bằng settings-driven tests, không dùng AST scan số thực.

### Sửa quality failures hiện tại

- Ruff-format 9 files.
- Xóa unused `Any`.
- Chuyển imports trong tests lên module scope.
- Sửa 26 mypy errors trong:
  - `semantic_cohort.py`;
  - `ablation.py`;
  - `pipeline.py`.
- Xóa stale fixture-path test thay vì thêm compatibility fallback.

---

## 7. Cập nhật `detail-plan-r3-r4.md`

Thay đầu tài liệu bằng receipt thực tế:

```text
Reviewed base HEAD      31d8092554119aa7d1ba22db2e094d701ba83c29
Worktree                implementation in progress
Node                    15 passed
Targeted R3 tests       92 passed
Full Python             482 passed, 2 skipped, 1 failed
Ruff                    FAIL
Mypy                    FAIL
Coverage                 not accepted
R4                       BLOCKED
Production training      BLOCKED
Hybrid victory           not established
```

Xóa các phase đã thực sự hoàn tất khỏi phần “remaining work”, nhưng không mark Snapshot lineage complete trước rebuilt artifact.

Phần còn lại trong tài liệu chỉ giữ:

1. Semantic session parser fix.
2. Strict six-field durable lineage.
3. Production config/promotion binding.
4. Independent run verifier.
5. Full quality gate.
6. Local lineage rebuild.
7. Conditional R4 and production campaign.

Chỉ sau full quality gate mới cập nhật:

```text
R3_SOURCE_READY
R4_LINEAGE_REBUILD_PENDING
PRODUCTION_TRAINING_BLOCKED
```

Không ghi HEAD frozen mới cho tới khi commit/push hoàn tất.

---

## 8. Source exit gate và rebuild

### Full source gate

```powershell
npm.cmd run test:seed-product

.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts

$coverageJson = Join-Path $env:TEMP "ai-service-r3-lineage-final.json"
.\.venv\Scripts\python.exe -m pytest `
  --cov=ai_service --cov-branch `
  --cov-report=term-missing `
  --cov-report=json:$coverageJson `
  --cov-fail-under=85 -q

.\.venv\Scripts\python.exe scripts\check_critical_coverage.py $coverageJson
git diff --check
```

Acceptance:

- Full tests pass.
- Đúng hai fixed-runner skips.
- Global branch coverage `>=85%`.
- Trainer/Pipeline `>=85%`.
- Checkpoint/report/release/bundle `>=90%`.
- Không threshold reduction hoặc coverage exclusion.

Commit/push và require worktree clean, HEAD bằng upstream.

### Rebuild local lineage

Chỉ sau source freeze:

1. Verify database v5 receipt read-only.
2. Không reset/reseed nếu receipt/spec/alignment pass.
3. Purge local artifacts sau dry-run và explicit confirmation.
4. Tạo snapshot ID mới chứa spec-prefix và frozen-commit-prefix.
5. Regenerate real feature và full-stat rule artifacts.
6. Chạy `preflight-r3`.

Require:

```text
events                      823371
users                       5000
items                       5200
orders                      15000
semantic cases              2000
VAL cases/trap              100
TEST cases/trap             100
TRAIN alignment             >= .40
VAL alignment               >= .40
six-field lineage           verified
```

Không so cohort/order SHA mới với hash artifact cũ.

---

## 9. Conditional R4 và training

Chỉ khi rebuilt lineage và preflight pass:

```text
Deep control/no-price/no-user-id/both
→ verified Deep selection
→ Hybrid H0/H1/H2/H3a/H3b
→ H3b absolute + paired + semantic + cold + Wide gates
→ materialize production Deep/Hybrid configs
→ config-only commit
→ verified promotion receipt
→ source freeze lần hai
→ production seed 42
```

H3b vẫn phải đạt:

```text
GAUC >= .75
HR@10 >= .15
NDCG@10 >= .08
paired CI lower > 0 cho strongest baseline ở cả ba metrics
all semantic targets thuộc đủ 10 traps pass
cold parity PASS
strict target readiness PASS
Wide readiness PASS
```

Bất kỳ failure nào giữ `PRODUCTION_TRAINING_BLOCKED`; không chạy seed 2027/31415.

## Assumptions khóa

- Tiếp tục current WIP; không rollback toàn bộ.
- Không compatibility shim cho durable v5 artifacts.
- Không hard-code campaign SHA/run/path trong runtime.
- Pinned model revision là dependency contract hợp lệ nhưng chỉ tồn tại một lần.
- Dataset policy lấy từ verified spec; metric policy lấy từ resolved settings.
- Không purge artifact hoặc chạy GPU trước source exit gate.
