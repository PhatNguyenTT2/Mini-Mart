# Stage 1B Remediation R1 — Fresh R6 Re-audit Contract

Status: `R6_REMEDIATION_PASS_REAUDIT_READY`

## Runtime and independence

- Model: `gpt-5.6-sol`.
- Reasoning: `high`.
- Execution: fresh dedicated task/worktree with no access to prior DA confidence statements beyond frozen artifacts.
- Read-only over R3–R6 and the remediation overlay.
- Write only a new re-audit bundle; do not revise any artifact under audit.

## Objective

Re-run Devil's Advocate Checkpoint 2 against the original R5 evidence plus the immutable R6 remediation overlay. Determine whether `R6-MAJ-001` is closed, whether `R6-MIN-002` is addressed, and whether any new Critical/Major issue was introduced.

`R6-MIN-001` / T-002 remains scholar-owned and cannot be closed by the auditor.

## Fail-closed input gate

- Match `r6_reaudit_input_manifest.json` exactly.
- Verify all frozen R5, original R6, and remediation bytes/hashes.
- Require R5 final validation `29/29`, original R6 final validation `26/26`, and remediation final validation `33/33`.
- Require remediation verdict `PASS_FRESH_R6_REAUDIT_ONLY`, exact source/family denominator replay, 44/44 counter-evidence bindings, and 33/33 unchanged citation marker/anchor pairs.
- Require all 12 tension pairs still pending, Stage 1B unsealed, Stage 2 unauthorized, and H1–H4 `NOT_RUN`.

## Re-audit scope

1. Independently replay exact source sets and canonical/nominal/dependency-adjusted denominators for all five themes.
2. Check every prose denominator pointer against machine-readable arrays.
3. Verify 44 claim IDs/dispositions and counter-evidence joins without trusting remediation conclusions.
4. Re-run source-family dependence, strongest-source removal, hostile-reviewer, and boundary stress tests.
5. Confirm all 33 citation marker/anchor pairs remain valid and unchanged.
6. Re-assess each original R6 finding and surface any new issue caused by remediation.
7. Preserve all 12 scholar confirmations as pending and retain the T-002 dispute recommendation without self-adjudication.

## Write scope and outputs

Write only under:

`research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase3_analysis/devils_advocate_cp2_reaudit/`

Required outputs:

1. `r6_reaudit_report.md`;
2. `r6_reaudit_findings.json`;
3. `tension_adjudication_packet_reaudit.json`;
4. `r6_reaudit_validation_receipt.json`;
5. `r6_reaudit_handoff.json`;
6. optional validator/support script(s) in the same scope.

## Verdict

- `PASS_PENDING_SCHOLAR_CONFIRMATION`: Critical=0, Major=0, remediation findings replay closed/addressed, all deterministic checks pass, and all 12 scholar confirmations remain pending. R7 remains unauthorized until user adjudication.
- `REVISE`: any Critical/Major finding remains or a new Critical/Major issue appears.

The re-auditor must not emit full PASS, adjudicate tensions, run R7–R9, seal Stage 1B, or authorize Stage 2 citations.
