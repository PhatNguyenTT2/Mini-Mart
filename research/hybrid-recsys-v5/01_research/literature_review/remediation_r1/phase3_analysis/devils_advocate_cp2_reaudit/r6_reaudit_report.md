# Fresh R6 Re-audit — Devil's Advocate Checkpoint 2

## Verdict: `PASS_PENDING_SCHOLAR_CONFIRMATION`

Severity counts: **Critical 0 · Major 0 · Minor 1 · Observation 5**.

The bounded remediation closes `R6-MAJ-001` and `R6-MIN-002` under fresh replay. `R6-MIN-001` remains open only as the scholar-owned T-002 classification question. All twelve tension decisions remain pending. This verdict does not authorize R7–R9, seal Stage 1B, authorize Stage 2 citations, or represent any H1–H4 result.

## Fail-closed input gate

The re-audit started only after recursively verifying the frozen control chain. The validator follows every path/byte/SHA-256 declaration reachable from `00_control/r6_reaudit_input_manifest.json`, including the transitive R5/R6 inputs, remediation bundle, local source artifacts, and PDF-preflight carriers. The replay found no missing file, byte mismatch, or SHA-256 mismatch. Signed gates remain R5 `PASS_29_OF_29`, original R6 `PASS_26_OF_26`, and remediation `PASS_33_OF_33`.

The frozen R5, original R6, and remediation artifacts were treated as immutable. Only this re-audit directory was written.

## Critical issues

No Critical issue was identified.

## Major issues

No Major issue was identified.

## Minor issue

### R6-MIN-001 — T-002 remains scholar-owned

- **Type:** Tension-classification precision
- **Status:** `OPEN_PENDING_SCHOLAR_ADJUDICATION`
- **Problem:** Candidate-universe sensitivity and split sensitivity are complementary protocol axes. The present `conditional_difference / resolved_in_synthesis` label may inflate the resolved-tension count unless a proposition-level conditional difference is supplied.
- **Recommendation:** Preserve the original DA recommendation: `dispute`, then prefer `no_material_conflict / not_applicable` absent a proposition-level difference.
- **Authority boundary:** This re-audit does not apply that recommendation. T-002 and the other eleven pairs retain `scholar_confirmation: pending`.

## Original R6 finding reassessment

### R6-MAJ-001 — closed by fresh re-audit

The exact theme source sets were reconstructed from citation markers in the frozen R5 synthesis, rather than accepted from remediation prose:

| Theme | Canonical records | Nominal families | Dependency-adjusted families | Re-audit result |
|---|---:|---:|---:|---|
| T1 | 6 | 6 | 6 | `ROBUST` |
| T2 | 8 | 8 | 8 | `ROBUST_WITH_LOCAL_WEAKENING` |
| T3 | 8 | 8 | 8 | `ROBUST_WITH_REDUCED_DIRECTNESS` |
| T4 | 9 | 9 | 8 | `ROBUST_WITH_DEPENDENCE_CAVEAT` |
| T5 | 2 operational records | 1 operational family | 1 | `FRAGILE_SINGLE_FAMILY` |

Every record resolves independently through `source_family_map_r1.json`. The only cross-family decrement inside the five exact sets is `SF-R1-052 -> SF-R1-017`, whose frozen `counting_effect` is `not_an_additional_independent_source_family`. Self-family manifestation edges do not reduce an already unique family count. Theme 5 remains operational and is never mixed into a scholarly denominator.

All denominator pointers in `synthesis_report_r1_remediated.md` resolve into `theme_evidence_denominators.json`, and the explicit source lists match the frozen R5 marker-derived sets. The accounting defect is therefore closed.

### R6-MIN-002 — closed by fresh re-audit

The replay joins all `44/44` claim IDs to exact upstream lane-card counter-evidence. It preserves 51 upstream counter-evidence items and resolves 136 claim-level source/locator pointers. Removing the added `counter_evidence_binding` object from each remediated claim row yields the frozen R5 claim row byte-for-structure: claim intent, support scope, sources, families, locators, forbidden extrapolations, and dispositions are unchanged. The population remains 22 `citation_ready_candidate` and 22 `planning_only` rows.

### Observations — preserved

1. `R6-OBS-001`: Theme 5 remains single-family and collapses as Complete Journey-specific positioning when `SF-R1-075` is removed.
2. `R6-OBS-002`: preprint and editorial statuses remain bounded; planning-only records are not promoted.
3. `R6-OBS-003`: the Liu substitution remains limited to the inspected 2007 predecessor and hybrid-method precedent.
4. `R6-OBS-004`: Complete Journey provider access, package execution/license, dataset rights, and redistribution remain separate.
5. `R6-OBS-005`: the targeted corpus and twelve-pair scan do not establish exhaustive positioning or pairwise coverage.

## Citation marker and locator replay

The frozen and remediated syntheses contain exactly 33 paired `ref`/`anchor` markers. All `33/33` raw marker/anchor strings remain in the same sequence and are unchanged. Each remediated pair resolves to exactly one frozen R4 locator with the same source/resource key and `locator_type:locator_value`, `verified_against_original=true`, and no page anchor.

## Strongest-source removal tests

- **T1:** removing Dacrema / `SF-R1-009` touches three claim rows but leaves each with another family; the protocol boundary remains robust with narrower repository/reproduction support.
- **T2:** removing BPR / `SF-R1-047` touches three rows but leaves no row family-orphaned; the theme survives with local weakening of the ItemCF–BPR and objective comparison.
- **T3:** removing Mansouri / `SF-R1-035` touches three rows but leaves no row family-orphaned; direct repeat/explore hybrid evidence weakens.
- **T4:** removing AlphaRec / `SF-R1-052` touches four rows but leaves no row family-orphaned; cohort, representation-versus-efficacy, and adaptation boundaries survive, while the language-representation bridge weakens.
- **T5:** removing `SF-R1-075` touches three rows and leaves the Complete Journey structural claim without another family. The Complete Journey-specific theme collapses, as its declared `FRAGILE_SINGLE_FAMILY` status requires.

These are structural row/family tests, not proofs that every remaining proposition has equal evidentiary strength.

## Boundary and hostile-reviewer stress tests

The remediation preserves the fixed distinctions: cold-item is not cold-user; Wide & Deep is not Apriori efficacy; architecture transfer is not H4; literature rationale is not an empirical v5 result; and an official reproduction is not a harmonized benchmark. Complete Journey still fails any unconditional readiness claim, and Liu 2007 still cannot support 2009-specific details.

### Strongest hostile-reviewer counterargument

> The remediation repairs auditability, not evidentiary breadth. This remains a contract-oriented map of heterogeneous method descriptions from a targeted, non-systematic corpus. Exact denominators and counter-evidence joins make its limits reproducible, but do not establish empirical robustness, novelty, external validity, or superiority of the v5 framing.

### Minimum defensible concession

Retain the five themes only as scoped design constraints and testable positioning hypotheses among reviewed candidates. Keep Theme 5 explicitly single-family, preserve non-systematic coverage limits, and keep H1–H4, Stage 1B sealing, R7–R9, and Stage 2 citations blocked.

## Tension checkpoint

All twelve pair records retain their R5 assessment, resolution status, and `scholar_confirmation: pending`. Recommendations remain 11 `confirm` and one `dispute`; T-002 is the sole dispute recommendation. The re-auditor self-confirmed zero pairs and self-disputed zero pairs.

R7 remains unauthorized until the user adjudicates all twelve pairs through the explicit scholar checkpoint.

## Limitations

- The re-audit is bounded to the frozen manifest and does not perform new literature discovery.
- Semantic stress tests are evidence-anchored judgments; deterministic hashes, joins, sets, counts, and locators are replayable, but prose judgments are not claimed byte-reproducible across models.
- Claim-level locator lists join the bounded counter-evidence carrier to the unchanged claim evidence graph; they do not create new per-sentence empirical support.
- No tension-pair completeness claim is made.

## AI assistance disclosure

This re-audit was produced with AI assistance under the ARS-Codex academic-research and Devil's Advocate contracts. Deterministic validation is separated from semantic judgment, all source material remained local, and no unpublished corpus was sent to an external model or API.

## Phase boundary

H1–H4 remain `NOT_RUN`. R7–R9 were not performed, Stage 1B was not sealed, Stage 2 production citations remain `NOT_AUTHORIZED`, and no benchmark training/evaluation was run.
