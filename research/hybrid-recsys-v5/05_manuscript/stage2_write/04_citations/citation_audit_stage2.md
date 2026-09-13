# Stage 2 Citation Audit

**Status:** `POST_DRAFT_STATIC_AUDIT_COMPLETE_WITH_COMPILE_UNAVAILABLE`  
**Checkpoint:** P2-G6 complete; mandatory Stage 2.5 integrity review remains
open  
**Authority:** R9 Stage 1B literature handoff and its hash-bound claim/locator
registries

## Scope

This report audits the Stage 2 draft after the user-approved outline was
implemented. The authoritative manuscript is
`03_draft/master_draft_stage2.tex`, which includes
`03_draft/introduction_related_work_stage2.tex`. The audit is static and
provenance-focused. It does not certify the scientific validity of the
unexecuted v5 experiment, and it does not replace the mandatory Stage 2.5
integrity gate.

## Current Determinations

| Check | Status | Basis |
|---|---|---|
| Authorized claim population | PASS | All 22 R9 `citation-ready` rows remain represented in the post-draft matrix. |
| Planning-only claim exclusion | PASS | All 22 planning-only/prohibited rows remain excluded; no implicit promotion was detected. |
| Locator coverage | PASS | The matrix preserves 33 verified non-null R9 locator pairs. |
| Source identity binding | PASS | All cited source keys resolve to the frozen literature corpus and locator registry. |
| In-text citation to bibliography | PASS_STATIC | 61 effective citation occurrences resolve to 35 unique keys in `refs_stage2.bib`. |
| Bibliography orphan check | PASS_STATIC | All 35 bibliography entries are cited at least once in the effective manuscript. |
| Provenance marker coverage | PASS_STATIC | 61 citation occurrences have adjacent `ref` and `anchor` markers; marker bindings replay to the locator registry. |
| Claim-to-prose bindings | PASS_STATIC | 22 authorized rows have actual section anchors and source-key occurrence counts in the matrix. |
| Public result artifact binding | PASS_STATIC | The four public rows and table `tab:public-validation` bind to the admitted aggregate artifact SHA-256. |
| Stale historical marker scan | PASS | No historical `1,380`, `0.4940`, or `0.8507` value is present in the new draft. The quarantined historical manuscript was not modified. |
| Blocked claim scan | PASS | No Hybrid superiority, H1-H4 outcome, strict `0.2768` reproduction, causal, production, or state-of-the-art claim is present. |
| Namespace separation | PASS | Public validation, official reproduction, harmonized v5, and future follow-up surfaces remain distinct; no numeric join is authorized. |
| Word-count estimate | PASS_APPROXIMATE | Deterministic lexical estimate is approximately 5,752 visible words, within the configured 5,500-6,500 body range. |
| LaTeX compilation | UNAVAILABLE | `pdflatex`, `bibtex`, `xelatex`, `latexmk`, `tectonic`, and `pandoc` are unavailable in the current environment. Compilation must be rerun at Stage 2.5 or on a configured LaTeX host. |

## Evidence Bindings

- R9 canonical handoff: `3391117fb1f7f2a13b1c3d246c669153d0bd7251a47d67b4f51ecb4548e7e7f7`.
- R9 seal: `5353afaf36fb7146d58ff8e461f9c1586f2a253231bf7d1b162d77ed97a2d3b7`.
- Effective citation occurrences: 46 from the included fragment plus 15
  direct occurrences in the root document.
- Unique bibliography keys: 35.
- Public aggregate artifact: `512fb8ad8862f5e677ec18f369d310ae58c9d6f3c4f7b2e79c17ede389930c17`.
- Root manuscript binding: `master_draft_stage2.tex` SHA-256
  `8fa271e44b7d1be5fb5ef14921d3b568180e175032268b8120aba438694d6f93`.
- Included fragment binding: `introduction_related_work_stage2.tex` SHA-256
  `338b55f4a330cae9d9a9ba87136e734979a90eeeff9b6ac0f81debe13ff8ac72`.

## Claim and Language Controls

The draft uses the conditional thesis authorized by the Stage 2 configuration.
The public Pop/BPR rows are described as procedural, namespace-scoped evidence.
The following remain blocked until a separately packeted and audited follow-up
experiment:

- Hybrid superiority or an `outperforms` statement;
- H1, H2, H3, or H4 outcome language;
- strict official reproduction of the illustrative `0.2768` value;
- direct numeric comparison between MovieLens public validation and v5;
- production effectiveness, causal improvement, or state-of-the-art language;
- reuse of historical values from `workspace/final/paper.tex`.

The matrix also records the controlled benchmark counts as manifest-level facts,
not observed shopper outcomes. The manuscript does not turn those declarations
into a result claim.

## Compilation Limitation

The static source has been normalized for common LaTeX hazards, including
escaped namespace underscores and removal of Markdown-style code delimiters
from prose. A real compile was not possible because the toolchain is absent.
Therefore this report does not claim that the PDF, bibliography labels, page
breaks, or final typography have passed. Stage 2.5 must run a clean compile and
resolve any toolchain-specific warnings before submission-oriented work.

## Next Gate

Stage 2 drafting stops here at the mandatory checkpoint. Stage 2.5 must
independently verify the exact input set, reparse the JSON artifacts, replay the
claim and locator bindings, run the available LaTeX toolchain, and inspect the
result namespace policy. It must not promote any blocked empirical claim or
reopen the v5 TEST surface.
