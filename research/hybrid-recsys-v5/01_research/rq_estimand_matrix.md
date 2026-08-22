# Stage 1A — RQ–Estimand–Artifact Traceability Matrix

> Material Passport: `stage1a_v1` · trạng thái `UNVERIFIED`  
> Mọi ô kết quả đều là planned artifact. Không có số liệu observed/accepted ở Stage 1A.

## 1. Traceability matrix

| RQ | Experiment | Dataset/protocol | Eligible unit | Comparator | Estimand/outcome | Inference/gate | Planned result artifact |
|---|---|---|---|---|---|---|---|
| **RQ1 Ranking** | `EXP-V5-HARMONIZED` | Immutable v5; temporal split; full 5,200-item catalog; seen mask; deterministic ties | TEST user có ≥1 novel organic purchase × seed | Strongest faithful baseline khóa riêng theo metric bằng validation | Mean paired `Hybrid − baseline`; primary `NDCG@10`, supporting `HR@10`, macro per-user `GAUC` | Hierarchical paired bootstrap, 2,000; H1 pass khi cả 3 CI lower `>0` | `T2_v5_primary_ranking` + per-user arrays + bootstrap receipt |
| **RQ2 Cold item** | `EXP-V5-HARMONIZED` | Cùng v5 protocol; cold items vẫn nằm trong full catalog | User có ≥1 cold-item novel truth × seed | Independent Deep (primary); strongest collaborative-only (secondary) | Cold-item NDCG@10 paired delta; thêm HR@10 và denominator | Primary lower CI `>=0`; semantic traps `10/10` | `T3_v5_cold_item` + cold cohort manifest |
| **RQ3 Mechanism** | `EXP-V5-HARMONIZED` | Rule-aligned cohort tạo từ train-only Apriori rules | Rule-aligned eligible user × seed | No-Wide ablation; thêm Wide-only/Deep-only diagnostic rows | NDCG@10 paired delta full Hybrid − no-Wide | CI lower `>0`; thresholds/cohort hash khóa trước run | `T4_v5_mechanism_ablation` + rule/cohort receipt |
| **RQ4 External validity** | `EXP-EXTERNAL-VALIDITY` | Một public dataset giữ essential full Hybrid contract; mỗi dataset có official và harmonized protocol riêng | Dataset-native eligible user × seed | Locked compatible baseline subset trong chính dataset | Dataset-specific paired NDCG@10 delta; HR/GAUC chỉ khi semantics tương thích | Confirmatory lower CI `>0`; không pool/cross-compare raw metric | `T5_external_official_reproduction` và `T6_external_harmonized` |
| **RQ5 Efficiency** | `EXP-V5-HARMONIZED` | Verified bundle; fixed runner/workload sau accuracy pass | Request batch/repetition theo runtime protocol | Frozen numerical gates; optional Deep/baseline profile chỉ để contextualize | p50/p95 latency, throughput, peak RAM/VRAM, bundle size | Pass/fail từng preregistered gate | `T7_fixed_runner_efficiency` + hardware/runtime receipt |

## 2. Method-integrity artifact không trực tiếp trả lời RQ

| Artifact | Experiment | Mục đích | Không được dùng để làm gì |
|---|---|---|---|
| `T1_official_reference_reproduction` | `EXP-REF-REPRO` | Chứng minh environment/adapter tái hiện được source protocol trong tolerance đã khóa | Không kết luận Hybrid tốt hơn; không đặt raw official metric cạnh v5 để suy luận hơn/kém. |

## 3. Planned table contracts

### T1 — Official reference reproduction

`adapter_id`, source paper/repository, immutable revision, license, official dataset/version, official split/metric, reported center, reproduction seeds/aggregation, observed reproduction statistic, preregistered tolerance, pass/fail, failure reason, environment hash.

### T2 — v5 primary ranking

Rows là toàn bộ promoted models và Hybrid; columns gồm validation mean, locked status, TEST mean/95% CI cho `NDCG@10`, `HR@10`, `GAUC`, absolute paired delta đối với metric-specific locked comparator, seed stability và artifact hash. Không nhập row nếu thiếu per-user evidence.

### T3 — v5 cold-item

Rows gồm collaborative-only, content/transfer, independent Deep, Hybrid; columns gồm cohort definition/hash, eligible users, cold truth count, cold-item `NDCG@10`, `HR@10`, paired delta/CI và semantic-trap status.

### T4 — mechanism/ablation

Rows tối thiểu: full Hybrid, no-Wide, Deep-only, Wide-only; columns gồm rule thresholds, rule registry hash, rule-aligned cohort size, coverage, `NDCG@10`, `HR@10`, paired delta/CI và H3 verdict.

### T5 — external official reproduction

Một block riêng cho từng dataset/model adapter: official split/metric và official comparator only. Không trộn với harmonized result.

### T6 — external harmonized comparison

Một block riêng cho từng dataset: task mapping, preserved/dropped signals, model label (`full Hybrid` hoặc `reduced-method ablation`), compatible baseline subset, shared metrics và paired intervals. Không average giữa dataset.

### T7 — fixed-runner efficiency

Hardware/OS/driver/runtime, bundle SHA, batch/candidate size, warm-up, repetitions, concurrency, p50/p95 latency, throughput, peak RAM/VRAM, bundle size, numerical gate và verdict.

## 4. Pre-result locks còn phải hoàn tất ở Stage 1E

- Exact finalist set dùng trong hierarchical bootstrap và eligible-user intersection.
- Tuning trial/wall-time budget theo model tier; early-stopping metric/patience.
- H3 Apriori support/confidence thresholds và immutable rule/cohort construction.
- External dataset revision, license, split, task mapping và essential-signal compatibility.
- Runtime runner, workload và numerical thresholds cho RQ5.
- Per-adapter official reproduction statistic, aggregation và tolerance.

Các mục này là **blocking cho experiment execution**, nhưng không chặn Stage 1B literature review.

