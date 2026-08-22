# Stage 1A — Methodology Blueprint

> Material Passport: `stage1a_v1` · trạng thái `UNVERIFIED` · kế thừa Phase 0 input lock  
> Đây là design blueprint, không phải Methods prose và không chứa empirical result.

## 1. Design decision

- **Paradigm:** post-positivist quantitative benchmarking: metrics được định nghĩa khách quan trong protocol, nhưng uncertainty, implementation dependence và external-validity limits phải được công khai.
- **Methodology type:** quantitative.
- **Primary pattern:** ARS Pattern 7 — Benchmarking Study, mở rộng bằng preregistered ablations, adapter reproduction và external validation.
- **Design label:** comparative offline recommender benchmark with method-faithful reproduction and harmonized evaluation.
- **Unit of analysis:** per-user metric vector nested within training seed; runtime analysis dùng repeated request/workload measurements trên fixed runner.
- **Causal boundary:** không ước lượng causal effect lên người dùng hoặc doanh thu; chỉ ước lượng comparative algorithmic performance dưới dataset/protocol đã nêu.

## 2. Why this method answers the RQ

Câu hỏi chính yêu cầu so sánh Hybrid với baseline dưới cùng temporal split, candidate universe, masking, metric và tuning constraints. Vì vậy một benchmark thống nhất, không phải so raw numbers từ literature, là thiết kế trực tiếp nhất. Official-code reproduction được dùng như acceptance test của adapter; v5 harmonized benchmark mới trả lời RQ1–RQ3/RQ5; external harmonized benchmark trả lời RQ4.

```text
Phase 0 input lock
  -> official-protocol adapter reproduction
  -> shared v5 validation/tuning
  -> baseline registry + comparator lock
  -> sealed v5 TEST evaluation
  -> mechanism/cold analyses from the same artifacts
  -> compatible external harmonized evaluation
  -> fixed-runner efficiency after accuracy pass
```

## 3. Data strategy

### 3.1 Internal controlled benchmark v5

- 5,000 users, 5,200 items, 250 cold items và 823,371 interactions là **dataset contract facts pending lineage verification**, không phải model results.
- Behavior là controlled/generated; language/catalog context là Vietnamese retail. Paper phải mô tả cả lợi thế mechanism control và giới hạn natural-behavior validity.
- Immutable temporal boundaries:
  - train: `2026-01-01 00:00:00Z`–`2026-06-19 23:59:59Z`;
  - validation: `2026-06-20 00:00:00Z`–`2026-07-10 23:59:59Z`;
  - test: `2026-07-11 00:00:00Z`–`2026-08-01 23:59:59Z`.
- User `0` bị loại; eligible user phải có ≥1 novel organic purchase trong target split.
- Full-catalog scoring trên 5,200 items; seen item mask `-inf`; tie-break score giảm dần rồi `raw_product_id` tăng dần.

### 3.2 External datasets

- Vietnamese priority candidate và multilingual commerce candidate chỉ được chọn sau audit revision/hash, license, task/labels, official split, history structure, item text và basket/session signal.
- Mỗi dataset có hai tables tách biệt: `OFFICIAL_PROTOCOL_REPRODUCTION` và `HARMONIZED_PROTOCOL_COMPARISON`.
- Dataset làm mất essential input/objective/mechanism phải đổi model label thành `reduced-method ablation`; không dùng để pass H4.
- Không thiết kế pooling raw metrics giữa v5 và external datasets.

### 3.3 Sampling and sample-size strategy

- Không subsample evaluation nếu full-catalog contract còn khả thi; dùng toàn bộ eligible users của frozen split.
- “Sample size” là số eligible users và truth events sau deterministic eligibility, phải được báo theo split và cohort.
- Three final training seeds: `42`, `2027`, `31415`.
- Precision được thể hiện bằng paired hierarchical bootstrap; Stage 1E phải thêm minimum detectable effect/precision analysis sau khi validation-only variance estimates khả dụng, không mở TEST để tính power.

### 3.4 Data quality and missingness

- Verify six-field lineage, schema, duplicate handling, timestamp ordering, item/user coverage, language provenance, PII và license.
- Missing item text, malformed histories và unsupported behavior types phải có deterministic handling trong adapter spec; không silently drop.
- Mọi exclusion phải tạo count/flow receipt theo dataset và split.

## 4. Model/comparator strategy

### 4.1 Mandatory families

- Sanity: Random, MostPop.
- Neighborhood/rule: ItemKNN/ItemCF, Apriori.
- Latent/graph: BPR-MF, LightGCN.
- Sequence/basket: SASRec, BERT4Rec, BTBR/Mask-Swap khi official semantics giữ được.
- Content/transfer: UniSRec, AlphaRec.
- Graph contrastive: SimGCL, XSimGCL, LightGCL.
- Project: independent Deep Two-Tower và proposed Hybrid.

7B LLM methods là optional compute tier. Nếu không thể chạy official recipe, ghi exclusion và thu hẹp claim; không dùng simplified surrogate với nhãn faithful reproduction.

### 4.2 Adapter acceptance

Mỗi adapter phải khóa paper/repository identity, immutable revision, license, dataset mapping, split/candidate/objective, search space/budget, seeds, checkpoint/config hashes và per-user metric artifacts. Text-aware adapter còn phải khóa encoder revision, tokenizer, serialization/prompt và embedding recipe/hash.

Acceptance order:

1. isolated environment/container;
2. toy metric/data parity;
3. official-protocol reproduction trong tolerance khóa trước run;
4. v5 split/mask/candidate parity;
5. per-user evidence emission;
6. status `READY` và registry inclusion.

Failure ở bước nào giữ nguyên failure report; không thay bằng số paper.

### 4.3 Fair tuning and comparator lock

- Validation-only selection; TEST không dùng chọn feature, model family, epoch hay hyperparameter.
- Cùng max trials/wall-time trong comparable compute tier; search spaces vẫn method-faithful.
- Strongest baseline được chọn riêng theo metric bằng validation mean trên registry đã khóa; tie-break theo lexicographic model ID.
- Registry SHA, exact seed/config/checkpoint và comparator ID được truyền vào TEST evaluator.

## 5. Outcome and metric contract

| Outcome | Definition/role |
|---|---|
| `NDCG@10` | Binary relevance, IDCG theo `min(|truth_u|,10)`; mean eligible users; primary inferential outcome. |
| `HR@10` | Per-user hit indicator; mean eligible users; không đồng nhất với Recall. |
| Macro per-user `GAUC` | Exact user AUC giữa novel positives và unseen non-positives; average-rank ties; unweighted mean eligible users. |
| `Recall@10` | Reporting compatibility metric sau khi implementation/schema tests pass; chưa là release gate. |
| Cold-item HR/NDCG | Required cohort outcomes kèm cohort size và denominator. |
| Rule-aligned outcomes | Same shared evaluator restricted by frozen train-defined cohort. |
| Efficiency | p50/p95 latency, throughput, peak RAM/VRAM, bundle size sau accuracy pass. |

Không tính metric bằng notebook riêng. Mọi outcome phải đến từ cùng prepared split, masking và deterministic ranking seam.

## 6. Statistical analysis plan

### 6.1 Primary estimate

`E1-NDCG = mean_{seed,user}[NDCG@10(Hybrid) − NDCG@10(locked baseline)]`.

Supporting estimates có cùng form cho HR@10 và GAUC. Báo mean, absolute delta, 95% CI và seed-specific estimates; relative percent chỉ là bổ sung.

### 6.2 Hierarchical paired bootstrap

- 2,000 replicates; two-sided percentile 95% interval; endpoints `2.5%/97.5%`; interpolation `linear`.
- RNG: NumPy `Generator(PCG64(42))` cho aggregate analysis.
- Mỗi replicate resample ba seed occurrences có hoàn lại; trong từng occurrence resample user IDs độc lập có hoàn lại; cùng user indices cho Hybrid và comparator.
- Point estimate dùng toàn bộ original seed/user cells.
- Không average ba seed trước rồi chỉ bootstrap users.

Single-seed diagnostic gates dùng paired user bootstrap với seed offsets: GAUC `training_seed+11`, HR `+13`, NDCG `+17`.

### 6.3 Multiplicity and selection

- H1 là preregistered conjunction của ba metric-specific contrasts; chỉ pass khi mọi CI lower `>0`.
- Exploratory multi-model p-values báo số comparisons và dùng Holm correction.
- Nếu comparator selection và inference vô tình dùng cùng sample, nominal selected-comparison CI bị cấm; dùng simultaneous/max-statistic interval hoặc rerun đúng pre-TEST lock.

### 6.4 Missing/failed runs

- Không impute failed seeds hoặc thay checkpoint bằng seed khác sau TEST.
- Failed run chỉ reuse khi failure policy đã preregister; hiện tại failed-run reuse là forbidden.
- Thiếu một required seed làm confirmatory aggregate `INCOMPLETE`, không tự động chuyển sang single-seed claim.

## 7. RQ-specific analysis

| RQ | Primary dataset | Primary comparator | Outcome | Decision |
|---|---|---|---|---|
| RQ1 | v5 TEST | Metric-specific strongest locked baseline | NDCG@10; supporting HR/GAUC | H1 conjunction pass/fail. |
| RQ2 | v5 cold cohort | Independent Deep | Cold NDCG@10 | Lower CI `>=0` + semantic traps `10/10`; collaborative comparator secondary. |
| RQ3 | v5 rule cohort | No-Wide ablation | NDCG@10 | Lower CI `>0`; otherwise mechanism claim rejected. |
| RQ4 | Full-contract external dataset | Locked compatible baseline | NDCG@10 | Dataset-specific lower CI `>0`; absent compatible data => `NOT_TESTED`. |
| RQ5 | Fixed runner | Frozen gates | latency/throughput/memory | Chỉ mở sau accuracy pass; all required gates pass. |

Chi tiết artifact/table nằm trong `rq_estimand_matrix.md`.

## 8. Validity and bias controls

### Internal/implementation validity

- Same split, truth, candidate universe, masking, tie-break, metrics và evaluator cho harmonized comparisons.
- Adapter parity tests và official reproduction giảm nguy cơ so implementation lỗi với proposed model.
- Validation-only comparator selection và TEST seal giảm leakage/cherry-picking.
- Config/source/dataset hashes và per-user arrays cho phép audit.

### Construct validity

- `HR`, `Recall`, `NDCG` và `GAUC` được tách semantics rõ ràng.
- Cold-item cohort không đại diện cold-user.
- Apriori mechanism chỉ được đánh giá trên train-defined rule-aligned cohort.
- Offline relevance không đại diện satisfaction, revenue hoặc long-term user impact.

### Statistical conclusion validity

- Paired estimands giữ dependence giữa model trên cùng users.
- Hierarchical resampling giữ seed-level uncertainty.
- Conjunctive H1 và Holm cho exploratory p-values hạn chế multiplicity abuse.
- Ba seeds vẫn là số cluster nhỏ; seed-specific instability phải được báo và diễn giải thận trọng.

### External validity

- Generated v5 behavior có thể encode assumptions thuận lợi cho Apriori/content fusion.
- Chỉ full-contract public dataset mới kiểm tra H4; Vietnamese reduced track chỉ kiểm tra domain sensitivity.
- Không có online/user study nên generalization tới production remains unsupported.

### Researcher degrees of freedom

- Freeze hypothesis, estimand, cohort builder, metric code, tuning budget, comparator selection và runtime gates trước TEST.
- Mọi deviation tạo versioned amendment, timestamp và lý do; analyses sau amendment phải ghi exploratory nếu nhìn thấy outcome liên quan.

## 9. Ethics, privacy, license and IRB

### Current determination

Stage 1A không tuyển, can thiệp hoặc tương tác với human participants. v5 dùng generated behavior; external track dự kiến dùng secondary public/de-identified data. Theo ARS IRB decision tree, dự án **không yêu cầu full/expedited human-subject review theo mô tả hiện tại**, nhưng public/de-identified data có thể cần institutional exempt-status confirmation tùy quy định của cơ sở.

Đây không phải quyết định pháp lý/IRB chính thức. Trước khi dùng external data, nhóm phải xin xác nhận từ đơn vị ethics/IRB của cơ sở nếu policy yêu cầu.

### Mandatory safeguards

- Audit direct/indirect identifiers và re-identification risk trước ingest/release.
- Verify source catalog, generated-data lineage, public-dataset license, redistribution và derivative-model rights.
- Không mô tả generated behavior là observed human behavior.
- Không release row-level histories nếu license/privacy chưa pass; ưu tiên aggregate statistics và controlled access khi cần.
- Re-run ethics determination nếu thêm private logs, identifiable users, surveys, interviews, online A/B test hoặc vulnerable populations.

## 10. Reporting-standard routing

EQUATOR routing không cho một guideline phù hợp trực tiếp:

- Q0: không phải systematic review/clinical guideline;
- Q1: không phải qualitative, quality-improvement, economic, animal hoặc mixed-method study;
- Q2–Q5: không phải case report, clinical prediction, intervention hay diagnostic-accuracy study;
- Q6: không phải epidemiological cohort/case-control/cross-sectional report.

Do đó không ép PRISMA/STROBE/TRIPOD+AI lên recommender benchmark. Primary reporting standard ở giai đoạn này là **target-venue author guidelines + venue artifact/reproducibility checklist**, vẫn `PENDING` vì venue chưa chọn. Internal minimum gồm dataset/model cards, exact split/candidate/metric contract, code/config/environment hashes, per-user evidence, uncertainty, negative results, ethics/license disclosure và artifact availability.

Stage 1B literature search nếu được trình bày như targeted review không tự biến paper thành systematic review; chỉ dùng PRISMA nếu scope được đổi thành systematic review thực sự.

## 11. Preregistration plan

Preregistration được **strongly recommended** vì đây là confirmatory secondary-data benchmark có hypotheses, multiple comparisons và TEST leakage risk.

- Platform đề xuất: OSF Registries.
- Timing: sau Stage 1E-Plan, trước first confirmatory training/Test access.
- Register tối thiểu: RQs/H1–H4, data status, frozen splits/eligibility/candidates, model conditions, sampling/seed/stopping rule, metric code version, primary/secondary outcomes, comparator-selection rule, search spaces/budgets, exclusions, hierarchical bootstrap, multiplicity, external compatibility gate, runtime protocol và deviations policy.
- Nếu TEST hoặc outcome liên quan đã được xem trước registration, disclosure phải ghi đây là prospective analysis plan/amendment chứ không gọi pre-data preregistration.
- Registered Reports không phải requirement mặc định; chỉ xem xét nếu target venue hỗ trợ và schedule cho phép.

## 12. Reproducibility and artifact plan

Mỗi accepted result phải liên kết được:

`paper claim -> result table cell -> aggregate receipt -> per-user arrays -> run/checkpoint/config -> adapter revision -> dataset/split hash`.

Artifacts bắt buộc: environment lock/container, source patch, adapter tests, dataset manifest, baseline registry, resolved configs, checkpoints, per-user metric arrays, bootstrap output, failure log, external mapping receipt và runtime receipt.

## 13. Stage 1A exit criteria

| Criterion | Status |
|---|---|
| Một canonical non-compound RQ và 4 sub-questions | PASS |
| FINER + explicit scope/exclusions | PASS |
| RQ1–RQ5 map tới dataset, comparator, estimand và planned table | PASS |
| Hypotheses có failure condition; null result được giữ | PASS |
| Primary outcome/comparator-selection/statistics định nghĩa | PASS |
| Ethics/IRB/reporting/preregistration route ghi rõ | PASS |
| Devil's Advocate Checkpoint 1 không còn critical issue | PASS |
| Experiment execution readiness | BLOCKED — thuộc Stage 1E-Plan |
| Final Introduction/Related Work writing readiness | BLOCKED — cần Stage 1B source verification |

**Stage 1A decision:** đủ điều kiện chuyển sang Stage 1B sau xác nhận của người dùng; không tự động bắt đầu search.

