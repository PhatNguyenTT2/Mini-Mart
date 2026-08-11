# Detail plan production campaign `ai-service` v5 sau Phase 5

## 1. Readiness decision hiện tại

### Kết luận

- **Source implementation:** `READY_FOR_SEED_42`.
- **Production execution:** `BLOCKED_UNTIL_SOURCE_FREEZE`.
- **Hybrid victory:** chưa được xác lập.

Không phát hiện blocker chức năng mới trong luồng train/evaluate/release. Tuy
nhiên, workspace hiện có 81 thay đổi và `HEAD` đang là
`6347dc571cd959f57dc6144deb25e0ee136aaed6`. `RunLifecycle` tại
[`run.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/run.py) chỉ lưu
Git commit do [`_git_commit()`](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py)
trả về. Vì vậy không được bắt đầu production run trước khi source, tests,
configs và tài liệu đã được commit/push và worktree sạch.

### Evidence đã xác minh lại ngày 2026-08-11

| Gate | Kết quả |
|---|---:|
| Ruff format/check | PASS |
| Mypy `src scripts` | PASS |
| Tests | 316 passed, 2 fixed-runner skips |
| Branch coverage | 89.89% |
| `training/checkpoint.py` | 98.55% |
| `evaluation/report.py` | 90.83% |
| `export/bundle.py` | 98.79% |
| `evaluation/release.py` | 90.69% |
| `training/trainer.py` | 87.35% |
| `training/pipeline.py` | 85.49% |
| Audit snapshot | PASS, 823,371 events |
| Streaming probes | PASS, parity exact với walkthrough |
| Full-stat rules | PASS, 216 directed rules |
| Legacy rules | Load audit-only, training reject |
| CUDA | RTX 3060 Laptop 6 GB, Torch 2.11/CUDA 12.8 |
| Production seed-42 IDs | Chưa tồn tại |

Numerical references được khóa:

```text
permutation GAUC = 0.5015448729863483
Persona GAUC     = 0.7828269506844938
ItemCF GAUC      = 0.8229374042613712
SBERT NDCG@10    = 0.01486986701767289
```

Artifact lineage bắt buộc:

```text
snapshot ID  = benchmark-v3-20260810-9088b0f3
snapshot SHA = 1ffcebe7dbe4fe5275bd2108a71567038a8bcc52120fa26c126b3e2be3409494
embedding ID = benchmark-v3-20260810-9088b0f3-real-f0453078fd58
embedding SHA= f0453078fd588403186f80321b9ad0500d7c5ce73266f8d50de8fc3a6b09de61
rules ID     = benchmark-v3-20260810-9088b0f3-rules-v2-ea0c72a89c41
rules SHA    = cb6dacb984edd6d9210c7c7f03f9361f8590e41cd867051f704cb99e57250356
comparison   = e07782c36302d4b8665ee2356fc4c852888d5a78fb3f947b1d412152393fb3ec
```

## 2. Interface và ownership được khóa

Không thay scoring semantics, schema, configs hoặc thresholds trong campaign.

| Module | Interface dùng trong campaign | Ownership |
|---|---|---|
| [`cli.py`](E:/UIT/cv/backend/ai-service/src/ai_service/cli.py) | `train`, `evaluate`, `release-gate`, `export`, `verify-bundle` | Parse command-specific inputs |
| [`pipeline.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py) | `execute_command()` | Preflight, lifecycle, lineage và orchestration |
| [`trainer.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py) | `Trainer.fit()` | Batch train, validation, cache, checkpoint, summary |
| [`stopping.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/stopping.py) | `EarlyStoppingController` | Kill-switch, patience và best selection |
| [`checkpoint.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/checkpoint.py) | `CheckpointManager` | Atomic best/last publication và strict restore |
| [`full_catalog.py`](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/full_catalog.py) | prepared split + streaming evaluation | Metrics và Deep hard cache |
| [`gates.py`](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/gates.py) | `evaluate_single_seed()` | Single-seed Victory Matrix |
| [`report.py`](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/report.py) | immutable evaluation artifact | Pair evidence ownership |
| [`release.py`](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/release.py) | `evaluate_three_seed()` | Aggregate VAL/TEST và selected-seed lock |
| [`bundle.py`](E:/UIT/cv/backend/ai-service/src/ai_service/export/bundle.py) | export/verify | Serving bundle integrity |

`Trainer.fit()` tiếp tục là external training seam duy nhất. Không thêm test
gọi private Trainer methods và không thay đổi code giữa các production runs.

## 3. Phase 0 — Chuẩn hóa tài liệu và freeze source

### Task 0.1 — Xóa tài liệu vận hành cũ/mơ hồ

Files cần cập nhật trước commit:

- [`README.md`](E:/UIT/cv/backend/ai-service/README.md): thay ví dụ
  `benchmark-v3` bằng exact snapshot ID; dùng cùng một command style đã được
  validate trong `.venv`; nêu TEST bắt buộc cả ba pairs.
- [`configs/ablations/README.md`](E:/UIT/cv/backend/ai-service/configs/ablations/README.md):
  thay `benchmark-local`/`hybrid-42` bằng production IDs; ghi rõ v3/v4 chỉ khác
  `training_variant`.
- [`walkthrough.md`](E:/UIT/cv/backend/walkthrough.md): giữ trạng thái source
  ready nhưng thêm execution gate `BLOCKED_UNTIL_SOURCE_FREEZE`.
- File này: thay hoàn toàn Phase 5 cũ bằng campaign plan hiện tại.

Validation:

```powershell
rg -n --pcre2 "benchmark-local|--run-id\s+(deep-42|hybrid-42)(?!-v5)|--snapshot-id\s+benchmark-v3(?!-20260810-9088b0f3)|BLOCKED before production training" `
  README.md configs\ablations\README.md ..\walkthrough.md
```

Không được còn command production dùng artifact ID rút gọn. Các chuỗi cũ chỉ được
xuất hiện trong chính kế hoạch dưới dạng mô tả negative test, không phải command.

### Task 0.2 — Freeze repository provenance

Không tự động xóa, reset hoặc bỏ qua bất kỳ thay đổi nào. Review toàn bộ dirty
files, commit/push theo workflow của repository, sau đó ghi commit SHA vào
walkthrough.

Acceptance:

```powershell
git diff --check
git status --porcelain
git rev-parse HEAD
```

- `git status --porcelain` phải rỗng.
- `git rev-parse HEAD` phải khác commit cũ nếu Phase 5 chưa nằm trong commit đó.
- Commit phải tồn tại trên remote trước khi tạo `deep-42-v5`.
- Không sửa source/config sau khi Deep seed 42 bắt đầu. Mọi sửa đổi làm hủy
  campaign hiện tại và yêu cầu run IDs mới.

### Exit gate Phase 0

```text
docs exact
worktree clean
source commit pushed
full quality gate pass tại chính commit đó
deep-42-v5 absent
hybrid-42-v5 absent
```

## 4. Phase 1 — Production environment và immutable lineage preflight

### Task 1.1 — Khóa environment

Chạy từ `E:\UIT\cv\backend\ai-service`. Đặt secrets qua secret store/shell
ngoài log; không ghi chúng vào Markdown, JSON hoặc terminal transcript.

```powershell
$env:AI_ENV = "production"
$env:AI_ARTIFACT_ROOT = (Resolve-Path artifacts).Path
$env:AI_STORE_ID = "1"
# CHATBOT_DATABASE_URL, CATALOG_DATABASE_URL, ORDER_DATABASE_URL
# và SUPABASE_DB_CA_PATH phải được set ngoài source.
```

Validate:

- `SUPABASE_DB_CA_PATH` là absolute path và file tồn tại.
- Artifact root resolve đúng
  `E:\UIT\cv\backend\ai-service\artifacts`.
- Không dùng synthetic/mock adapters.
- CUDA available; không có process khác chiếm GPU đáng kể.

### Task 1.2 — Chạy lại source quality gate trên frozen commit

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
$coverageJson = Join-Path $env:TEMP "ai-service-seed42-readiness.json"
.\.venv\Scripts\python.exe -m pytest --cov=ai_service --cov-branch `
  --cov-report=term-missing --cov-report=json:$coverageJson `
  --cov-fail-under=85 -q
.\.venv\Scripts\python.exe scripts\check_critical_coverage.py $coverageJson
```

Acceptance giữ nguyên 316 pass/2 fixed-runner skips hoặc cao hơn, không failure;
global branch coverage `>=85%`; sáu critical-file targets pass.

### Task 1.3 — Re-audit và re-probe

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli audit-data `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --device cpu

.\.venv\Scripts\python.exe -m ai_service.cli probe-data `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --device cpu
```

Acceptance:

- Audit `training_suitability_passed=true`, `gate_failures=[]`.
- Counts đúng 823,371/5,000/5,200/250.
- Bốn numerical references sai lệch tuyệt đối `<=1e-6`.
- Permutation GAUC trong `[0.48,0.52]`.

### Task 1.4 — Config/signature preflight

Files: [`v3.toml`](E:/UIT/cv/backend/ai-service/configs/ablations/v3.toml),
[`v4.toml`](E:/UIT/cv/backend/ai-service/configs/ablations/v4.toml).

Resolved production values:

```text
objective=sampled_softmax
max_epochs=30
batch_size=2048
explicit_negative_ratio=16
validation_user_batch_size=512
max_history_items=32
early_stopping_patience=4
min_delta=1e-4
max_wall_minutes=90
```

Expected signatures:

| Seed | Deep training SHA | Hybrid training SHA |
|---:|---|---|
| 42 | `522143ac18a73b6485a0cd0c4edd7d1e339eca0ede2b26cbe04d1284f2a5531a` | `8fabea050692d52102f276c76ef0421b9fdaa0e03985e86fbb5fac20a794e968` |
| 2027 | `8e9e7a910a4174dcd9e02162b8ba974530be59a560df135ac7d70731768c3c76` | `f47852f3b4e6dc956f84fb1f8dc746e6ac4234201879507e67f316fed1aa70c9` |
| 31415 | `2e9f8b222ce20eb1fd033e7bdfe00e104ab367c10c851139a0fbf49825478427` | `552a7fc5c9429dc94beca5ec1c1514b064225d19423878337f4e0f232bd25e06` |

Tất cả sáu run phải có comparison signature
`e07782c36302d4b8665ee2356fc4c852888d5a78fb3f947b1d412152393fb3ec`.

### Exit gate Phase 1

- Selectors resolve duy nhất exact real embedding và full-stat rules nêu trên.
- `require_training_capability()` pass; legacy rules reject.
- CUDA/Torch pass; production run IDs absent.
- Không có release gate cũ trong comparison namespace.

## 5. Phase 2 — Deep seed 42 capacity canary và production run

### Source ownership

- [`pipeline.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py):
  artifact selector, lifecycle và exception mapping.
- [`trainer.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/trainer.py):
  one validation/cache refresh per epoch và Deep/Wide invariant.
- [`stopping.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/stopping.py):
  GAUC kill-switch/patience.
- [`checkpoint.py`](E:/UIT/cv/backend/ai-service/src/ai_service/training/checkpoint.py):
  best/last checkpoint.

Không sửa các files này trong campaign; chỉ quan sát artifacts chúng tạo.

### Command

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id deep-42-v5 --variant deep_only `
  --config configs\ablations\v3.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --seed 42 --device cuda
```

### Epoch-1 capacity gate

Smoke trước đó chỉ dùng 128 users/256 items/batch 128; vì vậy epoch đầu của
Deep seed 42 là capacity canary cho batch 2048 và catalog 5,200 trên GPU 6 GB.

Theo dõi:

```text
artifacts/runs/deep-42-v5/run-manifest.json
artifacts/runs/deep-42-v5/training/history.jsonl
artifacts/runs/deep-42-v5/checkpoints/last.pt.manifest.json
```

Epoch 1 chỉ pass khi:

- mọi loss/logit/gradient/parameter finite;
- `wide_gradient_norm == 0`;
- Wide parameters byte-identical;
- `model_hard_cache_updated=true`;
- Deep/Hybrid/Wide logit RMS finite;
- validation GAUC `>=0.50`;
- `last.pt` strict-load được; `best.pt` tồn tại nếu controller chọn epoch 1.

Stop ngay khi CUDA OOM, non-finite, GAUC `<0.50`, sampler/cache error hoặc run
chuyển `FAILED`/`INTERRUPTED`. Không tự giảm batch size. Nếu cần đổi capacity
config, dừng campaign, sửa đồng thời v3/v4, dùng run IDs mới và chạy lại Phase
0–1 vì comparison signature sẽ thay đổi.

### Completion gate Deep 42

Sau terminal success/plateau:

- lifecycle cố ý giữ `TRAINING` để chờ paired evaluation;
- `pipeline-state.json` trỏ exact `checkpoints/best.pt`;
- summary, best manifest và stopping state có cùng best epoch/GAUC/NDCG/HR;
- `last.pt` chứa current epoch nhưng giữ selected stopping state;
- không có Pareto/release-candidate/evaluation/bundle.

Resume chỉ được dùng khi lifecycle là `INTERRUPTED`, config/signature/lineage
không đổi và `last.pt` + history còn nguyên:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id deep-42-v5 --variant deep_only `
  --config configs\ablations\v3.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --seed 42 --device cuda --resume
```

Không resume run `FAILED` và không reuse/delete immutable run ID.

## 6. Phase 3 — Hybrid seed 42

Chỉ chạy khi Deep 42 completion gate pass.

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id hybrid-42-v5 --variant hybrid `
  --config configs\ablations\v4.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --seed 42 --device cuda
```

Epoch-1 Hybrid gate:

- `wide_gradient_norm` finite và `>0`;
- Wide parameters thay đổi so với zero-init baseline;
- Deep/Wide/Hybrid RMS finite;
- model-hard cache cập nhật đúng một lần;
- validation GAUC `>=0.50`;
- không non-finite/OOM.

Completion gate giống Deep, cộng thêm:

- Hybrid và Deep comparison signatures giống exact SHA đã khóa;
- lineage ba parent SHA giống nhau;
- seed đều bằng 42;
- cả hai checkpoint schema v5 và strict-load pass.

## 7. Phase 4 — Single-seed validation pair 42

### Command

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli evaluate `
  --split val --hybrid-run-id hybrid-42-v5 `
  --deep-run-id deep-42-v5 --device cuda
```

### Artifact ownership

[`report.py`](E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/report.py)
phải publish duy nhất dưới:

```text
artifacts/runs/hybrid-42-v5/evaluation/val/
  report.json
  per-user-metrics.npz
  victory-matrix.json
```

Deep state tham chiếu cùng immutable matrix; không có NPZ duplicate dưới Deep.

### Victory gate acceptance

- Random GAUC nằm `[0.48,0.52]` và CI chứa 0.5.
- Hybrid GAUC `>=0.75`.
- Hybrid HR@10 thắng strongest competitor với paired CI lower `>0`.
- Hybrid NDCG@10 thắng Apriori với paired CI lower `>0`.
- Semantic traps `10/10`.
- Cold parity pass tại `wide_zero_atol=1e-7` và `cold_score_atol=1e-6`.
- Matrix canonical SHA, NPZ SHA, pair IDs, checkpoint SHAs và lineage verified.

VAL pass: cả hai lifecycle vẫn `TRAINING`, state có paired IDs và
`validation_gate_passed=true`. VAL fail: Hybrid chuyển `FAILED`, Deep giữ
`TRAINING`; dừng toàn bộ campaign và không train seed 2027.

Không chạy lại cùng pair/split khi immutable evaluation directory đã tồn tại.
Nếu command crash sau publication nhưng trước state update, dừng và thực hiện
recovery review; không xóa artifact để retry.

## 8. Phase 5 — Seeds 2027 và 31415

Chỉ mở khi seed-42 VAL matrix pass. Với từng seed, thứ tự bắt buộc là:

```text
Deep train → validate completion → Hybrid train → validate completion → VAL pair
```

Commands thay seed/run ID tương ứng:

```text
deep-2027-v5 / hybrid-2027-v5 / seed 2027
deep-31415-v5 / hybrid-31415-v5 / seed 31415
```

Không chạy hai training jobs song song trên GPU 6 GB. Không chạy seed kế tiếp
nếu pair hiện tại fail. Mỗi run phải khớp training SHA trong bảng Phase 1 và
comparison SHA chung.

## 9. Phase 6 — Aggregate validation 3+3

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli release-gate `
  --split val `
  --hybrid-run-ids hybrid-42-v5 hybrid-2027-v5 hybrid-31415-v5 `
  --deep-run-ids deep-42-v5 deep-2027-v5 deep-31415-v5
```

Validate
`artifacts/releases/e07782c36302d4b8665ee2356fc4c852888d5a78fb3f947b1d412152393fb3ec/validation-gate.json`:

- exact three seeds and six distinct run IDs;
- exact lineage/comparison signature;
- three single-seed VAL matrices pass và user IDs giống nhau;
- aggregate GAUC CI lower `>=-0.002`;
- aggregate NDCG CI lower `>=-0.001`;
- aggregate HR CI lower `>=-0.001`;
- selected run theo GAUC → NDCG → HR → smaller seed;
- report canonical hash pass;
- chưa run nào được seal.

Aggregate VAL fail: dừng; không mở TEST.

## 10. Phase 7 — TEST cho cả ba pairs

Validation gate pass là precondition bắt buộc. Chạy cả ba:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli evaluate `
  --split test --hybrid-run-id hybrid-42-v5 `
  --deep-run-id deep-42-v5 --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli evaluate `
  --split test --hybrid-run-id hybrid-2027-v5 `
  --deep-run-id deep-2027-v5 --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli evaluate `
  --split test --hybrid-run-id hybrid-31415-v5 `
  --deep-run-id deep-31415-v5 --device cuda
```

Mỗi TEST pair phải pass cùng single-seed gates như VAL. Pass chuyển cả pair
sang `EVALUATED`; fail chuyển Hybrid sang `FAILED`, Deep sang `EVALUATED` và
dừng release.

## 11. Phase 8 — Aggregate TEST, seal và selected-seed lock

```powershell
$releaseJson = .\.venv\Scripts\python.exe -m ai_service.cli release-gate `
  --split test `
  --hybrid-run-ids hybrid-42-v5 hybrid-2027-v5 hybrid-31415-v5 `
  --deep-run-ids deep-42-v5 deep-2027-v5 deep-31415-v5
$release = $releaseJson | ConvertFrom-Json
$selectedRun = $release.selected_run_id
```

Acceptance:

- exact validation finalist set/signature/report hash;
- selected run/seed không đổi so với aggregate VAL;
- aggregate TEST gates pass;
- `release-gate.json` immutable và canonical hash pass;
- chỉ selected Hybrid chuyển `SEALED`;
- hai Hybrid runner-up và ba Deep giữ `EVALUATED`.

## 12. Phase 9 — Export, verification và serving benchmark

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli export `
  --run-id $selectedRun --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli verify-bundle `
  --run-id $selectedRun
```

Validate:

- bundle schema v5, Hybrid variant;
- canonical TEST Victory Matrix SHA bằng release report;
- exact file allowlist và all checksums pass;
- mapping/profile/item/rule shapes, CSR bounds, statistics và q99 pass;
- ONNX parity `<=1e-5`;
- no placeholder SHA;
- selected PipelineState có verified `bundle_path`.

Fixed-runner benchmark:

```powershell
$env:AI_BENCHMARK_BUNDLE_PATH = <absolute-verified-bundle-path>
.\.venv\Scripts\python.exe -m pytest `
  tests\benchmark\test_serving_performance.py -q
```

Hai skips hiện tại phải chuyển thành pass trước production deployment.

## 13. Phase 10 — Walkthrough và declaration

Chỉ sau Phase 9 mới cập nhật [`walkthrough.md`](E:/UIT/cv/backend/walkthrough.md)
thành Hybrid victory report. Ghi exact:

- frozen Git commit;
- sáu run IDs và checkpoint SHAs;
- three VAL matrices + aggregate VAL;
- three TEST matrices + aggregate TEST;
- selected run/seed và canonical matrix SHA;
- bundle ID/SHA, ONNX parity, latency/throughput benchmark;
- final HR@10, NDCG@10, GAUC với paired confidence intervals.

Không tuyên bố Hybrid thành công nếu thiếu bất kỳ evidence nào.

## 14. Failure/resume decision matrix

| Failure point | Lifecycle/artifact action | Được tiếp tục? |
|---|---|---|
| Preflight trước run creation | Không tạo run directory | Sửa preflight rồi chạy lại |
| Training wall/keyboard interruption | `INTERRUPTED`, summary + last checkpoint | Chỉ `--resume` exact run/config/lineage |
| CUDA OOM hoặc unexpected error | `INTERRUPTED` | Dừng review; không tự đổi config/resume |
| Non-finite hoặc GAUC `<0.50` | `FAILED` | Không resume/reuse ID |
| Single-seed VAL fail | Hybrid `FAILED` | Dừng toàn campaign |
| Aggregate VAL fail | Immutable evidence giữ nguyên | Không mở TEST |
| Single-seed TEST fail | Hybrid `FAILED`, Deep `EVALUATED` | Không aggregate/seal |
| Aggregate TEST fail | Không seal/export | Dừng release |
| Bundle/parity/benchmark fail | Giữ bundle evidence để audit | Không deploy/claim victory |

## Assumptions khóa

- Không thay đổi v3/v4, scoring, objective, schema v5, early stopping hoặc gate
  thresholds trong campaign.
- Early stopping kill-switch là GAUC 0.50; `minimum_gauc=0.75` thuộc Victory
  Gate, không phải per-epoch kill threshold.
- Không xóa artifact/run thất bại; dùng immutable audit evidence và run ID mới
  sau khi có plan sửa cụ thể.
- Không chạy training song song trên GPU hiện tại.
- Không seal/export trước aggregate TEST pass.
