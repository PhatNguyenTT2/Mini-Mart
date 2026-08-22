# Stage 1B Remediation R1 — R7 Freeze Report

Verdict: `PASS_READY_FOR_INDEPENDENT_AUDIT`

## Frozen packet

- Packet members: `193` (`162` payload, `27` control, `4` receipt).
- Canonical root SHA-256: `f0f2d56e42ce0f181f83182ddffe1060bf8994f50ababd4b0dbe563a942370dd`.
- Paths are repository-relative, use forward slashes, are unique, and are sorted lexicographically.
- Every member records its exact byte length, SHA-256, role, and inclusion reason in `stage1b_r1_audit_packet_manifest.json`.
- Superseded R5, original R6, remediation, and re-audit evidence is retained rather than rewritten or omitted.

## Canonical root-hash preimage

The preimage is the UTF-8 encoding, without a trailing newline, of a compact JSON array containing only sorted member tuples:

`[[path,bytes,sha256,role], ...]`

Serialization is `json.dumps(ensure_ascii=False, separators=(',', ':'))`. Entries are sorted lexicographically by normalized path before serialization. Timestamps, absolute/worktree paths, mutable pipeline state, and all R7 output/self-hashes are excluded. The validator independently reconstructs the tuple array from current member bytes and fails on path, ordering, byte, SHA-256, role, serialization, or root-hash divergence.

Build mode validated the central pipeline state at `research/hybrid-recsys-v5/01_research/pipeline_state_stage1b_remediation_r1.json` with `7056` bytes and SHA-256 `d304b15d8042eb549f8f475f7e1615d26a70ceb4eb8bcb8726bbaaeb4356f246`. Those exact historical bytes are embedded as base64 in the packet manifest. Final mode validates the embedded byte length, SHA-256, JSON, required state, and R7 authorization against `r7_input_manifest.json`; it never dereferences the mutable live state path. The embedded snapshot remains a validation-only carrier and is not a root-hashed packet member.

## Deterministic gates

- Recursive replay: `71` reachable JSON files, `459` declarations, `193` unique declared targets, zero mismatches.
- R5: `29/29 PASS`.
- Original R6: `26/26 PASS`, verdict `REVISE`.
- R6 remediation: `33/33 PASS`, verdict `PASS_FRESH_R6_REAUDIT_ONLY`.
- Fresh R6 re-audit: `26/26 PASS`, `Critical=0`, `Major=0`.
- Claims: `44`; citation-ready candidates: `22`; planning-only: `22`.
- Verified citation/locator pairs: `33`.
- Scholar adjudication: `12/12` decided; `11` confirmed; `T-002` disputed and effectively reclassified to `no_material_conflict/not_applicable`; `0` pending and `0` unresolved.

## Boundary

R7 authorizes only a fresh read-only R8 independent audit. R8 and R9 were not performed. Stage 1B remains unsealed, Stage 2 remains unauthorized, and H1-H4 remain `NOT_RUN`.
