# L1 Evaluation and Reproducibility — remediation R1 lane report

## Scope and phase boundary

- Project: `hybrid-recsys-v5`
- Stage: `1B`
- Round: `remediation R1`
- Lane: `L1 — Evaluation and Reproducibility`
- Research cutoff: `2026-08-14`
- Search execution date: `2026-08-14` (Asia/Saigon)
- Phase: ARS Deep Research Phase 2 investigation only

This lane report records search, screening, source verification, acquisition, and bounded claim-card results. It does not contain manuscript synthesis, benchmark results, hypotheses, an Introduction, or Related Work prose.

## Preflight completed

The complete ARS academic-research skill, Deep Research workflow, bibliography-agent instructions, source-verification-agent instructions, locked control files, audit artifacts, Stage 1A research-question/estimand/methodology files, and the old L1 lane were read before investigation. The PDF skill was also applied for lawful full-artifact inspection. No plan, control, audit, input, Stage 1A, or old-lane file was edited.

## Screening accounting

The old lane stated 18 deduplicated candidates but contained 19 distinct works because the final exclusion bullet combined BARS and Cornac. This remediation uses the actual record count.

| Flow | Count |
|---|---:|
| Old-lane candidate records screened | 19 |
| Old-lane candidate records dispositioned | 19 |
| Gap-search candidate works entering title/abstract screen after deduplication | 16 |
| Total candidate records screened under the R1 criteria | 35 |
| Retained canonical scholarly records | 23 |
| Excluded, removed, or replaced candidate records | 12 |
| Retained independent scholarly source families | 21 |
| Retained operational-resource records | 0 |
| Retained records with authoritative full content inspected | 19 |
| Retained records with an original-content locator ready | 19 |

Old-lane dispositions are `RETAIN=11`, `REPLACE=4`, `REMOVE=4`, and `MOVE_TO_RESOURCE_REGISTRY=0`. The 12 non-retained screened records comprise eight old-lane records and four gap-search records. Version-family consolidation prevents the two retained Krichene records and the two retained Li records from inflating the independent-family count.

The web-search interface did not expose stable database-wide hit totals, so no unverifiable hit count is reported. The reproducible count is the set of deduplicated candidate works that entered screening; every one is individually logged in `disposition_log.json` or `exclusion_log.json`.

## Reproducible gap search

### Sites and source hierarchy

Search discovery used current web search, then preferred sources of record and authoritative original artifacts in this order: ACM Digital Library/DOI records; AAAI proceedings; IEEE proceedings and author-accepted manuscripts; SpringerLink; Wiley Online Library; arXiv version records; official institutional research portals; official author publication pages. DBLP and search-result snippets were used only for discovery or cross-checking and never as original-content verification.

### Filters and criteria

- Date filter: emphasis on 2022–2026 work through the locked cutoff; older sources retained only when foundational or directly inherited from the audited core.
- Topic filter: exact/full-catalog versus sampled evaluation; split and candidate-universe dependence; aggregation/metric semantics; tuning budget and evaluation-chain controls; negative sampling; reproducibility; official reproduction versus harmonized benchmarking.
- Inclusion: direct claim-level value, authoritative identity, canonical metadata traceable to a source of record, relevant support scope, and non-redundant coverage.
- Exclusion: version-family duplication without added claim value; broad survey/toolkit material duplicated by more direct sources; exposure-bias interventions outside the locked lane need; or metadata/content that could not support an in-scope claim.
- Identical criteria were applied to old and newly discovered candidates. A repository link was not treated as evidence that results were reproduced.

### Exact queries

The following exact query strings were run on `2026-08-14`:

1. `"On Sampled Metrics for Item Recommendation" Krichene Rendle PDF`
2. `"Towards Reliable Item Sampling for Recommendation Evaluation" PDF`
3. `"Revisiting Alternative Experimental Settings for Evaluating Top-N Item Recommendation Algorithms" PDF`
4. `"A Troubling Analysis of Reproducibility and Progress in Recommender Systems Research" PDF`
5. `"Improving Methodological Standards in Recommender Systems Offline Evaluation"`
6. `"Time to Split" recommender systems 2025 temporal split`
7. `recommender systems evaluation reproducibility 2022 2023 2024 2025 2026 offline evaluation`
8. `recommender systems benchmark evaluation protocol candidate sampling tuning reproducibility 2024 2025`
9. `"Widespread Flaws in Offline Evaluation of Recommender Systems"`
10. `"Where Do We Go From Here? Guidelines For Offline Recommender Evaluation"`
11. `"On the Convergent Validity of Offline Evaluation Designs for Recommender Systems"`
12. `"Reproducibility in Recommender Systems: A Survey"`
13. `"On Item-Sampling Evaluation of Recommender System" ACM DOI`
14. `"DaisyRec 2.0: Benchmarking Recommendation for Rigorous Evaluation"`
15. `"Quality Metrics in Recommender Systems: Do We Calculate Metrics Consistently?"`
16. `"Offline Evaluation Options for Recommender Systems"`
17. `"Offline recommender system evaluation: Challenges and new directions"`
18. `"RecBole 2.0: Towards a More Up-to-Date Recommendation Library"`
19. `"Diffusion Recommender Models and the Illusion of Progress"`
20. `"We Share Our Code Online" reproducibility recommender systems`
21. `"On the Reliability of Sampling Strategies in Offline Recommender Evaluation"`
22. `"On the Consistency, Discriminative Power and Robustness of Sampled Metrics"`
23. `"Candidate Set Sampling for Evaluating Top-N Recommendation"`
24. `"Reproducibility in Recommender Systems: A Survey" Alan Said Alejandro Bellogín ACM`
25. `"On the Convergent Validity of Offline Evaluation Designs for Recommender Systems" RecSys 2026`
26. `site:dl.acm.org/doi "Improving Methodological Standards in Recommender Systems Offline Evaluation"`
27. `site:dl.acm.org/doi "Time to Split" "3748164"`
28. `site:onlinelibrary.wiley.com 10.1002/aaai.12051 Castells Moffat title`
29. `site:dl.acm.org 10.1145/3604915.3610651`
30. `site:dl.acm.org 10.1145/3629171`
31. `recommender evaluation candidate set sampling Ihemelandu Ekstrand 2023 title DOI`
32. `recommender systems evaluation "Where Do We Go From Here" 2022 Schnabel title`
33. `recommender evaluation distributionally informed 2024 title`
34. `recommender systems evaluation landscape 2024 Bauer exact title`
35. `Carraro Bridge 2022 sampling approach debiasing recommender evaluation exact title DOI`

### Focused R3 acquisition and status re-audit

The following additional exact queries were run on `2026-08-14`. They were acquisition/status re-checks of nine already-screened records, not new candidate discoveries, so they do not inflate the 35-record screening flow:

36. `site:research.google/pubs "On Sampled Metrics for Item Recommendation"`
37. `site:storage.googleapis.com "On Sampled Metrics for Item Recommendation" pdf`
38. `site:static.googleusercontent.com "On Sampled Metrics for Item Recommendation"`
39. `"On Sampled Metrics for Item Recommendation" filetype:pdf -ijcai`
40. `site:walid.krichene.net/*.pdf "On Sampled Metrics"`
41. `site:walid.krichene.net "On Sampled Metrics for Item Recommendation" pdf`
42. `site:walid.krichene.net/publications "sampled metrics"`
43. `"On Sampled Metrics for Item Recommendation" "walid.krichene.net"`
44. `"Cumulated Gain-Based Evaluation of IR Techniques" PDF Järvelin Kekäläinen institutional repository`
45. `"The Use of the Area Under the ROC Curve in the Evaluation of Machine Learning Algorithms" PDF author university`
46. `"On the Consistency, Discriminative Power and Robustness of Sampled Metrics" PDF`
47. `"On Item-Sampling Evaluation for Recommender System" PDF`
48. `site:par.nsf.gov "On Item-Sampling Evaluation for Recommender System"`
49. `site:par.nsf.gov/biblio/ "On Item-Sampling Evaluation for Recommender System"`
50. `site:par.nsf.gov/file "On Item-Sampling Evaluation for Recommender System"`
51. `site:par.nsf.gov/servlets/purl "On Item-Sampling Evaluation for Recommender System"`
52. `"On Item-Sampling Evaluation for Recommender System" "par.nsf.gov/biblio"`
53. `"On Item-Sampling Evaluation for Recommender System" "par.nsf.gov/servlets"`
54. `"On Item-Sampling Evaluation for Recommender System" "Full Text Available" NSF PAR`
55. `"We Share Our Code Online: Why This Is Not Enough to Ensure Reproducibility" PDF`
56. `site:dl.acm.org "Reproducibility in Recommender Systems: A Survey"`
57. `site:dl.acm.org/doi "Reproducibility in Recommender Systems" Said Bellogín`
58. `site:dl.acm.org/doi "Improving Methodological Standards in Recommender Systems Offline Evaluation" editorial essay peer review`
59. `"Reproducibility in Recommender Systems: A Survey" Said Bellogín DOI`
60. `"Reproducibility in Recommender Systems" "ACM Transactions on Recommender Systems" Said`
61. `"Improving Methodological Standards in Recommender Systems Offline Evaluation" review editorial essay`
62. `site:dl.acm.org/doi/10.1145/3629171 "On Item-Sampling Evaluation"`
63. `site:dl.acm.org/doi/full/10.1145/3629171`
64. `site:dl.acm.org/doi/pdf/10.1145/3629171`

Direct routes were also tested without query expansion: ACM DOI/PDF endpoints; Google Research; Walid Krichene's official publication page and explicit author PDF; University of Copenhagen's institutional full-file endpoint; ResearchGate's author-uploaded final paper; University of Helsinki's research portal; NSF PAR; arXiv v2 for Pereira; and publisher DOI pages. Outcomes were: exact KDD author artifact acquired; exact Shehzad final published full text inspected through an author upload with its CC BY notice verified against the institutional record; four records remained metadata/abstract-only; Pereira remained structurally degraded but readable; Jannach–Chen remained editorial/essay with review status unknown; and Said–Bellogín remained a preprint with an announced but canonically unresolved journal version.

### Gap-screen outcomes

Twelve gap-search records were retained: the authoritative IJCAI same-family Krichene artifact; Castells and Moffat 2022; Hidasi and Czapp 2023; Liu, Medlar, and Głowacka 2023; Li, Jin, Liu, Ren, Gao, and Liu 2024; Ihemelandu and Ekstrand 2023; Pereira, Said, and Santos 2025; Gusak, Volodkevich, Klenitskiy, Vasilev, and Frolov 2025; Shehzad, Breuer, Maistro, and Jannach 2025; Benigni, Ferrari Dacrema, and Jannach 2026; Parajuli, Vaez Barenji, and Ekstrand 2026; and Said and Bellogín 2026. Four screened works were excluded with explicit reasons in `exclusion_log.json`.

## Metadata and content verification

- All 23 retained records have full author arrays, canonical titles, non-placeholder years, venue/status/type, DOI or official ID, source-family assignment, and verification provenance.
- No canonical metadata uses `et al.`. Names preserve accents, including Järvelin, Kekäläinen, Cañamares, Głowacka, Bellogín, Balázs Hidasi, and Ádám Tibor Czapp.
- `identity_verified`, `metadata_verified`, `source_content_verified`, and `locator_ready` are separate booleans in every registry record.
- Jannach and Chen 2026 is classified as an `editorial`, because the ACM abstract calls it an editorial and the article body calls it an essay. `peer_reviewed` remains `unknown`; no direct evidence of external peer review was located.
- Said and Bellogín 2026 is retained as an arXiv preprint/accepted-manuscript family record. A field announcement reported ACM TORS acceptance, but an ACM source-of-record DOI was not located by the cutoff, so the canonical record is not upgraded to published journal status.
- Search snippets and secondary indexes were not used to set `source_content_verified=true`.

## Lawful acquisition and locator status

Sixteen lawful PDFs were stored under `source_artifacts/` and inspected through full-text extraction. The ARS PDF preflight returned `PASS` for 15 files. The Pereira 2025 PDF was readable and inspected, but a fresh preflight again reported a malformed cross-reference warning; `pdfinfo` still enumerated ten pages, and the locked locator policy continues to withhold page anchors in favor of section anchors. Two additional full artifacts—Jannach and Chen 2026 and Castells and Moffat 2022—were inspected in authoritative publisher HTML. The exact final Shehzad et al. 2025 paper was inspected through an author upload; its DOI and CC BY notice match the University of Copenhagen final-version record. This yields 19 content-verified and locator-ready canonical records.

Core acquisition status:

| Core candidate | Exact artifact status | Locator status |
|---|---|---|
| Krichene and Rendle 2020 | Exact author-hosted ACM-formatted KDD PDF acquired and inspected; title page, venue, DOI, ten-page extent, and content verified; PDF preflight passed | Exact record ready |
| Li, Jin, Liu, Ren, Gao, and Liu 2023 | Authoritative proceedings PDF acquired and inspected | Ready |
| Zhao, Chen, Wang, Gu, and Wen 2020 | Author manuscript/proceedings artifact acquired and inspected | Ready |
| Ferrari Dacrema, Boglio, Cremonesi, and Jannach 2021 | Authoritative full artifact acquired and inspected | Ready |
| Jannach and Chen 2026 | Exact publisher HTML inspected | Ready |

Other unresolved exact-full-artifact acquisitions are Järvelin and Kekäläinen 2002, Bradley 1997, Liu, Medlar, and Głowacka 2023, and Li, Jin, Liu, Ren, Gao, and Liu 2024. These records are not used as the sole support for any claim card; Bradley was removed from the GAUC boundary card rather than allowing metadata to stand in for original content.

Acquisition failures were recorded as access or tooling failures, not evidence that a source does not exist: multiple ACM direct PDFs returned HTTP 403; the author host's KDD HTTPS route was unavailable while its explicitly linked HTTP PDF succeeded; the University of Copenhagen file endpoint returned HTTP 403 before the author-uploaded CC BY version was inspected; the Bradley mirror route lacked resolvable access/licensing evidence; NSF PAR advertised full text but did not expose a retrievable endpoint in this run; and the Pereira PDF preflight could not establish clean page-anchor structure. No paywall was bypassed and no redistribution right was inferred from mere availability.

Semantic Scholar was not queried in this R1 lane run. The audit's earlier HTTP 429 condition remains classified as degraded service evidence, never as an unmatched or nonexistent source.

## Claim-boundary results

The bounded claim cards preserve these distinctions without drafting synthesis:

- Exact/full-catalog metrics and sampled metrics are different estimands; sampled results cannot be relabeled as exact results.
- Sampling evidence is not one-sided: naive sampled metrics can fail to preserve exact ordering, while estimator-based or adaptive sampling can improve recovery under stated assumptions.
- Split policy, candidate universe, target selection, filtering, and dataset context can change metric values and model rankings.
- Metric aggregation and implementation semantics must be explicit and parity-tested.
- Tuning budget, validation rule, baseline optimization, seeds, preprocessing, and the rest of the evaluation chain are part of the reproducibility contract.
- A public repository permits an attempt; it is not evidence that the claimed result was reproduced.
- An official-protocol reproduction and a harmonized benchmark answer different questions and must be reported separately.
- Raw metrics from different datasets or pipelines are not authorized for direct comparison.

Every claim card is marked `planning_only=true` because this is Phase 2. No claim card authorizes a benchmark result or manuscript statement without central review.

## Remediation mapping

- `ST1B-META-002`: addressed. Jannach and Chen 2026 is editorial/essay; peer-review status is `unknown` absent direct evidence.
- `ST1B-META-003` lane share: addressed for all retained L1 records through full author arrays and UTF-8 canonical metadata.
- `ST1B-SYNTH-001`: addressed by separate counts: 23 canonical scholarly records and 21 independent scholarly source families.
- `ST1B-LOCATOR-001`: addressed for the locked core and every claim card. Nineteen retained records are full-content verified and locator-ready; all five audit-core exact records are ready. Four non-core metadata/abstract-only records remain explicitly queued and are not sole claim support.

## Local-gate verdict

`PASS`

The locked gate is not weakened. All 19 old candidates are dispositioned; the gap search and focused re-audit are reproducible; all 23 retained identities and metadata records are verified; version-family dependencies, limitations, counter-evidence, support scope, and forbidden extrapolations are explicit; the exact KDD core artifact is acquired; and every claim card is planning-only with an original-content locator. The four remaining metadata/abstract-only records, Pereira's section-only locator, and the two honest peer-review/status unknowns are carried forward explicitly, as the contract requires, rather than silently treated as resolved. None is sole support for a claim card. The required JSON, cross-file, hash, forbidden-field, source-family, and local-gate checks pass.
