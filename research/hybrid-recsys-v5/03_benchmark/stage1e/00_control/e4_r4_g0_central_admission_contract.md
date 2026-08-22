# Stage 1E — E4 R4-G0 central strict-admission contract

Date: 2026-08-22  
Context: current central  
Model: Sol Max Standard (gpt-5.6-sol, max, standard)  
Execution authority: DENIED

## Entry gate

R4-G0 may start only after R4-D1A, R4-D1B and R4-D1C each emit exactly the five
registered files and the central scout validator passes. The central context
then creates a canonical-LF hash manifest over all fifteen worker outputs before
performing any synthesis.

Worker admission is a proposal, not a central fact. R4-G0 must not change a
failed worker dimension to PASS, substitute a source, complete an environment
by guessing versions, or join evidence across identities.

## Mechanical validation and exact deduplication

The join key is proposal_id. The provenance identity is the exact ordered tuple
repository_url, full_revision, dataset_provider, dataset_release_id,
protocol_id, config_id, evaluator_id, numeric_target_id.

R4-G0 rejects malformed IDs, duplicate/case-colliding JSON keys, missing files,
hash drift, unregistered status values, non-direct URLs, unresolved mandatory
fields and inconsistent counts. Exact duplicate provenance tuples collapse to
one row. A conflict in any tuple component excludes all conflicting
representations until new evidence is explicitly authorized; central review
does not choose the convenient representation.

## Independent central replay

For every worker-admitted proposal, the central context independently opens
every decision-bearing URL. It records one of:

- CENTRAL_REPLAY_PRIMARY_PASS;
- CENTRAL_REPLAY_AUTHORITATIVE_PASS;
- CENTRAL_REPLAY_INACCESSIBLE;
- CENTRAL_REPLAY_IDENTITY_CONFLICT;
- CENTRAL_REPLAY_SCOPE_MISMATCH;
- CENTRAL_REPLAY_INDIRECT_ONLY.

Every URL must receive one of the two PASS states for the proposal to survive.
Central replay verifies the cited content, authority, immutable binding and
claim scope; merely reaching a page is not a pass. Cached worker prose and
search snippets cannot satisfy replay.

## Freeze rule

A proposal is centrally admissible only when:

1. all twelve worker dimensions are PASS_PRIMARY_REPLAYED;
2. the central replay of every decision-bearing URL passes;
3. all eight identity components remain equal across the candidate, evidence
   and numeric target;
4. unresolved mandatory fields and dispositive conflicts are both empty;
5. there is no exact duplicate or cross-identity evidence join; and
6. no operation forbidden before R4-M0 occurred.

R4-G0 freezes zero to three complete bundles. If more than three survive, the
preregistered tie order is: legal and byte-lineage clarity; exact environment
lock; same-surface protocol/config/evaluator/result binding; no-TEST evidence;
v5 adapter boundedness; then maintenance recency. Ranking is applied only among
already-complete bundles and cannot rescue a failed dimension.

If zero survive, the mandatory verdict is
NO_ADMISSIBLE_BUNDLE_STOP_FAIL_CLOSED and R4-A1–A3 are not launched. If one to
three survive, the verdict is FREEZE_COMPLETE_BUNDLES_FOR_AUDIT. This verdict
authorizes only independent evidence audits, not materialization.

## Exact outputs

R4-G0 writes exactly six files under
research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_x/E4_R4G0_strict_admission_freeze:

1. r4_g0_admission_decision.json
2. frozen_complete_bundles.json
3. central_source_replay_log.json
4. deduplication_log.json
5. r4_g0_report.md
6. r4_g0_handoff.json

All JSON is strict UTF-8. The handoff carries output hashes, cardinalities,
model profile, operation receipts, persistent truth state and the conditional
next gate.

## Persistent boundary

R4-G0 preserves RESULT_STATUS=NOT_RUN, TEST_SET_OPENED=NO,
ACCEPTED_RESULT_ROWS=0, execution_authorized=false and project benchmark
numbers=INVALID_FOR_PAPER. Repository/dataset acquisition, environment
creation, preprocessing, training, evaluation and TEST access remain blocked
until a later positive R4-G1 decision and explicit R4-M0 user approval.
