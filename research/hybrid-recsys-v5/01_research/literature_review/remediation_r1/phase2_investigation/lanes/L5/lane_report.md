# L5 remediation R1 lane report

## Scope and run identity

- Project: `hybrid-recsys-v5`
- Stage: `1B`
- Round: `remediation R1`
- Lane: `L5 — Vietnamese Literature and External Datasets/Resources/Rights`
- Research cutoff and execution date: `2026-08-14`
- Runtime lock: `gpt-5.6-sol`, reasoning `xhigh`
- Phase fence: Deep Research Phase 2 evidence investigation only. No manuscript section, hypothesis result, benchmark result, or H1-H4 test was produced.
- H4 state: `NOT_RUN` / `NOT_TESTED`.

The old lane was used only as a candidate index. All old candidates were re-screened under the same relevance, authority, coverage, claim-value, metadata, acquisition, locator, family-dependency, and rights criteria applied to new candidates.

## Required-artifact status

| Artifact | Status |
|---|---|
| `lane_report.md` | present |
| `candidate_registry.json` | present; JSON and schema-definition validation completed |
| `disposition_log.json` | present; 19/19 old candidates dispositioned |
| `claim_cards.json` | present; JSON and schema-definition validation completed |
| `source_acquisition_queue.json` | present |
| `exclusion_log.json` | present |
| `lane_handoff.json` | present after final hash pass |

Lawfully acquired supporting files are under `source_artifacts/`. No paywall was bypassed and no dataset payload was redistributed into the lane.

## Reproducible search protocol

### Eligibility and filters

- Date ceiling: publication or operational state available no later than `2026-08-14`.
- Language: English or Vietnamese records; a Vietnamese domain/dataset or a directly relevant external purchase/session resource was required.
- Scholarly inclusion: source-of-record identity resolvable and direct recommender, dataset, estimand, or rights value.
- Operational inclusion: exact provider/repository/edition can be pinned and the resource adds at least one locked compatibility field or a necessary rights comparison.
- Exclusion: non-recommender surveys, secondary overviews where primary evidence is required, mirrors without independent provenance or rights, redundant weaker datasets, and unresolved records unable to support their proposed claim.
- No minimum-year filter was applied. The search covered all indexed years through the cutoff and explicitly targeted 2025-2026 updates.
- Search snippets and secondary indexes were discovery aids only. Verification required official primary pages or authoritative full artifacts.

### Discovery batch

Search date: `2026-08-14`. Search surface: current web search with official-domain follow-up. Exact queries:

1. `"Vietnamese recommendation dataset e-commerce recommender 2024 2025 2026"`
2. `site:aclanthology.org Vietnamese recommendation dataset recommender food hotel ecommerce`
3. `site:arxiv.org Vietnamese recommender dataset recommendation 2025 2026`
4. `Vietnamese e-commerce recommendation dataset purchase basket session`

Screening accounting:

| Step | Count | Decision rule |
|---|---:|---|
| Displayed result rows | 30 | Raw rows returned across the four queries |
| Duplicate/cross-query rows | 8 | Same URL or same source-of-record family |
| Navigation, index, or clearly off-topic rows | 14 | Not a unique candidate record; discarded before candidate screening |
| Unique candidate records advanced | 8 | Title/abstract or data-card relevance met |
| Included | 3 | Added to canonical registry |
| Excluded | 5 | Individually recorded in `exclusion_log.json` |

Included gap records:

1. Xuan-Bach Nguyen and Hoang-Quynh Le, 2025, graph-based multimodal Vietnamese recommendation work; retained as a scholarly record but counted in the ViEcomRec data family.
2. Quoc-Dinh Truong, Trinh Diem Thi Bui, and Hai Thanh Nguyen, 2021, Vietnamese review opinion-mining recommendation chapter; retained with full-content acquisition pending.
3. Viet Hoang Pham, Anh Thai Nguyen, Bao The Phung, and Truong Ho-Viet Phan, 2024, Vietnamese restaurant recommendation work; full open artifact acquired and inspected.

The five excluded records were a broad 2026 dataset survey, a Vietnamese livestream-shopping human survey, a third-party Complete Journey mirror, a MovieLens-only hybrid method, and an incompletely resolved incremental/sentiment record. Exact decisions and source checks are in `exclusion_log.json`.

### Verification query log

The following exact queries were run after discovery. They are verification searches, not additional count inflation.

| Query | Target/site | Outcome |
|---|---|---|
| `site:dunnhumby.com/source-files Complete Journey terms conditions dataset` | dunnhumby | Official source-files and terms pages located |
| `site:github.com/bradleyboehmke/completejourney release package DESCRIPTION LICENSE` | GitHub | Package repository and revision located |
| `site:rdrr.io completejourney package version 2.0 CC0` | package documentation | Package metadata lead; CRAN used as source of record |
| `"Complete Journey" dataset license dunnhumby` | web | Provider/package distinction identified |
| `10.1007/s12626-025-00186-6` | DOI/Springer | Canonical graph-paper record verified |
| `"A Graph-based Deep Learning Model with Multimodal Fusion for Vietnamese Recommendation Systems"` | web | Exact-title family verified |
| `site:link.springer.com/article/s12626 Vietnamese recommendation systems graph multimodal fusion` | Springer | Official journal page located |
| `site:doi.org/10.1007/s12626-025-00186-6` | DOI | DOI resolution checked |
| `"Product Recommendation System Using Opinion Mining on Vietnamese Reviews"` | Springer/web | Canonical chapter located |
| `"Using Incremental Algorithm in Hybrid Recommender System Combined Sentiment Analysis"` | web | Candidate unresolved and excluded |
| `"Developing a Restaurant Recommendation System via the Vietnamese Food Image Classification"` | journal/web | Official article located; title normalized from source of record |
| `Vietnamese recommendation system site:link.springer.com/article OR site:link.springer.com/chapter` | Springer | Relevant Vietnamese records screened |
| `"Using Incremental Algorithm" "Hybrid Recommender"` | web | No complete authoritative identity obtained |
| `"Using Incremental Algorithm in Hybrid Recommender System Combined Sentiment Analysis" authors` | web | Full author/source record unresolved |
| `site:link.springer.com/chapter "Hybrid Recommender System Combined Sentiment"` | Springer | No authoritative full match sufficient for inclusion |
| `"Product Recommendation System Using Opinion Mining on Vietnamese Reviews" DOI` | DOI/Springer | DOI 10.1007/978-3-030-76620-7_27 verified |
| `site:ijece.iaescore.com peer review policy IJECE` | IJECE | Journal peer-review policy verified |
| `site:link.springer.com/journal/12626 peer review The Review of Socionetwork Strategies` | Springer | Journal review status checked |
| `site:link.springer.com "Soft Computing: Biomedical and Related Applications" 981 conference reviewed` | Springer | Book identity verified; explicit chapter review status not found |
| `site:aclanthology.org/about peer review anthology conference` | ACL Anthology | Proceedings context checked; ViFoodRec explicit review status remained unknown |
| `site:relbench.stanford.edu rel-amazon rel-hm license dataset card` | RelBench | Current cards verified; rel-amazon license unspecified |
| `site:amazon-reviews-2023.github.io dataset license Amazon Reviews 2023` | McAuley Lab | Portal located; no dataset license statement found |
| `site:github.com/otto-de/recsys-dataset LICENSE dataset CC BY 4.0` | OTTO GitHub | Dataset CC BY 4.0 and code MIT verified |
| `site:kaggle.com/competitions/h-and-m-personalized-fashion-recommendations rules data license` | Kaggle | Data page verified; license subject to competition rules |
| `site:aicrowd.com/challenges/amazon-kdd-cup-23-multilingual-recommendation-challenge terms dataset license` | AIcrowd | Challenge page verified; public click-through terms not exposed |
| `site:aicrowd.com/challenges/amazon-kdd-cup-23-multilingual-recommendation-challenge dataset files` | AIcrowd | Dataset/task page verified |
| `site:github.com/linh222/face_cleanser_recommendation_dataset license ViEcomRec` | GitHub | Official repository located; pinned license fetched |
| `site:github.com/QuocAn55 Restaurant-Recommendation-With-Vietnamese-Food license` | GitHub | Search miss; correct author-linked repository recovered from the old candidate and checked directly |
| `site:github.com/MinhNguyenDS/ViHoRec license dataset` | GitHub | Official repository and dual-scope license verified |
| `site:github.com/yuangh-x/2022-NIPS-Tenrec license` | GitHub | Dataset CC BY-NC 4.0 statement verified |

Primary sites inspected directly: DCU DORAS, ACL Anthology, arXiv, Springer, IJECE, NeurIPS Proceedings, DOI records, official GitHub repositories, Coveo, OTTO, RelBench, McAuley Lab, Kaggle, AIcrowd, dunnhumby, CRAN, and TAOBAO-MM.

### Search and acquisition failures

- The Springer graph and opinion-mining full texts were not openly available through a lawful route. Their identity and metadata are verified, but `source_content_verified=false` and `locator_ready=false` are preserved.
- The public H&M rules endpoint returned no usable rule body. The official data page states `Subject to Competition Rules`; exact accepted rules remain a carry-forward item.
- Initial raw GitHub fetches failed with a sandbox/TLS receive error. They were retried through the approved network route. All planned snapshots succeeded except the ViFoodRec `LICENSE` path, which returned HTTP 404; its pinned README contains no dataset license.
- The current AIcrowd challenge page was captured, but a current account-bound download agreement was not exposed. The original Amazon-M2 paper's Apache 2.0 statement is recorded separately.
- RelBench PDF geometry preflight reported invalid page objects. The artifact text was inspected, but its durable locator uses Section 3 and table anchors, not page coordinates.
- Complete Journey provider pages, terms, and package metadata were acquired. The full provider dataset and package payload were not acquired.
- No API 429 response occurred in this run. No degraded API outcome was converted into an unmatched identity.

## Candidate and disposition results

### Counts

| Unit | Count |
|---|---:|
| Old candidates dispositioned | 19/19 (100%) |
| `RETAIN` | 5 |
| `REPLACE` | 4 |
| `MOVE_TO_RESOURCE_REGISTRY` | 3 |
| `REMOVE` | 7 |
| Gap-search candidate records advanced | 8 |
| Gap-search inclusions | 3 |
| Gap-search exclusions | 5 |
| Final scholarly canonical records | 12 |
| Independent scholarly dataset-evidence families | 11 |
| Final operational canonical records | 14 |
| Operational root data families | 12 |

The difference between canonical records and independent families is deliberate. The 2025 Vietnamese graph paper reuses ViEcomRec. RelBench adapters depend on upstream Amazon Reviews and H&M. BLaIR depends on Amazon Reviews 2023. MUSE depends on TAOBAO-MM. The CRAN package depends on Complete Journey source files.

### Core audited candidates

- ViEcomRec 2024: canonical metadata and full content verified; repository rights are non-commercial and upstream Shopee redistribution authority remains unresolved.
- Amazon-M2 2023: canonical metadata and full content verified; formal task is next engaged product, not strict purchase. Dataset files are described as Apache 2.0 in Appendix B.3; current AIcrowd click-through terms remain unresolved.
- Coveo SIGIR eCom: full paper and pinned terms verified. Purchase/cart/session/content/time fields exist; persistent user does not. Redistribution is prohibited.
- Complete Journey: official provider page, provider terms, CRAN 1.1.1 metadata, and pinned package DESCRIPTION verified. It is structurally closest among reviewed resources but remains conditional on exact edition acquisition and rights-compliant use.

## Compatibility result

The full 14-row matrix is in `candidate_registry.json`. The locked fields are purchase outcome, persistent user, basket/session, timestamp, item content, split feasibility, and candidate universe.

| Resource family | Purchase | Persistent user | Basket/session | Time | Content | Split | Universe | Strict H4 planning status |
|---|---|---|---|---|---|---|---|---|
| ViEcomRec | post-purchase review proxy | yes | no | yes | yes | temporal leave-last | item table | conditional |
| Amazon-M2 | no; next engagement | no | session | ordinal | yes | provided | product table | not strict H4 |
| Coveo | yes | no | session/cart | shifted time | yes | provided | product metadata | conditional |
| OTTO | order event | no | session/cart/order | yes | limited | temporal | interaction universe | conditional |
| RelBench rel-amazon | verified-purchase review proxy | yes | no | yes | yes | temporal | product table | rights unresolved |
| H&M / rel-hm | yes | yes | derived date grouping | yes | yes | temporal | article table | terms conditional |
| Amazon Reviews 2023 | verified-purchase review proxy | yes | no | yes | yes | temporal | union with missing metadata | rights unresolved |
| Complete Journey | yes | yes | yes | yes | yes | feasible | product table | closest; conditional |
| TAOBAO-MM | no; click | yes | long sequence | split only | yes | temporal | target universe | incompatible outcome |

This table is a compact view of the reviewed records, not a prevalence statement about datasets outside the lane.

## Four-layer rights audit

Each operational record separates:

1. availability/access route;
2. code or package license;
3. paper license;
4. dataset rights and redistribution.

Rights state across 14 operational records:

| Field | Count |
|---|---:|
| Dataset rights `permitted` | 3 |
| Dataset rights `restricted` | 7 |
| Dataset rights `unknown` | 4 |
| Redistribution `permitted` | 2 |
| Redistribution `restricted` | 3 |
| Redistribution `unknown` | 9 |

The two redistribution-permitted records are OTTO and TAOBAO-MM, based on explicit official dataset-license statements. Public availability was not used as the rights basis. Complete Journey package CC0 was not propagated upstream. RelBench adapters were not treated as independent upstream grants.

## Acquisition and locator status

| Status | Count |
|---|---:|
| Scholarly full content verified | 10/12 |
| Scholarly metadata/abstract only | 2/12 |
| Scholarly locator ready | 10/12 |
| Operational terms snapshots verified | 9/14 |
| Operational terms snapshots partial | 2/14 |
| Operational terms snapshots degraded | 3/14 |
| Full dataset payloads acquired | 0 |

All production-relevant planning claims in `claim_cards.json` have original-content locators. The two non-acquired scholarly records do not support method-detail, quantitative, or strict-compatibility claims.

## Unresolved blockers carried forward

1. Acquire an authoritative full artifact for the 2025 graph paper if its method details are needed.
2. Acquire an authoritative full artifact for the 2021 Vietnamese opinion-mining chapter if its dataset or method details are needed.
3. Obtain explicit ViFoodRec dataset rights before reuse or redistribution.
4. Resolve ViEcomRec and ViHoRec upstream source-platform redistribution authority before distributing derived records.
5. Capture current AIcrowd Amazon-M2 download terms in an authorized session before any redistribution decision.
6. Obtain an upstream license determination for RelBench `rel-amazon` / Amazon Reviews and exact accepted rules for H&M / `rel-hm`.
7. Obtain an explicit Amazon Reviews 2023 dataset license or provider authorization.
8. If Complete Journey is selected, acquire and inspect the exact provider/package edition and user guide under provider terms; do not rely on package CC0 as an upstream grant.
9. Coveo data must not be redistributed to colleagues; each authorized user must follow the provider's access terms.
10. RelBench durable locators must remain section/table based for the inspected PDF.

## Remediation ownership

- `ST1B-META-001`: addressed by complete author/title/year/venue/type/status/DOI metadata and explicit unresolved peer-review fields.
- `ST1B-SCOPE-001`: addressed by scholarly/operational separation, 100% old-candidate disposition, and reviewed-candidate-only scope bounds.
- `ST1B-RIGHTS-001`: addressed by four independent rights layers and cutoff-dated terms/revision snapshots.
- `ST1B-META-003` lane share: addressed by explicit peer-review bases and `unknown` where the source did not establish status.
- `ST1B-SYNTH-001` lane share: addressed through bounded claim cards only; no manuscript synthesis was written.
- `ST1B-LOCATOR-001` lane share: addressed for 10 acquired scholarly works and all operational terms claims; two scholarly full-text locators remain explicitly queued.

## Local gate verdict: PASS

| Gate condition | Result |
|---|---|
| 100% old-candidate disposition | PASS — 19/19 |
| Reproducible complete lane gap search | PASS — exact queries, date, sites, filters, counts, decisions, and failures recorded |
| Retained identity/metadata verified or explicitly unresolved | PASS |
| No placeholder year, canonical shortened author list, or corrupted metadata text | PASS |
| Version and family dependencies recorded | PASS |
| Intended claims bounded and evidence-linked | PASS |
| No production-intended claim supported only by the old lane or metadata | PASS |
| Seven artifacts exist, parse, and are internally consistent | PASS |
| Unresolved acquisition, locator, rights, and peer-review issues carried forward | PASS |

The verdict passes the locked local gate while leaving H4 untested and all unresolved legal/acquisition questions explicit.
