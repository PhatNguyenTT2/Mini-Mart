# L2 Recommender Architectures — Phase 2 Remediation R1 Investigation Report

Project: `hybrid-recsys-v5`  
Stage: `1B`  
Lane: `L2 — Recommender Architectures`  
Research cutoff: `2026-08-14`  
Execution date: `2026-08-14` (Asia/Saigon)  
ARS phase: Deep Research Phase 2 investigation  
Local-gate verdict: **PASS**

## Phase boundary

This is an evidence inventory, source-verification, acquisition, and architecture-contract handoff. It does not write synthesis, Introduction, Related Work, hypotheses, benchmark results, or manuscript prose. Source-native results are not transported to dataset v5. The prior L2 lane was treated only as a candidate index.

Writes are confined to `research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase2_investigation/lanes/L2/`.

## Outcome and counts

| Measure | Count |
|---|---:|
| Old candidates dispositioned | 20/20 |
| Old candidates retained | 12 |
| Old candidates removed | 8 |
| Old candidates replaced | 0 |
| Old candidates moved to resource registry | 0 |
| New gap-search records screened | 15 |
| New records included | 2 |
| New records excluded | 13 |
| Canonical scholarly records | 14 |
| Independent publication/version families | 14 |
| Operational resources in scholarly corpus | 0 |
| Full artifacts lawfully acquired and inspected | 14/14 |
| Original-content locators ready | 14/14 |
| Audit-core candidates acquired and locator-ready | 5/5 |
| Claim cards | 8 |
| Exclusion decisions recorded | 21 |

The two gap-search additions are the final ICLR 2025 record for [ContextGNN](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1adcaf835e6987d8ae06f246832cf27c-Abstract-Conference.html) and the DOI-linked WWW 2025 record for [T2Diff](https://doi.org/10.1145/3696410.3714829). They are retained as recent controls on pair-agnostic two-tower retrieval, not as evidence of a v5 ranking.

## Inclusion and exclusion criteria

The same criteria were applied to old and new candidates:

1. Direct relevance to required L2 families or a necessary architecture, objective, stage-role, or evaluation-contract boundary.
2. Canonical identity and metadata resolvable to a publisher, proceedings, official venue, author, or repository source-of-record.
3. Lawful full artifact available for original-content inspection when a source is retained for a production-intended claim.
4. Incremental claim-level value after publication/version-family and method-lineage deduplication.
5. Architecture assumptions, inputs, objective, output role, and evaluation contract can be bounded without transferring a source-native result to v5.
6. No operational resource is promoted to a scholarly record and no year is fabricated.

Exclusions were made for scope, redundant coverage, unstable/withdrawn status, optional LLM/content compute, incompatible extra inputs, or lack of incremental claim value. No retained record was included to inflate a count.

## Old-lane disposition audit

All 20 old candidates received exactly one locked disposition in `disposition_log.json`: 12 `RETAIN`, 8 `REMOVE`, 0 `REPLACE`, and 0 `MOVE_TO_RESOURCE_REGISTRY`.

The material change from the prior lane is `YU2022_SIMGCL`: it is retained because the remediation contract explicitly requires graph/contrastive controls. `SHENG2025_ALPHAREC` is removed because content/text transfer is owned by L4. The remaining removals are either out of lane or redundant after the required architecture families are covered.

## Reproducible gap-search protocol

### Search environment and filters

- Search date: `2026-08-14`.
- Cutoff: publication or public record available no later than `2026-08-14`.
- Sites/databases: ACM Digital Library/DOI, OpenReview, ICLR proceedings, PMLR, NeurIPS proceedings, Google Research, IJCAI proceedings, UAI proceedings, arXiv, Crossref, OpenAlex, Semantic Scholar, DBLP, and general web search restricted to primary/official domains when possible.
- Language: English.
- Date range: 1900–2026 for canonical identity lookups; 2022–2026 prioritized for gap discovery.
- Document/status filter: final peer-reviewed proceedings preferred; preprints/submissions screened but excluded when unstable or when no incremental value existed.
- Topical filter: ItemCF/ItemKNN, pairwise implicit ranking/BPR-MF, NCF/DeepFM, dual/two-tower retrieval, candidate generation versus ranking, Wide & Deep, LightGCN, graph contrastive controls, objectives, and evaluation contracts.
- Screening unit: unique work/version family, not URL or index record.
- Search-engine totals were not reported because result totals are dynamic and unreliable. Counts below are manually deduplicated visible candidate records actually screened.

### Exact queries

Gap discovery:

1. `site:dl.acm.org recommender systems two-tower candidate generation ranking 2022 2023 2024 2025 2026`
2. `site:openreview.net recommender graph contrastive LightGCN 2022 2023 2024 2025 2026`
3. `site:arxiv.org recommender two-tower retrieval ranking 2024 2025 2026`
4. `site:proceedings.mlr.press recommender graph contrastive 2024 2025 2026`
5. `site:openreview.net/forum recommender systems collaborative filtering ICLR 2024 2025 2026 two-tower`
6. `site:dl.acm.org/doi recommender retrieval two tower RecSys 2024 2025`
7. `site:research.google/pubs recommender two tower retrieval ranking 2024 2025 2026`
8. `site:proceedings.iclr.cc recommender collaborative filtering 2024 2025 graph`
9. `"ContextGNN: Beyond Two-Tower Recommendation Systems" official ICLR 2025`
10. `"Unleashing the Potential of Two-Tower Models" DOI WWW 2025`
11. `"LightGCL: Simple yet Effective Graph Contrastive Learning for Recommendation" official ICLR 2023`
12. `"Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations" official Google Research`

Core identity and artifact lookups:

13. `"Item-based Collaborative Filtering Recommendation Algorithms" Sarwar official PDF`
14. `"BPR: Bayesian Personalized Ranking from Implicit Feedback" official PDF UAI 2009`
15. `"LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation" official PDF`
16. `"Deep Neural Networks for YouTube Recommendations" official PDF`
17. `"Wide & Deep Learning for Recommender Systems" official PDF authors`
18. `"Neural Collaborative Filtering" official PDF authors WWW 2017`
19. `"DeepFM: A Factorization-Machine based Neural Network for CTR Prediction" official IJCAI PDF`
20. `"Towards Representation Alignment and Uniformity in Collaborative Filtering" official PDF`
21. `site:dl.acm.org/doi "Unleashing the Potential of Two-Tower Models"`
22. `site:dblp.org "Unleashing the Potential of Two-Tower Models"`
23. `site:thewebconf.org "Unleashing the Potential of Two-Tower Models" 2025`
24. `"Unleashing the Potential of Two-Tower Models" "10.1145"`
25. `"Are Graph Augmentations Necessary?" "Simple Graph Contrastive Learning for Recommendation" arXiv`
26. `"Learning Deep Structured Semantic Models for Web Search using Clickthrough Data" official PDF Microsoft`
27. `"Towards Representation Alignment and Uniformity in Collaborative Filtering" arxiv PDF`
28. `"Neural Collaborative Filtering" arxiv PDF 1708.05031`

Exclusion/status and metadata resolution:

29. `site:openreview.net ICLR recommender "RHGCL"`
30. `site:proceedings.neurips.cc recommender "CGI" graph contrastive`
31. `site:proceedings.mlr.press recommendation "KPCL"`
32. `site:openreview.net ICLR 2026 "two tower" recommendation theoretical paradigm`
33. `recommender "HMCF" 2025 official`
34. `recommender "LT-TTD" arXiv 2505.04434`
35. `recommender "LGHRec" ICLR 2026 OpenReview`
36. `recommender "GRank" arXiv 2510.15299`
37. `"Textual Graph Contrastive Learning" "Dataset Recommendation"`
38. `"The Case Against Generation" retrieval recommendation arXiv`
39. `"InteractRank" pre-ranking arXiv`
40. `"MixRec" WWW 2025 recommendation`
41. `site:dl.acm.org "CALRec: Contrastive Alignment of Generative LLMs for Sequential Recommendation"`
42. `"CALRec" "Contrastive Alignment" recommendation 2024`

### Screening flow

- Unique new work/version families enumerated from primary/official result cards: 15.
- Title, abstract, and status records screened: 15.
- Included for full lawful artifact acquisition and inspection: 2.
- Excluded after title/abstract/status screening: 13.
- Included: ContextGNN and T2Diff.
- Every excluded record has an individual decision in `exclusion_log.json`.
- Core and retained-candidate lookup queries were verification/acquisition operations and were not double-counted as new gap candidates.

### Search and acquisition failures

- Semantic Scholar returned HTTP 429 for Rendle 2009, LightGCL 2023, and ContextGNN 2025. These are recorded as `degraded_not_unmatched`; official records plus other transports resolved identity and metadata.
- Some direct shell downloads failed with Windows `schannel` `SEC_E_NO_CREDENTIALS`. Alternate lawful publisher/author/repository routes succeeded.
- Initial automated OpenReview/Microsoft PDF routes returned HTTP 403 for some artifacts. Same-family author or arXiv artifacts were acquired. No paywall, authentication, or access control was bypassed.
- Search snippets and secondary indexes were used only to discover or cross-check records, never to set `source_content_verified=true`.

## Canonical identity and source-family accounting

All 14 retained scholarly records have full author lists, stable titles, publication years, venues, document types/statuses, DOI or official ID where available, and explicit version-family relations. Canonical metadata contains no abbreviated author lists, placeholder years, or mojibake.

There are 14 canonical records and 14 independent publication/version families. Preprint, accepted-manuscript, publisher, and index manifestations of the same work are collapsed. Method-lineage dependence remains explicit: NDR/T2Diff depend on the dual-encoder lineage; SimGCL/LightGCL depend on LightGCN-style graph propagation; DirectAU is an objective control rather than an independent architecture claim.

## Required architecture coverage and contracts

| Required coverage | Retained sources | Assumptions and inputs | Objective/output role | Locked evaluation boundary |
|---|---|---|---|---|
| ItemCF/ItemKNN | Sarwar 2001 | Interaction overlap and item-item similarities | Neighbor aggregation baseline | Same temporal split, similarity/normalization, candidate universe, tie rules, and evaluator |
| BPR-MF | Rendle 2009 | Implicit positives plus an explicit unobserved-item sampler | Pairwise objective with MF instantiation | Same negatives, regularization, optimization, and full-catalog evaluator |
| NCF | He 2017 | User/item IDs and sampled labels | Nonlinear interaction scorer | Source sampled leave-one-out is not v5; harmonize split and candidate universe |
| DeepFM | Guo 2017 | Sparse feature fields and shared embeddings | FM plus deep CTR scorer | Feature availability/leakage and CTR versus top-k task must be explicit |
| Two-tower candidate generation versus ranking | Huang 2013; Covington 2016; Yi 2019; ContextGNN 2025; T2Diff 2025 | Independently encodable user/item representations enable indexing; pair-specific interaction is constrained | Retrieval/matching, distinct from rich ranking | Freeze stage role, retrieval depth, index, negatives, latency, and downstream evaluator |
| Wide & Deep | Cheng 2016 | Explicit crosses support memorization; embeddings/MLP support generalization | Joint feature-rich ranker | Cross construction must be time-safe; no Apriori claim is supported |
| LightGCN | He 2020 | Observed user-item graph and ID embeddings | Simplified graph propagation with BPR | Train-only graph, propagation depth, sampling, and evaluator fixed |
| Graph/contrastive controls | SimGCL 2022; LightGCL 2023; DirectAU 2022 | Observed graph or positive pairs; augmentation/global-view assumptions | Contrastive or alignment/uniformity objective controls | Hold backbone, graph, sampling, objective weights, and compute budget fixed |

## Claim support, limitations, and counter-evidence

Seven production-intended bounded claim cards use original-content locators; one additional card is explicitly planning-only. No production-intended card relies only on the old lane, metadata, a search snippet, or a secondary index.

Important counter-evidence and limits are carried on the records and cards:

- Objective and sampling changes can confound apparent architecture gains; DirectAU, BPR, and corrected two-tower sampling are retained to expose this.
- Pair-agnostic towers trade interaction expressiveness for indexability; ContextGNN and T2Diff are recent controls, not universal replacements.
- LightGCN, SimGCL, and LightGCL depend on observed graph structure. Sparse-edge improvements cannot be extrapolated to zero-edge cold items.
- DeepFM's native CTR task and NCF's sampled leave-one-out protocol are not the Stage 1A full-catalog temporal contract.
- Wide & Deep contains no Apriori experiment.

## Evidence quality, predatory, and conflict screening

- Evidence level: all retained records are level VI individual technical/empirical studies under the locked discipline-relative framework; none is presented as a systematic review or independent replication.
- Quality grades: records are A or B based on directness, source integrity, and transportability to the architecture contract.
- Predatory screen: no retained record showed a predatory indicator in its official proceedings/venue record.
- Conflict screen: several industrial papers evaluate systems created by their authors/employers; all records flag that institutional/self-evaluation dependence. Academic method papers also lack independent v5 replication.
- Wide & Deep peer-review process is recorded as `unknown`: official ACM workshop publication is verified, but the inspected source-of-record did not independently document its review process. This uncertainty does not affect identity, content verification, or locator readiness.

## Remediation responsibility

- `ST1B-META-003`: lane share remediated. Canonical records use full authors, verified years/statuses, DOI/official IDs, UTF-8 text, and explicit version families. No abbreviated canonical authors or placeholder years remain.
- `ST1B-SYNTH-001`: lane share remediated at the evidence-accounting level. The handoff reports 14 canonical records separately from 14 independent publication/version families and exposes method-lineage dependence. No synthesis prose was written.
- `ST1B-LOCATOR-001`: lane share remediated. All 14 retained sources, including all five audit-core candidates, have lawfully acquired full artifacts, verified source content, SHA-256 hashes, and original-content locators.

## Unresolved items and downstream constraints

No acquisition or locator blocker remains. The following bounded uncertainties/constraints are carried forward:

1. Wide & Deep review-process status remains `unknown` from the inspected official record.
2. Three Semantic Scholar transports were rate-limited; they remain degraded, not unmatched.
3. Stage 1E must freeze whether v5 is single-stage ranking or two-stage retrieval-plus-ranking before two-tower metrics are operationalized.
4. Any v5 comparison must use the Stage 1A temporal, full-catalog, segment-aware evaluator with matched inputs, objectives, sampling, tuning, and compute accounting.

## Locked local-gate decision

**PASS**

Gate evidence:

- 100% old-candidate disposition: pass (20/20).
- Reproducible gap search through cutoff: pass (42 exact queries logged; 15 unique new records screened; 2 included; 13 excluded).
- Canonical identity/metadata or explicit uncertainty: pass (14/14 verified; one peer-review-process field explicitly unknown).
- No placeholder year, abbreviated canonical author list, or mojibake: pass.
- Source-family/version dependencies and independent-family count: pass (14 canonical; 14 independent version families).
- Bounded claim cards with limitations, counter-evidence, support scope, and forbidden extrapolations: pass (8/8).
- Production-intended claims have original-content locators: pass (7/7).
- Acquisition and locator readiness: pass (14/14; core 5/5).
- Required handoff JSON and internal consistency: subject to the machine-validation receipt recorded in `lane_handoff.json`.

The gate is not weakened by treating API degradation as an identity failure or by treating metadata as original-content verification.
