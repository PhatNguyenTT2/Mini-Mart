# Detail plan đóng blocker và mở Production Training Phase cho `ai-service`

## 1. Kết luận kiểm chứng hiện tại

**Trạng thái: `BLOCKED_BEFORE_PRODUCTION_TRAINING`.**

| Gate | Kết quả |
|---|---:|
| Git worktree | Dirty do Phase A hotfix đang triển khai |
| `HEAD` | `1da72054da69c485079c7e43bb13f73686c14e27` |
| `origin/main` | Commit trước hotfix, ahead/behind `0/0` |
| Ruff format/lint | PASS |
| Mypy | PASS |
| Tests | 330 passed, 2 fixed-runner skips |
| Phase A targeted contracts | 73 passed, 1 warning |
| Branch coverage | 90.06% |
| Sáu critical coverage targets | PASS |
| Snapshot audit | PASS, 823,371 events |
| Streaming probes | PASS |
| Full-stat rules | PASS, 216 directed rules |
| CUDA | RTX 3060 6 GB, Torch 2.11/CUDA 12.8 |
| Production run IDs | Cả sáu ID chưa tồn tại |
| Production environment | Chưa cấu hình trong shell hiện tại |
| Source lifecycle safety | Phase A hotfix đã triển khai; targeted/full quality gates PASS locally; commit/push còn chờ |

Source chưa được phép chạy `deep-42-v5` vì hotfix lifecycle/provenance đang nằm ngoài commit đã push. Full gate local đã PASS; hotfix vẫn phải được commit/push và xác nhận worktree sạch rồi mới chạy training.

## 2. Kết quả review hai trục

### Standards

Vi phạm README về snapshot mặc định đã được sửa và kiểm chứng trong working tree:

- [README.md](E:/UIT/cv/backend/ai-service/README.md) hiện truyền exact `--snapshot-id` và tách bootstrap/reuse; commit/push hotfix vẫn là điều kiện source-freeze.

Hai design smells không chặn training và phải hoãn tới sau campaign:

- `dict[str, str]` lineage lặp lại tại pipeline/release là possible Data Clumps/Primitive Obsession. Sau release mới thay bằng typed `ArtifactLineage`.
- `execute_command()` trong [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py:928) sở hữu quá nhiều command family. Sau release mới tách private handlers, giữ nguyên interface CLI.

### Spec

Ba finding:

1. **P0:** lifecycle hole đã được sửa cục bộ; preflight dựng loader/model/evaluator trước run creation và protected envelope bao phủ Trainer/setup/state publication.
2. **P1:** provenance đã được sửa cục bộ; Git SHA bắt buộc hợp lệ, production train yêu cầu clean worktree và HEAD bằng upstream.
3. **P1:** walkthrough/detail-plan/README đã được cập nhật cục bộ; full gate đã PASS, chỉ được chuyển trạng thái ready sau commit/push hotfix.

Tổng kết review: Standards có 1 vi phạm và 2 smells; Spec có 3 finding, nghiêm trọng nhất là lifecycle hole trước `Trainer.fit()`.

## 3. Phase A — Hotfix source bắt buộc trước training

### Task A1 — Fail-closed repository provenance

File: [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py)

Thay `_git_commit()` bằng ba private helpers:

```python
_git_output(arguments: Sequence[str]) -> str
_resolve_git_commit() -> str
_require_frozen_repository() -> str
```

`_resolve_git_commit()`:

- Chạy `git rev-parse HEAD` tại repository root.
- Require lowercase SHA-1 40 ký tự hoặc SHA-256 64 ký tự.
- Git unavailable, timeout, empty/non-hex output → `ConfigurationError`; không trả `"unknown"`.

`_require_frozen_repository()`:

1. Require `git status --porcelain` rỗng.
2. Resolve upstream bằng `git rev-parse --abbrev-ref --symbolic-full-name @{u}`.
3. Resolve upstream commit.
4. Require upstream commit bằng HEAD.
5. Trả verified HEAD SHA.

Sửa `_train()`:

```python
def _train(
    ...,
    require_frozen_source: bool,
) -> tuple[HybridTwoTowerModel, PipelineState]:
```

Call-site:

- `execute_command("train")` truyền `require_frozen_source=True`.
- `execute_command("run-all")` truyền `False`.
- Production train luôn fail trước run creation nếu worktree dirty, thiếu upstream hoặc chưa push.
- Smoke vẫn ghi commit SHA nhưng không bắt buộc worktree sạch.

### Task A2 — Đóng lifecycle hole trước `Trainer.fit()`

File: [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py)

Tổ chức lại `_train()` theo thứ tự:

```text
validate run ID/config/artifact lineage
→ verify frozen repository
→ build purchase index/sampler/loader
→ build CPU model + evaluator
→ create/load lifecycle
→ protected training session:
     transition TRAINING
     construct Trainer/device optimizer
     Trainer.fit()
     validate result.checkpoint_path
     publish PipelineState
→ return
```

Các bước trước `RunLifecycle.create()` không được tạo `<artifact_root>/runs/<run-id>`.

Đưa các operation sau lifecycle creation vào cùng một protected envelope:

- `lifecycle.transition(TRAINING)`;
- `Trainer(...)`;
- `Trainer.fit()`;
- đọc `TrainResult`;
- tạo và atomic-write `pipeline-state.json`.

Mapping cố định:

- `CatastrophicTrainingError` → summary `failed`, lifecycle `FAILED`.
- `TrainingInterruptedError`/`KeyboardInterrupt` → summary `interrupted`, lifecycle `INTERRUPTED`.
- CUDA OOM hoặc unexpected exception → summary `interrupted`, reason exact exception type, lifecycle `INTERRUPTED`.
- Preflight failure trước lifecycle → không có run directory.
- Không để trạng thái `STAGING`/`TRAINING` thiếu summary sau failure.

Tách nested summary writer thành private helper:

```python
_ensure_training_terminal_summary(
    run_dir: Path,
    *,
    action: TerminalAction,
    reason: str,
) -> None
```

Helper dùng `atomic_write_json()`; không tự viết temp/replace riêng trong pipeline.

### Task A3 — Validate Git SHA trong lifecycle

File: [run.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/run.py)

Trong `RunLifecycle.create()` và `load()`:

- Require `git_commit` match `[0-9a-f]{40}` hoặc `[0-9a-f]{64}`.
- Reject `"unknown"`, `"fixture"`, empty hoặc uppercase/non-hex values.
- Không bump model schema hoặc tạo compatibility shim.
- Giữ manifest schema hiện tại; chỉ siết invariant của field provenance.

### Task A4 — Behavioral tests

Files:

- [test_pipeline_error_edges.py](E:/UIT/cv/backend/ai-service/tests/unit/test_pipeline_error_edges.py)
- [test_pipeline_utility_edges.py](E:/UIT/cv/backend/ai-service/tests/unit/test_pipeline_utility_edges.py)
- [test_pipeline_preflight_contracts.py](E:/UIT/cv/backend/ai-service/tests/unit/test_pipeline_preflight_contracts.py)
- [test_run_lifecycle_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_run_lifecycle_contract.py)
- [test_lifecycle_item_edges.py](E:/UIT/cv/backend/ai-service/tests/unit/test_lifecycle_item_edges.py)
- [test_pipeline_cli_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_pipeline_cli_contract.py)

Thêm tests:

1. Mỗi seam `build_purchase_training_index`, sampler, iterator, model và evaluator raise → không tạo run directory.
2. `Trainer.__init__` raise sau lifecycle → `INTERRUPTED` + exact terminal summary.
3. `Trainer.fit()` catastrophic/interrupted/unexpected → lifecycle và summary khớp tuyệt đối.
4. Pipeline-state publication raise → `INTERRUPTED`, không để run thành công giả.
5. Git unavailable, empty/non-hex SHA → fail trước run creation.
6. Dirty worktree, missing upstream, upstream mismatch → fail trước run creation.
7. Clean worktree + HEAD bằng upstream → cho phép train.
8. `train` bắt buộc frozen source; `run-all` chỉ yêu cầu valid commit.
9. Lifecycle create/load reject invalid Git SHA.

Không gọi private Trainer methods trong các test mới; `Trainer.fit()` tiếp tục là external training seam.

### Exit gate Phase A

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_pipeline_error_edges.py `
  tests\unit\test_pipeline_utility_edges.py `
  tests\unit\test_pipeline_preflight_contracts.py `
  tests\unit\test_run_lifecycle_contract.py `
  tests\unit\test_lifecycle_item_edges.py `
  tests\unit\test_pipeline_cli_contract.py -q
```

Acceptance:

- Không failure.
- Không setup exception nào để lại run ở `STAGING`/`TRAINING`.
- `"unknown"` không còn được ghi vào run manifest.
- Production run không thể bắt đầu từ dirty/unpushed source.

## 4. Phase B — Chuẩn hóa README và readiness documents

### [README.md](E:/UIT/cv/backend/ai-service/README.md)

Tách runbook thành hai phần:

1. `Bootstrap immutable lineage — chỉ khi artifact chưa tồn tại`.
2. `Reuse verified campaign lineage — đường chạy mặc định`.

Trong reuse path:

- Không chứa lệnh `snapshot`, `features` hoặc `rules`.
- Pin exact IDs:
  - snapshot `benchmark-v3-20260810-9088b0f3`;
  - embedding `benchmark-v3-20260810-9088b0f3-real-f0453078fd58`;
  - rules `benchmark-v3-20260810-9088b0f3-rules-v2-ea0c72a89c41`.
- Sửa diagnostic commands:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli audit-data `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --device cpu

.\.venv\Scripts\python.exe -m ai_service.cli probe-data `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --device cpu
```

- Thêm production shell preflight: `AI_ENV`, absolute `AI_ARTIFACT_ROOT`, `AI_STORE_ID`, ba database URLs và absolute CA path.
- Ghi rõ không log secret values.
- Ghi đủ IDs cho seeds 42/2027/31415 và TEST cả ba pairs; không dùng comment mơ hồ thay cho command bắt buộc.

### [configs/ablations/README.md](E:/UIT/cv/backend/ai-service/configs/ablations/README.md)

- Giữ v3/v4 chỉ khác `training_variant`; config diff hiện tại đã xác minh đúng.
- Thêm exact train/evaluate order cho ba seeds.
- Ghi single-seed VAL fail thì dừng campaign.
- Ghi aggregate VAL không seal; TEST phải đủ ba pair.
- Không lặp bootstrap artifact commands.

### [walkthrough.md](E:/UIT/cv/backend/walkthrough.md)

Sau khi hotfix được commit/push và full gate pass:

- Thay stale `BLOCKED_UNTIL_SOURCE_FREEZE`.
- Ghi exact frozen commit mới, branch và upstream.
- Ghi kết quả quality gate mới.
- Giữ `Hybrid victory not established`.
- Trạng thái chỉ được đổi thành:

```text
READY_FOR_DEEP_42_TRAINING
```

### [detail-plan.md](E:/UIT/cv/backend/master/detail-plan.md)

- Thay HEAD cũ `6347dc5`/81 dirty entries bằng commit hotfix cuối.
- Đưa Phase A–B của kế hoạch này thành prerequisite mới.
- Không ghi `READY_FOR_SEED_42` trước khi lifecycle/provenance tests xanh.
- Giữ nguyên thresholds, six-run matrix và artifact lineage hiện tại.

## 5. Phase C — Full source freeze và execution readiness

Chạy full gate:

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts

$coverageJson = Join-Path $env:TEMP "ai-service-training-ready.json"
.\.venv\Scripts\python.exe -m pytest `
  --cov=ai_service --cov-branch `
  --cov-report=term-missing `
  --cov-report=json:$coverageJson `
  --cov-fail-under=85 -q

.\.venv\Scripts\python.exe scripts\check_critical_coverage.py $coverageJson
```

Require:

- 316+ tests pass; chỉ đúng 2 fixed-runner skips.
- Global branch coverage `>=85%`.
- Trainer/Pipeline `>=85%`.
- Checkpoint/report/release/bundle `>=90%`.
- Static invariant scans sạch.
- `git diff --check` pass.

Commit/push hotfix, sau đó:

```powershell
git status --porcelain
git rev-parse HEAD
git rev-parse origin/main
```

Require worktree sạch và HEAD bằng `origin/main`.

Production environment phải được set; shell hiện tại chưa có biến nào:

```text
AI_ENV
AI_ARTIFACT_ROOT
AI_STORE_ID
CHATBOT_DATABASE_URL
CATALOG_DATABASE_URL
ORDER_DATABASE_URL
SUPABASE_DB_CA_PATH
```

Sau đó chạy lại audit/probe/rule capability/CUDA checks. Require numerical parity hiện tại và cả sáu production run ID vẫn absent.

Chỉ khi toàn bộ Phase A–C pass mới đổi readiness thành `READY_FOR_DEEP_42_TRAINING`.

## 6. Phase D — Deep seed 42

Command:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id deep-42-v5 --variant deep_only `
  --config configs\ablations\v3.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --seed 42 --device cuda
```

Validate files:

- `artifacts/runs/deep-42-v5/run-manifest.json`
- `artifacts/runs/deep-42-v5/resolved-config.json`
- `artifacts/runs/deep-42-v5/training/history.jsonl`
- `artifacts/runs/deep-42-v5/training/summary.json`
- `artifacts/runs/deep-42-v5/checkpoints/best.pt`
- `artifacts/runs/deep-42-v5/checkpoints/last.pt`
- hai checkpoint manifests;
- `pipeline-state.json`.

Require:

- Lifecycle giữ `TRAINING` sau terminal training success.
- `git_commit` bằng frozen source commit.
- Training SHA bằng `522143ac...531a`.
- Wide gradient toàn bộ bằng zero và Wide parameters không đổi.
- Hard cache cập nhật mỗi completed epoch.
- Metrics/logit RMS finite; GAUC không dưới 0.50.
- Summary, stopping state, best manifest và `TrainResult` thống nhất.
- Không evaluation/release/bundle/Pareto artifacts.

CUDA OOM/unexpected → `INTERRUPTED`; non-finite/GAUC `<0.50` → `FAILED`. Không reuse/delete run ID.

## 7. Phase E — Hybrid seed 42 và single-seed VAL

Train:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id hybrid-42-v5 --variant hybrid `
  --config configs\ablations\v4.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --seed 42 --device cuda
```

Require:

- Training SHA `8fabea05...e968`.
- Epoch 1 Wide gradient finite và `>0`.
- Deep/Wide/Hybrid RMS finite.
- Same comparison signature `e07782c3...b3ec`.
- Best/last/summary consistency.

Sau đó:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli evaluate `
  --split val --hybrid-run-id hybrid-42-v5 `
  --deep-run-id deep-42-v5 --device cuda
```

Require toàn bộ single-seed Victory Matrix pass. Bất kỳ gate fail → dừng campaign, không tạo seed 2027.

## 8. Phase F — Ba seeds, aggregate VAL và TEST

Lặp Deep → Hybrid → VAL cho seeds `2027`, `31415`, giữ exact training signatures trong detail plan.

Sau ba pair:

1. Aggregate VAL exact 3+3; chưa seal.
2. Evaluate TEST cho cả ba pair.
3. Aggregate TEST exact 3+3.
4. Selected seed/run phải giữ nguyên từ VAL.
5. Chỉ selected Hybrid chuyển `SEALED`; hai Hybrid còn lại và ba Deep giữ `EVALUATED`.

Không sửa source/config/docs giữa các production runs. Bất kỳ sửa đổi nào làm hủy campaign và yêu cầu run IDs mới.

## 9. Phase G — Export, verify và declaration

- Export selected sealed Hybrid bằng comparison-signature namespace.
- Verify bundle v5, canonical TEST Victory Matrix SHA, exact rules arrays và ONNX parity `<=1e-5`.
- Chạy fixed-runner serving benchmark.
- Chỉ cập nhật walkthrough thành Hybrid victory khi:
  - ba VAL matrices pass;
  - aggregate VAL/TEST pass;
  - selected Hybrid sealed;
  - bundle verify pass;
  - ONNX parity và benchmark pass.

## Assumptions khóa

- Không thay scoring, objective, schema v5, v3/v4 hyperparameters, early stopping hoặc Victory thresholds.
- Provenance/lifecycle hotfix phải hoàn tất trước production training.
- Typed `ArtifactLineage` và tách `execute_command()` được hoãn tới sau campaign để tránh thay đổi rộng trước training.
- Không chạy production jobs song song trên GPU 6 GB.
- Không xóa hoặc overwrite artifact/run thất bại.
- `Trainer.fit()` tiếp tục là external training seam duy nhất.
