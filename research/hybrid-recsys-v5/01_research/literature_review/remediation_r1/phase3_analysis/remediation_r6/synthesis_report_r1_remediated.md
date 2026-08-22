# R6 Remediation Overlay — Phase 3 Synthesis Report — Hybrid Recommender Systems v5

## Material Passport

- Origin skill: `deep-research`
- Origin mode: `direct-mode Phase 3 synthesis`
- Origin date: `2026-08-21`
- Verification status: `REMEDIATED_PENDING_FRESH_R6_REAUDIT` (R5 remains frozen; this overlay does not self-close R6)
- Version label: `stage1b-r1-r6-remediation-overlay-v1.0`
- Upstream dependencies: frozen R3 integration handoff and frozen R4 acquisition handoff
- Input cutoff: `2026-08-21`
- Reproducibility boundary: deterministic hashes and validators are replayable; analytical synthesis is not claimed byte-reproducible.

## Overlay boundary

This bounded overlay preserves the frozen R5 claims and all verified citation markers/anchors. It changes only evidence-denominator wording, exact-source-set disclosures, and phase-status metadata required by R6-MAJ-001/R6-MIN-002. Every thematic evidence denominator resolves to `theme_evidence_denominators.json`; the one-shot claim intent remains unchanged.

## Scope and evidence base

This is an ARS Phase 3 research artifact, not an Introduction, Related Work section, manuscript draft, benchmark report, or hypothesis result. The frozen registry contains 74 canonical scholarly records mapped to 71 nominal scholarly source families; the included synthesis corpus contains 52 canonical scholarly records and 52 nominal family IDs [denominator: `theme_evidence_denominators.json#/global_context_counts`]. The R4 core contains 23 scholarly records plus one operational source family, reported as 24 core objects without treating the operational family as a scholarly paper [denominator: `theme_evidence_denominators.json#/global_context_counts`]. R5 uses no sources beyond the frozen input graph.

The synthesis yields five themes, five key debates, twelve assessed cross-paper pairs, and six gaps. Pairwise tension coverage is deliberately recall-limited: seven pairs are conditional differences resolved in this synthesis, four show no material conflict, and one has insufficient overlap; all twelve pair assessments await scholar confirmation [denominator: `theme_evidence_denominators.json#/tension_population_counts`].

## Theme 1 — The evaluation protocol is part of the estimand

### Assumptions

Offline recommender comparisons do not isolate an architecture unless the target event, split, candidate universe, metric implementation, aggregation rule, negative sampling, and tuning budget are held fixed. Krichene and Rendle show that naive sampled metrics can change ordering relative to exact evaluation (Krichene & Rendle, 2020)<!--ref:krichene2020_sampled_metrics--><!--anchor:section:Abstract; empirical ordering results; Sections 7–8-->, while later work shows that sampling reliability varies with estimator and regime rather than admitting an unconditional sampled-versus-exact verdict (Li et al., 2023)<!--ref:li2023_reliable_sampling--><!--anchor:section:Abstract; Introduction; experimental comparison section-->. The synthesis therefore treats exact and sampled evaluation as different estimands unless an estimator-specific equivalence argument is supplied.

Candidate construction and time splitting are likewise design variables, not implementation details. Alternative candidate settings can alter offline conclusions (Zhao et al., 2020)<!--ref:zhao2020_alternative_settings--><!--anchor:table:Abstract; Sections 2–4; Table 2-->, and sequential model rankings can change across split policies (Gusak et al., 2025)<!--ref:gusak2025_time_split--><!--anchor:figure:Figure 1; Sections 1–3; global temporal split and results subsections-->. These findings justify locking the v5 protocol before outcomes are inspected; they do not establish that one split or sampling strategy is universally best.

### Evaluation protocols

The methodological convergence is strong but bounded: six canonical scholarly records across six nominal and six dependency-adjusted source families support treating preprocessing, tuning, baseline optimization, seeds, stopping rules, and evaluation code as parts of the comparison contract [denominator: `theme_evidence_denominators.json#/themes/T1`]. Exact source keys: krichene2020_sampled_metrics, li2023_reliable_sampling, zhao2020_alternative_settings, gusak2025_time_split, dacrema2021_reproducibility, jannach2026_methodological_standards. Exact family IDs: SF-R1-028, SF-R1-031, SF-R1-069, SF-R1-013, SF-R1-009, SF-R1-023. Reproducibility criteria require more than a public repository (Dacrema et al., 2021)<!--ref:dacrema2021_reproducibility--><!--anchor:section:Section 3; reproducible-setup criteria; discussion of evaluation practice-->, while the frozen Jannach–Chen record contributes editorial guidance rather than measured effect-size evidence (Jannach & Chen, 2026)<!--ref:jannach2026_methodological_standards--><!--anchor:section:Abstract; Sections 1–3 and 5; Appendix evaluation guidelines-->.

An official-protocol reproduction and a harmonized benchmark must remain two separate outputs. The former asks whether an implementation reproduces a source-specific pipeline; the latter asks how alternatives behave under the common v5 data, candidate, metric, and tuning contract. Neither a public codebase nor a successful source-native reproduction supplies a harmonized v5 result.

## Theme 2 — Architecture labels conceal different signals, objectives, and stage roles

### Input signals

The retained baselines span distinct evidence channels. ItemCF aggregates item-neighbor evidence from historical co-interaction (Sarwar et al., 2001)<!--ref:sarwar2001_itemcf--><!--anchor:section:Sections 3.1 Item Similarity Computation and 3.2 Prediction Computation-->, whereas BPR specifies a pairwise implicit-feedback objective usable with matrix factorization or another differentiable scorer (Rendle et al., 2009)<!--ref:rendle2009_bpr--><!--anchor:section:Sections 4.1 BPR Optimization Criterion, 4.2 BPR Learning Algorithm, and 4.3.1 Matrix Factorization-->. NCF learns nonlinear user–item interaction functions from IDs (He et al., 2017)<!--ref:he2017_ncf--><!--anchor:section:Sections 3.1 General Framework, 3.2 GMF, 3.3 MLP, and 3.4 Fusion of GMF and MLP-->, while DeepFM combines low- and high-order interactions over sparse feature fields for a CTR task (Guo et al., 2017)<!--ref:guo2017_deepfm--><!--anchor:section:Section 2 Our Approach, especially 2.1 DeepFM-->. Shared use of embeddings therefore does not make their input or target contracts interchangeable.

### Objectives and system role

Large-corpus systems commonly separate retrieval from ranking. YouTube's inspected system reduces a large corpus through candidate generation before richer ranking (Covington et al., 2016)<!--ref:covington2016_youtube--><!--anchor:section:Sections 2 System Overview, 3 Candidate Generation, and 4 Ranking-->, and sampled two-tower training introduces its own sampling-bias correction problem (Yi et al., 2019)<!--ref:yi2019_ndr--><!--anchor:section:Sections 2.3 Two-tower Models, 3 Modeling Framework, and 5 Neural Retrieval System-->. By contrast, DirectAU directly optimizes alignment and uniformity in collaborative filtering (Wang et al., 2022)<!--ref:wang2022_directau--><!--anchor:section:Sections 2.2 Alignment and Uniformity, 3 Alignment and Uniformity in CF, and 4 Direct Optimization-->. Architecture, objective, negative distribution, and system stage must therefore be controlled separately.

The same separation limits graph claims. LightGCN learns trainable ID embeddings and propagates them over an observed interaction graph (He et al., 2020)<!--ref:he2020_lightgcn--><!--anchor:section:Sections 3.1.1 Light Graph Convolution, 3.1.2 Layer Combination, and 3.3 Model Training-->. Improvement on sparse observed graphs does not establish a representation for an item with zero training edges. Across this theme, eight canonical scholarly records from eight nominal and eight dependency-adjusted source families converge on role- and objective-specific comparison; none reports a v5 architecture ranking [denominator: `theme_evidence_denominators.json#/themes/T2`]. Exact source keys: sarwar2001_itemcf, rendle2009_bpr, he2017_ncf, guo2017_deepfm, covington2016_youtube, yi2019_ndr, wang2022_directau, he2020_lightgcn. Exact family IDs: SF-R1-050, SF-R1-047, SF-R1-014, SF-R1-012, SF-R1-008, SF-R1-064, SF-R1-060, SF-R1-015.

## Theme 3 — Hybridization is precedent for ablation, not evidence of v5 efficacy

### Assumptions and objectives

Apriori defines association-rule mining through support and confidence thresholds (Agrawal & Srikant, 1994)<!--ref:agrawal1994_apriori--><!--anchor:section:Introduction, formal statement of the association-rule problem and minimum support/confidence thresholds-->. It is not thereby a recommender ranking model. Wide & Deep, in a different task, jointly trains an explicit linear cross-product component and an embedding/MLP component (Cheng et al., 2016)<!--ref:cheng2016_wide_deep--><!--anchor:section:Sections 2 Recommender System Overview and 3.1-3.3 Wide, Deep, and Joint Training-->. That paper supports a memorization/generalization decomposition, not Apriori efficacy.

The frozen Liu key is backed for R5 by the 2007 conference predecessor only. That inspected work combines sequential-rule and collaborative-filtering scores and therefore supports a bounded hybrid-method precedent (Liu et al., 2007)<!--ref:liu2009_hybrid_seq_cf--><!--anchor:figure:Replacement work Sections 3 and 3.1; Figures 1–4; Conclusions-->. It cannot support any Liu 2009 journal-specific implementation detail, numerical result, or expanded conclusion.

### Sequential and basket objectives

Sequential objectives also differ. SASRec uses causal self-attention for next-item prediction (Kang & McAuley, 2018)<!--ref:kang2018_sasrec--><!--anchor:section:Section III-C causality; Sections III-E and III-F prediction/objective; Section IV-D evaluation metrics-->, whereas BERT4Rec uses bidirectional sequence encoding with a masked-item Cloze objective (Sun et al., 2019)<!--ref:sun2019_bert4rec--><!--anchor:section:Section 3.3 Cloze task; Section 4.2 task settings and evaluation metrics-->. Neither source-native sampled evaluation is the locked v5 full-catalog protocol, and neither next-item objective is identical to a next-basket set objective.

For baskets, aggregate accuracy can mix repeat and exploration behavior. The reality-check analysis shows why repeat ratios and baseline behavior require decomposition (Li et al., 2023)<!--ref:li2023_nbr_reality--><!--anchor:figure:Figure 1 and Introduction contribution bullets; repeat-ratio and baseline analyses-->, and exploration-specific analysis further separates the harder novel-item question (Li et al., 2023)<!--ref:li2023_repetition_exploration--><!--anchor:section:Introduction definitions and research questions; exploration-only analyses-->. A repeat/explore-aware LightGCN study provides component and ablation precedent under its own data and protocol (Mansouri et al., 2026)<!--ref:mansouri2026_repeat_explore_lightgcn--><!--anchor:table:Abstract; Table 5 repeat/explore results; Section 6 ablation study; limitations-->. These eight canonical scholarly records across eight nominal and eight dependency-adjusted source families motivate a v5 ablation design, but they do not estimate H3 or show that the Apriori-aligned Wide branch improves the locked cohort [denominator: `theme_evidence_denominators.json#/themes/T3`]. Exact source keys: agrawal1994_apriori, cheng2016_wide_deep, liu2009_hybrid_seq_cf, kang2018_sasrec, sun2019_bert4rec, li2023_nbr_reality, li2023_repetition_exploration, mansouri2026_repeat_explore_lightgcn. Exact family IDs: SF-R1-001, SF-R1-007, SF-R1-033, SF-R1-026, SF-R1-053, SF-R1-030, SF-R1-032, SF-R1-035.

## Theme 4 — Zero-edge cold-item evidence requires content and adaptation boundaries

### Cold-item definition

Cold-item is not cold-user. For the v5 item-side cohort, a strict zero-edge item has no interaction in the training graph; a rare item with observed edges belongs to a sparse cohort instead. DropoutNet explicitly trains for cold-start conditions under its paper-specific framework (Volkovs et al., 2017)<!--ref:volkovs2017_dropoutnet--><!--anchor:section:Section 2, Framework; Section 4.2, Training for Cold Start; Section 5.1, CiteULike-->, while ALDI formalizes its own cold-item distillation setting (Huang et al., 2023)<!--ref:huang2023_aldi--><!--anchor:section:Section 2.1, Problem Formulation; Section 2.2, Existing Solutions-->. These sources support cohort separation, not automatic transfer of their thresholds or denominators to v5.

### Content signals and transfer

Sentence-BERT supports a rationale for semantic text embeddings (Reimers & Gurevych, 2019)<!--ref:reimers2019_sbert--><!--anchor:section:Abstract; Section 1, Introduction; Section 3, Training Details-->, but it supplies no retail recommendation objective or cold-item ranking evaluation. AlphaRec evaluates language representations inside a paper-specific recommendation and zero-shot protocol (Sheng et al., 2025)<!--ref:sheng2025_alpharec--><!--anchor:section:Section 4.1, AlphaRec; Section 5.2, Zero-Shot Recommendation; Section 6, Limitations-->. Semantic embedding quality is therefore a representation rationale, not recommender efficacy.

Transferable sequential recommenders also retain target-domain assumptions. UniSRec includes explicit downstream adaptation (Hou et al., 2022)<!--ref:hou2022_unisrec--><!--anchor:figure:Figure 1; Sections 2.2-2.4, especially 2.4 Adaptation to Downstream Recommendation Tasks-->, VQ-Rec evaluates vector-quantized transfer under its own setup (Hou et al., 2023)<!--ref:hou2023_vqrec--><!--anchor:section:Sections 2.1-2.3; Section 3.1 Experimental Setup-->, and UTGRec includes downstream fine-tuning (Zheng et al., 2026)<!--ref:zheng2026_utgrec--><!--anchor:section:Section 2.4.2, Downstream Fine-tuning; Sections 3.1.1 and 3.1.3-3.1.4; Section 3.3, Ablation Study-->. Architecture transfer is not H4 replication; data lineage, encoder, adaptation, split, candidates, metrics, and statistical procedure would all need alignment or declared deviation.

Content is not automatically neutral. Content representations aligned to collaborative teachers can inherit popularity structure (Meehan & Pauwels, 2025)<!--ref:meehan2025_cold_popbias--><!--anchor:section:Section 1, Introduction; Sections 3.1-3.3-->, while later sparse contrastive work evaluates a different content-based cold-item objective under bounded paper-native conditions (Meehan & Pauwels, 2026)<!--ref:meehan2026_semco--><!--anchor:section:Section 1, Introduction; Section 3.1, Problem Definition; Sections 3.2-3.3-->. The convergence here spans nine canonical scholarly records across nine nominal source families and at most eight dependency-adjusted families [denominator: `theme_evidence_denominators.json#/themes/T4`]. The adjustment applies `SF-R1-052 -> SF-R1-017` with `counting_effect=not_an_additional_independent_source_family`; shared authorship and benchmark lineages still prevent treating every record as an independent replication. Exact source keys: volkovs2017_dropoutnet, huang2023_aldi, reimers2019_sbert, sheng2025_alpharec, hou2022_unisrec, hou2023_vqrec, zheng2026_utgrec, meehan2025_cold_popbias, meehan2026_semco. Exact nominal family IDs: SF-R1-059, SF-R1-021, SF-R1-046, SF-R1-052, SF-R1-017, SF-R1-018, SF-R1-071, SF-R1-036, SF-R1-037.

## Theme 5 — External-resource compatibility and rights are separate axes

The Complete Journey evidence must remain layered. The provider describes the dataset's household, transaction, basket, time, product, and marketing structure, but access to the full provider payload remains unresolved (The Complete Journey provider, 2026)<!--ref:R-L5-COMPLETE-JOURNEY-PROVIDER--><!--anchor:section:The Complete Journey; What is inside; intended uses; source-file access form; Terms and Conditions section A.1-->. The R package exposes documented data objects and its own package license, but package availability and execution do not create an upstream dataset redistribution grant (completejourney R package, 2026)<!--ref:R-L5-COMPLETEJOURNEY-R-PACKAGE--><!--anchor:section:CRAN Description, License, Downloads; package manual named data-object entries; user-guide Accessing Data and Dataset Details sections-->.

Accordingly, provider availability, provider access, package license, local execution access, dataset rights, and redistribution permission remain six distinct fields. This theme concerns exactly two canonical operational resource records within one nominal and one dependency-adjusted operational source family; it is `FRAGILE_SINGLE_FAMILY` and is never mixed with scholarly denominators [denominator: `theme_evidence_denominators.json#/themes/T5`]. Exact operational resource keys: R-L5-COMPLETE-JOURNEY-PROVIDER, R-L5-COMPLETEJOURNEY-R-PACKAGE. Exact operational family ID: SF-R1-075. Complete Journey remains a planning candidate, not a passed H4 replication dataset.

## Convergence and divergence

Five convergence statements survive family-aware counting:

1. Evaluation design affects the meaning of offline comparisons: six canonical scholarly records, six nominal families, and six dependency-adjusted families [denominator: `theme_evidence_denominators.json#/themes/T1`].
2. Architecture, objective, input signal, and stage role must be separated: eight canonical scholarly records, eight nominal families, and eight dependency-adjusted families [denominator: `theme_evidence_denominators.json#/themes/T2`].
3. Hybrid and basket literature supports ablation structure but not the v5 H3 result: eight canonical scholarly records, eight nominal families, and eight dependency-adjusted families [denominator: `theme_evidence_denominators.json#/themes/T3`].
4. Cold-item content and transfer evidence requires explicit zero-edge, adaptation, and lineage boundaries: nine canonical scholarly records, nine nominal families, and at most eight dependency-adjusted families after the declared `SF-R1-052 -> SF-R1-017` edge [denominator: `theme_evidence_denominators.json#/themes/T4`].
5. Complete Journey compatibility and permission are layered: exactly two operational records in one nominal and one dependency-adjusted operational family; this is `FRAGILE_SINGLE_FAMILY` and is not a scholarly denominator [denominator: `theme_evidence_denominators.json#/themes/T5`].

The principal divergences are conditional rather than direct contradictions. Sampled evaluation can fail under naive regimes yet improve under estimator-specific designs; causal and bidirectional sequence objectives answer related but non-identical tasks; graph-collaborative and content-based methods differ in what signal exists for a zero-edge item; and transfer systems differ in adaptation and lineage. These distinctions resolve apparent conflict by narrowing scope, not by declaring one literature camp universally correct.

## Tensions and resolutions

#### Tension T-001

Krichene–Rendle and Li et al. are reconciled by estimator scope: a negative result for naive sampled ranking metrics does not imply that every estimator-specific sampling design is invalid. The v5 benchmark must name its estimator and validate it against the intended exact estimand.

#### Tension T-002

Candidate-universe sensitivity and split sensitivity are complementary protocol risks. Neither licenses post-result protocol changes; together they support precommitting both candidate and split rules.

#### Tension T-003

SASRec and BERT4Rec differ in information access and objective. The synthesis treats them as distinct sequential controls rather than interchangeable implementations of one objective.

#### Tension T-005

LightGCN and AlphaRec expose different signal-availability regimes. Observed-graph propagation addresses collaborative structure; language representations can supply content signal where collaborative edges are absent, but only a recommender evaluation can establish ranking efficacy.

#### Tension T-009

The repeat/explore literature is reconciled by outcome decomposition: aggregate basket performance and novel-item performance are separate targets, and a gain on one does not imply a gain on the other.

#### Tension T-010

UniSRec and VQ-Rec both concern transferable representations, but their representation and downstream adaptation contracts differ. They motivate explicit adaptation reporting rather than an adaptation-free transfer claim.

#### Tension T-011

Inherited-popularity analysis and sparse contrastive content learning can coexist: the former identifies a failure pathway in teacher-aligned content representations, while the latter evaluates a bounded mitigation route. Shared authorship and adjacent lineage are retained as a dependence caveat.

The remaining five assessed pairs are non-tensions or have insufficient overlap and therefore have `resolution_status: not_applicable`. No pair is scholar-confirmed at R5; all twelve remain `pending` for R6/user adjudication [denominator: `theme_evidence_denominators.json#/tension_population_counts`].

## Knowledge gaps

1. **Empirical gap:** no frozen source estimates the exact v5 H3 contrast of an Apriori train-only Wide branch versus No-Wide on the locked rule-aligned cohort. H3 remains `NOT_RUN`.
2. **Empirical gap:** no frozen source establishes H4 under the exact v5 encoder, external-data lineage, adaptation, split, candidate, metric, and statistical contract. H4 remains `NOT_RUN`.
3. **Methodological gap:** protocol equivalence between source-native and v5 implementations still requires adapter-parity tests; public code and official reproductions do not fill this gap.
4. **Measurement gap:** novel-item, repeat-item, and aggregate basket metrics need separate denominators and uncertainty reporting.
5. **Theoretical gap:** content-based cold-item work does not yet yield a general account of when collaborative-teacher alignment transfers useful structure versus popularity bias.
6. **Operational gap:** Complete Journey's full provider payload, dataset-rights basis, and redistribution permission remain unresolved even though the package is available and locally executable.

## Theoretical and methodological implications

The most defensible organizing framework is a contract matrix rather than an architecture ladder. Each candidate should be described by assumptions, available signals, objective, system stage, cohort definition, adaptation, and evaluation protocol. This prevents an architecture label from carrying unsupported conclusions about task role or cold-start capability.

Methodologically, the literature supports a two-table discipline: source-faithful reproduction results remain separate from harmonized v5 benchmark results. Within the harmonized table, H3 requires a component ablation on the frozen rule-aligned cohort, and H4 requires explicit external-data and adaptation provenance. These are design implications only; they are not benchmark outcomes.

## Bounded positioning

The frozen literature justifies evaluating a hybrid recommender that separates collaborative, sequential, content, and rule-derived signals under one locked protocol. It also justifies reporting warm, sparse-edge, and strict zero-edge item cohorts separately; decomposing repeat and novel-item behavior; and exposing objective, negative-sampling, and tuning differences. It does not justify claiming that Wide & Deep proves Apriori efficacy, that a content encoder solves recommendation, that transfer establishes H4 replication, or that any source-native architecture ranking will persist on v5.

R5 preserves exactly 22 conditional rows as `citation_ready_candidate`; the other 22 rows remain `planning_only` [denominator: `theme_evidence_denominators.json#/claim_population_counts`]. Their claim intents are unchanged, and all 44 rows now bind the separate counter-evidence overlay. Claim-level readiness is not Stage 2 authorization: Stage 2 production citations remain `NOT_AUTHORIZED`, and Stage 1B remains unsealed.

## Synthesis limitations

- The source set is frozen at 2026-08-21; no broad discovery was performed in R5.
- The 12-pair tension inventory is a scoped candidate-edge scan, not complete pairwise contradiction detection [denominator: `theme_evidence_denominators.json#/tension_population_counts`].
- Seven tension resolutions are analytical scope reconciliations and await scholar confirmation; none is self-confirmed.
- The Liu evidence is limited to the inspected 2007 predecessor for hybrid-method precedent and cannot support 2009-specific details or results.
- Complete Journey provider availability, package license, execution access, dataset rights, and redistribution permission remain separate; the full provider payload was not acquired.
- No page anchor appears in this synthesis. All visible citations use verified non-page locators from the frozen R4 registry.
- H1–H4 remain `NOT_RUN`. The initial R6 checkpoint and this bounded remediation overlay were performed; the fresh R6 re-audit, R7–R9, manuscript drafting, benchmark training/evaluation, and Stage 2 citation authorization were not performed.
