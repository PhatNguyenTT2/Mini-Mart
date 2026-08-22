# R3 source verification report — remediation R1

Generated: 2026-08-21T00:00:00+07:00  
Research cutoff: 2026-08-14

## Verification outcome

All 79 scholarly lane rows and 14 operational-resource rows were normalized only after the frozen-input gate passed. Identity evidence was merged before prose and claim cards. The result contains 74 scholarly identities, 71 scholarly families, 12 operational roots, and 75 unique family IDs across both registries.

Corpus counts recomputed from merged data: 32/52 recent (2022–2026), 45/52 directly evidenced as peer reviewed, 40/52 locally acquired, 52/52 content verified, and 52/52 locator ready. The scholarly core is 23/23 content verified and 23/23 locator ready.

## Conflict and exception resolutions

| Item | Resolution | Downstream restriction |
|---|---|---|
| Jannach–Chen 2026 | Official institutional metadata classifies it as an editorial; peer review remains unknown. | Editorial context only; no empirical-evidence upgrade. |
| Said–Bellogín 2026 | Official arXiv identity retained; no canonical proceedings/journal status established. | Preprint/peer-review unknown. |
| Pereira et al. 2025 | Identity and section anchor retained; PDF preflight reported UNAVAILABLE with an object-pointer warning. | Section-only locator until R4 reacquisition. |
| Liu–Lai–Lee 2007/2009 | Official journal metadata confirms the 2009 source of record; 2007 is a predecessor manifestation. | 2007 inspected content cannot verify the exact 2009 text. |
| LightGCL | Official OpenReview identity normalized across differently formatted lane IDs. | OpenReview browser challenge logged as transport degradation, not absence. |
| Wide & Deep | DOI identity and full author metadata checked against the official Google Research record. | No use as Apriori or association-rule evidence. |
| Time to Split | DOI and author identity checked against the official RecSys 2025 accepted-contributions record. | Evaluation-design evidence only; no benchmark result inferred. |

## Service degradation

Semantic Scholar returned HTTP 429 for Rendle, LightGCL, and ContextGNN checks; affected records are marked `api_degraded`, never unmatched. OpenReview presented a browser challenge during the central recheck; locally frozen authoritative artifacts and official identity fields remain the evidentiary basis. Crossref and publisher DOI endpoints that returned access errors were treated as transport failures, not source absence.

## Central claim state

All original lane flags are preserved. The eight L4 cards retain both `planning_only=true` and `production_intended=true`; centrally each is `conditional_production_candidate`, not `production_ready`. Across all 44 cards, the original planning flags are 30 true and 14 false, while explicit original production intent is true for 8 and absent for 36. Central dispositions are 22 conditional candidates, 22 planning-only cards, and 0 production-ready cards. Conditional candidates still require R4 as applicable, the central citation gate, and Stage 1B sealing.

## Rights boundary

The operational registry keeps availability, code/package license, paper license, dataset rights, and redistribution permission separate. Coveo's frozen terms restrict the resource to noncommercial research/education and do not permit third-party redistribution. The CompleteJourney R package's CC0 declaration is not propagated to provider files; upstream access and redistribution remain separately conditional.

## Phase boundary

This report verifies Phase 2 evidence infrastructure only. It contains no Phase 3 synthesis, no H1–H4 conclusion, no benchmark result, and no permission to use metadata-only records as production citations. A PASS authorizes only R4 lawful source acquisition.
