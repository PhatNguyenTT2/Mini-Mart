# Detail plan đóng final blockers và chuẩn bị Production Training Campaign

## 1. Kết luận kiểm duyệt hiện tại

Trạng thái chính xác: `BLOCKED_BEFORE_PRODUCTION_TRAINING`.

Các gate đã xác nhận trên commit đã push `5ceeded10f3d256543f2a831642d354e8346507f`:

| Gate | Kết quả |
|---|---:|
| Worktree/source freeze | Phase 0 đã validate; phải xác nhận clean và đồng bộ upstream trước training |
| Baseline review | `5ceeded10...` đã push; final frozen revision lấy bằng `git rev-parse HEAD` sau Phase 0 |
| Ruff format/lint | PASS |
| Mypy | PASS |
| Tests | 352 passed, 2 fixed-runner skips |
| Phase 0/campaign-freeze targeted contracts | 77 passed |
| Branch coverage | 89.99% |
| Critical coverage | Cả sáu file PASS |
| Audit snapshot | PASS, 823,371 events |
| Streaming probes | PASS, parity giữ nguyên |
| Full-stat rules | PASS, 216 rules |
| Legacy rules | Audit-only, training reject |
| CUDA | RTX 3060 6 GB, Torch 2.11/CUDA 12.8 |
| Production run IDs | Cả sáu chưa tồn tại |
| Production environment | Bảy biến bắt buộc chưa được cấu hình |
| Source lifecycle safety | Phase 0 hardening PASS; final source-freeze verification còn bắt buộc |

### Standards review

- Resume commit lock, strict `last.pt` preflight và cross-run source revision lock đã được triển khai; cần rerun final freeze gate trên revision đã push.
- Hai design smells không độc lập chặn training:
  - Git/process policy đã được gom vào deep module `training/provenance.py`; typed lineage và command dispatcher vẫn hoãn sau campaign.
- Không còn Standards blocker đã biết sau Phase 0; source freeze vẫn là execution gate.

### Spec review

- P0: transition/setup lifecycle hole đã được sửa cục bộ; transition hiện nằm trong protected envelope và failures được terminalize theo status contract.
- P1: resume exact source commit lock đã được thêm.
- P1: paired evaluation và aggregate release hiện reject mixed source revisions; readiness chỉ mở sau source-freeze và production-environment gate.
- Chưa có Spec blocker còn lại đã biết trong Phase 0; final freeze vẫn bắt buộc.

Không bắt đầu `deep-42-v5` trước khi Phase 0–2 bên dưới hoàn tất.

---

## 2. Phase 0 — Đóng source blockers cuối cùng

### Task 0.1 — Tách Git provenance thành deep module

Tạo mới:

[provenance.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/provenance.py)

Thêm internal contract:

```python
@dataclass(frozen=True)
class SourceRevision:
    commit_sha: str
    upstream_ref: str | None
```

Thêm functions:

```python
is_git_commit_sha(value: object) -> TypeGuard[str]
resolve_source_revision() -> SourceRevision
require_frozen_source_revision() -> SourceRevision
```

Implementation:

- Chỉ chấp nhận lowercase SHA-1 40 ký tự hoặc SHA-256 64 ký tự.
- `_git_output()` chạy Git tại repository root, timeout 5 giây.
- Git unavailable, timeout, empty/non-hex output → `ConfigurationError`.
- `require_frozen_source_revision()` yêu cầu:
  - `git status --porcelain --untracked-files=normal` rỗng;
  - upstream tồn tại;
  - upstream commit hợp lệ;
  - upstream commit bằng HEAD.
- `resolve_source_revision()` dùng cho synthetic smoke: SHA vẫn bắt buộc hợp lệ nhưng không yêu cầu worktree sạch/upstream.
- Không expose module qua package public API.

Sửa [pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py):

- Xóa `_GIT_SHA_PATTERN`, `_git_output()`, `_resolve_git_commit()`, `_require_frozen_repository()` và `_git_commit()`.
- Production `_train(..., require_frozen_source=True)` dùng `require_frozen_source_revision()`.
- `run-all` dùng `resolve_source_revision()`.
- Chỉ truyền `revision.commit_sha` vào lifecycle.

Sửa [run.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/run.py):

- Xóa `_GIT_COMMIT_PATTERN`.
- Dùng chung `is_git_commit_sha()` khi create/load manifest.
- Vẫn chuyển invalid manifest thành `ArtifactIntegrityError`; không để `ConfigurationError` rò khỏi artifact loader.
- Không đổi manifest schema hoặc `MODEL_SCHEMA_VERSION`.

### Task 0.2 — Atomic publication cho run lifecycle

File:

[run.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/run.py)

Sửa `RunLifecycle.create()`:

1. Validate run ID, lineage, signatures và Git commit trước filesystem mutation.
2. Dựng `resolved-config.json` và `run-manifest.json` trong temporary sibling directory dưới `runs/`.
3. Flush/fsync cả hai file.
4. Verify lại temporary documents bằng private validation helper.
5. Destination tồn tại → reject.
6. Atomic rename temporary directory thành final run directory.
7. Mọi failure trước rename phải cleanup temporary directory và không để final run directory.

Sửa `RunLifecycle.transition()`:

- Không mutate `self.document` trước persistence.
- Dựng `candidate_document = {**self.document, ...}`.
- Atomic-write candidate manifest.
- Chỉ sau khi write thành công mới gán `self.document = candidate_document`.
- Giữ nguyên transition map; đặc biệt không thêm `STAGING -> INTERRUPTED`.

### Task 0.3 — Đưa transition vào protected training envelope

File:

[pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py)

Flow cuối:

```text
artifact/config/source preflight
→ build loader/model/evaluator
→ create/load lifecycle
→ validate resume provenance
→ protected try:
     transition TRAINING
     construct Trainer
     Trainer.fit
     validate best checkpoint path
     publish PipelineState
→ return
```

Thêm private helper:

```python
_terminalize_training_session(
    lifecycle: RunLifecycle,
    run_dir: Path,
    *,
    requested_action: TerminalAction,
    reason: str,
) -> None
```

Mapping:

- Transition sang `TRAINING` thất bại khi lifecycle vẫn `STAGING`:
  - ghi summary `FAILED`;
  - `STAGING -> FAILED`;
  - reason là exact exception type.
- Catastrophic trong `TRAINING`:
  - summary `FAILED`;
  - lifecycle `FAILED`;
  - giữ exact catastrophic reason.
- Wall/keyboard/interruption trong `TRAINING`:
  - summary/lifecycle `INTERRUPTED`;
  - giữ exact reason.
- CUDA OOM hoặc unexpected trong `TRAINING`:
  - summary/lifecycle `INTERRUPTED`;
  - reason là exact exception type.
- Nếu terminal persistence cũng thất bại:
  - raise `ArtifactIntegrityError` với original exception trong chain;
  - không báo success hoặc tạo `pipeline-state.json`.

### Task 0.4 — Khóa resume vào exact source revision

File:

[pipeline.py](E:/UIT/cv/backend/ai-service/src/ai_service/training/pipeline.py)

Trong nhánh `resume=True`, trước transition:

```python
recorded_commit = lifecycle.document["git_commit"]
if recorded_commit != revision.commit_sha:
    raise ArtifactIntegrityError(
        "resume run Git commit differs from the frozen source revision"
    )
```

Ngoài commit, tiếp tục require:

- Lifecycle đang `INTERRUPTED`.
- Same run ID.
- Same artifact lineage.
- Same training signature.
- Same variant.
- `checkpoints/last.pt` tồn tại và strict-load được.

Commit mismatch phải:

- Giữ lifecycle `INTERRUPTED`.
- Không sửa summary/history/checkpoint.
- Không tạo pipeline state mới.
- Không cho phép compatibility override.

Khóa source revision còn được áp dụng tại hai campaign boundary:

- `training/pipeline.py::_evaluate_pair()` reject nếu Deep và Hybrid không có
  cùng `run-manifest.git_commit`.
- `evaluation/release.py::evaluate_three_seed()` require cả sáu finalist dùng
  cùng một Git commit trước khi load/publish aggregate gate.
- Commit mismatch không được tạo evaluation artifact, release report, seal hoặc
  bundle.

### Task 0.5 — Tests cho provenance/lifecycle

Tạo:

[test_provenance_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_provenance_contract.py)

Bao phủ:

- Valid SHA-1/SHA-256.
- Empty, uppercase, non-hex và wrong-length SHA.
- Git unavailable/timeout.
- Dirty worktree.
- Missing upstream.
- Invalid upstream SHA.
- HEAD/upstream mismatch.
- Clean synchronized repository.
- Smoke revision không yêu cầu upstream nhưng vẫn yêu cầu valid HEAD.

Cập nhật:

- [test_pipeline_error_edges.py](E:/UIT/cv/backend/ai-service/tests/unit/test_pipeline_error_edges.py):
  - transition `TRAINING` raise trước persistence → final lifecycle `FAILED`;
  - exact terminal summary;
  - không tạo pipeline state;
  - Trainer constructor/fit/state publication mappings tiếp tục pass.
- [test_pipeline_preflight_recovery.py](E:/UIT/cv/backend/ai-service/tests/unit/test_pipeline_preflight_recovery.py):
  - resume commit mismatch;
  - same commit pass đến Trainer seam;
  - commit mismatch không mutate interrupted run.
- [test_run_lifecycle_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_run_lifecycle_contract.py):
  - create failure giữa hai files không để final directory;
  - transition write failure không mutate in-memory document;
  - temporary directories được cleanup;
  - invalid Git SHA create/load.
- [test_pipeline_cli_contract.py](E:/UIT/cv/backend/ai-service/tests/unit/test_pipeline_cli_contract.py):
  - `train` bắt buộc frozen revision;
  - `run-all` dùng non-frozen valid revision.
- Di chuyển Git-specific tests khỏi `test_pipeline_utility_edges.py` sang provenance test; không giữ duplicate tests.

### Exit gate Phase 0

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_provenance_contract.py `
  tests\unit\test_pipeline_error_edges.py `
  tests\unit\test_pipeline_preflight_recovery.py `
  tests\unit\test_run_lifecycle_contract.py `
  tests\unit\test_pipeline_cli_contract.py -q
```

Acceptance:

- Không run directory partial.
- Không `STAGING`/`TRAINING` thiếu terminal summary sau lỗi protected session.
- Resume khác commit bị reject trước transition.
- Git SHA regex chỉ còn một implementation.
- Pipeline không trực tiếp gọi `subprocess.run()`.

---

## 3. Phase 1 — Cập nhật readiness documents và source freeze

### [walkthrough.md](E:/UIT/cv/backend/walkthrough.md)

Cập nhật theo hai bước:

1. Trong lúc Phase 0 đang triển khai, giữ `BLOCKED_BEFORE_PRODUCTION_TRAINING` và ghi:
   - reviewed pushed baseline `5ceeded10f3d256543f2a831642d354e8346507f`;
   - hai blocker mới;
   - production environment chưa cấu hình;
   - Hybrid victory chưa được thiết lập.
2. Chỉ sau Phase 0–2 pass mới đổi thành:
   - `READY_FOR_DEEP_42_TRAINING`;
   - exact final quality results;
   - final frozen commit được lấy từ `git rev-parse HEAD`;
   - sáu production IDs vẫn absent;
   - final CUDA smoke ID.

Không cập nhật walkthrough giữa các production runs vì việc đó làm dirty worktree và production train tiếp theo sẽ bị reject.

### [detail-plan.md](E:/UIT/cv/backend/master/detail-plan.md)

Thay phần trạng thái cũ:

- Worktree: clean.
- Pushed baseline: `5ceeded10...`.
- Tests: 345 passed, 2 skips.
- Phase 0 targeted contracts: 64 passed.
- Coverage: 90.04%.
- Source readiness: Phase 0 blockers fixed locally; commit/push and environment gate remain.
- Environment: unset.
- Xóa nội dung nói hotfix chưa commit/push.
- Mark Phase A/B cũ là completed.
- Thay phần “next phase” bằng Phase 0–7 của plan này.
- Ghi đủ sáu training signatures:

| Run | Training signature |
|---|---|
| `deep-42-v5` | `522143ac18a73b6485a0cd0c4edd7d1e339eca0ede2b26cbe04d1284f2a5531a` |
| `hybrid-42-v5` | `8fabea050692d52102f276c76ef0421b9fdaa0e03985e86fbb5fac20a794e968` |
| `deep-2027-v5` | `8e9e7a910a4174dcd9e02162b8ba974530be59a560df135ac7d70731768c3c76` |
| `hybrid-2027-v5` | `f47852f3b4e6dc956f84fb1f8dc746e6ac4234201879507e67f316fed1aa70c9` |
| `deep-31415-v5` | `2e9f8b222ce20eb1fd033e7bdfe00e104ab367c10c851139a0fbf49825478427` |
| `hybrid-31415-v5` | `552a7fc5c9429dc94beca5ec1c1514b064225d19423878337f4e0f232bd25e06` |

Shared comparison signature:

```text
e07782c36302d4b8665ee2356fc4c852888d5a78fb3f947b1d412152393fb3ec
```

### [README.md](E:/UIT/cv/backend/ai-service/README.md)

Giữ runbook hiện tại và bổ sung resume policy:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id <interrupted-run-id> --variant <same-variant> `
  --config <same-config> --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --seed <same-seed> --device cuda --resume
```

Ghi rõ:

- Chỉ lifecycle `INTERRUPTED` được resume.
- HEAD phải bằng `run-manifest.git_commit`.
- Không đổi config, seed, variant, lineage hoặc source.
- `FAILED` không được resume.
- OOM chỉ được resume nếu có thể chạy lại same config; muốn đổi batch size phải tạo campaign/config/run IDs mới.
- Không xóa hoặc reuse run ID.

### [configs/ablations/README.md](E:/UIT/cv/backend/ai-service/configs/ablations/README.md)

Bổ sung một đoạn ngắn:

- Same-commit resume policy.
- Không chỉnh v3/v4 sau khi campaign bắt đầu.
- Không chỉnh tracked docs giữa sáu training runs.

### Documentation validation

```powershell
rg -n "1da72054|hotfix.*commit/push còn chờ|Dirty do Phase A" `
  ..\walkthrough.md

rg -n --pcre2 -- `
  "--snapshot-id\s+benchmark-v3(?!-20260810-9088b0f3)|--run-id\s+(deep-42|hybrid-42)(?!-v5)" `
  README.md configs\ablations\README.md
```

Cả hai scan phải rỗng.

---

## 4. Phase 2 — Final code, data và CUDA readiness gate

### Full quality gate

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts

$coverageJson = Join-Path $env:TEMP "ai-service-seed42-ready.json"
.\.venv\Scripts\python.exe -m pytest `
  --cov=ai_service --cov-branch `
  --cov-report=term-missing `
  --cov-report=json:$coverageJson `
  --cov-fail-under=85 -q

.\.venv\Scripts\python.exe scripts\check_critical_coverage.py $coverageJson
git diff --check
```

Require:

- Ít nhất 330 tests pass.
- Đúng 2 fixed-runner skips.
- Global branch coverage `>=85%`.
- Trainer/Pipeline `>=85%`.
- Checkpoint/report/release/bundle `>=90%`.
- Không giảm threshold hoặc thêm coverage exclusion.

Static invariants:

```powershell
rg -n "pareto|release-candidate|scores_by_user|_wide_logit_scale|Softplus" src
rg -n "experiment_signature.*fallback|file_sha256\(.*victory" src
```

Phải rỗng.

### Source freeze

Sau khi Phase 0/1 được commit và push:

```powershell
git status --porcelain
$frozenCommit = git rev-parse HEAD
$upstreamCommit = git rev-parse '@{u}'
git rev-list --left-right --count HEAD...@{u}
```

Require:

- Worktree sạch.
- `$frozenCommit == $upstreamCommit`.
- Ahead/behind `0/0`.
- Không sửa source/config/docs từ thời điểm này tới sau aggregate TEST.

### Diagnostic CUDA smoke

Chạy trong shell diagnostic, không dùng `AI_ENV=production`:

```powershell
$env:AI_ENV = "development"
.\.venv\Scripts\python.exe -m ai_service.cli run-all `
  --config configs\smoke\v5.toml `
  --source synthetic --embedding-source mock `
  --run-id smoke-v5-ready-<UTC-timestamp> `
  --seed 42 --device cuda
```

Require:

- Một epoch.
- `best.pt`/`last.pt` strict-load.
- Finite metrics.
- No evaluation/release/seal/export/bundle.
- Run manifest ghi valid frozen commit.
- Không tạo production run ID.

### Production shell preflight

Mở shell mới và cấu hình, không in secret values:

```powershell
$env:AI_ENV = "production"
$env:AI_ARTIFACT_ROOT = (Resolve-Path artifacts).Path
$env:AI_STORE_ID = "1"
# Set externally:
# CHATBOT_DATABASE_URL
# CATALOG_DATABASE_URL
# ORDER_DATABASE_URL
# SUPABASE_DB_CA_PATH
```

Require:

- Bảy biến đều present.
- `AI_ARTIFACT_ROOT` absolute và trỏ đúng campaign artifact root.
- CA path absolute và file tồn tại.
- Không log database URL values.

### Data readiness

Chạy lại audit/probes và require exact reference:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli audit-data `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --device cpu

.\.venv\Scripts\python.exe -m ai_service.cli probe-data `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --device cpu
```

Acceptance:

- Events `823371`.
- Permutation GAUC `0.5015448729863483`.
- Persona GAUC `0.7828269506844938`.
- ItemCF GAUC `0.8229374042613712`.
- SBERT NDCG@10 `0.01486986701767289`.
- Absolute parity error `<=1e-6`.

Rule artifact:

```text
benchmark-v3-20260810-9088b0f3-rules-v2-ea0c72a89c41
```

Require full statistics, schema `2.0.0`, min count `3`, min lift `1.0`, 216 rules và training capability pass. Legacy artifact phải tiếp tục bị training reject.

Confirm cả sáu production IDs absent.

Chỉ khi tất cả điều kiện trên pass mới đổi readiness thành `READY_FOR_DEEP_42_TRAINING`.

---

## 5. Phase 3 — Deep seed 42

Command:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id deep-42-v5 --variant deep_only `
  --config configs\ablations\v3.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --seed 42 --device cuda
```

Validate:

- `run-manifest.git_commit == $frozenCommit`.
- Training signature đúng `522143ac...531a`.
- Lifecycle vẫn `TRAINING` sau successful Trainer completion.
- Summary action là `completed` hoặc plateau hợp lệ.
- Mỗi history row:
  - tất cả losses/metrics/logit RMS finite;
  - `wide_gradient_norm == 0`;
  - `model_hard_cache_updated == true`;
  - GAUC `>=0.50`.
- Wide parameters không đổi.
- `best.pt`/`last.pt` và hai manifests tồn tại.
- Best summary, stopping state và best manifest khớp epoch/GAUC/NDCG/HR.
- `pipeline-state.json.checkpoint_path` là exact `checkpoints/best.pt`.
- Không evaluation/release/Pareto/bundle.

Failure policy:

- `FAILED`: dừng campaign; không resume hoặc reuse ID.
- `INTERRUPTED`: chỉ resume cùng commit/config/seed bằng `--resume`.
- OOM cần đổi batch size: không resume; dừng và lập campaign/run IDs mới.

---

## 6. Phase 4 — Hybrid seed 42 và single-seed VAL gate

Train Hybrid:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id hybrid-42-v5 --variant hybrid `
  --config configs\ablations\v4.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --seed 42 --device cuda
```

Validate:

- Training signature `8fabea05...e968`.
- Comparison signature exact `e07782c3...b3ec`.
- Epoch 1 Wide gradient finite và `>0`.
- Wide parameters thay đổi.
- Deep/Wide/Hybrid logit RMS finite.
- Hard cache cập nhật mỗi completed epoch.
- Best/last/summary/state consistency.
- Same commit và artifact lineage với Deep seed 42.

VAL:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli evaluate `
  --split val `
  --hybrid-run-id hybrid-42-v5 `
  --deep-run-id deep-42-v5 `
  --device cuda
```

Require single-seed matrix:

- Random GAUC trong `[0.48,0.52]`, CI chứa `0.5`.
- Hybrid GAUC `>=0.75`.
- Hybrid HR thắng strongest competitor với paired CI lower `>0`.
- Hybrid NDCG thắng Apriori với paired CI lower `>0`.
- Semantic traps `10/10`.
- Cold parity pass.
- Immutable Hybrid-owned evaluation artifact verified.

Bất kỳ gate fail → dừng campaign; không tạo seed 2027.

---

## 7. Phase 5 — Seeds 2027 và 31415

Thứ tự bắt buộc:

```text
deep-2027-v5
→ hybrid-2027-v5
→ VAL pair 2027
→ deep-31415-v5
→ hybrid-31415-v5
→ VAL pair 31415
```

Dùng cùng commands như seed 42, thay run ID và seed.

Sau mỗi train:

- Check exact training signature theo bảng Phase 1.
- Same frozen commit, lineage và comparison signature.
- Áp dụng Deep/Wide invariants tương ứng.
- Không chạy bước kế tiếp nếu run failed/interrupted hoặc VAL fail.

Không chỉnh bất kỳ tracked file nào giữa các runs.

---

## 8. Phase 6 — Aggregate VAL, TEST 3+3 và release

Aggregate VAL:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli release-gate `
  --split val `
  --hybrid-run-ids hybrid-42-v5 hybrid-2027-v5 hybrid-31415-v5 `
  --deep-run-ids deep-42-v5 deep-2027-v5 deep-31415-v5
```

Require:

- Exact seed set `{42,2027,31415}`.
- Exact three paired artifacts verified.
- Aggregate GAUC/NDCG/HR gates pass.
- Selected seed/run recorded.
- Chưa run nào `SEALED`.

Evaluate TEST cho cả ba pair, không chỉ selected validation seed:

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

Aggregate TEST:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli release-gate `
  --split test `
  --hybrid-run-ids hybrid-42-v5 hybrid-2027-v5 hybrid-31415-v5 `
  --deep-run-ids deep-42-v5 deep-2027-v5 deep-31415-v5
```

Require:

- Selected seed/run giữ nguyên từ VAL.
- Selected TEST matrix SHA verified.
- Chỉ selected Hybrid `SEALED`.
- Hai Hybrid runner-up và ba Deep giữ `EVALUATED`.

---

## 9. Phase 7 — Export, runtime benchmark và tài liệu kết quả

Export/verify selected Hybrid:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli export `
  --run-id <selected-hybrid-run-id> --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli verify-bundle `
  --run-id <selected-hybrid-run-id>
```

Require:

- Bundle schema v5.
- Canonical TEST Victory Matrix SHA khớp aggregate release.
- Full rules arrays và q99 verified.
- Hybrid variant.
- ONNX parity `<=1e-5`.
- Exact bundle allowlist/checksums.

Fixed-runner benchmark:

```powershell
$env:AI_BENCHMARK_BUNDLE_PATH = "<absolute-verified-bundle-path>"
.\.venv\Scripts\python.exe -m pytest `
  tests\benchmark\test_serving_performance.py -q
```

Hai fixed-runner skips phải chuyển thành pass trước deployment.

Sau campaign mới cập nhật tracked docs:

- [walkthrough.md](E:/UIT/cv/backend/walkthrough.md):
  - actual run IDs, metrics, selected seed;
  - aggregate artifact hashes;
  - bundle ID;
  - ONNX/latency results;
  - chỉ ghi Hybrid victory nếu toàn bộ gates pass.
- [detail-plan.md](E:/UIT/cv/backend/master/detail-plan.md):
  - mark completed phases;
  - ghi failure path nếu campaign dừng;
  - giữ “Hybrid victory not established” nếu thiếu bất kỳ acceptance gate nào.

## Assumptions khóa

- Không đổi scoring, objective, schema v5, thresholds hoặc v3/v4 hyperparameters.
- Typed `ArtifactLineage` và tách toàn bộ `execute_command()` tiếp tục hoãn sau campaign.
- Provenance module nhỏ được thực hiện ngay vì trực tiếp đóng resume/source-freeze blocker.
- Không chạy production jobs song song trên GPU 6 GB.
- Không xóa, overwrite hoặc reuse failed production artifacts.
- Không sửa source/config/docs giữa các production runs.
- `Trainer.fit()` tiếp tục là external training seam duy nhất.
