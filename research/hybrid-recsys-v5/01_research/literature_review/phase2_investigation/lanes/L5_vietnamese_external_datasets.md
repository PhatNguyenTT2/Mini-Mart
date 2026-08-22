---
lane: L5
task_id: 019ffb38-af64-7372-8040-2b56ccf497ab
model: 5.6 Sol / XHigh
status: complete
captured_at: 2026-08-13
provenance: verbatim task final handoff
---

# L5 raw literature-search handoff

Kết quả lane L5: đã sàng lọc 19 ứng viên, giữ 12 nguồn. Không có dataset nào hiện đủ điều kiện “green” vô điều kiện cho H4. `Complete Journey` là ứng viên strict-H4 tốt nhất về mặt cấu trúc nhưng còn vướng revision/license; `Coveo` là ứng viên điều kiện; `Amazon-M2` phù hợp chuyển giao kiến trúc nhưng không giữ outcome purchase nên không thể tự động tính là H4 replication.

## SEARCH_LOG

- **Ngày chốt tìm kiếm:** 2026-08-13.
- **Đầu vào đã đọc:** toàn bộ bảy artifact được chỉ định cùng workflow lit-review, source verification và evidence assessment của ARS-Codex.
- **Không chỉnh sửa:** không có file nào trong worktree bị thay đổi.
- **Không gian tìm kiếm:** Springer/DORAS, ACL Anthology, NeurIPS Proceedings, arXiv, SIGIR eCom, Kaggle official dataset/competition pages, official project repositories và các dataset portals do tác giả/tổ chức phát hành.
- **Query clusters:**
  - Vietnamese e-commerce/food/hotel recommendation dataset.
  - Public commerce session, basket, order, temporal split, item text.
  - Amazon-M2, Tenrec, Coveo, OTTO, RelBench, Amazon Reviews, H&M, Complete Journey, Taobao.
  - Dataset license, redistribution, challenge protocol, DOI, repository provenance.
- **Sàng lọc:** 19 candidate families; 12 accepted, 7 excluded.
- **Nguyên tắc đánh giá:**
  - `VI`: primary computational/dataset study.
  - `VII`: official operational dataset/documentation.
  - `A`: peer-reviewed/official, identity và protocol mạnh, terms rõ.
  - `B`: nguồn mạnh nhưng còn một khoảng trống material về version/license/protocol.
  - `C`: preprint hoặc provenance/quyền sử dụng còn đáng kể.
- **Nhãn tương thích:**
  - `FULL-ARCH`: có thể cấp dữ liệu cho cả Wide/session-cooccurrence và Deep/content branch.
  - `H4-CONDITIONAL`: có thể hỗ trợ H4 sau khi đóng target, split, candidate set, revision và license.
  - `REDUCED`: chỉ dùng cho reduced-method ablation/sensitivity.
  - `NOT-H4`: không giữ essential task/outcome contract.
- Các metric dưới đây chỉ mô tả **ngữ nghĩa protocol từng nguồn**; không dùng để so raw scores giữa dataset hoặc protocol.

## ACCEPTED_SOURCES

### L5-VN-01 — ViEcomRec

- **Full identity:** Quang-Linh Tran, Binh T. Nguyen, Gareth J. F. Jones, Cathal Gurrin, “ViEcomRec: A Dataset for Recommendation in Vietnamese E-Commerce.”
- **Năm/venue:** CSoNet 2023 paper; xuất bản trong Springer LNCS 14479 năm 2024, pp. 74–82.
- **DOI/official:** [DOI 10.1007/978-981-97-0669-3_7](https://doi.org/10.1007/978-981-97-0669-3_7); [DORAS publication record](https://doras.dcu.ie/29693/); [CSoNet accepted papers](https://csonet-conf.github.io/csonet23/index.php/accepted-papers/index.html).
- **Repository:** [face_cleanser_recommendation_dataset](https://github.com/linh222/face_cleanser_recommendation_dataset); repository declares [CC BY-NC-SA 4.0](https://raw.githubusercontent.com/linh222/face_cleanser_recommendation_dataset/main/LICENSE).
- **Evidence tier:** VI-B.
- **Claims supported:** có Vietnamese e-commerce interaction dataset công khai với item text/attributes; Vietnamese public resources vẫn hẹp về domain và thiếu basket/session.
- **Dataset/protocol:** 2,244 facial-cleanser items, 369,099 reviews/interactions, 304,708 users, thu thập từ Shopee. Leave-one-out theo thứ tự tương tác; hai tương tác cuối dùng cho validation/test.
- **Metric semantics:** NDCG@10 cho next-item ranking trong protocol riêng của paper.
- **Official vs harmonized:** official reproduction có thể tái hiện next-item LOO; harmonized-v5 chỉ là content/cold-history sensitivity. Không có order/basket/session để tạo full Wide mechanism.
- **Limitations:** user cực thưa; chỉ một phần nhỏ user đủ lịch sử cho validation/test; review không chứng minh purchase/order. Quyền đối với nội dung Shopee và tính tương thích với ToS chưa được giải quyết chỉ bằng license của repository.
- **RQ/H mapping:** RQ4 context và dataset-contribution boundary; `REDUCED`, `NOT-H4`.
- **Foundational/recent:** recent.
- **Include rationale:** nguồn Vietnamese e-commerce trực tiếp và đã peer review; cần thiết để định vị đóng góp nhưng không được trình bày như external full-Hybrid replication.

### L5-VN-02 — Vietnamese Food Recommendation Dataset

- **Full identity:** An Tran, Thanh Dang, Hong Dang, Tin Huynh, “A New Dataset and Empirical Evaluation for Vietnamese Food Recommendation System.”
- **Năm/venue:** PACLIC 2024, Proceedings of the 38th Pacific Asia Conference on Language, Information and Computation, pp. 35–45.
- **DOI/official:** không có DOI trong official record; [ACL Anthology record](https://aclanthology.org/2024.paclic-1.4/).
- **Repository:** [official author-linked repository](https://github.com/QuocAn55/A-New-Dataset-and-Empirical-Evaluation-for-Vietnamese-Food-Recommendation-System).
- **Evidence tier:** VI-B-.
- **Claims supported:** tồn tại Vietnamese food item-feature dataset; không nên đồng nhất item metadata/rating benchmark với retail purchase recommendation.
- **Dataset/protocol:** 5,509 dishes, 16 attributes, thu thập từ monngonmoingay.com và cooky.vn. Paper mô tả việc lấp khoảng 40% phần tử rating còn thiếu bằng median vì giới hạn tính toán.
- **Metric semantics:** rating/similarity recommendation setup, không phải novel top-k purchase prediction.
- **Official vs harmonized:** có thể tái hiện setup của paper riêng biệt; harmonized-v5 thiếu timestamp, user-order, basket/session và outcome purchase.
- **Limitations:** việc median-fill thay đổi ý nghĩa missingness; không có temporal split hoặc commerce transaction semantics. Repository không có dataset `LICENSE` rõ.
- **RQ/H mapping:** dataset-contribution boundary; `REDUCED`, `NOT-H4`.
- **Foundational/recent:** recent.
- **Include rationale:** nguồn peer-reviewed quan trọng để tránh tuyên bố quá rộng về “Vietnamese recommendation datasets,” nhưng không phải external commerce replication candidate.

### L5-VN-03 — ViHoRec

- **Full identity:** Minh Hoang Nguyen, “ViHoRec: A Quality-Controlled Vietnamese Hotel Recommendation Dataset and Cold-Start Benchmark.”
- **Năm/venue:** 2026; arXiv preprint, submitted 14 July 2026. Chưa xác minh peer-reviewed venue.
- **DOI/official:** [arXiv:2607.12946](https://arxiv.org/abs/2607.12946); DOI DataCite của preprint: [10.48550/arXiv.2607.12946](https://doi.org/10.48550/arXiv.2607.12946).
- **Repository:** [ViHoRec](https://github.com/MinhNguyenDS/ViHoRec).
- **Evidence tier:** VI-C+.
- **Claims supported:** Vietnamese hospitality dataset có temporal LOO và cold-start benchmark; review/rating data vẫn không tương đương retail baskets.
- **Dataset/protocol:** 18,267 interactions, 6,832 users, 560 hotels; public benchmark dùng temporal leave-last-one-out. Dữ liệu đến từ Booking, Traveloka và Ivivu.
- **Metric semantics:** top-k held-out hotel retrieval, gồm Recall@10; không phải purchase-basket ranking.
- **Official vs harmonized:** official cold-start reproduction khả thi; harmonized-v5 chỉ nên là sparse-history sensitivity.
- **Limitations:** preprint-only; public benchmark nhỏ và sparse; reviewer names có thể gây lỗi entity resolution; metadata không hoàn chỉnh. Repository tuyên bố data CC BY-NC 4.0 và code MIT, nhưng dataset card cũng cảnh báo source-platform ToS/commercial constraints.
- **RQ/H mapping:** Vietnamese sparsity/cold-start boundary; `REDUCED`, `NOT-H4`.
- **Foundational/recent:** very recent.
- **Include rationale:** nguồn Vietnamese mới nhất và có provenance pipeline rõ hơn nhiều nguồn scraper, nhưng publication status và quyền nguồn phải được giữ nguyên trạng thái preprint/conditional.

### L5-EXT-01 — Amazon-M2

- **Full identity:** Wei Jin, Haitao Mao, Zheng Li, Haoming Jiang, Chen Luo, Hongzhi Wen, Haoyu Han, Hanqing Lu, Zhengyang Wang, Ruirui Li, Zhen Li, Monica Cheng, Rahul Goutam, Haiyang Zhang, Karthik Subbian, Suhang Wang, Yizhou Sun, Jiliang Tang, Bing Yin, Xianfeng Tang, “Amazon-M2: A Multilingual Multi-Locale Shopping Session Dataset for Recommendation and Text Generation.”
- **Năm/venue:** NeurIPS 2023 Datasets and Benchmarks, volume 36.
- **DOI/official:** [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/193df57a2366d032fb18dcac0698d09a-Abstract-Datasets_and_Benchmarks.html); [DOI 10.52202/075280-0351](https://doi.org/10.52202/075280-0351); [Amazon Science page](https://www.amazon.science/publications/amazon-m2-a-multilingual-multi-locale-shopping-session-dataset-for-recommendation-and-text-generation).
- **Repository:** [Amazon-M2 Session Recommendation](https://github.com/HaitaoMao/Amazon-M2-Session-Recommendation); [official KDD Cup challenge](https://rails-aws.aicrowd.com/challenges/amazon-kdd-cup-23-multilingual-recommendation-challenge).
- **Evidence tier:** VI-A-.
- **Claims supported:** large multilingual session dataset with chronological interactions and rich item text can exercise both session/co-occurrence and content branches.
- **Dataset/protocol:** hơn 3.6M train sessions, khoảng 1.41M products, six European/Japanese locales; title, brand, color, price và description. Tasks gồm next-product, cross-locale recommendation và title generation.
- **Metric semantics:** recommendation tasks rank 100 product IDs; MRR@100 evaluates the first relevant next engagement.
- **Official vs harmonized:** official reproduction must retain task/locale split và MRR semantics. Harmonized-v5 may run full architecture, but sessions are product engagements—not verified orders/purchases.
- **Limitations:** không có persistent cross-session user và không có evidence rằng interaction target là purchase. Repository text/citation metadata conflicts with official proceedings on year; proceedings year 2023 controls. Paper appendix states Apache 2.0 for dataset distribution through AIcrowd; exact downloaded artifact and agreement still need archival.
- **RQ/H mapping:** strong `FULL-ARCH` transfer; `NOT-H4` under the locked purchase-outcome contract.
- **Foundational/recent:** recent.
- **Include rationale:** nguồn tốt nhất cho architecture transfer và multilingual/session robustness, nhưng không được dùng để claim H4 replication nếu outcome không được giữ.

### L5-EXT-02 — Tenrec

- **Full identity:** Guanghu Yuan, Fajie Yuan, Yudong Li, Beibei Kong, Shujie Li, Lei Chen, Min Yang, Chenyun Yu, Bo Hu, Zang Li, Yu Xu, Xiaohu Qie, “Tenrec: A Large-scale Multipurpose Benchmark Dataset for Recommender Systems.”
- **Năm/venue:** NeurIPS 2022 Datasets and Benchmarks.
- **DOI/official:** [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2022/hash/4ad4fc1528374422dd7a69dea9e72948-Abstract-Datasets_and_Benchmarks.html); [DOI 10.52202/068431-0834](https://doi.org/10.52202/068431-0834).
- **Repository:** [2022-NIPS-Tenrec](https://github.com/yuangh-x/2022-NIPS-Tenrec).
- **Evidence tier:** VI-A-/B+.
- **Claims supported:** multi-behavior datasets can test robustness across feedback semantics; protocol-specific results must not be pooled.
- **Dataset/protocol:** khoảng 5M users và 140M interactions từ Tencent article/video feeds; behaviors include click, like, share, follow, read và favorite. Paper defines multiple CTR, top-N và sequential tasks.
- **Metric semantics:** task-dependent; includes classification/ranking/sequential metrics, không có một metric chung hợp lệ để so với retail purchase NDCG.
- **Official vs harmonized:** official protocols phải được tái hiện riêng từng task. Timestamps bị loại bỏ, không có basket/order/raw item text nên v5 chỉ còn reduced branches.
- **Limitations:** non-commerce feed; sequence order không thay thế absolute time; repo states CC BY-NC 4.0 nhưng official Tencent download còn có agreement riêng.
- **RQ/H mapping:** robustness/context only; `REDUCED`, `NOT-H4`.
- **Foundational/recent:** recent.
- **Include rationale:** strong primary benchmark cho interaction-semantics boundary và reduced-method stress test.

### L5-EXT-03 — Coveo SIGIR eCom Data Challenge

- **Full identity:** Jacopo Tagliabue, Ciro Greco, Jean-Francis Roy, Bingqing Yu, Patrick John Chia, Federico Bianchi, Giovanni Cassani, “SIGIR 2021 E-Commerce Workshop Data Challenge.”
- **Năm/venue:** SIGIR eCom 2021 workshop.
- **DOI/official:** [official challenge page](https://sigir-ecom.github.io/ecom2021/data-task.html); [arXiv:2104.09423](https://arxiv.org/abs/2104.09423). Manuscript DOI is a placeholder and must not be cited as valid.
- **Repository/data:** [Coveo official repository](https://github.com/coveooss/SIGIR-ecom-data-challenge); [official terms](https://raw.githubusercontent.com/coveooss/SIGIR-ecom-data-challenge/main/Terms%20%26%20Conditions.txt).
- **Evidence tier:** VI+VII-B+.
- **Claims supported:** real e-commerce sessions can combine interaction types, timestamps, search context, catalog fields and text/image embeddings.
- **Dataset/protocol:** Public Data Release 1.0.0; approximately 36M events and nearly 5M sessions; event types include detail, add, purchase và remove.
- **Metric semantics:** next-item MRR; all-subsequent-item F1 derived from Precision@20/Recall@20; cart task uses weighted micro-F1.
- **Official vs harmonized:** official challenge reproduction evaluates future interactions/cart under its supplied split. A harmonized future-**purchase** top-k task could be H4-eligible only after validating purchase-positive counts, leakage-safe temporal split and candidate-set construction.
- **Limitations:** no persistent user beyond session; primary recommendation task is not necessarily purchase. Terms restrict use to noncommercial research/education, prohibit redistribution and de-anonymization.
- **RQ/H mapping:** `FULL-ARCH`; `H4-CONDITIONAL`.
- **Foundational/recent:** foundational for public e-commerce session benchmarks.
- **Include rationale:** closest public source to the session + content + commerce-event structure required by full v5.

### L5-EXT-04 — OTTO Recommender Systems Dataset

- **Full identity:** Philipp Normann, Sophie Baumeister, Timo Wilm, “OTTO Recommender Systems Dataset: A real-world e-commerce dataset for session-based recommender systems research.”
- **Năm/venue:** 2023, Kaggle dataset release.
- **DOI/official:** [dataset DOI 10.34740/KAGGLE/DSV/4991874](https://doi.org/10.34740/KAGGLE/DSV/4991874); [official dataset page](https://www.kaggle.com/datasets/otto/recsys-dataset).
- **Repository:** [otto-de/recsys-dataset](https://github.com/otto-de/recsys-dataset); [official protocol notes](https://raw.githubusercontent.com/otto-de/recsys-dataset/main/KAGGLE.md).
- **Evidence tier:** VII-A for dataset facts.
- **Claims supported:** large-scale sessions with clicks, carts and orders support temporal/event-type stress testing.
- **Dataset/protocol:** khoảng 12.9M train sessions, 216.7M train events và 1.86M items; four-week training period followed by one-week test.
- **Metric semantics:** weighted Recall@20 across click, cart and order targets; weights are part of the official challenge estimand.
- **Official vs harmonized:** official reproduction retains multi-target weighted Recall@20. Harmonized purchase/order top-k is possible, but the release intentionally contains only anonymized IDs.
- **Limitations:** no item/user metadata or text; full Deep/content branch cannot be instantiated. Same dataset may support session/order mechanism only.
- **License:** official repository identifies dataset as CC BY 4.0 and code as MIT; exact downloaded Kaggle revision still needs checksum.
- **RQ/H mapping:** `REDUCED`; cannot support strict full-Hybrid H4.
- **Foundational/recent:** recent.
- **Include rationale:** strongest order/session source for isolating the Wide/event branch and showing why missing content must be labeled reduced-method.

### L5-EXT-05 — RelBench v1, especially rel-amazon and rel-hm

- **Full identity:** Joshua Robinson, Rishabh Ranjan, Weihua Hu, Kexin Huang, Jiaqi Han, Alejandro Dobles, Matthias Fey, Jan E. Lenssen, Yiwen Yuan, Zecheng Zhang, Xinwei He, Jure Leskovec, “RelBench: A Benchmark for Deep Learning on Relational Databases.”
- **Năm/venue:** NeurIPS 2024 Datasets and Benchmarks.
- **DOI/official:** [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/25cd345233c65fac1fec0ce61d0f7836-Abstract-Datasets_and_Benchmarks_Track.html); [DOI 10.52202/079017-0672](https://doi.org/10.52202/079017-0672).
- **Repository:** [stanford-star/relbench](https://github.com/stanford-star/relbench); [rel-amazon](https://relbench.stanford.edu/datasets/rel-amazon/); [rel-hm](https://relbench.stanford.edu/datasets/rel-hm/).
- **Evidence tier:** VI-A for benchmark; B/C depending on underlying dataset rights.
- **Claims supported:** official temporal purchase tasks can be constructed from relational commerce data while preventing future leakage.
- **Dataset/protocol:** `rel-amazon` uses user/product/review relations and verified-purchase information; `rel-hm` uses transaction history plus item metadata. Both expose temporal splits and user-item purchase recommendation tasks.
- **Metric semantics:** MAP over future-purchase rankings within task-specific windows.
- **Official vs harmonized:** official reproduction should pin RelBench v1 and its task definitions. Harmonized-v5 can reuse temporal purchase labels and content but neither adapter provides native basket/session grouping sufficient for the locked Wide mechanism.
- **Limitations:** `rel-amazon` card says underlying dataset license not specified; `rel-hm` inherits source-specific restrictions. RelBench v2 appeared in 2026, so an unpinned current install is not a valid reproduction of the 2024 paper.
- **RQ/H mapping:** strong purchase/content protocol evidence; `REDUCED`, not strict H4.
- **Foundational/recent:** recent.
- **Include rationale:** provides the clearest official separation between temporal database construction and downstream task estimands.

### L5-EXT-06 — Amazon Reviews 2023 / BLaIR

- **Full identity:** Yupeng Hou, Jiacheng Li, Xiangjun Fu, Zhankui He, An Yan, Xiusi Chen, Julian McAuley, “Bridging Language and Items for Retrieval and Recommendation: Benchmarking LLMs as Semantic Encoders.”
- **Năm/venue:** ACL 2026, pp. 3251–3265.
- **DOI/official:** [ACL Anthology](https://aclanthology.org/2026.acl-long.147/); [DOI 10.18653/v1/2026.acl-long.147](https://doi.org/10.18653/v1/2026.acl-long.147); [dataset portal](https://amazon-reviews-2023.github.io/main.html).
- **Repository/data:** [AmazonReviews2023](https://github.com/hyp1231/AmazonReviews2023); [official Hugging Face dataset](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023); [0-core split documentation](https://amazon-reviews-2023.github.io/data_processing/0core.html).
- **Evidence tier:** VI-A for paper/protocol; C for redistribution rights.
- **Claims supported:** very large review corpus with timestamped interactions and rich item text is suitable for semantic/content and sparse-history sensitivity.
- **Dataset/protocol:** 571.54M reviews, 54.51M users, 48.19M items across 33 domains; provides leave-last-out and absolute-timestamp splits.
- **Metric semantics:** retrieval/recommendation semantics defined per BLaIR task; review/rating interaction is not automatically a purchase event.
- **Official vs harmonized:** official split reproduction should retain the documented cold-start treatment. Harmonized-v5 lacks basket/session/order identity, so only sequential/content branches are valid.
- **Limitations:** 0-core LLO sends one-interaction users directly to test and two-interaction users to validation/test, materially changing cold-start interpretation. Dataset maintainers explicitly state they cannot assign a dataset license and that users remain responsible for legal/ethical compliance; code license does not license the data.
- **RQ/H mapping:** `REDUCED`, `NOT-H4`.
- **Foundational/recent:** recent publication based on a major dataset revision.
- **Include rationale:** central source for item-language transfer and an important counterexample to assuming “public download” means licensed redistribution.

### L5-EXT-07 — H&M Personalized Fashion Recommendations

- **Full identity:** H&M Group/Kaggle, “H&M Personalized Fashion Recommendations.”
- **Năm/venue:** competition release year remains `UNRESOLVED` from the inspected primary data page; no DOI.
- **Official:** [official competition data page](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data); [RelBench rel-hm adapter](https://relbench.stanford.edu/datasets/rel-hm/).
- **Repository:** no official standalone source repository verified; RelBench provides a third-party research adapter.
- **Evidence tier:** VII-B.
- **Claims supported:** dated purchase histories with rich article metadata/images can support temporal future-purchase and content modeling.
- **Dataset/protocol:** customer transactions plus article/customer metadata; challenge target is items purchased in a future seven-day period.
- **Metric semantics:** official recommendation ranking uses mean average precision at 12.
- **Official vs harmonized:** official protocol is future purchase ranking. Harmonized-v5 can instantiate content/deep purchase prediction, but there is no native basket/order ID; same-day grouping would be an unvalidated pseudo-basket.
- **Limitations:** competition-specific access terms govern use; license/redistribution status was not established from a durable primary license artifact. Lack of native basket grouping removes the locked Wide mechanism.
- **RQ/H mapping:** purchase/content `REDUCED`; not strict H4.
- **Foundational/recent:** recent commerce benchmark.
- **Include rationale:** useful external purchase-domain sensitivity and explicit example where semantic task fit does not imply full-mechanism fit.

### L5-EXT-08 — Complete Journey

- **Full identity:** dunnhumby/84.51°, “The Complete Journey”; community research packaging as `completejourney`.
- **Năm/venue:** official provider resource; no paper year, venue or DOI verified.
- **Official:** [dunnhumby source-files page](https://www.dunnhumby.com/source-files/).
- **Repository:** [completejourney R package](https://github.com/bradleyboehmke/completejourney); [package metadata](https://raw.githubusercontent.com/bradleyboehmke/completejourney/master/DESCRIPTION).
- **Evidence tier:** VII-B-/C+ until version and rights are reconciled.
- **Claims supported:** household-level retail transactions with basket IDs, timestamps and product descriptions are structurally closest to the locked purchase/basket/content contract.
- **Dataset/protocol:** official provider page describes 2,500 frequent-shopper households and two years of purchases. R package `Complete Journey 2.0` describes 2,469 households, one year and transaction lines keyed by baskets/products.
- **Metric semantics:** no official recommender split or metric. Any NDCG@10 protocol would be a new harmonized protocol, not official reproduction.
- **Official vs harmonized:** `OFFICIAL_PROTOCOL_REPRODUCTION = N/A`; harmonized temporal top-k purchase prediction could supply full Wide + Deep mechanisms.
- **Limitations:** official provider and R package describe different scopes/editions. Package CC0 declaration cannot be assumed to license the underlying corporate dataset without a matching provider grant. Exact raw revision, checksum and redistribution terms remain unresolved.
- **RQ/H mapping:** strongest `H4-CONDITIONAL` candidate; experiment must not start until provenance/license lock.
- **Foundational/recent:** foundational retail transaction resource.
- **Include rationale:** only shortlisted source presently combining persistent household, true basket, purchase timestamp and product text closely enough for strict H4 consideration.

### L5-EXT-09 — TAOBAO-MM / MUSE

- **Full identity:** Bin Wu, Feifan Yang, Zhangming Chan, Yu-Ran Gu, Jiawei Feng, Chao Yi, Xiang-Rong Sheng, Han Zhu, Jian Xu, Mang Ye, Bo Zheng, “MUSE: A Simple Yet Effective Multimodal Search-Based Framework for Lifelong User Interest Modeling.”
- **Năm/venue:** 2025 arXiv preprint; submitted 8 December 2025. Peer-reviewed venue not verified.
- **DOI/official:** [arXiv:2512.07216](https://arxiv.org/abs/2512.07216); [TAOBAO-MM official portal](https://taobao-mm.github.io/).
- **Repository/data:** [MUSE code](https://github.com/alimama-tech/MUSE); [TAOBAO-MM release](https://huggingface.co/datasets/TaoBao-MM/Taobao-MM).
- **Evidence tier:** VI-preprint+VII-B.
- **Claims supported:** large-scale temporal interaction streams with multimodal item representations can stress semantic and long-history components.
- **Dataset/protocol:** official current portal reports millions of users/items and tens of millions of temporally split samples; item category/location and precomputed multimodal embeddings are provided, while raw images are withheld.
- **Metric semantics:** binary click/CTR evaluation using AUC/GAUC-style measures, not top-k purchase NDCG.
- **Official vs harmonized:** official reproduction is CTR-oriented. Harmonized ranking would change both estimand and candidate construction; no basket/order/purchase label supports H4.
- **License:** official portal/release declares Apache 2.0, but exact artifact revision and checksum must be pinned.
- **Limitations:** preprint status; click rather than purchase; no baskets; portal and manuscript statistics may reflect different revisions.
- **RQ/H mapping:** multimodal/content `REDUCED`, `NOT-H4`.
- **Foundational/recent:** very recent.
- **Include rationale:** relevant 2025–2026 external commerce resource, especially for method-sensitivity, but should not be elevated to purchase replication evidence.

## EXCLUDED_SOURCES

1. **L5-X-01 — ViMRHP, arXiv:2505.07416.** Vietnamese multimodal review-helpfulness resource, approximately 46K reviews/2K products. Excluded because the target is helpfulness classification rather than user-item recommendation or purchase prediction. [Preprint](https://arxiv.org/abs/2505.07416), [repository](https://github.com/trng28/ViMRHP).

2. **L5-X-02 — Instacart Market Basket Analysis / “3 Million Instacart Orders.”** Structurally valuable basket histories and repeat-product target, but the historical provider dataset pages were not durably accessible in this review, item text is absent, and a current canonical data license/redistribution grant was not verified. Third-party mirrors cannot establish provenance. [Official Kaggle challenge overview](https://www.kaggle.com/c/basket-analysis/overview).

3. **L5-X-03 — Retailrocket recommender-system dataset.** Contains view/add-to-cart/transaction events, but lacks a strong primary publication, official split and provider-controlled repository; many item-property values are hashed. Kaggle metadata alone is insufficient to resolve original provenance and rights. [Dataset page](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset).

4. **L5-X-04 — Ta-Feng grocery dataset.** Frequently republished, but no canonical provider release, exact revision and primary license were verified. Excluded until a source-of-record can be established.

5. **L5-X-05 — YOOCHOOSE / RecSys Challenge 2015.** Primary challenge identity exists and sessions include click/purchase, but it is legacy, lacks item text, and current canonical download/license status remains unresolved. [Official RecSys 2015 challenge page](https://recsys.acm.org/recsys15/challenge/); paper DOI: [10.1145/2792838.2798723](https://doi.org/10.1145/2792838.2798723).

6. **L5-X-06 — Diginetica CIKM Cup 2016.** Processed mirrors are common, but a current canonical organizer-hosted artifact and applicable license were not verified. Excluded on provenance/access grounds.

7. **L5-X-07 — Legacy Alibaba/Tianchi Taobao or Tmall releases.** Exact editions and download agreements are challenge/login scoped; generic references to “Taobao dataset” do not uniquely identify an artifact. Newer TAOBAO-MM was retained instead. [Tianchi platform](https://tianchi.aliyun.com/specials/promotion/about).

## UNRESOLVED

- **U-01:** Complete Journey official page and `completejourney` R package describe different durations/household counts. Exact edition, raw-file checksum and governing license must be reconciled.
- **U-02:** Coveo workshop manuscript contains a placeholder DOI; record it as **no verified DOI**, not as a resolvable citation.
- **U-03:** H&M competition publication year and durable dataset license were not independently verified from the inspected primary artifact.
- **U-04:** ViFoodRec repository has no dataset license; ACL paper CC BY 4.0 licenses the paper, not automatically the scraped dataset.
- **U-05:** ViEcomRec repository license does not by itself settle Shopee content rights or platform ToS.
- **U-06:** ViHoRec release license and source-platform restrictions need an institutional review before redistribution or commercial reuse.
- **U-07:** Amazon Reviews 2023 maintainers explicitly do not assign a dataset license; public hosting must not be described as open licensing.
- **U-08:** Amazon-M2 repository contains inconsistent year metadata; official NeurIPS 2023 proceedings control. Downloaded AIcrowd revision/agreement still needs archival.
- **U-09:** Tenrec repository license and Tencent download agreement must both be captured; neither should silently overwrite the other.
- **U-10:** RelBench experiments must pin v1/2024-compatible code and processed-data hashes; current v2 behavior is not presumed identical.
- **U-11:** TAOBAO-MM portal, preprint and release statistics appear revision-sensitive. Store exact dataset revision and checksum before use.
- **U-12:** Instacart, Ta-Feng and Diginetica remain inaccessible or provenance-incomplete; do not substitute community mirrors without separate verification.
- **U-13:** No accepted source currently has both verified unrestricted redistribution rights and unconditional strict-H4 compatibility.

## CLAIM_SOURCE_CARDS

### CSC-L5-01 — Vietnamese resource boundary

- **Claim:** Public Vietnamese recommendation resources now cover e-commerce reviews, food metadata/ratings and hotel reviews, but remain narrow and do not expose the basket/session/order-plus-content contract needed by full v5.
- **Supports:** L5-VN-01, L5-VN-02, L5-VN-03.
- **Allowed wording:** “The reviewed Vietnamese resources provide valuable language/domain coverage but support reduced-method or cold-start evaluation rather than full Hybrid replication.”
- **Forbidden extrapolation:** “No Vietnamese recommender datasets exist,” or “Vietnamese datasets are universally smaller/worse.”

### CSC-L5-02 — Architecture transfer is not H4 replication

- **Claim:** Amazon-M2 and Coveo contain enough session and content signals to exercise the architecture, but their official outcomes differ from the locked future-purchase estimand.
- **Supports:** L5-EXT-01, L5-EXT-03.
- **Allowed wording:** “These datasets support architecture-transfer or conditional harmonized evaluation.”
- **Forbidden extrapolation:** treating an MRR improvement on next engagement as a replication of purchase NDCG@10.

### CSC-L5-03 — Purchase semantics without the full mechanism

- **Claim:** H&M and RelBench provide temporal future-purchase tasks with item content, but do not provide native basket/session identity sufficient for the locked Wide branch.
- **Supports:** L5-EXT-05, L5-EXT-07.
- **Allowed wording:** “Purchase-task sensitivity under a reduced architecture.”
- **Forbidden extrapolation:** creating same-day pseudo-baskets and describing them as observed baskets without a preregistered sensitivity analysis.

### CSC-L5-04 — Basket/event semantics without content

- **Claim:** OTTO supplies session, cart and order events but intentionally withholds item metadata, preventing full Deep/content reproduction.
- **Supports:** L5-EXT-04.
- **Allowed wording:** “Wide/event-branch stress test.”
- **Forbidden extrapolation:** reporting OTTO as full-Hybrid evidence.

### CSC-L5-05 — Strict-H4 candidate

- **Claim:** Complete Journey is structurally closest to the required household + basket + timestamp + purchase + product-text contract.
- **Supports:** L5-EXT-08.
- **Allowed wording:** “Leading H4 candidate pending exact revision and rights verification.”
- **Forbidden extrapolation:** “H4 dataset selected” or “CC0 retail dataset” before provider/package rights are reconciled.

### CSC-L5-06 — Multi-behavior and multimodal sensitivity

- **Claim:** Tenrec and TAOBAO-MM can test robustness to behavior semantics, long histories and multimodal content, but neither preserves retail purchase-basket H4.
- **Supports:** L5-EXT-02, L5-EXT-09.
- **Allowed wording:** “Reduced-method sensitivity or mechanism stress test.”
- **Forbidden extrapolation:** pooling their AUC/GAUC/top-N results with purchase NDCG.

### CSC-L5-07 — Public availability is not redistribution permission

- **Claim:** Downloadability, repository code licenses and paper licenses do not necessarily license underlying datasets.
- **Supports:** L5-VN-01, L5-VN-02, L5-VN-03, L5-EXT-03, L5-EXT-05, L5-EXT-06, L5-EXT-08.
- **Allowed wording:** “License/redistribution status is source-specific and must be archived per exact artifact.”
- **Forbidden extrapolation:** inferring dataset licensing from an ACL paper license, code MIT license, package license or public URL.

### CSC-L5-08 — H4 decision rule

- **Claim:** H4 can only be tested when the external dataset preserves the essential purchase/top-k/model contract and the paired dataset-specific NDCG@10 CI is estimable under the harmonized protocol.
- **Supports:** Stage 1A RQ/estimand artifacts plus L5-EXT-03 and L5-EXT-08 as conditional candidates.
- **Allowed wording:** “If no candidate clears the audit, H4 = NOT_TESTED.”
- **Forbidden extrapolation:** using an official-protocol score, architecture-only run or reduced-method gain as an H4 pass.

## OVERLAP_FLAGS

- **OF-01:** Amazon Reviews 2023 is upstream data for RelBench `rel-amazon`; do not count them as two independent datasets in synthesis or robustness totals.
- **OF-02:** H&M competition data is upstream for RelBench `rel-hm`; distinguish original competition protocol from RelBench relational task construction.
- **OF-03:** Amazon-M2 paper, GitHub repository, Amazon Science page and KDD Cup challenge are one artifact family.
- **OF-04:** Coveo paper, repository, challenge page and terms are one artifact family.
- **OF-05:** Each ViEcomRec, ViFoodRec and ViHoRec paper/repository pair is one source family, not independent corroboration.
- **OF-06:** TAOBAO-MM dataset and MUSE preprint/code are one release family.
- **OF-07:** Tenrec may overlap with a benchmarking/multi-behavior lane; L5 should own dataset semantics/license, while another lane may own model-performance claims.
- **OF-08:** OTTO may overlap with session-recommender literature; this lane should retain only provenance, split, event and compatibility evidence.
- **OF-09:** Complete Journey community package is an adapter/distribution layer, not independent confirmation of dunnhumby’s underlying rights or dataset scope.

## CENTRAL_REVIEW_ALERTS

1. **Amazon-M2 must be downgraded from default H4 candidate to architecture-transfer evidence.** It supplies sessions and item content, but its official target is next engagement rather than verified purchase and it lacks persistent cross-session user identity.

2. **No dataset is presently unconditionally eligible for H4.**
   - First audit: Complete Journey exact edition, raw source and license.
   - Second audit: Coveo purchase-only harmonized target, positive support, temporal split and candidate construction.
   - If neither clears the gate, record `H4 = NOT_TESTED`; do not substitute a reduced-method result.

3. **Maintain two separate result families:**
   - `OFFICIAL_PROTOCOL_REPRODUCTION`
   - `HARMONIZED_PROTOCOL_COMPARISON`
   
   Metric values must not be compared across these families or across datasets.

4. **Recommended experiment queue after legal/provenance audit:**
   - Complete Journey — prospective strict H4.
   - Coveo — conditional full-architecture/future-purchase analysis.
   - Amazon-M2 — full-architecture transfer only.
   - OTTO/H&M/RelBench — reduced-branch sensitivity.
   - ViEcomRec/ViHoRec — Vietnamese domain and cold-start sensitivity.

5. **Pin before Stage 1E:** source URL, access date, exact file list, checksums, repository commit, dataset revision, license/terms snapshot and preprocessing script version.

6. **Do not redistribute:** Coveo explicitly restricts redistribution; Amazon Reviews lacks a dataset license; Complete Journey, H&M, ViFoodRec and scraped Vietnamese sources require further rights review.

7. **Dataset contribution boundary:** a defensible contribution is not “first Vietnamese recommender dataset,” but a reproducible Vietnamese retail benchmark/protocol that adds missing transaction semantics, temporal controls, basket/session identity, item text, provenance and legal/revision documentation.

8. **Contradiction to preserve in the central synthesis:** datasets richest in text are often missing verified orders/baskets, while datasets richest in baskets/orders often omit item content. This is a real compatibility constraint, not a reason to silently modify the architecture.

9. **Publication status discipline:** ViHoRec and MUSE are preprints as of the review date; Coveo has no verified DOI; H&M and Complete Journey are operational dataset resources rather than peer-reviewed dataset papers.

10. **ESCALATION_RECOMMENDED: NO** for literature discovery. Institutional/legal review is nevertheless recommended before redistribution or commercial reuse of source-derived datasets.

