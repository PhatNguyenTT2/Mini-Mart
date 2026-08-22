# Experimental Log and Preregistered Evaluation Protocol

## 0. Trạng thái bằng chứng

```text
LOG_SCHEMA_VERSION       = 1.0.0
RESULT_STATUS            = NOT_RUN
ACCEPTED_RESULT_ROWS     = 0
FINAL_SNAPSHOT_ID        = PENDING
REFERENCE_BASELINES      = NOT_REPRODUCED
HYBRID_VICTORY           = NOT_ESTABLISHED
TEST_SET_OPENED          = NO
```

File này cố ý **không chứa kết quả mô hình**. Các bảng số trong phiên bản cũ và
`workspace/final/paper.tex` là số ước chừng/không có immutable artifact nên đã
bị loại bỏ. Chỉ được điền một result row bằng script từ verified JSON/NPZ;
không sửa tay metric trong Markdown.

Các asset `inputs/walkthrough.md`, `inputs/template.tex` và
`inputs/figures/{captions.json,latency_comparison.png,performance_ablation.png}`
vẫn chứa nội dung lịch sử. Chúng bị **quarantine**, không được đưa vào paper mới
hoặc dùng làm result source. Việc xóa/tái tạo chúng nằm ngoài phạm vi ba file
được rewrite trong task này.

## 1. Phân loại mọi con số

Mỗi số trong log phải mang một trong bốn nhãn:

| Nhãn | Ý nghĩa | Có được dùng làm kết quả paper? |
|---|---|---|
| `CONTRACT` | Giá trị khóa trong spec/standard | Không; chỉ mô tả protocol |
| `RECEIPT` | Dataset/system/provenance fact strict-load từ immutable artifact | Chỉ hỗ trợ setup; không hỗ trợ model-effect claim |
| `TARGET` | Threshold preregister | Không được gọi là observed result |
| `RESULT` | Metric từ verified run/evaluation artifact | Chỉ loại này hỗ trợ performance/effect claim |

`ESTIMATE`, `EXPECTED_RESULT` và số lấy từ paper cũ không phải nhãn hợp lệ.

## 2. Dataset normalization sheet

### 2.1 Contract hiện hành

Nguồn: `master/standard.md` và
`backend/docs/chatbot/seed-product/benchmark-spec-v5.json`.

| Field | Value | Label | Runtime receipt |
|---|---:|---|---|
| generator schema/version | `3.0.0 / 5.0.0` | CONTRACT | PENDING |
| users | 5,000 | CONTRACT | PENDING |
| products | 5,200 | CONTRACT | PENDING |
| cold products | 250 | CONTRACT | PENDING |
| events | 823,371 | CONTRACT | PENDING |
| train events | 658,697 | CONTRACT | PENDING |
| validation events | 82,337 | CONTRACT | PENDING |
| test events | 82,337 | CONTRACT | PENDING |
| distinct user–item cells | 356,181 | CONTRACT | PENDING |
| orders | 15,000 | CONTRACT | PENDING |
| organic / semantic orders | 14,250 / 750 | CONTRACT | PENDING |
| generated personas | 8 | CONTRACT | PENDING |
| semantic traps | 10 | CONTRACT | PENDING |

Research inputs dùng dấu phẩy phân tách hàng nghìn và dấu chấm làm thập phân.
Machine-readable artifacts dùng JSON number không có thousands separator.

### 2.2 Hai khái niệm density không được trộn

```text
possible user-item cells = 5,000 * 5,200 = 26,000,000
distinct-cell density    = 356,181 / 26,000,000 = 1.3699%
event-frequency density  = 823,371 / 26,000,000 = 3.1668%
distinct-cell sparsity   = 98.6301%
```

`event-frequency density` có thể lớn hơn distinct-cell density do nhiều event
cho cùng user–item. Paper phải dùng distinct-cell density khi nói về độ thưa của
ma trận implicit feedback. Giá trị 7.2%–10.0%, 3.85% và dataset một triệu events
thuộc tài liệu lịch sử, không hợp lệ cho v5.

### 2.3 Dataset provenance receipt bắt buộc

Điền tự động sau khi snapshot v5 strict-load:

| Receipt | Value |
|---|---|
| snapshot ID | `PENDING` |
| snapshot SHA-256 | `PENDING` |
| embedding SHA-256 | `PENDING` |
| rules SHA-256 | `PENDING` |
| benchmark-spec SHA-256 | `PENDING` |
| semantic-cohort SHA-256 | `PENDING` |
| order-metadata SHA-256 | `PENDING` |
| frozen source commit | `PENDING` |
| product-source/license audit | `PENDING` |
| Vietnamese language audit | `PENDING` |

Nếu thiếu một trong sáu lineage SHA, mọi run dùng snapshot đó là invalid.

### 2.4 Bản chất dữ liệu

- Product metadata có bối cảnh tiếng Việt và phải được audit nguồn/license.
- User/event/order behavior được sinh deterministic từ generator spec.
- Persona là generator label, không phải demographic inference.
- 250 cold products tạo cold-item cohort; chưa có accepted cold-user cohort.
- Kết luận chỉ áp dụng cho controlled benchmark cho tới khi lặp lại trên public
  hoặc observed-behavior dataset.

## 3. Split và eligibility contract

### 3.1 Temporal boundaries

| Split | Inclusive start | Inclusive end | History used for evaluation |
|---|---|---|---|
| Train | 2026-01-01 00:00:00Z | 2026-06-19 23:59:59Z | n/a |
| Validation | 2026-06-20 00:00:00Z | 2026-07-10 23:59:59Z | Train only |
| Test | 2026-07-11 00:00:00Z | 2026-08-01 23:59:59Z | Train + Validation |

Random 80/10/10 split bị cấm. Test không được dùng để chọn feature,
hyperparameter, epoch hoặc model family.

### 3.2 Truth và candidate universe

- Chỉ organic purchase trong target split được dùng làm truth.
- Truth của user là target purchases trừ toàn bộ item đã thấy trong history.
- User 0 bị loại.
- User chỉ eligible khi có ít nhất một novel organic purchase.
- Scoring dùng toàn bộ 5,200-item catalog; seen items được mask `-inf`.
- Tie-break bắt buộc: score giảm dần, sau đó `raw_product_id` tăng dần.
- Cold items không bị loại khỏi full-catalog evaluation; cold parity/cohort được
  báo cáo riêng.

Log bắt buộc ghi:

| Split | total users | eligible users | users without novel truth | catalog items |
|---|---:|---:|---:|---:|
| Validation | PENDING | PENDING | PENDING | PENDING |
| Test | PENDING | PENDING | PENDING | PENDING |

## 4. Metric definitions khớp evaluator

### 4.1 HR@10

Với user `u`, `HR_u@10 = 1` nếu top 10 có ít nhất một item thuộc novel truth,
ngược lại bằng 0. Report là mean trên eligible users. Đây không phải Recall@10.

### 4.2 NDCG@10

Binary relevance:

```text
DCG_u@10  = sum(1 / log2(rank + 1)) trên relevant ranks trong top 10
IDCG_u@10 = sum(1 / log2(rank + 1)), rank=1..min(|truth_u|, 10)
NDCG_u@10 = DCG_u@10 / IDCG_u@10
```

Mean chỉ trên eligible users. Không dùng NDCG lấy từ sampled candidate set để
so với full-catalog NDCG.

### 4.3 GAUC

Evaluator tính exact user AUC giữa scores của toàn bộ novel-positive items và
toàn bộ unseen non-positive items. Score ties nhận average rank. GAUC là mean
unweighted của user AUC trên eligible users. Mọi paper phải nói rõ đây là macro
per-user GAUC, không phải global pooled AUC hoặc impression-weighted GAUC.

### 4.4 Reporting metrics cần thêm để tương thích literature

| Metric | Status | Rule |
|---|---|---|
| Recall@10 | `IMPLEMENTATION_REQUIRED` | per-user `hits / cardinality(truth)`, mean eligible users |
| MRR@10 | `OPTIONAL` | reciprocal rank của relevant item đầu tiên |
| catalog coverage@10 | `OPTIONAL` | unique recommended items / catalog |
| cold-item HR/NDCG | `REQUIRED` | report cohort size và denominator |

Recall/MRR không được tính bằng notebook riêng. Chúng phải dùng cùng prepared
split, masking và deterministic ranking seam; schema/artifact tests phải pass.

### 4.5 Statistical testing

- Giữ per-user vectors cho HR, NDCG, GAUC (và Recall khi triển khai).
- Paired bootstrap: 2,000 resamples, 95% interval.
- Primary comparison: Hybrid trừ strongest baseline trên cùng users.
- Strongest baseline cho mỗi primary metric được chọn bằng validation mean từ
  danh sách model preregistered và khóa trước khi TEST. Nếu selection và
  inference dùng cùng sample, bắt buộc dùng simultaneous/max-statistic interval.
- Khi thử nhiều candidate/model, báo số comparisons và dùng Holm correction cho
  exploratory p-values; release decision vẫn theo preregistered paired CI.
- Report mean, CI và absolute delta; không chỉ report relative percentage.

Exact bootstrap RNG schedule cho single-seed gates:

```text
GAUC dominance seed = training_seed + 11
HR@10 dominance seed = training_seed + 13
NDCG@10 dominance seed = training_seed + 17
```

Mỗi single-seed gate cũng dùng two-sided percentile 95%, quantile interpolation
`linear` và NumPy `Generator(PCG64(gate_seed))` trên paired user deltas.

Primary final estimand là mean paired delta qua cả user và training seed. Với ba
seed `42, 2027, 31415`, mỗi hierarchical-bootstrap replicate phải:

1. sample ba seed có hoàn lại;
2. với **mỗi seed occurrence đã sample**, sample độc lập có hoàn lại user IDs
   từ giao của eligible users trên cả sáu finalist; nếu cùng seed được lấy hai
   lần thì hai user resamples vẫn độc lập;
3. trong từng occurrence, dùng cùng user indices cho Hybrid và locked baseline;
4. lấy mean paired delta qua toàn bộ sampled seed/user cells.

Interval là two-sided percentile 95% với endpoints 2.5% và 97.5%, quantile
interpolation `linear`. RNG phải là NumPy `Generator(PCG64(42))`; không dùng
global RNG. Point estimate là mean paired delta của toàn bộ original seed/user
cells. Aggregate bootstrap dùng 2,000 replicates. Báo thêm mean/CI từng seed để
lộ instability.
Việc chỉ average ba seed trước rồi bootstrap users bỏ qua seed-level uncertainty
và không được dùng cho paper claim. Vì implementation hiện tại còn làm theo cách
đó, aggregate release phải được sửa và có parity test trước final experiments.

## 5. Project gates: target, không phải observed result

Nguồn: `master/standard.md` và resolved config.

| Gate | Threshold | Label |
|---|---:|---|
| Hybrid GAUC | `>= 0.75` | TARGET |
| Hybrid HR@10 | `>= 0.15` | TARGET |
| Hybrid NDCG@10 | `>= 0.08` | TARGET |
| Random GAUC | `[0.48, 0.52]`, CI contains `0.5` | TARGET |
| Paired dominance | CI lower `> 0` for each primary metric | TARGET |
| Semantic traps | all target cases across `10/10` traps | TARGET |
| Cold parity | PASS | TARGET |
| Training safety | finite and validation GAUC `>= 0.50` | KILL-SWITCH |

Các target `.75/.15/.08` không phải ước lượng từ literature, không được điền
vào result table và không chứng minh model thành công trước khi chạy.

## 6. Reference-compatible model matrix

### 6.1 Mandatory internal baselines

| Tier | Model | Implementation origin | Objective policy | Status |
|---|---|---|---|---|
| Sanity | Random, MostPop | local deterministic | no tuning | NOT_RUN |
| Neighborhood | ItemKNN/ItemCF | local + parity fixture | method-faithful | NOT_RUN |
| Rule | Apriori | local immutable rules | no neural tuning | NOT_RUN |
| Latent | BPR-MF | [RecBole](https://github.com/RUCAIBox/RecBole) third-party benchmark implementation | method-faithful pairwise objective | NOT_ADAPTED |
| Graph | LightGCN | RecBole third-party benchmark implementation | method-faithful graph/BPR recipe | NOT_ADAPTED |
| Sequence | SASRec | RecBole third-party benchmark implementation | method-faithful sequential recipe | NOT_ADAPTED |
| Sequence | BERT4Rec | RecBole third-party benchmark implementation | method-faithful masked-item recipe | NOT_ADAPTED |
| Novel basket | BTBR | [official code](https://github.com/liming-7/Mask-Swap-NNBR) | official basket mask/swap recipe | NOT_ADAPTED |
| Transfer/content | UniSRec | [official code](https://github.com/RUCAIBox/UniSRec) | official pretrain/fine-tune modes | NOT_ADAPTED |
| Language/CF | AlphaRec | [official code](https://github.com/LehengTHU/AlphaRec) | official language-representation CF recipe | NOT_ADAPTED |
| Graph-CL | SimGCL | [official code](https://github.com/Coder-Yu/QRec) | official contrastive recipe | NOT_ADAPTED |
| Graph-CL | XSimGCL | [official code](https://github.com/Coder-Yu/SELFRec) | official contrastive recipe | NOT_ADAPTED |
| Graph-CL | LightGCL | [official code](https://github.com/HKUDS/LightGCL) | official global contrast recipe | NOT_ADAPTED |
| Project | independent Deep | ai-service | immutable resolved config | NOT_RUN |
| Project | Hybrid | ai-service | immutable resolved config | NOT_RUN |

LLaRA và A-LLMRec là optional 7B compute-tier comparisons. Nếu không chạy
đúng official recipe do hardware, paper phải công bố exclusion và không dùng
claim “state of the art against LLM recommenders”.

### 6.2 Adapter acceptance record

Một adapter chỉ chuyển `READY` khi toàn bộ cột kiểm chứng của chính model đó có
artifact. Không được suy trạng thái của model này từ adapter của model khác.

| Adapter | Revision pinned | License | Toy parity | Reference reproduction | v5 split/mask parity | Per-user evidence |
|---|---|---|---|---|---|---|
| BPR-MF | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| LightGCN | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| SASRec | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| BERT4Rec | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| BTBR | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| UniSRec | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| AlphaRec | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| SimGCL | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| XSimGCL | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| LightGCL | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

Text-aware adapter còn phải khóa `text_encoder_id`, revision, tokenizer,
prompt/text-serialization hash, embedding SHA, generation recipe và license.
Thiếu một field thì UniSRec/AlphaRec/LLM adapter không được gọi là faithful.

### 6.3 Reference-reproduction tolerance record

Mỗi hàng phải được khóa **trước** reproduction run. Không được nhìn output rồi
chọn tolerance. `PENDING` chặn adapter chuyển sang `READY`.

| Adapter | Reference dataset/version | Reference statistic/protocol | Reported center | Reproduction seeds + aggregation | Allowed abs/relative delta | Software/hardware allowance | Deterministic pass rule |
|---|---|---|---:|---|---|---|---|
| BPR-MF | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| LightGCN | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| SASRec | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| BERT4Rec | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| BTBR | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| UniSRec | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| AlphaRec | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| SimGCL | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| XSimGCL | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| LightGCL | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

Pass rule tối thiểu phải chỉ rõ metric nào phải nằm trong tolerance, cách xử lý
reported multi-run mean/std, và failure nào là adapter bug thay vì unsupported
hardware. Author-official implementation được ưu tiên; implementation benchmark
bên thứ ba như RecBole phải ghi rõ provenance và không được gọi là official code.
GPU baseline-reproduction jobs được phép trong namespace cô lập sau khi hàng
tương ứng được freeze; chúng không mở quyền train Hybrid.

### 6.4 Locked baseline registry

Trước proposed/Hybrid training, codebase phải publish và verified-load một
immutable registry có exact schema:

```text
schema_version
six_field_dataset_lineage
eligible_user_ids_sha256
seed_set: [42, 2027, 31415]
model_id -> paper, adapter revision, base_config_sha256
model_record: LearnedModelRecord | StatelessBaselineRecord | FittedBaselineRecord
LearnedModelRecord -> seed -> {
  run_id, seed_value, resolved_config_sha256, checkpoint_sha256,
  validation_per_user_sha256
}
StatelessBaselineRecord -> {
  implementation_sha256, deterministic_spec_sha256, config_sha256,
  seed_schedule, validation_per_user_sha256_by_seed
}
FittedBaselineRecord -> {
  implementation_sha256, fitted_model_artifact_sha256, config_sha256,
  seed_schedule, validation_per_user_sha256_by_seed
}
selected_baseline_id_by_metric: {gauc, hr_at_10, ndcg_at_10}
selection_rule: highest validation mean across the locked seed/user cells,
                then lexicographically smaller model_id
canonical_artifact_sha256
```

TEST và aggregate release phải nhận registry SHA và dùng đúng locked model ID
cho từng metric; cấm reselect strongest competitor trên TEST. Mỗi TEST artifact
phải bind đúng seed và identity đã khóa: run/checkpoint với learned model;
implementation/spec hoặc fitted-model artifact với non-neural baseline. Không
ghi TEST metric vào pre-TEST registry. Registry phải gồm mọi mandatory adapter
đã `READY`, không chỉ local Random/Deep/Apriori/ItemCF.

`Random` dùng `StatelessBaselineRecord` và khóa toàn bộ random-seed schedule;
`MostPop` có thể stateless nếu fit được biểu diễn hoàn toàn bởi deterministic
spec + lineage, còn `ItemCF`/`Apriori` phải dùng `FittedBaselineRecord`. Learned
models bắt buộc có run/checkpoint cho từng seed. Không dùng placeholder SHA hoặc
nullable checkpoint để ép ba loại record vào một shape.

`base_config_sha256` hash phần config chưa áp seed override; mỗi learned seed
entry phải bind `seed_value` và exact `resolved_config_sha256` sau override.
Selection/release reject nếu seed key, embedded seed hoặc resolved SHA lệch nhau.
Current evaluator/release chưa có contract này, vì vậy proposed training tiếp
tục `BLOCKED` cho tới khi có typed registry, corruption tests và TEST lock test.

## 7. External-dataset experiment tracks

### 7.1 Vietnamese track

Primary candidate: [ViEcomRec](https://doras.dcu.ie/29693/). Record before use:

| Field | Value |
|---|---|
| exact dataset revision/hash | PENDING |
| license and redistribution | PENDING |
| task/labels | PENDING |
| official split/protocol | PENDING |
| harmonized protocol mapping | PENDING |
| supported baseline subset | PENDING |

Vietnamese Food Dataset và ViHoRec được dùng nếu task phù hợp. ViHoRec là 2026
preprint và chủ yếu hữu ích cho short-history-user cold-start sensitivity, không
phải strict zero-history protocol và không thay thế retail cold-item evaluation.

### 7.2 English/multilingual track

Primary candidate: [Amazon-M2](https://papers.nips.cc/paper_files/paper/2023/hash/193df57a2366d032fb18dcac0698d09a-Abstract-Datasets_and_Benchmarks.html).
Nó gần domain shopping sessions nhưng không có tiếng Việt. Tenrec là secondary
multi-behavior benchmark.

Mỗi external dataset có hai result tables riêng:

1. `OFFICIAL_PROTOCOL_REPRODUCTION` — dùng split/metric của source;
2. `HARMONIZED_PROTOCOL_COMPARISON` — chạy proposed + baselines dưới cùng
   adapter protocol.

Không gộp hai bảng và không average metrics giữa datasets.
Nếu adapter phải bỏ signal hoặc đổi objective thiết yếu của proposed method,
model đó được đổi tên thành reduced-method ablation; kết quả không được dùng làm
external replication của full Hybrid.

## 8. Hyperparameter và compute budget preregistration

| Field | Value |
|---|---|
| final seeds | `42, 2027, 31415` |
| tuning data | validation only |
| test access | after config freeze only |
| max trials per comparable tier | PENDING BEFORE RUN |
| early-stopping metric/patience | PENDING FROM RESOLVED CONFIG |
| bootstrap samples | 2,000 |
| GPU/CPU/RAM/driver | PENDING RUNTIME RECEIPT |
| max wall time/model | PENDING BEFORE RUN |
| failed-run reuse | forbidden |

Equal budget không có nghĩa hyperparameter giống nhau. Mỗi model có search space
method-faithful, nhưng số trial/wall-time budget phải được khai báo trước.

## 9. Empty result tables

### 9.1 Validation — benchmark v5

| Model | HR@10 | NDCG@10 | GAUC | Recall@10 | 95% CI artifact | Run/checkpoint SHA |
|---|---:|---:|---:|---:|---|---|
| Random | — | — | — | — | NOT_RUN | — |
| MostPop | — | — | — | — | NOT_RUN | — |
| ItemCF | — | — | — | — | NOT_RUN | — |
| Apriori | — | — | — | — | NOT_RUN | — |
| BPR-MF | — | — | — | — | NOT_RUN | — |
| LightGCN | — | — | — | — | NOT_RUN | — |
| SASRec | — | — | — | — | NOT_RUN | — |
| BERT4Rec | — | — | — | — | NOT_RUN | — |
| BTBR | — | — | — | — | NOT_RUN | — |
| UniSRec | — | — | — | — | NOT_RUN | — |
| AlphaRec | — | — | — | — | NOT_RUN | — |
| SimGCL | — | — | — | — | NOT_RUN | — |
| XSimGCL | — | — | — | — | NOT_RUN | — |
| LightGCL | — | — | — | — | NOT_RUN | — |
| Independent Deep | — | — | — | — | NOT_RUN | — |
| Hybrid | — | — | — | — | NOT_RUN | — |

### 9.2 Test and external datasets

Không tạo bảng TEST cho tới khi aggregate validation selection được khóa. Không
tạo external result row cho tới khi official reproduction receipt pass.

## 10. Run registry template

Mỗi execution append một record; không sửa record cũ:

```yaml
experiment_id: PENDING
timestamp_utc: PENDING
purpose: baseline_reproduction | harmonized_validation | ablation | final_test
dataset_id: PENDING
dataset_lineage: PENDING
model_reference: PENDING
official_code_revision: PENDING
adapter_revision: PENDING
resolved_config_sha256: PENDING
seed: PENDING
hardware_receipt: PENDING
status: planned | running | failed | interrupted | completed | rejected
terminal_reason: PENDING
checkpoint_sha256: PENDING
metric_artifact_sha256: PENDING
notes: PENDING
```

## 11. Failure and abort log

| Time | Stage | Run | Signal | Action | Evidence SHA |
|---|---|---|---|---|---|
| — | — | — | No experiment executed | Keep training blocked | — |

### Fail-closed policy

- Adapter reproduction fail: không chạy proposed model để “lấy số trước”.
- Non-finite/corruption/lineage mismatch: dừng toàn campaign.
- Seed-42 Hybrid fail promotion gate: không train 2027/31415.
- Public benchmark reproduction không đạt documented tolerance: sửa/replace
  adapter hoặc retire current training backend.
- Metric definition thay đổi: tạo experiment namespace mới; không trộn runs.

## 12. Paper-result acceptance checklist

- [ ] Immutable dataset and six-field lineage verified.
- [ ] Vietnamese text/provenance/license receipt complete.
- [ ] At least one official public-dataset result reproduced.
- [ ] Mandatory baseline adapters pass parity tests.
- [ ] Same split/candidate/masking/metric contract for harmonized comparison.
- [ ] Three final seeds complete without source/config changes.
- [ ] Per-user metrics and paired confidence intervals verified.
- [ ] Cold-item and semantic cohorts reported with denominators.
- [ ] TEST opened once, after validation selection.
- [ ] Runtime measured on fixed runner after bundle verification.
- [ ] Every table cell traceable to artifact SHA.
- [ ] Negative and contradictory results retained.

Until every applicable item is checked, the paper may describe only protocol
and research questions; it may not contain a Results claim.
