# Stage 2 Argument Blueprint

**Project:** `hybrid-recsys-v5`  
**Stage:** `P2-G3`  
**Status:** `ARGUMENT_BLUEPRINT_COMPLETE`  
**Paper:** *Reproducible Hybrid Recommendation for Vietnamese Retail*  
**Argument mode:** conditional, evidence-bounded methods/empirical paper

## Central Thesis

This paper argues that a decoupled Wide-and-Deep recommender can only be
interpreted through a fixed, provenance-aware full-catalog protocol. The paper
therefore contributes a reproducibility and comparison framework, while the
effect of the proposed Hybrid on the controlled Vietnamese benchmark remains an
empirical question for a separately audited follow-up experiment.

The thesis is deliberately conditional. The current evidence establishes the
need for protocol control and the feasibility of a bounded public validation
lane; it does not establish a model ordering for the controlled benchmark or
an effect on users, revenue, or deployment outcomes.

## Argument Scope and Terms

- `Public validation` denotes the four admitted Pop/BPR rows in the
  `PUBLIC_DATA_PROTOCOL_VALIDATION` namespace.
- `Controlled benchmark` denotes the v5 dataset and its declared temporal,
  item-cold, rule-aligned, and full-catalog contracts. Its numeric rows remain
  outside the paper result set for this manuscript version.
- `Official reproduction` denotes a source-native reproduction lane. The
  current lane is closed as incomparable and cannot supply a baseline number.
- `Hybrid` denotes the proposed combination of a deep two-tower score and a
  train-defined rule/Wide score. It is a hypothesis, not an observed result.

## Sub-Arguments and CER Chains

### A1. Evaluation protocol is part of the estimand

**Claim.** A recommender result is interpretable only relative to its target
event, split, candidate universe, masking rule, metric implementation,
aggregation rule, and training procedure.

**Evidence.** The retained split and replicability sources document sensitivity
to temporal partitioning, target construction, implementation choices, and
training conditions (`L3-PROTO-007`; locators
`LOC-R4-S-gusak2025_time_split-01` and
`LOC-R4-S-petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo-01`).

**Reasoning.** If those choices alter the population of prediction events or
the ordering of candidates, two numbers with the same metric label estimate
different quantities. A shared evaluator and an immutable protocol consequently
provide the comparison object, rather than merely improving documentation.

**Counter-argument.** A widely used library or a familiar metric name may be
adequate for practical comparison, even when details differ.

**Rebuttal strategy.** Concede that a library reduces implementation effort,
but separate library identity from protocol equivalence. Report source-native
results as their own evidence surface and admit a cross-method row only after
the relevant bindings are replayable.

**Strength.** Strong for the methodological contribution; it does not by itself
support any claim about which model is most effective.

### A2. Model names conceal distinct signal and objective contracts

**Claim.** Item-neighbor aggregation, pairwise implicit learning, feature-field
interaction, two-stage retrieval, and two-tower scoring must be compared as
distinct contracts rather than as interchangeable implementations.

**Evidence.** ItemCF uses historical item overlap and neighbor aggregation
(`L2-CLAIM-ITEMCF-BPR-001`; locators
`LOC-R4-S-sarwar2001_itemcf-01` and `LOC-R4-S-rendle2009_bpr-01`). NCF and
DeepFM use different input and task formulations (`L2-CLAIM-NCF-DEEPFM-002`).
Industrial retrieval references separate candidate generation from ranking
(`L2-CLAIM-TWO-STAGE-003`), and Wide & Deep gives a memorization/generalization
decomposition (`L2-CLAIM-WIDE-DEEP-004`).

**Reasoning.** A result can change because of the encoder, the objective, the
negative distribution, or the system stage. The proposed design must therefore
export component scores and retain model, data, and evaluator provenance before
any component attribution is attempted.

**Counter-argument.** A single common evaluator already makes all methods fair,
so model-specific details need not be retained in the paper.

**Rebuttal strategy.** A common evaluator controls the output measurement, not
the training process or the meaning of an input. Preserve native objectives
where faithful reproduction is intended, and disclose deviations when an
adapter changes the contract.

**Strength.** Strong for protocol design; moderate for the proposed
memorization/generalization interpretation until the ablation is run.

### A3. The rule branch and cold-item claims require explicit cohorts

**Claim.** Association-rule signals and item-side content signals can motivate
the Hybrid design, but their contribution must be tested on train-defined
cohorts with separate denominators and a matching ablation.

**Evidence.** Apriori defines support and confidence as rule-mining thresholds,
not as a recommender ranking objective (`L3-APR-001`; locator
`LOC-R4-S-agrawal1994_apriori-01`). Prior multi-item and next-basket work
provides conditional rule and component-comparison precedents (`L3-RULE-002`,
`L3-HYB-006`). Next-basket analyses distinguish repeat behavior from
exploration (`L3-BTBR-005`, `L3-NBR-004`). Cold-start sources define the
zero-edge boundary and motivate separate warm, sparse, and zero-edge cohorts
(`L4-CC-01`, `L4-CC-02`).

**Reasoning.** Aggregate basket accuracy can be dominated by repeat behavior,
while a rare item with one training edge is not a strict zero-edge item. A
train-only rule fit, a no-Wide ablation, and cohort-specific denominators are
needed to attribute any observed change to the proposed mechanism.

**Counter-argument.** If the full model has a higher aggregate score, the
component explanation is sufficiently clear for an applied paper.

**Rebuttal strategy.** Treat the aggregate score as an outcome, not a mechanism
test. Require component exports, leakage checks, and the preregistered cohort
contrast; otherwise report the mechanism as unresolved.

**Strength.** Moderate. The literature supports the design logic, but the
central mechanism question has no admitted result in this stage.

### A4. Evidence namespaces are necessary for honest synthesis

**Claim.** Public protocol validation, source-native reproduction, controlled
v5 comparison, and external validity are different evidence surfaces and must
not be numerically merged.

**Evidence.** The Phase 1E admission decision admits four descriptive Pop/BPR
rows in `PUBLIC_DATA_PROTOCOL_VALIDATION`, closes the official lane as
incomparable, and retains zero admitted v5 rows. Transfer and content sources
also show why encoder, adaptation, data lineage, and task definitions must be
matched before an external result is treated as a replication (`L4-CC-04`
through `L4-CC-08`).

**Reasoning.** Namespace separation prevents a procedurally successful public
run from becoming evidence for an unexecuted Hybrid comparison. It also keeps
external validity conditional on the exact task and data bindings rather than
on a shared application label.

**Counter-argument.** A single descriptive table is easier to read and may be
more persuasive than several qualified evidence surfaces.

**Rebuttal strategy.** Prefer a readable table with explicit namespace labels
and a short interpretation over a pooled number whose estimand is ambiguous.
Clarity of scope is part of the scientific result.

**Strength.** Strong for evidence governance; the external-validity conclusion
remains pending a compatible dataset and audited run.

## Argument Synthesis

A1 establishes why the protocol is the object that makes comparison meaningful.
A2 specifies why model-family labels cannot replace objective and input
bindings. A3 turns the conceptual Hybrid decomposition into falsifiable
ablation and cohort requirements. A4 determines how results can be reported
without turning one evidence surface into another. Together these arguments
support a methods contribution and a conditional empirical question, but they
stop short of a model-effect conclusion.

## Logical Flow

```text
Introduction
  sparse retail setting -> comparability problem -> distinct model contracts
  -> conditional Hybrid question -> bounded contributions
       |
Related Work
  evaluation sensitivity -> collaborative/deep/sequence families
  -> Wide/Deep and tower roles -> rules and basket novelty
  -> graph/cold/content/transfer boundaries
       |
Methodology and Protocol
  frozen data/split -> full catalog and masking -> model descriptors
  -> metrics, seeds, and hierarchical uncertainty
       |
Experimental Design and Evidence Scope
  public validation lane | official lane | controlled-v5 follow-up
  -> namespace-specific admission and artifact lineage
       |
Results
  descriptive Pop/BPR public rows only
       |
Discussion and Limitations
  what procedural validation supports -> what remains unmeasured
  -> conditions for a future Hybrid conclusion
       |
Conclusion
  protocol contribution and explicit empirical boundary
```

## Counter-Argument Register

| Issue | Risk to the paper | Response in prose |
|---|---|---|
| Public BPR values appear higher than Pop | Readers may infer a general algorithm ordering | State the values as namespace-scoped descriptive observations; note the single Pop run and absent paired per-user inference. |
| Wide and Deep is used as conceptual precedent | Readers may equate a linear Wide branch with Apriori rules | Distinguish the source architecture from the proposed rule-derived feature branch and reserve attribution for the follow-up ablation. |
| Sparse v5 data are called cold-start data | Sparse and zero-edge cohorts may be conflated | Define strict zero-edge items from the training graph and report denominators separately. |
| Text embeddings are available | Representation quality may be mistaken for ranking quality | Require a recommender objective, shared evaluator, and task-specific result before making an effectiveness statement. |
| Public and internal datasets share a recommendation label | Cross-dataset pooling may look natural | Keep namespaces, estimands, and artifact lineages separate. |
| A paper can be framed as an engineering report | Scientific boundaries may be weakened | State the causal and production boundary and retain null or unresolved outcomes as valid outcomes. |

## Strength Assessment

| Sub-argument | Evidence strength | Logic validity | Counter-argument risk |
|---|---|---|---|
| A1 Protocol as estimand | Strong | Valid | Low |
| A2 Distinct model contracts | Strong | Valid with qualified inference | Medium |
| A3 Rule and cold cohorts | Moderate | Valid with untested mechanism premise | High |
| A4 Namespace separation | Strong | Valid | Low |

The central thesis is **strong as a protocol and reporting argument** and
**adequate as a claim about the proposed model**, because the latter awaits the
follow-up experiment. No core argument is rated weak, but the paper must keep
the conditional wording in the title-adjacent framing, abstract, results, and
conclusion.

## Notes for the Draft Writer

1. Open with the comparability problem, not with a claim about a winning model.
2. Use the terms `controlled`, `semi-synthetic`, `descriptive`, and
   `conditional` where they carry methodological meaning.
3. Cite source-native method descriptions only for the bounded signal/objective
   statements authorized by the matrix. Do not transfer their metrics to v5.
4. Keep all four public rows in a table titled
   `PUBLIC_DATA_PROTOCOL_VALIDATION` and identify the aggregate receipt as the
   numeric source.
5. Use a short limitations paragraph whenever a reader could confuse a
   protocol result with a model-effect result.
6. Avoid absolute priority language and avoid causal or deployment conclusions.

