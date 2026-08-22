# Master plan ARS-Codex — Paper Methods/Empirical về Hybrid Recommender

## 1. Mục tiêu và các quyết định đã khóa

Paper được định hướng là **methods/empirical paper**: đóng góp chính nằm ở phương pháp Hybrid và benchmark có thể tái lập, không định vị là dataset paper khi benchmark v5 còn controlled/semi-synthetic.

Điểm vào phù hợp của ARS không phải Draft/Review mà là:

```text
Stage 0 Intake
→ Stage 1 Targeted Research Backfill
→ Experiment Agent: Plan → Run → Validate
→ Stage 2 Academic Paper
→ Stage 2.5 Integrity Review
→ Stage 3 Independent Review
→ Stage 4 Revision
→ Stage 3'/4' Re-review loop
→ Stage 4.5 Final Integrity
→ Stage 5 Finalize
→ Stage 6 Process Summary
```

Các phase quan trọng nhất:

1. **Experiment bridge và benchmark harmonization**: quyết định paper có giá trị khoa học hay không.
2. **Stage 1 — Literature/source verification**: quyết định Introduction và Related Work có đáng tin hay không.
3. **Stage 2.5 và 4.5 — Integrity gates**: chặn citation ảo, claim quá mức và số liệu không truy xuất được.
4. **Stage 2 — Introduction/Related Work**: được ưu tiên cao về chất lượng viết, nhưng chỉ bắt đầu sau khi evidence map đủ chắc.
5. Stage 5–6 chủ yếu là định dạng và tổng kết; workload nhẹ hơn nhưng runtime override hiện tại vẫn yêu cầu Sol High.

Các trạng thái trong [idea.md](/E:/UIT/cv/backend/inputs/idea.md), [experimental_log.md](/E:/UIT/cv/backend/inputs/experimental_log.md) được giữ nguyên: `RESULT_STATUS=NOT_RUN`, chưa được phép tuyên bố Hybrid tốt hơn baseline và không tái sử dụng số liệu cũ.

## 2. Tổ chức artifact và provenance

Master plan chính sẽ được lưu tại:

`E:\UIT\cv\backend\master\academic-research-master-plan.md`

Toàn bộ artifact mới, có kiểm soát phiên bản:

`E:\UIT\cv\backend\research\hybrid-recsys-v5\`

Dữ liệu lớn, checkpoint và kết quả chạy không đưa vào Git:

`E:\UIT\cv\backend\ai-service\artifacts\research-v5\`

Cấu trúc chuẩn:

| Thư mục | Nội dung bắt buộc |
|---|---|
| `00_control/` | `pipeline_state.json`, venue matrix, decision log, Material Passports, checksum input |
| `01_research/` | RQ Brief, Methodology Blueprint, novelty-boundary report |
| `02_literature/` | search log, source registry, screening matrix, `refs.bib`, synthesis, claim–citation matrix |
| `03_benchmark/` | dataset manifest, adapter registry, repo revisions, official-reproduction reports |
| `04_experiments/` | run registry, configs, per-user metrics, statistical reports, negative results |
| `05_manuscript/` | paper configuration, outline, argument map, master draft, tables/figures |
| `06_integrity/` | Stage 2.5 và Stage 4.5 reports, claim verification ledger |
| `07_review/` | năm independent reviews, editorial synthesis, revision matrix |
| `08_submission/` | venue-specific LaTeX, BibTeX, figures, PDF, disclosure |
| `09_process/` | process summary, limitations, reproducibility checklist |

Mỗi handoff phải có Material Passport gồm ít nhất:

- `origin_skill`, `origin_mode`, `origin_date`;
- `verification_status`, `version_label`;
- input/output checksum;
- model, reasoning effort và orchestration thực tế;
- repo commit, dataset hash, seed và run ID nếu liên quan experiment.

Các thư mục `workspace/`, `paper/` hiện tại và [full_detail_report.md](/E:/UIT/cv/backend/detail-report/full_detail_report.md) được coi là **historical/quarantined**. Có thể khai thác ý tưởng hoặc thuật ngữ, nhưng mọi claim và con số phải được kiểm chứng lại từ đầu.

## 3. Chiến lược references, Introduction và Related Work

### Quy mô bibliography

Mức khuyến nghị cho bản conference methods/empirical:

- Corpus tìm kiếm ban đầu: **45–55 nguồn đã xác minh**.
- Bibliography cuối: **32–38 references**, tâm điểm khoảng **35**.
- Nguồn 2022–2026: **12–14 references thực sự được dùng**, khoảng 35–45% bibliography.
- Nguồn nền tảng trước 2022: khoảng **9–11**.
- Nguồn evaluation, dataset, reproducibility, ethics và deployment: khoảng **8–12**.

Không giữ đủ 15 nguồn mới chỉ để đạt quota. Mỗi nguồn được chấm:

- liên hệ trực tiếp với RQ/claim: 0–3;
- tương thích task/protocol: 0–2;
- chất lượng và tính primary: 0–2;
- code/data/reproducibility: 0–2;
- tính mới hoặc không trùng lặp: 0–1.

Ngưỡng:

- `≥8`: core reference;
- `6–7`: supporting/conditional;
- `≤5`: loại khỏi manuscript, có thể giữ trong search log.

Từ 15 nguồn hiện có, nhóm core candidate ban đầu gồm:

- Krichene & Rendle;
- UniSRec;
- SimGCL;
- LightGCL;
- Mask-Swap/BTBR;
- Amazon-M2;
- ViEcomRec;
- Vietnamese Food Dataset;
- XSimGCL;
- AlphaRec.

Nhóm conditional gồm Tenrec, cold-start user elicitation, LLaRA, A-LLMRec và ViHoRec. Chỉ giữ khi chúng hỗ trợ một claim cụ thể:

- LLaRA/A-LLMRec chỉ giữ nếu paper thực sự thảo luận LLM recommender;
- cold-user elicitation chỉ dùng để phân biệt cold-user với cold-item;
- Tenrec chỉ giữ nếu dùng cho external track hoặc lập luận multi-behavior;
- ViHoRec phải được đánh dấu concurrent preprint và kiểm tra policy/cutoff của venue.

Nếu sau screening chỉ 10–11 nguồn hiện tại đạt chuẩn, bổ sung nguồn mới đúng khoảng trống thay vì giữ nguồn lệch scope.

### Introduction

Introduction gồm sáu khối lập luận, chiếm khoảng 12–15% phần thân:

1. Bài toán recommendation trong retail và các yêu cầu sparse, temporal, basket, cold item.
2. Vấn đề comparability: sampled/full-catalog, split và candidate protocol khác nhau có thể làm metric không so sánh được.
3. Landscape phương pháp: collaborative, Wide & Deep, Two-Tower, sequence, graph và association-rule.
4. Bối cảnh Việt Nam: ViEcomRec, Vietnamese Food và các tài nguyên gần domain, tránh claim “chưa có dataset Việt Nam”.
5. Research gap được phát biểu theo phạm vi tìm kiếm, không tuyên bố novelty toàn cầu.
6. RQ và tối đa ba contribution, viết có điều kiện theo kết quả thực nghiệm.

Mục tiêu:

- 8–12 nguồn khác nhau;
- 10–15 citation anchors;
- mỗi claim quan trọng có ID `C-INTRO-*` và liên kết tới nguồn hoặc experiment;
- không chèn kết quả số trước khi run được `SEALED`.

### Related Work

Related Work chiếm khoảng 15–18% phần thân. Các chủ đề Two-Tower, Wide & Deep, Deep Learning, Recommendation và Apriori là nội dung lập luận, không bắt buộc trở thành tiêu đề riêng.

Cấu trúc đề xuất:

1. **Evaluation and reproducibility**: exact/full-catalog metrics, temporal split, shared evaluation.
2. **Collaborative and deep recommendation**: ItemCF, BPR, NCF/DeepFM, Wide & Deep, Two-Tower.
3. **Sequential and basket recommendation**: Apriori, SASRec, BERT4Rec, Mask-Swap/BTBR.
4. **Graph contrastive recommendation**: LightGCN, SimGCL, XSimGCL, LightGCL.
5. **Content, transfer and cold-item recommendation**: SBERT, UniSRec, AlphaRec; LLM methods chỉ khi cần.
6. **Vietnamese and external e-commerce resources**: ViEcomRec, Vietnamese Food, ViHoRec, Amazon-M2/Tenrec.

Mục tiêu:

- 18–24 nguồn khác nhau;
- 25–35 citation anchors;
- mỗi subsection kết thúc bằng “positioning sentence” chỉ rõ Hybrid khác gì và chưa giải quyết được gì;
- không viết dạng liệt kê từng paper; phải tổng hợp theo assumption, input signal, objective và evaluation protocol.

## 4. Runbook theo phase ARS

Runtime override `2026-08-21`: từ R5 của Stage 1B trở đi, mọi stage/task chưa bắt đầu dùng `gpt-5.6-sol`, reasoning `high`. Cột model bên dưới giữ lại provenance/đề xuất gốc cho các phase đã hoàn thành; override này có quyền ưu tiên cho toàn bộ công việc tương lai. Independent review/audit vẫn chạy trong fresh context riêng.

| Phase | Hoạt động và đầu ra | Gate bắt buộc | Model đề xuất |
|---|---|---|---|
| **0 — Intake/Governance** | Khóa checksum ba input; khai báo `experiments_declared`; xác nhận methods/empirical; lập venue matrix từ CFP chính thức; tạo pipeline state và Material Passport | Không kế thừa số liệu lịch sử; paper config được xác nhận; venue có thể còn TBD nhưng phải chọn trước submission-format draft | Terra Max; Sol XHigh kiểm tra quyết định |
| **1A — RQ/Methodology Backfill** | Chuẩn hóa RQ1–RQ5, hypotheses, estimands, contribution boundaries và failure conditions | Mỗi RQ ánh xạ được sang dataset, metric, baseline và bảng kết quả dự kiến | Sol XHigh |
| **1B — Targeted Literature Review** | Dùng ARS deep-research/lit-review theo năm lane: evaluation, architectures, basket/hybrid, cold/content, Vietnamese/external; chạy remediation theo [kế hoạch hoàn tất 1B](../research/hybrid-recsys-v5/01_research/stage1b_completion_plan.md) | 100% nguồn có source-of-record identity, DOI khi áp dụng và venue/document type; corpus 45–55; operational resources tách riêng; claim–source map và original-source locators hoàn chỉnh; không ghost citation; independent audit cho phép seal | L1–R4 giữ provenance thực tế; R5–R9: Sol High |
| **1E-Plan — Experiment Agent** | Khóa dataset manifest, adapter contract, baseline registry, tuning budget, seed và statistics plan | Test set vẫn sealed; protocol được version hóa; mọi baseline có implementation provenance | Sol High |
| **1E-Adapt/Reproduce** | Cô lập môi trường từng repo; smoke test; tái lập kết quả official dataset trước khi đưa v5 vào | Official reproduction đạt tolerance hoặc baseline bị loại cùng failure report | Sol High |
| **1E-Harmonized Run** | Train/tune tất cả baseline trên cùng v5; đánh giá qua shared evaluator; sau đó chạy hai external tracks | Ba seed; per-user metrics; hierarchical bootstrap; run receipts `SEALED`; test chỉ mở sau registry lock | Sol High |
| **2 — Academic Paper** | Chạy paper configuration, `ars-outline`, argument map; viết Introduction/Related Work trước, sau đó Methods, Experiments, Results, Limitations; Abstract viết cuối | Mọi số liệu được import từ artifact; outline được xác nhận; không hand-type benchmark numbers | Sol High |
| **2.5 — Integrity Review** | 100% bibliography/existence; kiểm tra citation context, statistics, originality và high-impact claims | Không còn reference ảo, số liệu không truy xuất được hoặc novelty claim tuyệt đối | Sol High, fresh context |
| **3 — Independent Review** | Năm review độc lập: venue-fit, methodology, domain, skeptical perspective và devil’s advocate; sau đó editorial synthesis | Reviewer không sửa manuscript; mỗi issue có severity và evidence | Sol High, các context độc lập |
| **4 — Revision** | Lập claim-level revision matrix; sửa paper; cập nhật response log và Material Passport | Mỗi major issue có trạng thái resolved/deferred/rejected kèm lý do | Sol High |
| **3′/4′ — Re-review Loop** | Chỉ review phần thay đổi và các major issue còn lại; tối đa hai vòng trước escalation | Không còn unresolved fatal/major issue | Sol High, fresh review context |
| **4.5 — Final Integrity** | Kiểm tra 100% references, citation context, statistics và critical claims; 100% changed text, ≥50% originality sample | Zero major distortion; zero unverifiable result; claim–experiment alignment hoàn chỉnh | Sol High, fresh context |
| **5 — Finalize** | Chọn template chính thức, format convert, disclosure, anonymization, camera-ready checks, compile PDF | PDF sạch lỗi; không missing citation; page limit và AI policy hợp lệ | Sol High |
| **6 — Process Summary** | Tổng hợp quyết định, negative results, limitations, reproducibility package và artifact index | Người khác có thể lần từ paper → claim → run → config → dataset hash | Sol High |

## 5. Benchmark và training pipeline

### Ba lớp evidence phải tách riêng

1. **Official reproduction**

   Chạy official repository trên dataset/protocol của tác giả. Chỉ dùng để chứng minh adapter và môi trường đúng; không dùng để kết luận Hybrid tốt hơn.

2. **Harmonized v5 benchmark**

   Tất cả baseline và Hybrid dùng cùng:

   - temporal split;
   - full catalog;
   - seen-item masking;
   - candidate policy;
   - metrics;
   - validation objective;
   - tuning budget;
   - seed;
   - shared evaluator.

3. **External validation**

   Chạy riêng từng dataset. Không đặt raw metric của Amazon-M2, ViEcomRec và v5 trên cùng một hàng để suy luận hơn/kém.

### Adapter contract

Không cài các dependency legacy vào `.venv` chính của `ai-service`. Mỗi repo dùng environment/container riêng và pin commit.

Thứ tự implementation ưu tiên:

1. official author repository;
2. official framework implementation như [RecBole](https://github.com/RUCAIBox/RecBole);
3. implementation độc lập chỉ khi đã tái lập được reference result.

Các repo ban đầu:

- [UniSRec](https://github.com/RUCAIBox/UniSRec);
- [QRec/SimGCL](https://github.com/Coder-Yu/QRec);
- [SELFRec/XSimGCL](https://github.com/Coder-Yu/SELFRec);
- [LightGCL](https://github.com/HKUDS/LightGCL);
- [Mask-Swap-NNBR](https://github.com/liming-7/Mask-Swap-NNBR);
- [AlphaRec](https://github.com/LehengTHU/AlphaRec).

QRec phụ thuộc TensorFlow 1.14, trong khi các repo khác dùng các thế hệ PyTorch/CUDA khác nhau; vì vậy environment isolation là gate bắt buộc, không phải tối ưu tùy chọn.

Hợp đồng tối thiểu:

```text
DatasetManifest
  schema_version, dataset_hash, users, items, interactions,
  timestamp/order/session fields, item text, split hashes,
  candidate policy, cold cohorts

BaselineAdapter
  prepare(manifest)
  fit(train, validation, seed, budget)
  score(user_batch, candidate_items)
  export_run_receipt()

RunReceipt
  repo_url, commit_sha, environment_hash, config_hash,
  seed, hardware, duration, checkpoint_hash, status

ResultBundle
  report.json
  per-user-metrics.npz
  prediction/checksum receipt
  statistical-comparison.json
```

Tận dụng seam [evaluate_external_scores](/E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/full_catalog.py:747) để mọi model được xếp hạng qua cùng evaluator. Scorer phải chạy theo user batch để không giữ toàn bộ score matrix trên GPU.

### Baseline promotion

- Gate 0: Random, MostPop, ItemCF, Apriori.
- Gate 1: BPR-MF, LightGCN, SASRec, BERT4Rec qua framework thống nhất.
- Gate 2: BTBR, UniSRec, AlphaRec, SimGCL, XSimGCL, LightGCL.
- Gate 3: Deep và Hybrid hiện tại.

Baseline được gọi là “strongest” dựa trên validation NDCG@10 theo registry đã khóa, không chọn sau khi xem test.

Quy trình mỗi model:

1. Smoke test: seed 42, subset nhỏ, tối đa hai epoch.
2. Official reproduction: official config và official dataset.
3. Reference tolerance: pass nếu chênh lệch không vượt `max(0.005 absolute, 5% relative)` hoặc nằm trong CI do tác giả công bố.
4. Harmonized tuning: tối đa 12 completed trials, model-faithful search space, seed 42, early stopping trên validation.
5. Khóa config và checkpoint hash.
6. Final run trên ba seed `42`, `2027`, `31415`.
7. Chỉ sau khi toàn bộ registry được khóa mới mở test.

Máy hiện tại có RTX 3060 Laptop 6 GB:

- chạy tuần tự một model;
- dùng mixed precision hoặc gradient accumulation chỉ khi không làm sai phương pháp;
- nếu OOM hoặc một seed vượt ngưỡng vận hành đã định, chuyển sang GPU ngoài tối thiểu 24 GB sau khi được phê duyệt;
- không giảm kiến trúc một cách âm thầm để vừa GPU.

### Metrics và statistics

Primary:

- NDCG@10;
- HR@10;
- Recall@10;
- macro per-user GAUC.

Secondary:

- cold-item metrics;
- coverage;
- inference latency, throughput và memory;
- mechanism-specific Apriori/rule coverage.

Statistics:

- lưu per-user metric cho từng seed;
- hierarchical paired bootstrap 2.000 lần;
- 95% confidence interval và effect size;
- Holm correction khi so sánh nhiều baseline;
- mọi negative/null result được giữ, không loại khỏi log.

Các ngưỡng `.75/.15/.08` trong input vẫn là `TARGET`, không được đổi thành `RESULT`.

### External validation hai track

**Track A — Full-mechanism external validity**

Ưu tiên Amazon-M2 vì đây là dataset shopping-session đa ngôn ngữ với next-product task và item attributes [theo mô tả chính thức của NeurIPS 2023](https://papers.nips.cc/paper_files/paper/2023/hash/193df57a2366d032fb18dcac0698d09a-Abstract-Datasets_and_Benchmarks.html).

Chỉ chạy full Hybrid nếu audit xác nhận:

- có session/order grouping phù hợp cho co-occurrence;
- item text/metadata đủ cho Deep/Two-Tower;
- tạo được temporal split và full-catalog candidates;
- license/access cho phép;
- không phải định nghĩa lại task để ưu ái Hybrid.

Nếu Amazon-M2 không đạt, lần lượt đánh giá Instacart, Ta-Feng và Dunnhumby. Nếu không dataset nào đủ tín hiệu, H4 được ghi `NOT_TESTED`, không dựng một thí nghiệm reduced rồi gọi là full Hybrid.

**Track B — Vietnamese domain sensitivity**

ViEcomRec là ưu tiên đầu. Nguồn chính thức mô tả 369.099 interactions và public content/attribute baselines, nhưng số user lớn so với số interaction nên phải audit khả năng temporal/sequential evaluation trước [DORAS](https://doras.dcu.ie/29693/), [repository](https://github.com/linh222/face_cleanser_recommendation_dataset).

Nếu không đủ history:

- chỉ chạy content/cold-item/domain-sensitivity task;
- ghi rõ đây không phải bằng chứng cho full Hybrid;
- Vietnamese Food hoặc ViHoRec chỉ thay thế nếu cùng task và license đạt compatibility gate.

## 6. Chính sách model Codex, kiểm thử và tiêu chí hoàn tất

Runtime policy đang hoạt động:

- Mọi stage/task chưa bắt đầu kể từ R5 dùng `gpt-5.6-sol`, reasoning `high`, kể cả extraction, synthesis, benchmark, drafting, review, audit, formatting và handoff.
- Review/audit độc lập vẫn phải dùng fresh context, chỉ đọc frozen packet và không được tự sửa artifact đang audit.
- Provenance của phase đã chạy phải giữ model/reasoning thực tế; không hồi tố đổi L1–L5, R3 hoặc R4 thành Sol High.
- Chỉ thay đổi chính sách này khi người dùng đưa ra quyết định mới; runtime thực tế phải được ghi trong dispatch manifest và handoff của từng stage.

Nếu runtime không hỗ trợ đổi model theo subagent, mỗi phase phải chạy trong task riêng với model được chọn thủ công. Nếu toàn bộ workflow chạy inline trong một task, tất cả role được ghi là session model hiện tại; không được tuyên bố đã dùng model khác.

### Test và acceptance scenarios

- Thay đổi một input checksum phải làm Material Passport cũ mất hiệu lực.
- Citation key không có source-of-record identity phải làm integrity gate fail; thiếu DOI chỉ được chấp nhận khi source type thực sự không có DOI và có authoritative source pointer cùng lý do được ghi rõ.
- Một claim số không trỏ tới `report.json`/run ID phải bị xóa hoặc đánh `UNVERIFIED`.
- Adapter trả sai shape, NaN hoặc candidate order phải bị shared evaluator từ chối.
- Split leakage, cold-item leakage hoặc train-seen item lọt vào candidates phải fail benchmark.
- Raw metric từ official repo không được xuất hiện trong harmonized comparison table.
- Kết quả hai dataset khác nhau phải nằm trong bảng riêng.
- Chưa khóa registry thì test loader phải từ chối truy cập.
- Baseline không tái lập được phải có failure report, không được âm thầm thay implementation.
- Mỗi bảng manuscript phải được sinh từ artifact đã sealed.
- Stage 4.5 chỉ pass khi 100% references, statistics và critical claims kiểm chứng được, zero major issue.
- Submission hoàn tất khi PDF compile sạch, bibliography không thiếu, disclosure đúng venue và artifact index truy ngược được từ paper tới dataset/config/checkpoint.

### Giả định mặc định

- Manuscript viết bằng tiếng Anh; master plan, logs và decision records có thể viết tiếng Việt.
- Venue chưa được chọn; master manuscript dùng format trung lập và chỉ chuyển template sau khi venue matrix được phê duyệt.
- External validation dùng hai track như đã chọn.
- Model budget là “Ultra chọn lọc”.
- Không có kết quả thắng mặc định: Hybrid thua, hòa hoặc chỉ thắng ở một cohort đều là kết quả hợp lệ.
