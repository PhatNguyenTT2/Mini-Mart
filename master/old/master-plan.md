# Clean-slate Benchmark v5, R3 Diagnostic và Production Training

## 1. Quyết định đã khóa

“Xóa toàn bộ dữ liệu cũ” được hiểu là xóa vĩnh viễn toàn bộ dữ liệu benchmark của `store_id=1` và mọi output ML cũ. Không:

- `DROP DATABASE`, `DROP SCHEMA` hoặc `TRUNCATE` bảng dùng chung.
- Xóa customer, catalog product hoặc order nghiệp vụ.
- Lưu `_archive`, legacy artifact, checksum archive hoặc restore package.
- In database URL/credential ra terminal.

Phạm vi theo microservice:

| Database | Thao tác |
|---|---|
| Order | Xóa `sale_order` có `store_id=1 AND benchmark_run_id IS NOT NULL`; `sale_order_detail` cascade |
| Chatbot | Xóa events, run/partition metadata và toàn bộ derived recommendation data của store 1 |
| Auth | Read-only: xác minh 5.000 customers |
| Catalog | Read-only: xác minh 5.200 products |
| Inventory/Payment/Supplier/DB mặc định | Không thay đổi |

Không thể bảo đảm mô hình chắc chắn hội tụ. Hệ thống sẽ bảo đảm theo nghĩa fail-closed: Hybrid không đạt chuẩn thì dừng, xuất báo cáo nguyên nhân và không cho chạy seeds tiếp theo/release.

Hard promotion gates:

```text
Hybrid GAUC       >= 0.75
Hybrid HR@10      >= 0.15
Hybrid NDCG@10    >= 0.08
Paired dominance  CI lower > 0 theo từng metric
Semantic traps    10/10 bằng serving-equivalent evaluation
Cold parity       PASS
```

## 2. Phase R0 — Đóng chẩn đoán R3 trước khi xóa dữ liệu

### Mã nguồn

Tạo [r3_diagnostics.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/r3_diagnostics.py):

- Thêm `R3DiagnosticReport` và verified NPZ chứa per-user HR/NDCG/GAUC.
- Đo riêng:
  - strict context→positive rule coverage;
  - positive-other, negative và explicit-negative rule exposure;
  - Hybrid−Deep trên cohort aligned/unaligned;
  - từng trap: raw/internal IDs, rule presence, Deep cutoff, Wide bonus, required bonus;
  - item-as-query và serving-cohort ranks;
  - alpha sweep cố định `[0, 0.25, 0.5, 1, 2, 4, 8]`.
- Hash report, NPZ, snapshot, rules, checkpoints và semantic cohort.
- Alpha sweep chỉ dùng chẩn đoán, tuyệt đối không tự chọn alpha để release.

Cập nhật:

- [contracts.py](E:/UIT/cv/backend/ai-service/src/ai_service/contracts.py): bump evaluation schema lên `5.2.0`; thêm typed diagnostic contracts.
- [cli.py](E:/UIT/cv/backend/ai-service/src/ai_service/cli.py): thêm `diagnose-r3 --hybrid-run-id --deep-run-id --split`.
- [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py): thêm handler read-only, verified-load hai run và reject lineage/commit mismatch.
- [report.md](E:/UIT/cv/backend/master/report.md): ghi nguyên nhân đã đo được:
  - strict positive-rule rate chỉ khoảng `7.31%`;
  - row-any rule coverage `69.10%` đang đo sai tín hiệu hữu ích;
  - semantic evaluator cũ không serving-equivalent;
  - seed thiếu ba directed trap transitions;
  - GAUC-only selection bỏ qua HR/NDCG.

### Validate R0

Diagnostic cũ phải tái hiện:

```text
Hybrid GAUC   = 0.775218972
Hybrid HR@10  = 0.054092097
Hybrid NDCG   = 0.011513037
Semantic      = 0/10
ItemCF delta  < 0
Persona HR delta < 0
Apriori NDCG delta < 0
```

Sau khi xác nhận, output v4 này sẽ bị xóa cùng toàn bộ artifact cũ; không giữ archive.

## 3. Phase R1 — Reset benchmark nhiều database và purge output

### Reset database

Tạo [reset-benchmark-v5.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/reset-benchmark-v5.js).

Interface:

```powershell
node reset-benchmark-v5.js --spec benchmark-spec-v5.json --preflight

node reset-benchmark-v5.js --spec benchmark-spec-v5.json `
  --execute --confirm RESET_STORE_1_BENCHMARK_V5
```

Script phải:

1. Đọc riêng các URL trong [backend/.env](E:/UIT/cv/backend/backend/.env) và CA tại [prod-ca-2021.crt](E:/UIT/cv/backend/backend/.certs/prod-ca-2021.crt).
2. Không log URL, password hoặc connection string.
3. Verify bốn database identities là riêng biệt.
4. Reject `store_id != 1`, thiếu confirmation hoặc selector rộng.
5. Ghi nhận counts trước reset trong memory, không publish audit file.
6. Chatbot transaction, đúng thứ tự:
   - `item_similarity WHERE store_id=1`;
   - `user_product_interaction WHERE store_id=1`;
   - `co_purchase_stats WHERE store_id=1`;
   - `product_order_frequency WHERE store_id=1`;
   - `ml_interaction_event_v1 WHERE store_id=1`;
   - `ml_benchmark_item_partition_v1 WHERE store_id=1`;
   - `ml_benchmark_run_v1 WHERE store_id=1`.
7. Order transaction:
   - `DELETE FROM sale_order WHERE store_id=1 AND benchmark_run_id IS NOT NULL`;
   - require `sale_order_detail` FK `ON DELETE CASCADE`.
8. Không có distributed transaction: các bước phải idempotent và chạy lại an toàn sau partial failure.
9. Postcondition:
   - tất cả benchmark counts bằng zero;
   - non-benchmark order count không đổi;
   - Auth/Catalog không có mutation.

Không fallback sang xóa mọi order của store 1 nếu `benchmark_run_id` thiếu.

### Purge local artifacts

Tạo [purge_benchmark_outputs.py](E:/UIT/cv/backend/ai-service/scripts/purge_benchmark_outputs.py):

```powershell
python scripts\purge_benchmark_outputs.py --dry-run
python scripts\purge_benchmark_outputs.py `
  --confirm PURGE_ALL_PRE_V5_OUTPUTS
```

Chỉ được xóa nội dung dưới absolute root:

```text
E:\UIT\cv\backend\ai-service\artifacts
```

Allowlist:

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

Script phải reject symlink/junction, path ngoài artifact root, unexpected directory hoặc artifact root rỗng/sai. Không xóa chính thư mục `artifacts`.

### Tests R1

Thêm Node tests:

- Missing/wrong confirmation.
- Store khác 1.
- Business orders được giữ nguyên.
- Benchmark order details cascade.
- Chatbot table delete đúng thứ tự.
- Partial failure rồi rerun.
- Auth/Catalog chỉ nhận `SELECT`.
- Output không chứa secret.

Thêm Python tests cho purge:

- Dry-run không mutation.
- Path traversal/symlink bị reject.
- Unexpected directory khiến fail.
- Chỉ allowlisted children bị xóa.

## 4. Phase R2 — Dataset v5 và rule-target alignment

### Seed schema

Thay [benchmark-spec-v4.json](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/benchmark-spec-v4.json) bằng `benchmark-spec-v5.json`:

```text
generator_version                     = 5.0.0
dataset_schema_version                = 3.0.0
organic_rule_transition_fraction      = 0.50
minimum_training_target_rule_rate     = 0.40
minimum_val_rule_target_rate          = 0.40
minimum_non_trap_directed_rules       = 5000
minimum_distinct_organic_rule_items   = 3000
```

Giữ quy mô:

```text
users       = 5000
products    = 5200
cold items  = 250
```

### Seed logic

Sửa [mock-orders.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/mock-orders.js):

- Thay global `index % targets.length` bằng occurrence counter riêng cho từng trap.
- Với 75 orders/trap, mọi target phải xuất hiện `floor/ceil(75 / target_count)` lần.
- Persist metadata:
  - `benchmark_kind`: `organic` hoặc `semantic_trap`;
  - `benchmark_template_id`;
  - `benchmark_trap_id`.

Sửa [init.sql](E:/UIT/cv/backend/backend/services/order/src/db/init.sql):

- Thêm ba nullable benchmark metadata columns trên `sale_order`.
- Business orders bắt buộc để các field này `NULL`.
- Thêm check constraint cho `benchmark_kind`.

Sửa [seed-ml-events.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/seed-ml-events.js):

- Bỏ transition xác suất đơn thuần.
- Dựng deterministic organic chains từ bundle graph.
- Ít nhất 50% eligible users có prior context và novel next-split target nối bằng organic rule.
- Semantic cohorts giữ anchor trong history và target ở VAL/TEST.
- Không dùng semantic trap baskets làm organic training signal.

Sửa [seed-ml-benchmark.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/seed-ml-benchmark.js):

- Chỉ chấp nhận generator `5.0.0`/schema `3.0.0`.
- Reject v3/v4 thay vì compatibility fallback.
- Validate từng expected anchor-target direction, không chỉ tổng trap.
- Validate target alignment train/VAL trước khi chuyển run sang `ready`.
- Không còn `reclaimLegacyMlStorage()`; reset là command riêng bắt buộc.

Sửa [populate-copurchase.js](E:/UIT/cv/backend/backend/docs/chatbot/seed-product/populate-copurchase.js):

- Tách:
  - `nonTrapDirectedRules`;
  - `trapAnchoredDirectedRules`;
  - `distinctOrganicRuleItems`;
  - exact fixture pair counts/support/lift.
- Fail nếu thiếu bất kỳ expected direction.

### Seed execution

Sau reset:

```powershell
$env:NODE_ENV = "development"

node backend\docs\chatbot\seed-product\seed-ml-benchmark.js `
  --spec backend\docs\chatbot\seed-product\benchmark-spec-v5.json `
  --store-id 1 --seed 42 --preflight-only

node backend\docs\chatbot\seed-product\seed-ml-benchmark.js `
  --spec backend\docs\chatbot\seed-product\benchmark-spec-v5.json `
  --store-id 1 --seed 42
```

Ghi lại generated benchmark run ID. Không dùng lại ID v4.

## 5. Phase R3 — Python readiness, objective và evaluation

### Data contracts

Cập nhật:

- [sources.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/sources.py): load benchmark order metadata từ Order DB.
- [snapshot.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/snapshot.py): bind spec SHA, cohort SHA, order-metadata SHA và alignment counters.
- [dataset.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/dataset.py):
  - giữ sequential purchase index;
  - thêm `RulePairIndex` từ organic baskets;
  - loại semantic-trap baskets khỏi auxiliary training.
- [rules.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/rules.py):
  - chỉ chấp nhận full-stat v5 artifact;
  - bỏ audit-only legacy loader path;
  - verify mọi expected fixture direction.
- [rule_readiness.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/rule_readiness.py):
  - thay row-any-only bằng typed counters:
    - strict target rule;
    - other-positive rule;
    - valid negative rule;
    - explicit-negative rule;
    - negative-only row.
  - Pre-GPU fail nếu strict target-rule rate `<0.40`.

Đổi:

```text
RULE_COVERAGE_SEMANTICS_VERSION = organic-target-alignment-v3
```

Giữ `MODEL_SCHEMA_VERSION=5.0.0`.

### Wide objective và sampling

Cập nhật [sampling.py](E:/UIT/cv/backend/ai-service/src/ai_service/data/sampling.py):

- Thêm quota `4/16` rule-hard negatives.
- Rule-hard negative phải warm, unseen, không có organic edge với anchor và unique.
- Không lấy semantic fixture làm positive training edge.

Cập nhật [objectives.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/objectives.py):

```python
rule_loss = -logsigmoid(wide_positive - wide_negative).mean()
total_loss = main_loss + view_weight * view_loss + rule_weight * rule_loss
```

- Deep logits detached khỏi rule auxiliary.
- Chỉ Wide parameters nhận gradient từ `rule_loss`.
- Zero-init scoring semantics giữ nguyên.

Cập nhật [trainer.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py):

- Log positive/negative Wide margins và gradient mass.
- Epoch 1 Hybrid require Wide gradient finite và `>0`.
- Deep-only Wide phải byte-identical.
- Add staged diagnostic stop:
  - mọi epoch: non-finite hoặc GAUC `<0.50` → catastrophic `FAILED`;
  - epoch 1: Wide/cache invariant fail → `FAILED`;
  - sau epoch 3: best-so-far GAUC `<0.65` hoặc HR `<0.10` hoặc NDCG `<0.04` → diagnostic `FAILED`.

Tạo `DiagnosticQualityError` và immutable `training/diagnostic-stop.json`. Run `FAILED` không được resume.

### Checkpoint eligibility

Cập nhật [stopping.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/stopping.py):

- GAUC vẫn là primary improvement signal.
- Sau warmup, checkpoint chỉ eligible nếu:
  - staged floors pass;
  - Hybrid không vi phạm Deep/Wide HR/NDCG/GAUC guardrails.
- Nếu hết training mà không có eligible checkpoint: fail diagnostic, không publish release candidate.

### Serving-equivalent semantic gate

Viết lại [semantic_traps.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/semantic_traps.py):

- Lấy semantic cohort từ immutable snapshot.
- History kết thúc tại anchor; heldout target không nằm trong history.
- Dùng cùng HistoryEncoder/UserTower, profiles, seen masking và raw-ID tie-break như full-catalog evaluator.
- Một trap pass khi:
  - mọi cohort target rank `<=10`;
  - không target nào xấu hơn independent Deep;
  - có strict Hybrid improvement.
- Require `10/10`.
- Item-as-query chỉ còn trong diagnostic report.

### Absolute gates và R3 selection

Cập nhật [gates.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/gates.py):

```text
minimum_gauc       = 0.75
minimum_hr_at_k    = 0.15
minimum_ndcg_at_k  = 0.08
```

Các threshold phải nằm trong resolved config và comparison signature.

Cập nhật [ablation.py](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/ablation.py):

- NPZ giữ per-user GAUC, HR và NDCG.
- Candidate Deep eligible nếu:
  - finite;
  - GAUC `>=0.55`;
  - paired GAUC CI vs Random lower `>0`;
  - GAUC/HR/NDCG noninferior với control theo configured guardrails;
  - ít nhất một metric có paired CI lower `>0`.
- Chọn theo:
  1. `max min(GAUC/.75, HR/.15, NDCG/.08)`;
  2. GAUC;
  3. NDCG;
  4. HR;
  5. config name.
- Không candidate eligible → dừng R3.

## 6. Phase R4 — Diagnostic campaign v5

### Deep ablations

Chạy tuần tự cùng seed 42:

```text
diag-v5-deep-control-s42
diag-v5-deep-no-price-s42
diag-v5-deep-no-user-s42
diag-v5-deep-both-s42
```

Config đặt tại `configs/diagnostics/r3-v5/`. Sau đó chạy `compare-deep-ablations`.

### Hybrid falsification ladder

Chạy từng biến một:

```text
H0: v5 data + main objective
H1: H0 + rule auxiliary weight 0.10
H2: H1 + 4/16 rule-hard negatives
H3a: H2 + view auxiliary weight 0
H3b: H2 + view auxiliary weight 0.10
```

Không chạy candidate tiếp theo khi:

- staged quality stop;
- target-rule readiness fail;
- semantic cohort corruption;
- checkpoint không eligible.

Candidate cuối chỉ được promote nếu paired VAL pass toàn bộ:

```text
GAUC >= .75
HR@10 >= .15
NDCG@10 >= .08
strongest-baseline paired CI lower > 0 theo metric
semantic traps 10/10
cold parity PASS
Wide readiness PASS
```

Nếu fail, publish `diagnostic-stop.json` và R3 report; không chạy seeds `2027/31415`.

## 7. Cleanup source và final quality gate

Sau khi v5 paths pass:

- Xóa `benchmark-spec-v4.json`.
- Xóa old R3 configs và `configs/ablations/v3.toml`, `v4.toml`.
- Promote exact selected settings thành:
  - `configs/production/deep.toml`;
  - `configs/production/hybrid.toml`.
- Bỏ generator v3/v4 and legacy RuleArtifact compatibility branches.
- Cập nhật mọi README để chỉ còn reset → v5 seed → R3 → production.
- Track và hiệu chỉnh [standard.md](E:/UIT/cv/backend/master/standard.md) theo temporal novel-purchase full-catalog protocol.
- Cập nhật `report.md`, `detail-plan.md`, `walkthrough.md` trước source freeze.

Quality gates:

```powershell
npm.cmd run test:seed-product

.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
.\.venv\Scripts\python.exe -m pytest `
  --cov=ai_service --cov-branch --cov-fail-under=85 -q

.\.venv\Scripts\python.exe scripts\check_critical_coverage.py <coverage.json>
git diff --check
```

Bắt buộc có corruption tests cho:

- missing trap direction;
- target-alignment dưới 0.40;
- order metadata/spec hash mismatch;
- semantic cohort tampering;
- diagnostic NPZ tampering;
- quality-stop report;
- GAUC-only candidate có top-k kém;
- reset làm thay đổi business order.

## 8. Production training và release

Sau khi R3 pass, commit/push và khóa worktree sạch. Không chỉnh tracked file giữa các run.

```text
deep-42-v5
→ hybrid-42-v5
→ VAL pair 42
→ deep-2027-v5
→ hybrid-2027-v5
→ VAL pair 2027
→ deep-31415-v5
→ hybrid-31415-v5
→ VAL pair 31415
→ aggregate VAL 3+3
→ TEST cả ba pair
→ aggregate TEST
→ seal selected Hybrid
→ export/verify bundle
→ ONNX parity
→ fixed-runner benchmark
```

Mỗi pair phải cùng:

- Git commit;
- dataset/spec/cohort lineage;
- comparison signature;
- seed;
- full-stat RuleArtifact.

Bất kỳ absolute/paired/semantic/cold gate nào fail:

- run/campaign dừng;
- không tạo seed kế tiếp;
- không seal/export;
- không tuyên bố Hybrid victory.

Chỉ ghi “Hybrid victory established” sau khi aggregate VAL/TEST, bundle verification, ONNX parity `<=1e-5` và fixed-runner latency đều pass.
