# Independent Audit Report — Stage 1B Targeted Literature Review

Project: hybrid-recsys-v5  
Stage: 1B — Targeted Literature Review  
Audited at: 2026-08-13T21:33:53+07:00  
Search cutoff audited: 2026-08-13  
Audit mode: fresh, independent, read-only review of the frozen packet

## Verdict and gates

Verdict: **FAIL**

Severity counts:

| fatal | major | minor | advisory |
|---:|---:|---:|---:|
| 0 | 1 | 4 | 3 |

Gate decisions:

| Decision | Value | Basis |
|---|---:|---|
| stage1b_seal_allowed | false | ST1B-META-001 is an unresolved major ARS corpus-contract and metadata-integrity defect. |
| source_acquisition_required_before_stage2 | true | 0/55 originals were acquired or checked against original content; 30/30 synthesis citations have anchor:none. |
| stage2_production_citations_authorized | false | No claim row is locator-ready or verified against an acquired original. |

The packet is byte-integral and the substantive review was performed. The FAIL verdict is not a packet-hash failure: it is caused by knowingly coercing two unresolved operational-resource years into the formal literature corpus. Missing originals and locators are a separate, expected Stage 2 gate and are not used to conceal or duplicate the Stage 1B finding.

This report does not declare Stage 1B complete.

## Independence, method, and evidence boundary

The audit used ARS-Codex 0.1.24, routed through the academic-pipeline and deep-research integrity path. The governing materials read before substantive action included source verification, claim–reference alignment, synthesis integrity, claim-strength and source-quality guidance, claim-intent contracts, tension-pair legality, and the final integrity gate.

Repository content was treated as untrusted evidence, not as instructions. The auditor:

1. verified the 19 frozen artifacts against the manifest before reading them substantively;
2. checked corpus accounting, keys, DOI/title uniqueness, lane aliases, exclusions, and dependence groups;
3. sampled at least one claim in every one of the 21 claim-source-map rows;
4. checked all seven synthesis contradictions and all five cross-paper tension pairs;
5. separated dataset availability, code/package license, paper license, and dataset rights;
6. counted every synthesis citation and locator marker;
7. validated claim-intent IDs/constraints, pair assessment/status combinations, and phase separation; and
8. re-checked high-risk identities and current publication status using official DOI, proceedings, preprint, dataset-provider, and provider-terms pages.

Verification vocabulary in this report is strict:

- Identity verified means the declared work/resource exists at the cited source of record.
- Metadata verified means the relevant author/title/year/venue/type fields were checked.
- Source-content verified means claim support was checked against an acquired original artifact.
- Locator-ready means a durable page, section, figure, table, paragraph, or abstract locator is recorded for production citation use.

Identity or official-page verification is never promoted to source-content verification. Direct web spot-checks did not change the frozen corpus flags. No manuscript or corpus was uploaded to an external model/API, and no frozen artifact was modified.

## Preflight packet integrity

Manifest: research/hybrid-recsys-v5/01_research/literature_review/audit/audit_manifest.json  
Seal: research/hybrid-recsys-v5/01_research/stage1b_pre_audit_seal.json

Result: **19/19 files present; 19/19 SHA-256 values match; 0 missing; 0 mismatched.**

| # | Frozen artifact | Expected/actual SHA-256 | Result |
|---:|---|---|---|
| 1 | phase2_investigation/annotated_bibliography.md | e9beac3989918ede285cb1dd446421c30ccf1fbbb0a0f88ff251a178ef77e981 | MATCH |
| 2 | phase2_investigation/claim_source_map.md | 8fc27f0b1d4785938a9c94bf0810631424a1fa8f02860399288120009528e57f | MATCH |
| 3 | phase2_investigation/deduplication_report.md | 229008fa1c21a6a0c67d90b50d4e149374513230ee5774265ef14215256c7f8b | MATCH |
| 4 | phase2_investigation/lanes/L1_evaluation_reproducibility.md | 0dc65c5318a21bc73c119d3fcaaa9d6e0489cf66cff776936284b279078a92da | MATCH |
| 5 | phase2_investigation/lanes/L2_recommender_architectures.md | 7da07c5137c0d88b87f814a1fa05315ad641fd1cdb28ae82b245baa686e7b913 | MATCH |
| 6 | phase2_investigation/lanes/L3_basket_sequential_hybrid.md | f6fd7358bc07723d0571d913408b89880613855f5d5f1b5dd8d03074432f2b30 | MATCH |
| 7 | phase2_investigation/lanes/L4_cold_content_transfer.md | 6c78b30e90cdf8f9e75b74e33f8629e53832537ea38d7010c704bf7b9e2b2e60 | MATCH |
| 8 | phase2_investigation/lanes/L5_vietnamese_external_datasets.md | 987e664495190c41db065b12f994682aa3852ce9d2c59dd6e221e02d446c200e | MATCH |
| 9 | phase2_investigation/literature_corpus.json | 094db2f9e1b7ca07222fc8923af7b706f5d905f0eac88a61107070dd9a6d0db1 | MATCH |
| 10 | phase2_investigation/search_strategy.md | a2b485df31a998964b90c6c1358e632801a70e2e7ffb813c6500585d733128a0 | MATCH |
| 11 | phase2_investigation/source_quality_matrix.json | b78ff915a88133aa1b3018811ea3a0342a3425c75ad803b4502bc3e75ccef474 | MATCH |
| 12 | phase2_investigation/source_registry.json | 0405126c258e1023efbe24625a95e5cfc2e0d00d157e5c72f463cdd31aa2a31c | MATCH |
| 13 | phase2_investigation/source_verification_report.md | b022d5799d4522d0b40daefc368418fba03e50b5300f84bffe6bf2e74dfeed8b | MATCH |
| 14 | phase2_investigation/tri_index_verification.json | 32eac83d0ca05afd1720937f22b236e288089a91b560702f9d1d34d313f1cceb | MATCH |
| 15 | phase2_investigation/verified_source_registry.json | 7491241e7917131f05e924bc5d4ae7599312227faf4f25a2a1a7b1150d5d4ada | MATCH |
| 16 | phase2_investigation/verify_source_registry.py | 21f4166ef2b4636127266cdbc4e615452a015b4bdaf5fb2f2cd6b1af64fdd5be | MATCH |
| 17 | phase3_analysis/claim_intent_manifest.json | caad19915f1d8e2f0dfbe0665291dcc2062032775dad17f1cfaf7beb4d1b271b | MATCH |
| 18 | phase3_analysis/cross_paper_tensions.json | f6e35ef025d83d6999c517846e1c52a55e077a977615b6deeed8d1d1ac3baf1b | MATCH |
| 19 | phase3_analysis/synthesis_report.md | 8afb2b143796bd81f3ad2207134a9ce11093371fcb8e280280d16f7fe2d97340 | MATCH |

The manifest file itself matches the seal at 22c98ce38b64302c0936a836dbaf6d32d0a616f5085a636b7e8055fb7aed9b4b. The audit packet matches the seal at 8e4f17abb7a531d396c9274ab776c197a489d4b9698357b6c8fca0ffb9637f08.

The declared packet root is 07a0e7c4cfd986db82bddc46339c6b9ff35a716a7240cf5a64f887f23d155095. Neither seal, manifest, nor packet specifies the root construction, artifact ordering, path normalization, byte framing, or canonicalization algorithm. In accordance with the fail-closed instruction, no algorithm was guessed. Therefore:

- individual-artifact integrity: PASS;
- manifest and packet hash integrity: PASS;
- packet-root recomputation: NOT VERIFIABLE BY SPECIFICATION;
- permission to continue substantive audit: yes, because every listed artifact individually matched.

## Coverage matrix for the seven audit questions

| Audit question | Coverage | Result |
|---|---|---|
| 1. Corpus identity and deduplication | 55 keys, normalized titles, DOI uniqueness, three alias merges, dependence groups, two exclusions | Covered. No ghost or duplicate identity found. |
| 2. Metadata/publication status | All high-risk records plus Complete Journey, Coveo, and Amazon-M2 checked against authoritative pages | Covered. One major and two minor metadata findings. |
| 3. Claim–source alignment | 21/21 claim rows sampled; 63 source occurrences/48 unique keys; forbidden extrapolations checked | Covered. Planning-level alignment is coherent; original-content verification is 0/21. |
| 4. Synthesis integrity | Seven contradiction rows, five tension pairs, thematic integration, family dependence, H1–H4 boundary | Covered. One minor family-count qualification finding. |
| 5. Dataset compatibility/rights | Complete Journey, Coveo, Amazon-M2; four separate rights/license layers | Covered. Frozen reasoning is conservative; one advisory snapshot requirement remains. |
| 6. Citation/locator readiness | 30 references, 30 adjacent anchors, 30 anchor:none; 24-source acquisition list | Covered. Production citation gate is closed. |
| 7. ARS contracts | 12 claim IDs, claim and manifest constraints, five legal pair states, phase separation | Covered. Structural pass; one-shot temporal ordering is not independently demonstrable. |

## Corpus identity and deduplication

The corpus accounting reconciles:

- 55 canonical records;
- 58 included lane identities;
- 2 central exclusions;
- 60 screened lane/exclusion identities in total;
- 3 cross-lane alias merges.

The only multi-lane canonical records are correctly merged:

| Canonical key | Lane aliases | Audit result |
|---|---|---|
| cheng2016_wide_deep | L2-04, L3-WD | One work; DOI 10.1145/2988450.2988454. |
| cai2023_lightgcl | L2-11, L4-12 | One ICLR 2023 work. |
| sheng2025_alpharec | L2-12, L4-07 | One ICLR 2025 work. |

There are no duplicate canonical keys, normalized titles, or DOI values. The verified registry contains 46 DOI-bearing records after the MUSE DataCite DOI correction; all 46 DOI identities and all 9 official no-DOI source pointers resolved to real declared works/resources during the independent check.

Dependence is represented rather than deduplicated away:

- Amazon Reviews 2023 and RelBench rel-amazon are one upstream family;
- H&M and RelBench rel-hm are one upstream family;
- BLaIR and Amazon Reviews 2023 share an upstream dataset family;
- each paper/repository/provider/competition bundle is treated as one artifact family where appropriate.

The two central exclusions do not create a topic gap:

- Jin et al. 2021 is redundant after retaining Krichene 2020 for the naive-sampling risk and Li 2023 for the estimator counterpoint.
- PERE is a new-user elicitation paper and is correctly excluded from cold-item evidence; the cold-item/content lane remains populated by direct item-side sources.

Identity verification passes for 55/55 at the declared granularity. Version/edition metadata is not fully locked for H&M and Complete Journey, and none of the 55 records is source-content verified or locator-ready.

## Metadata and publication-status spot checks

All checks below were current as of 2026-08-13. “Official page spot-check” does not mean an original was acquired into the corpus.

| Record | Authoritative check | Identity | Metadata/publication status | Content/locator status |
|---|---|---|---|---|
| Jannach & Chen 2026 | [ACM DOI record](https://doi.org/10.1145/3800587); [HKBU institutional record](https://scholars.hkbu.edu.hk/en/publications/improving-methodological-standards-in-recommender-systems-offline/) | Verified | 2026, TORS 4(3), DOI correct. Official descriptions call it an editorial/essay; formal peer-review status is not established. | Official-page spot-check only; frozen source_verified=false; no production locator. |
| AlphaRec 2025 | [ICLR/OpenReview record](https://openreview.net/forum?id=eIJfOIMN9z); [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/e4bab1843c8d5a69f5abfd0824593493-Abstract-Conference.html) | Verified | ICLR 2025 Oral, six authors, peer-reviewed conference paper. No proceedings DOI. The arXiv DOI belongs to the preprint version and must not silently replace the conference source of record. | Abstract/page spot-check; no acquired original/locator. |
| Time to Split 2025 | [ACM DOI record](https://doi.org/10.1145/3705328.3748164) | Verified | RecSys 2025, pp. 874–883, five authors, DOI and year correct. | Official page and abstract spot-check; no acquired original/locator. |
| ViHoRec 2026 | [arXiv record](https://arxiv.org/abs/2607.12946) | Verified | Submitted 2026-07-14, one author, DOI 10.48550/arXiv.2607.12946; preprint, not peer reviewed. | Abstract spot-check; release/rights still conditional; no locator. |
| BLaIR / ACL 2026 | [ACL Anthology](https://aclanthology.org/2026.acl-long.147/) | Verified | ACL 2026 long paper, pp. 3251–3265, seven authors, DOI 10.18653/v1/2026.acl-long.147. | Official abstract/page spot-check; no frozen locator. |
| MUSE 2025 | [arXiv record](https://arxiv.org/abs/2512.07216) | Verified | Submitted 2025-12-08, DOI 10.48550/arXiv.2512.07216, 11 authors; preprint, not peer reviewed. Frozen compact author list remains abbreviated. | Abstract spot-check; no acquired original/locator. |
| Amazon-M2 2023 | [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/193df57a2366d032fb18dcac0698d09a-Abstract-Datasets_and_Benchmarks.html) | Verified | NeurIPS 2023 Datasets and Benchmarks. Official task is session/next-product engagement and text generation, not verified persistent-user purchase replication. | Official abstract/PDF spot-check; no frozen locator. |
| Complete Journey | [dunnhumby Source Files](https://www.dunnhumby.com/source-files/); [completejourney package](https://github.com/bradleyboehmke/completejourney) | Verified as resources | Provider: about 2,500 households/two years. Package: 2,469 households/one year. Exact edition/year relationship is not locked. | Rights and revision unresolved; not locator-ready. |
| Coveo SIGIR eCom | [official repository](https://github.com/coveooss/SIGIR-ecom-data-challenge); [dataset terms](https://raw.githubusercontent.com/coveooss/SIGIR-ecom-data-challenge/main/Terms%20%26%20Conditions.txt) | Verified | Operational/workshop resource. Terms allow noncommercial research/education and prohibit redistribution/de-anonymization. | Conditional dataset; not strict H4; terms snapshot must be archived before use. |

No retraction, withdrawal, or ghost-source signal was found for the high-risk records. Semantic Scholar HTTP 429 remains degraded transport, not evidence of absence.

The frozen statement “49 peer-reviewed” is not independently sustained because the Jannach–Chen work is an editorial/essay. Until formal external peer review is demonstrated, the defensible count is at most 48 peer-reviewed records.

## Claim–source alignment: 21/21 rows sampled

All 63 source-key occurrences resolve to 48 unique corpus keys; there are no dangling keys. The alignment findings below are planning-level only because source_acquired=false and source_verified_against_original=false for all 55 entries.

| Claim row | Sampled claim and source surface | Audit conclusion |
|---|---|---|
| C-INTRO-01 | Split/candidate/metric/aggregation/tuning dependence; L1-S04/S05/S08/S10 | Provisionally aligned as a composite methodological claim. |
| C-INTRO-02 | Naive sampling versus estimator counterpoint; L1-S01/L1-S03 | Aligned and properly conditional; it does not claim all sampling is invalid. |
| C-INTRO-03 | Faithful implementation, tuned baselines, frozen reporting; L1-S09–S12 | Aligned at summary level; public code is not treated as proof of reproduction. |
| C-RW-CF-01 | ItemCF/BPR/NCF/LightGCN assumptions; L2-01/L2-02/L2-06/L2-09 | Definitional framing is coherent; no v5 ranking is inferred. |
| C-RW-TOWER-01 | Independent encoders and candidate/ranking boundaries; L2-03/L2-05/L2-08 | Architecture framing only; project retrieval boundary remains conditional. |
| C-RW-WIDE-01 | Wide memorization/deep generalization; L2-04/L2-07 | Aligned. No Apriori efficacy is attributed to Wide & Deep. |
| C-RW-GRAPH-01 | Graph/contrastive collaborative controls; L2-09/L2-11/L4-10–L4-12 | Aligned with the explicit sparse-edge versus zero-edge boundary. |
| C-RW-SEQ-01 | SASRec/BERT4Rec and protocol sensitivity; L3 SASREC/BERT4REC/TIME-SPLIT | Aligned; paper-native metrics are not transferred. |
| C-RW-RULE-01 | Apriori support/confidence and mining/evaluation separation; AR-APR/AR-MULTI | Aligned; Apriori is not presented as a ranking model. |
| C-RW-HYBRID-01 | Prior fusion/ablation work; HYB-SR-CF/WD/HAM/M2 | Plausibility only; not H3 evidence. |
| C-RW-NBR-01 | Repeat/explore heterogeneity; NBR-REALITY/REP-EXP/BTBR | Aligned; aggregate gain is not equated with novel-item gain. |
| C-RW-COLD-01 | Item-side content/distillation signal; L4-01–L4-04 | Aligned; cold item is not transformed into cold user. |
| C-RW-TRANSFER-01 | UniSRec/VQ-Rec/AlphaRec transfer; SBERT embedding boundary; L4-05–L4-08 | Aligned; SBERT is encoder rationale, not recommender efficacy evidence. |
| C-DATA-VN-01 | Three reviewed Vietnamese resources lack the complete frozen contract; CSC-L5-01 | Properly search-bounded; no “first” or “none exist” claim. |
| C-DATA-EXT-01 | Content/purchase/basket/session compatibility tradeoff; CSC-L5-02–05 | Core claim aligns, but “often” is too prevalence-like for a targeted review; see ST1B-SCOPE-001. |
| C-H4-01 | No unconditional candidate; Complete Journey/Coveo conditional; Amazon-M2 transfer-only | Correctly bounded; architecture transfer is not H4 replication. |
| C-BENCH-01 | Official reproduction versus harmonized comparison | Correctly labelled internal design plus methodological caution. |
| C-RQ3-COHORT-01 | Held-out-consequent membership is outcome-labelled | Correct internal logical constraint, not an empirical literature result. |
| C-EFFICIENCY-01 | Retrieval/ranking separation is not deployment readiness | Correct internal design boundary; no unmeasured latency claim. |
| C-NOVELTY-01 | Controlled integration/evaluation gap, not invention of components | Conditional only; absolute novelty remains blocked. |
| C-RESULT-01 | H1–H4 are NOT_RUN | Clean. No literature statement is written as an observed v5 result. |

Forbidden extrapolations are enforced in the frozen packet:

- cold item is not changed into cold user;
- Wide & Deep is not used as evidence that Apriori improves the proposed Wide branch;
- Amazon-M2 or other architecture transfer is not renamed H4 replication;
- source-native scores are not transferred into a v5 leaderboard;
- H1–H4 remain NOT_RUN; and
- absolute first/novelty claims remain blocked because the dedicated novelty search is incomplete.

## Synthesis integrity

The synthesis is organized by themes and tensions rather than by a serial paper list. Its literature matrix, key themes, contradiction table, evidence convergence map, and remaining gaps jointly integrate the five lanes.

### Seven contradictions

| # | Contradiction | Audit result |
|---:|---|---|
| 1 | Naive sampled metrics versus improved estimators | Legal conditional difference; exact full-catalog remains preferred when feasible. |
| 2 | Native-paper gains versus reproduction/tuned-baseline reversals | Correctly resolved as no transferable ordering. |
| 3 | Wide & Deep rationale versus the untested Apriori-Wide proposal | Correctly limited to architecture rationale; H3 remains NOT_RUN. |
| 4 | Content cold-start versus strong collaborative graph controls | Correctly separates zero-interaction items from sparse edges. |
| 5 | Amazon-M2 signal richness versus the locked H4 purchase estimand | Correctly classified as architecture transfer only. |
| 6 | Complete Journey structural fit versus edition/rights uncertainty | Correctly conditional; no execution or licensing inference. |
| 7 | Rule-aligned cohort focus versus held-out-consequent membership | Correctly requires a train-mined, outcome-labelled cohort description. |

### Five cross-paper tension pairs

| Pair | pair_assessment / resolution_status | Contract/content audit |
|---|---|---|
| CP-001 | conditional_difference / resolved_in_synthesis | Legal. Krichene/Rendle and Li et al. answer different sampling-estimation conditions; resolution pointer exists. |
| CP-002 | insufficient_overlap / not_applicable | Legal. Wide & Deep and Apriori do not jointly test the proposed branch; no false resolution pointer. |
| CP-003 | conditional_difference / resolved_in_synthesis | Legal. Collaborative-edge propagation and content-assisted cold-item representation cover different missingness regimes. |
| CP-004 | conditional_difference / resolved_in_synthesis | Legal. Amazon-M2 and Complete Journey differ in outcome/user/basket semantics and rights readiness. |
| CP-005 | no_material_conflict / not_applicable | Legal. Repeat/explore diagnosis and novel-basket intervention are complementary, not contradictory. |

All five scholar_confirmation fields remain pending, which is appropriate given that original acquisition has not occurred. No illegal pair_assessment/resolution_status combination was found.

The synthesis does, however, report “12 sources” for Vietnamese/external compatibility without stating that these are canonical records rather than independent evidence/data families. This is a minor convergence-strength ambiguity under MNC-8; see ST1B-SYNTH-001.

## Dataset compatibility and rights

The frozen L5 analysis correctly distinguishes availability from rights. Independent authoritative spot-checks support its conservative treatment.

| Dataset/resource | Public availability | Code/package license | Paper license | Dataset rights | H4 status |
|---|---|---|---|---|---|
| Complete Journey | Provider download exists; provider and package describe different scopes/editions. | The R package declares CC0 at the package layer. | No canonical dataset paper controls the resource. | Package CC0 does not by itself prove an upstream provider redistribution grant. Provider terms/revision must be archived and reviewed. | H4-CONDITIONAL; structurally closest, not cleared. |
| Coveo SIGIR eCom | Release requires form/acceptance; public repository describes about 36M events and about 5M sessions. | No separate OSS code grant was established by this audit. | Workshop/preprint rights are a separate layer. | Official terms: noncommercial research/education only; no redistribution or de-anonymization. | H4-CONDITIONAL; no persistent user and strict purchase protocol still requires audit. |
| Amazon-M2 | Official NeurIPS/competition distribution exists. | Repository-code licensing was not used as a dataset grant. | NeurIPS paper rights are separate. | Exact downloaded dataset revision/agreement must be archived even if a paper appendix states a license. | NOT strict H4: next interaction/engagement, no verified purchase outcome or persistent cross-session user. |

Public hosting is not redistribution permission. A code or package license is not a paper license; a paper license is not a dataset license; and a dataset license does not erase source-platform terms. No frozen statement conflates these layers.

## Citation and locator readiness

The synthesis contains exactly:

- 30 reference markers;
- 30 anchor markers;
- 30/30 adjacent ref/anchor pairs;
- 30/30 anchors equal to anchor:none;
- 29 unique cited corpus keys because one key is cited twice.

The corpus contains:

- source_acquired=true: 0/55;
- source_verified_against_original=true: 0/55;
- source_verification_method=none: 55/55.

Therefore every claim row is only planning-ready. None is production-citation-ready. stage2_production_citations_authorized is false regardless of the Stage 1B verdict.

### Required 24-source acquisition shortlist

This is the exact core set to acquire before the production Introduction/Related Work is finalized. Acquisition means an official/version-of-record or accepted-author artifact, durable locator capture, and claim-level verification. Any additional source used in production prose must undergo the same process.

| # | Canonical key and source | Acquisition purpose |
|---:|---|---|
| 1 | [krichene2020_sampled_metrics — On Sampled Metrics](https://dl.acm.org/doi/10.1145/3394486.3403226) | Exact-versus-sampled boundary. |
| 2 | [li2023_reliable_sampling — Towards Reliable Item Sampling](https://ojs.aaai.org/index.php/AAAI/article/view/25561) | Estimator counterpoint. |
| 3 | [zhao2020_alternative_settings — Alternative Experimental Settings](https://dl.acm.org/doi/10.1145/3340531.3412095) | Split/candidate/metric semantics. |
| 4 | [dacrema2021_reproducibility — Troubling Analysis](https://doi.org/10.1145/3434185) | Faithful reproduction and tuned baselines. |
| 5 | [jannach2026_methodological_standards — Methodological Standards](https://doi.org/10.1145/3800587) | Current standards position; cite as editorial/essay unless review status is proven. |
| 6 | [sarwar2001_itemcf — Item-based CF](https://doi.org/10.1145/371920.372071) | Neighborhood comparator definition. |
| 7 | [rendle2009_bpr — BPR](https://www.auai.org/uai2009/papers.html) | Pairwise implicit-ranking objective. |
| 8 | [he2020_lightgcn — LightGCN](https://doi.org/10.1145/3397271.3401063) | Graph-CF control and edge requirement. |
| 9 | [covington2016_youtube — YouTube Recommendations](https://doi.org/10.1145/2959100.2959190) | Candidate-generation/ranking systems boundary. |
| 10 | [cheng2016_wide_deep — Wide & Deep](https://doi.org/10.1145/2988450.2988454) | Memorization/generalization and non-Apriori boundary. |
| 11 | [kang2018_sasrec — SASRec](https://doi.org/10.1109/ICDM.2018.00035) | Canonical sequential mechanism. |
| 12 | [gusak2025_time_split — Time to Split](https://doi.org/10.1145/3705328.3748164) | Current temporal split sensitivity. |
| 13 | [agrawal1994_apriori — Apriori](https://vldb.org/conf/1994/P487.PDF) | Support/confidence definitions. |
| 14 | [ghoshal2014_multi_item_rules — Multi-item Association Rules](https://doi.org/10.1287/ijoc.2013.0575) | Direct rule-recommender precedent. |
| 15 | [liu2009_hybrid_seq_cf — Hybrid Sequential Rules and CF](https://doi.org/10.1016/j.ins.2009.06.004) | Association/CF fusion precedent. |
| 16 | [li2023_nbr_reality — Next Basket Reality Check](https://doi.org/10.1145/3587153) | Repeat/explore confounding. |
| 17 | [volkovs2017_dropoutnet — DropoutNet](https://papers.neurips.cc/paper_files/paper/2017/hash/dbd22ba3bd0df8f385bdac3e9f8be207-Abstract.html) | Foundational cold-item boundary. |
| 18 | [hou2022_unisrec — UniSRec](https://doi.org/10.1145/3534678.3539381) | Transferable text-aware sequence representation. |
| 19 | [sheng2025_alpharec — AlphaRec](https://proceedings.iclr.cc/paper_files/paper/2025/hash/e4bab1843c8d5a69f5abfd0824593493-Abstract-Conference.html) | Recent language-representation comparator. |
| 20 | [reimers2019_sbert — Sentence-BERT](https://aclanthology.org/D19-1410/) | Embedding construction only. |
| 21 | [tran2024_viecomrec — ViEcomRec](https://doras.dcu.ie/29693/) | Vietnamese e-commerce positioning. |
| 22 | [jin2023_amazon_m2 — Amazon-M2](https://proceedings.neurips.cc/paper_files/paper/2023/hash/193df57a2366d032fb18dcac0698d09a-Abstract-Datasets_and_Benchmarks.html) | Architecture-transfer and non-purchase boundary. |
| 23 | [tagliabue2021_coveo — Coveo SIGIR eCom](https://sigir-ecom.github.io/ecom2021/data-task.html) | Conditional purchase-compatible resource audit. |
| 24 | [completejourney_resource — Complete Journey](https://www.dunnhumby.com/source-files/) | Leading strict-H4 candidate; edition, terms, and rights audit. |

For papers, capture page/section/table/figure or an explicitly justified abstract locator. For operational resources, also capture exact revision, file list, checksums, repository commit, provider terms, license text, and redistribution conditions.

## ARS contract checks

### Claim-intent manifest

Structural result: PASS.

- manifest_id M-2026-08-13T13:55:30Z-a13b is well formed;
- 12 unique claim IDs run from C-001 through C-012;
- each claim has a unique claim-level NC-CNNN-1 constraint;
- 10 unique manifest constraints run from MNC-1 through MNC-10;
- all 32 unique planned reference keys resolve in the corpus;
- constraints explicitly cover cold item/cold user, Apriori efficacy, H4 replication, novelty, source-family dependence, and null-locator refusal.

One-shot precommitment semantics are not independently provable from the frozen end state. The manifest declares emitted_at and emitted_by, and filesystem times place it before the synthesis report, but there is no immutable invocation ledger or hash chain proving that it was emitted before the first prose block and never mutated. This is an audit limitation, not evidence of a violation.

### Tension contract

Structural result: PASS.

- five unique CP IDs;
- every paper key resolves;
- three conditional_difference/resolved_in_synthesis pairs have resolution pointers;
- insufficient_overlap and no_material_conflict correctly use not_applicable and omit a false resolution pointer;
- all scholar confirmations remain pending.

### Phase scope

Result: PASS.

- Phase 2 artifacts contain search, screening, investigation, lane cards, verification, and claim mapping.
- Phase 3 contains claim intent, tension inventory, and synthesis.
- The synthesis explicitly states that it is neither manuscript prose nor an audit verdict.
- No frozen artifact contains a Stage 1B seal, manuscript, or substantive independent-audit verdict.
- H1–H4 remain NOT_RUN.

## Findings by severity

### Major

#### ST1B-META-001 — Unverified operational years were coerced into publication-year fields

Audit questions: 2 and 7.

Exact artifact pointers:

- research/hybrid-recsys-v5/01_research/literature_review/phase2_investigation/literature_corpus.json > non_source_metadata.note
- same file > literature_corpus[citation_key=hm_fashion_competition].year
- same file > literature_corpus[citation_key=completejourney_resource].year
- research/hybrid-recsys-v5/01_research/literature_review/phase2_investigation/verified_source_registry.json > sources[key=hm_fashion_competition].year
- same file > sources[key=completejourney_resource].year
- research/hybrid-recsys-v5/01_research/literature_review/phase2_investigation/annotated_bibliography.md > L5 entries 10–11

Evidence: the formal corpus records H&M as 2022 and Complete Journey as 2014, while the verified registry stores null and the bibliography cites n.d. The corpus note states that these values were used to satisfy the ARS schema and that exact release/edition metadata remains unresolved. The ARS literature-corpus contract defines year as publication year and requires rejection rather than placeholder coercion when it cannot be determined.

Rationale: a knowingly non-bibliographic operational value in a publication-year field makes the formal corpus internally inconsistent and can contaminate recency counts, filters, and reference export. This is more than incomplete metadata because the contradiction was created deliberately to pass a schema.

Remediation: before resealing, either (a) move H&M and Complete Journey into a separate operational-resource registry until verified edition years exist, or (b) adopt a reviewed resource schema that permits null year plus explicit operational_year and year_basis without misrepresenting publication year. Recompute all corpus/recency/peer summaries, regenerate dependent artifacts, and issue a new manifest/seal for re-audit.

Gate impact: packet_integrity remains PASS; stage1b_seal_allowed=false until remediation and re-audit; Stage 2 remains independently blocked by locators.

### Minor

#### ST1B-META-002 — Jannach & Chen editorial is counted as proven peer-reviewed research

Audit question: 2.

Exact artifact pointers:

- phase2_investigation/source_registry.json > sources[key=jannach2026_methodological_standards].peer_reviewed
- phase2_investigation/verified_source_registry.json > sources[key=jannach2026_methodological_standards].peer_reviewed
- phase2_investigation/source_quality_matrix.json > sources[citation_key=jannach2026_methodological_standards].peer_review_assessment
- phase2_investigation/annotated_bibliography.md > opening summary and L1 entry 11

Evidence: DOI, authors, year, journal, and volume/issue are verified, but ACM describes the work as an essay/editorial and the institutional record classifies it as Contribution to journal — Editorial. The packet supplies no evidence of formal external peer review.

Rationale: venue publication is not itself proof that an editorial was formally peer reviewed. The work remains an authoritative standards/position source, but the 49 peer-reviewed total is unsupported.

Remediation: record venue_type editorial/essay and peer_reviewed=false or unknown unless the journal confirms formal review; recompute the peer-reviewed summary to at most 48 pending proof.

Gate impact: no independent seal block, but it must be corrected in the rebuilt packet caused by ST1B-META-001.

#### ST1B-META-003 — Mojibake corrupts canonical bibliographic names/titles

Audit question: 2.

Exact artifact pointers:

- phase2_investigation/literature_corpus.json > records jarvelin2002_cumulated_gain, canamares2020_offline_options, peng2023_m2, completejourney_resource
- phase2_investigation/verified_source_registry.json > the same records
- phase2_investigation/annotated_bibliography.md > entries containing JÃ¤rvelin, CaÃ±amares, MÂ², and 84.51Â°
- phase2_investigation/source_quality_matrix.json and tri_index_verification.json > peng2023_m2.title

Evidence: UTF-8 names and symbols are stored as mojibake, including Järvelin/Kekäläinen, Rocío Cañamares, M², and 84.51°.

Rationale: identity still resolves through DOI/title context, but production references and machine matching can be damaged.

Remediation: normalize from authoritative metadata and validate UTF-8 round trips before reference export.

Gate impact: no independent Stage 1B block; production bibliography must not use the corrupted strings.

#### ST1B-SCOPE-001 — “Often” overstates prevalence beyond a targeted corpus

Audit question: 3.

Exact artifact pointers:

- phase2_investigation/claim_source_map.md > C-DATA-EXT-01
- phase3_analysis/synthesis_report.md > Literature matrix > External compatibility
- phase2_investigation/search_strategy.md > Search limitations

Evidence: the packet is explicitly targeted and non-exhaustive, yet the external-compatibility claim says text-rich sources “often” lack specified signals and order-rich sources “often” omit others.

Rationale: “often” reads as a prevalence statement about the literature rather than an observation bounded to reviewed candidates.

Remediation: production wording should begin “Among the reviewed candidates...” and preserve the targeted-search boundary.

Gate impact: no independent seal block; production prose must be bounded.

#### ST1B-SYNTH-001 — Evidence convergence count does not qualify dependent source families

Audit question: 4.

Exact artifact pointers:

- phase3_analysis/synthesis_report.md > Evidence convergence map > Vietnamese/external compatibility — 12 sources
- phase2_investigation/lanes/L5_vietnamese_external_datasets.md > OVERLAP_FLAGS > OF-01, OF-02, OF-09
- phase3_analysis/claim_intent_manifest.json > manifest_negative_constraints[MNC-8]

Evidence: the convergence map states 12 sources without saying these are canonical corpus records, even though RelBench rel-amazon depends on Amazon Reviews, rel-hm depends on H&M, and adapter/package layers are not independent corroboration.

Rationale: the wording can overstate independent convergence despite the dependence being correctly recorded elsewhere.

Remediation: report “12 canonical corpus records; fewer independent data/source families” and name the dependent lineages. Do not invent a family count until a counting rule is frozen.

Gate impact: no independent seal block; it blocks any production claim of 12 independent corroborating sources.

### Advisory

#### ST1B-LOCATOR-001 — Claim alignment is not source-content or locator verified

Audit questions: 3 and 6.

Exact artifact pointers:

- phase2_investigation/claim_source_map.md > Claim map and Locator status
- phase2_investigation/literature_corpus.json > literature_corpus[*].source_acquired, source_verified_against_original, source_verification_method
- phase2_investigation/search_strategy.md > Search limitations
- phase3_analysis/synthesis_report.md > Synthesis boundary and Synthesis limitations

Evidence: 21/21 rows depend on lane cards/official summaries; 0/55 originals are acquired or verified; 30/30 anchors are none.

Rationale: identity verification cannot support production claim emission. The packet discloses this correctly, so it is an expected separate gate rather than a hidden Stage 1B defect.

Remediation: acquire and verify the 24-source core set, add durable locators, then re-run claim-level alignment. Apply the same rule to any additional production citation.

Gate impact: source_acquisition_required_before_stage2=true; stage2_production_citations_authorized=false; no additional Stage 1B seal impact.

#### ST1B-ARS-001 — One-shot claim-intent ordering is structurally plausible but not independently auditable

Audit question: 7.

Exact artifact pointers:

- phase3_analysis/claim_intent_manifest.json > manifest_id, emitted_at, emitted_by
- phase3_analysis/synthesis_report.md > root status and first prose block

Evidence: IDs and constraints pass structural checks, and timestamps are consistent with manifest-before-synthesis order, but the packet contains no immutable invocation ledger or manifest/synthesis hash chain.

Rationale: a self-declared emitted_at field proves neither pre-prose emission nor no later mutation.

Remediation: future synthesis invocations should persist a write-once ledger with manifest hash/time, synthesis start time, and final output hash.

Gate impact: advisory only; no evidence of an actual violation and no independent seal block.

#### ST1B-RIGHTS-001 — Complete Journey terms and edition relationship are not snapshotted

Audit question: 5.

Exact artifact pointers:

- phase2_investigation/lanes/L5_vietnamese_external_datasets.md > L5-EXT-08 > Limitations
- same file > UNRESOLVED > U-01
- same file > CSC-L5-05 and CSC-L5-07
- same file > CENTRAL_REVIEW_ALERTS items 2, 5, and 6

Evidence: the frozen artifact correctly refuses to treat package CC0 as an upstream dataset grant, but it does not archive the contemporaneous provider terms, exact package revision, or the mapping between the provider’s 2,500-household/two-year resource and the package’s 2,469-household/one-year resource.

Rationale: availability and package licensing do not establish provider redistribution rights or edition equivalence.

Remediation: archive URL/time/terms bytes, exact download revision and checksums, package commit/version, and obtain institutional/legal review before acquisition sharing, execution, or redistribution.

Gate impact: no Stage 1B seal block; Complete Journey remains H4-CONDITIONAL and execution/redistribution is not authorized.

## Limitations

- No original artifact was locally acquired by the frozen corpus. Official pages and abstracts were spot-checked, but source-content verification and locator readiness remain false unless explicitly stated otherwise.
- The packet-root algorithm is not specified, so the declared root cannot be recomputed without guessing. All 19 individual hashes, the manifest hash, and the packet hash do match.
- Semantic Scholar was API-degraded by HTTP 429 for 55 records. This audit did not interpret degradation as non-existence.
- Full author lists remain abbreviated for eight compact records, including MUSE. They must be expanded before production reference export.
- Dedicated novelty searching is incomplete. All absolute first/novelty claims remain prohibited.
- Web terms and provider pages can change. Rights conclusions require archived snapshots and institutional/legal review; this audit is not legal advice.
- The audit is targeted to the seven packet questions and is not a systematic review or PRISMA review.

## Required remediation and re-gating

Before a new Stage 1B seal decision:

1. resolve ST1B-META-001 by separating unresolved operational resources or adopting a truthful nullable/resource-year schema;
2. rebuild the affected corpus, summaries, synthesis dependencies, manifest, and seal rather than editing the frozen packet in place;
3. correct the editorial peer-review classification and bibliographic encoding during that rebuild;
4. bound the external-compatibility wording and qualify the source-family count; and
5. submit the newly sealed packet for independent re-audit.

Before Stage 2 production Introduction/Related Work citations:

1. acquire the 24-source core set from official/version-of-record or accepted-author locations;
2. verify every planned production claim against original content;
3. record non-null page/section/table/figure/abstract locators;
4. expand full author/proceedings/page metadata and normalize encoding; and
5. keep any source not in the core set subject to the same acquisition and locator rules.

Before any H4 external-dataset execution or redistribution:

1. lock exact dataset revisions, files, checksums, terms, and licenses;
2. verify purchase outcome, persistent-user, basket, timestamp, item-content, split, and candidate-universe compatibility;
3. keep Amazon-M2 as architecture-transfer evidence rather than H4 replication; and
4. obtain institutional/legal approval where provider or source-platform rights remain conditional.

## Model/runtime actually used

- Model: gpt-5.6-sol
- Reasoning effort: ultra
- ARS skill: ars-codex:academic-research-suite 0.1.24
- Route: academic-pipeline plus deep-research integrity audit
- Parallel read-only sub-audits: corpus/metadata; claim rows/locators; synthesis/contracts/rights
- Audit timestamp: 2026-08-13T21:33:53+07:00

Only the three authorized audit-output files are written. The 19 frozen artifacts, audit packet, manifest, pre-audit seal, pipeline state, and manuscript surfaces remain untouched.
