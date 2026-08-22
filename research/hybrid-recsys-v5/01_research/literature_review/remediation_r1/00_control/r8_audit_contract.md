# Stage 1B Remediation R1 — R8 Independent Audit Contract

Status: `R8_AUTHORIZED`

## Runtime, independence, and authority

- Model: `gpt-5.6-sol`.
- Reasoning: `high`.
- Execution: fresh dedicated task/worktree.
- Role: independent read-only auditor; do not act as packet builder or remediator.
- Consume the immutable R7 packet and its canonical root. Do not rely on central/lane confidence statements.
- Write only the R8 audit bundle. Never modify R7 or earlier artifacts.

## Fail-closed input gate

1. Match `r8_input_manifest.json` exactly.
2. Run the R7 final validator and independently recompute all 193 member byte lengths, hashes, canonical ordering, root preimage, and root SHA-256.
3. Require R7 verdict `PASS_READY_FOR_INDEPENDENT_AUDIT`, central validation `29/29 PASS`, canonical root SHA-256 `f0f2d56e42ce0f181f83182ddffe1060bf8994f50ababd4b0dbe563a942370dd`, Stage 1B unsealed, Stage 2 unauthorized, and H1–H4 `NOT_RUN`.
4. Fail if mutable live-state bytes, absolute/worktree paths, timestamps, self-hashes, or nondeterministic ordering enter the canonical root preimage.

## Independent audit scope

1. Packet completeness and replayability: verify current and superseded artifacts required for audit history are present and role-labelled.
2. Corpus integrity: replay canonical source identities, deduplication, source-family dependence, recent-source count, core-source contract, operational-resource separation, and locator coverage.
3. Claim integrity: replay 44 unique claims, 22 citation-ready candidates, 22 planning-only claims, claim/source/counter-evidence joins, and all 33 visible citation/non-none locator pairs.
4. Synthesis integrity: replay five theme source sets and canonical/nominal/dependency-adjusted denominators; test strongest-source removal and hostile-reviewer boundaries.
5. Tension integrity: verify the frozen original 12-pair artifact plus the user-owned overlay; effective results must be 11 confirmed, T-002 disputed/reclassified to `no_material_conflict/not_applicable`, zero pending, and zero unresolved disputes.
6. Boundary integrity: no manuscript drafting, no benchmark execution, no H1–H4 result claim, no unsupported superiority/novelty/external-validity claim, and no premature Stage 2 authorization.
7. Re-run relevant upstream deterministic validators and report any degraded/unavailable check explicitly rather than converting it to PASS.
8. Record Critical, Major, Minor, and Observation findings without repairing them.

## Write scope and exact output roster

Write only under:

`research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase5_audit/r8_independent_audit/`

Required outputs:

1. `r8_independent_audit_report.md`;
2. `r8_findings.json`;
3. `r8_packet_replay.json`;
4. `r8_validation_receipt.json`;
5. `r8_handoff.json`;
6. `validate_r8_audit.py`.

No additional files are allowed in the write scope.

## Verdict and boundary

- `PASS_READY_TO_SEAL`: Critical=0, Major=0, deterministic checks pass, no unresolved scholar decision remains, and no R7 input was modified.
- `REVISE`: any Critical/Major issue, packet/root mismatch, unresolved decision, citation/claim gate failure, or phase-boundary breach.

R8 must not repair findings, perform R9, seal Stage 1B, authorize Stage 2, draft manuscript prose, run benchmarks, or change H1–H4 from `NOT_RUN`.
