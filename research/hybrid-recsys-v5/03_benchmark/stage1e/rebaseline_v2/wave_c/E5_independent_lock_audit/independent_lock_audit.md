# E5 independent lock audit

## Decision

**E5 verdict: `REVISE_E4_ADDITIONAL_FINDINGS`.**

E4's fail-closed conclusion is independently confirmed: the frozen bundle has zero `READY_FOR_E5_AUDIT` rows, the command packet is `DRAFT_BLOCKED_NOT_EXECUTABLE`, and no execution can be authorized. Four additional E4 defects require regeneration before a replacement E5 audit.

Authorization is denied with `authorized=false`, `confirmed=false`, `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, and `ACCEPTED_RESULT_ROWS=0`. A remediated, newly frozen E4 packet, a new independent E5 audit, and explicit user confirmation of a future exact-command packet are mandatory.

## Scope and method

This was a fresh, audit-only ARS experiment-agent validation under `ars-codex:academic-research-suite` 0.1.26 using `gpt-5.6-sol` at `xhigh`. E1-E4 claims were treated as untrusted. Central receipts were used only as local structural inputs. No candidate repository was cloned or fetched; no dataset was downloaded; no authenticated access, package installation, environment creation, source/data/model modification, command execution, training, evaluation, smoke test, benchmark, or TEST access occurred.

Local text was decoded as strict UTF-8, CRLF was normalized to LF, and SHA-256 was computed over the normalized UTF-8 bytes. Primary-source replay used author-maintained immutable repository files/commits, official papers and supplements, canonical provider pages/checksums, and framework-owned result pages. Unavailable or incomplete evidence stayed open.

## Frozen entry gate

| Check | Required | Matched | Result |
|---|---:|---:|---|
| E5 manifest self-hash | 1 | 1 | PASS |
| E5 direct input rows | 10 | 10 | PASS |
| E4 parent-manifest transitive rows | 28 | 28 | PASS |
| Required artifact checks | 38 | 38 | PASS |

- E5 contract canonical-LF SHA-256: `59394ab80d3d78c491d20346bf44cfab5ab7d75e8acbab45ae3ecaf50c62dff5`
- E5 manifest canonical-LF SHA-256: `f06e3b4e60afd53923fb343b74cedd4e1a49c75d2b4e0151197adc9c7945446f`
- E4 central receipt canonical-LF SHA-256: `b7a7ed680f2aafe1e42fb246225c3a507a03c514f122ebeadd809ce88f5a41f7`
- E4 parent manifest canonical-LF SHA-256: `e320eff700eae6e12d8e4059e25656b88dfd1ac1904e42290fce32944ddf41d2`

No entry-gate mismatch occurred, so E5 outputs were permitted.

## Criterion matrix

| Criterion | Coverage | Result | Audit conclusion |
|---|---:|---|---|
| Candidate rows | 13/13 | PARTIAL | Seven pending and six rejected remain non-ready; the SimGCL provenance row is contradicted. |
| Prohibited joins | 5/5 | CONFIRMED | All five joins remain prohibited. |
| Wave A blocker dispositions | 26/26 | CONFIRMED | `1 RESOLVED / 18 CARRIED / 7 REJECTED_WITH_ROW`; the sole resolution is supported only at design scope. |
| E4 command records | 10/10 | CONTRADICTED | Blocked/null semantics are present, but several declared controls and failure semantics are not implemented. |
| Required decision points | 8/8 | PARTIAL | Fail-closed decisions stand; four additional packet defects require E4 regeneration. |
| Reported tolerance arithmetic | 26/26 metrics | CONFIRMED | Every tolerance equals `max(0.005, 0.05 * abs(center))`. |
| Sequence lock | 4/4 stages | CONFIRMED | Official acceptance precedes method-faithful adaptation, harmonized v5 comparison, then separate external validation. |
| Cross-dataset raw metric guard | 1/1 | CONFIRMED | Raw metrics are not authorized as one league table. |

## Candidate replay: 13/13

| Row | E4 status | E5 replay | Independent result |
|---|---|---|---|
| `E3-LIGHTGCN-GOWALLA-PYTORCH-001` | PENDING_EVIDENCE | PARTIAL | Pinned README confirms command, seed, layer count, and repository centers `Recall@20=.1824`, `NDCG@20=.1547`, `Precision@20=.05589`; lineage, rights, license, dependency, tie, and checkpoint gates remain open. |
| `E3-SIMGCL-YELP2018-QREC-001` | PENDING_EVIDENCE | CONTRADICTED | QRec's pinned selector/config and the correct SimGCL paper support the method and `.0721/.0601` center, but E4's `S_SIM_GCL_PAPER` URL is an unrelated condensed-matter paper. |
| `E3-XSIMGCL-YELP2018-SELFREC-001` | PENDING_EVIDENCE | PARTIAL | Pinned SELFRec and the paper distinguish the three-layer `.0723/.0604` row from the four-layer `.0733/.0606` row; unresolved gates remain. |
| `E3-LIGHTGCL-YELP-UPDATED-001` | PENDING_EVIDENCE | PARTIAL | Appendix E confirms the interaction-sampler update and `.0985/.0842/.1553/.1051`; data, rights, lock, tie, checkpoint, and run identity remain incomplete. |
| `E3-UNISREC-SCIENTIFIC-TRANS-001` | PENDING_EVIDENCE | PARTIAL | Official paper and pinned README confirm Scientific commands and `.1235/.0634/.2473/.0904`; bundle identity and run receipts remain incomplete. |
| `E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001` | PENDING_EVIDENCE | PARTIAL | UniSRec framework source confirms the SASRec command and `.1080/.0553/.2042/.0760`; it remains a framework-bound, non-ready row. |
| `E3-BTBR-TAFENG-JOINT-001` | REJECTED | CONFIRMED | Paper Table 5 is joint-task batch 128 while the public README command is item-selection batch 64; no canonical Ta-Feng provider/rights/hash lock exists. |
| `E3-ALPHAREC-MOVIES-TV-001` | PENDING_EVIDENCE | PARTIAL | Official ICLR paper and pinned README confirm `.1221/.1144/.5587` and the Movies & TV command; anonymous acquisition, lineage, rights, and run identity remain open. |
| `E3-RB001-LIGHTGCL-TABLE1-CURRENT-COMMAND` | REJECTED | CONFIRMED | The current command uses Appendix E's changed sampler and cannot bind Table 1 centers. |
| `E3-RB002-XSIMGCL-THREELAYER-FOURLAYER-CENTER` | REJECTED | CONFIRMED | Three-layer and four-layer centers are distinct source rows. |
| `E3-RB003-MASKSWAP-BTBR-TABLE5` | REJECTED | CONFIRMED | Public Mask-Swap command semantics do not bind the BTBR joint-task table. |
| `E3-RB004-LIGHTGCN-PAPER-CENTER-PYTORCH-README-COMMAND` | REJECTED | CONFIRMED | Paper Gowalla `.1830/.1554` and PyTorch README `.1824/.1547` belong to different locked result surfaces. |
| `E3-RB005-OFFICIAL-METRIC-AS-V5-SUPERIORITY` | REJECTED | CONFIRMED | Source metrics cannot establish v5 superiority without the harmonized v5 seam. |

## Blocker-disposition replay: 26/26

All carried blockers remain open, all rejected-with-row blockers retain an explicit rejection target, and the sole resolved blocker was independently checked against the bounded collector interface.

| Blocker | E4 disposition | E5 result | Independent basis |
|---|---|---|---|
| `E1-B01` | CARRIED | CONFIRMED | Processed-pack origins and rights remain incomplete. |
| `E1-B02` | CARRIED | CONFIRMED | Split/candidate/sampler/metric/checkpoint locks remain incomplete. |
| `E1-B03` | CARRIED | CONFIRMED | Pinned RecBole MIT file and README academic-purpose wording coexist. |
| `E1-B04` | CARRIED | CONFIRMED | Named pinned candidate commits expose no affirmative license file. |
| `E1-B05` | CARRIED | CONFIRMED | AlphaRec's badge does not substitute for a grant file at the pinned commit. |
| `E1-B06` | REJECTED_WITH_ROW | CONFIRMED | The Mask-Swap/BTBR join remains rejected. |
| `E1-B07` | CARRIED | CONFIRMED | No SELFRec dependency lock was produced. |
| `E1-B08` | CARRIED | CONFIRMED | Local CLI/training paths remain dirty versus HEAD. |
| `E1-B09` | RESOLVED | CONFIRMED | Adapter contract lines 21-44 define a bounded, method-preserving collector envelope; implementation and parity are still blocked. |
| `E1-B10` | CARRIED | CONFIRMED | No E4 empirical result is verified or accepted. |
| `E2-B01` | CARRIED | CONFIRMED | LightGCN/LightGCL/SELFRec processed lineage and rights remain incomplete. |
| `E2-B02` | CARRIED | CONFIRMED | UniSRec/AlphaRec bundle release, hashes, lineage, and text rights remain incomplete. |
| `E2-B03` | CARRIED | CONFIRMED | Amazon Reviews 2018 identity, digest, split, and rights remain incomplete. |
| `E2-B04` | REJECTED_WITH_ROW | CONFIRMED | Amazon-M2 is anonymous-session data and fails the persistent-user/order/basket contract. |
| `E2-B05` | CARRIED | CONFIRMED | Complete Journey's provider page exists, but exact bytes/version/hash/terms remain unlocked. |
| `E2-B06` | CARRIED | CONFIRMED | No replayed canonical Instacart acquisition surface closed the gate. |
| `E2-B07` | CARRIED | CONFIRMED | Tenrec terms/files/hash/task configuration remains unlocked. |
| `E2-B08` | REJECTED_WITH_ROW | CONFIRMED | No canonical Ta-Feng provider/rights/version lock was found. |
| `E2-B09` | REJECTED_WITH_ROW | CONFIRMED | ViFoodRec is ratings/content data with median-imputed gaps and no event-time/basket seam. |
| `E3-B01` | CARRIED | CONFIRMED | No candidate is E5-validated. |
| `E3-B02` | CARRIED | CONFIRMED | No pending row has an immutable raw-to-split receipt. |
| `E3-B03` | CARRIED | CONFIRMED | Seed/checkpoint/run/dispersion evidence remains incomplete. |
| `E3-B04` | REJECTED_WITH_ROW | CONFIRMED | LightGCL cross-sampler binding remains prohibited. |
| `E3-B05` | REJECTED_WITH_ROW | CONFIRMED | BTBR batch/task mismatch remains prohibited. |
| `E3-B06` | REJECTED_WITH_ROW | CONFIRMED | Framework commands and author centers remain non-interchangeable. |
| `E3-B07` | CARRIED | CONFIRMED | Deterministic tie handling remains unstated for most pending rows. |

## Command audit: 10/10

All records have `user_confirmation_required=true`, `confirmed=false`, `execution_authorized=false`, and `NO_AUTO_RETRY`; no credential literal was found. Network flags, write flags, and timeouts are explicit for executable strings, while the two unavailable phases use null command/shell/cwd/timeout semantics. These correct fail-closed fields do not make the sequence executable.

| Command | E5 result | Audit conclusion |
|---|---|---|
| `E4-LGCN-000-PREFLIGHT` | CONTRADICTED | It reports GPU inventory but does not assert RTX 3060/6144 MiB, index 0, 5120 MiB free, wrapper existence/hash/enforcement, marker contents, reparse safety, or nested collisions despite claiming those mismatches stop. |
| `E4-LGCN-010-CLONE` | CONTRADICTED | Its working directory is not created by any packet command; redirect/unexpected-remote and receipt semantics are not implemented by the command string. |
| `E4-LGCN-020-CHECKOUT` | PARTIAL | Exact detached SHA is present, but submodule ambiguity and out-of-namespace mutation controls are not enforced in this command. |
| `E4-LGCN-030-VERIFY-SOURCE` | CONTRADICTED | HEAD is asserted, but dirty and submodule output is printed rather than rejected. |
| `E4-LGCN-040-CREATE-ENV` | CONFIRMED | Null/blocked semantics correctly refuse to invent a runtime. |
| `E4-LGCN-050-INSTALL` | PARTIAL | `--no-index --require-hashes` is sound, but the runtime, lock, and wheelhouse do not exist and are not created by the packet. |
| `E4-LGCN-060-PREPROCESS-GATE` | CONTRADICTED | It checks property presence and a label only; it does not validate types, hashes, source binding, duplicate/case-colliding keys, or semantics, and improperly assigns receipt creation/verification to E5. |
| `E4-LGCN-070-TRAIN-AND-INTEGRATED-EVALUATE` | PARTIAL | GPU 0, 5120 MiB, CPU 4, RAM 12288 MiB, 10-second telemetry, and 21600-second timeout are passed, but the wrapper is absent/unhashed and the command does not emit the declared receipt. |
| `E4-LGCN-080-STANDALONE-EVALUATE` | CONFIRMED | Null semantics correctly preserve the integrated-evaluator source binding. |
| `E4-LGCN-090-FINALIZE-RECEIPTS` | CONTRADICTED | It lists/hashes files but does not enforce required phase receipts, schema/parse validity, duplicate/case-colliding names, or write the expected manifest. |

The working directories, revision, network/write behavior, receipt fields, timeouts, GPU controls, namespace controls, credentials, retry policy, confirmation flags, authorization flags, and blocked/null semantics were inspected for every row.

## Decision-point replay

1. **MovieLens 1M — CONFIRMED/PARTIAL.** GroupLens checksum `c4d9eecfca2ab87c1945afe126590906` and terms are confirmed. The pinned RecBole-GNN page confirms rating >=3 filtering, 8:1:1, full sort, common settings, and framework centers, but no result-bound seed/run, checkpoint, dependency lock, byte-to-split receipt, or tie policy. It is not an exact reproduction row.
2. **MovieLens 10M — CONFIRMED.** GroupLens checksum `ce571fd55effeba0271552578f2648bd` is confirmed. Provider five-fold scripts are rating-prediction utilities, not a framework-owned top-N center. No promotion is justified.
3. **Amazon-M2 — CONFIRMED/PARTIAL.** The paper confirms anonymous 30-minute sessions and a two-week/one-week temporal division. It does not provide persistent customer/order/basket identity. The canonical acquisition route requires authentication and exposes no replayed provider digest, so the full contract remains rejected; only a separately labelled future acquisition-gated session study could be considered.
4. **Other external datasets — CONFIRMED/PARTIAL.** Complete Journey has relevant household transactions but lacks a locked exact acquisition/version/hash/terms seam; Instacart and Tenrec gates remain open; Ta-Feng and ViFoodRec remain rejected; ViEcomRec and ViHoRec do not satisfy the frozen full external-validation seam.
5. **LightGCN/Gowalla — CONFIRMED/PARTIAL.** The pinned README center/command is real, and the paper's `.1830/.1554` center is a different result surface. Dataset lineage/rights/license, dependency, sampler/tie/checkpoint, and receipt gaps prevent readiness.
6. **Metric and tolerance seam — CONFIRMED.** All 26 frozen tolerances recompute exactly. Source-specific split, candidate, sampler, tie, and checkpoint gaps are not filled by inference.
7. **Sequence lock — CONFIRMED.** `OFFICIAL_REPRODUCTION_ACCEPTANCE -> METHOD_FAITHFUL_V5_ADAPTATION -> HARMONIZED_V5_COMPARISON -> SEPARATE_EXTERNAL_VALIDATION` is preserved.
8. **Cross-dataset comparison guard — CONFIRMED.** E4 prohibits raw Recall/NDCG/HR/MRR/AUC values from being presented as one cross-dataset league table.

## Adaptation and reporting audit

The method-faithful adapter boundary is substantively sound: it permits identifier translation, source-native serialization, pinned invocation, score exposure, and bounded per-user collection while prohibiting changes to model mathematics, sampler, optimizer, stopping rule, or scoring equation. The shared evaluator contract fixes the 5200-product catalog, seen-item masking, raw-ID tie break, seed schedule, validation checkpoint rule, metric formulas, and hierarchical seed-plus-user bootstrap. These are design contracts only; no implementation, parity proof, exact hashed argv, clean local commit, or empirical receipt exists.

The adaptation binding is not internally complete because the benchmark-spec hash is attached to a nonexistent path (`E5-F002`). Local read-only Git inspection also confirms the inherited CLI/training surfaces remain dirty, so no local revision can be treated as immutable.

The reporting contract correctly separates official reproduction, harmonized v5 evaluation, and external validation into distinct tables and forbids subtraction, ratios, ranks, color scales, or narrative that would make incompatible raw metrics appear comparable. No raw cross-dataset metric league table was created in E5.

## Additional findings

| ID | Severity | Summary | Required disposition |
|---|---|---|---|
| `E5-F001` | MAJOR | E4's SimGCL paper URL resolves to unrelated physics research; the correct primary record is arXiv:2112.08679. | Regenerate E4 source catalog and all affected row/source bindings. |
| `E5-F002` | MAJOR | The adapter contract binds hash `acef...166d` to a nonexistent benchmark-spec path; the frozen manifest binds that hash to `backend/docs/chatbot/seed-product/benchmark-spec-v5.json`. | Regenerate E4 with a single exact path/hash binding. |
| `E5-F003` | MAJOR | Several command failure/control claims are stronger than the exact commands implement. | Replace the packet in a new frozen E4 revision with mechanically enforced checks and receipts. |
| `E5-F004` | MAJOR | E4 assigns runtime/data receipt/argv/packet remediation to E5, conflicting with the audit-only E5 boundary and the required new-E4/new-E5 cycle. | Move remediation and packet construction to a future E4 packet; keep E5 audit-only. |

Full structured findings and locators are in `audit_findings.json`.

## Final truth state and remediation order

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- `confirmed=false`
- Candidate counts: 13 total, 0 ready, 7 pending, 6 rejected
- Blocker counts: 26 total, 1 resolved, 18 carried, 7 rejected-with-row
- Command counts: 10 total, all blocked/unconfirmed/unauthorized

Remediation order:

1. Correct the SimGCL source binding and the v5 specification path/hash binding.
2. Resolve candidate dataset/code rights, raw-to-processed identity, dependency, evaluator, tie, checkpoint, and run-receipt gates without inventing evidence.
3. Build a new self-consistent, mechanically enforced exact-command packet under E4 ownership.
4. Freeze and validate a new E4 packet.
5. Run a new independent E5 audit.
6. Only after a future E5 pass, request explicit user confirmation of that replacement exact-command packet.

No `PASS_EXECUTION_AUTHORIZED` outcome is possible from this frozen packet.
