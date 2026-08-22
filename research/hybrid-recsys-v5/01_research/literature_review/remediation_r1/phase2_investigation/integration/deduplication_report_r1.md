# R3 deduplication report — remediation R1

Generated: 2026-08-21T00:00:00+07:00  
Research cutoff: 2026-08-14

## Result

The five frozen lanes supplied 79 scholarly rows. Bibliographic identity merging produced 74 canonical scholarly records and 71 independent scholarly families. The 14 operational resources remain in a separate registry and resolve to 12 operational root families. Across both registries there are 75 unique family IDs because eight operational roots are shared with dataset or benchmark papers.

| Measure | Before | After |
|---|---:|---:|
| Scholarly lane rows | 79 | 74 canonical records |
| Scholarly independent families | — | 71 |
| Operational rows | 14 | 14 records / 12 roots |
| Cross-registry unique families | — | 75 |
| Selected scholarly corpus | 52 old scholarly candidates | 52 |
| Core shortlist | — | 23 scholarly + 1 operational family |

## Identity merges

1. Exact DOI merges: Wide & Deep (L2/L3), Time to Split (L1/L3), and SimGCL (L2/L4).
2. Source-of-record/title merge: LightGCL (L2/L4), whose official OpenReview identity was formatted differently.
3. Version relation: Liu–Lai–Lee 2007 conference predecessor and 2009 journal paper share a canonical identity group, but both manifestations and both DOIs remain explicit. The verified 2007 content is not treated as verification of the 2009 journal content.
4. Family-only joins, not identity merges: Krichene 2020/2021; Li 2023/2024; ViEcomRec and its 2025 graph-reuse paper.

## Corpus disposition

The corpus was not padded. Seven old but redundant or incompletely verified works remain in the transparent registry-only tier: Bradley 1997 AUC, Järvelin–Kekäläinen 2002 nDCG, Tamm et al. 2021 metric consistency, Huang et al. 2013 DSSM, MTPR, CLCRec, and XSimGCL. Seven sources required by bounded production-intended claim cards were added: the BERT4Rec replicability study, ContextGNN, T2Diff, repeat/explore-aware LightGCN, inherited popularity bias, SEMCo, and UTGRec.

Jannach–Chen remains an editorial/essay with peer-review status unknown. Said–Bellogín remains a preprint with peer-review status unknown. Pereira 2025 retains a section-only locator because its preflight is degraded. Operational-resource years were not inferred.

## Duplicate gates

Canonical key duplicates: 0  
Canonical normalized-title duplicates: 0  
Canonical normalized-DOI duplicates: 0  
Placeholder publication years: 0  
Shortened canonical author lists: 0
