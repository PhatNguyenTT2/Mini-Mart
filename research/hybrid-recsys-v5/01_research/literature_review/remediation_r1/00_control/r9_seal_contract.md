# Stage 1B Remediation R1 — R9 Seal and Stage 2 Handoff Contract

Status: `R9_AUTHORIZED`

## Runtime and role boundary

- Model: `gpt-5.6-sol`.
- Reasoning: `high`.
- Execution: dedicated task/worktree acting as the final Stage 1B sealer.
- Consume only frozen R7 and central-validated R8 artifacts plus their control manifests.
- Do not perform a new semantic research synthesis, revise frozen artifacts, or override R8 findings.
- Write only the R9 seal/handoff bundle; do not edit central pipeline state.

## Fail-closed seal gate

1. Match `r9_input_manifest.json` exactly and verify all declared byte/SHA bindings.
2. Re-run R7 final validation and R8 final validation read-only.
3. Require R7 `PASS_READY_FOR_INDEPENDENT_AUDIT` with `29/29 PASS`, R8 `PASS_READY_TO_SEAL` with `60/60 PASS`, and severity `Critical=0`, `Major=0`, `Minor=0`.
4. Require the 193-member R7 packet and canonical root SHA-256 `f0f2d56e42ce0f181f83182ddffe1060bf8994f50ababd4b0dbe563a942370dd` to replay exactly.
5. Require scholar adjudication complete: 11 confirmed, T-002 disputed and effectively reclassified to `no_material_conflict/not_applicable`, zero pending/unresolved.
6. Require H1–H4 and benchmark training/evaluation to remain `NOT_RUN`.

## Seal requirements

1. Preserve the initial v0 audit `FAIL` as history and record that remediation R1 supersedes it only for Stage 1B completion; do not erase or rewrite v0.
2. Account for every original audit finding with a closure basis and immutable evidence pointer. Any unaccounted finding blocks the seal.
3. Bind the Stage 1B seal to the R7 canonical root, R8 handoff hash, R8 severity arithmetic, scholar adjudication hash, and exact R9 input manifest hash.
4. Define a deterministic seal preimage and seal SHA-256 that excludes timestamps, absolute paths, worktree paths, mutable state, and self-hashes.
5. Clearly separate deterministic integrity evidence from semantic audit judgment; do not describe the seal as proof of scientific correctness, novelty, superiority, external validity, or benchmark success.

## Stage 2 handoff requirements

1. Authorize only the 22 citation-ready candidates for bounded Stage 2 drafting use; retain all verified source/locator/claim restrictions.
2. Keep the 22 planning-only claims prohibited from production citation until their own prerequisites are satisfied.
3. Carry the 33 verified citation/non-none locator pairs, claim map, counter-evidence overlay, source-family dependence, theme denominators, tension overlay, corpus/operational-resource separation, and core-source/acquisition records by immutable pointer and SHA.
4. Prioritize Introduction and Related Work as downstream writing targets without drafting those sections in R9.
5. State that H1–H4, benchmark comparison, empirical superiority, dataset compatibility, and training/evaluation results remain unauthorized as factual results until the experiment pipeline runs on a common dataset/reference protocol.
6. Stage 2 authorization is bounded literature-drafting authorization, not permission to fabricate citations, results, or benchmark claims.

## Write scope and exact output roster

Write only under:

`research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase6_seal/r9_stage1b_seal/`

Required outputs:

1. `stage1b_r1_seal_manifest.json`;
2. `stage2_literature_handoff.json`;
3. `r9_seal_report.md`;
4. `r9_validation_receipt.json`;
5. `r9_handoff.json`;
6. `validate_r9_seal.py`.

No additional files are allowed in the write scope.

## Verdict

- `PASS_STAGE1B_SEALED`: all seal gates pass, every original finding is accounted for, the deterministic seal replays, and the bounded Stage 2 handoff is complete.
- `REVISE`: any missing closure, hash/validator/root mismatch, unresolved decision, boundary overreach, or output validation failure.

R9 must not draft manuscript prose, run benchmark/training/evaluation code, claim H1–H4 results, or authorize planning-only claims as production citations.
