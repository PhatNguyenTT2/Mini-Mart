# Stage 1B Remediation R1 — R6 Devil's Advocate Checkpoint 2 Contract

Status: `R5_PASS_R6_READY`

## Runtime and independence

- Model: `gpt-5.6-sol`.
- Reasoning: `high`.
- Execution: one fresh dedicated task/worktree.
- R6 is read-only over all frozen R3, R4, and R5 evidence.
- The R6 task may critique but must not revise the synthesis, claim map, tension inventory, or acquisition records.

## Phase boundary

R6 is ARS Deep Research Phase 3 Devil's Advocate Checkpoint 2. It stress-tests the completed R5 synthesis for cherry-picking, confirmation bias, unresolved contradictions, source-family dependence, alternative explanations, hostile-reviewer attacks, scope transfer, and the strength of bounded positioning.

R6 must not perform manuscript drafting, benchmark execution, H1–H4 interpretation, R7 packet freeze, R8 audit, R9 seal, or Stage 2 citation authorization.

## Fail-closed input gate

Before writing an R6 output, the task must:

1. match `r6_input_manifest.json` exactly;
2. verify every frozen R5 input byte/hash plus the R5 handoff and append-only ledger;
3. run `validate_r5_synthesis.py --final` and require `29/29 PASS`;
4. require R5 verdict `PASS`, `r6_authorized=true`, 44 claims, 22 citation-ready candidates, 22 planning-only, 33/33 verified citation–locator pairs, and 12 pending scholar confirmations;
5. transitively require R3 `PASS / 20-of-20` and R4 `PASS / 22-of-22`;
6. require H1–H4 `NOT_RUN`, Stage 1B unsealed, and Stage 2 production citations unauthorized.

Any failed gate returns `HANDOFF_INCOMPLETE` and writes no partial R6 bundle.

## Required attacks

1. Steel-man the strongest bounded version of each of the five synthesis themes before attacking it.
2. Test cherry-picking and confirmation bias against the full 44-claim map, including planning-only and counter-evidence rows.
3. Remove the strongest source or source family for each major theme and report whether the claim still stands.
4. Recount convergence by canonical records and independent families; detect family double counting.
5. Challenge all seven `conditional_difference` tension resolutions and the five non-tension classifications; do not invent complete pairwise coverage.
6. Test whether source selection, publication status, preprint dependence, unavailable payloads, or replacements could change positioning.
7. Attack the fixed boundaries: cold-item/cold-user, Wide & Deep/Apriori, transfer/H4, literature/empirical results, official reproduction/harmonized benchmark.
8. Stress-test Complete Journey rights/access separation and the bounded Liu 2007 replacement.
9. State the strongest hostile-reviewer counterargument and the minimum defensible concession.
10. Apply the ARS severity taxonomy accurately and log concession-threshold decisions if any rebuttal is considered.

## Scholar-owned tension checkpoint

R6 may recommend `confirm` or `dispute` for each pair with a rationale, but it must not set `scholar_confirmation` itself. It emits a review packet retaining `scholar_confirmation: pending` for all twelve pairs.

R7 remains unauthorized until the user explicitly adjudicates every pair and Critical/Major findings are zero after any required remediation.

## Write scope and outputs

Write only under:

`research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase3_analysis/devils_advocate_cp2/`

Required outputs:

1. `devils_advocate_checkpoint2_r1.md`;
2. `r6_findings.json`;
3. `tension_adjudication_packet.json`;
4. `r6_validation_receipt.json`;
5. `r6_handoff.json`;
6. optional validator/support script(s) within the same scope.

## Verdict and gate

- `PASS_PENDING_SCHOLAR_CONFIRMATION`: Critical=0, Major=0, output contract passes, but one or more scholar confirmations remain pending. This is the expected pre-adjudication state and does not authorize R7.
- `REVISE`: one or more Critical or Major findings require bounded remediation. R7 is not authorized.
- `PASS`: legal only after a separate user-authored adjudication artifact confirms/disputes every pair and any disputes are resolved or explicitly flagged. The R6 worker itself cannot mint this state during initial emission.

The handoff must report exact severity counts, stress-test results, per-pair recommendations, remaining pending confirmations, output hashes, and phase boundaries.
