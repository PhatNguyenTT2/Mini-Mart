---
lane: L2
task_id: 019ffb38-af73-7293-a6d0-8964c715c886
model: 5.6 Tera / XHigh
status: complete
captured_at: 2026-08-13
provenance: verbatim task final handoff
---

# L2 raw literature-search handoff

Hoàn tất lane L2 theo ARS lit-review, read-only: 20 candidates screened, 12 nguồn P1 được shortlist. Không có file nào bị sửa. Không nguồn nào chứng minh H1/H2/H3; chúng chỉ hỗ trợ framing kiến trúc và comparator design.

## SEARCH_LOG

- Ngày tìm kiếm: 2026-08-13.
- Scope: ItemCF/ItemKNN, BPR-MF, NCF/DeepFM, Wide & Deep, Two-Tower retrieval/ranking, LightGCN; ưu tiên 2022–2026 nhưng giữ nguồn nền tảng cần thiết.
- Nguồn truy vấn: proceedings/DOI pages, author-hosted primary PDFs, Google Research, IJCAI, ICLR/OpenReview, official author repositories.
- Queries chính: exact-title + DOI cho `Wide & Deep`, `YouTube Recommendations`, `BPR`, `NCF`, `DeepFM`, `LightGCN`, `DirectAU`, `LightGCL`, `AlphaRec`, `UniSRec`, `SimGCL`, `XSimGCL`, `LLaRA`, `A-LLMRec`.
- Screening: 20 candidate → 12 accepted P1 → 8 excluded/hand-off do trùng lặp hoặc thuộc lane khác.
- Đây là targeted review, không phải systematic review/PRISMA.
- Quy tắc evidence: P1 = primary peer-reviewed paper/proceedings; mọi P1 chỉ là architecture/source-protocol evidence. `official-protocol reproduction = NONE`; `harmonized-v5 result = NONE`.

## ACCEPTED_SOURCES

| ID | Nguồn | Vai trò L2 |
|---|---|---|
| L2-01 | Sarwar et al. (2001), Item-based CF | ItemCF/ItemKNN comparator |
| L2-02 | Rendle et al. (2009), BPR | Pairwise implicit-ranking comparator |
| L2-03 | Huang et al. (2013), DSSM | Khung independent encoders/two-tower |
| L2-04 | Cheng et al. (2016), Wide & Deep | Memorization–generalization framing |
| L2-05 | Covington et al. (2016), YouTube DNN | Candidate generation vs ranking |
| L2-06 | He et al. (2017), NCF | Deep CF comparator |
| L2-07 | Guo et al. (2017), DeepFM | Learned low-/high-order interactions |
| L2-08 | Yi et al. (2019), NDR | Two-tower retrieval with sampled-negative caveat |
| L2-09 | He et al. (2020), LightGCN | Graph architectural comparator |
| L2-10 | Wang et al. (2022), DirectAU | Modern objective/representation comparator |
| L2-11 | Cai et al. (2023), LightGCL | Modern graph-contrastive comparator |
| L2-12 | Sheng et al. (2025), AlphaRec | Recent text-representation/CF comparator |

## EXCLUDED_SOURCES

- `DESHPANDE2004_ITEMTOPN` — [Deshpande & Karypis, 2004](https://doi.org/10.1145/963770.963776), *Item-based top-N recommendation algorithms*: verified P1, but redundant with L2-01 for this bounded lane.
- `WANG2017_DCN` — [Wang et al., 2017](https://www.adkdd.org/papers/deep-%26-cross-network-for-ad-click-predictions/2017), *Deep & Cross Network for Ad Click Predictions*, DOI `10.1145/3124749.3124754`: CTR-specific adjacent architecture; lower direct relevance than Wide & Deep + DeepFM.
- `MAO2021_SIMPLEX` — [Mao et al., 2021](https://doi.org/10.1145/3459637.3482297), *SimpleX*: valid strong CF baseline, but not necessary once BPR, NCF, LightGCN, and DirectAU are retained.
- `YU2022_SIMGCL` — *Are Graph Augmentations Necessary?: Simple Graph Contrastive Learning for Recommendation*, SIGIR 2022, DOI `10.1145/3477495.3531937`: hand off to graph-contrastive lane.
- `YU2023_XSIMGCL` — [Yu et al., 2023](https://arxiv.org/abs/2209.02544), *XSimGCL*, IEEE TKDE, DOI `10.1109/TKDE.2023.3288135`: hand off to graph-contrastive lane.
- `HOU2022_UNISREC` — [Hou et al., 2022](https://arxiv.org/abs/2206.05941), *Towards Universal Sequence Representation Learning for Recommender Systems* / UniSRec, KDD 2022, DOI `10.1145/3534678.3539381`: hand off to content/transfer lane.
- `LIAO2024_LLARA` — [Liao et al., 2024](https://arxiv.org/abs/2312.02445), *LLaRA*, SIGIR 2024, DOI `10.1145/3626772.3657690`: LLM/sequential scope; optional compute tier.
- `KIM2024_ALLMREC` — [Kim et al., 2024](https://arxiv.org/abs/2404.11343), *A-LLMRec*, KDD 2024, DOI `10.1145/3637528.3671931`: LLM/content lane; not a mandatory L2 architecture source.

## UNRESOLVED

- Direct ACM/DOI endpoints returned HTTP 403 in this environment for several records. Title, author, venue, and DOI strings were cross-checked against primary PDFs, official venue pages, or author/organization records; DOI redirect resolution itself remains `UNVERIFIED_BY_RUNTIME`.
- No peer-reviewed 2026 L2 source was promoted. This is not evidence that none exists; it is a search-boundary result.
- For the proposed “decoupled Wide-and-Deep Two-Tower Hybrid,” the inputs do not yet pin: tower inputs, independent-encoder constraint, retrieval candidate count, fusion location, ranking stage, or training loss. Therefore it cannot yet be mapped faithfully to either Wide & Deep or a two-stage retrieval system.
- No accepted source provides a public official reproduction receipt or harmonized-v5 result for this project.

## CLAIM_SOURCE_CARDS

### L2-01 — `SARWAR2001_ITEMCF`

- Full identity: Badrul Sarwar, George Karypis, Joseph A. Konstan, and John Riedl. *Item-based Collaborative Filtering Recommendation Algorithms*. WWW 2001. DOI: [`10.1145/371920.372071`](https://doi.org/10.1145/371920.372071).
- Repository: none verified; primary archival paper exists through the GroupLens/WWW record.
- Tier/status: P1; foundational; publication identity verified.
- Claims supported: ItemCF constructs item–item similarity from interaction data and is a legitimate neighborhood comparator for RQ1.
- Method/task/protocol: item-based collaborative filtering; source-native recommendation evaluation, not v5 temporal novel-purchase full-catalog evaluation.
- Metric semantics: source-native quality/efficiency measures only; no raw metric is transferable.
- Limitations: interaction-only; does not establish cold-item benefit, Wide-branch value, or superiority under v5.
- Mapping/rationale: RQ1 comparator registry; include because ItemCF is mandatory and conceptually distinct from latent/deep models.

### L2-02 — `RENDLE2009_BPR`

- Full identity: Steffen Rendle, Christoph Freudenthaler, Zeno Gantner, and Lars Schmidt-Thieme. *BPR: Bayesian Personalized Ranking from Implicit Feedback*. UAI 2009, pp. 452–461. [Official proceedings listing](https://www.auai.org/uai2009/papers.html); no DOI identified.
- Repository: no author-maintained implementation verified in this lane.
- Tier/status: P1; foundational.
- Claims supported: BPR-Opt formalizes pairwise personalized ranking from implicit feedback; it supports a method-faithful BPR-MF objective.
- Method/task/protocol: pairwise preference learning for item recommendation from implicit feedback.
- Metric semantics: optimization criterion, not a v5 metric contract; does not license claims based on paper-reported scores.
- Limitations: does not specify the project’s full-catalog masking, temporal split, or hierarchical inference.
- Mapping/rationale: RQ1 baseline architecture/objective; include because BPR-MF is mandatory in the planned suite.

### L2-03 — `HUANG2013_DSSM`

- Full identity: Po-Sen Huang, Xiaodong He, Jianfeng Gao, Li Deng, Alex Acero, and Larry Heck. *Learning Deep Structured Semantic Models for Web Search using Clickthrough Data*. CIKM 2013, pp. 2333–2338. DOI: [`10.1145/2505515.2505665`](https://doi.org/10.1145/2505515.2505665).
- Repository: none verified.
- Tier/status: P1; foundational, cross-domain retrieval evidence.
- Claims supported: independently encoded query/document representations provide a defensible architectural antecedent for two-tower matching.
- Method/task/protocol: clickthrough web-search matching, not retail recommendation.
- Metric semantics: search-native evaluation; no recommender metric may be imported.
- Limitations: not evidence that a two-tower retail model is superior, nor evidence for an Apriori Wide branch.
- Mapping/rationale: theoretical positioning for the independent Deep/two-tower baseline; RQ1 only.

### L2-04 — `CHENG2016_WIDENDEEP`

- Full identity: Heng-Tze Cheng, Levent Koc, Jeremiah Harmsen, Tal Shaked, Tushar Chandra, Hrishi Aradhye, Glen Anderson, Greg Corrado, Wei Chai, Mustafa Ispir, Rohan Anil, Zakaria Haque, Lichan Hong, Vihan Jain, Xiaobing Liu, and Hemal Shah. *Wide & Deep Learning for Recommender Systems*. DLRS 2016. DOI: [`10.1145/2988450.2988454`](https://doi.org/10.1145/2988450.2988454).
- Repository: no immutable author repository confirmed here.
- Tier/status: P1; foundational.
- Claims supported: explicit cross features can serve memorization while a deep component generalizes through embeddings; jointly trained branches are a valid framing.
- Method/task/protocol: Google Play recommendation with online acquisition outcome.
- Metric semantics: online app-acquisition evidence; not interchangeable with v5 `NDCG@10`, `HR@10`, or GAUC.
- Limitations: the source does not use Apriori rules; it cannot support “Apriori Wide improves relevance.” That requires H3’s frozen cohort and ablation.
- Mapping/rationale: theoretical framework and RQ3 hypothesis motivation, never H3 confirmation.

### L2-05 — `COVINGTON2016_YOUTUBE`

- Full identity: Paul Covington, Jay Adams, and Emre Sargin. *Deep Neural Networks for YouTube Recommendations*. RecSys 2016, pp. 191–198. DOI: [`10.1145/2959100.2959190`](https://doi.org/10.1145/2959100.2959190).
- Repository: none verified.
- Tier/status: P1; foundational industrial-system paper.
- Claims supported: candidate generation and ranking are separate design stages with different computational roles.
- Method/task/protocol: large-scale video recommendation; source-specific production architecture and operational outcomes.
- Metric semantics: source-native offline/online system evidence only.
- Limitations: v5 presently states full-catalog scoring, not an ANN retrieval-plus-ranker protocol. Do not label the project “two-stage” without a frozen retrieval-stage contract.
- Mapping/rationale: RQ1 architecture positioning and RQ5 systems framing; not comparative performance evidence.

### L2-06 — `HE2017_NCF`

- Full identity: Xiangnan He, Lizi Liao, Hanwang Zhang, Liqiang Nie, Xia Hu, and Tat-Seng Chua. *Neural Collaborative Filtering*. WWW 2017, pp. 173–182. DOI: [`10.1145/3038912.3052569`](https://doi.org/10.1145/3038912.3052569). [Author repository](https://github.com/hexiangnan/neural_collaborative_filtering).
- Tier/status: P1; foundational.
- Claims supported: replacing a fixed MF inner product with a learned nonlinear interaction function is a defensible independent deep-CF comparator.
- Method/task/protocol: implicit-feedback top-N recommendation with the source’s own negative-sampling/evaluation setup.
- Metric semantics: reported HR/NDCG are source-protocol-specific and must not be compared with v5 full-catalog measures.
- Limitations: no item text, rule feature, temporal split, or cold-item guarantee follows from the paper.
- Mapping/rationale: RQ1 independent Deep baseline; supports architecture diversity, not expected superiority.

### L2-07 — `GUO2017_DEEPFM`

- Full identity: Huifeng Guo, Ruiming Tang, Yunming Ye, Zhenguo Li, and Xiuqiang He. *DeepFM: A Factorization-Machine based Neural Network for CTR Prediction*. IJCAI 2017, pp. 1725–1731. DOI: [`10.24963/ijcai.2017/239`](https://doi.org/10.24963/ijcai.2017/239). [Official proceedings record](https://www.ijcai.org/proceedings/2017/239).
- Repository: no author repository confirmed in this lane.
- Tier/status: P1; foundational.
- Claims supported: low-order and high-order feature interactions can be learned from shared raw inputs without manually specified cross features.
- Method/task/protocol: CTR prediction on benchmark and commercial data.
- Metric semantics: CTR/ranking-classification semantics, not top-k recommendation semantics.
- Limitations: DeepFM is an adjacent feature-interaction comparator, not a direct v5 baseline unless a method-faithful adapter and task mapping are specified.
- Mapping/rationale: positioning and architecture contrast for RQ1/RQ3.

### L2-08 — `YI2019_NDR`

- Full identity: Xinyang Yi, Ji Yang, Lichan Hong, Derek Zhiyuan Cheng, Lukasz Heldt, Aditee Ajit Kumthekar, Zhe Zhao, Li Wei, and Ed Chi. *Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations*. RecSys 2019. DOI: [`10.1145/3298689.3346996`](https://doi.org/10.1145/3298689.3346996). [Google Research primary record](https://research.google/pubs/sampling-bias-corrected-neural-modeling-for-large-corpus-item-recommendations/).
- Repository: none verified.
- Tier/status: P1; foundational two-tower retrieval evidence.
- Claims supported: in-batch negatives can bias two-tower retrieval under skewed item distributions; sampling design is architectural/protocol-relevant.
- Method/task/protocol: Neural Deep Retrieval for large-corpus YouTube retrieval with item features and online testing.
- Metric semantics: source-native offline and A/B evidence; no transferable metric.
- Limitations: reinforces, rather than relaxes, the need to define project negative sampling and retrieval protocol.
- Mapping/rationale: RQ1 two-tower design and RQ4 adapter requirements.

### L2-09 — `HE2020_LIGHTGCN`

- Full identity: Xiangnan He, Kuan Deng, Xiang Wang, Yan Li, Yongdong Zhang, and Meng Wang. *LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation*. SIGIR 2020. DOI: [`10.1145/3397271.3401063`](https://doi.org/10.1145/3397271.3401063). [Author repository](https://github.com/kuandeng/LightGCN).
- Tier/status: P1; foundational graph comparator.
- Claims supported: linear neighborhood propagation on the user–item graph can be a meaningful GCN-based collaborative comparator.
- Method/task/protocol: top-k CF over source-native public interaction datasets.
- Metric semantics: native Recall/NDCG-style top-k protocol only; no raw-result transfer.
- Limitations: interaction graph alone does not test text-aware cold-item transfer or rule memorization.
- Mapping/rationale: mandatory RQ1 comparator; RQ2 collaborative-only secondary comparator.

### L2-10 — `WANG2022_DIRECTAU`

- Full identity: Chenyang Wang, Yuanqing Yu, Weizhi Ma, Min Zhang, Chong Chen, Yiqun Liu, and Shaoping Ma. *Towards Representation Alignment and Uniformity in Collaborative Filtering*. KDD 2022, pp. 1816–1825. DOI: [`10.1145/3534678.3539253`](https://doi.org/10.1145/3534678.3539253). [Author repository](https://github.com/THUwangcy/DirectAU).
- Tier/status: P1; recent.
- Claims supported: representation geometry and learning objective can affect CF outcomes independently of a more complex encoder.
- Method/task/protocol: matrix-factorization-based CF evaluated on source-native public datasets.
- Metric semantics: source-native top-k evaluation only.
- Limitations: does not establish that a wide/deep fusion beats BPR or LightGCN on v5; it warns against treating encoder complexity as the sole explanation.
- Mapping/rationale: RQ1 baseline-selection rationale and a counterweight to architectural-age/superiority claims.

### L2-11 — `CAI2023_LIGHTGCL`

- Full identity: Xuheng Cai, Chao Huang, Lianghao Xia, and Xubin Ren. *LightGCL: Simple yet Effective Graph Contrastive Learning for Recommendation*. ICLR 2023. [Official OpenReview record](https://openreview.net/forum?id=FKXVK9dyMM); [author repository](https://github.com/HKUDS/LightGCL).
- Tier/status: P1; recent.
- Claims supported: graph-contrastive augmentation can incorporate global collaborative structure, giving a modern comparator beyond LightGCN.
- Method/task/protocol: graph recommendation with source-native benchmark datasets.
- Metric semantics: benchmark top-k results are source-native only.
- Limitations: overlap with graph lane; claims about robustness to sparsity are not a v5 cold-item result.
- Mapping/rationale: RQ1 modern architectural comparator, subject to adapter/reproduction gate.

### L2-12 — `SHENG2025_ALPHAREC`

- Full identity: Leheng Sheng, An Zhang, Yi Zhang, Yuxin Chen, Xiang Wang, and Tat-Seng Chua. *Language Representations Can be What Recommenders Need: Findings and Potentials*. ICLR 2025. [Official proceedings record](https://proceedings.iclr.cc/paper_files/paper/2025/hash/e4bab1843c8d5a69f5abfd0824593493-Abstract-Conference.html); [author repository](https://github.com/LehengTHU/AlphaRec).
- Tier/status: P1; recent.
- Claims supported: item text representations can be mapped and combined with CF components, making a recent text-aware comparator relevant to item-side coldness.
- Method/task/protocol: source-native multi-dataset CF and zero-shot analysis.
- Metric semantics: source-native top-k/zero-shot protocol; not v5 evidence.
- Limitations: architecture includes language representations, graph convolution, and contrastive loss; it is not an independent Deep two-tower control.
- Mapping/rationale: RQ2 comparator and RQ4 adapter input-provenance requirements; overlap with content/transfer lane.

## OVERLAP_FLAGS

| Source/finding | Overlap | L2 handling |
|---|---|---|
| LightGCN, SimGCL, XSimGCL, LightGCL | Graph/contrastive lane | L2 retains only LightGCN and LightGCL as architecture comparators; graph-specific claims hand off. |
| UniSRec, AlphaRec | Content/transfer and cold-item lane | L2 retains AlphaRec only as a modern comparator; cold/transfer efficacy claims require that lane. |
| Wide & Deep + Apriori project branch | Basket/rule/hybrid lane | Wide & Deep supports the abstract framing only; it is not Apriori evidence. |
| YouTube/NDR two-stage systems | Evaluation/systems lane | Relevant only after the project freezes a retrieval/ranking boundary and serving workload. |
| LLaRA, A-LLMRec | LLM/content lane | Excluded from L2 shortlist; optional-compute status remains unchanged. |

## CENTRAL_REVIEW_ALERTS

- `H1`: no literature source can establish superiority. It remains a sealed v5, metric-specific locked-baseline comparison.
- `H3`: the most important claim boundary is strict: Wide & Deep supports memorization/generalization framing, but not that train-mined Apriori rules add relevance. Only the preregistered no-Wide ablation on the rule-aligned cohort can support this.
- `Two-Tower`: central review should require a concrete architecture contract before Stage 1E—retrieval tower inputs, item-tower inputs, matching score, negative-sampling scheme, fusion point, candidate count, and whether a separate ranker exists.
- `Metrics`: do not carry over HR/NDCG/AUC values from NCF, LightGCN, LightGCL, AlphaRec, or other source-native protocols. Wide & Deep and DeepFM are CTR/online-ranking evidence, not top-k evidence.
- `Comparator interpretation`: architecture age and paper-reported wins are not superiority evidence. DirectAU and SimpleX-type results reinforce the need for method-faithful objectives, tuning budgets, and locked shared evaluation.
- `Provenance`: official author repositories found for NCF, LightGCN, DirectAU, LightGCL, and AlphaRec. Their immutable revision, license, data mapping, and reproduction tolerance remain Stage 1E gates.
- `ESCALATION_RECOMMENDED: NO` for this discovery/screening lane.

