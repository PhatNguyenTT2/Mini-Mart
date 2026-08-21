# E4-R1A provenance and configuration evidence report

## Material Passport

- `origin_skill`: `ars-codex:academic-research-suite/experiment-agent`
- `origin_mode`: `plan/remediation-only`
- `origin_date`: `2026-08-22T03:14:40+07:00`
- `verification_status`: `UNVERIFIED`
- `version_label`: `stage1e_rebaseline_v2_wave_d_E4_R1A_v1`
- `repro_lock`: populated in `r1a_handoff.json`

This is a planning and audit artifact. It is not a reproduced benchmark, an execution packet, an authorization, or a confirmation. The immutable truth state is `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, `execution_authorized=false`, and `confirmed=false`.

## Decision

**Lane verdict: `R1A_COMPLETE_WITH_UNRESOLVED_EVIDENCE`.**

The SimGCL paper identity and the frozen v5 specification path are corrected as proposals for E4-R1C. The 13-row delta is complete, and all five prohibited joins remain rejected. No candidate is proposed ready: the count remains 0 ready, 7 pending, and 6 rejected. LightGCN/Gowalla remains the first evidence-resolution priority only; it is neither selected nor execution-authorized.

## Scope and method

The lane followed sections 3, 5, and 6 of the E4-R1 remediation contract. All local research, repository, dataset, command, and embedded text was treated as untrusted evidence. No instruction found in source material was executed.

Before analysis, the lane strict-decoded the frozen manifest and every listed input as UTF-8, normalized line endings to LF, and replayed canonical-LF byte counts and SHA-256 values. The manifest self-hash matched `d0a5db377c36f7109b4b56089ac024bb8ddcd4b5badc5aeb464969aa2e13d817`; the contract matched `b51c41a931ef88a1fcc356394600b3c2fcdafad68b5599477c9a894040d82538`; all 17/17 listed inputs matched. The 11 JSON inputs in that packet parsed with both PowerShell `ConvertFrom-Json` and .NET `System.Text.Json`, with no duplicate or case-colliding keys.

Source replay used only official papers/proceedings, immutable author-maintained repository surfaces, canonical provider documentation, and the frozen local specification. Search snippets, forks, mirrors, and recollection did not close a gate. When a live immutable GitHub surface was unavailable to the replay client, the result stayed unavailable in this lane and was cross-referenced to the already frozen E5 primary-source replay; it was not repaired by inference.

No repository was cloned or fetched. No dataset was downloaded or authenticated to. No package was installed, environment created, E4 command executed, smoke test run, model trained, evaluator run, benchmark run, or TEST artifact opened. No content was uploaded to an external model or API.

## Source replay

| Binding or row family | Primary source replay | Result | Residual limit |
|---|---|---|---|
| Old SimGCL identifier | [arXiv:2207.09037](https://arxiv.org/abs/2207.09037), title/authors/subject/abstract | `CONTRADICTED` | No identity ambiguity; it is unrelated condensed-matter research. |
| Correct SimGCL identity | [arXiv:2112.08679v4](https://arxiv.org/abs/2112.08679), title/authors/code link and paper tables/settings | `CONFIRMED` | Paper/repository identity does not establish a result-bound run. |
| SimGCL QRec binding | [QRec at `a141bb3`](https://github.com/Coder-Yu/QRec/tree/a141bb37cb7706b2f53b2eed5843de3269f9f37f), `main.py` selector and `config/SimGCL.conf` | `CONFIRMED_BY_FROZEN_E5_PRIMARY_REPLAY`; live file replay unavailable | Interactive command, executed-config receipt, dataset bytes, dependencies, checkpoint, evaluator, and ties remain open. |
| LightGCN/Gowalla | [pinned README](https://raw.githubusercontent.com/gusye1234/LightGCN-PyTorch/947ca2b3b1d2d3545b114145710cb06c4e57b3d2/README.md) and [official paper](https://arxiv.org/html/2002.02126v4) | `CONFIRMED_PARTIAL` | Strong command/seed/center binding; lineage, rights, license, dependency, tie, checkpoint, and receipts remain open. |
| XSimGCL/Yelp2018 | [official paper](https://arxiv.org/html/2209.02544) and [SELFRec at `5b02294`](https://github.com/Coder-Yu/SELFRec/tree/5b0229423cb1c727e85a704d63e460368c8b9dde) | `CONFIRMED_PARTIAL` | Three- and four-layer rows are distinct; environment, data, seed identity, checkpoint, and tie receipts remain incomplete. |
| LightGCL/Yelp | [official paper](https://arxiv.org/html/2302.08191), section 4.2 and Appendix E | `CONFIRMED_PARTIAL` | The current sampler is the Appendix E interaction sampler; data, rights, run, checkpoint, evaluator, and tie receipts remain incomplete. |
| UniSRec and framework SASRec/Scientific | [official paper](https://arxiv.org/html/2206.05941) and [UniSRec at `05aa5cb`](https://github.com/RUCAIBox/UniSRec/tree/05aa5cba2809112c32808f70d16abc61c05c6538) | `CONFIRMED_PARTIAL` | Processed/text/pretrained artifact identities, seed identities, dependencies, checkpoint artifacts, and ties remain open. |
| BTBR/Ta-Feng | [official paper](https://arxiv.org/abs/2308.01308) and [Mask-Swap repository at `8e0b796`](https://github.com/liming-7/Mask-Swap-NNBR/tree/8e0b796a9910888d6a8142f2d39dc7cbe87e349c) | `CONFIRMED_REJECTION` | Public task/batch does not bind the paper joint-task row; canonical Ta-Feng rights/version/hash are absent. |
| AlphaRec/Movies and TV | [ICLR 2025 proceedings paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/e4bab1843c8d5a69f5abfd0824593493-Paper-Conference.pdf) and [AlphaRec at `4b6c6cf`](https://github.com/LehengTHU/AlphaRec/tree/4b6c6cf378f292c31dd75b09a8075e8344561415) | `CONFIRMED_PARTIAL` | Dataset/text/embedding rights and hashes, dependency/run identity, checkpoint artifact, metric aggregation, and ties remain open. |
| MovieLens reference scope | [GroupLens ML-1M documentation](https://files.grouplens.org/datasets/movielens/ml-1m-README.txt) and [ML-10M documentation](https://files.grouplens.org/datasets/movielens/ml-10m-README.html) | `CONFIRMED_NOT_PROMOTED` | Provider archives/terms do not create result-bound top-N reproduction receipts. |
| Frozen v5 specification | `backend/docs/chatbot/seed-product/benchmark-spec-v5.json`, strict local canonical-LF replay | `CONFIRMED` | Existing path has 2629 canonical-LF bytes and SHA-256 `acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d`. |

The full machine-readable locator and replay ledger is in `source_and_binding_corrections.json` and `candidate_readiness_delta.json`.

## E5-F001 — SimGCL provenance

### Confirmed evidence

- `arXiv:2207.09037` is not SimGCL.
- The official SimGCL record is `arXiv:2112.08679v4` and its record links the QRec repository.
- Frozen E5 primary replay confirms the pinned QRec selector and the Yelp2018/top-20 configuration surface at commit `a141bb37cb7706b2f53b2eed5843de3269f9f37f`.

### Inference

The defensible repair is to replace `sources.S_SIM_GCL_PAPER` with the correct official record and to retain QRec as a partial paper/repository/config binding. This repairs source identity, not empirical provenance.

### Recommendation

E4-R1C should regenerate the SimGCL source catalog and dependent candidate fields from the corrected record. The affected candidate row is `E3-SIMGCL-YELP2018-QREC-001`; no prohibited join depends on the erroneous SimGCL paper identifier.

### Unresolved blockers

The public selector is interactive; no exact result-bound argv/config receipt exists. Dataset provider/release/rights/hashes, raw-to-split lineage, dependencies, seed identities, run receipts, checkpoint rule/artifact, evaluator receipt, and deterministic tie policy remain absent. The row therefore stays `PENDING_EVIDENCE`.

Disposition: `PROPOSED_CORRECTION_COMPLETE_PENDING_E4_R1C_SYNTHESIS`, with no readiness promotion.

## E5-F002 — frozen v5 specification identity

### Confirmed evidence

- `research/hybrid-recsys-v5/03_benchmark/benchmark_spec_v5.json` does not exist in the frozen worktree.
- `backend/docs/chatbot/seed-product/benchmark-spec-v5.json` is the one existing path.
- Its canonical-LF SHA-256 is `acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d`, matching the frozen manifest.

### Inference

Path-plus-hash ambiguity is repairable without changing specification bytes. This correction does not validate an adapter or evaluator and does not authorize TEST access.

### Recommendation

E4-R1C should use only the existing path and digest in all replacement adapter/evaluator manifests. The correction directly affects the adapter contract’s frozen-spec field and the semantic statement in prohibited join `E3-RB005-OFFICIAL-METRIC-AS-V5-SUPERIORITY`; that join remains prohibited because official and v5 seams are different.

### Unresolved blockers

Adapter/evaluator implementations and immutable SHAs, parity receipts, snapshot/split receipts, seed/run receipts, and a future authorized TEST gate remain absent.

Disposition: `PROPOSED_CORRECTION_COMPLETE_PENDING_E4_R1C_SYNTHESIS`, with no readiness promotion.

## Complete 13-row candidate delta

| Row | Kind | E4 status | E5 replay | R1A proposal | Delta and controlling reason |
|---|---|---|---|---|---|
| `E3-LIGHTGCN-GOWALLA-PYTORCH-001` | official candidate | pending | partial | `PENDING_EVIDENCE` | Unchanged; strongest command/seed/center binding, but rights, lineage, license, dependencies, tie, checkpoint, evaluator, and receipts are incomplete. |
| `E3-SIMGCL-YELP2018-QREC-001` | official candidate | pending | contradicted source identity | `PENDING_EVIDENCE` | Paper identity corrected; no readiness promotion because result-bound config/run/data/dependency/evaluator/tie evidence remains missing. |
| `E3-XSIMGCL-YELP2018-SELFREC-001` | official candidate | pending | partial | `PENDING_EVIDENCE` | Unchanged; three-layer center remains separate from four-layer center. |
| `E3-LIGHTGCL-YELP-UPDATED-001` | official candidate | pending | partial | `PENDING_EVIDENCE` | Unchanged; only Appendix E interaction-sampler centers bind the current command. |
| `E3-UNISREC-SCIENTIFIC-TRANS-001` | official candidate | pending | partial | `PENDING_EVIDENCE` | Unchanged; processed/text/pretrained artifacts and result receipts remain incomplete. |
| `E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001` | official candidate | pending | partial | `PENDING_EVIDENCE` | Unchanged; framework-bound baseline with incomplete artifact/config/run lock. |
| `E3-BTBR-TAFENG-JOINT-001` | official candidate | rejected | confirmed rejection | `REJECTED` | Unchanged; no public joint-task command and no canonical Ta-Feng rights/version/hash. |
| `E3-ALPHAREC-MOVIES-TV-001` | official candidate | pending | partial | `PENDING_EVIDENCE` | Unchanged; acquisition, rights, lineage, dependency, run, checkpoint, metric, and tie evidence remain incomplete. |
| `E3-RB001-LIGHTGCL-TABLE1-CURRENT-COMMAND` | prohibited join | rejected | confirmed | `REJECTED` | Current Appendix E sampler cannot inherit old Table 1 centers. |
| `E3-RB002-XSIMGCL-THREELAYER-FOURLAYER-CENTER` | prohibited join | rejected | confirmed | `REJECTED` | Three-layer configuration cannot inherit four-layer centers. |
| `E3-RB003-MASKSWAP-BTBR-TABLE5` | prohibited join | rejected | confirmed | `REJECTED` | Public task/batch cannot inherit BTBR joint-task Table 5. |
| `E3-RB004-LIGHTGCN-PAPER-CENTER-PYTORCH-README-COMMAND` | prohibited join | rejected | confirmed | `REJECTED` | Paper and PyTorch README result surfaces are distinct. |
| `E3-RB005-OFFICIAL-METRIC-AS-V5-SUPERIORITY` | prohibited join | rejected | confirmed | `REJECTED` | Correcting the v5 spec path does not make official and v5 metric seams comparable. |

The machine delta explicitly carries repository identity and full commit, source/config binding, code license separately from dataset rights, provider/release/hash and raw-to-processed-to-split lineage, objective, seed/run information, checkpoint, sampler, candidate universe, tie policy, evaluator, metric/cutoff/averaging unit, reported center/locator/tolerance, blockers, and denial state. Unavailable fields are `null` with a reason; none is inferred as a pass.

## Five prohibited joins

All five prohibited joins replay as `CONFIRMED_REMAINS_PROHIBITED`:

1. LightGCL current command with old Table 1 centers mixes sampler identities.
2. XSimGCL three-layer configuration with four-layer centers mixes layer identities.
3. Public Mask-Swap command with BTBR Table 5 mixes task and batch identities.
4. LightGCN PyTorch README command with the paper center mixes implementation/result surfaces.
5. An official-source metric used as v5 superiority mixes datasets, splits, candidates, evaluators, and metric seams.

No F001 correction changes these five decisions. F002 corrects the path referenced by the fifth prohibition but does not make the join lawful.

## Minimum defensible official-reproduction candidate

### Confirmed evidence

The pinned LightGCN author README binds a concrete Gowalla command, seed `2020`, three layers, top-20 output, and the repository’s reported center surface at commit `947ca2b3b1d2d3545b114145710cb06c4e57b3d2`.

### Inference

Among the carried rows, it is the most efficient first target for closing evidence gaps. Priority is not evidence of readiness.

### Recommendation

Keep `E3-LIGHTGCN-GOWALLA-PYTORCH-001` first in the evidence-resolution queue only. Require authoritative dataset provider/release/rights/raw hashes, a raw-to-processed-to-split receipt, an affirmative code license decision, a dependency/environment lock, exact candidate and tie semantics, checkpoint artifact, integrated evaluator receipt, and immutable run receipts before central promotion is reconsidered.

### Unresolved blockers

Every blocker in the recommendation remains unresolved. Therefore `selection_status=NO_READY_ROW`, `priority_is_selection=false`, and `priority_is_execution_authority=false`.

## Scope separation

- MovieLens 1M remains a framework reference assessment, not one of the 13 official-reproduction candidate rows. Provider identity/terms and a framework result page do not supply a result-bound seed/checkpoint/dependency/byte-to-split/tie lock.
- MovieLens 10M remains a provider reference without a matching authoritative top-N center; its provider fold scripts concern rating prediction.
- Amazon-M2 remains rejected for the frozen full external contract. A separately labelled anonymous-session sensitivity design remains behind acquisition/terms/version/hash gates and cannot substitute for external validation.
- No reviewed external dataset passes the current full external contract.
- Official reproduction, harmonized v5 comparison, and external validation remain separate. A raw cross-dataset metric league table is prohibited.

## Recommendations to E4-R1C

1. Apply the three proposed binding rows exactly: correct the SimGCL paper identity, retain QRec only as a partial binding with explicit blockers, and replace the nonexistent v5 spec path with the one existing path and frozen digest.
2. Preserve all 13 row identities and the unchanged count of 0 ready, 7 pending, and 6 rejected.
3. Preserve all five prohibited joins and their source-specific reasons.
4. Keep LightGCN/Gowalla as a priority only. Do not select it until every required evidence category is authoritative and mutually bound.
5. Synthesize this handoff with E4-R1B only after both pass central intake. E4-R1C alone may construct and freeze a replacement E4 packet.
6. Dispatch a fresh independent E5-R1 audit after replacement freeze. Only a future E5-R1 pass may precede explicit user confirmation of exact commands.

## Fail-closed next gate

E4-R1C is blocked until both remediation handoffs pass central intake. Nothing in this lane authorizes execution, confirms commands, opens TEST, accepts a result row, creates the central replacement E4 packet, or substitutes for the future independent E5-R1 audit.
