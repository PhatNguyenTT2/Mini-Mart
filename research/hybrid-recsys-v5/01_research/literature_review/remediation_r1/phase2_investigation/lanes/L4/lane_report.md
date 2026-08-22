# L4 remediation R1 — Phase 2 investigation report

## Status

- Project: `hybrid-recsys-v5`
- Stage: `1B`
- Round: `remediation R1`
- Lane: `L4 — Cold-item, Content, and Transfer`
- Research cutoff: `2026-08-14`
- Investigation date: `2026-08-14` (`Asia/Saigon`)
- Local-gate verdict: **PASS**
- Phase boundary: evidence search, verification, acquisition accounting, and claim-card handoff only. No synthesis, manuscript prose, hypotheses, or benchmark conclusions are produced here.

The PASS is a local L4 handoff verdict. It is not a Stage 1B seal, a Stage 2 citation authorization, or a claim that all retained sources have been acquired. Six non-core retained records remain explicitly queued, and none supports a production-intended claim card in metadata-only form.

## Locked scope and decision criteria

Required coverage was item-side cold-start definitions and cohort construction; DropoutNet, Sentence-BERT, UniSRec, VQ-Rec, and AlphaRec; zero collaborative edge versus sparse edge; encoder rationale versus demonstrated recommender efficacy; and transfer assumptions with target-domain adaptation.

Candidates were retained only when they added at least one of the following under authoritative identity control:

1. direct item-side zero-edge definition or reproducible cohort-construction value;
2. an audit-core source;
3. non-redundant method coverage for content-based cold-item recommendation;
4. a transfer/adaptation mechanism or data-lineage boundary;
5. counter-evidence or a necessary collaborative sparse-graph control.

The same relevance, authority, coverage, and claim-level-value criteria were applied to all 19 old candidates and all new search results. Authority alone was not sufficient. Old records were not grandfathered, and recent records were not retained merely to increase counts.

## Reproducible gap search

### Formal counted search

- Database/site: Crossref REST API (`api.crossref.org/works`)
- Run date: `2026-08-14`
- Publication-date filter: `from-pub-date:2022-01-01,until-pub-date:2026-08-14`
- Selected fields: `DOI,title,author,published,container-title,type,URL`
- Rows per query: `20`
- Ranking: Crossref default relevance order; no client-side re-ranking before retrieval
- Screening rule: DOI-deduplicate, title/metadata screen every unique record using the locked criteria, then verify retained identity against source of record and acquire authoritative full artifacts when a claim card requires them.

| Query ID | Exact endpoint | Crossref `total-results` | Retrieved |
|---|---|---:|---:|
| Q1 | `https://api.crossref.org/works?query.title=cold-start%20item%20recommendation&filter=from-pub-date:2022-01-01,until-pub-date:2026-08-14&select=DOI,title,author,published,container-title,type,URL&rows=20` | 125,588 | 20 |
| Q2 | `https://api.crossref.org/works?query.title=zero%20interaction%20cold%20item%20content%20recommendation&filter=from-pub-date:2022-01-01,until-pub-date:2026-08-14&select=DOI,title,author,published,container-title,type,URL&rows=20` | 417,521 | 20 |
| Q3 | `https://api.crossref.org/works?query.title=transferable%20sequential%20recommendation%20text%20item%20representation&filter=from-pub-date:2022-01-01,until-pub-date:2026-08-14&select=DOI,title,author,published,container-title,type,URL&rows=20` | 211,722 | 20 |
| Q4 | `https://api.crossref.org/works?query.title=language%20representations%20recommendation%20cold%20start&filter=from-pub-date:2022-01-01,until-pub-date:2026-08-14&select=DOI,title,author,published,container-title,type,URL&rows=20` | 396,406 | 20 |

Crossref `total-results` is the fuzzy query universe, not a relevant-record count. The bounded reproducible screen consists of the 80 retrieved rows only.

### Screening flow

| Step | Count |
|---|---:|
| Retrieved rows | 80 |
| Duplicate DOI rows removed | 17 |
| Unique DOI records screened | 63 |
| Old retained records rediscovered | 2 |
| New records retained | 4 |
| Unique gap-search records excluded | 57 |

The four new retained records are CGRC (SIGIR 2024), inherited popularity bias (RecSys 2025), SEMCo (SIGIR 2026), and UTGRec (SIGIR 2026). ALDI and VQ-Rec were rediscovered old retained records. All 57 other unique DOI records have explicit decisions in `exclusion_log.json`.

### Supplementary primary-source discovery and verification

The following exact web searches were used as non-counted discovery aids before canonical verification:

- `site:dl.acm.org "cold-start item recommendation" recommender 2024 2025 2026`
- `site:proceedings.iclr.cc recommendation cold-start item content 2025 2026`
- `site:arxiv.org "cold-start item" recommendation 2025 2026`
- `site:aclanthology.org recommendation item representation transfer 2025 2026`

No date filter was exposed by the search interface; cutoff eligibility was checked against canonical records. The interface did not expose stable total-result counts, so these searches were not pooled into screening counts and no inclusion was made from a snippet alone. They led to official publisher/proceedings, DOI, institutional, or author-artifact verification. This limitation is reported rather than converted into an invented count.

### Search and transport failures

1. Opening Crossref API endpoints through the web retrieval layer returned safe-URL/internal errors.
2. The same Crossref requests from the default sandbox experienced a closed TLS connection.
3. The exact four requests then succeeded through the approved network route; the failures were treated as degraded transport, not unmatched records.
4. The CGRC author PDF was discoverable through the official Google Research record, but repeated full-artifact transport returned internal errors after metadata/first-page discovery. CGRC therefore remains `source_content_verified=false` and `locator_ready=false`.

## Old-lane disposition

The old lane contained 19 candidate identities: 12 previously accepted and 7 previously excluded. All 19 were re-screened and dispositioned.

| Disposition | Count |
|---|---:|
| RETAIN | 11 |
| REPLACE | 0 |
| REMOVE | 8 |
| MOVE_TO_RESOURCE_REGISTRY | 0 |
| Total | 19 |
| Coverage | 100% |

The previously accepted PERE record was removed because it is a cold-user elicitation paper. Seven old exclusions remained excluded. Amazon-M2 was removed rather than moved to the operational-resource registry because it is a scholarly dataset paper, not an operational resource. No publication year was assigned to an operational resource because this lane retains none.

## Retained corpus and dependency accounting

| Count type | Count |
|---|---:|
| Canonical scholarly records | 15 |
| Independent version families | 15 |
| Evidence-lineage clusters | 10 |
| Operational resources | 0 |

The canonical count must not be reported as 15 independent corroborations. Important dependencies recorded in `candidate_registry.json` include:

- UniSRec, VQ-Rec, and UTGRec share authorship/method lineage; UTGRec uses Amazon 2023 subsets for both pretraining and all four downstream domains.
- SimGCL and XSimGCL are a direct overlapping-author method lineage.
- The inherited-popularity-bias and SEMCo papers share the same two authors and research program.
- MTPR and CLCRec share authorship/research lineage, with further overlap to AlphaRec.
- AlphaRec reuses/adapts UniSRec and VQ-Rec as baselines and includes an Amazon target alongside Amazon source domains; its MovieLens and Book-Crossing targets remain separately identified.

## Identity, metadata, acquisition, and locator status

All 15 retained canonical records have `identity_verified=true` and `metadata_verified=true`. Canonical authors are fully enumerated; no canonical record uses “et al.”, placeholder years, or mojibake. DOI-bearing records were checked against Crossref and official publication records. Non-DOI records were checked against official NeurIPS, ICLR, ACL Anthology, or OpenReview records. XSimGCL is cited as IEEE TKDE 36(2), 913–926 (2024); its 2023 DOI/online-first metadata is preserved as a version relation rather than substituted for the issue year.

| Acquisition/locator class | Count |
|---|---:|
| Authoritative full artifacts lawfully inspected remotely | 9 |
| `source_content_verified=true` | 9 |
| `locator_ready=true` | 9 |
| Retained records queued for full artifact and locator | 6 |
| Local artifacts stored | 0 |

All four audit-core records—DropoutNet 2017, UniSRec 2022, AlphaRec 2025, and Sentence-BERT 2019—have authoritative full artifacts inspected and original-content locators. The remaining six acquisition/locator queues are MTPR, CLCRec, SimGCL, XSimGCL, LightGCL, and CGRC. They do not support any production-intended claim card in metadata-only form.

No remote availability was treated as redistribution permission. Author manuscripts carrying personal-use or uncertain redistribution notices were inspected remotely and not stored. ACL Anthology exposes a permissive license notice for Sentence-BERT, but no local copy was necessary and none was stored.

## Coverage and bounded evidence status

| Required coverage | Evidence status | Original-content anchors | Boundary carried forward |
|---|---|---|---|
| Item-side cold definition | Covered | DropoutNet §2; ALDI §2.1 | Cold-item is not cold-user. |
| Cohort construction | Covered | DropoutNet §§4.2, 5.1; ALDI §2.1 | Lock zero-edge rule and separate denominators; do not merge sparse items. |
| DropoutNet | Core verified | Official NeurIPS full PDF | Paper-native dropout and cohort results are not v5 results. |
| Sentence-BERT | Core verified | ACL Anthology full PDF | Semantic embedding quality is not recommendation quality. |
| UniSRec | Core verified | Author full artifact §2.4 | Inductive evaluation still includes an explicit target-domain adaptation setup. |
| VQ-Rec | Verified | Author full artifact §§2.1–2.3, 3.1 | Discrete codes do not remove target-domain or data-lineage assumptions. |
| AlphaRec | Core verified | Official ICLR full PDF §§4.1, 5.2, 6 | Graph, projection, objective, and source/target lineage must accompany language features. |
| Zero edge versus sparse edge | Covered with mechanism boundary | DropoutNet §2; ALDI §2.1; AlphaRec §4.1 | Observed-edge graph controls cannot be cited as zero-edge content evidence. |
| Encoder rationale versus recommender efficacy | Covered | Sentence-BERT; AlphaRec; SEMCo | Encoder substitutions are ablations unless the original setup is matched. |
| Transfer assumptions and target adaptation | Covered | UniSRec §2.4; VQ-Rec; UTGRec §2.4.2 and §3.3 | Architecture transfer is not H4 replication; shared platform lineage is not independent evidence. |
| Counter-evidence/limitations | Covered | Inherited-popularity-bias §§1, 3.1–3.3; SEMCo §§3.1–3.3 | Two publications in one author/method lineage are not independent corroborations. |

Eight bounded claim cards are supplied. Six are supported and two are partially supported mechanism/protocol inferences. Every card has an original-content locator and is marked planning-only pending central synthesis review. No benchmark result or hypothesis verdict is asserted.

## Remediation responsibility

- `ST1B-META-003`: L4 canonical authors, titles, years, venues, types/status, DOI/official IDs, and version relations are normalized; XSimGCL's issue year is separated from its online-first year.
- `ST1B-SYNTH-001`: claim cards record support scope, counter-evidence, limitations, source-family dependencies, and forbidden extrapolations. This lane does not perform synthesis.
- `ST1B-LOCATOR-001`: all production-intended L4 claim cards have original-content locators. Six unused/non-core retained records remain visibly queued rather than being promoted from metadata.

## Local gate

| Locked condition | Result |
|---|---|
| Seven required artifacts present in the exclusive lane directory | PASS |
| 100% of 19 old candidates dispositioned using allowed values | PASS |
| Reproducible cutoff-bounded gap search with exact queries, filters, counts, decisions, and failures | PASS |
| Retained identity and canonical metadata verified or explicitly unresolved | PASS — all 15 verified |
| Identity, metadata, content, and locator flags remain distinct | PASS |
| Canonical record, version-family, and evidence-lineage counts separated | PASS |
| Production-intended cards supported by authoritative original-content locators | PASS — 8/8 |
| Acquisition/rights blockers carried forward without invented verification | PASS |
| JSON parse, schema-definition, referential, and count consistency validation | PASS |

**Local-gate verdict: PASS.**

Unresolved blockers are limited to the six explicit full-artifact/locator queues. They must be resolved before any future production claim directly relying on those records, but the locked local gate permits explicit acquisition carry-forward when no production-intended claim is metadata-only.
