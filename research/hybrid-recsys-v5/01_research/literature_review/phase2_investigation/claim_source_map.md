# Claim–Source Map — Stage 1B Pre-Audit

Status: complete for Introduction/Related Work planning; independent audit pending. Manuscript citation emission is not yet authorized because original full-text locators have not been acquired.

## Status vocabulary

- `SUPPORTED_FOR_FRAMING`: literature supports the bounded conceptual/method claim.
- `CONDITIONAL`: support holds only under stated task/protocol/source conditions.
- `INTERNAL_DESIGN`: the statement is a project definition or preregistered choice, not literature consensus.
- `NOT_RUN`: only sealed experiments may determine the claim.
- `FORBIDDEN`: the claim must not appear in the manuscript.

## Claim map

| Claim ID | Planned section | Bounded claim / allowed wording | Canonical sources | Status | Forbidden extrapolation |
|---|---|---|---|---|---|
| C-INTRO-01 | Introduction | Offline recommender conclusions depend on split, candidate universe, metric definition, aggregation, and baseline/tuning choices. | `zhao2020_alternative_settings`; `tamm2021_metric_consistency`; `canamares2020_offline_options`; `sun2023_daisyrec2` | SUPPORTED_FOR_FRAMING | “Metric names alone guarantee comparability” or raw cross-paper leaderboard claims. |
| C-INTRO-02 | Introduction / Evaluation RW | Naive sampled ranking metrics can disagree with exact/global evaluation; improved estimators exist, but they do not make sampled and exact values interchangeable. | `krichene2020_sampled_metrics`; `li2023_reliable_sampling` | SUPPORTED_FOR_FRAMING | “All sampling is invalid” or “sampled NDCG equals exact NDCG.” |
| C-INTRO-03 | Introduction | Reproducible comparison requires faithful implementations, tuned baselines, frozen protocol choices, and explicit reporting. | `dacrema2021_reproducibility`; `sun2023_daisyrec2`; `jannach2026_methodological_standards`; `zhao2022_recbole2` | SUPPORTED_FOR_FRAMING | “Using a public repository automatically proves faithful reproduction.” |
| C-RW-CF-01 | Collaborative/deep RW | ItemCF, BPR, NCF, and graph CF instantiate distinct neighborhood, pairwise-ranking, nonlinear-interaction, and propagation assumptions. | `sarwar2001_itemcf`; `rendle2009_bpr`; `he2017_ncf`; `he2020_lightgcn` | SUPPORTED_FOR_FRAMING | Any architecture-age or source-native-score claim of expected superiority on v5. |
| C-RW-TOWER-01 | Collaborative/deep RW | Independent encoders/two-tower matching are established retrieval patterns; candidate generation, ranking, and negative-sampling choices must be specified separately. | `huang2013_dssm`; `covington2016_youtube`; `yi2019_ndr` | SUPPORTED_FOR_FRAMING | Calling the project “two-stage” before freezing candidate count, retrieval boundary, fusion point, and ranker. |
| C-RW-WIDE-01 | Collaborative/deep RW | Wide & Deep motivates explicit memorization plus embedding-based generalization; DeepFM supplies an adjacent learned-interaction contrast. | `cheng2016_wide_deep`; `guo2017_deepfm` | SUPPORTED_FOR_FRAMING | “Wide & Deep proves Apriori rules improve relevance” or equating CTR/online outcomes with v5 top-k metrics. |
| C-RW-GRAPH-01 | Graph-contrastive RW | LightGCN, SimGCL, XSimGCL, and LightGCL are credible collaborative controls under sparse interaction graphs. | `he2020_lightgcn`; `yu2022_simgcl`; `yu2024_xsimgcl`; `cai2023_lightgcl` | SUPPORTED_FOR_FRAMING | Treating sparse-graph robustness as evidence for a zero-interaction cold item. |
| C-RW-SEQ-01 | Sequential/basket RW | SASRec and BERT4Rec are canonical but task/protocol-specific sequential baselines; their reported metrics are not apples-to-apples with v5. | `kang2018_sasrec`; `sun2019_bert4rec`; `gusak2025_time_split` | SUPPORTED_FOR_FRAMING | Copying sampled/leave-one-out results into a v5 comparison table. |
| C-RW-RULE-01 | Sequential/basket RW | Apriori defines support/confidence and frequent-rule mining; direct rule recommenders provide precedent for mining on training transactions and evaluating separately. | `agrawal1994_apriori`; `ghoshal2014_multi_item_rules` | SUPPORTED_FOR_FRAMING | “Apriori is a ranking model” or selecting support/confidence using TEST. |
| C-RW-HYBRID-01 | Sequential/basket RW | Rule/association, preference, popularity, transition, and collaborative components have been fused and ablated in prior systems, motivating—without confirming—complementarity. | `liu2009_hybrid_seq_cf`; `peng2022_ham`; `peng2023_m2`; `cheng2016_wide_deep` | SUPPORTED_FOR_FRAMING | “Prior work demonstrates the proposed decoupled Apriori Wide branch improves v5.” |
| C-RW-NBR-01 | Sequential/basket RW | Repeat and exploration/novel behavior can be confounded by aggregate next-basket accuracy; novelty composition and cohort coverage should be reported. | `li2023_nbr_reality`; `li2023_repetition_exploration`; `li2023_mask_swap` | SUPPORTED_FOR_FRAMING | “An aggregate NDCG gain necessarily improves novel-item discovery.” |
| C-RW-COLD-01 | Cold/content RW | Content or distillation can provide item-side signal when collaborative item history is missing or sparse. | `volkovs2017_dropoutnet`; `du2020_mtpr`; `wei2021_clcrec`; `huang2023_aldi` | SUPPORTED_FOR_FRAMING | Cold-item → cold-user transfer; or stating H2 is already supported. |
| C-RW-TRANSFER-01 | Cold/content RW | UniSRec, VQ-Rec, and AlphaRec motivate transferable/text-aware item representations; SBERT supports embedding construction only. | `hou2022_unisrec`; `hou2023_vqrec`; `sheng2025_alpharec`; `reimers2019_sbert` | CONDITIONAL | “SBERT solves cold-item recommendation” or treating an SBERT substitution as faithful AlphaRec/UniSRec reproduction. |
| C-DATA-VN-01 | Vietnamese/resources RW | Reviewed Vietnamese resources cover e-commerce reviews, food metadata/ratings, and hotel reviews, but not the complete basket/order/session-plus-content contract. | `tran2024_viecomrec`; `tran2024_vietnamese_food`; `nguyen2026_vihorec` | CONDITIONAL | “No Vietnamese recommendation datasets exist,” “first Vietnamese recommender dataset,” or treating reviews as verified purchases. |
| C-DATA-EXT-01 | External resources RW / Methods | Text-rich datasets often lack verified orders/baskets, while order/basket datasets often lack item content or persistent users; this is a real compatibility tradeoff. | `jin2023_amazon_m2`; `normann2023_otto`; `robinson2024_relbench`; `completejourney_resource` | SUPPORTED_FOR_FRAMING | Silently fabricating baskets/content or changing the model/task and retaining the “full Hybrid” label. |
| C-H4-01 | Introduction / Methods | No reviewed external dataset is unconditionally strict-H4-ready; Complete Journey and Coveo are conditional candidates, whereas Amazon-M2 is architecture-transfer evidence. | `completejourney_resource`; `tagliabue2021_coveo`; `jin2023_amazon_m2` | CONDITIONAL | “External dataset selected,” “H4 replicated,” or “openly licensed” before exact revision/task/rights gates pass. |
| C-BENCH-01 | Introduction / Methods | Official-protocol reproduction and harmonized comparison are separate evidence families; raw metrics across datasets or pipelines must remain in separate tables. | `dacrema2021_reproducibility`; `sun2023_daisyrec2`; `canamares2020_offline_options`; Stage 1A methodology | SUPPORTED_FOR_FRAMING + INTERNAL_DESIGN | Any direct numerical ranking between paper-native and v5 results. |
| C-RQ3-COHORT-01 | Methods / Limitations | If cohort membership uses the held-out consequent, call it a “train-mined rule-aligned evaluation cohort,” not a purely train-defined cohort; freeze its builder before TEST. | `agrawal1994_apriori`; `li2023_nbr_reality`; Stage 1A/L3 central alert | INTERNAL_DESIGN | Claiming an outcome-labelled cohort is defined entirely from training data. |
| C-EFFICIENCY-01 | Introduction / Systems context | Retrieval/ranking separation motivates systems analysis, but deployment readiness requires fixed-runner latency/throughput/memory gates after accuracy passes. | `covington2016_youtube`; Stage 1A RQ5 | INTERNAL_DESIGN | “Lightweight,” “real-time,” or “deployment-ready” before sealed RQ5 measurements. |
| C-NOVELTY-01 | Introduction / Related Work positioning | The defensible novelty target is controlled integration and evaluation of complementary signals under one harmonized protocol, contingent on experimental support—not invention of Two-Tower, Wide & Deep, Apriori, cold-item, or hybrid recommendation. | `cheng2016_wide_deep`; `liu2009_hybrid_seq_cf`; `ghoshal2014_multi_item_rules`; `volkovs2017_dropoutnet` | CONDITIONAL | “First hybrid recommender,” “first Apriori/deep hybrid,” or any absolute novelty claim without a dedicated novelty search. |
| C-RESULT-01 | All manuscript sections | H1–H4 and all superiority/mechanism/external-replication claims are currently NOT_RUN; literature supports rationale and design only. | Stage 1A experiment provenance; all five lane alerts | NOT_RUN | Any benchmark number, pass/fail verdict, or expected win written as an observed result. |

## Coverage by paper section

- Introduction: C-INTRO-01–03, C-H4-01, C-BENCH-01, C-NOVELTY-01, C-RESULT-01.
- Related Work: C-RW-CF-01 through C-DATA-EXT-01.
- Methods guardrails: C-BENCH-01, C-RQ3-COHORT-01, C-EFFICIENCY-01.
- Results: no literature-backed result claim is authorized; only sealed experiment artifacts may populate this section.

## Locator status

Every source has a verified identity/source pointer, but no local original-PDF acquisition was performed. Therefore this map authorizes claim planning, not production citations. Stage 2 must acquire the core 18–24 Related Work sources and attach page/section/abstract locators before prose is finalized.

