# Detail plan còn lại: R3 contract closure, R4 diagnostics và production handoff

## Trạng thái kiểm chứng hiện tại

```text
SOURCE_IMPLEMENTATION_IN_PROGRESS
R3_CONTRACT_REPAIR_IN_PROGRESS
R4_DIAGNOSTIC_BLOCKED
PRODUCTION_TRAINING_BLOCKED
Hybrid victory not established
```

Các thay đổi source đã triển khai trong working tree nhưng chưa được source-freeze:

- `training/preflight.py` cung cấp `PreparedTrainingInputs` và
  `run_r3_preflight()`; audit/probe/readiness fail trước run creation.
- `DataProbeReport` là typed report có cờ `passed`; probe output không còn là
  quyết định ngầm từ dictionary.
- `semantic_cohort.py` chỉ đọc cohort thuộc snapshot và kiểm tra đủ 10 trap.
- R3 selection có thể nhận chính xác một `report.json`, khóa selected run và
  diagnostic commit; candidate `FAILED` được ghi ineligible thay vì làm abort
  candidate hợp lệ.
- `R4PromotionReport`, CLI `promote-r4` và `verify_training_run.py` đã có seam
  ban đầu cho handoff diagnostic -> production.
- Run lifecycle atomic publication re-raises mọi lỗi trước rename; v5 run state
  active yêu cầu six-field lineage.

Không được chạy R3/R4 GPU hoặc production seed khi các exit gate dưới đây chưa
pass. Snapshot local hiện tại vẫn phải được kiểm tra lại vì schema/cohort cũ bị
loader reject đúng contract.

## R3-C2 — việc còn phải đóng ở source

### C2.1 Preflight và training seam

Files: `ai-service/src/ai_service/training/preflight.py`,
`training/pipeline.py`, `evaluation/probes.py`, `data/sources.py`.

1. `prepare_training_inputs()` phải là nguồn duy nhất của snapshot, embedding,
   rules, purchase index, sampler và loader cho `train` schema `3.0.0`.
2. `run_r3_preflight()` phải gọi `check_production_connections()` khi
   `AI_ENV=production`, rồi audit snapshot, probes và strict target readiness.
3. Mọi failure phải xảy ra trước `RunLifecycle.create()` và không tạo thư mục
   run. Probe chỉ coi metrics finite/range-valid, permutation sanity và shape
   hợp lệ là pass; Persona/ItemCF/SBERT vẫn là reference, không biến thành
   absolute gate.
4. `execute_command(train)` phải truyền cùng `PreparedTrainingInputs` vào
   `_train()`; không được load/build lại sampler hoặc iterator.

Validate:

```powershell
python -m pytest tests/unit/test_pipeline_preflight_contracts.py tests/unit/test_r3_c2_contract.py -q
python -m ruff check src tests
python -m mypy src
```

### C2.2 Six-field lineage

Files: `contracts.py`, `lineage.py`, `data/snapshot.py`,
`training/run.py`, `training/checkpoint.py`, `evaluation/report.py`,
`evaluation/ablation.py`, `evaluation/release.py`, `export/bundle.py`.

1. Active v5 boundaries chỉ nhận `ArtifactLineageV5` với exact keys:
   `snapshot`, `embedding`, `rules`, `benchmark_spec`, `semantic_cohort`,
   `order_metadata`.
2. Snapshot loader phải verify `benchmark-spec.json`,
   `semantic-cohort.json` và canonical order-metadata receipt; mutation hoặc
   thiếu file phải raise `ArtifactIntegrityError`.
3. Run manifest, pipeline state, checkpoint payload/manifest, evaluation,
   ablation, release và bundle phải serialize cùng sáu SHA; không dựng mapping
   ba trường trong active path.
4. TEST aggregate phải nhận expected lineage từ VAL aggregate và reject mismatch
   trước publication.

Validate bằng corruption tests của checkpoint/report/release/ONNX và kiểm tra:

```powershell
rg -n 'set\(.*snapshot.*embedding.*rules|require_v5=' src/ai_service
```

Chỉ compatibility path synthetic/schema 2 được phép tồn tại trong test seam;
không được dùng trong R3/R4 hoặc production.

### C2.3 Exact selection artifact và promotion

Files: `evaluation/ablation.py`, `training/pipeline.py`,
`evaluation/promotion.py`, `cli.py`.

1. Diagnostic Hybrid bắt buộc `--r3-selection-report` trỏ tới đúng
   `report.json`; pipeline không được scan toàn bộ `diagnostics/r3`.
2. Report phải chọn đúng Deep run, flags, comparison signature, six-field
   lineage và `diagnostic_git_commit` bằng source revision hiện tại.
3. Candidate `FAILED` có summary hợp lệ được ghi `eligible=false`; candidate
   `INTERRUPTED`, corrupt checkpoint, corrupt lineage hoặc non-finite evidence
   abort comparison. Nếu vẫn có candidate eligible thì không đặt
   `diagnostic_pause=true` chỉ vì một candidate thất bại.
4. `promote-r4` publish immutable `R4PromotionReport`; receipt bind selected
   Deep/H3b checkpoints, VAL matrix, config hashes, diagnostic commit và
   production commit. Production train chỉ nhận receipt đã verified và commit
   hiện tại.

### C2.4 Sampling và semantic gate

Files: `data/dataset.py`, `data/sampling.py`, `training/objectives.py`,
`training/trainer.py`, `data/semantic_cohort.py`,
`evaluation/semantic_traps.py`, `evaluation/full_catalog.py`.

1. `RulePairIndex` chỉ lấy organic order baskets; view/click timestamp không
   tạo positive edge.
2. `MixedNegativeBatch` phải giữ `source_tags`/`rule_hard_mask`. Rule-hard quota
   đúng `4/16`, warm/unseen/unique, loại organic positive và protected trap
   edges; thiếu quota phải fail, không fallback.
3. Rule auxiliary loss chỉ có gradient vào Wide; Deep-only Wide parameters và
   gradients giữ nguyên.
4. Semantic gate chỉ đọc snapshot cohort, không fallback fixture/arbitrary user
   cho Postgres. Mỗi trap phải có đủ target cases: mọi case rank <=10, không xấu
   hơn Deep, có ít nhất một strict improvement/trap.

Validate targeted tests:

```powershell
python -m pytest tests/unit/test_purchase_objective_contract.py tests/unit/test_semantic_trap_contract.py tests/unit/test_full_catalog_contract.py -q
```

## R3-C3 — source exit gate và tài liệu

Chạy toàn bộ:

```powershell
npm.cmd run test:seed-product
python -m ruff format --check src tests scripts
python -m ruff check src tests scripts
python -m mypy src scripts
python -m pytest --cov=ai_service --cov-branch --cov-fail-under=85 -q
python scripts/check_critical_coverage.py <coverage.json>
git diff --check
```

Acceptance: tests pass, đúng 2 fixed-runner skips, global branch >=85%,
Trainer/Pipeline >=85%, Checkpoint/Report/Release/Bundle >=90%, không threshold
reduction hoặc coverage exclusion.

Trước freeze:

- `README.md` chỉ dùng config `configs/diagnostics/r3-v5` và yêu cầu
  `--benchmark-spec`.
- `configs/ablations/README.md` không còn executable v3/v4 production path.
- `walkthrough.md` ghi `R3_SOURCE_READY / R4_LINEAGE_REBUILD_PENDING /
  PRODUCTION_TRAINING_BLOCKED`, test receipt mới và `Hybrid victory not
  established`.
- Commit/push, sau đó require `git status --porcelain` rỗng,
  `HEAD == origin/main`, ahead/behind `0/0`.

## R4.0 — rebuild immutable Python lineage

Không reset database nếu receipt v5 vẫn đúng; chỉ purge local
`ai-service/artifacts` bằng `purge_benchmark_outputs.py`. Sau source freeze:

1. Load ba database URL từ allowlist trong `backend/.env`, inject qua shell
   không log secrets; CA phải là absolute file.
2. Chạy production settings và read-only `SELECT 1` receipt cho chatbot,
   catalog, order; database identities phải distinct.
3. Purge dry-run rồi execute; không xóa source, `.env` hoặc database.
4. Tạo snapshot mới với explicit `benchmark-spec-v5.json`, real SBERT feature
   artifact và full-stat rule artifact v3. Không reuse snapshot schema cũ.
5. Chạy audit, probes, `inspect-ml-storage`, rule capability và preflight.

Expected receipt: 823371 events, 5000 users, 5200 items, 15000 orders,
TRAIN/VAL strict target rate >=.40, >=5000 non-trap directed rules, >=3000
organic rule items, all ten semantic target cases and six-field lineage.

## R4.1 — Deep ablation seed 42

Run tuần tự, không song song GPU:

```text
diag-v5-deep-control-s42
diag-v5-deep-no-price-s42
diag-v5-deep-no-user-id-s42
diag-v5-deep-both-s42
```

File thật là `deep-no-user-id.toml`; không dùng `deep-no-user.toml`.
Sau mỗi run dùng `scripts/verify_training_run.py`. Control phải hoàn tất;
candidate `FAILED` có summary hợp lệ được ghi ineligible; interrupted/corrupt
hoặc lineage mismatch dừng toàn bộ R4.

`compare-deep-ablations` phải publish một verified report chứa per-user
GAUC/HR/NDCG, exact run IDs/checkpoint SHAs, six-field lineage, configured
guardrails và selected run. Không có selected eligible run hoặc
`diagnostic_pause=true` thì dừng.

## R4.2 — Hybrid H0–H3b falsification ladder

Năm config phải có `r3_feature_selection_mode="selection_artifact"` và nhận
đúng `--r3-selection-report`:

```text
H0 rule weight 0.00, rule-hard 0, view 0.10
H1 rule weight 0.10, rule-hard 0, view 0.10
H2 rule weight 0.10, rule-hard 4, view 0.10
H3a rule weight 0.10, rule-hard 4, view 0.00
H3b rule weight 0.10, rule-hard 4, view 0.10
```

Evaluate each against selected independent Deep on VAL. Integrity failure,
target readiness failure, non-finite/GAUC<.50, epoch-one Wide/cache failure,
semantic corruption, staged diagnostic stop or no eligible checkpoint stops the
ladder. H0–H3a may fail Victory Matrix as diagnostic evidence; H3b must pass
GAUC >=.75, HR@10 >=.15, NDCG@10 >=.08, strongest-baseline paired CI for all
three metrics, all ten serving-equivalent traps, cold parity, strict readiness
and Wide readiness.

H3b failure means no production config, no seeds 2027/31415, no seal/export,
and status remains `PRODUCTION_TRAINING_BLOCKED`.

## R4.3 — promotion and conditional production campaign

Only after H3b pass:

1. Materialize fixed `configs/production/deep.toml` and `hybrid.toml` with
   selected feature flags, H3b objective settings, selection SHA and six-field
   lineage.
2. Publish and verify `R4PromotionReport`; commit only the two production
   config files, push and source-freeze again.
3. Re-run full quality/corruption/CUDA smoke and confirm six production IDs are
   absent.
4. Train `deep-42-v5 -> hybrid-42-v5 -> VAL`; stop if any train or VAL gate
   fails. Then repeat seeds 2027 and 31415 sequentially.
5. Aggregate VAL 3+3, evaluate TEST for all three pairs, aggregate TEST, seal
   only selected Hybrid, export/verify bundle, run ONNX parity and fixed-runner
   benchmark.

Do not update tracked documentation between production runs. Declare Hybrid
victory only when every acceptance gate and runtime benchmark passes.
