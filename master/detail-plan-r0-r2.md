# Detail plan cấp codebase — Phase R0–R2

## 1. Authority, trạng thái và phạm vi khóa

Tài liệu này là kế hoạch triển khai chi tiết cho ba phase đầu của
[master-plan.md](E:/UIT/cv/backend/master/master-plan.md). Master plan là nguồn chân lý
về mục tiêu, threshold và thứ tự campaign; tài liệu này chỉ làm rõ file, interface,
implementation, dependency và validation. Không sửa master plan trong khi triển khai
R0–R2.

Baseline dùng để khóa tài liệu:

```text
repository HEAD       = b5f5d255606685feadd440b6a7ffb084518aea85
master-plan SHA-256   = c3d89d366b9ecbeb49c525c133f6d89ade5e34c8c0a0a279d04fff13bee09287
active dataset        = benchmark v4
active R3 result      = FAIL
production training  = FORBIDDEN
```

Worktree hiện có thao tác tài liệu do người dùng sở hữu:

```text
D  master/detail-plan.md
?? master/master-plan.md
?? master/standard.md
```

Không restore, rename, overwrite hoặc stage các file trên trong R0–R2. File hiện tại
được tạo độc lập tại `master/detail-plan-r0-r2.md`.

### 1.1. Dependency graph bắt buộc

```text
R0 contracts
  -> R0 streaming diagnostic replay
  -> R0 immutable diagnostic artifact
  -> R0 CLI/pipeline read-only command
  -> reproduce v4 failure
  -> R0 PASS

R0 PASS
  -> R1 reset module/tests
  -> R1 local purge module/tests
  -> R2 v5 spec + seed implementation/tests
  -> full R0-R2 source quality gate
  -> destructive DB reset + artifact purge
  -> R1 PASS

R1 PASS
  -> execute the already-validated R2 v5 seed
  -> R2 independent DB validation
  -> publish exactly one ready v5 run
  -> R2 PASS
```

Không thực hiện song song các bước có mũi tên phụ thuộc. Vì reset command dùng canonical
v5 spec, toàn bộ source/tests R0–R2 phải hoàn tất trước R1 destructive execution. Điều
này không đổi runtime phase order: R0 replay vẫn chạy trước, R1 vẫn xóa dữ liệu trước,
và R2 seed chỉ chạy khi R1 postcondition xác nhận database benchmark rỗng.

### 1.2. Ngoài phạm vi R0–R2

Không chỉnh sửa trong tài liệu này:

- `training/trainer.py`, `training/stopping.py`, `training/checkpoint.py`;
- `training/objectives.py`, `data/sampling.py`;
- production semantic Victory Gate;
- R3 neural ablation configs và production configs;
- Deep/Hybrid production runs, lifecycle evaluation, release, seal hoặc bundle.

Các module trên thuộc R3–R4 của master plan. R0 có thể tạo replay serving-equivalent
cho mục đích chẩn đoán nhưng chưa thay gate release đang hoạt động.

## 2. Interfaces được khóa trước implementation

R0–R2 phải tạo ba module sâu, với interface nhỏ và implementation/test tập trung.

### 2.1. R0 diagnostic module

File mới:

- `ai-service/src/ai_service/evaluation/r3_diagnostics.py`.

Interface duy nhất cho caller:

```python
def publish_r3_diagnostic(
    *,
    hybrid_run: LoadedDiagnosticRun,
    deep_run: LoadedDiagnosticRun,
    split: Literal[SplitName.VAL],
    settings: Settings,
    artifact_root: Path,
    device: torch.device,
) -> R3DiagnosticArtifact:
    ...


def load_r3_diagnostic(
    directory: Path,
    *,
    expected_hybrid_run_id: str,
    expected_deep_run_id: str,
    expected_lineage: ArtifactLineage,
    expected_comparison_signature: str,
) -> R3DiagnosticArtifact:
    ...
```

Caller không truyền generic dictionaries, output path hoặc precomputed full-catalog
score dictionaries. Module tự chuẩn bị split, stream scoring, dựng evidence, publish
atomically và verified-load artifact.

### 2.2. R1 reset module

File mới:

- `backend/docs/chatbot/seed-product/reset-benchmark-v5.js`.

Interface test/CLI:

```javascript
async function planBenchmarkReset({ clients, spec }) { ... }
async function executeBenchmarkReset({ clients, spec, confirmation }) { ... }
```

`planBenchmarkReset()` hoàn toàn read-only. `executeBenchmarkReset()` ẩn transaction
ordering, referential checks và idempotent retry. Production adapters là bốn PostgreSQL
clients từ `benchmark-lib.js`; tests dùng recording clients. Không tạo thêm port cho
từng câu SQL.

### 2.3. R2 spec/seed module

File mới:

- `backend/docs/chatbot/seed-product/benchmark-spec.js`.

Interface:

```javascript
function loadBenchmarkSpec(specPath) { ... }
function canonicalSpecSha256(spec) { ... }
```

Mọi seed/reset/inspect command phải đi qua interface này. Không còn validator riêng
trong `seed-ml-benchmark.js` hoặc logic version riêng trong `mock-orders.js`.

## 3. Phase R0 — Immutable root-cause diagnostic

### R0.0 — Khóa baseline và failure reproduction inputs

Không chỉnh sửa artifact v4 trước khi R0 hoàn tất. Resolve read-only và ghi vào test
receipt tạm thời:

- Hybrid run `diag-r3-hybrid-both-s42`;
- selected Deep run `diag-r3-deep-both-s42`;
- exact snapshot, embedding, rules và checkpoint SHA từ hai run manifests;
- exact Git commit của hai runs;
- VAL split và comparison signature.

Precondition:

- hai run cùng commit, seed, lineage và comparison signature;
- lifecycle đủ điều kiện strict-load checkpoint;
- Hybrid checkpoint là `best.pt` và Deep là independent checkpoint;
- v4 artifact chưa bị purge.

Nếu một precondition fail, dừng R0 và không chạy R1.

### R0.1 — Thêm diagnostic artifact contracts

File:

- `ai-service/src/ai_service/contracts.py`.

Thay đổi:

1. Đổi `EVALUATION_SCHEMA_VERSION` từ `5.1.0` thành `5.2.0`.
2. Thêm `R3_DIAGNOSTIC_SCHEMA_VERSION = "1.0.0"` để version diagnostic artifact
   độc lập với model schema `5.0.0`.
3. Thêm các Pydantic models:

```python
class RuleAlignmentEvidence(BaseModel):
    training_targets: int
    strict_training_rule_targets: int
    strict_training_rule_rate: float
    positive_other_rule_hits: int
    in_batch_negative_rule_hits: int
    explicit_negative_rule_hits: int
    negative_only_rows: int
    val_eligible_users: int
    val_rule_aligned_users: int
    val_rule_aligned_rate: float


class CohortMetricDelta(BaseModel):
    cohort_name: Literal["aligned", "unaligned"]
    user_count: int
    hybrid_minus_deep_gauc: float
    hybrid_minus_deep_hr_at_k: float
    hybrid_minus_deep_ndcg_at_k: float


class TrapDiagnosticEvidence(BaseModel):
    trap_id: int
    anchor_raw_id: int
    target_raw_ids: tuple[int, ...]
    anchor_internal_id: int
    target_internal_ids: tuple[int, ...]
    rule_present: tuple[bool, ...]
    raw_lifts: tuple[float, ...]
    item_query_deep_rank: int
    item_query_hybrid_rank: int
    serving_deep_rank: int
    serving_hybrid_rank: int
    deep_top_k_cutoff: float
    learned_wide_bonus: float
    required_wide_bonus: float


class AlphaSweepEvidence(BaseModel):
    alpha: float
    gauc: float
    hr_at_k: float
    ndcg_at_k: float
    meets_absolute_floors: bool


class R3DiagnosticReport(BaseModel):
    schema_version: Literal["1.0.0"]
    evaluation_schema_version: Literal["5.2.0"]
    split: Literal[SplitName.VAL]
    hybrid_run_id: str
    deep_run_id: str
    hybrid_checkpoint_sha256: str
    deep_checkpoint_sha256: str
    git_commit: str
    lineage: ArtifactLineage
    comparison_signature_sha256: str
    benchmark_spec_sha256: str
    semantic_cohort_sha256: str
    rule_alignment: RuleAlignmentEvidence
    cohort_deltas: tuple[CohortMetricDelta, CohortMetricDelta]
    trap_evidence: tuple[TrapDiagnosticEvidence, ...]
    alpha_sweep: tuple[AlphaSweepEvidence, ...]
    per_user_metrics_sha256: str
    artifact_sha256: str
```

Validators:

- mọi count không âm; rate/metric nằm `[0,1]`;
- diagnostic chỉ nhận `VAL`;
- exactly hai cohort records `aligned`, `unaligned`;
- exactly 10 distinct trap IDs `1..10`;
- alpha tuple chính xác `(0, 0.25, 0.5, 1, 2, 4, 8)`;
- mọi float finite;
- SHA lowercase 64 hex; Git SHA 40/64 hex;
- canonical `artifact_sha256` tính sau khi bỏ chính field này.

Không thêm compatibility constructor cho schema cũ.

### R0.2 — Tạo streaming pair-replay seam

File:

- `ai-service/src/ai_service/evaluation/full_catalog.py`.

Thêm internal typed records:

```python
@dataclass(frozen=True)
class TargetReplayRequest:
    trap_id: int
    user_id: int
    target_item_ids: tuple[int, ...]


@dataclass(frozen=True)
class TargetReplayRow:
    trap_id: int
    user_id: int
    deep_rank: int
    hybrid_rank: int
    deep_top_k_cutoff: float
    target_deep_score: float
    learned_wide_bonus: float
    required_wide_bonus: float


@dataclass(frozen=True)
class PairDiagnosticReplay:
    deep: EvaluationResult
    hybrid: EvaluationResult
    alpha_results: dict[float, EvaluationResult]
    targets: tuple[TargetReplayRow, ...]
```

Thêm method trên `FullCatalogEvaluator`:

```python
def evaluate_pair_diagnostics(
    self,
    *,
    hybrid_model: HybridTwoTowerModel,
    deep_model: HybridTwoTowerModel,
    snapshot: Snapshot,
    prepared_split: PreparedEvaluationSplit,
    alpha_values: tuple[float, ...],
    target_requests: tuple[TargetReplayRequest, ...],
    device: torch.device,
) -> PairDiagnosticReplay:
    ...
```

Implementation:

- encode Hybrid/Deep catalog đúng một lần/model;
- build history profiles đúng một lần;
- stream theo `validation_user_batch_size`;
- dùng cùng `_metric_row()`, seen masking và raw-product tie-break;
- Hybrid alpha score luôn là `hybrid_deep_logits + alpha * wide_logits`;
- không giữ `dict[user] = full_catalog_scores`;
- chỉ giữ per-user metrics, bounded top-k và target replay evidence;
- reject non-finite logits, unknown users/targets, duplicate alpha hoặc request không thuộc
  eligible split;
- item-query legacy replay không được đưa vào method này.

Các path `evaluate()`, `evaluate_variants()` và training validation hiện có không đổi
semantics. Test toàn bộ behavior qua `evaluate_pair_diagnostics()`, không gọi private
scoring helpers.

### R0.3 — Implement diagnostic calculation and publication

File mới:

- `ai-service/src/ai_service/evaluation/r3_diagnostics.py`.

Private implementation steps:

1. `_validate_pair()`:
   - exact seed 42;
   - Hybrid/Deep variants đúng;
   - same commit, lineage, comparison signature;
   - checkpoint SHA khớp manifests;
   - strict-load cả hai checkpoints.
2. `_build_rule_alignment()`:
   - mirror timestamp semantics của `build_purchase_training_index()`;
   - context của target chỉ là last purchase từ timestamp trước;
   - tách diagonal positive, other positive, in-batch negative và explicit negative;
   - dựng tập aligned VAL users bằng organic novel truth.
3. `_build_target_requests()`:
   - đọc `event_origin=semantic_trap` và `cohort_id` từ immutable snapshot;
   - history chứa anchor trước split boundary;
   - target nằm trong VAL, novel và không seen;
   - raw/internal mapping round-trip exact.
4. Gọi `evaluate_pair_diagnostics()` một lần.
5. `_replay_item_query_legacy()`:
   - tái hiện item-vector-as-query chỉ để so sánh nguyên nhân;
   - ghi score/cutoff/rank nhưng không trả gate result.
6. `_cohort_deltas()`:
   - join per-user arrays bằng sorted `user_ids`;
   - tính Hybrid−Deep riêng aligned/unaligned;
   - reject user set mismatch.
7. `_validate_metrics()` cho NPZ exact keys:

```text
user_ids
deep_gauc, deep_hr, deep_ndcg
hybrid_gauc, hybrid_hr, hybrid_ndcg
aligned_mask
alpha_0_gauc/hr/ndcg
alpha_0_25_gauc/hr/ndcg
alpha_0_5_gauc/hr/ndcg
alpha_1_gauc/hr/ndcg
alpha_2_gauc/hr/ndcg
alpha_4_gauc/hr/ndcg
alpha_8_gauc/hr/ndcg
```

8. Publish destination:

```text
artifacts/diagnostics/r3-root-cause/<diagnostic-signature>/
  report.json
  per-user-metrics.npz
```

Publication contract:

- temp sibling directory;
- NPZ exact key/dtype/shape/finite validation;
- fsync NPZ và report;
- report chứa NPZ SHA;
- verified-load temp;
- destination tồn tại thì reject;
- atomic directory rename;
- verified-load lại destination;
- cleanup temp khi error.

`load_r3_diagnostic()` yêu cầu exact file allowlist và recompute cả NPZ SHA lẫn canonical
report SHA.

### R0.4 — CLI và pipeline read-only orchestration

Files:

- `ai-service/src/ai_service/cli.py`;
- `ai-service/src/ai_service/training/pipeline.py`.

CLI command:

```powershell
python -m ai_service.cli diagnose-r3 `
  --hybrid-run-id diag-r3-hybrid-both-s42 `
  --deep-run-id diag-r3-deep-both-s42 `
  --split val --device cuda
```

Parser contract:

- `--hybrid-run-id`, `--deep-run-id`, `--split`, `--device` required;
- split choice chỉ có `val` trong schema 1.0.0;
- reject same run ID.

Trong `pipeline.py`:

- thêm `_diagnose_r3(args, settings) -> R3DiagnosticArtifact`;
- dùng `_load_run_context()` cho cả hai run;
- không duplicate loader/checkpoint validation;
- không gọi `_evaluate_pair()`, Victory Gates hoặc release;
- không mutate lifecycle, `PipelineState`, checkpoints hay evaluation directories;
- `execute_command()` chỉ dispatch và `_emit(report.model_dump(mode="json"))`.

### R0.5 — Tests

File mới:

- `ai-service/tests/unit/test_r3_diagnostics_contract.py`.

Test cases:

1. Streaming replay parity với reference fixture cho mọi alpha, `atol=1e-6`.
2. Aligned/unaligned masks exact và disjoint.
3. Row chỉ có negative rule không tăng strict target coverage.
4. Timestamp-equal purchase không được dùng làm prior context.
5. Semantic request target seen/missing/cold/corrupt bị reject.
6. Item-query và serving-query evidence cùng tồn tại nhưng chỉ serving result được gắn
   cohort semantics.
7. NPZ missing/extra key, wrong dtype/shape, NaN/Inf bị reject.
8. Report/NPZ/hash/checkpoint/lineage mutation bị reject.
9. Partial directory và overwrite bị reject.
10. Alpha sweep không được ghi thành selected alpha hoặc config mutation.

Cập nhật:

- `test_full_catalog_contract.py`: pair replay batch bound, parity, no full-score dict.
- `test_pipeline_cli_contract.py`: parser → real dispatch seam, read-only side effects.
- `test_checkpoint_report_and_trap_contracts.py`: diagnostic artifact corruption.
- `tests/support/v5_factories.py`: typed diagnostic fixture; không tạo generic dict helper.

### R0 exit gate

Targeted:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_r3_diagnostics_contract.py `
  tests\unit\test_full_catalog_contract.py `
  tests\unit\test_pipeline_cli_contract.py `
  tests\unit\test_checkpoint_report_and_trap_contracts.py -q
```

Runtime reproduction:

```text
Hybrid GAUC              = 0.775218972 ± 1e-6
Hybrid HR@10             = 0.054092097 ± 1e-6
Hybrid NDCG@10           = 0.011513037 ± 1e-6
strict target-rule rate  ≈ 0.0731
semantic legacy gate     = 0/10
ItemCF GAUC delta        < 0
Persona HR delta         < 0
Apriori NDCG delta       < 0
```

R0 pass khi diagnostic artifact verified-load được, tái hiện failure và không làm đổi
bất kỳ run lifecycle/state nào. R0 fail thì giữ toàn bộ v4 data, chưa chạy reset.

## 4. Phase R1 — Clean-slate reset và local output purge

### R1.0 — Shared database connection utilities

File:

- `backend/docs/chatbot/seed-product/benchmark-lib.js`.

Thay đổi:

- giữ `dbConfig()` là nơi duy nhất dựng verified TLS config;
- thêm `databaseTargetFingerprint(connectionString)` trả SHA-256 của
  `hostname:port:database`, không gồm username/password;
- thêm `queryDatabaseIdentity(client)` trả `current_database`, server address/port
  trong memory;
- `connectDatabases()` tiếp tục trả named clients `auth`, `catalog`, `order`, `chat`;
- không log config/URL trong helper;
- export helpers trên để reset tests dùng production behavior thay vì duplicate parser.

Preflight reset require bốn target fingerprints distinct. Output chỉ được ghi labels
`auth/catalog/order/chat` và boolean `distinct=true`.

### R1.1 — Reset benchmark database module

File mới:

- `backend/docs/chatbot/seed-product/reset-benchmark-v5.js`.

CLI:

```powershell
node backend\docs\chatbot\seed-product\reset-benchmark-v5.js `
  --spec backend\docs\chatbot\seed-product\benchmark-spec-v5.json `
  --preflight

node backend\docs\chatbot\seed-product\reset-benchmark-v5.js `
  --spec backend\docs\chatbot\seed-product\benchmark-spec-v5.json `
  --execute --confirm RESET_STORE_1_BENCHMARK_V5
```

Argument rules:

- exactly one of `--preflight` hoặc `--execute`;
- execute require exact confirmation token;
- spec `store_id` phải bằng `1`;
- không hỗ trợ wildcard, list store hoặc custom SQL;
- CA file phải absolute/exist và four URLs present;
- `--preflight` không gọi `BEGIN`, `DELETE`, DDL hoặc lock write.

`planBenchmarkReset()` trả immutable document:

```javascript
{
  storeId: 1,
  distinctDatabases: true,
  chatbot: {
    events, partitions, runs, interactions,
    similarities, coPurchaseRows, frequencyRows
  },
  order: { benchmarkOrders, benchmarkOrderDetails, businessOrders },
  auth: { customers, activeCustomers, minId, maxId },
  catalog: { activeProducts, minId, maxId }
}
```

Preflight requirements:

- Auth exact 5.000 active customers, IDs `1..5000`, no unlinked customer;
- Catalog exact 5.200 active products;
- inspect `pg_constraint` xác nhận `sale_order_detail.order_id` có
  `ON DELETE CASCADE`;
- business order count được giữ làm in-memory postcondition;
- query không đọc/in secret.

`executeBenchmarkReset()`:

1. Chạy lại preflight trong cùng process.
2. Chatbot transaction:

```sql
DELETE FROM item_similarity
WHERE store_id = 1;

DELETE FROM user_product_interaction
WHERE store_id = 1;

DELETE FROM co_purchase_stats
WHERE store_id = 1;

DELETE FROM product_order_frequency
WHERE store_id = 1;

DELETE FROM ml_interaction_event_v1
WHERE store_id = 1;

DELETE FROM ml_benchmark_item_partition_v1
WHERE store_id = 1;

DELETE FROM ml_benchmark_run_v1
WHERE store_id = 1;
```

3. Order transaction:

```sql
DELETE FROM sale_order
WHERE store_id = 1
  AND benchmark_run_id IS NOT NULL;
```

4. `sale_order_detail` chỉ bị xóa qua verified cascade.
5. Auth/Catalog connections giữ read-only và không mở transaction write.
6. Rerun `planBenchmarkReset()`.
7. Require tất cả benchmark/derived counts bằng zero và `businessOrders` không đổi.

Cross-database failure:

- không tuyên bố success nếu một transaction fail;
- rollback database đang fail;
- transaction đã commit không được bù bằng khôi phục;
- command rerun an toàn vì mọi delete có selector chính xác và idempotent;
- không persist reset receipt/audit file theo clean-slate policy.

Không có fallback `TRUNCATE`, `DROP` hoặc `DELETE sale_order WHERE store_id=1`.

### R1.2 — Remove legacy reclaim from normal seed path

File:

- `backend/docs/chatbot/seed-product/seed-ml-benchmark.js`.

Trong R1 chỉ chuẩn bị seam, chưa chuyển generator:

- xóa `reclaimLegacyMlStorage()` và call site;
- normal seed không tự delete bất kỳ lineage/data cũ;
- nếu preflight tìm thấy benchmark run/order/event cũ, fail với hướng dẫn chạy
  `reset-benchmark-v5.js`;
- `requireUnusedBenchmarkRun()` vẫn reject immutable destination;
- xóa export `reclaimLegacyMlStorage`.

R2 sẽ tiếp tục thay validator/spec v4 bằng v5.

### R1.3 — Local artifact purge module

File mới:

- `ai-service/scripts/purge_benchmark_outputs.py`.

Interface nội bộ:

```python
@dataclass(frozen=True)
class PurgeEntry:
    path: Path
    byte_count: int
    file_count: int


@dataclass(frozen=True)
class PurgePlan:
    artifact_root: Path
    entries: tuple[PurgeEntry, ...]


def build_purge_plan(artifact_root: Path) -> PurgePlan: ...
def execute_purge(plan: PurgePlan, *, confirmation: str) -> None: ...
```

CLI:

```powershell
.\.venv\Scripts\python.exe scripts\purge_benchmark_outputs.py --dry-run

.\.venv\Scripts\python.exe scripts\purge_benchmark_outputs.py `
  --confirm PURGE_ALL_PRE_V5_OUTPUTS
```

Path policy:

- artifact root resolve exact
  `E:\UIT\cv\backend\ai-service\artifacts`;
- chỉ các direct children sau được phép:

```text
_archive
snapshots
features
rules
runs
diagnostics
releases
bundles
```

- unexpected non-empty child khiến toàn operation fail;
- reject symlink, junction/reparse point và resolved path ngoài root;
- không nhận glob hoặc arbitrary target;
- không xóa root directory;
- dry-run chỉ tính file count/bytes;
- execute recompute plan ngay trước delete để phát hiện TOCTOU;
- xóa children bằng explicit resolved paths, không shell out sang `rm`, `cmd` hoặc glob.

Sau execute, recreate empty allowlisted directories chỉ khi runtime cần; không tạo archive
hoặc tombstone.

### R1.4 — Tests

File mới:

- `backend/docs/chatbot/seed-product/tests/reset-benchmark-v5.test.js`.

Test bằng recording clients:

1. `--preflight` chỉ phát SELECT.
2. Missing/wrong confirmation không mở write transaction.
3. `store_id != 1` bị reject.
4. Duplicate physical database target bị reject.
5. Missing/non-cascade FK bị reject trước delete.
6. Chatbot delete exact table/selector/order.
7. Order delete có cả `store_id` và `benchmark_run_id IS NOT NULL`.
8. Không statement nào mutation Auth/Catalog.
9. Chatbot failure rollback và không chạy Order.
10. Order failure rollback; rerun trên already-empty Chatbot pass.
11. Business order count thay đổi khiến postcondition fail.
12. Captured stdout/stderr không chứa URL/password.

Cập nhật:

- `seed-ml-benchmark.test.js`: xóa legacy reclaim test; thêm old data blocks seed.
- `backend/package.json`: `test:seed-product` hiện đã include glob, không đổi script trừ
  khi test mới không được discovered.

File mới:

- `ai-service/tests/unit/test_purge_benchmark_outputs.py`.

Test purge:

- dry-run no mutation;
- valid nested files được đếm/xóa;
- wrong root, unexpected child, symlink/junction, wrong token bị reject;
- recomputed plan mismatch bị reject;
- root và unrelated sibling được giữ nguyên;
- second run idempotent.

### R1.5 — Source validation trước destructive execution

```powershell
cd E:\UIT\cv\backend\backend
npm.cmd run test:seed-product

cd E:\UIT\cv\backend\ai-service
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_purge_benchmark_outputs.py `
  tests\unit\test_pipeline_cli_contract.py -q

.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
```

Đây là targeted gate của reset/purge module. Chưa chạy destructive commands ngay sau
gate này: hoàn tất tiếp toàn bộ R2 implementation/tests, chạy cross-phase quality gate
ở Mục 6, commit/push toàn bộ R0–R2 và require clean/upstream-synchronized source trước
khi reset. `benchmark-spec-v5.json` vì vậy đã tồn tại và verified trước khi reset dùng
nó. `.env` và CA không được stage hoặc copy vào logs/docs.

### R1.6 — Destructive execution order

Precondition: toàn bộ R0–R2 source/tests và Mục 6 đã pass trên commit được push.

1. Chạy DB `--preflight`; lưu counts chỉ trong operator terminal hiện tại.
2. Chạy artifact purge `--dry-run`; review exact paths và sizes.
3. Chạy DB reset với exact confirmation.
4. Chạy DB `--preflight` lần hai; require benchmark counts zero.
5. Chạy artifact purge với exact confirmation.
6. Chạy artifact `--dry-run` lần hai; require zero files.
7. Verify Git worktree vẫn clean.

Không chạy seed giữa bước 3 và bước 6.

### R1 exit gate

```text
Order benchmark rows                      = 0
Order benchmark detail rows               = 0
Order non-benchmark row count              = unchanged
Chatbot benchmark run/event/partition rows = 0
Chatbot store-1 derived recommendation rows = 0
Auth/Catalog mutation                      = none
pre-v5 artifact files                      = 0
archive/restore package                    = absent
worktree                                   = clean
```

R1 fail thì không seed. Partial reset được hoàn thiện bằng idempotent rerun; không tạo
manual broad-delete workaround.

## 5. Phase R2 — Deterministic benchmark v5 seed

### R2.0 — Centralize and freeze the v5 spec contract

Files:

- tạo `backend/docs/chatbot/seed-product/benchmark-spec.js`;
- tạo `backend/docs/chatbot/seed-product/benchmark-spec-v5.json`;
- sau R2 exit gate, xóa `benchmark-spec-v4.json`.

`benchmark-spec-v5.json` giữ event/order scale hiện tại và thay đổi semantics:

```json
{
  "schema_version": "3.0.0",
  "generator_version": "5.0.0",
  "seed": 42,
  "store_id": 1,
  "num_users": 5000,
  "num_products": 5200,
  "num_cold_products": 250,
  "num_events": 823371,
  "num_orders": 15000,
  "organic_order_count": 14250,
  "semantic_order_count": 750,
  "organic_rule_transition_fraction": 0.50,
  "minimum_training_target_rule_rate": 0.40,
  "minimum_val_rule_target_rate": 0.40,
  "minimum_non_trap_directed_rules": 5000,
  "minimum_distinct_organic_rule_items": 3000
}
```

Giữ nguyên các split counts/cutoffs, persona distribution, organic template count/repeat,
semantic cohort sizes, minimum lift/count và 10 fixture definitions trừ khi một test
chứng minh arithmetic inconsistency.

`loadBenchmarkSpec()`:

- parse JSON và reject extra/missing required top-level keys;
- require exact schema/generator;
- require split counts sum đúng event count;
- require organic+semantic orders đúng 15.000;
- require persona distribution finite, nonnegative và sum `1 ± 1e-12`;
- require trap IDs exactly `1..10`, anchor/targets positive, distinct và không duplicate
  giữa fixtures;
- require transition fraction `0.50` và target floors `0.40`;
- require organic rule thresholds như master plan;
- deep-freeze returned spec.

`canonicalSpecSha256()` dùng recursive key-sort/canonical JSON. Seed, reset, inspect và
database run metadata phải dùng cùng hash này; không dùng raw file-byte hash hoặc plain
`JSON.stringify(spec)` có thứ tự phụ thuộc input.

### R2.1 — Order Service owns benchmark metadata schema

Files:

- `backend/services/order/src/db/init.sql`;
- đồng bộ docs schema tại `backend/docs/database-design/service3-order.sql`;
- đồng bộ aggregate schema tại `backend/docs/supabase_init_all.sql`.

Add nullable columns:

```sql
benchmark_kind TEXT,
benchmark_template_id TEXT,
benchmark_trap_id INTEGER
```

Add constraint:

```text
benchmark_run_id IS NULL
  -> kind/template/trap đều NULL

benchmark_run_id IS NOT NULL AND kind='organic'
  -> template non-empty, trap NULL

benchmark_run_id IS NOT NULL AND kind='semantic_trap'
  -> template non-empty, trap_id trong 1..10
```

Add index only if query plan requires it:

```sql
(store_id, benchmark_run_id, benchmark_kind, order_date)
WHERE benchmark_run_id IS NOT NULL
```

Schema application diễn ra như migration/preflight riêng. `mock-orders.js` không được
`ALTER TABLE` trong normal seed transaction. Seed preflight query `information_schema`
và reject nếu columns/constraint chưa tồn tại.

Validation:

- current business orders vẫn thỏa constraint với all-null benchmark metadata;
- migration idempotent;
- rollback on invalid existing benchmark rows;
- service Order unit/integration tests pass.

### R2.2 — Shared affinity creates deterministic transition cohorts

File:

- `backend/docs/chatbot/seed-product/benchmark-affinity.js`.

Giữ nguyên:

- `buildPersonaAssignments()`;
- `buildUserAffinities()`;
- `buildOrganicBundleTemplates()`.

Thêm:

```javascript
function buildOrganicRuleTransitions({
  users,
  preferredProducts,
  neighborsByProduct,
  fixtureProducts,
  coldProducts,
  fraction,
  seed,
  split
}) { ... }
```

Algorithm:

1. Stable-order users bằng SHA-256 của `seed:split:user_id`.
2. Chọn exact `round(fraction * users.length)` users.
3. Với mỗi user, chọn anchor từ preferred warm organic items.
4. Chọn target từ `neighborsByProduct[anchor]` thỏa:
   - khác anchor;
   - warm;
   - không thuộc semantic fixtures;
   - chưa seen trong earlier split;
   - cùng persona affinity.
5. Stable tie-break bằng raw product ID.
6. Không đủ candidate cho bất kỳ selected user thì fail, không giảm cohort ngầm.
7. Return deep-frozen records `{userId, anchorProductId, targetProductId, split}`.

Build riêng VAL và TEST transitions; target VAL không được xuất hiện trong TRAIN, target
TEST không được xuất hiện trong TRAIN/VAL.

### R2.3 — Fix order generation and persist provenance

File:

- `backend/docs/chatbot/seed-product/mock-orders.js`.

`generateOrderPlan()`:

- replace v4 guard bằng exact v5 guard từ loaded spec; không giữ v3/v4 message;
- giữ 14.250 organic/750 semantic orders;
- giữ organic template repeat contract;
- semantic target selection dùng counter riêng/trap:

```javascript
const occurrence = occurrencesByTrap.get(trapId) || 0;
const target = trap.targets[occurrence % trap.targets.length];
occurrencesByTrap.set(trapId, occurrence + 1);
```

- sau generation, với mỗi expected `(anchor,target)` require count nằm trong
  `floor(trap_orders/target_count)..ceil(...)`;
- order record luôn chứa `kind`, `templateId`, `trapId`.

`insertOrders()`:

- thêm columns `benchmark_kind`, `benchmark_template_id`, `benchmark_trap_id`;
- arrays phải cùng length và non-null theo kind;
- không derive metadata lại từ products khi insert.

`seedOrders()`:

- bỏ DDL `ALTER TABLE`/`CREATE INDEX`;
- preflight schema trước `BEGIN`;
- immutable run check trước reserve IDs;
- transaction insert theo batches như hiện tại;
- postcondition group by `benchmark_kind` và exact pair distribution;
- rollback toàn run order insert khi any postcondition fail.

### R2.4 — Reserve deterministic organic rule transitions in events

File:

- `backend/docs/chatbot/seed-product/seed-ml-events.js`.

Refactor thành các bước rõ ràng:

1. `buildSemanticCohorts()` giữ behavior hiện tại.
2. Thêm `buildOrganicRuleCohorts()` gọi shared affinity transition function.
3. `reserveOrganicRuleRows()` tạo:
   - prior view + purchase anchor ở history split;
   - view + novel purchase target ở target split;
   - unique session/cohort IDs;
   - `event_origin='organic'`.
4. Đưa reserved rows vào `definitions.before/after` trước khi tính organic filler quota.
5. `buildOrganicRows()` fill phần còn lại và không được chọn blocked future targets.
6. Exact split event counts và timestamp boundary giữ nguyên.

Thay `organic_rule_transition_probability` bằng deterministic
`organic_rule_transition_fraction`; xóa probability branch và RNG decision liên quan.

Independent database validations sau insert:

- each selected user có anchor trước boundary;
- target chỉ xuất hiện ở target split;
- anchor→target tồn tại trong generated organic bundle graph;
- target novel đối với history;
- eligible/aligned counts khớp planned cohort;
- actual rate `>=0.40` cho TRAIN và VAL;
- semantic/cold cohorts vẫn disjoint với organic rule cohorts;
- no session crosses split boundaries.

Không dùng cùng in-memory planned records làm nguồn duy nhất của postcondition; validation
phải query actual persisted events.

### R2.5 — Strengthen co-purchase evidence

File:

- `backend/docs/chatbot/seed-product/populate-copurchase.js`.

Source query thêm:

```text
o.benchmark_kind
o.benchmark_template_id
o.benchmark_trap_id
```

Accumulator lưu per pair:

- total count;
- organic count;
- semantic count;
- organic template IDs;
- trap IDs.

Rule summary exact shape:

```javascript
{
  totalOrders,
  storedPairCount,
  totalDirectedRules,
  nonTrapDirectedRules,
  trapAnchoredDirectedRules,
  trapAnchoredRuleFraction,
  distinctOrganicRuleItems,
  fullCatalogOrganicPairCoverage,
  expectedTrapDirections: [
    { trapId, anchor, target, count, support, lift, passed }
  ]
}
```

Classification rules:

- non-trap rule require organic count `>=min_count` và cả hai endpoints ngoài fixture set;
- trap direction validated cho từng anchor-target, không dùng aggregate trap order count;
- every expected direction require count `>=minimum_semantic_copurchase_count / target_count`
  làm tròn xuống, lift đạt spec và both directions có thể materialize trong Python rule
  artifact;
- summary fail trước Chatbot commit nếu threshold không đạt.

Derived table rebuild vẫn replace toàn store-1 data, hợp lệ vì R1 đã xác nhận clean slate.

### R2.6 — Seed orchestrator becomes v5-only

File:

- `backend/docs/chatbot/seed-product/seed-ml-benchmark.js`.

Thay đổi theo symbol:

- xóa local `loadBenchmarkSpec()`; import từ `benchmark-spec.js`;
- xóa `reclaimLegacyMlStorage()` hoàn toàn;
- `buildAffinityModel()` không còn optional/version branch;
- generated ID giữ format:

```text
benchmark-v5-s42-<catalog-sha-prefix>-<canonical-spec-sha-prefix>
```

- preflight require R1 zero-state:
  - no store-1 benchmark run/events/partitions;
  - no benchmark orders;
  - no store-1 derived recommendation rows;
  - business orders allowed;
- require order metadata schema trước mutation;
- create run `staging` only after all read-only preflight passes;
- seed order/events, rebuild interaction/copurchase, then call one `validateRun()`;
- only `validateRun()` may transition `staging -> ready`;
- failure transitions current run to `failed` if run row exists; no auto-delete/retry ID.

`validateRun()` phải independently verify:

```text
events/splits/users/products/cold counts
orders and order-kind counts
event/order benchmark run IDs
catalog SHA and canonical spec SHA
organic conversion and novel purchase coverage
training strict target-rule rate >= 0.40
VAL strict target-rule rate >= 0.40
VAL context rule coverage >= existing 0.60 gate
non-trap directed rules >= 5000
distinct organic rule items >= 3000
trap-anchored fraction <= 0.10
every expected trap direction passes
semantic VAL/TEST cohorts exact and isolated
```

Persist full validation document in existing `ml_benchmark_run_v1.rule_coverage`; do not
create an old-data audit table.

Resume policy:

- `--resume-run` only for same v5 staging run/spec/catalog hash;
- completed/failed/old-version run cannot resume;
- resume re-runs independent validation before publication.

### R2.7 — Storage inspector reflects v5 truth

File:

- `backend/docs/chatbot/seed-product/inspect-ml-storage.js`.

Thay đổi:

- require explicit `--spec benchmark-spec-v5.json` và `--run-id`;
- use canonical spec loader/hash;
- display only non-secret typed JSON;
- include order-kind counts, exact trap directions, TRAIN/VAL target-rule rates,
  non-trap rules and distinct organic items;
- verify run status `ready`, published timestamp, catalog/spec hashes;
- fail exit code on any mismatch; no warning-only path.

### R2.8 — Node contract tests

Tạo:

- `backend/docs/chatbot/seed-product/tests/benchmark-spec.test.js`.

Cập nhật:

- `benchmark-affinity.test.js`;
- `mock-orders.test.js`;
- `seed-ml-events.test.js`;
- `rule-readiness.test.js`;
- `seed-ml-benchmark.test.js`.

Required tests:

1. v5 spec accepts exact schema; v3/v4/extra/missing keys reject.
2. Canonical hash independent of JSON key order.
3. Affinity and transitions deterministic across two runs.
4. Exact 50% transition cohort; every target warm/novel/non-fixture.
5. Organic templates remain persona aligned and repeated six times.
6. Every single anchor-target semantic pair gets floor/ceil distribution.
7. Regression asserts old global-index algorithm would miss the known three directions.
8. Insert SQL persists kind/template/trap columns.
9. Business rows remain nullable and untouched.
10. Event split counts/timestamps/session isolation exact.
11. TRAIN/VAL target-rule rate below 0.40 rejects publication.
12. Aggregate trap count pass but one direction missing still fails.
13. Old v4 data present blocks normal seed; no implicit reclaim.
14. Staging resume requires same v5 spec/catalog hash.
15. Inspector rejects corrupted rule coverage/spec hash/order metadata.

Run:

```powershell
cd E:\UIT\cv\backend\backend
npm.cmd run test:seed-product
npm.cmd test
```

The root `npm test` may still expose unrelated legacy failures; every newly introduced
failure must be classified. R2 files/tests must be green and no exclusion may remove
`docs/chatbot/seed-product/tests/*.test.js` from the root gate.

### R2.9 — Database migration and seed execution

Execution shell reads [backend/.env](E:/UIT/cv/backend/backend/.env) and
[prod-ca-2021.crt](E:/UIT/cv/backend/backend/.certs/prod-ca-2021.crt). Không echo secret.

Order:

1. Verify R1 zero-state again.
2. Apply idempotent Order benchmark metadata migration.
3. Run Order schema contract query.
4. Seed preflight:

```powershell
$env:NODE_ENV = "development"

node backend\docs\chatbot\seed-product\seed-ml-benchmark.js `
  --spec backend\docs\chatbot\seed-product\benchmark-spec-v5.json `
  --store-id 1 --seed 42 --preflight-only
```

5. Require preflight JSON matches R1 zero-state and Auth/Catalog contracts.
6. Execute seed exactly once:

```powershell
node backend\docs\chatbot\seed-product\seed-ml-benchmark.js `
  --spec backend\docs\chatbot\seed-product\benchmark-spec-v5.json `
  --store-id 1 --seed 42
```

7. Capture generated run ID from command result; do not construct a second ID manually.
8. Inspect:

```powershell
node backend\docs\chatbot\seed-product\inspect-ml-storage.js `
  --spec backend\docs\chatbot\seed-product\benchmark-spec-v5.json `
  --run-id <generated-v5-run-id>
```

9. Run inspector a second time to prove deterministic read-only result.

### R2 exit gate

```text
benchmark run status                  = ready/published
generator/schema                      = 5.0.0 / 3.0.0
users/products/cold                   = 5000 / 5200 / 250
events                                = 823371
train/val/test                         = 658697 / 82337 / 82337
orders organic/semantic/total         = 14250 / 750 / 15000
business orders                       = unchanged
training strict target-rule rate      >= 0.40
VAL strict target-rule rate           >= 0.40
VAL context rule coverage             >= 0.60
non-trap directed rules               >= 5000
distinct organic rule items           >= 3000
trap-anchored fraction                <= 0.10
expected trap directions              = all pass
semantic cohorts                      = exact and split-isolated
old v4 database rows/artifacts         = absent
```

R2 pass chỉ chứng minh database dataset v5 sẵn sàng cho Python snapshot/readiness của
R3. Không được bắt đầu GPU training, Deep ablation hoặc production campaign ở cuối R2.

## 6. Cross-phase quality gate và handoff

Sau R0–R2 code hoàn tất, trước handoff sang R3:

```powershell
cd E:\UIT\cv\backend\backend
npm.cmd run test:seed-product

cd E:\UIT\cv\backend\ai-service
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts

$coverageJson = Join-Path $env:TEMP "ai-service-r0-r2.json"
.\.venv\Scripts\python.exe -m pytest `
  --cov=ai_service --cov-branch `
  --cov-report=term-missing `
  --cov-report=json:$coverageJson `
  --cov-fail-under=85 -q

.\.venv\Scripts\python.exe scripts\check_critical_coverage.py $coverageJson
git diff --check
```

Static invariants:

```powershell
rg -n "benchmark-spec-v4|generator v4|reclaimLegacyMlStorage" `
  backend\docs\chatbot\seed-product

rg -n "scores_by_user|dict\[int, np\.ndarray\]" `
  ai-service\src\ai_service\evaluation

rg -n "DROP DATABASE|DROP SCHEMA|TRUNCATE" `
  backend\docs\chatbot\seed-product\reset-benchmark-v5.js
```

Sau khi v5 replacement được xác minh và file v4 đã xóa, ba scan phải không có
production-path match.

Handoff document cho R3 phải chứa duy nhất:

- generated v5 benchmark run ID;
- canonical spec SHA;
- exact DB validation counters;
- R0 root-cause diagnostic SHA trước purge, nếu còn được ghi trong tracked report;
- R2 pass/fail matrix;
- source commit đã push.

Không giữ binary v4 diagnostic, snapshot, rules, run hoặc archive. Không cập nhật master
plan thresholds/phase order. Nếu bất kỳ R0, R1 hoặc R2 exit gate fail, trạng thái cuối là:

```text
BLOCKED_BEFORE_R3_AND_PRODUCTION_TRAINING
```

## 7. Implementation receipt (2026-08-12)

Source implementation completed for the R0/R1/R2 seams without changing the
master plan or starting production training.

Completed:

- R0 diagnostic contracts, streaming trap replay, immutable NPZ/report
  publication, verified loader, and read-only `diagnose-r3` CLI.
- R0 replay on the existing v4 pair completed on CUDA. The resulting artifact
  is under `ai-service/artifacts/diagnostics/r3/` and reproduces the failure:
  strict context-to-target rule rate 0.0730966, VAL aligned users 378/4973,
  aligned Hybrid gain positive, unaligned gain neutral/negative, and the
  standard HR/NDCG floors remain unmet.
- R1 reset module with read-only plan, exact confirmation token,
  store-scoped transactions, order-first deletion, and local artifact purge
  utility. The live reset was executed for store `1`; business orders (rows
  without `benchmark_run_id`) were not touched. The reset removed the failed
  v5 attempt and all store-scoped benchmark/derived rows before reseeding.
- R2 v5 spec loader/spec file, trap target occurrence fix, order metadata
  columns, exact anchor-target rule evidence, v5 inspector path, managed-DB
  bulk-load index handling, and Node contract tests. The semantic-trap
  validator now checks aggregate count per trap plus the minimum count for
  every anchor-target direction (multi-target traps intentionally split
  `75` into `38+37`).

R2 runtime result:

- Ready run: `benchmark-v5-s42-7f40639b0d-c77f0824fb`.
- Canonical v5 spec SHA: `c77f0824fb9cc8f67cb498447616084848b503738c4af50e4f405b67b13ae7d3`.
- Events/users/items: `823371 / 5000 / 5200`; cold items: `250`.
- Orders: `14250` organic + `750` semantic-trap; total `15000`.
- Directed rules: `14112` total, `14086` non-trap, `4143` distinct organic
  items; trap-anchored fraction `0.0018424`.
- Validation: context-rule coverage `0.9066319`; VAL target-rule rate
  `0.4452014`; all 10 traps pass aggregate and per-direction checks.
- Read-only inspector verified the ready run and every expected anchor-target
  direction; its strict TRAIN target-rule replay is `63657/127265 = 0.5001925`
  and therefore clears the `0.40` floor. (The post-seed validator now performs
  this same check for future v5 runs before publication.)
- The managed database did not have enough temporary space to rebuild the
  823k-row event index after bulk load; the seed path now leaves that optional
  index dropped. No data-contract gate was weakened.

Validation receipt:

- Python: 388 passed, 2 fixed-runner skips, branch coverage 85.27%.
- Critical coverage: checkpoint 97.24%, report 90.79%, bundle 98.79%, release
  90.22%, trainer 86.68%, pipeline 85.15%; all critical thresholds pass.
- Ruff format/lint and mypy pass; `git diff --check` has no whitespace errors.
- Seed-product Node suite: 16 passed.

Runtime state remains `BLOCKED_BEFORE_R3_AND_PRODUCTION_TRAINING` until the
operator reruns the R0 diagnostic against this new v5 snapshot and confirms
the R3 gates on the new lineage. R2 is data-ready; no production training,
release, seal, or export was executed.
