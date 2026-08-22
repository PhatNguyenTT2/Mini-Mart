# Stage 1B Remediation R1 — R7 Freeze Packet Contract

Status: `R7_AUTHORIZED`

## Runtime and role boundary

- Model: `gpt-5.6-sol`.
- Reasoning: `high`.
- Execution: fresh dedicated task/worktree.
- Role: packet builder and deterministic validator, not semantic auditor.
- Read-only over all R0–R6 artifacts and the scholar adjudication overlay.
- Write only the R7 packet bundle. Do not edit any input artifact or central pipeline state.

## Fail-closed input gate

1. Match `r7_input_manifest.json` exactly, including byte counts and SHA-256 values.
2. Recursively replay all path/byte/hash declarations reachable through the frozen R6 re-audit manifest and handoffs.
3. Require R5 `29/29 PASS`, original R6 `26/26 PASS` with `REVISE`, remediation `33/33 PASS`, and fresh R6 re-audit `26/26 PASS` with `Critical=0`, `Major=0`.
4. Require an explicit user-owned adjudication for all 12 tension pairs: 11 confirmed, T-002 disputed and reclassified to `no_material_conflict/not_applicable`, zero pending, zero unresolved disputes.
5. Require 44 claims, 22 citation-ready candidates, 22 planning-only claims, 33 verified citation/locator pairs, H1–H4 `NOT_RUN`, Stage 1B unsealed, and Stage 2 unauthorized.

## Freeze requirements

1. Select every immutable artifact required to replay R3–R6, the remediation overlay, re-audit, and scholar adjudication. Do not silently omit superseded evidence needed for audit history.
2. Separate packet payload artifacts from control/receipt artifacts and document why each item is included.
3. Normalize every path to a repository-relative forward-slash path and sort entries lexicographically by normalized path.
4. Record exact byte length and SHA-256 for every packet member.
5. Define and implement a canonical root-hash algorithm. The root preimage must be deterministic UTF-8 JSON derived only from the sorted immutable member tuples `(path, bytes, sha256, role)`; it must not include timestamps, absolute paths, worktree paths, self-hashes, or mutable state.
6. Recompute the root hash independently in the validator and fail if ordering, path normalization, bytes, member hashes, or preimage semantics differ.
7. Preserve the original T-002 row and carry the scholar overlay as the authoritative effective classification; do not rewrite frozen R5/R6 files.

## Write scope and required outputs

Write only under:

`research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase4_freeze/r7_packet_r1/`

Required outputs:

1. `stage1b_r1_audit_packet_manifest.json`;
2. `stage1b_r1_root_hash.json`;
3. `stage1b_r1_freeze_report.md`;
4. `r7_validation_receipt.json`;
5. `r7_handoff.json`;
6. `validate_r7_freeze.py`.

The output roster is exact; no additional files are allowed in the write scope.

## Verdict and phase boundary

- `PASS_READY_FOR_INDEPENDENT_AUDIT`: all deterministic gates pass and a replayable immutable packet/root hash is emitted.
- `REVISE`: any input mismatch, missing member, unresolved adjudication, noncanonical root-hash behavior, or validator failure.

R7 may authorize only a fresh read-only R8 audit. It must not perform R8, seal Stage 1B, authorize Stage 2, draft manuscript prose, run benchmarks, or change H1–H4 from `NOT_RUN`.
