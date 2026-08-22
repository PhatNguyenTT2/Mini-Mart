# Stage 1E — E4 R5 targeted source-only evidence materialization

Date: 2026-08-23  
Stage family: R5  
Entry verdict: NO_ADMISSIBLE_BUNDLE_STOP_FAIL_CLOSED  
User scope decision: AUTHORIZE_TARGETED_SOURCE_ONLY_EVIDENCE_MATERIALIZATION_REDESIGN  
Execution authority: SOURCE_ONLY_CONDITIONAL_AFTER_R5_S0

## 1. Decision and scientific boundary

R4 showed that requiring every environment, evaluator, no-TEST and adapter
fact to be visible on public web pages before source acquisition is too early
for the two strongest non-dispositive candidates. R5 changes when those facts
are collected; it does not weaken the final benchmark gate.

R5 may materialize only the named repositories at the exact immutable commits
in `e4_r5_candidate_lock.json`. The materialized source remains vendor evidence,
not project implementation and not an admitted benchmark. The R4 numeric values
remain provisional targets only. They are invalid for the paper unless a later
official-surface reproduction and harmonized-v5 run pass every applicable
lineage, protocol, evaluator, parity and leakage gate.

The user decision is recorded from the instruction to continue the proposed
route after R4-G0. It authorizes this narrow source-only redesign, not dataset
acquisition, environment creation or execution.

## 2. Why these two candidates

R5 carries exactly two R4 rows:

- R4-D1C-PROP-001: RecBole v1.2.1, BPR on MovieLens 100K, immutable revision
  `9a6f63d8d4a5b989fe27955a833f813a6d86041e`;
- R4-D1B-PROP-003: RecBole-GNN, LightGCN on MovieLens 1M, immutable revision
  `632ef888589944c190ad8f449b49ca559618d4df`.

Both are official owner repositories, have immutable revisions, source-owned
training/evaluation surfaces and no dispositive conflict. They also match the
frozen project baseline plan: RecBole is the declared framework-authoritative
surface for classical controls, and LightGCN is a mandatory graph baseline.
Neither row is promoted from its R4 exclusion status. All other R4 proposals
remain preserved as historical negative evidence and are not reconsidered.

## 3. Gate redesign

The strict D01–D12 framework from R4 is retained for final admission. R5 divides
evidence acquisition into two auditable gates.

Before source materialization, R5-S0 requires for each candidate:

1. one named project-owner repository;
2. one full immutable commit;
3. affirmative code-license evidence at that revision;
4. public source access without authentication or terms acceptance;
5. no recorded dispositive conflict; and
6. an exact local root, sparse path policy and operation boundary.

After source materialization, R5-M1A and R5-M1B may inspect the hash-locked
source to determine what can be established for environment declarations,
entrypoints, configuration/default resolution, evaluator semantics, TEST
isolation and bounded v5 adaptation. They must distinguish:

- source fact established at the pinned revision;
- locally proposed completion that would require a later controlled run;
- evidence still missing; and
- a conflict that permanently rejects the candidate.

Local inspection cannot by itself establish D03 provider-to-framework byte
lineage, reproduce D09 numeric targets, or claim VERIFIED reproducibility.
Those dimensions require later data acquisition and an actual rerun.

## 4. Stage topology

R5-S0 is central and freezes the candidate identities, source-only operation
contract, transition registry, model policy and input hashes.

R5-M0 is a central acquisition operation. It may create two isolated sparse Git
worktrees under the ignored `materialized_sources/r5` root, verify detached HEAD
at the locked commits, inventory tree metadata, hash every materialized file
and emit provenance receipts. It may not initialize submodules or Git LFS,
checkout dataset directories, fetch archives or modify vendor source.

After a passing R5-M0 receipt, two fresh worker contexts run concurrently:

- R5-M1A audits the RecBole/BPR source;
- R5-M1B audits the RecBole-GNN/LightGCN source.

R5-G1 is central and sequential. It validates source and audit hashes, compares
the two candidates without cross-joining evidence, and selects zero or one
candidate for a later dataset/environment materialization proposal. Selection
at R5-G1 is not benchmark admission and does not authorize a run.

R5-M2 is the mandatory next user checkpoint before any canonical dataset bytes,
package installation, environment/container creation, preprocessing, training,
evaluation, or TEST access.

## 5. Source-only operation boundary

Allowed only after R5-S0 passes:

- create the exact two declared local source roots;
- clone/fetch only the named project-owner Git repositories;
- resolve and checkout only the locked full commits in detached-HEAD mode;
- inspect Git tree metadata before checkout;
- materialize root source/metadata files plus declared source, properties and
  result-documentation directories through sparse checkout;
- read and hash source, license, dependency, configuration, evaluator and
  result-documentation files; and
- write R5 manifests, receipts, reports and handoffs to declared artifact roots.

Forbidden throughout R5-S0 through R5-G1:

- any repository, revision or source path not declared in the lock;
- submodule initialization, Git LFS object download, release/source archives,
  dataset/example-dataset directories, checkpoints or pretrained weights;
- authentication, accepting terms or contacting maintainers;
- modifying or executing vendor source;
- package installation, environment/container creation, preprocessing,
  training, evaluation or hyperparameter search;
- acquiring MovieLens or v5 data bytes; and
- opening the project v5 TEST set or treating a repository unit-test directory
  as authorization to access benchmark TEST data.

If a target root already exists, a commit cannot be resolved, the selected tree
contains a submodule/symlink/LFS pointer, a prohibited data artifact enters the
sparse worktree, or HEAD differs from the lock, materialization fails closed.
Nothing is overwritten or repaired in place.

## 6. No evidence cross-join

RecBole v1.2.1 and RecBole-GNN remain separate candidate tuples. A dependency
on RecBole does not permit a RecBole-GNN result to inherit RecBole's config,
evaluator, seed, environment or numeric run receipt. Likewise, prior GroupLens
provider checksums do not prove the bytes used by either framework. Every fact
is attributed to its exact source revision and claim scope.

## 7. Runtime model policy

- central stages: Sol Max Standard, runtime model `gpt-5.6-sol`, reasoning
  `max`, service tier `standard`;
- newly created worker stages: Sol XHigh Standard, runtime model
  `gpt-5.6-sol`, reasoning `xhigh`, service tier `standard`;
- plugin: `ars-codex:academic-research-suite` 0.1.26.

For worker dispatch, Standard speed is represented by omitting a service-tier
override. Artifacts still record `service_tier=standard`.

## 8. Persistent truth state

Every R5 artifact must preserve:

- `RESULT_STATUS=NOT_RUN`;
- `TEST_SET_OPENED=NO`;
- `ACCEPTED_RESULT_ROWS=0`;
- `execution_authorized=false`; and
- project benchmark numbers: `INVALID_FOR_PAPER`.

Source materialization is evidence acquisition, not experiment execution and
not a reproducibility success claim.
