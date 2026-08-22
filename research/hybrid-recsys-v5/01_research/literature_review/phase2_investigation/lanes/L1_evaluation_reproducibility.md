---
lane: L1
task_id: 019ffb38-af65-7d73-bd68-e7af73de5c43
model: 5.6 Tera / XHigh
status: complete
captured_at: 2026-08-13
provenance: verbatim task final handoff
---

# L1 raw literature-search handoff

Đã hoàn tất lane L1 độc lập. Tôi không sửa file hay chạy experiment. Kết luận chính: protocol full-catalog temporal với seen-item masking, metric code công khai và adapter reproduction là có cơ sở mạnh; nhưng hierarchical bootstrap theo seed và macro per-user GAUC là thiết kế project cần được khóa/kiểm thử riêng, không nên mô tả là chuẩn chung đã được literature xác lập.

## SEARCH_LOG

- Mode: `ars-codex:academic-research-suite` → `deep-research/lit-review`; chỉ thực hiện discovery/screening Phase 2.
- Ngày search: 2026-08-13.
- Nguồn truy vấn: trang proceedings/publisher chính thức (ACM, AAAI, IEEE, JMLR, Springer, Elsevier), official project repositories.
- Query families:
  - `"sampled metrics" item recommendation`, `"top-k recommendation" sampling evaluation`
  - `recommender offline evaluation temporal split candidate set`
  - `reproducibility rigorous evaluation recommender systems`
  - `recommender metrics consistency NDCG HR Recall AUC`
  - `RecBole`, `DaisyRec`, `Elliot`, `BARS`
- Sàng lọc: 18 candidate đã deduplicate → 12 accepted, 6 excluded.
- Include nếu: primary peer-reviewed/official, identity–venue–DOI xác minh được, trực tiếp hỗ trợ L1.
- Không dùng metric của bất kỳ paper nào làm baseline/số liệu so sánh cho v5.

Evidence tiers: `P1` = peer-reviewed primary study; `P1-M` = primary metric-definition source; `P1-T` = peer-reviewed toolkit/benchmark paper, chỉ hỗ trợ implementation/provenance claim.

## ACCEPTED_SOURCES

| ID | Nguồn | Tier | Vai trò L1 |
|---|---|---|---|
| L1-S01 | Krichene & Rendle (2020), *On Sampled Metrics for Item Recommendation* | P1 | Exact vs sampled |
| L1-S02 | Jin et al. (2021), *On Estimating Recommendation Evaluation Metrics under Sampling* | P1 | Estimator cho sampled metrics |
| L1-S03 | Li et al. (2023), *Towards Reliable Item Sampling for Recommendation Evaluation* | P1 | Adaptive sampled estimator |
| L1-S04 | Zhao et al. (2020), *Revisiting Alternative Experimental Settings…* | P1 | Split, candidate sampling, HR/Recall semantics |
| L1-S05 | Tamm et al. (2021), *Quality Metrics in Recommender Systems…* | P1 | Metric-definition ambiguity |
| L1-S06 | Järvelin & Kekäläinen (2002), *Cumulated Gain-based Evaluation…* | P1-M | NDCG foundation |
| L1-S07 | Bradley (1997), *The Use of the Area Under the ROC Curve…* | P1-M | AUC foundation |
| L1-S08 | Cañamares, Castells & Moffat (2020), *Offline evaluation options…* | P1 | Split, candidate set, per-user testing |
| L1-S09 | Dacrema et al. (2021), *A Troubling Analysis of Reproducibility…* | P1 | Faithful reproduction / tuned baselines |
| L1-S10 | Sun et al. (2023), *DaisyRec 2.0…* | P1-T | Rigorous benchmark and seed/hyper-factor controls |
| L1-S11 | Zhao et al. (2022), *RecBole 2.0…* | P1-T | Unified implementation/evaluation toolkit |
| L1-S12 | Jannach & Chen (2026), *Improving Methodological Standards…* | P1 | Current reproducibility and reporting checklist |

## EXCLUDED_SOURCES

- Krichene & Rendle (2022), *On sampled metrics for item recommendation*, CACM, DOI `10.1145/3535335`: verified as a later communication of the KDD 2020 work; do not count as an independent evidence item.
- Li, Jin, Gao & Liu (2020), *On Sampling Top-K Recommendation Evaluation*, KDD, DOI `10.1145/3394486.3403262`: technically sound but excluded from shortlist because v5 prohibits sampled final evaluation; retained only as contradiction context.
- Gunawardana & Shani (2009), *A Survey of Accuracy Evaluation Metrics of Recommendation Tasks*, JMLR: authoritative survey, but superseded for shortlist by direct metric/protocol sources.
- Dacrema, Cremonesi & Jannach (2019), *Are We Really Making Much Progress?*, RecSys, DOI `10.1145/3298689.3347058`: superseded by the broader 2021 TOIS reproduction study.
- Anelli et al. (2021), *Elliot*, SIGIR, DOI `10.1145/3404835.3463245`: valid toolkit paper, but redundant after DaisyRec/RecBole and does not certify a project-specific adapter’s faithfulness.
- BARS (2022), SIGIR, DOI `10.1145/3477495.3531723`; Cornac (2020), JMLR 21(95): useful frameworks but not direct enough for fixed temporal top-N/full-catalog protocol. BARS author metadata also conflicted between project page and paper PDF; do not persist until direct ACM metadata is captured.

## UNRESOLVED

- `macro per-user GAUC`: Bradley supports ordinary AUC only. The per-user, exact-unseen-negative, average-rank-tie, unweighted macro aggregation is a v5 operational definition—not a universal literature definition. It needs unit/property tests and an explicit formula in Methods.
- Hierarchical paired bootstrap with resampling seed occurrences then users is defensible design, but no accepted source establishes this exact three-seed hierarchy as RecSys consensus. Present it as preregistered analysis plan; validate it by simulation/property tests.
- Seen-item masking and deterministic tie-break are essential protocol invariants, not literature-derived claims. Preserve them in the evaluator contract and test receipts.
- No accepted toolkit/repository is “adapter-ready” without pinned commit, environment hash, official-dataset reproduction, and v5 parity tests.

## CLAIM_SOURCE_CARDS

### L1-S01

- **Identity/status:** Walid Krichene, Steffen Rendle (2020), “[On Sampled Metrics for Item Recommendation](https://dl.acm.org/doi/10.1145/3394486.3403226),” KDD 2020, pp. 1748–1757; published; DOI `10.1145/3394486.3403226`. The CACM 2022 version is DOI `10.1145/3535335`.
- **Repository:** none located.
- **Claims supported:** naive sampled ranking metrics need not preserve relative method ordering versus exact metrics; exact calculation is preferred where feasible.
- **Method/task/protocol:** theoretical and empirical analysis of sampled versus global ranking metrics for item recommendation.
- **Metric semantics:** concerns metrics calculated after ranking positives only against sampled negatives, not full catalog.
- **Limitations:** does not prescribe v5’s temporal split, masking, or bootstrap.
- **Mapping/rationale:** `RQ1/H1`, methodology validity; direct support for banning sampled TEST metrics.

### L1-S02

- **Identity/status:** Ruoming Jin, Dong Li, Benjamin Mudrak, Jing Gao, Zhi Liu (2021), “[On Estimating Recommendation Evaluation Metrics under Sampling](https://ojs.aaai.org/index.php/AAAI/article/view/16537),” AAAI 35(5), 4147–4154; published; DOI `10.1609/aaai.v35i5.16537`.
- **Repository:** none identified on official proceeding page.
- **Claims supported:** sampled top-k observations can be used to estimate global metrics under stated estimation assumptions.
- **Method/task/protocol:** weighted-MLE/max-entropy recovery of rank distributions for sampled top-k evaluation.
- **Metric semantics:** estimator evidence—not an assertion that sampled HR/Recall/NDCG equals exact HR/Recall/NDCG.
- **Limitations:** irrelevant to v5 final scoring if full-catalog is feasible; estimator error/assumptions remain.
- **Mapping/rationale:** protocol caveat for `RQ1/H1`; retained to avoid one-sided treatment of sampling evidence.

### L1-S03

- **Identity/status:** Dong Li, Ruoming Jin, Zhenming Liu, Bin Ren, Jing Gao, Zhi Liu (2023), “[Towards Reliable Item Sampling for Recommendation Evaluation](https://ojs.aaai.org/index.php/AAAI/article/view/25561),” AAAI 37(4), 4409–4416; published; DOI `10.1609/aaai.v37i4.25561`.
- **Repository:** none identified on official proceeding page.
- **Claims supported:** naive item sampling has a top-k “blind spot”; adaptive/estimated sampling can improve recovery of global metric estimates.
- **Method/task/protocol:** theoretical and empirical sampling-estimator study.
- **Metric semantics:** reports estimated global top-k performance, not a license to relabel sampled metric values as exact.
- **Limitations:** does not defeat the reason for exact full-catalog evaluation when computationally possible.
- **Mapping/rationale:** `RQ1/H1` validity boundary; records the strongest counterpoint to an absolute anti-sampling claim.

### L1-S04

- **Identity/status:** Wayne Xin Zhao, Junhua Chen, Pengfei Wang, Qi Gu, Ji-Rong Wen (2020), “[Revisiting Alternative Experimental Settings for Evaluating Top-N Item Recommendation Algorithms](https://dl.acm.org/doi/10.1145/3340531.3412095),” CIKM 2020, pp. 2329–2332; published; DOI `10.1145/3340531.3412095`.
- **Repository:** RecBole links this paper as its evaluation reference; no separate verified author repository retained.
- **Claims supported:** split choice, sampled metrics, and domain selection can change comparative results; temporal ordering should be treated explicitly.
- **Method/task/protocol:** eight algorithms across Amazon domains under alternate split/sampling configurations.
- **Metric semantics:** provides top-k Precision, Recall, HR, MAP, AUC and NDCG formulations; HR is all-but-one-oriented in its stated setup.
- **Limitations:** formula/denominator must not be copied blindly into v5’s multi-truth novel-purchase setup.
- **Mapping/rationale:** `RQ1/H1`, external protocol audit for `RQ4/H4`; main source for explicit split/candidate-policy reporting.

### L1-S05

- **Identity/status:** Yan-Martin Tamm, Rinchin Damdinov, Alexey Vasilev (2021), “[Quality Metrics in Recommender Systems: Do We Calculate Metrics Consistently?](https://dl.acm.org/doi/10.1145/3460231.3478848),” RecSys 2021, pp. 708–713; published; DOI `10.1145/3460231.3478848`.
- **Repository:** none verified.
- **Claims supported:** identically named RecSys metrics can differ across papers/libraries; formulas and aggregation require explicit disclosure.
- **Method/task/protocol:** comparison of metric definitions and library implementations.
- **Metric semantics:** direct warning against assuming HR, Recall, NDCG, or AUC are self-defining.
- **Limitations:** diagnostic study; does not select v5 definitions.
- **Mapping/rationale:** `RQ1/H1`; requires formula, eligibility denominator, candidate universe, tie rule, and aggregation to be frozen.

### L1-S06

- **Identity/status:** Kalervo Järvelin, Jaana Kekäläinen (2002), “[Cumulated Gain-based Evaluation of IR Techniques](https://doi.org/10.1145/582415.582418),” *ACM Transactions on Information Systems* 20(4), 422–446; published; DOI `10.1145/582415.582418`.
- **Repository:** none.
- **Claims supported:** DCG/NDCG rank-sensitive, ideal-normalized evaluation foundation.
- **Method/task/protocol:** IR ranking evaluation with graded relevance.
- **Metric semantics:** v5 binary `NDCG@10` is a documented specialization; `IDCG=min(|truth_u|,10)` is a project-level contract.
- **Limitations:** does not define RecSys candidate sets, temporal evaluation, or multi-seed inference.
- **Mapping/rationale:** primary metric-definition anchor for `E1-NDCG`, `E2-COLD`, `E3-WIDE`, `E4-EXT`.

### L1-S07

- **Identity/status:** Andrew P. Bradley (1997), “[The Use of the Area Under the ROC Curve in the Evaluation of Machine Learning Algorithms](https://doi.org/10.1016/S0031-3203(96)00142-2),” *Pattern Recognition* 30(7), 1145–1159; published; DOI `10.1016/S0031-3203(96)00142-2`.
- **Repository:** none.
- **Claims supported:** AUC’s threshold-independent pairwise-ranking interpretation.
- **Method/task/protocol:** general ML classifier evaluation.
- **Metric semantics:** only supports base AUC semantics. v5’s per-user exact AUC, unseen-negative universe, average-rank ties and macro aggregation must be separately specified.
- **Limitations:** not a recommender-specific GAUC source.
- **Mapping/rationale:** supporting metric anchor for `E1-GAUC`; prevents overclaiming that macro GAUC is universally standardized.

### L1-S08

- **Identity/status:** Rocío Cañamares, Pablo Castells, Alistair Moffat (2020), “[Offline evaluation options for recommender systems](https://doi.org/10.1007/s10791-020-09371-3),” *Information Retrieval Journal* 23(4), 387–410; published; DOI `10.1007/s10791-020-09371-3`.
- **Repository:** none.
- **Claims supported:** filtering/splitting, eligible users, unscorable items, full/condensed output lists, metric choice and statistical comparison are coupled design decisions.
- **Method/task/protocol:** methodological analysis with controlled experiments on offline RecSys choices.
- **Metric semantics:** supports user-weighted versus volume-weighted comparison distinction and explicit candidate treatment.
- **Limitations:** does not mandate v5’s exact bootstrap or three seeds.
- **Mapping/rationale:** `RQ1/H1` protocol validity and all external mapping receipts under `RQ4/H4`.

### L1-S09

- **Identity/status:** Maurizio Ferrari Dacrema, Simone Boglio, Paolo Cremonesi, Dietmar Jannach (2021), “[A Troubling Analysis of Reproducibility and Progress in Recommender Systems Research](https://doi.org/10.1145/3434185),” *ACM Transactions on Information Systems* 39(2), Article 20, 1–49; published; DOI `10.1145/3434185`.
- **Repository:** author repository: [RecSys2019_DeepLearning_Evaluation](https://github.com/MaurizioFD/RecSys2019_DeepLearning_Evaluation).
- **Claims supported:** availability of paper/code alone is not faithful reproduction; baseline tuning and reproducible split/preprocessing matter.
- **Method/task/protocol:** reproduction study of neural collaborative-filtering proposals and stronger baselines.
- **Metric semantics:** no metric-definition authority; evidence concerns comparison faithfulness.
- **Limitations:** historical algorithm sample; does not validate project-specific adapters.
- **Mapping/rationale:** `RQ1/H1` methodology; supports Gate T1 official reproduction and exclusion-with-failure-report policy.

### L1-S10

- **Identity/status:** Zhu Sun, Hui Fang, Jie Yang, Xinghua Qu, Hongyang Liu, Di Yu, Yew-Soon Ong, Jie Zhang (2023), “[DaisyRec 2.0: Benchmarking Recommendation for Rigorous Evaluation](https://doi.org/10.1109/TPAMI.2022.3231891),” *IEEE TPAMI* 45(7), 8206–8226; published; DOI `10.1109/TPAMI.2022.3231891`.
- **Repository:** [official DaisyRec-v2.0](https://github.com/recsys-benchmark/DaisyRec-v2.0).
- **Claims supported:** evaluation-chain hyper-factors—including splits, sampling, tuning and initialization—can materially alter conclusions; standardized procedures improve rigor.
- **Method/task/protocol:** review of 141 papers plus benchmark/testbed experiments.
- **Metric semantics:** supports locking the full metric/evaluation chain; not a definition source for v5 GAUC.
- **Limitations:** general top-N benchmark; repo must still be pinned and audited.
- **Mapping/rationale:** `RQ1/H1`, seed-variability reporting, validation-only tuning and adapter acceptance design.

### L1-S11

- **Identity/status:** Wayne Xin Zhao, Yupeng Hou, Xingyu Pan, Chen Yang, Zeyu Zhang, Zihan Lin, Jingsen Zhang, Shuqing Bian, Jiakai Tang, Wenqi Sun, Yushuo Chen, Lanling Xu, Gaowei Zhang, Zhen Tian, Changxin Tian, Shanlei Mu, Xinyan Fan, Xu Chen, Ji-Rong Wen (2022), “[RecBole 2.0: Towards a More Up-to-Date Recommendation Library](https://doi.org/10.1145/3511808.3557680),” CIKM 2022, pp. 4722–4726; published; DOI `10.1145/3511808.3557680`.
- **Repository:** [RUCAIBox/RecBole](https://github.com/RUCAIBox/RecBole).
- **Claims supported:** unified interfaces can support transparent implementation, data loading, setup and evaluation across model packages.
- **Method/task/protocol:** software/library paper, not a comparative efficacy study.
- **Metric semantics:** implementation support only; its configured evaluator must be parity-tested against v5’s formulae/masking/ties.
- **Limitations:** does not prove faithful reproduction of an architecture or satisfy v5 full-catalog contract by default.
- **Mapping/rationale:** adapter fallback for `RQ1–RQ4`; evidence for implementation provenance, not superiority.

### L1-S12

- **Identity/status:** Dietmar Jannach, Li Chen (2026), “[Improving Methodological Standards in Recommender Systems Offline Evaluation](https://doi.org/10.1145/3800587),” *ACM Transactions on Recommender Systems* 4(3), Article 34; published; DOI `10.1145/3800587`.
- **Repository:** none.
- **Claims supported:** fair HPO, frozen train/test boundaries, method-appropriate tests, confidence intervals, hardware disclosure and validated toolkits are methodological requirements.
- **Method/task/protocol:** current methodological standards/checklist for offline RecSys evaluation.
- **Metric semantics:** no replacement for explicit metric formulas; reinforces reporting them.
- **Limitations:** standards paper, not empirical validation of v5’s proposed Hybrid.
- **Mapping/rationale:** strongest current source for `RQ1/H1` validity and `RQ5` reporting; supports but does not certify the proposed bootstrap.

## OVERLAP_FLAGS

- **Architecture lane:** Dacrema, DaisyRec and RecBole overlap baseline selection/adaptation. L1 transfers only reproduction/provenance conditions, not claims about any architecture’s performance.
- **Basket/hybrid lane:** L1’s temporal, candidate and metric contracts apply to BTBR/Apriori studies, but no L1 source establishes H3’s Wide-branch mechanism.
- **Cold/content lane:** metric aggregation and cold-cohort denominators transfer, but no L1 source supports cold-item ⇒ cold-user inference; retain the Stage 1A prohibition.
- **Vietnamese/external lane:** external datasets must receive separate official-protocol and harmonized tables. L1 prohibits pooled raw scores across v5, Amazon-M2, ViEcomRec, or any other dataset.

## CENTRAL_REVIEW_ALERTS

1. Keep `NDCG@10` primary; label HR@10, Recall@10, and macro per-user GAUC with exact formulas. Do not call HR and Recall interchangeable.
2. State “exact full-catalog” only when every eligible user is ranked against the defined full item universe after seen-item masking. Otherwise report a distinct sampled/condensed protocol.
3. The sampling literature is not unanimous: estimators can be useful where exact scoring is impossible. That does not weaken the v5 decision to avoid sampling when full-catalog is feasible.
4. Official reproduction proves adapter/environment parity only. It cannot appear in a harmonized ranking table or substantiate Hybrid superiority.
5. Lock validation selection, candidate policy, split hashes, seed set, tie rule, metric code and baseline registry before TEST. Report all failed seeds/adapters.
6. Do not claim H1–H4 support from literature. Literature supports the evaluation design; only sealed, harmonized artifacts can answer the hypotheses.

ESCALATION_RECOMMENDED: không cần.

