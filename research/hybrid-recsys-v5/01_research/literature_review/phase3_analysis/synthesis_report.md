# Stage 1B Synthesis Report — Pre-Audit

Status: central synthesis complete; independent Sol Ultra audit pending. This is an analysis artifact, not manuscript prose and not an audit verdict.

## Synthesis boundary

The synthesis integrates the frozen 55-source corpus across five search lanes. All citations below include a corpus slug and an explicit `anchor:none` marker because original PDFs were not locally acquired. Under ARS, these null locators are a known gate refusal for production citation emission. They are deliberately visible so the independent audit and Stage 2 source-acquisition pass cannot mistake identity verification for claim-level source verification.

## Literature matrix

| Theme | Canonical evidence | Collective finding | Evidence strength | Project implication |
|---|---|---|---|---|
| Evaluation and reproducibility | Krichene & Rendle (2020) <!--ref:krichene2020_sampled_metrics--><!--anchor:none:-->; Zhao et al. (2020) <!--ref:zhao2020_alternative_settings--><!--anchor:none:-->; Tamm et al. (2021) <!--ref:tamm2021_metric_consistency--><!--anchor:none:-->; Sun et al. (2023) <!--ref:sun2023_daisyrec2--><!--anchor:none:--> | Candidate construction, split, metric definition, aggregation, and tuning are parts of the estimand rather than interchangeable implementation details. | Strong | Keep exact temporal full-catalog evaluation and separate official reproduction from harmonized comparison. |
| Collaborative/deep/retrieval architectures | Sarwar et al. (2001) <!--ref:sarwar2001_itemcf--><!--anchor:none:-->; Rendle et al. (2009) <!--ref:rendle2009_bpr--><!--anchor:none:-->; He et al. (2017) <!--ref:he2017_ncf--><!--anchor:none:-->; He et al. (2020) <!--ref:he2020_lightgcn--><!--anchor:none:-->; Huang et al. (2013) <!--ref:huang2013_dssm--><!--anchor:none:--> | Comparator families encode different assumptions; two-tower retrieval additionally requires an explicit candidate-generation and negative-sampling contract. | Strong | Baseline diversity is justified, but paper-native rankings cannot predict v5 winners. |
| Wide/rule/hybrid mechanisms | Agrawal and Srikant (1994) <!--ref:agrawal1994_apriori--><!--anchor:none:-->; Cheng et al. (2016) <!--ref:cheng2016_wide_deep--><!--anchor:none:-->; Liu et al. (2009) <!--ref:liu2009_hybrid_seq_cf--><!--anchor:none:-->; Peng et al. (2022) <!--ref:peng2022_ham--><!--anchor:none:--> | Prior work establishes rule semantics, memorization/generalization framing, and precedents for fusing association and preference signals. It does not test the proposed Apriori-Wide causal contrast. | Moderate–strong | Treat H3 as a preregistered mechanism hypothesis, not a literature-backed result. |
| Sequential/basket novelty | Kang and McAuley (2018) <!--ref:kang2018_sasrec--><!--anchor:none:-->; Sun et al. (2019) <!--ref:sun2019_bert4rec--><!--anchor:none:-->; Li et al. (2023) <!--ref:li2023_nbr_reality--><!--anchor:none:-->; Li et al. (2023) <!--ref:li2023_mask_swap--><!--anchor:none:--> | Sequential baselines are protocol-sensitive, and aggregate basket accuracy can conceal repetition shortcuts or heterogeneous novelty behavior. | Strong | Report novel/repeat composition, cohort coverage, and source-versus-v5 protocol differences. |
| Cold-item/content/transfer | Volkovs et al. (2017) <!--ref:volkovs2017_dropoutnet--><!--anchor:none:-->; Wei et al. (2021) <!--ref:wei2021_clcrec--><!--anchor:none:-->; Hou et al. (2022) <!--ref:hou2022_unisrec--><!--anchor:none:-->; Sheng et al. (2025) <!--ref:sheng2025_alpharec--><!--anchor:none:--> | Content and transfer objectives can supply item-side representations when collaborative evidence is sparse, while collaborative graph methods still require interaction edges. | Strong | H2 may concern cold items only; SBERT is an encoder rationale, not an efficacy guarantee. |
| Vietnamese/public data | Tran et al. (2024) <!--ref:tran2024_viecomrec--><!--anchor:none:-->; Tran et al. (2024) <!--ref:tran2024_vietnamese_food--><!--anchor:none:-->; Nguyen (2026) <!--ref:nguyen2026_vihorec--><!--anchor:none:--> | Vietnamese resources exist, but each supports a reduced task and none preserves the complete v5 basket/order/session-plus-content contract. | Moderate | Frame the contribution around a reproducible Vietnamese retail benchmark/protocol, not dataset nonexistence or absolute novelty. |
| External compatibility | Jin et al. (2023) <!--ref:jin2023_amazon_m2--><!--anchor:none:-->; Normann et al. (2023) <!--ref:normann2023_otto--><!--anchor:none:-->; Robinson et al. (2024) <!--ref:robinson2024_relbench--><!--anchor:none:-->; dunnhumby (n.d.) <!--ref:completejourney_resource--><!--anchor:none:--> | Text-rich session/review sources often lack verified purchase/basket/user semantics; order-rich sources often omit item content or native baskets. | Moderate | Complete Journey and Coveo remain conditional; Amazon-M2 is architecture transfer, not automatic H4 replication. |

## Key themes

### 1. Evaluation is part of the scientific claim

The clearest convergence is methodological: exact versus sampled candidates, temporal versus leave-one-out splitting, metric formulas, user eligibility, aggregation, baseline tuning, and implementation provenance can change the meaning or ordering of results. Krichene and Rendle (2020) <!--ref:krichene2020_sampled_metrics--><!--anchor:none:--> and Li et al. (2023) <!--ref:li2023_reliable_sampling--><!--anchor:none:--> jointly support a conditional resolution: naive sampling is unsafe for exact-score interpretation, while improved estimators may be useful when exact scoring is impossible. This does not weaken the v5 decision to use full-catalog evaluation when feasible.

Anchor justification: the lane cards ground this theme in official abstracts/proceedings, but no source-local page/section locator is yet available.

The central implication is stricter than “use the same metric name.” The project must use one temporal split, candidate universe, seen-item mask, tie rule, metric implementation, tuning budget, and locked validation-selection process for all harmonized models. Official-code reproduction remains an adapter-validity receipt only.

### 2. Architecture families differ by assumption, not by transferable rank

ItemCF, BPR, NCF, LightGCN, and graph-contrastive methods span neighborhood, pairwise-ranking, nonlinear interaction, and propagation/augmentation assumptions. DirectAU and modern contrastive methods further show that objectives and representation geometry matter independently of architectural complexity. Therefore a “newer/deeper wins” narrative is not justified.

Two-tower positioning is especially conditional. DSSM and large-scale recommender systems establish independent encoders and candidate-generation precedents, but a project cannot claim a two-stage retrieval architecture until tower inputs, score function, negatives, retrieval cutoff, fusion point, and ranker boundary are frozen. The v5 full-catalog evaluator may evaluate a two-tower scoring model without implying a production ANN retrieval stage.

### 3. Wide, Apriori, and hybrid evidence supports a hypothesis—not H3

Apriori provides support/confidence and train-side rule-mining semantics; Wide & Deep provides memorization/generalization framing; sequential-rule/CF, HAM, and M² provide precedents for combining and ablating complementary components. These lines converge on architectural plausibility, not on the proposed effect.

The unique testable gap is whether a train-mined Apriori-derived Wide signal contributes under the same Deep branch, candidates, masks, seeds, tuning budget, calibration, and target. If held-out consequents define cohort membership, the honest label is “train-mined rule-aligned evaluation cohort,” not “train-defined cohort.” Only the frozen Full-minus-No-Wide paired estimate can support H3.

### 4. Novel behavior changes the interpretation of basket accuracy

Next-basket literature shows that repeat behavior and exploration/novel behavior can be conflated. Novel-specific interventions may help on some datasets and harm or fail on others. The project therefore needs cohort coverage, repeat/novel composition, and explicit novel-purchase semantics rather than relying on aggregate top-k quality alone.

This theme also blocks direct transplantation of SASRec/BERT4Rec/HAM/M²/BTBR metrics: their candidate sampling, split, target, and repeat treatment differ from v5.

### 5. Cold-item evidence has a hard cold-user boundary

Dropout, content–collaborative contrast, distillation, transferable sequence representation, and language representations converge on one bounded proposition: content can supply item-side information when collaborative item history is sparse or absent. They do not establish zero-history user effectiveness. Graph-contrastive controls remain useful for sparse collaborative data but still require interaction edges.

SBERT supports a text-embedding construction; it is not a recommender result and cannot license “SBERT solves cold start.” An SBERT-based substitution for another model's encoder is a separately labelled ablation, not faithful reproduction.

### 6. Dataset compatibility is a matrix, not a leaderboard

The external-resource review exposes a structural tradeoff. Amazon-M2 provides sessions and rich text but not verified purchase outcome or persistent users. OTTO provides clicks, carts, and orders but no item metadata. RelBench/H&M provide temporal purchase/content tasks but no native basket identity. Complete Journey is structurally closest to persistent household, basket, purchase, timestamp, and product description, but its exact edition and rights are unresolved. Coveo offers sessions, event types, search/catalog content, and purchase-intent structure, yet a strict purchase top-k protocol still requires an explicit compatibility audit.

Consequently, there is no unconditional H4 dataset. A failed compatibility gate yields H4 = NOT_TESTED; it does not authorize a reduced experiment to be renamed full replication.

## Contradictions and resolutions

| Claim A | Claim B | Resolution |
|---|---|---|
| Sampled metrics can distort method ordering. | Estimator-based sampling can recover global metrics under assumptions. | Conditional difference: exact full-catalog remains preferred when feasible; estimator results must remain distinctly labelled. |
| Deep/graph/modern methods report improvements in their native papers. | Reproduction studies show simple/tuned baselines and protocol choices can reverse conclusions. | No transferable ordering: v5 must select and test baselines under one frozen protocol. |
| Wide & Deep supports memorization/generalization. | The proposed Wide branch uses Apriori rules and a decoupled fusion not tested by the original paper. | Architecture rationale only; H3 remains NOT_RUN. |
| Content helps cold-start recommendation. | Collaborative graph controls can be strong under sparsity. | Different missingness regimes: sparse edges and zero-interaction items are not interchangeable. |
| Amazon-M2 is rich in sessions and content. | H4 requires a future-purchase/full-contract estimand. | Architecture-transfer evidence, not strict H4 replication. |
| Complete Journey appears structurally closest to H4. | Provider/package edition and rights metadata conflict or remain incomplete. | Leading conditional candidate; no execution or licensing claim until provenance lock. |
| A rule-aligned cohort can focus H3. | Outcome-labelled membership is not purely train-defined. | Rename and freeze the cohort builder; report whether membership uses held-out consequents. |

### Cross-paper tension inventory

```yaml
cross_paper_tensions:
  - pair_id: CP-001
    paper_a: krichene2020_sampled_metrics
    paper_b: li2023_reliable_sampling
    candidate_basis: opposite finding direction on shared metric-sampling question
    overlap_topic: sampled versus exact top-k evaluation
    a_finding: naive sampled metrics need not preserve exact/global ordering
    a_evidence_pointer: phase2_investigation/lanes/L1_evaluation_reproducibility.md > CLAIM_SOURCE_CARDS > L1-S01
    b_finding: adaptive or estimated sampling can improve recovery of global metric estimates
    b_evidence_pointer: phase2_investigation/lanes/L1_evaluation_reproducibility.md > CLAIM_SOURCE_CARDS > L1-S03
    pair_assessment: conditional_difference
    resolution_status: resolved_in_synthesis
    resolution_pointer: Synthesis Report > Contradictions and resolutions, row 1
    scholar_confirmation: pending
  - pair_id: CP-002
    paper_a: cheng2016_wide_deep
    paper_b: agrawal1994_apriori
    candidate_basis: shared RQ subtopic
    overlap_topic: explicit memorization signals in the proposed Wide branch
    a_finding: crossed features and a deep component can be jointly trained for memorization and generalization
    a_evidence_pointer: phase2_investigation/lanes/L2_recommender_architectures.md > CLAIM_SOURCE_CARDS > L2-04
    b_finding: support and confidence define frequent association rules over transactions
    b_evidence_pointer: phase2_investigation/lanes/L3_basket_sequential_hybrid.md > ACCEPTED_SOURCES > AR-APR
    pair_assessment: insufficient_overlap
    resolution_status: not_applicable
    scholar_confirmation: pending
  - pair_id: CP-003
    paper_a: he2020_lightgcn
    paper_b: wei2021_clcrec
    candidate_basis: shared construct/outcome/measure
    overlap_topic: recommendation under sparse or missing item interaction evidence
    a_finding: graph propagation uses collaborative user-item edges
    a_evidence_pointer: phase2_investigation/lanes/L2_recommender_architectures.md > CLAIM_SOURCE_CARDS > L2-09
    b_finding: content-collaborative contrast targets cold-start representation
    b_evidence_pointer: phase2_investigation/lanes/L4_cold_content_transfer.md > CLAIM_SOURCE_CARDS > L4-01 to L4-04
    pair_assessment: conditional_difference
    resolution_status: resolved_in_synthesis
    resolution_pointer: Synthesis Report > Contradictions and resolutions, row 4
    scholar_confirmation: pending
  - pair_id: CP-004
    paper_a: jin2023_amazon_m2
    paper_b: completejourney_resource
    candidate_basis: agent-noted cross-cluster
    overlap_topic: strict external-dataset compatibility
    a_finding: multilingual sessions and rich item text support architecture transfer but not verified persistent-user purchase replication
    a_evidence_pointer: phase2_investigation/lanes/L5_vietnamese_external_datasets.md > ACCEPTED_SOURCES > L5-EXT-01
    b_finding: household purchases, baskets, timestamps, and product descriptions are structurally close to the full contract
    b_evidence_pointer: phase2_investigation/lanes/L5_vietnamese_external_datasets.md > ACCEPTED_SOURCES > L5-EXT-08
    pair_assessment: conditional_difference
    resolution_status: resolved_in_synthesis
    resolution_pointer: Synthesis Report > Contradictions and resolutions, rows 5 to 6
    scholar_confirmation: pending
  - pair_id: CP-005
    paper_a: li2023_nbr_reality
    paper_b: li2023_mask_swap
    candidate_basis: shared construct/outcome/measure
    overlap_topic: novel versus repeat next-basket behavior
    a_finding: aggregate next-basket accuracy can hide repeat/explore heterogeneity
    a_evidence_pointer: phase2_investigation/lanes/L3_basket_sequential_hybrid.md > ACCEPTED_SOURCES > NBR-REALITY
    b_finding: novel-specific masking/swap interventions do not help uniformly across datasets
    b_evidence_pointer: phase2_investigation/lanes/L3_basket_sequential_hybrid.md > ACCEPTED_SOURCES > BTBR
    pair_assessment: no_material_conflict
    resolution_status: not_applicable
    scholar_confirmation: pending
```

Coverage Note: 55 papers/resources in the corpus; 5 candidate pairs considered using opposite direction, shared RQ subtopic, shared construct, and agent-noted cross-cluster signals. This is a scoped advisory scan, not complete pairwise contradiction detection. Cross-neighborhood pairs may be absent. Bibliographic coupling was not available and was not used to exclude any pair. Scholar confirmation remains pending.

## Knowledge gaps

1. **Empirical/mechanism gap:** no source tests the exact decoupled Apriori-Wide plus Deep/two-tower architecture under the frozen temporal full-catalog v5 estimand.
2. **Methodological gap:** source-native results rarely share the same split, candidate set, metric semantics, tuning budget, and evaluator; faithful official reproduction and harmonized comparison must therefore remain separate.
3. **Dataset gap:** no reviewed public source is unconditionally verified to preserve persistent identity, purchase outcome, native baskets/sessions, timestamps, item text, and rights/version provenance simultaneously.
4. **Geographic/domain gap:** Vietnamese resources provide valuable language/domain coverage but not the complete retail mechanism/task contract.
5. **Evidence gap:** core claim locators are absent because original PDFs were not acquired; source existence is verified, claim faithfulness is not yet production-grade.
6. **Experimental gap:** H1–H4 and deployment gates remain NOT_RUN; literature cannot supply their answers.

## Evidence convergence map

- Strong: evaluation/protocol dependence — 11 sources.
- Strong: architecture/comparator diversity — 12 sources.
- Moderate–strong: sequential/rule/hybrid rationale — 11 sources.
- Strong but bounded: cold-item/content/transfer — 9 sources.
- Moderate: Vietnamese/external compatibility — 12 sources, including preprints/operational resources.
- Gap: strict-H4-ready external dataset — 0 unconditional candidates.
- Gap: manuscript-ready non-null source locators — 0 acquired originals.

## Theoretical integration and positioning

The evidence supports a conditional positioning: established recommender components encode complementary inductive biases, while evaluation design can dominate apparent progress. The paper's potentially defensible contribution is therefore not invention of the components. It is a reproducible test of whether their controlled integration helps under one frozen Vietnamese retail protocol, with explicit mechanism, cold-item, external-compatibility, and systems gates.

That positioning remains provisional in two ways. First, it requires a dedicated novelty audit before any “first” language. Second, it requires sealed experiments: a negative, null, cohort-only, or incompatibility result is scientifically valid and must narrow the final claim.

## Synthesis limitations

- This analysis does not audit itself and does not claim Stage 1B passed.
- All citation anchors are `none`; production citation emission is therefore blocked.
- The review is targeted and may miss cross-neighborhood tensions or late 2026 work.
- Semantic Scholar was unavailable; two-index plus official-record verification was used with explicit degradation.
- Dataset rights and exact revisions remain unresolved for several candidates.
- Evidence levels use the ARS generic hierarchy with technology-field fitness adjustments; they are not clinical-style causal grades.
