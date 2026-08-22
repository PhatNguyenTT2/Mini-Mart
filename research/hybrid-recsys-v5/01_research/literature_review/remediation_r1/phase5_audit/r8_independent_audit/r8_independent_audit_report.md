# Stage 1B Remediation R1 — R8 Independent Read-Only Audit

Verdict: `PASS_READY_TO_SEAL`

Severity counts: **Critical 0 · Major 0 · Minor 0 · Observation 5**.

This is a fresh audit of the frozen R7 packet in the audit role. It does not accept the R7 packet builder's semantic conclusions as authority, does not repair R7 or earlier artifacts, and does not perform R9, seal Stage 1B, authorize Stage 2, draft manuscript prose, run benchmarks, or change H1–H4.

## Fail-closed input and packet gate

- R8 audit contract: `3357` bytes, SHA-256 `b251f8e3f676a0dd3c0b3a3258e281ce312d7278c71a7343419ec054d9788b13` — exact match.
- R8 input manifest: `3695` bytes, SHA-256 `319e10f1fc26263179c3f16bbed91eebddf2c9a8f915aab9a5772a7f159e68cf` — exact match.
- All nine direct files bound by the R8 manifest match both declared byte length and SHA-256.
- The frozen R7 validator independently reran in `final` mode and returned `PASS_READY_FOR_INDEPENDENT_AUDIT`, `29/29 PASS`, with no failures.

The R8 root replay does not import or reuse R7 root-building code. It reads all 193 manifest members directly, recomputes every byte length and SHA-256, verifies lexicographic normalized repository-relative ordering and uniqueness, serializes only `[path,bytes,sha256,role]` tuples as compact UTF-8 JSON without a trailing newline, and hashes that preimage.

- Members replayed: `193/193`; mismatches: `0`.
- Roles: `162` payload, `27` control, `4` receipt.
- Canonical preimage: `43,928` bytes.
- Replayed root SHA-256: `f0f2d56e42ce0f181f83182ddffe1060bf8994f50ababd4b0dbe563a942370dd`.
- Declared root SHA-256: `f0f2d56e42ce0f181f83182ddffe1060bf8994f50ababd4b0dbe563a942370dd`.
- Root match: exact.

No timestamp field, absolute/worktree path, mutable central-state path, R7 output self-hash, or nondeterministic ordering is present in the root preimage. The embedded historical central-state bytes remain a validation-only carrier and are not a packet member.

## Upstream deterministic replays

The audit reran the relevant validators read-only:

| Gate | Result |
|---|---:|
| R4 acquisition | `22/22 PASS` |
| R5 synthesis | `29/29 PASS` |
| Original R6 Devil's Advocate | `26/26 PASS` with historical verdict `REVISE` |
| R6 remediation | `33/33 PASS` |
| Fresh R6 re-audit | `26/26 PASS` |
| R7 freeze | `29/29 PASS` |

The R6 re-audit validator was invoked in its read-only check mode because its `--final` mode writes a receipt. No frozen artifact was rewritten.

## Packet completeness and replayability

The packet retains the current and superseded R5 synthesis, original R6 critique, remediation overlay, fresh R6 re-audit, user-owned scholar overlay, relevant contracts, handoffs, validators, receipts, source artifacts, and PDF-preflight carriers. Every member has one legal role and a non-empty inclusion reason. Required audit-history artifacts are present rather than overwritten by later versions.

## Corpus, source-family, and locator audit

The independent corpus replay produced:

- `74` canonical scholarly records and `71` nominal scholarly families;
- `52` included scholarly corpus records, of which `32` are dated 2022–2026;
- `23` core scholarly records plus `1` core operational family = `24` core objects;
- `14` operational resource records in `12` operational root families;
- `75` locators: `61` scholarly-source locators and `14` operational-resource locators;
- `0` page anchors; all visible citations use non-`none` structural locators;
- `27` PDF structural preflight `PASS` results and `1` explicit `UNAVAILABLE` result.

Canonical source keys, normalized DOI identities, and normalized title/year identities have zero duplicate canonical records. All 79 lane aliases resolve to one canonical source key. Every scholarly source and operational resource belongs to exactly one declared family, all 13 dependency edges resolve, and scholarly versus operational counting remains separate. Availability, provider access, package/code license, paper license, dataset rights, and redistribution are not conflated.

The one degraded PDF preflight is for `li2023_repetition_exploration.pdf`. It remains `UNAVAILABLE` because of an xref-coverage warning and is reported as Observation R8-OBS-001; it is not relabelled PASS. No page anchor depends on it.

## Claim, counter-evidence, and citation audit

The one-shot intent manifest, original R5 map, R4 acquisition map, remediated map, and counter-evidence overlay join without drift:

- `44` unique claim rows;
- `22` citation-ready candidates and `22` planning-only rows;
- `0` planning-only promotions and `0` Stage 2 production authorizations;
- `44/44` exact upstream counter-evidence bindings;
- `51` exact upstream counter-evidence items;
- `136` source/locator pointers, all resolving;
- `114` pointers verified against original content and `22` bounded operational registry pointers not verified against original content;
- `33/33` visible citation/non-`none` locator pairs unchanged from frozen R5 and independently resolving to verified non-page locators.

The 22 bounded operational pointers are retained only as planning/audit graph context. They are not used to pass any visible citation or to authorize production use (Observation R8-OBS-002).

## Five-theme synthesis audit

Exact theme source sets, family joins, dependency edges, prose pointers, and denominator arithmetic independently replay as:

| Theme | Canonical records | Nominal families | Dependency-adjusted families | Strongest-source/family removal |
|---|---:|---:|---:|---|
| T1 | 6 | 6 | 6 | `ROBUST` |
| T2 | 8 | 8 | 8 | `ROBUST_WITH_LOCAL_WEAKENING` |
| T3 | 8 | 8 | 8 | `ROBUST_WITH_REDUCED_DIRECTNESS` |
| T4 | 9 | 9 | 8 | `ROBUST_WITH_DEPENDENCE_CAVEAT` |
| T5 | 2 operational records | 1 operational family | 1 | `FRAGILE_SINGLE_FAMILY` |

The T4 decrement is exactly the frozen `SF-R1-052 -> SF-R1-017` dependence edge. Self-family manifestation edges do not reduce already unique family counts. Removing the declared strongest source/family reproduces the recorded touched-claim sets; only Theme 5 leaves an orphaned row (`C-L5-EXT-03`). Theme 5 therefore remains an explicitly fragile operational single-family positioning (Observation R8-OBS-003).

## Hostile-reviewer and boundary audit

The hostile-reviewer boundary is preserved: exact accounting improves auditability, not evidentiary breadth. The frozen work is a targeted, non-systematic mapping of heterogeneous literature and operational resources. It cannot establish empirical robustness, global novelty, external validity, or superiority of the v5 framing (Observation R8-OBS-004).

The minimum defensible concession remains to treat the five themes as scoped design constraints and testable positioning hypotheses among reviewed candidates. The audit independently confirms the required distinctions:

- cold-item is not cold-user;
- Wide & Deep is not evidence of Apriori efficacy;
- architecture transfer is not H4 replication;
- literature rationale is not an H1–H4 result;
- official reproduction is not a harmonized benchmark;
- Complete Journey access, execution, rights, and redistribution remain separate;
- the Liu predecessor supports only bounded hybrid-method precedent, not 2009-specific results.

No manuscript Introduction or Related Work section was drafted, no benchmark was run, and no novelty, superiority, or external-validity conclusion was promoted.

## Scholar tension decisions

The original 12-pair R5 artifact remains present and unchanged with historical `scholar_confirmation: pending` rows. The explicit user-owned overlay covers every pair exactly once:

- `11` confirmed;
- `1` disputed and reclassified;
- `0` pending;
- `0` flagged unresolved.

T-002 is preserved historically as `conditional_difference / resolved_in_synthesis / pending`. Its effective overlay state is `disputed` and `no_material_conflict / not_applicable`, with `flagged_unresolved=false`. Confirmed decisions T-001 and T-003 through T-012 preserve their original assessment/resolution pairs.

## Findings

No Critical, Major, or Minor finding was identified. Five observations are recorded without repair:

1. `R8-OBS-001`: one PDF preflight is explicitly `UNAVAILABLE`, bounded by zero page anchors;
2. `R8-OBS-002`: 22 counter-evidence pointers are bounded operational registry locators, not original-content-verified evidence;
3. `R8-OBS-003`: Theme 5 is a fragile single operational family;
4. `R8-OBS-004`: the targeted corpus and 12-pair scan are not systematic or exhaustive;
5. `R8-OBS-005`: deterministic byte replay does not make semantic judgments or scientific truth byte-reproducible.

The complete machine-readable finding records are in `r8_findings.json`.

## Final deterministic gate and verdict

The R8 final validator returns `60/60 PASS`. Critical=0, Major=0, all deterministic gates pass, and no scholar decision is pending or unresolved. The R8 verdict is therefore `PASS_READY_TO_SEAL`.

This verdict is an R8 handoff to the central gate. It does not itself perform R9 or seal Stage 1B. Stage 1B remains unsealed, Stage 2 remains unauthorized, manuscript drafting remains not performed, benchmark training/evaluation remains `NOT_RUN`, and H1–H4 remain `NOT_RUN`.

The deterministic packet/root replay is exact; semantic judgments remain evidence-anchored audit conclusions rather than byte-replay guarantees (Observation R8-OBS-005).
