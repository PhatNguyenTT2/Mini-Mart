# Source Verification Report — Stage 1B Pre-Audit

## Overall assessment

- Sources reviewed: 55.
- Bibliographic/source-of-record identity verified: 55.
- Fabricated or rejected after central verification: 0.
- Grade A: 12; Grade B: 39; Grade C: 4.
- Predatory-publication alerts: 0.
- DOI-bearing records after correction: 46; records with no DOI: 9.
- Original full texts locally acquired: 0.
- `source_verified_against_original`: false for all 55.

“Verified” in this report means title/author/year/venue/DOI or operational source identity. It does not mean every method, result, quotation, or page locator has been checked against a locally acquired original PDF.

## Verification stack

| Layer | Result | Interpretation |
|---|---:|---|
| Semantic Scholar | 0 matched; 55 degraded | First lookup returned HTTP 429 after retries. Signals were omitted with `api_degraded`; no negative inference was made. |
| OpenAlex | 50 matched; 4 unmatched; 1 degraded | Four operational/non-indexed records were checked against official sources. SimGCL's OpenAlex request returned HTTP 400 and was checked through DOI/official metadata. |
| Crossref | 40 matched; 15 unmatched; 0 degraded | Unmatched includes no-DOI works, non-Crossref registrants, and abbreviated Crossref titles. Fifteen exception checks were completed. |
| DataCite / official records | 15 exception checks | Covered UAI/VLDB/NeurIPS/ACL/ICLR/arXiv and provider-controlled dataset resources. |

Crossref abbreviates the registered titles for LightGCN, BERT4Rec, and SimGCL; the DOI records resolve to the expected works and are independently supported by OpenAlex or official venue metadata. ViHoRec, OTTO, and MUSE use DataCite/arXiv/Kaggle DOI records rather than Crossref.

## Quality grading

The detailed 55-row matrix is in `source_quality_matrix.json`. ARS design levels are separated from field-relative fitness:

- Most peer-reviewed computational studies are Level VI by the generic seven-level design hierarchy but Grade A/B for their bounded technology claim.
- Standards/operational records are Level VII and may still be Grade B for source facts.
- ViHoRec and MUSE remain preprints; H&M and Complete Journey retain metadata/rights caveats. These four are Grade C.

Older sources were retained only for seminal definitions or direct historical architecture/method precedent. Paper-native performance values are never transferred into the v5 benchmark.

## Predatory and publication-status checks

No accepted journal or conference identity showed a predatory-venue indicator in the source-of-record check. Preprints are labelled as preprints rather than treated as journals. Operational dataset pages are labelled as resources rather than peer-reviewed studies.

This was not a complete Scopus/WoS/COPE/Cabells or retraction-database audit. The independent audit should sample current publication status and retraction signals for high-impact claims.

## Conflict-of-interest assessment

No critical undisclosed conflict was identified from metadata. Industry-authored system/dataset sources (including Wide & Deep, YouTube/NDR, Amazon-M2, Coveo, OTTO, H&M, Complete Journey, and MUSE) carry a contextual institutional-interest flag. Their internal or challenge results are not used as transferable efficacy evidence.

This is not a full author-disclosure audit.

## Flagged sources

- ViHoRec (2026): verified arXiv/DataCite identity; preprint-only; source-platform and redistribution caveats remain.
- MUSE/TAOBAO-MM (2025): verified arXiv identity; preprint-only and revision-sensitive.
- H&M competition: official resource confirmed, but release year and durable primary licensing metadata remain unresolved in the central registry.
- Complete Journey: provider identity and dataset description confirmed; exact edition, package/provider scope, checksum, and governing rights remain unresolved.

Recommendation: retain all four only for explicitly caveated resource/status claims. They must not carry superiority, novelty, or strict-H4 claims.

## Verification limitations and downstream gate

- No local PDF acquisition means no production-grade page/section anchors.
- Claim cards are grounded in official abstracts/records and lane extraction, not complete source-content audits.
- External dataset legal/provenance compatibility remains open.
- Final independent Sol Ultra audit must check the frozen claim map, dependence groups, forbidden extrapolations, and locator gaps before Stage 1B is sealed.

