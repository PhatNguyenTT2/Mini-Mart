# L3 remediation R1 evidence report

## Phase boundary and scope

- Project: `hybrid-recsys-v5`
- Stage: `1B`
- Round: `remediation R1`
- Lane: `L3 — Basket, Sequential, Association-Rule, and Hybrid Recommendation`
- Research cutoff: `2026-08-14`
- Execution mode: ARS Deep Research Phase 2 investigation
- Write scope: this L3 remediation directory only

This is a source-verification and evidence-handoff report. It does not write manuscript synthesis, hypotheses, benchmark results, or experimental conclusions. H1–H4 remain `NOT_RUN` where the Stage 1A inputs say they are not run.

## Locked decision criteria

Old and newly discovered candidates were assessed with the same criteria:

1. Direct relevance to required L3 coverage or a necessary counter-evidence/protocol guardrail.
2. Canonical identity and metadata verifiable from a source of record.
3. Non-duplicative claim-level value after source-family and version grouping.
4. Authority and an inspectable original-content path for any production-intended claim.
5. Explicit limitations, counter-evidence, and forbidden extrapolations.
6. No inference from a paper-native metric to a v5 benchmark result and no inference that literature plausibility proves H3.

Operational resources were not converted into scholarly records. No operational resource was required for this lane, and no publication year was fabricated for one.

## Reproducible search log

All searches were executed on `2026-08-14` in English. Discovery was limited to primary scholarly works and official/publisher/proceedings/author/institutional pages. Date filters were applied in the query where shown; foundational searches had no lower date bound. Search-result snippets and secondary indexes were used for discovery only, never for original-content verification.

| ID | Exact query | Databases/sites | Filters | Result pages reviewed | Scholarly candidate works after title screening | New unique candidates | New inclusions | New exclusions | Old-lane overlaps |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| Q-GAP-01 | `site:dl.acm.org/doi OR site:recsys.acm.org "next basket recommendation" repeat explore novel 2022..2026` | ACM Digital Library and official RecSys pages via web search | 2022–2026; primary papers; NBR/repeat/explore relevance | 9 | 7 | 3 | 0 | 3 | 4 |
| Q-GAP-02 | `site:pubsonline.informs.org/doi OR site:sciencedirect.com/science/article association rules recommendations hybrid sequential rules collaborative filtering` | INFORMS and ScienceDirect official pages via web search, followed by institutional-record checks | No lower date bound; association-rule recommendation or rule/CF hybrid | 17 | 5 | 2 | 1 | 1 | 3 |
| Q-GAP-03 | `site:arxiv.org/abs SASRec BERT4Rec sequential recommendation objective reproducibility split` | arXiv discovery followed by DOI/proceedings/institutional checks | Sequential objective or reproducibility; primary paper/preprint | 5 | 5 | 3 | 1 | 2 | 2 |
| Q-GAP-04 | `site:arxiv.org/abs "next basket recommendation" 2024 2025 repeat novel baseline` | arXiv | 2024–2025; direct NBR/repeat/novel relevance | 4 | 4 | 4 | 0 | 4 | 0 |
| Q-GAP-05a | `site:dl.acm.org/doi OR site:arxiv.org/abs OR site:mdpi.com "next basket recommendation" 2026` | ACM, arXiv, and MDPI via web search | 2026 through cutoff; direct NBR | 8 target/noise pages reviewed | 3 | 3 | 1 | 2 | 0 |
| Q-GAP-05b | `site:dl.acm.org/doi OR site:arxiv.org/abs "next-basket recommendation" 2025 2026 repeat explore` | ACM and arXiv via web search | 2025–2026; repeat/explore relevance | Corroborating sweep; duplicates only after candidate-level deduplication | 3 duplicate candidates | 0 | 0 | 0 | 3 |

Candidate-level flow after deduplication:

- Old-lane candidate index: `18` unique works.
- Gap-search candidate occurrences after title screening: `24`.
- Old-lane overlaps/duplicate occurrences removed from the gap set: `9`.
- New unique candidate works: `15`.
- Total unique candidate works dispositioned: `33`.
- Final retained canonical records: `15` (`12` old-lane retentions + `3` new inclusions).
- Excluded or replaced candidate works: `18` (`6` old candidates + `12` new candidates).

Every retained, excluded, and replaced candidate-level decision is represented in `candidate_registry.json`, `disposition_log.json`, or `exclusion_log.json`. Search-page noise that was not a scholarly candidate work was not counted as a candidate.

## Search and access failures

- Crossref REST API: eight DOI requests failed because the TLS connection closed unexpectedly. Status: `degraded_transport`, not unmatched. Official publisher, proceedings, institutional, and inspected full-artifact records were used instead.
- Direct MDPI HTML: returned HTTP `429`. Status: `degraded_http_429`. The official MDPI asset-host PDF was lawfully acquired and inspected, so the source was ultimately verified.
- National Yang Ming Chiao Tung University repository: the 2007 full PDF was inspectable through the research browser, but local acquisition failed because the repository TLS certificate was expired. No certificate bypass was used.
- University of Amsterdam author PDF: full content was inspected remotely; local TLS issuer-chain validation failed. No certificate bypass was used.
- In-app browser automation runtime: initialization failed with a local `EPERM` filesystem error. Ordinary web research and lawful HTTPS acquisition were used.
- Exact 2009 Information Sciences article: official metadata and abstract were available, but no lawful open full artifact of the exact journal work was found. No paywall bypass was attempted.

## Old-lane remediation

The old lane was treated as a candidate index, not ground truth. All `18/18` candidates received a locked disposition:

- `RETAIN`: 12
- `REPLACE`: 1
- `REMOVE`: 5
- `MOVE_TO_RESOURCE_REGISTRY`: 0

The replacement is the 2023 “Turning Dross” paper with Petrov and Macdonald's peer-reviewed 2022 systematic review and BERT4Rec replicability study. The replacement supplies broader implementation/training-budget evidence and an inspected lawful artifact.

The old-lane file itself contains mojibake and two initially unresolved metadata areas. This remediation does not edit that immutable input. Canonical records here use clean UTF-8, full author lists, source-of-record years/status, and no `et al.` shorthand. The 2025 Time to Split identity was reverified from its accepted author version: Danil Gusak, Anna Volodkevich, Anton Klenitskiy, Alexey Vasilev, and Evgeny Frolov; title *Time to Split: Exploring Data Splitting Strategies for Offline Evaluation of Sequential Recommenders*.

## Corpus and family counts

- Canonical scholarly records: `15`
- Independent source families: `14`
- The difference is the Liu–Lai–Lee hybrid family, which contains a 2007 conference predecessor and the expanded 2009 journal article. Those two records must not be counted as independent corroboration.
- Local full artifacts acquired and inspected: `12`
- Additional authoritative full artifacts inspected remotely: `2`
- Source-content-verified records: `14/15`
- Locator-ready records: `14/15`
- Operational resources: `0`

Method dependence is also recorded without collapsing genuinely independent studies: the Petrov–Macdonald replication is an independent source family but methodologically depends on the original BERT4Rec family.

## Audit-core acquisition status

| Audit-core candidate | Identity | Metadata | Exact-work full content | Locator ready | Status |
|---|---|---|---|---|---|
| Apriori 1994 | verified | verified | verified | yes | Official VLDB PDF stored and inspected |
| Multi-item Association Rules 2014 | verified | verified | verified | yes | Author manuscript stored and inspected; official INFORMS metadata used |
| Hybrid Sequential Rules + CF 2009 | verified | verified | **not verified** | **no** | Official metadata/abstract only; exact full text remains queued |
| SASRec 2018 | verified | verified | verified | yes | Author version stored and inspected |
| Next Basket Reality Check 2023 | verified | verified | verified | yes | Author version stored and inspected |
| Time to Split 2025 | verified | verified | verified | yes | Accepted author version stored and inspected |

Exact audit-core content/locator completion is `5/6`. The lawful 2007 predecessor in the same hybrid family was fully inspected and is locator-ready, but it is explicitly not treated as verification of the exact 2009 journal work.

## Required coverage disposition

| Required area | Retained coverage | Boundary |
|---|---|---|
| Apriori support/confidence and association-rule recommendation | Agrawal–Srikant 1994; Ghoshal–Sarkar 2014 | Apriori mines rules; recommendation requires an additional scoring/ranking policy. |
| SASRec, BERT4Rec, and sequential objectives | SASRec 2018; BERT4Rec 2019; Petrov–Macdonald 2022 | Next-item and sampled source protocols are not the v5 basket/full-catalog protocol. |
| Next-basket repeat/explore/novel behavior | Reality Check 2023; Repetition and Exploration 2023; Mansouri–Lahmiri–Vahidov 2026 | Aggregate basket quality cannot establish novel-item quality. |
| Mask-Swap, BTBR, or direct basket baselines | Mask-Swap/BTBR 2023; M² 2023 | Effects are dataset/protocol dependent; paper metrics are not v5 results. |
| Hybrid precedents and attribution ablations | Liu–Lai–Lee 2007; Wide & Deep 2016; HAM 2022; M² 2023; 2026 repeat/explore hybrid | External ablations motivate a controlled v5 ablation; they do not estimate H3. |
| Temporal and implementation sensitivity | Time to Split 2025; Petrov–Macdonald 2022 | Supports protocol discipline, not post-result protocol changes. |

## Claim-control outcomes

`claim_cards.json` contains eight bounded cards:

- Seven are supported by inspected original content and are not planning-only.
- One is a search-bounded gap statement and is explicitly `planning_only=true` and `partially_supported`.
- No production-intended claim relies on the old lane summary, metadata alone, a search snippet, or a source without an original-content locator.
- The content-unverified 2009 article is excluded from the evidentiary source list of production-intended hybrid claims.

Forbidden conclusions are enforced in the cards and source records:

- Apriori is not labeled a ranking model on mining-only evidence.
- Literature plausibility is not treated as proof of H3.
- Aggregate basket gain is not treated as novel-item gain.
- No paper-native metric is reported as a v5 benchmark result.

## Remediation responsibility

- `ST1B-META-003`: lane share complete. Full author lists are present for all retained records; canonical fields contain no `et al.`, placeholder years, or detected mojibake. The immutable mojibake old lane was not edited.
- `ST1B-SYNTH-001`: lane share complete. Canonical-record count (`15`) and independent-family count (`14`) are separate; version and method dependencies, support scope, counter-evidence, and forbidden extrapolations are explicit. No manuscript synthesis was written.
- `ST1B-LOCATOR-001`: lane share complete under the locked local gate with an explicit downstream restriction. `14/15` retained records are original-content verified and locator-ready; the exact 2009 hybrid journal article remains unresolved and cannot support production prose until acquired.

## Downstream blockers and restrictions

1. Acquire and inspect an authorized full artifact of Liu, Lai, and Lee (2009) before making any exact-work content claim. Authorized routes include institutional subscription, author-supplied copy, interlibrary loan, or licensed document delivery.
2. Do not substitute the 2007 conference predecessor for the exact 2009 journal contents. It may support only claims explicitly attributed to the 2007 work/family.
3. Keep H3 `NOT_RUN`. The complete v5 estimand—Apriori train-only Wide branch, frozen train-mined rule-aligned evaluation cohort, Full versus No-Wide, temporal full-catalog evaluation—was not evaluated by any inspected source.
4. Preserve the Stage 1A naming distinction: when held-out consequent membership is used, the cohort is `train-mined rule-aligned evaluation cohort`, not purely train-defined.
5. Any v5 Full/No-Wide comparison must share the Deep branch, candidates, masks, seeds, tuning budget, calibration, tie-breaking, and target; external hybrid studies do not relax that requirement.

## Local gate

**Verdict: PASS**

Rationale: the old candidate index is 100% dispositioned; the gap search is reproducible through the cutoff; retained canonical metadata are verified; all source-family/version dependencies are explicit; all seven required artifacts are present and machine-parseable; production-intended claims use inspected original-content locators; unresolved acquisition and rights conditions are carried forward rather than silently passed. The remaining 2009 full-text issue is a downstream source-use blocker, not a hidden gate waiver: that record is marked `source_content_verified=false`, `locator_ready=false`, queued, and barred from production-intended content claims.
