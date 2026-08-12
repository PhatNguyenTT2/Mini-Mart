# Detail plan còn lại: R4 diagnostic và production handoff

## 1. Readiness receipt hiện tại

Source R3-C0/C1 đã hoàn tất trong working tree:

- Python: `436 passed, 2 skipped`.
- Branch coverage: `85.02%`.
- Critical coverage: pipeline `85.33%`, trainer `86.16%`, checkpoint `96.03%`, report `90.73%`, release `90.37%`, bundle `94.70%`.
- Ruff format/lint, mypy, `git diff --check`: pass.
- Node seed-product: `15 passed`.
- Six-field lineage, selection-artifact mode, immutable diagnostic stop, rule-hard exclusion và read-only `preflight-r3` seam đã được kiểm thử.

Readiness vẫn khóa:

```text
R3_SOURCE_READY
R4_LINEAGE_REBUILD_PENDING
PRODUCTION_TRAINING_BLOCKED
Hybrid victory not established
```

Blocker vận hành duy nhất trước R4 là snapshot local hiện tại không có `benchmark-spec.json` và semantic cohort đang dùng shape cũ; `load_snapshot()` reject đúng contract. Không chạy GPU, không tạo R4 run và không purge database cho tới khi Phase R4.0 hoàn tất.

Frozen database receipt cần giữ nguyên:

```text
benchmark_run_id = benchmark-v5-s42-7f40639b0d-1ace202aaa
spec_sha256      = 1ace202aaa8f54204ead66ceabe809b3c51795e097dd71c505f07b8367c80bd2
cohort_sha256    = da59e744fdb4e572be52a5fd1f76daae62fb61685fcc39fa53e0015c60ca30f7
events           = 823371
orders           = 15000 (14250 organic, 750 semantic_trap)
train_alignment  = 0.43658977441932684
val_alignment    = 0.40214646464646464
non_trap_rules   = 14086
organic_items    = 4143
```

Không thay đổi source/config sau source freeze; mọi failed run/artifact dùng ID mới, không overwrite.

## 2. Phase R4.0 — Rebuild immutable Python lineage

### Task R4.0.1 — Production shell preflight

Files/seams:

- `ai-service/src/ai_service/config.py::Settings.validate_production()` — chỉ đọc biến môi trường, không ghi secret.
- `ai-service/src/ai_service/data/sources.py` — dùng đúng TLS helper cho ba database.
- `ai-service/src/ai_service/training/provenance.py` — require clean worktree và `HEAD == @{u}` trước snapshot publication.

Trong shell mới tại `E:\UIT\cv\backend\ai-service`, cấu hình `AI_ENV=production`, absolute `AI_ARTIFACT_ROOT`, `AI_STORE_ID=1`, ba database URL và `SUPABASE_DB_CA_PATH`. Chỉ in tên database và `PASS`; không in URL.

Validate:

```powershell
git status --porcelain
git rev-parse HEAD
git rev-parse '@{u}'
git rev-list --left-right --count HEAD...@{u}
.\.venv\Scripts\python.exe -c "from ai_service.config import get_settings; s=get_settings(); s.validate_production(); assert s.data.database_ssl_root_cert and s.data.database_ssl_root_cert.is_file(); print('production_settings=PASS')"
```

Reject nếu worktree dirty, upstream thiếu/mismatch, CA không tồn tại hoặc bất kỳ DB `SELECT 1` nào fail.

### Task R4.0.2 — Purge local Python outputs only

File: `ai-service/scripts/purge_benchmark_outputs.py`.

1. Chạy `--dry-run`, kiểm tra allowlist exact (`_archive`, `snapshots`, `features`, `rules`, `runs`, `diagnostics`, `releases`, `bundles`).
2. Xác nhận không có production/R4 run cần giữ.
3. Chạy với confirmation token đã định nghĩa trong script.
4. Kiểm tra root vẫn tồn tại và không còn snapshot/rule/diagnostic v4 hoặc schema cũ.

Không chạy reset database; database receipt đã pass và không cần audit archive.

### Task R4.0.3 — Snapshot publication

Files:

- `ai-service/src/ai_service/data/snapshot.py::SnapshotBuilder.build/load_snapshot` — publish và verify `benchmark-spec.json`, `semantic-cohort.json`, order metadata receipt; hash canonical JSON.
- `ai-service/src/ai_service/cli.py` — snapshot command phải nhận `--benchmark-spec` explicit.
- `ai-service/src/ai_service/training/pipeline.py::_configure` — resolve path và reject file không tồn tại.

Tạo snapshot ID mới, không reuse local ID cũ:

```text
benchmark-v5-r3-s42-<spec-sha-prefix>-<frozen-commit-prefix>
```

Publish bằng Postgres source và canonical spec `backend/docs/chatbot/seed-product/benchmark-spec-v5.json`. Sau đó load lại snapshot bằng `load_snapshot()`; mutation hoặc thiếu bất kỳ file lineage nào phải fail.

### Task R4.0.4 — Features và rules

Files:

- `ai-service/src/ai_service/data/features.py::SBERTArtifactBuilder` — build real pinned SBERT artifact từ snapshot mới.
- `ai-service/src/ai_service/data/rules.py::AprioriRuleMiner/load_rule_artifact` — mine full-stat v3 rules, bind snapshot SHA/spec/cohort/order metadata và reject legacy.
- `ai-service/src/ai_service/lineage.py::resolve_artifact_lineage` — verify sáu SHA bằng manifest thực tế.

Require:

```text
events=823371, users=5000, items=5200, orders=15000
strict TRAIN target rate >= .40
strict VAL target rate >= .40
non-trap directed rules >= 5000
distinct organic rule items >= 3000
all semantic target directions present
```

## 3. Phase R4.1 — Read-only preflight và source exit gate

### Files

- `ai-service/src/ai_service/training/pipeline.py::_preflight_r3` — dùng cùng snapshot/features/rules/sampler với training; không tạo run directory.
- `ai-service/src/ai_service/data/rule_readiness.py` — strict target-rule rate, negative-only rows và denominator phải finite.
- `ai-service/src/ai_service/evaluation/probes.py` — streaming probe parity với reference.

Chạy:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli preflight-r3 `
  --config configs\diagnostics\r3-v5\deep-control.toml `
  --snapshot-id <new-snapshot-id> --device cpu
```

Validate response có snapshot/embedding/rules/spec/cohort/order SHA, audit pass, strict readiness pass và probe parity `<=1e-6`. Nếu fail, dừng trước GPU.

Chạy lại quality gate sau khi snapshot lineage mới được publish:

```powershell
npm.cmd run test:seed-product
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
.\.venv\Scripts\python.exe -m pytest --cov=ai_service --cov-branch --cov-fail-under=85 -q
.\.venv\Scripts\python.exe scripts\check_critical_coverage.py <coverage.json>
```

Require exactly two fixed-runner skips, critical thresholds như receipt trên, clean worktree và `HEAD == origin/main`.

## 4. Phase R4.2 — Deep ablation seed 42

### Config/source files

- `ai-service/configs/diagnostics/r3-v5/deep-control.toml`
- `ai-service/configs/diagnostics/r3-v5/deep-no-price.toml`
- `ai-service/configs/diagnostics/r3-v5/deep-no-user.toml`
- `ai-service/configs/diagnostics/r3-v5/deep-no-price-no-user-id.toml`
- `ai-service/src/ai_service/training/pipeline.py::_train` — verify six-field lineage and diagnostic stage before `RunLifecycle.create`.
- `ai-service/src/ai_service/training/trainer.py` — enforce post-warmup eligible checkpoint, finite metrics, cache update, Deep/Wide invariant.

Chạy tuần tự, một GPU job mỗi lần:

```text
diag-v5-deep-control-s42
diag-v5-deep-no-price-s42
diag-v5-deep-no-user-s42
diag-v5-deep-both-s42
```

Sau mỗi run kiểm tra `run-manifest.json`, `resolved-config.json`, `training/history.jsonl`, `training/summary.json`, `checkpoints/best.pt`, `checkpoints/last.pt` và pipeline state. Epoch trước warmup không được tạo `best.pt`; không eligible checkpoint hoặc non-finite/GAUC `<.50` là diagnostic stop và dừng ladder.

So sánh:

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli compare-deep-ablations `
  --control-run-id diag-v5-deep-control-s42 `
  --candidate-run-ids diag-v5-deep-no-price-s42 diag-v5-deep-no-user-s42 diag-v5-deep-both-s42 `
  --device cuda
```

Selection artifact phải có exact per-user HR/NDCG/GAUC, six-field lineage, source commit và một candidate eligible theo GAUC/HR/NDCG floors + paired CI. Không có candidate eligible: publish diagnostic pause, không chạy Hybrid.

## 5. Phase R4.3 — Hybrid falsification ladder

### Config files

- `ai-service/configs/diagnostics/r3-v5/hybrid-h0-main.toml`
- `hybrid-h1-rule-aux.toml`
- `hybrid-h2-rule-hard.toml`
- `hybrid-h3a-view-zero.toml`
- `hybrid-h3b-view-point-one.toml`

Mỗi file phải giữ `r3_feature_selection_mode="selection_artifact"`; không khai báo feature flags trái selection receipt.

### Execution

Với selection report đã verified, chạy H0 → H1 → H2 → H3a → H3b, truyền:

```text
--r3-selection-report <verified-selection-report>/report.json
```

Mỗi Hybrid pair với đúng selected Deep run, cùng seed/source/six-field lineage/comparison signature. Sau mỗi run chạy `evaluate --split val` với independent Deep.

Dừng ngay khi selection/lineage mismatch, target readiness fail, cohort corruption, non-finite, GAUC `<.50`, epoch-1 Wide/cache fail, staged diagnostic stop hoặc không có eligible checkpoint. H0–H3a có thể fail Victory Matrix nhưng phải giữ immutable evidence trước candidate kế tiếp.

H3b chỉ pass khi tất cả đồng thời:

```text
GAUC >= .75
HR@10 >= .15
NDCG@10 >= .08
paired CI lower > 0 vs strongest baseline cho cả ba metrics
semantic cohort đủ 10/10 target cases
cold parity PASS
strict target readiness PASS
Wide readiness PASS
```

Nếu H3b fail: publish diagnostic-stop/R3 report, không train seed 2027/31415, không tạo production config, seal hoặc bundle.

## 6. Phase R4.4 — Promotion gate

Chỉ sau H3b pass:

1. Tạo `ai-service/configs/production/deep.toml` và `hybrid.toml` với feature flags cố định.
2. Ghi selection report SHA và six-field lineage receipt vào resolved config.
3. Chạy full quality/corruption/CUDA smoke trong artifact root tạm.
4. Commit/push và freeze source; không sửa tracked files trong production campaign.
5. Verify production env/TLS, snapshot/rules/features và cả sáu production run ID chưa tồn tại.

Readiness chỉ chuyển thành `READY_FOR_DEEP_42_TRAINING` sau các điều kiện trên. Khi chưa đạt, giữ `R4_DIAGNOSTIC_BLOCKED` và `Hybrid victory not established`.

## 7. Source checks added in the current working tree

These checks are now part of the R3 source gate and must be rerun after the
next commit; they do not authorize a GPU campaign while snapshot rebuild is
pending:

- `evaluation/ablation.py` stores the selected comparison-signature SHA in a
  v5 Deep selection report, and `require_selected_r3_pair()` rejects a mismatch
  against Hybrid resolved settings after lineage and feature checks.
- `evaluation/semantic_traps.py` rejects duplicate `(trap_id,user_id,target_id)`
  rows before serving-equivalent scoring.
- Regression coverage is in `test_ablation_contract.py` and
  `test_checkpoint_report_and_trap_contracts.py`.

Current validation receipt:

```text
Python tests       438 passed, 2 fixed-runner skips
Branch coverage   85.00% (cov-branch, fail-under=85)
Critical files    checkpoint 96.03%, report 90.73%, bundle 94.70%,
                  release 90.37%, trainer 86.16%, pipeline 85.33%
Node seed tests   15 passed
Ruff/mypy         PASS
```

The local snapshot `benchmark-v5-s42-7f40639b0d-1ace202aaa` remains rejected
because `benchmark-spec.json` is missing and its cohort uses the old shape.
Next action is R4.0.3 snapshot publication from the verified database receipt,
then `preflight-r3`; do not bypass this failure or start a diagnostic run.

## 8. Production handoff sau R4

Campaign bắt buộc tuần tự:

```text
deep-42-v5 → hybrid-42-v5 → VAL 42
→ deep/hybrid 2027 → VAL 2027
→ deep/hybrid 31415 → VAL 31415
→ aggregate VAL 3+3
→ TEST cả ba pairs
→ aggregate TEST
→ seal selected Hybrid
→ export/verify bundle
→ ONNX parity và fixed-runner benchmark
```

Các file kiểm chứng sau mỗi run:

- `ai-service/src/ai_service/training/run.py` — status/reason/commit.
- `ai-service/src/ai_service/training/checkpoint.py` — best/last hash, stopping state, six-field lineage.
- `ai-service/src/ai_service/evaluation/report.py` — Hybrid-owned evaluation artifact.
- `ai-service/src/ai_service/evaluation/release.py` — exact 3+3 seeds, source commit và selected winner lock.
- `ai-service/src/ai_service/export/bundle.py` — canonical Victory Matrix SHA, allowlist/checksums, ONNX parity.

Không tuyên bố Hybrid victory nếu thiếu một gate trong acceptance matrix; không xóa hoặc reuse run/artifact thất bại.
