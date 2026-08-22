# Stage 1B Remediation R1 — R6 Findings Remediation Contract

Status: `R6_REVISE_REMEDIATION_READY`

## Runtime and ownership

- Model: `gpt-5.6-sol`.
- Reasoning: `high`.
- Execution: one fresh dedicated task/worktree acting as synthesis remediation owner.
- Frozen R3, R4, R5, and R6 artifacts are read-only.
- Write a versioned overlay; never overwrite the R5 synthesis bundle or R6 critique.

## Objective

Close `R6-MAJ-001` and address `R6-MIN-002` without changing the underlying 44 claim intents or fabricating new evidence:

1. enumerate the exact scholarly source keys supporting every synthesis theme;
2. report canonical-record, nominal-family, and dependency-adjusted-family counts separately;
3. apply every relevant source-family dependency edge and expose the adjustment;
4. make every prose denominator replayable against the exact enumerated sets;
5. carry bounded counter-evidence and source/locator pointers for all 44 claim rows in a hash-bound overlay.

`R6-MIN-001` / T-002 remains scholar-owned. The remediation may present the DA recommendation but must not change `scholar_confirmation`, pair assessment, or resolution status before user adjudication.

## Fail-closed input gate

- Match `r6_remediation_input_manifest.json` exactly.
- Verify all frozen R5 and R6 artifacts and handoffs.
- Require R5 final replay `29/29 PASS` and R6 final replay `26/26 PASS`.
- Require R6 verdict `REVISE`, `Critical=0`, `Major=1`, and exact blocker `R6-MAJ-001`.
- Require 44 claims, 12 tension pairs, and 12 pending scholar confirmations.
- Require Stage 1B unsealed, Stage 2 citations unauthorized, and H1–H4 `NOT_RUN`.

If any gate fails, emit `HANDOFF_INCOMPLETE` and no partial overlay.

## Write scope

Write only under:

`research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase3_analysis/remediation_r6/`

Required outputs:

1. `theme_evidence_denominators.json`;
2. `claim_counter_evidence_overlay.json`;
3. `claim_source_map_r1_remediated.json`;
4. `synthesis_report_r1_remediated.md`;
5. `r6_remediation_report.md`;
6. `r6_remediation_validation_receipt.json`;
7. `r6_remediation_handoff.json`;
8. optional validator/support scripts in the same scope.

## Remediation rules

- Preserve exactly 44 claim IDs, 22 citation-ready candidates, and 22 planning-only rows.
- Do not add or delete sources, claims, themes, or tension pairs.
- Preserve the original one-shot claim-intent manifest and explicitly report zero intended-claim drift.
- For each theme, list exact source keys and family IDs; derive all three denominators from those lists rather than constants.
- Theme 5 must remain operational and explicitly single-family/fragile; do not mix scholarly and operational counts.
- For every dependency adjustment, cite the exact source-family edge and `counting_effect` from frozen R3.
- Every remediated visible citation keeps the verified R5 ref/anchor pair unchanged.
- Counter-evidence overlay must use only upstream bounded counter-evidence with resolvable source and locator pointers; no invented counterclaim.
- Keep T-002 pending scholar adjudication and preserve all other tension statuses.
- No manuscript drafting, benchmark, H1–H4, R7–R9, seal, or Stage 2 authorization.

## PASS gate

- Exact theme source sets and all denominator arithmetic replay with zero mismatch.
- Canonical, nominal-family, and dependency-adjusted-family counts are never conflated.
- All 44 claim rows bind to bounded counter-evidence entries, including explicit `none_identified` only when upstream truly contains none.
- All claim/source/family/locator references resolve; duplicates and dangling references are zero.
- All citation markers and anchors remain unchanged and valid.
- R6-MAJ-001 is marked `REMEDIATED_PENDING_REAUDIT`; the task does not self-close the finding.
- R7 remains unauthorized and all 12 scholar confirmations remain pending.

PASS authorizes only a fresh R6 re-audit of the remediation overlay.
