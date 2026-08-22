# Stage 1B Remediation R1 — R9 Seal Report

Verdict: `PASS_STAGE1B_SEALED`

Deterministic seal SHA-256: `5353afaf36fb7146d58ff8e461f9c1586f2a253231bf7d1b162d77ed97a2d3b7`

## Fail-closed gate

- All `13/13` direct R9 input byte/SHA bindings match the frozen control manifest.
- R7 final replay: `29/29 PASS`, `193/193` packet members, canonical preimage `43,928` bytes, root SHA-256 `f0f2d56e42ce0f181f83182ddffe1060bf8994f50ababd4b0dbe563a942370dd`.
- R8 final replay: `60/60 PASS`; severity arithmetic is Critical `0`, Major `0`, Minor `0`, Observation `5`.
- Scholar adjudication is complete: `11` confirmed, `1` disputed and reclassified; T-002 is effectively `no_material_conflict/not_applicable`; pending `0`, unresolved `0`.
- H1–H4 and benchmark/training/evaluation remain `NOT_RUN`.

Both frozen validators were re-run in a temporary mirror so their receipt-writing final modes could execute without changing any R7 or R8 byte in the source worktree.

## Historical v0 verdict and closure accounting

The initial v0 audit verdict remains immutable `FAIL`. Remediation R1 supersedes that verdict only for Stage 1B completion. It does not rewrite the historical audit, declare that the v0 packet passed, or erase its eight findings.

| Original finding | R1 closure basis | Immutable evidence |
|---|---|---|
| `ST1B-META-001` | Scholarly and operational registries are separate; publication years are not fabricated; counts are recomputed. | `literature_corpus_r1.json`, `operational_resource_registry.json` |
| `ST1B-META-002` | Jannach–Chen is treated as editorial/essay without unsupported peer-review promotion. | `source_quality_matrix_r1.json` |
| `ST1B-META-003` | Canonical UTF-8 metadata and full-author identities are normalized and replay-validated. | `literature_corpus_r1.json`, `source_quality_matrix_r1.json` |
| `ST1B-SCOPE-001` | Prevalence wording is bounded to reviewed candidates and the non-systematic scope remains explicit. | remediated claim map and bounded synthesis |
| `ST1B-SYNTH-001` | Canonical-record, nominal-family, and dependency-adjusted-family counts are separated. | `source_family_map_r1.json`, `theme_evidence_denominators.json` |
| `ST1B-LOCATOR-001` | Core acquisition is `24/24`; all 13 queue targets are terminal; visible citations resolve through `33/33` verified non-none locators. | acquisition manifest, locator registry, claim-acquisition map, remediated claim map |
| `ST1B-ARS-001` | The synthesis invocation is bound by an immutable input/output ledger. | `synthesis_invocation_ledger.json` |
| `ST1B-RIGHTS-001` | Provider terms and the package revision are snapshotted and hashed; rights layers stay separate and restricted. | rights registry, provider-terms bytes, pinned package archive |

Closure count: `8/8`; unaccounted findings: `0`.

Exact evidence paths and SHA-256 bindings are recorded in `stage1b_r1_seal_manifest.json` and are members of the replayed R7 canonical packet.

## Deterministic seal construction

The seal preimage is the `seal_preimage` object in `stage1b_r1_seal_manifest.json`, serialized as compact UTF-8 JSON with keys sorted and no trailing newline. It binds the exact R9 input-manifest digest, R7 root and validator gate, R8 handoff digest and severity arithmetic, scholar-adjudication digest and counts, all eight closure IDs and evidence digests, and bounded Stage 2 authorization counts.

The preimage excludes timestamps, absolute or worktree paths, mutable pipeline state, and output self-hashes. Deterministic replay establishes frozen-byte integrity and declared arithmetic; it does not make semantic audit judgments or scientific truth byte-reproducible.

## Bounded Stage 2 literature handoff

- `22 authorized`: only the frozen `citation_ready_candidate` rows may be used for bounded literature drafting.
- `22 prohibited`: all frozen `planning_only` rows remain prohibited from production citation until their own prerequisites and a later explicit promotion gate are satisfied.
- `33/33` visible citation/non-`none` locator pairs are carried by immutable synthesis and locator-registry pointers.
- The handoff carries the claim map, counter-evidence overlay, source-family dependence, theme denominators, tension and scholar overlays, scholarly/operational separation, and core-source/acquisition and rights records by repository-relative path and SHA-256.
- Introduction and Related Work are priority downstream targets. R9 drafts neither section.
- Stage 2 authorization is bounded literature-drafting authorization only. It forbids fabricated citations, fabricated results, benchmark claims, and use of planning-only claims as production citations.

H1–H4, benchmark comparison, empirical superiority, cross-dataset compatibility, and training/evaluation results remain unauthorized as factual results until a common dataset/reference protocol and the experiment pipeline have actually run.

## Authority boundary

This seal is not proof of scientific correctness, novelty, superiority, external validity, or benchmark success. All five R8 observations remain visible, including the one unavailable PDF structural preflight, bounded operational pointers, fragile single-family Theme 5, targeted/non-exhaustive coverage, and the semantic reproducibility boundary.

Central pipeline state remains unchanged. The next action is central import plus replay of `validate_r9_seal.py`; only central state authority may record the Stage 1B seal and activate this bounded Stage 2 handoff.
