# Stage 1E — R2-G1 central merge, verification, deduplication and synthesis

Verdict: `NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`  
Model: `gpt-5.6-sol`  
Reasoning: `high`  
Execution authority: `DENIED`

## Outcome

No candidate may advance to materialization. The exact A1 × A2 × A3 intersection contains zero fully sufficient rows:

- R2-A1: 0 sufficient, 6 incomplete, 1 dispositive reject;
- R2-A2: 0 sufficient, 7 incomplete;
- R2-A3: 0 sufficient, 7 incomplete;
- final selection cardinality: 0.

This is a fail-closed negative decision, not a successful reproduction and not permission to acquire materials. All benchmark values remain `INVALID_FOR_PAPER`.

## Central verification

The three provenance commits were imported as three separate central commits. Central replay verified all 12 files, 11/11 JSON documents, all handoff hashes and all nine non-handoff hashes. Candidate order is identical across lanes. All Material Passports remain `UNVERIFIED`; all three lanes declare no experiment; `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0` and execution remains unauthorized.

Central validation also found three schema nonconformances:

1. `R2-CF-A1-001`: A1 abbreviates the sufficient-status count key.
2. `R2-CF-A2-001`: all seven A2 register rows use `lane_evidence_status` and omit seven common-row fields required by the frozen contract.
3. `R2-CF-A3-001`: the A3 handoff uses an output-root label instead of lane ID `R2-A3`.

These defects do not create evidence. They prohibit any positive selection. The explicit incomplete/reject states remain sufficient to close this gate only as `NO_SELECTION`.

## Candidate decisions

- LightGCN/Gowalla remains the first evidence-resolution priority, not a selected baseline. Its repository documents a runnable 3-layer command and a seed-2020 result center, but no affirmative pinned code license, lawful exact Gowalla lineage, checkpoint hash or immutable run/evaluator/tie receipt is closed.
- SimGCL/Yelp2018 remains pending: code license/noninteractive command, historical provider rights and exact split lineage, and source evaluator/run receipts remain unresolved.
- XSimGCL/Yelp2018 is rejected in its current row. The pinned README center uses layer 3, while the pinned YAML sets `n_layer: 2`. Cross-joining them is prohibited.
- LightGCL/Yelp remains pending because the corrected sampler revision, exact provider/split lineage and run/evaluator receipts are not jointly closed.
- UniSRec/Scientific has an affirmative MIT license for repository code only. Dataset rights, pretrained/processed assets, exact RecBole/evaluator identity and run/checkpoint receipts remain unresolved.
- SASRec/Scientific remains pending because the external framework/model revision, independent preprocessing lineage and evaluator/checkpoint receipts are not bound.
- AlphaRec/Movies & TV remains pending because code/data/text/embedding rights, preprocessing lineage and run/evaluator receipts are unresolved.

## Deduplication

The three main registers contain 77 authoritative-source mentions but only 62 exact unique URLs. Fifteen repeated mentions were deduplicated for evidence accounting. Repetition is not independent corroboration and does not increase readiness.

## Benchmark consequence

R2-M0 and every materialization/execution stage remain blocked. No clone, source archive, dataset acquisition, authentication, terms acceptance, installation, environment/container creation, preprocessing, training, evaluation, TEST access or benchmark execution occurred.

The paper may not cite any current benchmark number as valid comparative evidence. The earlier authorization to draft bounded Introduction and Related Work claims is unaffected, because it is independent of Stage 1E benchmark readiness.

## Recommended next route

Do not start R2-M0. Start a change-controlled evidence-remediation round:

1. repair the A1/A2/A3 schema carriers without changing their scientific truth state;
2. keep LightGCN as the first target and seek an affirmative code-license basis plus an exact lawful processed-split lineage and source-owned checkpoint/evaluator receipt;
3. if those cannot be obtained from public authoritative sources, ask the user whether to contact maintainers or introduce a new, separately labeled reproducible framework/dataset row;
4. never relabel a framework reproduction on MovieLens or another dataset as an official reproduction of a paper-specific center.

Any new candidate or material scope requires a new frozen contract and a fresh G1 intersection.
