# Detail plan cấp codebase — R3-R4 v5 diagnostic campaign

Trạng thái hiện tại: `R0_R2_CONTRACT_COMPLETE / R3_SOURCE_PENDING / PRODUCTION_TRAINING_BLOCKED`.
Source/data gates đã xanh trên lineage v5; không chạy GPU R3 cho tới khi
change set được commit/push và frozen source revision được xác nhận.

## Current state override (2026-08-12)

`R0_R2_CONTRACT_COMPLETE / R3_SOURCE_PENDING / PRODUCTION_TRAINING_BLOCKED`.
Source quality, reset/purge/reseed, snapshot, embedding, rules, audit, probes
and inspect are complete. R3 GPU diagnostics remain blocked until this change
set is committed/pushed and the frozen source revision is verified.

## R3 source closure

1. `ai_service/contracts.py`: giữ schema `5.2.0`, dùng
   `ArtifactLineage` với snapshot/embedding/rules và ba hash benchmark metadata;
   `R3DiagnosticReport` phải bind checkpoint pair, spec/cohort và NPZ SHA.
2. `data/sources.py`: load order metadata
   (`benchmark_kind`, `benchmark_template_id`, `benchmark_trap_id`) và giữ
   `BenchmarkRunMetadata` trong `RawDataset`; reject malformed benchmark rows.
3. `data/snapshot.py`: ghi canonical `semantic-cohort.json`, hash order metadata
   và verify mọi hash khi load snapshot.
4. `data/dataset.py`: `build_rule_pair_index()` chỉ dùng organic same-basket
   edges, deterministic sorted neighbors; không cho semantic-trap edge vào
   training target index.
5. `data/rule_readiness.py`: report strict target, other-positive, valid
   negative, explicit-negative và negative-only rates; fail nếu strict target
   rate dưới `settings.data.minimum_training_target_rule_rate`.
6. `data/sampling.py`: khi `rule_hard_negative_count=4`, mỗi row có đúng 4/16
   rule-hard candidates, warm/unseen/unique và không fallback; expose
   `sample_with_sources()` để test source tags.
7. `training/objectives.py`: `rule_pairwise_wide_loss()` chỉ nhận Wide logits;
   `Trainer` truyền rule masks/weight và ghi `rule_loss`.
8. `training/trainer.py`: giữ catastrophic NaN/Inf/GAUC<.50; sau warmup publish
   `training/diagnostic-stop.json` nếu maxima không đạt diagnostic floors;
   ineligible checkpoint không được save best.
9. `training/stopping.py`: patience chỉ reset khi checkpoint eligible; tie-break
   vẫn GAUC → NDCG → HR; không có eligible best thì fail closed.
10. `evaluation/full_catalog.py` và `evaluation/semantic_traps.py`: dùng cùng
    profile/catalog/masking/stable-rank seam. Trap request phải có anchor trong
    history và novel target trong VAL cohort.
11. `evaluation/gates.py`: thêm hard gates GAUC `.75`, HR `.15`, NDCG `.08`;
    giữ random/strongest-baseline paired CI, semantic `10/10`, cold parity.
12. `evaluation/r3_diagnostics.py`: NPZ exact keys gồm `user_ids`, `aligned_mask`,
    sáu vector per-user và ba ma trận alpha `[7,U]`; publish/load atomic, hash
    report/NPZ/cohort.
13. `evaluation/ablation.py`: selection artifact phải verified, candidate không
    được chọn chỉ vì GAUC nếu HR/NDCG non-inferior không đạt; diagnostic pause
    là immutable stop.
14. `training/pipeline.py`: `--r3-selection-report` verified-load report,
    materialize selected feature flags trước signatures; không mở production
    nếu selection pause.

### R3 validation

```powershell
npm.cmd run test:seed-product
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
.\.venv\Scripts\python.exe -m pytest --cov=ai_service --cov-branch --cov-fail-under=85 -q
```

Static checks must find no `Softplus`, `_wide_logit_scale`, `scores_by_user`,
Pareto/release-candidate path, signature fallback or unverified NPZ loader.

## R4 execution order

1. `reset-benchmark-v5.js --preflight`, then exact confirmation execute;
   `purge_benchmark_outputs.py --dry-run` then exact confirmation execute.
2. Seed canonical v5, inspect readiness and publish one immutable snapshot,
   real embedding and full-stat rules. Require events `823371`, users `5000`,
   items `5200`, orders `15000`, strict TRAIN/VAL target rates `>=.40`, all trap
   directions and non-trap rule thresholds.
3. Run Deep control/no-price/no-user/both with seed 42, one at a time. Each run
   must be same commit/lineage, have finite history, cache updates and eligible
   `best.pt`. Run `compare-deep-ablations`; pause if no candidate is eligible.
4. Run Hybrid H0 → H1 → H2 → H3a → H3b, each against the selected independent
   Deep checkpoint and verified selection report. Integrity/staged-stop failure
   halts immediately; metric-gate failure records evidence but may continue the
   falsification ladder.
5. Promote only H3b when all absolute, paired, semantic, cold and strict-rule
   gates pass. Materialize fixed production configs, run the full quality gate,
   commit/push, and freeze source before seed 42 production training.

## Acceptance

No production seed, release, seal or export is permitted if any R3/R4 gate is
red. If H3b is red, retain only the immutable diagnostic-stop/report evidence,
keep `Hybrid victory not established`, and do not weaken thresholds.

## Current execution receipt (2026-08-12)

- R0-R2 source/data closure is complete. Reset/purge/reseed v5 finished after
  source quality gates; no GPU R3 or production training has started.
- Ready database run: `benchmark-v5-s42-7f40639b0d-1ace202aaa`.
- Snapshot: `8966df159883fc95940bb1c226544f194eafa8e45988e945d3ef54e73a0264a4`;
  spec `1ace202aaa8f54204ead66ceabe809b3c51795e097dd71c505f07b8367c80bd2`.
- Embedding: `f0453078fd588403186f80321b9ad0500d7c5ce73266f8d50de8fc3a6b09de61`.
- Rules: `benchmark-v5-s42-7f40639b0d-1ace202aaa-rules-v3-554b1decf887`;
  content `79b4b2beed757767261b8531f98a96c618b902c057ab6372451623bea74cf19d`.
- Readiness receipt: TRAIN rule-target `0.4365897744`, VAL rule-target
  `0.4021464646`, VAL context coverage `0.9383417508`, all trap directions,
  audit and probes pass.
- Source gate receipt: Python `399 passed, 2 skipped`, branch coverage
  `85.02%`, critical checker/Ruff/mypy pass, seed-product `15/15`.
- Next authorized phase is the sequential R3 seed-42 Deep ablation ladder;
  production IDs, release, seal, export and Hybrid victory remain blocked.
