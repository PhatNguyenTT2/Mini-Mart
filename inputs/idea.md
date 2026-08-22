# Research Idea: Reproducible Hybrid Recommendation for Vietnamese Retail

## 0. Trạng thái và phạm vi

```text
DOCUMENT_STATUS          = RESEARCH_DESIGN_ONLY
ACCEPTED_MODEL_RESULTS   = NONE
HYBRID_VICTORY           = NOT_ESTABLISHED
PRODUCTION_TRAINING      = BLOCKED_BY_RESEARCH_GATES
```

Các blocker đang mở: six-field lineage; language/provenance/license receipt;
reference-adapter reproduction; immutable seed-indexed baseline registry; và
seed-aware statistical implementation. Venue selection không chặn diagnostic
research, nhưng chặn submission formatting và policy freeze.

Tài liệu này là đặc tả nghiên cứu cho bài báo mới. Nó không kế thừa số liệu,
kết luận hoặc tuyên bố thành công từ `workspace/final/paper.tex`. Paper cũ chỉ
được giữ để truy vết lịch sử vì dùng dataset 500 users/1,380 items, random
80/10/10 split, quy trình training không có provenance và các bảng kết quả
không được ràng buộc với immutable artifacts.

Ba nguyên tắc khóa:

1. Không ghi metric mô hình nếu chưa có manifest, checkpoint, per-user evidence
   và hash có thể kiểm chứng.
2. Không so sánh trực tiếp các con số lấy từ hai dataset, hai candidate universe
   hoặc hai split protocol khác nhau.
3. Không mở production training của `ai-service` nếu chưa tái hiện được các
   baseline tham chiếu bằng official implementation hoặc adapter đã kiểm chứng.

## 1. Sửa các giả định nền tảng

### 1.1 Dataset hiện tại thực sự là gì?

Benchmark v5 được đặc tả như một **controlled/semi-synthetic Vietnamese retail
benchmark**. Chỉ sau khi snapshot strict-load và six-field lineage receipt pass,
nó mới được gọi là một benchmark instance bất biến:

- catalog chứa metadata sản phẩm bán lẻ tiếng Việt từ catalog của dự án; script
  bootstrap ghi nhận nguồn thu thập metadata từ Bách Hóa Xanh;
- user, persona, event, session và order behavior được sinh có kiểm soát từ
  immutable generator spec với seed cố định;
- các semantic-trap cohort và co-purchase transitions được cài đặt để kiểm tra
  từng cơ chế cụ thể;
- dữ liệu không phải log hành vi tự nhiên của 5,000 khách hàng thật và không
  được mô tả là “proprietary real-world user behavior”.

Hệ quả: benchmark phù hợp cho falsification, ablation, data-lineage và kiểm tra
cơ chế Wide/Deep. Nó **không đủ** để suy rộng hành vi mua sắm của người Việt nếu
không có thêm đánh giá trên dữ liệu quan sát thực hoặc benchmark công khai.

### 1.2 “Dataset tiếng Việt” phải được định nghĩa chính xác

Điểm tiếng Việt hiện nằm chủ yếu ở product title/category/brand và bối cảnh bán
lẻ. Trước khi viết paper, cần một language-and-provenance receipt gồm:

- tỷ lệ title/category được language-ID là tiếng Việt;
- tỷ lệ text trống, duplicate và normalization collision;
- nguồn, ngày thu thập, điều khoản sử dụng và quyền công bố từng trường;
- tỷ lệ item thật, item được bổ sung và semantic-trap item;
- kiểm tra PII và khả năng công bố dataset/model artifact.

Nếu receipt này chưa đạt, chỉ được gọi đây là “Vietnamese-language catalog
benchmark”, không được gọi là “public Vietnamese recommender dataset”.

### 1.3 Cold start hiện tại là cold-item, không phải cold-user

Benchmark giữ 250 cold items. Điều này hỗ trợ câu hỏi về item cold-start bằng
content features. Nó không tự động chứng minh new-user cold-start. New-user cần
cohort không có lịch sử hoặc một protocol elicitation riêng. Kết quả cold-item
không được diễn giải thành “eliminate cold start” hay “solve user cold-start”.

### 1.4 Điều kiện so sánh công bằng

Yêu cầu “mọi model phải dùng cùng training method” cần được diễn đạt lại:

- bắt buộc giống nhau: dataset version, train/validation/test boundary,
  eligibility, candidate universe, seen-item masking, metric implementation,
  seed set, tuning budget, stopping information budget và statistical test;
- phải trung thành với từng phương pháp: BPR dùng pairwise objective, SASRec dùng
  sequential objective, graph contrastive methods dùng objective chính thức;
- không ép các phương pháp khác bản chất dùng cùng loss/optimizer nếu điều đó làm
  biến dạng thuật toán;
- phải có cả bảng **official-protocol reproduction** và bảng **harmonized
  protocol**. Chỉ bảng harmonized mới dùng cho kết luận model A hơn model B.

Raw HR/NDCG/GAUC từ paper khác không phải baseline của dự án. Baseline chỉ tồn
tại sau khi chạy lại trên cùng data/protocol hoặc sau khi chạy cả hai phương
pháp trên cùng external benchmark.

## 2. Fact sheet cho benchmark v5

Nguồn contract: `master/standard.md` và
`backend/docs/chatbot/seed-product/benchmark-spec-v5.json`. Các giá trị này là
đặc tả dataset, **không phải kết quả mô hình**.

| Thuộc tính | Giá trị contract | Cách diễn giải đúng |
|---|---:|---|
| Users | 5,000 | generated identities, không phải verified real customers |
| Items | 5,200 | Vietnamese retail catalog plus controlled test items |
| Cold items | 250 | cold-item cohort |
| Events | 823,371 | event rows, có thể lặp user–item |
| Temporal split | 658,697 / 82,337 / 82,337 | train / validation / test |
| Distinct user–item cells | 356,181 | numerator đúng cho interaction-matrix density |
| Distinct-cell density | 1.3699% | `356181 / (5000 * 5200)` |
| Event-frequency density | 3.1668% | `823371 / (5000 * 5200)`; không gọi là matrix density |
| Orders declared by spec | 15,000 | 14,250 organic + 750 semantic; runtime receipt required |
| Personas declared by spec | 8 | generated affinity segments, không phải discovered demographics |
| Evaluation target | organic novel purchases | target purchase trừ toàn bộ seen history |
| Ranking | full catalog, `k=10` | mask seen; tie-break `(-score, raw_product_id)` |

VAL dùng train history; TEST dùng train+VAL history. User không có novel organic
purchase trong split không đóng góp HR/NDCG/GAUC. Mọi paper table phải ghi cả
`num_total_users` và `num_eligible_users`.

Các kiểm tra còn thiếu trước khi dataset có thể là contribution:

- immutable six-field lineage và public data card;
- language/provenance/license audit;
- distribution plots cho history length, item popularity và repeat purchase;
- comparison giữa generated distributions và ít nhất một real-world dataset;
- privacy/ethics statement và release feasibility.

### 2.1 Ma trận khác biệt với các benchmark tham chiếu

“Ưu thế” dưới đây là ưu thế **thiết kế có thể kiểm chứng từ spec/protocol**, không
phải bằng chứng model v5 tốt hơn model chạy trên dataset khác.

| Dataset | Ngôn ngữ/domain | Signal và task gốc | V5 cho phép kiểm tra thêm | Giới hạn của v5 khi so sánh |
|---|---|---|---|---|
| Benchmark v5 | catalog bán lẻ tiếng Việt; generated behavior | temporal multi-behavior, novel purchase, full catalog | deterministic persona/rule/trap/cold-item cohorts và six-field lineage | không có natural-user behavior hoặc public external validity trước audit |
| [ViEcomRec](https://doras.dcu.ie/29693/) | Vietnamese face-cleanser e-commerce | 369,099 user–item interactions; content/attribute baselines | v5 rộng hơn về catalog, behavior types và controlled mechanism tests | ViEcomRec cung cấp public interaction reference gần domain; phải chạy harmonized task, không so raw metrics |
| [Vietnamese Food Dataset](https://aclanthology.org/2024.paclic-1.4/) | Vietnamese food | food recommendation dataset và empirical evaluation | v5 kiểm tra retail basket/rule/cold-item mechanisms khác domain | schema/task compatibility và license phải được xác minh trước adapter |
| [Amazon-M2](https://papers.nips.cc/paper_files/paper/2023/hash/193df57a2366d032fb18dcac0698d09a-Abstract-Datasets_and_Benchmarks.html) | multilingual shopping sessions, sáu locales | next-product, domain shift và title generation | v5 cung cấp Vietnamese catalog và explicit co-purchase falsification | Amazon-M2 có real shopping-session scale/language diversity mà v5 không có |
| [Tenrec](https://proceedings.neurips.cc/paper_files/paper/2022/hash/4ad4fc1528374422dd7a69dea9e72948-Abstract-Datasets_and_Benchmarks.html) | multi-scenario, không đặc thù tiếng Việt | multiple positive/negative feedback tasks | v5 có temporal novel-purchase contract và exact semantic cohorts | Tenrec có quy mô và observed multi-feedback lớn hơn nhiều |

Vì task gốc khác nhau, mỗi external dataset cần hai bảng: reproduction theo
official protocol và harmonized comparison chạy lại mọi model trên cùng adapter.
Nếu không thể xây harmonized task mà vẫn giữ mechanism thiết yếu, dataset đó chỉ
là sensitivity/ablation track và không xác nhận H4.

## 3. Research problem và câu hỏi nghiên cứu

### Problem statement

Trong retail recommendation thưa và nhiều item mới, collaborative signal có thể
ghi nhớ co-purchase nhưng khó xử lý item chưa có lịch sử; content/sequence models
có thể tổng quát hóa nhưng không nhất thiết giữ được explicit basket relations.
Nghiên cứu kiểm tra liệu một lightweight hybrid kết hợp hai loại signal có tạo
ra cải thiện **có ý nghĩa thống kê và tái lập được** hay không, thay vì giả định
kiến trúc hiện tại là đóng góp.

### Research questions

- **RQ1 — Ranking:** Trên cùng temporal novel-purchase full-catalog protocol,
  Hybrid có thắng strongest faithful baseline về HR@10, NDCG@10 và GAUC không?
- **RQ2 — Cold item:** Content-aware/transfer methods và Hybrid thay đổi ranking
  trên 250 cold items như thế nào so với collaborative-only models?
- **RQ3 — Mechanism:** Organic Apriori signal có giúp đúng cohort target-rule,
  hay chỉ đổi top-k/gradient mà không cải thiện relevance?
- **RQ4 — External validity:** Kết luận có lặp lại trên một Vietnamese public
  dataset và một established multilingual e-commerce dataset hay không?
- **RQ5 — Efficiency:** Sau khi accuracy gates pass, bundle đã verify có đạt
  latency/memory gates trên fixed runner không?

### Falsifiable hypotheses

- **H1:** Hybrid vượt strongest baseline trên cả ba metric với paired 95% CI
  lower bound `> 0`.
- **H2:** Hybrid không giảm chất lượng cold-item cohort so với independent Deep
  và đạt semantic target gate đã preregister.
- **H3:** Loại Wide branch làm giảm metric trên rule-aligned cohort; nếu không,
  Wide mechanism không được xem là đóng góp.
- **H4:** Hướng cải thiện giữ nguyên trên ít nhất một external dataset dưới
  harmonized protocol; nếu không, claim chỉ giới hạn ở controlled v5 benchmark.

Một hypothesis fail là kết quả khoa học hợp lệ. Nó không được “sửa” bằng cách
hạ gate sau khi nhìn TEST.

## 4. Landscape 2022–2026 và khoảng trống nghiên cứu

Tìm kiếm được thực hiện ngày 2026-08-12 trên ACL Anthology, PMLR, NeurIPS,
SIGIR/ACM program, arXiv và official GitHub repositories. Chỉ primary paper page,
proceedings hoặc repository của tác giả được dùng. ViHoRec được giữ riêng là
2026 preprint/concurrent work, không được trình bày như peer-reviewed prior art.

### 4.1 Mười lăm nguồn gần đây dùng cho framing

| Năm | Nguồn | Tín hiệu chính | Vai trò đối với dự án |
|---:|---|---|---|
| 2022 | [Krichene & Rendle, *On Sampled Metrics for Item Recommendation*](https://doi.org/10.1145/3535335) | sampled vs exact metrics | Cấm so sánh khi candidate protocol khác |
| 2022 | [UniSRec](https://doi.org/10.1145/3534678.3539381) / [code](https://github.com/RUCAIBox/UniSRec) | transferable text-aware sequential representation | Baseline content/transfer quan trọng cho cold item |
| 2022 | [SimGCL](https://doi.org/10.1145/3477495.3531937) / [code](https://github.com/Coder-Yu/QRec) | simple graph contrastive learning | Modern collaborative baseline |
| 2022 | [Tenrec](https://proceedings.neurips.cc/paper_files/paper/2022/hash/4ad4fc1528374422dd7a69dea9e72948-Abstract-Datasets_and_Benchmarks.html) / [code](https://github.com/yuangh-x/2022-NIPS-Tenrec) | large multi-behavior benchmark | Tham chiếu thiết kế multi-behavior và true negatives |
| 2023 | [LightGCL](https://openreview.net/forum?id=FKXVK9dyMM) / [code](https://github.com/HKUDS/LightGCL) | lightweight global graph contrast | Strong graph comparator, kiểm tra sparsity |
| 2023 | [Masked and Swapped Sequence Modeling for Next Novel Basket Recommendation](https://doi.org/10.1145/3604915.3608803) / [code](https://github.com/liming-7/Mask-Swap-NNBR) | grocery next-novel-basket Transformer | Trực tiếp tham chiếu task basket/novel-item của dự án |
| 2023 | [Amazon-M2](https://papers.nips.cc/paper_files/paper/2023/hash/193df57a2366d032fb18dcac0698d09a-Abstract-Datasets_and_Benchmarks.html) | multilingual shopping sessions | External e-commerce benchmark chính |
| 2024 | [ViEcomRec](https://doras.dcu.ie/29693/) / [data](https://github.com/linh222/face_cleanser_recommendation_dataset) | refereed CSoNet 2023 proceedings item, repository record published 2024; Vietnamese e-commerce interactions | Public Vietnamese comparison, domain hẹp |
| 2024 | [Vietnamese Food Recommendation Dataset](https://aclanthology.org/2024.paclic-1.4/) | Vietnamese food recommendation | Chứng minh đã có nghiên cứu/dataset tiếng Việt |
| 2024 | [Cold-start Recommendation by Personalized Embedding Region Elicitation](https://proceedings.mlr.press/v244/nguyen24a.html) | adaptive new-user elicitation | Phân biệt user cold-start với item cold-start |
| 2024 | [LLaRA](https://doi.org/10.1145/3626772.3657690) / [code](https://github.com/ljy0ustc/LLaRA) | conventional recommender + LLM knowledge | Literature/compute-tier comparator |
| 2024 | [A-LLMRec](https://doi.org/10.1145/3637528.3671931) / [code](https://github.com/ghdtjr/A-LLMRec) | LLM + collaborative filtering, warm/cold | Literature/compute-tier comparator |
| 2024 | [XSimGCL](https://doi.org/10.1109/TKDE.2023.3288135) / [code](https://github.com/Coder-Yu/SELFRec) | extremely simple graph contrastive learning | Primary source cho graph-CL baseline thay vì chỉ cite repository |
| 2025 | [AlphaRec: Language Representations Can Be What Recommenders Need](https://proceedings.iclr.cc/paper_files/paper/2025/hash/e4bab1843c8d5a69f5abfd0824593493-Abstract-Conference.html) / [code](https://github.com/LehengTHU/AlphaRec) | language-representation-based collaborative filtering | Recent text/zero-shot comparator sát với SBERT item signal |
| 2026 | [ViHoRec](https://arxiv.org/abs/2607.12946) / [data](https://github.com/MinhNguyenDS/ViHoRec) | Vietnamese hotel recommendation under short histories | Concurrent preprint; short-history-user cold-start sensitivity, không phải strict zero-history protocol |

Tính mới phải đến từ khoảng trống và evidence, không đến từ việc đếm năm xuất
bản. Các model nền tảng như BPR,
LightGCN, SASRec và BERT4Rec vẫn bắt buộc làm baseline dù cũ hơn 2022; chúng
không được dùng làm bằng chứng cho “latest method”.

[RecBole 2.0](https://doi.org/10.1145/3511808.3557680) là CIKM 2022 software
paper và vẫn hữu ích như tooling/adaptation reference. Nó không được tính trong
danh sách mười lăm nguồn framing vì scope của danh sách là method, dataset và
evaluation evidence trực tiếp cho các RQ, không phải benchmark-library tooling.

### 4.2 Kết luận về nghiên cứu tiếng Việt

Khẳng định “chưa có dataset tiếng Việt” là sai. Ít nhất ViEcomRec, Vietnamese
Food Recommendation Dataset và ViHoRec đã công bố resource/protocol liên quan.
Khoảng trống hợp lý hơn là:

- ít public retail benchmark tiếng Việt kết hợp catalog text, temporal
  multi-behavior, basket rules và controlled cold-item cohorts;
- các dataset hiện có khác domain/task và chưa tạo một chuẩn chung cho
  full-catalog temporal novel-purchase ranking;
- benchmark v5 có độ kiểm soát cao nhưng behavior tổng hợp, do đó lợi thế về
  cơ chế đi kèm bất lợi về ecological validity.

Đây là trade-off phải trình bày công khai, không phải ưu thế tuyệt đối.

### 4.3 Các dòng phương pháp hiện đại

Không có một “phương pháp hiện đại nhất” cho mọi setting. Các frontier liên quan
gồm:

- sequential/transfer representation: UniSRec và Transformer baselines;
- graph collaborative/contrastive: SimGCL, XSimGCL, LightGCL;
- content/language-model augmentation: LLaRA, A-LLMRec và AlphaRec;
- explicit relation and hybrid models: rule/content/collaborative fusion;
- cold-start elicitation: protocol riêng cho new user, không thay cho cold item.

Các 7B LLM methods không phải baseline bắt buộc trên laptop 6 GB nếu official
recipe cần GPU lớn. AlphaRec vẫn là baseline text/CF quan trọng vì trực tiếp kiểm
tra language representations mà không dựa vào generative prompting. Nếu các
7B methods không chạy được, paper phải giới hạn claim và không được tuyên bố
SOTA so với LLM recommenders.

## 5. Benchmark design bắt buộc

### Track A — Internal controlled benchmark

Chạy toàn bộ baseline và proposed model trên cùng immutable v5 snapshot:

1. Random, MostPop.
2. ItemKNN/ItemCF, Apriori.
3. BPR-MF, LightGCN.
4. SASRec, BERT4Rec.
5. BTBR/Mask-Swap-NNBR nếu basket sequence adapter giữ được official semantics.
6. UniSRec và AlphaRec.
7. Cả ba graph-CL references: SimGCL, XSimGCL và LightGCL.
8. Independent Deep two-tower và proposed Hybrid.

Author-official hoặc explicitly identified third-party reference implementation
được bọc bởi dataset/evaluator adapter; không copy con số từ paper. RecBole phải
luôn mang nhãn third-party benchmark implementation trong provenance.

### Track B — Public Vietnamese validation

Ưu tiên ViEcomRec vì gần e-commerce nhất. Trước khi chạy phải xác minh license,
schema và task. Nếu data không có sequence/purchase semantics đủ để hỗ trợ cùng
task, chạy một harmonized implicit top-k task và ghi rõ scope. Vietnamese Food
và ViHoRec được dùng như sensitivity tracks nếu schema/license phù hợp.

Một track làm mất input, objective hoặc mechanism thiết yếu của proposed method
chỉ là **reduced-method ablation**, không phải external replication của H4. H4
chỉ được đánh giá trên dataset hỗ trợ cùng task và đủ signal để giữ nguyên model
contract; nếu không có dataset như vậy, H4 giữ trạng thái `NOT_TESTED`.

### Track C — Established external e-commerce benchmark

Amazon-M2 là lựa chọn chính cho multilingual shopping-session/next-product.
Tenrec là lựa chọn phụ cho multi-behavior. Hai bảng cần được tách:

- reproduction theo official split/metric của dataset;
- harmonized top-k protocol chạy cả proposed model và cùng baseline suite.

Không so số Amazon-M2 với số v5 theo hàng ngang để kết luận hơn/kém.

## 6. Training contract và official-code adapters

### 6.1 Adapter interface tối thiểu

Mỗi model adapter phải khai báo:

```text
paper_reference
official_repository + immutable revision/tag
license
dataset_mapping_hash
split_hash
candidate_policy
objective_and_negative_sampling
hyperparameter_search_space
search_budget
seed
checkpoint_hash
per_user_metric_artifact_hash
text_encoder_id + immutable revision
tokenizer_hash
prompt_or_text_serialization_hash
embedding_artifact_sha256
embedding_generation_recipe
```

Các trường text/embedding là bắt buộc cho UniSRec, AlphaRec, LLaRA, A-LLMRec
và mọi adapter dùng pretrained text representations. Thay encoder chính thức
bằng SBERT là một ablation riêng, không được gọi là faithful reproduction.

RecBole được dùng cho BPR, LightGCN, SASRec và BERT4Rec; official repositories
được ưu tiên cho UniSRec/SimGCL/XSimGCL/LightGCL. Mọi thay đổi để hỗ trợ v5 phải
được ghi thành patch và test metric parity trên toy fixture.

### 6.2 Fair tuning

- cùng validation data và số trial tối đa cho các model cùng tier;
- search space được preregister, không mở rộng sau khi thấy TEST;
- method-faithful loss/negative sampling;
- cùng seeds `42`, `2027`, `31415` cho final comparison;
- test chỉ mở sau khi model/config được khóa bằng validation;
- lưu training time, peak RAM/VRAM và inference latency cùng accuracy.

### 6.3 Metric contract

Primary: HR@10, NDCG@10 và GAUC đúng evaluator v5. Reporting thêm Recall@10
để tương thích nhiều public benchmark, nhưng Recall chưa được dùng làm release
gate cho tới khi code/evidence schema được review. Mọi metric phải có per-user
arrays và paired 95% bootstrap CI.

Project promotion floors trong `standard.md` là `.75/.15/.08`; đây là
**acceptance thresholds**, không phải kết quả mong đợi và không phải giá trị lấy
từ literature.

“Strongest baseline” cho từng metric được chọn bằng validation mean trong danh
sách baseline preregistered, rồi khóa trước khi mở TEST. Final inference dùng
paired interval trên TEST đối với baseline đã khóa. Nếu lựa chọn vẫn được thực
hiện trên cùng sample dùng để inference, phải dùng simultaneous/max-statistic
interval thay cho nominal CI của một comparison được chọn hậu nghiệm.

## 7. Điều kiện dừng và quyết định về `ai-service`

### Chặn proposed/Hybrid GPU training nếu

- chưa có verified v5 lineage hoặc dataset language/provenance receipt;
- không tái hiện được official baseline trên một public dataset;
- adapter thay đổi split/candidate/metric mà không có parity test;
- chưa chạy đủ BPR, LightGCN, SASRec, BERT4Rec, BTBR, UniSRec, AlphaRec,
  SimGCL, XSimGCL và LightGCL trên v5;
- bất kỳ dữ liệu/result table nào chỉ tồn tại trong Markdown mà không có artifact.

Các GPU job cô lập để tái hiện **reference baseline** được phép chạy trước gate
này trong namespace riêng. Chúng chỉ tạo reproduction/parity evidence, không
được dùng để tuyên bố kết quả hay superiority của proposed model.

### Dừng campaign sau seed 42 nếu

- non-finite, GAUC `< .50`, corruption hoặc integrity failure;
- Hybrid không đạt `.75/.15/.08`;
- Hybrid không thắng strongest baseline cho từng metric bằng paired CI;
- semantic/cold/Wide readiness gate fail.

### Hủy hoặc thay thế current training implementation nếu

Sau một vòng adapter/parity có kiểm soát, current `ai-service` không thể dùng
cùng immutable datasets, split và evaluator với reference baselines, hoặc
không thể tái hiện kết quả official-code trên public benchmark trong tolerance
đã preregister. Khi đó không “tinh chỉnh tới khi pass”; đóng pipeline hiện tại,
giữ diagnostic evidence và xây training backend từ framework tham chiếu.

## 8. Blueprint cho Introduction

1. **Bối cảnh:** retail recommendation phải cân bằng behavior, content, cold
   items và serving cost.
2. **Methodological problem:** cross-paper numbers thường không so sánh được do
   split/candidate/metric khác; cite Krichene & Rendle và RecBole.
3. **Low-resource context:** đã có Vietnamese recommendation resources nhưng
   domain/protocol phân mảnh; cite ViEcomRec, PACLIC Food và ViHoRec (preprint).
4. **Dataset statement:** mô tả v5 là controlled Vietnamese-language catalog
   benchmark với generated behavior; nêu cả ưu thế lẫn external-validity limit.
5. **Research gap:** chưa biết explicit organic co-purchase signal có bổ sung
   content/sequence models dưới shared full-catalog temporal protocol hay không.
6. **Contributions:** chỉ viết ở dạng conditional cho tới khi artifacts pass:
   benchmark protocol, faithful baseline suite, mechanism analysis, lightweight
   deployment. Không dùng “SOTA”, “eliminate cold-start” hoặc “real-world
   superiority” trước external validation.

## 9. Blueprint cho Related Work

Related Work phải được tổ chức theo vấn đề, không liệt kê paper:

1. reproducible top-k evaluation and sampled-metric limitations;
2. sequential and transferable representation (SASRec/BERT4Rec/UniSRec);
3. graph collaborative and contrastive recommendation
   (LightGCN/SimGCL/XSimGCL/LightGCL);
4. content/language-model augmentation (UniSRec/LLaRA/A-LLMRec/AlphaRec) và
   compute trade-offs;
5. next-novel-basket, explicit co-purchase và hybrid signals;
6. cold-item versus cold-user protocols;
7. Vietnamese resources và khoảng trống retail temporal multi-behavior.

Mỗi subsection phải kết thúc bằng một câu “what remains unresolved”, nối trực
tiếp tới RQ/Hypothesis. Không lấy metric trong paper khác làm expected result.

## 10. Research provenance và limitations

- Retrieval date: `2026-08-12`.
- Search strings chính: `Vietnamese recommender system dataset`, `Vietnamese
  e-commerce recommendation dataset`, `next novel basket recommendation`,
  `cold-start recommendation 2024`, `graph contrastive recommendation`,
  `language representations recommender 2025`, và `multilingual shopping
  session recommendation dataset`.
- Source scopes: ACL Anthology, ACM/RecSys, PMLR, NeurIPS, OpenReview/ICLR,
  arXiv cho preprint và repositories chính thức của tác giả.
- Inclusion: 2022–2026 primary proceedings/paper pages, official repositories,
  cộng với foundational baselines cần cho benchmark.
- Exclusion: blog, leaderboard không có protocol, repository không xác định tác
  giả, metric không có split/candidate definition.
- ViHoRec: concurrent 2026 preprint; cần kiểm tra peer-review status tại thời
  điểm submission.
- Chưa có systematic review exhaustive; bibliography phải được cập nhật khi đã
  chọn conference và cutoff date thật.
- Việc dùng AI để hỗ trợ tìm kiếm/soạn thảo phải tuân thủ policy của venue và
  được human-verify từng citation.
