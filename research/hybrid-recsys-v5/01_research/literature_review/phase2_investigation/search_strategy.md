# Stage 1B Search Strategy and Screening Record

Status: central merge complete; independent audit pending. Search cutoff: 2026-08-13.

## Review type and scope

This is a targeted, five-lane literature review for the paper's Introduction, Related Work, benchmark design, and dataset-compatibility decisions. It is not a systematic review and does not claim exhaustive recall.

The five lanes were:

1. L1 — evaluation, metrics, and reproducibility.
2. L2 — collaborative, deep, Wide & Deep, and two-tower architectures.
3. L3 — Apriori, sequential/basket recommendation, and hybrid mechanisms.
4. L4 — cold-item, content, transfer, and graph-contrastive controls.
5. L5 — Vietnamese and external e-commerce datasets/resources.

## Search parameters

- Databases/source families: ACM Digital Library, AAAI proceedings, IEEE, Springer, Elsevier, IJCAI, VLDB, NeurIPS proceedings, ACL Anthology, PMLR, ICLR/OpenReview, arXiv, official research/project repositories, and provider-controlled dataset pages.
- Date policy: prioritize 2022–2026; retain older works only when they define a metric, method, architecture, dataset, or direct historical precedent needed by the argument.
- Language: English-language scholarly/official records; Vietnamese relevance is defined by dataset/domain, not publication language.
- Document types: peer-reviewed technical papers, benchmark/dataset papers, official proceedings records, preprints only when uniquely current, and provider-controlled operational dataset records.
- Excluded: blogs, community mirrors without provenance, generic surveys when a primary source was available, source-native benchmark numbers as evidence for v5, and sources outside the lane's bounded claim.

## Query families

- Evaluation: sampled metrics, exact/full-catalog evaluation, temporal split, metric consistency, offline reproducibility, RecBole, DaisyRec.
- Architectures: ItemCF, BPR, NCF, DeepFM, Wide & Deep, DSSM/two-tower, YouTube/NDR, LightGCN, DirectAU, LightGCL, AlphaRec.
- Basket/hybrid: Apriori support/confidence, association-rule recommendation, sequential-rule/CF hybrids, SASRec, BERT4Rec, next/novel basket, repeat/explore, time split.
- Cold/content: cold-start item, content representation, DropoutNet, CLCRec, UniSRec, VQ-Rec, AlphaRec, SBERT, SimGCL/XSimGCL/LightGCL.
- Data/resources: Vietnamese e-commerce/food/hotel recommendation, Amazon-M2, Tenrec, Coveo, OTTO, RelBench, Amazon Reviews 2023, H&M, Complete Journey, TAOBAO-MM/MUSE, license and redistribution terms.

## Screening criteria

Include when all applicable conditions hold:

- directly supports a frozen RQ, contribution boundary, comparator family, protocol choice, or dataset compatibility decision;
- identity is traceable to a DOI registry, official proceedings page, author/team repository, or provider-controlled source-of-record;
- claim use can be bounded to what the source's task and protocol actually support;
- recent work is preferred unless a seminal source is necessary.

Exclude or retain only in the exclusion log when:

- redundant with a stronger/current canonical source;
- belongs to a different task (for example cold-user evidence used as cold-item evidence);
- only a community mirror or ambiguous dataset edition is available;
- it would expand implementation scope without changing a required claim;
- it invites raw-score comparison across different datasets/protocols.

## PRISMA-like accounting

These counts describe lane-level candidate families, not raw database hit counts.

- Candidate families screened: 94.
  - L1: 18; L2: 20; L3: 18; L4: 19; L5: 19.
- Excluded or handed off within lanes: 34.
- Accepted lane records: 60.
- Paper-level duplicates merged centrally: 3.
- Additional relevance/redundancy exclusions: 2.
- Final unique corpus: 55.
- Final sources from 2022–2026: 27/55 (49.1%).
- Final peer-reviewed sources: 49/55 (89.1%).

## Distributional coverage advisory

DISTRIBUTIONAL_SKEW_ADVISORY:

- Dimension: methodological distribution.
- Concentration: computational/technical/dataset evidence = 55/55 (100%).
- Advisory: this is a coverage-distribution signal, not a defect. The corpus is not methodologically diverse outside recommender-system technical research.
- Search response: no expansion. The RQs concern model architecture, offline evaluation, and benchmark compatibility, so this concentration is substantively intended.

No time-distribution advisory triggered: neither the 2022–2026 bucket (27/55) nor the older/foundational bucket (28/55) reaches 70%. Geography and venue-tier skew were not computed because the registry does not contain sufficiently normalized metadata for those dimensions.

## Search limitations

- The review is targeted rather than exhaustive; raw result counts per query/database were not preserved by every lane.
- Full PDFs were not locally acquired, so source-content verification and precise page/section locators remain incomplete.
- Semantic Scholar was API-degraded (HTTP 429); DOI/title deduplication used Crossref, OpenAlex, official records, and manual exception checks.
- Dataset licenses and source-platform terms are not interchangeable; legal compatibility remains an experiment-stage gate.

