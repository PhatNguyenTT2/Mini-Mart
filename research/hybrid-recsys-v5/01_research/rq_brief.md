# Stage 1A — Research Question Brief

> Material Passport: `stage1a_v1` · trạng thái `UNVERIFIED` · kế thừa `intake_v1`  
> Phạm vi: chuẩn hóa câu hỏi, hypotheses, estimands và biên claim; chưa tạo bibliography, chưa viết paper, chưa chạy experiment.

## 1. Quyết định scoping

Paper được định vị là **quantitative methods/empirical benchmarking study**. Đối tượng kiểm tra không phải “hành vi người mua Việt Nam nói chung”, mà là hiệu quả xếp hạng của một Hybrid recommender dưới protocol đã khóa trên controlled/semi-synthetic Vietnamese retail benchmark v5, sau đó mới kiểm tra khả năng chuyển sang dữ liệu công khai tương thích.

Câu hỏi chính dùng một outcome trung tâm để tránh compound RQ và tránh chọn metric thuận lợi hậu nghiệm. `NDCG@10` là **primary inferential estimand**; `HR@10` và macro per-user `GAUC` là confirmatory supporting outcomes. H1 chỉ pass khi cả ba paired 95% CI có lower bound `> 0`.

## 2. Câu hỏi nghiên cứu chính

### Canonical manuscript wording

**Under a fixed temporal novel-purchase full-catalog protocol on the controlled Vietnamese retail benchmark v5, does the proposed decoupled Wide-and-Deep Two-Tower Hybrid improve ranking effectiveness over the strongest faithfully reproduced baseline selected using validation data?**

### Bản dịch điều hành

Trên protocol temporal novel-purchase full-catalog cố định của controlled Vietnamese retail benchmark v5, mô hình decoupled Wide-and-Deep Two-Tower Hybrid có cải thiện hiệu quả xếp hạng so với strongest faithfully reproduced baseline được chọn bằng validation hay không?

### Operational definition

- Primary outcome: mean paired difference `Hybrid − locked baseline` của per-user `NDCG@10` trên TEST.
- Supporting confirmatory outcomes: cùng paired difference cho `HR@10` và macro per-user `GAUC`.
- Comparator được chọn **riêng cho từng metric** bằng validation mean từ baseline registry đã preregister, sau đó khóa trước khi mở TEST.
- Candidate universe là toàn bộ catalog; seen items bị mask; chỉ eligible users có novel organic purchase truth được đưa vào estimand.
- “Improve” không đồng nghĩa với causal effect ngoài protocol, SOTA, hay real-world superiority.

## 3. Sub-questions chuẩn hóa

| ID | Câu hỏi | Vai trò |
|---|---|---|
| **RQ2 — Cold item** | Within the preregistered cold-item cohort, does Hybrid preserve or improve ranking quality relative to independent Deep and the strongest collaborative-only comparator? | Kiểm tra content/transfer benefit đúng phạm vi cold-item; không suy diễn sang cold-user. |
| **RQ3 — Mechanism** | On the train-defined rule-aligned cohort, does removing the Apriori-derived Wide branch reduce ranking quality relative to the full Hybrid? | Kiểm tra Wide branch có đóng góp relevance hay chỉ thay đổi score/top-k. |
| **RQ4 — External validity** | Does the direction of the locked Hybrid effect replicate on at least one public external commerce dataset that preserves the essential model and task contract? | Kiểm tra khả năng chuyển; dataset không tương thích chỉ là sensitivity/reduced-method ablation. |
| **RQ5 — Efficiency** | After all accuracy gates pass, does the verified bundle satisfy preregistered latency, throughput, and memory gates on a fixed runner? | Claim hệ thống chỉ được xét sau accuracy; threshold phải khóa ở Stage 1E trước benchmark runtime. |

## 4. Hypotheses và tiêu chí bác bỏ

### H1 — Ranking superiority

Hybrid có paired 95% CI lower bound `> 0` so với locked strongest baseline trên từng metric `NDCG@10`, `HR@10`, và macro per-user `GAUC`.

- `NDCG@10` là primary inferential estimand.
- H1 là conjunction: fail một metric thì H1 fail; không đổi metric chính hoặc hạ gate sau TEST.
- Các absolute project floors `.08/.15/.75` chỉ là acceptance targets nội bộ, không phải expected results hoặc hiệu ứng lấy từ literature.

### H2 — Cold-item preservation

Trên eligible users có ít nhất một cold-item novel truth, lower bound của paired 95% CI cho `NDCG@10(Hybrid − independent Deep)` phải `>= 0`, đồng thời semantic-trap gate phải pass `10/10` theo fixture đã khóa.

- Báo thêm cold-item `HR@10`, cohort size và denominator.
- So sánh với strongest collaborative-only model là secondary contrast.
- Không dùng kết quả này để tuyên bố giải quyết new-user/zero-history cold-start.

### H3 — Wide-branch mechanism

Trên rule-aligned cohort được tạo chỉ từ train-mined Apriori rules, lower bound của paired 95% CI cho `NDCG@10(full Hybrid − no-Wide ablation)` phải `> 0`.

- Antecedent phải nằm trong user history; consequent phải là held-out relevant item.
- Rule mining, support/confidence thresholds và cohort construction không được dùng validation/test targets để học rule.
- Nếu H3 fail, Wide branch không được trình bày là demonstrated mechanism contribution.

### H4 — External replication

Ít nhất một public external commerce dataset phải giữ được essential Hybrid contract và cho paired `NDCG@10` effect cùng hướng với v5 dưới harmonized protocol; confirmatory pass yêu cầu lower 95% CI `> 0`.

- Nếu không có dataset thỏa signal/task compatibility, H4 là `NOT_TESTED`, không phải `PASS` hay `FAIL`.
- Vietnamese dataset không giữ đủ mechanism được ghi là domain sensitivity hoặc reduced-method ablation.
- Raw metrics từ các dataset khác nhau không được so theo hàng ngang hay average chung.

### RQ5 không có H5 inferential ở Stage 1A

Efficiency là engineering acceptance gate. Stage 1E phải khóa runner, warm-up, batch size, repetition count, latency statistic, throughput definition, peak RAM/VRAM measurement và numerical thresholds trước khi chạy. Không được đặt threshold sau khi nhìn profile.

## 5. Estimands

| ID | Population/unit | Contrast | Outcome | Point estimate | Uncertainty/decision |
|---|---|---|---|---|---|
| `E1-NDCG` | Eligible TEST user × training seed | Hybrid − metric-specific locked baseline | Per-user NDCG@10 | Mean paired delta qua seed/user cells | Hierarchical paired bootstrap, 2,000 replicates, 95% percentile CI; primary. |
| `E1-HR` | Như `E1-NDCG` | Hybrid − locked HR baseline | Per-user HR@10 | Mean paired delta | Cùng bootstrap; H1 supporting gate. |
| `E1-GAUC` | Như `E1-NDCG` | Hybrid − locked GAUC baseline | Macro per-user GAUC | Mean paired delta | Cùng bootstrap; H1 supporting gate. |
| `E2-COLD` | Eligible users có cold-item novel truth | Hybrid − independent Deep | Cold-item NDCG@10 | Mean paired delta | 95% hierarchical paired CI; lower bound `>= 0`; cohort size bắt buộc. |
| `E3-WIDE` | Train-defined rule-aligned eligible users | Full Hybrid − no-Wide ablation | NDCG@10 | Mean paired delta | 95% hierarchical paired CI; lower bound `> 0`. |
| `E4-EXT` | Dataset-native eligible users trên một full-contract external dataset | Hybrid − locked harmonized comparator | NDCG@10 | Dataset-specific mean paired delta | Dataset-specific paired CI; không pool raw metric qua dataset. |
| `E5-SYS` | Fixed runner × fixed request workload | Verified Hybrid bundle so với frozen gates | p50/p95 latency, throughput, peak RAM/VRAM, bundle size | Statistic theo runtime protocol | Pass/fail từng gate; chỉ chạy sau accuracy pass. |

Primary aggregate bootstrap dùng seeds `42`, `2027`, `31415`, resample seed occurrences rồi resample users độc lập trong mỗi occurrence, dùng NumPy `Generator(PCG64(42))`, 2,000 replicates và percentile endpoints `2.5%/97.5%`. Thành phần finalist set và eligible-user intersection phải được khóa tại Stage 1E.

## 6. Scope

### In scope

- Top-k retail/e-commerce recommendation dưới temporal novel-purchase evaluation.
- Controlled/semi-synthetic benchmark v5 với Vietnamese-language catalog, generated behavior, full catalog và cold-item/rule cohorts.
- Faithful baseline reproduction, shared evaluator, fair validation-only tuning và three-seed paired inference.
- Two-Tower/Deep, Wide-and-Deep, Apriori/rule, collaborative, sequence, graph-contrastive, content/transfer baselines theo compatibility gate.
- Một full-contract public external validation và một Vietnamese domain-sensitivity track nếu license/schema cho phép.
- Accuracy, mechanism, cold-item, reproducibility và post-accuracy efficiency.

### Out of scope

- Online A/B testing, causal user-behavior claims, business uplift hoặc production deployment effectiveness.
- New-user/zero-history cold-start nếu không có cohort/protocol riêng.
- Cross-dataset raw-score league tables.
- Human-subject surveys/interviews, demographic fairness claims hoặc personalization harms not measurable from available fields.
- 7B LLM baselines khi không thể chạy method-faithful recipe; việc loại phải được disclosure.
- Absolute SOTA, “solve cold start”, “real-world Vietnamese shopper behavior”, hoặc “first Vietnamese dataset” claims.

### Domain, population, geography, timeframe

- **Domain:** offline top-k recommender-system benchmarking for retail/e-commerce.
- **Population:** eligible user histories và catalog candidates theo dataset contract; v5 units là generated user histories, không phải recruited human participants.
- **Geography/language:** Vietnamese retail context ở v5/Vietnamese sensitivity; external multilingual commerce chỉ dùng cho generalization test.
- **Experiment timeframe:** frozen dataset-specific temporal windows; v5 train `2026-01-01`–`2026-06-19`, validation `2026-06-20`–`2026-07-10`, test `2026-07-11`–`2026-08-01` UTC.
- **Literature timeframe:** evidence framing đến 2026 sẽ được xác minh ở Stage 1B, không được coi là hoàn tất trong artifact này.

## 7. FINER assessment

ARS research-question agent dùng thang 1–5; Schema 1 dùng 1–10. Bảng giữ cả hai để không làm mất semantics.

| Dimension | ARS /5 | Schema 1 /10 | Rationale |
|---|---:|---:|---|
| Feasible | 3.5 | 7 | Protocol rõ, nhưng adapter registry, external compute và dataset compatibility chưa hoàn tất. |
| Interesting | 4.5 | 9 | Kết nối reproducibility, hybrid mechanism và Vietnamese retail context. |
| Novel | 3.5 | 7 | Novelty chỉ là provisional boundary; Stage 1B phải kiểm chứng, không được khẳng định trước. |
| Ethical | 4.0 | 8 | Không tuyển người tham gia; vẫn cần provenance/license/privacy audit cho catalog và public data. |
| Relevant | 4.5 | 9 | Trực tiếp trả lời vấn đề so sánh recommender không đồng protocol và cold-item evaluation. |

**Total:** `20/25` (tương đương `40/50`). Kết luận: RQ đủ rõ để chuyển sang literature review, nhưng chưa đủ điều kiện chạy confirmatory experiments.

## 8. Theoretical/operational framework

Framework làm việc là **memorization–generalization complementarity**:

- Wide/Apriori branch biểu diễn explicit co-purchase regularities đã quan sát trong train.
- Deep Two-Tower/content branch biểu diễn khả năng tổng quát hóa từ history và item features.
- Decoupled fusion chỉ được xem là mechanism contribution nếu H3 pass; nếu không, kiến trúc chỉ là implementation choice.

Đây là operational framework của paper, chưa phải một lý thuyết mới hoặc claim đã được literature xác nhận.

## 9. Contribution boundaries

| Candidate contribution | Điều kiện để được claim | Nếu điều kiện fail |
|---|---|---|
| Shared-protocol empirical comparison | Adapter provenance, parity, registry lock, sealed per-user results | Chỉ mô tả protocol, không claim superiority. |
| Hybrid ranking improvement | H1 pass trên frozen TEST | Báo null/negative result; bỏ superiority claim. |
| Cold-item support | H2 pass và denominator minh bạch | Giới hạn hoặc bỏ cold-item claim; tuyệt đối không chuyển thành cold-user claim. |
| Apriori/Wide mechanism | H3 pass trên train-defined cohort | Gọi là ablation-negative; không claim mechanism contribution. |
| External validity | H4 pass trên full-contract public dataset | Giới hạn kết luận ở v5; nếu không có dataset phù hợp, ghi `NOT_TESTED`. |
| Vietnamese benchmark/resource | Dataset lineage, language provenance, generator disclosure, distribution audit và release/license pass | Chỉ gọi là controlled internal benchmark, không gọi public/real-world dataset contribution. |
| Lightweight deployment | Accuracy pass trước, sau đó RQ5 gates pass trên fixed runner | Chỉ báo profile, không claim deployment readiness. |

## 10. Failure conditions và stop rules

- Bất kỳ thay đổi split, candidate universe, masking, metric implementation hoặc test access nào tạo experiment namespace mới.
- Official reproduction ngoài tolerance hoặc parity fail khiến adapter đó không được vào harmonized registry; failure phải được giữ trong log.
- Nếu mandatory comparator không chạy method-faithful vì hardware/software, scope claim phải thu hẹp; không thay bằng metric chép từ paper.
- Nếu H1 fail sau seed `42`, campaign stop rule trong experiment plan được kích hoạt; không dùng seeds bổ sung để “cứu” kết quả nếu chưa preregister.
- Nếu source/license/provenance của v5 hoặc external dataset không pass, không sử dụng dataset đó cho paper claim.
- Null/negative results là kết quả hợp lệ và không được sửa hypothesis/gate hậu nghiệm.

## 11. Stage bindings

- **Stage 1B:** kiểm chứng novelty và xây claim–source map; không thay đổi estimand bằng kết quả literature thuận lợi.
- **Stage 1E-Plan:** đóng băng comparator set, H2 cohort implementation, H3 rule thresholds, tuning budget, runtime gates và preregistration.
- **Stage 1E-Run:** tạo duy nhất số liệu có thể đi vào paper từ sealed artifacts.
- **Stage 2:** chỉ viết claims nằm trong contribution boundaries ở trên.

