---
lane: L3
task_id: 019ffb38-af79-7c22-b38a-b31bd0ce2cd8
model: 5.6 Tera / XHigh
status: complete
captured_at: 2026-08-13
provenance: verbatim task final handoff
---

# L3 raw literature-search handoff

Đã hoàn tất sàng lọc độc lập L3 theo workflow ARS lit-review: 18 candidate identities, shortlist 12 nguồn primary/official. Không sửa file, không chạy thí nghiệm, và không suy diễn kết quả H3 từ literature.

## SEARCH_LOG

- Phạm vi: Apriori/rule recommendation, hybrid rule–sequential mechanisms, SASRec/BERT4Rec, next-/novel-basket, repeat–explore bias, và temporal evaluation.
- Nguồn tra cứu/chấp nhận: trang proceedings/DOI chính thức, PDF tác giả hợp lệ, và repository của tác giả/lab. Không dùng blog hay survey làm bằng chứng kỹ thuật chính.
- Truy vấn chuẩn hoá: `association rule recommendation support confidence`, `hybrid sequential rules collaborative filtering`, `SASRec/BERT4Rec official repository`, `next basket recommendation reality check`, `masked swapped novel basket`, `sequential recommender data split`.
- Sau khử trùng title/DOI: 18 nguồn; chấp nhận 12; loại 6.
- Phân bố: 6/12 nguồn 2022–2025; 6 nguồn foundational cần thiết. Tất cả đều là nghiên cứu kỹ thuật/benchmark—đúng chủ đích lane L3, nhưng không phải một corpus đa phương pháp.

Tier: `P1-A` = peer-reviewed primary, protocol/repository hoặc provenance tốt; `P1-B` = primary nhưng adapter/reproducibility hạn chế; `P1-F` = foundational definition, không phải bằng chứng ranking.

## ACCEPTED_SOURCES

1. **AR-APR — P1-F, foundational.** Rakesh Agrawal and Ramakrishnan Srikant (1994), *Fast Algorithms for Mining Association Rules in Large Databases*, VLDB 1994, pp. 487–499. [Official proceedings/PDF](https://vldb.org/conf/1994/P487.PDF); DOI: **không thấy DOI được gán**; repository: không áp dụng.  
   - Claims: định nghĩa support, confidence, frequent itemset, và Apriori/AprioriTid/AprioriHybrid.
   - Method/protocol: transaction-itemset mining, không phải recommender evaluation; metric semantics là support count và confidence, không phải NDCG/Recall.
   - Hạn chế: không chứng minh Apriori cải thiện ranking hay hiệu quả H3.
   - Mapping: định nghĩa rule registry cho RQ3/H3. Include vì cần neo chính xác cho support/confidence và train-only mining.

2. **AR-MULTI — P1-B, foundational direct recommendation.** Abhijeet Ghoshal and Sumit Sarkar (2014), *Association Rules for Recommendations with Multiple Items*, *INFORMS Journal on Computing*, 26(3), 433–448. DOI: [10.1287/ijoc.2013.0575](https://doi.org/10.1287/ijoc.2013.0575); repository: không tìm thấy official code.  
   - Claims: association rules có thể là recommender thực sự; consequent nhiều item và so sánh với traditional rules/CF/MF; hiệu quả thay đổi theo loại dữ liệu.
   - Method/protocol: transactional và sparse-clickstream; random 80/20 transaction split, mine rules trên train rồi evaluate test baskets.
   - Metric semantics: paper-specific recommendation accuracy; chi tiết candidate universe/metric chưa tái-audit đầy đủ, không chuyển sang NDCG@10 v5.
   - Hạn chế: random split, không temporal; không full-catalog contract; không public adapter.
   - Mapping: RQ3/H3 leakage-safe pattern. Include vì là nguồn trực tiếp nhất cho rule-based recommendation, nhưng chỉ dùng cơ chế/protocol separation.

3. **HYB-SR-CF — P1-B, foundational hybrid.** Duen-Ren Liu, Chin-Hui Lai, and Wang-Jung Lee (2009), *A Hybrid of Sequential Rules and Collaborative Filtering for Product Recommendation*, *Information Sciences*, 179(20), 3505–3519. DOI: [10.1016/j.ins.2009.06.004](https://doi.org/10.1016/j.ins.2009.06.004); [official institutional record](https://scholar.nycu.edu.tw/en/publications/a-hybrid-of-sequential-rules-and-collaborative-filtering-for-prod/); repository: không tìm thấy.  
   - Claims: sequential-rule và CF có thể được kết hợp; dùng current purchase/history và RFM segmentation.
   - Method/protocol: product recommendation với segmentation-based sequential rules và kNN-CF.
   - Metric semantics: experimental ranking/recommendation metrics theo paper; chi tiết không dùng để so trực tiếp.
   - Hạn chế: cũ, protocol/dataset legacy, không phải wide/deep và không có reproduction artifact công khai.
   - Mapping: evidence kiến trúc cho H3, không phải evidence hiệu quả dự kiến.

4. **WD — P1-B, foundational architecture.** Heng-Tze Cheng, Levent Koc, Jeremiah Harmsen, Tal Shaked, Tushar Chandra, Hrishi Aradhye, Glen Anderson, Greg Corrado, Wei Chai, Mustafa Ispir, Rohan Anil, Zakaria Haque, Lichan Hong, Vihan Jain, Xiaobing Liu, and Hemal Shah (2016), *Wide & Deep Learning for Recommender Systems*, DLRS@RecSys 2016, pp. 7–10. DOI: [10.1145/2988450.2988454](https://doi.org/10.1145/2988450.2988454); [official metadata](https://dblp.org/rec/conf/recsys/Cheng0HSCAACCIA16.html); repository provenance: **UNRESOLVED**.  
   - Claims: wide crossed features hỗ trợ memorization; deep embeddings hỗ trợ generalization; joint training là thiết kế gốc.
   - Method/protocol: Google Play app-acquisition/CTR online experiment, proprietary data.
   - Metric semantics: business/CTR-style outcome, không phải temporal full-catalog top-K.
   - Hạn chế: khác sâu với v5 two-tower fusion; kết quả proprietary không chứng minh Apriori Wide branch.
   - Mapping: rationale ablation Full/No-Wide/Deep-only/Wide-only cho RQ3/H3.

5. **SASREC — P1-A, foundational sequential baseline.** Wang-Cheng Kang and Julian McAuley (2018), *Self-Attentive Sequential Recommendation*, IEEE ICDM 2018, pp. 197–206. DOI: [10.1109/ICDM.2018.00035](https://doi.org/10.1109/ICDM.2018.00035); [author repository](https://github.com/kang205/SASRec).  
   - Claims: causal self-attention là baseline sequential mạnh; code công khai TensorFlow/Python legacy.
   - Method/protocol: next-item sequence ranking, timestamp-sorted interactions và sampled-negative loss.
   - Metric semantics: top-K theo protocol gốc; candidate sampling và split không tương đương full-catalog v5.
   - Hạn chế: không basket-native; implementation TensorFlow 1.12/Python 2 cần pin commit và adapter.
   - Mapping: sequential baseline lane cho RQ3; không phải direct test của H3.

6. **BERT4REC — P1-A, foundational sequential baseline.** Fei Sun, Jun Liu, Jian Wu, Changhua Pei, Xiao Lin, Wenwu Ou, and Peng Jiang (2019), *BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations from Transformer*, CIKM 2019, pp. 1441–1450. DOI: [10.1145/3357384.3357895](https://doi.org/10.1145/3357384.3357895); [author repository](https://github.com/FeiSun/BERT4Rec).  
   - Claims: masked-item, bidirectional transformer là baseline sequential khác bản chất với SASRec.
   - Method/protocol: masked sequential-item prediction; source implementation dùng TensorFlow 1.12/Python 2.7.
   - Metric semantics: paper-specific top-K protocol; không transplant raw metric sang v5.
   - Hạn chế: không next-basket-native; legacy stack; cần harmonized adapter riêng.
   - Mapping: baseline comparator, RQ3 supporting context.

7. **HAM — P1-A, recent hybrid mechanism.** Bo Peng, Zhiyun Ren, Srinivasan Parthasarathy, and Xia Ning (2022 issue; online 2021), *HAM: Hybrid Associations Models for Sequential Recommendation*, *IEEE Transactions on Knowledge and Data Engineering*, 34(10), 4838–4853. DOI: [10.1109/TKDE.2021.3049692](https://doi.org/10.1109/TKDE.2021.3049692); [author manuscript](https://pmc.ncbi.nlm.nih.gov/articles/PMC10034966/); [lab repository](https://github.com/ninglab/HAM).  
   - Claims: fusion long-term preference, high-/low-order sequential associations, and item synergies can be ablated.
   - Method/protocol: BPR-trained sequential model, six public datasets, paper-specific evaluation settings.
   - Metric semantics: top-K ranking only within its source protocol; no direct NDCG comparison.
   - Hạn chế: learned associations, **không phải Apriori rules**; sampled-negative objective; code commit phải được pin.
   - Mapping: architecture/fusion-ablation evidence for RQ3, not rule-leakage evidence.

8. **M2 — P1-A, recent next-basket hybrid.** Bo Peng, Zhiyun Ren, Srinivasan Parthasarathy, and Xia Ning (2023; online 2022), *M²: Mixed Models With Preferences, Popularities and Transitions for Next-Basket Recommendation*, *IEEE Transactions on Knowledge and Data Engineering*, 35(4), 4033–4046. DOI: [10.1109/TKDE.2022.3142773](https://doi.org/10.1109/TKDE.2022.3142773); [official record](https://ohiostate.elsevierpure.com/en/publications/msup2sup-mixed-models-with-preferences-popularities-and-transitio/); [lab repository](https://github.com/ninglab/M2).  
   - Claims: preference, global popularity, và transition components có thể được tách/fuse rồi ablate.
   - Method/protocol: next 1/2/3 basket trên bốn public basket datasets; source preprocessing gồm leave-one-style choices.
   - Metric semantics: basket-ranking metrics theo protocol nguồn; không phải full-catalog temporal v5.
   - Hạn chế: không novel-only, không Apriori, và leave-one preprocessing khác contract v5.
   - Mapping: basket/fusion baseline evidence; hỗ trợ thiết kế diagnostic ablations.

9. **NBR-REALITY — P1-A, recent evaluation guard.** Ming Li, Sami Jullien, Mozhdeh Ariannezhad, and Maarten de Rijke (2023), *A Next Basket Recommendation Reality Check*, *ACM Transactions on Information Systems*, 41(4), Article 116. DOI: [10.1145/3587153](https://doi.org/10.1145/3587153); repository: không tìm thấy official code.  
   - Claims: next-basket prediction trộn repeat và exploration; aggregate accuracy có thể che khuất hai hành vi này.
   - Method/protocol: phân tích next-basket datasets và đề xuất đánh giá repeat/explore.
   - Metric semantics: ratio/analysis cho repeat-vs-explore, không phải H3 NDCG.
   - Hạn chế: không kiểm tra Apriori Wide branch hay Vietnamese retail.
   - Mapping: guardrail cho cohort report—phải nêu coverage/repeat–novel composition, không chỉ average quality.

10. **BTBR — P1-A, recent novel-basket baseline.** Ming Li, Mozhdeh Ariannezhad, Andrew Yates, and Maarten de Rijke (2023), *Masked and Swapped Sequence Modeling for Next Novel Basket Recommendation in Grocery Shopping*, RecSys 2023. DOI: [10.1145/3604915.3608803](https://doi.org/10.1145/3604915.3608803); [official repository](https://github.com/liming-7/Mask-Swap-NNBR).  
    - Claims: novel-only objective, masking strategy, và basket swap là các can thiệp cần ablation; chúng không có lợi nhất quán trên mọi dataset.
    - Method/protocol: three grocery datasets; user-level 80/20 train/test, validation user split, filtering basket/user; novel target K=10/20.
    - Metric semantics: fixed-K novel-basket ranking theo protocol nguồn; không phải temporal per-user cutoff/full catalog v5.
    - Hạn chế: user split và grocery assumptions khác v5; improvement/harm từ swapping phụ thuộc dataset.
    - Mapping: candidate reference cho basket/sequential adapter; evidence phản biện cho bất kỳ claim “augmentation luôn giúp”.

11. **REP-EXP — P1-A, recent diagnostic.** Ming Li, Ali Vardasbi, Andrew Yates, and Maarten de Rijke (2023), *Repetition and Exploration in Sequential Recommendation*, SIGIR 2023, pp. 2532–2541. DOI: [10.1145/3539618.3591914](https://doi.org/10.1145/3539618.3591914); [author PDF](https://staff.fnwi.uva.nl/m.derijke/wp-content/papercite-data/pdf/li-2023-repetition.pdf); repository: không xác minh được official repo.  
    - Claims: aggregate accuracy/significance không đủ để mô tả repeat và explore; recommendation có thể hưởng lợi từ repetition shortcut.
    - Method/protocol: phân tách repeat/explore trong sequential recommendation.
    - Metric semantics: source-specific accuracy/exposure diagnostics, không phải v5 NDCG@10.
    - Hạn chế: không Apriori, không basket rule cohort.
    - Mapping: report guardrail cho RQ3/H3; cohort quality không thay thế overall benchmark result.

12. **TIME-SPLIT — P1-A, recent protocol evidence.** Danil Gusak, Anna Volodkevich, Anton Klenitskiy, Alexey Vasilev, and Evgeny Frolov (2025), *Time to Split: Exploring Data Splitting Strategies for Offline Evaluation of Sequential Recommenders*, RecSys 2025, pp. 874–883. DOI: [10.1145/3705328.3748164](https://doi.org/10.1145/3705328.3748164); [official repository](https://github.com/monkey0head/time-to-split).  
    - Claims: leave-one-out và global temporal splits thay đổi outcome/ranking; split choice là một phần của estimand.
    - Method/protocol: controlled comparison of sequential-recommender split strategies; repository includes unsampled ranking evaluation.
    - Metric semantics: source uses HR/NDCG/MRR under its own split/candidate design; v5 GAUC/NDCG@10 remains distinct.
    - Hạn chế: không rule-mining study và không Vietnamese retail.
    - Mapping: mạnh nhất cho temporal boundary, immutable pre-Test registry, và không chọn support/confidence theo test.

## EXCLUDED_SOURCES

- Weiyang Lin, Sergio A. Alvarez, and Carolina Ruiz (2002), *Efficient Adaptive-Support Association Rule Mining for Recommender Systems*, *Data Mining and Knowledge Discovery*, 6(1), 83–105. DOI [10.1023/A:1013284820704](https://doi.org/10.1023/A:1013284820704). Direct rule recommender nhưng cũ, không mạnh hơn AR-MULTI cho H3; giữ làm backup nếu cần phân tích adaptive support.
- Zhiang Wu, Changsheng Li, Jie Cao, and Yong Ge (2020), *On Scalability of Association-rule-based Recommendation: A Unified Distributed-computing Framework*, *ACM TWEB*, 14(3), Article 13. DOI [10.1145/3398202](https://doi.org/10.1145/3398202). Chủ yếu scaling/serving; không trả lời causal Wide ablation.
- Mozhdeh Ariannezhad et al. (2022), *ReCANet: A Repeat Consumption-Aware Neural Network for Next Basket Recommendation*, SIGIR 2022. DOI [10.1145/3477495.3531708](https://doi.org/10.1145/3477495.3531708). Repeat-focused; xung đột với novel-purchase target.
- Ori Katz, Oren Barkan, Nir Zabari, and Noam Koenigstein (2022), *Learning to Ride a Buy-Cycle: A Hyper-Convolutional Model for Next Basket Recommendation*, RecSys 2022. DOI [10.1145/3523227.3546763](https://doi.org/10.1145/3523227.3546763). Repurchase/buy-cycle focus, không phù hợp direct baseline cho organic-novel v5.
- Anton Klenitskiy and Alexey Vasilev (2023), *Turning Dross Into Gold Loss: is BERT4Rec really better than SASRec?*, RecSys 2023. DOI [10.1145/3604915.3610644](https://doi.org/10.1145/3604915.3610644); [repository](https://github.com/antklen/sasrec-bert4rec-recsys23). Loại khỏi shortlist L3 vì thuộc adapter/evaluation lane; cần chuyển alert sang L1.
- Arnob Saha? No—**Krichene and Rendle** (2022), *On Sampled Metrics for Item Recommendation*, *Communications of the ACM*, 65(7), 75–83. DOI [10.1145/3535335](https://doi.org/10.1145/3535335). Loại vì là source evaluation chung, không L3 mechanism; vẫn nên dùng ở L1 để cấm suy luận từ sampled metrics.

## UNRESOLVED

- Không có nguồn nào trực tiếp kiểm định đúng estimand: **Apriori train-only wide branch + rule-aligned cohort + Full/No-Wide + temporal full-catalog Vietnamese retail**. Đây là khoảng trống nghiên cứu, không phải bằng chứng H3.
- Wide & Deep nói code từng được mở nhưng repository/revision tương ứng paper chưa xác minh được; không dùng làm reproduction source.
- AR-MULTI và HYB-SR-CF không có public implementation chính thức đã xác minh; chỉ đủ làm architecture/protocol evidence.
- Với SASRec/BERT4Rec, exact source candidate universe và metric pipeline cần audit từ code/paper trước khi tuyên bố “official reproduction”; repository legacy phải pin commit/hash.
- Với BTBR, page range và toàn bộ preprocessing details ngoài các điều kiện đã kiểm tra không nên ghi như fact cho manuscript cho tới khi source card đầy đủ được central review.
- Không có conflict-of-interest bất thường từ metadata scan; đây **không** phải full disclosure audit.

## CLAIM_SOURCE_CARDS

- **C1 — Apriori semantics.** AR-APR hỗ trợ support là transaction frequency và confidence là conditional rule strength. Trạng thái: factual/foundational. Không suy ra ranking effectiveness.
- **C2 — Rule recommender phải mine/evaluate tách biệt.** AR-MULTI cho precedent transaction-train mining rồi test evaluation. Trạng thái: factual precedent; v5 nên mạnh hơn bằng temporal cutoff. Inference: support/confidence, rule cap, antecedent length, và score aggregation phải chọn trước Test.
- **C3 — Hybrid complementarity là hypothesis, không phải kết luận.** HYB-SR-CF, WD, HAM và M2 cho thấy các component preference/association có thể fuse và ablate. Trạng thái: architecture evidence. Không nguồn nào chứng minh Apriori Wide sẽ tăng NDCG@10 v5.
- **C4 — SASRec/BERT4Rec là baseline reference, không phải apples-to-apples benchmark.** Hai nguồn cung cấp canonical sequential mechanisms và source code. Trạng thái: baseline provenance. Cần adapter harmonized-v5.
- **C5 — Novel/repeat confounding.** NBR-REALITY, REP-EXP và BTBR hỗ trợ việc báo cáo novelty/repeat composition và cohort coverage. Trạng thái: evaluation guardrail.
- **C6 — Temporal split là một phần của estimand.** TIME-SPLIT hỗ trợ cấm rule mining/tuning trên validation/test target và yêu cầu freeze registry trước Test. Trạng thái: protocol evidence.
- **C7 — H3 testable claim.** H3 chỉ được xác nhận nếu lower 95% CI của `Full − No-Wide` NDCG@10 trên cohort đã đóng băng lớn hơn 0. Trạng thái hiện tại: **NOT_RUN**.

## OVERLAP_FLAGS

- **L1 evaluation/reproducibility:** TIME-SPLIT, Krichene–Rendle, và Klenitskiy–Vasilev. L1 nên sở hữu sampled-vs-exact và split-comparability claims.
- **Baseline adapter lane:** SASRec/BERT4Rec repositories. L3 chỉ giữ mechanism/provenance; central phải tách “official protocol result” khỏi “harmonized-v5 result”.
- **Hybrid architecture lane:** WD, HAM, M2 cũng có ích cho lane kiến trúc; tránh duplicate narrative và chỉ dùng một canonical claim card mỗi source.
- **External-data lane:** BTBR grocery datasets hữu ích nếu kiểm thử basket semantics; không dùng như evidence về Vietnamese language/cold-item behavior.
- **No overlap evidence for H4:** không nguồn L3 nào chứng minh content/text hoặc cold-item benefit.

## CENTRAL_REVIEW_ALERTS

- Cụm “**train-defined rule-aligned cohort**” đang không chính xác nếu membership đòi hỏi consequent `c` nằm trong held-out truth. Rules là train-mined, nhưng cohort khi đó là outcome-labelled. Đề xuất tên: `train-mined rule-aligned evaluation cohort`; freeze registry và cohort-builder trước Test.
- Nếu cần cohort thuần train-defined, chỉ dùng antecedent/history để chọn user. Khi đó nó đo potential rule coverage, không xác nhận rule success trên held-out consequent.
- Rule registry phải chỉ dùng organic purchase events trước cutoff; xác định rõ semantic/trap injections có bị loại không. Nếu không, synthetic artifacts có thể tạo rules dễ đoán và làm H3 không còn diễn giải được.
- Full/No-Wide là contrast duy nhất cho H3: cùng Deep branch, candidate universe, seen-item mask, seed policy, tuning budget, score calibration, tie-breaking và target. Deep-only/Wide-only chỉ là diagnostics.
- Report bắt buộc: support/confidence, max antecedent size, rule cap, aggregation/scoring, registry hash, cutoff, cohort size/coverage, và zero-eligible-user behavior. Không chọn các tham số này theo Test.
- Không so raw metrics với SASRec, BERT4Rec, HAM, M2 hoặc BTBR vì dataset, split, masking, negative sampling và task khác v5.
- BTBR cho thấy augmentation/novel-specific training không luôn hữu ích; không viết prior khẳng định “Mask-Swap sẽ nâng chất lượng”.
- H3 hiện không có kết quả thực nghiệm: manuscript chỉ được nói mechanism hypothesis/estimand cho đến khi T4 chạy xong.

