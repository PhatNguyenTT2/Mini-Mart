# Stage 1B Remediation R1 — R3 Integration Contract

Status: `LOCKED_INPUT_READY`

Gate receipt (2026-08-14): L1–L5 = 5/5 PASS; 145 files and 68,391,781 bytes received; 56 JSON files parsed; 30/30 producer-declared non-self hashes matched; prohibited user-owned read fields = 0.

Runtime lock: `gpt-5.6-sol`, reasoning `xhigh`, one fresh Codex worktree.

## Phase boundary

R3 remains ARS Deep Research Phase 2. It merges and verifies bibliographic identities, metadata, source families, evidence status, operational-resource records, and bounded claim cards. It must not produce Phase 3 synthesis, Introduction, Related Work, manuscript prose, or H1–H4 results.

The current central task owns intake validation and freezes the input manifest. The fresh R3 task is the only writer under:

`research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase2_investigation/integration/`

## Mandatory input gate

R3 may start only when:

1. L1–L5 each contain the seven lane-contract artifacts;
2. all six JSON files per lane parse;
3. all producer-declared non-self hashes match;
4. every lane local verdict is `PASS`;
5. all input bytes are frozen in `r3_input_manifest.json`;
6. no lane artifact contains prohibited user-owned `human_read_source` or `human_read_at` fields.

Missing or invalid input is `HANDOFF_INCOMPLETE`; do not integrate a partial lane set.

## Merge order

1. Validate all lane handoffs and input-manifest hashes.
2. Merge candidate records by identity before merging descriptions or claim prose.
3. Deduplicate by normalized DOI, source-of-record identifier, canonical title, author/year consistency, and version-family relation.
4. Separate scholarly works from operational datasets, repositories, provider pages, packages, and adapters.
5. Re-verify all identity conflicts and high-risk/non-Crossref/official-resource exceptions against authoritative sources.
6. Record S2/OpenAlex/Crossref degradation as degradation, not as an unmatched result.
7. Freeze source-family counting rules and report canonical records separately from independent families.
8. Apply identical inclusion/exclusion criteria to old and new lane candidates.
9. Recompute publication-year, recent-source, peer-review, quality-grade, acquisition, content-verification, and locator counts from merged records.
10. Merge bounded claim cards only after source keys and source-family IDs are stable.

## Non-negotiable integrity rules

- No ghost citation, dangling source key, duplicate canonical key/DOI/title, placeholder publication year, canonical `et al.`, or mojibake.
- A scholarly record requires a verified numeric publication year.
- Operational resources remain outside `literature_corpus_r1.json`; availability, code license, paper license, dataset rights, and redistribution status remain separate.
- `peer_reviewed=true` requires direct evidence basis. Editorials/essays are not silently counted as peer-reviewed research.
- `source_verified_against_original=true` requires lawful acquisition and an affirmative verification method.
- Source-family dependence is an invariant in data, not a prose-only note.
- Production-intended claims without original-content locators remain blocked or planning-only.
- Raw metrics across different datasets/pipelines are never converted into comparative benchmark evidence.

## Required outputs

1. `source_registry_r1.json`
2. `operational_resource_registry.json`
3. `source_family_map_r1.json`
4. `deduplication_report_r1.md`
5. `source_quality_matrix_r1.json`
6. `source_verification_report_r1.md`
7. `literature_corpus_r1.json`
8. `annotated_bibliography_r1.md`
9. `claim_source_map_r1.md`
10. `r3_handoff.json`

All JSON must parse and all cross-file references must resolve. The handoff records file hashes, counts, unresolved acquisition/locator/rights questions, and the local R3 verdict.

## R3 pass gate

- canonical key/title/DOI duplicates: 0;
- dangling source keys and family IDs: 0;
- ghost citations: 0;
- placeholder publication years: 0;
- mojibake and canonical shortened-author metadata: 0;
- 100% of `peer_reviewed=true` records have an evidence basis;
- scholarly corpus target: 45–55 records, or a documented evidence-based deviation;
- core shortlist target: 18–24 sources;
- canonical-record and independent-family counts are both reported;
- unresolved original-content acquisition and locator work is queued for R4 rather than misreported as complete.

R3 PASS authorizes R4 source acquisition. It does not seal Stage 1B and does not authorize Stage 2 production citations.
