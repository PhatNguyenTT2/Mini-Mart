# Stage 2 Paper Outline

**Project:** `hybrid-recsys-v5`  
**Paper type:** methods/empirical  
**Working title:** *Reproducible Hybrid Recommendation for Vietnamese Retail*  
**Language:** English  
**Citation style:** IEEE numbered, venue-neutral  
**Author metadata:** intentionally blank  
**Status:** OUTLINE_APPROVED_USER_CONFIRMED

**Approval record:** The user approved this outline and requested continuation
to the P2-G3 argument blueprint and P2-G4--P2-G6 drafting steps on
2026-09-12. The approval covers the structure and scope only; it does not
authorize any blocked empirical or superiority claim.

## Scope and Evidence Boundary

This outline is the Stage 2 architecture deliverable. It is not an argument
blueprint and it is not manuscript prose. The paper may describe the design of
the reproducible protocol, the bounded literature synthesis, and the admitted
public protocol validation. It may not claim that the proposed Hybrid is
superior, that the strict official reproduction succeeded, or that the
harmonized v5 comparison is complete.

The four admitted result rows belong exclusively to the
`PUBLIC_DATA_PROTOCOL_VALIDATION` namespace. They are descriptive protocol
evidence. `OFFICIAL_PROTOCOL_REPRODUCTION` has zero admitted rows,
`HARMONIZED_V5_COMPARISON` has zero admitted rows, and the proposed Hybrid has
no admitted result. No raw numeric join between these namespaces is planned.

## Structure Pattern: Conference-Oriented IMRaD

The paper uses a compact conference-oriented IMRaD structure with a thematic
Related Work section. The narrative moves from the comparability problem, to
the protocol and estimands, to the evidence boundary, and finally to a
conditional interpretation. The follow-up harmonized-v5 experiment is named as
the required next empirical gate, not silently presented as completed work.

## Overview

The Introduction motivates reproducible offline recommendation evaluation in a
sparse retail setting and narrows the contribution to protocol design and
auditable evidence handling. Related Work synthesizes collaborative, deep,
two-tower, rule-based, sequential, graph, content, and cold-item methods while
keeping source-native results separate from the locked v5 estimand. Methodology
defines the dataset/protocol/evaluator boundary and the conditional Hybrid
question. Experimental Design and Evidence Scope separates the public
validation lane from the closed official lane and the sealed v5 lane. Results
reports only descriptive public protocol validation. Discussion interprets what
can and cannot be learned from those rows, and Conclusion restates the
conditional contribution without a superiority claim.

## Review Criteria Coverage Plan

`criteria_binding_unavailable`: no venue-specific ReviewTargetContext or
ReviewCriteriaBindingManifest is active because the venue matrix remains
`NOT_SELECTED`. The outline therefore makes no venue-fit claim and maps only
scientific validity and evidence needs from the approved research plan.

## Detailed Outline

### 1. Introduction (~850 words)

**Purpose:** Establish the practical and methodological problem, state the
bounded research question, and define what this paper contributes before any
follow-up result is available.

**Serves sub-question:** Framing; no inherited sub-question binding.

**Content:**

- **1.1 Retail recommendation under sparse and changing behavior**
  - Frame offline top-k recommendation as a ranking problem involving sparse
    user-item observations, temporal behavior, item metadata, and potentially
    novel items.
  - Explain why a Vietnamese retail context is a domain setting for the
    controlled benchmark, not evidence about Vietnamese shoppers in general.
  - Keep the internal benchmark label `controlled/semi-synthetic` visible.
- **1.2 The comparability problem**
  - Explain how split construction, candidate universe, seen-item masking,
    relevance definition, negative sampling, and evaluator choice can change
    reported outcomes.
  - Motivate a shared full-catalog protocol and auditable result lineage rather
    than direct copying of source-paper metrics.
  - Use the literature's evaluation and split-sensitivity evidence only within
    the bounded wording of `L3-PROTO-007`.
- **1.3 Method families and the conditional Hybrid question**
  - Introduce ItemCF/BPR, Wide and Deep, Two-Tower retrieval/ranking, rules,
    sequential models, and graph/content approaches as distinct signal and
    objective families.
  - State that the proposed decoupled Wide-and-Deep Two-Tower Hybrid is a
    hypothesis about complementary memorization and generalization signals,
    not a pre-validated winner.
- **1.4 Research question and contributions**
  - State the primary RQ and the four sub-questions exactly as bounded in the
    Stage 1A RQ brief.
  - Present three permitted contributions: a provenance-aware shared protocol,
    explicit separation of evidence namespaces, and an auditable public
    protocol validation with limitations.
  - State the boundary: no Hybrid result, H1-H4 result, production claim,
    causal claim, or state-of-the-art claim is made in this version.

**Evidence and claim IDs:** `L2-CLAIM-ITEMCF-BPR-001`,
`L2-CLAIM-TWO-STAGE-003`, `L2-CLAIM-WIDE-DEEP-004`, `L3-PROTO-007`,
`L3-HYB-006`, `L3-NBR-004`.

**Transition to Section 2:** The Introduction identifies the comparison and
provenance problem; Related Work now shows why each signal family requires its
own task and evaluator assumptions.

### 2. Related Work (~1,350 words)

**Purpose:** Synthesize prior work by signal, objective, and evaluation
contract, then position the current protocol without importing source-native
rankings.

**Serves sub-question:** Framing and RQ1-RQ4 positioning; no empirical result
binding.

**Content:**

- **2.1 Evaluation and reproducibility in recommender systems**
  - Contrast source-native metrics with a shared full-catalog evaluation.
  - Discuss temporal split sensitivity, target construction, implementation
    choices, and training budget as sources of ranking instability.
  - End with the positioning sentence: prior work motivates protocol control,
    but does not provide a v5 ranking or authorize changing the frozen split
    after observing outcomes.
- **2.2 Collaborative, neural, and sequence recommendation**
  - Distinguish ItemCF similarity aggregation from BPR's pairwise implicit
    objective.
  - Distinguish NCF ID-based nonlinear interaction modeling from DeepFM's
    sparse-field CTR contract.
  - Contrast SASRec causal attention and BERT4Rec masked-item training, while
    noting their paper-native candidate/sampling designs.
  - End with the positioning sentence: these families supply comparator and
    objective precedents, not directly comparable v5 results.
- **2.3 Wide and Deep, Two-Tower, and semantic representations**
  - Explain Wide and Deep as memorization plus generalization, without equating
    its production result with an Apriori effect.
  - Distinguish retrieval, matching, pre-ranking, and ranking roles in
    two-stage systems.
  - Position recent pair-aware or cross-interaction tower controls as evidence
    that the role of a tower must be named precisely.
  - Discuss objective/sampling effects separately from encoder complexity.
  - End with the positioning sentence: the paper tests a decoupled architecture
    under one locked ranking contract; it does not assume an architecture
    ordering from these sources.
- **2.4 Apriori, association rules, and next-basket recommendation**
  - Define support and confidence as rule-mining thresholds rather than
    treating Apriori as a ranking model.
  - Review multi-item rules, next-basket baselines, repeat/explore behavior,
    and prior hybrid component ablations.
  - State why aggregate basket accuracy cannot by itself establish novel-item
    gain.
  - End with the positioning sentence: the Wide/rule branch is a mechanism
    hypothesis requiring a train-defined cohort and a no-Wide ablation.
- **2.5 Graph and contrastive recommendation**
  - Summarize graph propagation and graph-contrastive controls as methods that
    learn from observed interaction edges and trainable IDs.
  - Separate sparse-graph performance from strict zero-edge item capability.
  - End with the positioning sentence: graph results motivate controls and
    cold-item definitions, but do not establish v5 or zero-edge performance.
- **2.6 Content, cold-item, and transfer learning**
  - Define strict zero-edge cold items by the training graph and require
    separate denominators for warm, sparse, and zero-edge cohorts.
  - Explain why semantic text quality is not recommendation quality.
  - Discuss target-domain adaptation assumptions, shared lineage, inherited
    popularity bias, and declared deviations needed for a replication.
  - End with the positioning sentence: external and cold-item claims remain
    conditional on matching encoder, data, adaptation, split, candidates,
    metrics, and statistics.

**Evidence and claim IDs:** `L3-PROTO-007`, `L2-CLAIM-ITEMCF-BPR-001`,
`L2-CLAIM-NCF-DEEPFM-002`, `L3-SEQ-003`, `L2-CLAIM-WIDE-DEEP-004`,
`L2-CLAIM-TWO-STAGE-003`, `L2-CLAIM-OBJECTIVE-006`,
`L2-CLAIM-RECENT-TOWER-CONTROLS-007`, `L3-APR-001`, `L3-BTBR-005`,
`L3-HYB-006`, `L3-NBR-004`, `L3-RULE-002`, `L2-CLAIM-GRAPH-ZERO-EDGE-005`,
`L4-CC-01`, `L4-CC-02`, `L4-CC-03`, `L4-CC-04`, `L4-CC-05`, `L4-CC-06`,
`L4-CC-07`, `L4-CC-08`.

**Transition to Section 3:** The synthesis shows that model names are not
enough for comparison; the next section specifies the data, protocol, and
evaluator contracts that make the proposed comparison interpretable.

### 3. Methodology and Protocol (~1,100 words)

**Purpose:** Define the study design and the frozen evaluation contract without
claiming that the planned Hybrid experiment has been run.

**Serves sub-question:** RQ1-RQ5 methodological specification.

**Content:**

- **3.1 Study design and causal boundary**
  - Describe the work as a quantitative comparative offline benchmark.
  - Define per-user metrics nested within training seeds as the analysis unit.
  - State that the design estimates comparative algorithmic performance under a
    protocol, not causal effects on users, revenue, or production behavior.
- **3.2 Dataset and temporal protocol**
  - Describe v5 as a controlled/semi-synthetic Vietnamese retail benchmark.
  - Specify the dataset-manifest fields, immutable temporal split, user/item
    coverage checks, item-text provenance, and raw-to-internal mapping.
  - Treat counts as contract facts pending lineage receipts, not empirical
    findings.
- **3.3 Candidate universe, relevance, masking, and cold cohorts**
  - Define full-catalog scoring, novel-purchase eligibility, seen-item masking,
    deterministic tie handling, and strict zero-edge cold-item cohorts.
  - Require cohort denominators and exclusion-flow receipts.
- **3.4 Models, objective, and adapter provenance**
  - Define Random/MostPop controls, faithful reference adapters, independent
    Deep, Wide/Rule-only, and proposed Hybrid as separate model descriptors.
  - Keep BPR-style objective, negative sampling, feature inputs, rule fitting,
    configuration, checkpoint, and adapter hashes explicit.
  - State that the Hybrid is not promoted until follow-up execution and audit.
- **3.5 Metrics and statistical plan**
  - Define NDCG@10 as primary, HR@10 and macro per-user GAUC as confirmatory
    supporting outcomes, and Recall@10 as reporting compatibility output.
  - Specify three seeds, per-user vectors, hierarchical paired bootstrap, 95%
    intervals, and Holm correction for exploratory comparisons.
  - State no imputation of failed seeds and no post-test comparator changes.

**Evidence and claim IDs:** `L3-PROTO-007`, `L4-CC-01`, `L4-CC-02`,
`L4-CC-03`, `L4-CC-04`, `L4-CC-08`, `L2-CLAIM-OBJECTIVE-006`.

**Transition to Section 4:** The protocol defines what a valid comparison would
be; Section 4 distinguishes the evidence lanes that are currently complete,
closed, or deferred.

### 4. Experimental Design and Evidence Scope (~800 words)

**Purpose:** Make the paper's current evidentiary status auditable and prevent
the descriptive public lane from being mistaken for the proposed experiment.

**Serves sub-question:** RQ1-RQ5 evidence governance.

**Content:**

- **4.1 Evidence namespaces**
  - Define `OFFICIAL_PROTOCOL_REPRODUCTION`,
    `PUBLIC_DATA_PROTOCOL_VALIDATION`, and `HARMONIZED_V5_COMPARISON` as
    independent namespaces.
  - State the source-bound RecBole/MovieLens lane and its descriptive role.
  - State that the official illustrative center is closed incomparable and that
    v5 remains sealed with major limitations.
- **4.2 Admitted public validation**
  - Describe the one Pop run and three BPR seeds that passed the independent
    artifact audit.
  - Report that four rows are admissible only for descriptive protocol
    validation; defer exact numeric table cells to artifact import in the prose
    drafting stage.
  - Explicitly exclude significance, superiority, Hybrid validation, and
    cross-namespace numeric comparison.
- **4.3 Follow-up harmonized-v5 experiment**
  - Specify the required comparator registry, validation-only tuning, three
    final seeds, TEST opening, per-user artifacts, bootstrap, and ablations.
  - State that H1-H4 and efficiency remain `NOT_RUN` or `NOT_TESTED` until the
    new packet is completed and independently audited.
- **4.4 External validity and reproducibility**
  - Keep full-mechanism external validity separate from Vietnamese sensitivity.
  - Require task/signal/license compatibility before calling a result a full
    replication; otherwise label it a reduced-method sensitivity analysis.

**Evidence and claim IDs:** `L3-PROTO-007`, `L3-HYB-006`, `L4-CC-05`,
`L4-CC-06`, `L4-CC-08`.

**Transition to Section 5:** Once the evidence lanes are separated, the small
set of currently admissible observations can be reported without implying the
unrun scientific comparison.

### 5. Results: Descriptive Public Protocol Validation (~600 words)

**Purpose:** Report only the four P5-admitted public protocol rows and their
traceability status.

**Serves sub-question:** Procedural validation only; no H1-H4 result.

**Content:**

- **5.1 Runtime and audit completeness**
  - Report the frozen Pop/BPR run inventory, source/data/protocol bindings,
    evaluator identity, and independent audit status.
  - Link every table cell to the admitted aggregate artifact and its hash.
- **5.2 Descriptive metric table**
  - Present the four rows within the
    `PUBLIC_DATA_PROTOCOL_VALIDATION` namespace, with NDCG@10 and the other
    admitted diagnostics as descriptive values.
  - Report BPR seed variability without inferential comparison to Pop or to
    v5.
- **5.3 Explicit non-results**
  - State that no Hybrid, official numeric reproduction, v5 harmonized row,
    paired per-user inference, external-validity, or efficiency result is
    admitted by this stage.

**Evidence and claim IDs:** No literature claim is introduced here. Every
number must be imported from the AIS-R8 P5-admitted artifact namespace; no
number may be copied from `workspace/final/paper.tex` or from source papers.

**Transition to Section 6:** The descriptive lane demonstrates traceability of
the protocol, not the effectiveness of the proposed architecture; the
Discussion therefore focuses on interpretation and limitations.

### 6. Discussion and Limitations (~950 words)

**Purpose:** Interpret the bounded contribution, distinguish procedural from
scientific evidence, and state the exact work required before superiority or
external-validity claims can be made.

**Serves sub-question:** All RQs as limitation-aware interpretation.

**Content:**

- **6.1 What the current evidence establishes**
  - Establish auditable execution of a pinned public protocol and explicit
    namespace separation.
  - Explain why this is useful for reproducibility without treating it as an
    architecture ranking.
- **6.2 What remains unresolved**
  - Discuss the absent Hybrid result, closed official reproduction, sealed v5
    comparison, absent paired inference, untested H4, and untested efficiency.
  - Keep controlled/generated behavior distinct from observed shopper behavior.
- **6.3 Threats to validity**
  - Internal validity: adapter fidelity, split/candidate/masking parity, and
    failed-run handling.
  - Construct validity: offline metrics do not equal satisfaction, revenue, or
    causal impact; cold-item does not mean cold-user.
  - Statistical conclusion validity: three seeds and selection rules require
    the preregistered paired analysis.
  - External validity: source-family dependence, license/access constraints,
    and task mismatch may leave H4 `NOT_TESTED`.
- **6.4 Follow-up decision criteria**
  - Define the conditions for reporting Hybrid, cold-item, Wide-branch, and
    external claims after the new experiment packet is audited.
  - Preserve null or negative outcomes as valid conclusions.

**Evidence and claim IDs:** `L2-CLAIM-GRAPH-ZERO-EDGE-005`, `L3-BTBR-005`,
`L3-HYB-006`, `L3-NBR-004`, `L4-CC-01`, `L4-CC-03`, `L4-CC-05`,
`L4-CC-06`, `L4-CC-07`, `L4-CC-08`.

**Transition to Section 7:** The limitations define the conditions under which
the protocol can support a later empirical conclusion; the Conclusion states
only the contribution currently supported.

### 7. Conclusion (~300 words)

**Purpose:** Close with a precise, conditional summary of the method and
evidence boundary.

**Serves sub-question:** Overall RQ framing; no new empirical claim.

**Content:**

- Restate the reproducibility problem and the value of a fixed full-catalog
  protocol with explicit provenance.
- Summarize the three permitted contributions and the four descriptive public
  validation rows.
- State that the proposed Hybrid's effectiveness remains an open empirical
  question requiring the follow-up harmonized-v5 experiment.
- Avoid superiority, SOTA, production, causal, and cross-dataset claims.

**Sources:** No new source; synthesize Sections 1-6.

**Transition:** Terminal section.

## Evidence Map

The following mapping assigns every source used by the authorized 22 claim
cards to at least one planned section. The source key and locator IDs are
resolved in `claim_citation_matrix_stage2.json`; this table is a navigation
map, not a new evidence judgment.

| Planned section | Source keys | Evidence role |
|---|---|---|
| 1 Introduction; 2.2 | `sarwar2001_itemcf`, `rendle2009_bpr`, `he2017_ncf`, `guo2017_deepfm`, `kang2018_sasrec`, `sun2019_bert4rec` | Method-family and objective distinctions |
| 1 Introduction; 2.1; 2.3 | `covington2016_youtube`, `yi2019_ndr`, `wang2025_t2diff`, `cheng2016_wide_deep`, `wang2022_directau`, `yuan2025_contextgnn` | Two-stage, tower, Wide/Deep, and objective boundaries |
| 2.1; 2.4 | `gusak2025_time_split`, `petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo` | Split and reproducibility sensitivity |
| 2.4 | `agrawal1994_apriori`, `ghoshal2014_multi_item_rules`, `li2023_mask_swap`, `li2023_nbr_reality`, `li2023_repetition_exploration`, `liu2009_hybrid_seq_cf`, `peng2022_ham`, `peng2023_m2`, `mansouri2026_repeat_explore_lightgcn` | Rules, next-basket behavior, and hybrid ablation precedent |
| 2.5 | `he2020_lightgcn`, `yu2022_simgcl`, `cai2023_lightgcl` | Graph and contrastive limits |
| 2.6; 3.3; 6 | `volkovs2017_dropoutnet`, `huang2023_aldi`, `reimers2019_sbert`, `hou2022_unisrec`, `hou2023_vqrec`, `sheng2025_alpharec`, `zheng2026_utgrec`, `meehan2025_cold_popbias`, `meehan2026_semco` | Cold-item, content, transfer, and lineage boundaries |

## Word Count Summary

| Section | Target words |
|---|---:|
| Introduction | 850 |
| Related Work | 1,350 |
| Methodology and Protocol | 1,100 |
| Experimental Design and Evidence Scope | 800 |
| Results | 600 |
| Discussion and Limitations | 950 |
| Conclusion | 300 |
| **Body total** | **5,950** |
| Abstract (separate) | 200 |

## Outline Quality Gate

- Recognized structure pattern: **PASS** (`Conference-Oriented IMRaD`).
- Section purposes: **PASS** (all seven sections have a purpose).
- Evidence assignment: **PASS** (all 22 authorized claim IDs and all 35
  referenced source keys are assigned).
- Transition logic: **PASS** (each adjacent section boundary is specified).
- Scope discipline: **PASS** (no Hybrid result, H1-H4 result, stale historical
  number, or prohibited superiority claim is introduced).
- Review-target binding: **criteria_binding_unavailable** (venue not selected).
- User outline approval: **PASS_USER_APPROVED** (2026-09-12).

**Checkpoint result:** The approval gate is satisfied. The Argument Blueprint
and manuscript draft were created in the dedicated Stage 2 namespace. The next
mandatory checkpoint is the independent Stage 2.5 integrity review.
