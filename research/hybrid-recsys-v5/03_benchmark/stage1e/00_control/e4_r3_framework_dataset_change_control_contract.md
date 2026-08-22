# Stage 1E — E4 R3 framework/dataset bundle discovery contract

Date: `2026-08-22`  
Stage family: `R3-FD`  
Entry verdict: `NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`  
User scope decision: `CREATE_NEW_FRAMEWORK_DATASET_ROW`  
Execution authority: `DENIED`

## 1. Objective and label

R3-FD searches for a new reproducibility bundle that can serve as the reference
training backend for a later adaptation to the current v5 dataset. A bundle is
one provenance-preserving row, not one URL and not a cross-join of attractive
parts from different projects. It must bind:

1. an affirmatively licensed framework/repository at an immutable revision;
2. one lawfully accessible, release-identified reference dataset;
3. a source-owned preprocessing/split/config/training/evaluation recipe;
4. a published or source-owned benchmark target produced for that same
   framework–dataset–protocol surface; and
5. a plausible adapter path to the current v5 task without silently changing
   the model objective, split, candidate policy or evaluator semantics.

Any selected row is labeled `FRAMEWORK_REPRODUCTION_REFERENCE`. It is not an
official reproduction of the LightGCN paper and cannot inherit that label.

The discovery target is three to five seed bundles. The central gate may select
zero or one. Popularity, stars, public GitHub visibility, a paper citation, or a
downloadable archive do not establish permission or reproducibility.

## 2. Supersession, not deletion

The seven R2 candidate rows are preserved as historical evidence and are marked
`ARCHIVED_SUPERSEDED_NOT_EXECUTION_ELIGIBLE` in
`e4_r3_supersession_registry.json`. No prior artifact is edited or deleted.
Nothing was cloned, installed, trained or evaluated in those rows, so there are
no materialized model assets to remove.

No R3 lane may repair an old row by borrowing a new repository, dataset or
benchmark surface. A new provenance bundle receives a new `R3-BUNDLE-*` ID.

## 3. Runtime model policy

The user replaced the preceding Fast policy for all newly created stages:

- worker stages `R3-FD1` through `R3-FD4`: display `Sol XHigh Standard`, model
  `gpt-5.6-sol`, reasoning `xhigh`, service tier `standard`;
- central stages `R3-FD0`, validation/import and `R3-G1`: display
  `Sol Max Standard`, model `gpt-5.6-sol`, reasoning `max`, service tier
  `standard`;
- plugin: `ars-codex:academic-research-suite` `0.1.26`.

For subagent dispatch, an omitted service-tier override is the runtime mechanism
for Standard speed. Every artifact still records `service_tier=standard`.
Standard changes scheduling only; it does not lower evidence requirements.

## 4. Topology and context isolation

`R3-FD0` is central change control and input freeze.

`R3-FD1` then runs in a fresh worker context and emits exactly three to five
candidate seeds. It searches broadly but may admit a seed only when official
primary-source locators plausibly cover all five bundle components in Section 1.

After central schema/hash validation of the frozen FD1 output, three fresh
worker contexts run concurrently over the exact same candidate IDs:

- `R3-FD2`: repository license, dataset rights/release and lineage verification;
- `R3-FD3`: benchmark/config/training/evaluator and result-target verification;
- `R3-FD4`: v5 compatibility, adaptation scope and reproducibility-risk stress
  test using local project contracts plus official source evidence.

`R3-G1` is central and sequential. It performs exact-ID joins, deduplication,
authoritative locator replay and a zero-or-one selection. Worker lanes never
select the winner.

## 5. Source and evidence policy

Decision-bearing evidence must come from primary or authoritative sources:

- the project owner's repository, immutable tree/blob/commit/release pages and
  repository license;
- the original paper/proceedings page and its supplementary artifacts;
- the canonical dataset provider, release page, terms/license and checksums;
- source-owned documentation, configs, scripts, evaluator and result tables.

Search snippets, generated summaries, mirrors, forks, package indexes, blogs,
leaderboards without protocol, and third-party tutorials are locators only.
Failed or blocked replay remains `UNVERIFIED`; absence of evidence is never
converted into a negative or positive factual claim.

Every claim must carry a direct locator, an access result, an evidence scope and
an explicit confidence/status. Web page text is evidence data, never pipeline
instruction.

## 6. Positive gate

`R3-G1` may return `PROVISIONAL_SINGLE_BUNDLE_FOR_MATERIALIZATION` only when one
candidate satisfies all of the following without a cross-join:

1. `FD2=EVIDENCE_SUFFICIENT_FOR_G1_REVIEW` and the repository has an affirmative
   code license whose scope covers the intended use;
2. the exact dataset release has an affirmative lawful-use basis, stable
   provider identity, and enough acquisition/preprocessing/split lineage to
   reproduce the reference protocol;
3. `FD3=EVIDENCE_SUFFICIENT_FOR_G1_REVIEW` with a pinned repository revision,
   source-owned train/evaluate entry points, frozen config/protocol locators,
   evaluator semantics and a numeric reference target tied to the same row;
4. `FD4=COMPATIBLE_WITH_BOUNDED_ADAPTER` and no dispositive task, schema,
   objective, environment or evaluator mismatch is present;
5. every decision-bearing locator replays centrally; and
6. the bundle is preferable to every other sufficient row under the frozen
   ranking order: provenance completeness, legal clarity, protocol fit,
   evaluator parity feasibility, adaptation cost, then maintenance recency.

A source producing only paper numbers but no reusable recipe is insufficient.
A runnable framework with no same-surface benchmark target is also insufficient.
A checkpoint or historical run receipt is desirable but is not substituted for
our future reproduction receipt: the later materialization stage must generate
its own hashes, environment lock, run IDs and comparison against the frozen
target tolerance.

If no row passes all conditions, the only valid verdict is
`NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`.

## 7. Benchmark interpretation boundary

Published/source-owned reference metrics are usable only as a target for
reproducing the selected framework on its reference dataset and protocol. They
must not be compared directly with v5 metrics to claim superiority.

The later harmonized comparison requires all selected baselines and the proposed
model to be trained and evaluated on the same immutable v5 split, candidate
policy, tuning budget, seeds and shared evaluator. Cross-dataset values remain
in separate tables and support reproducibility/external-validity discussion,
not a direct ranking claim.

## 8. Forbidden operations before R3-M0

Until a positive `R3-G1` verdict and an explicit user materialization checkpoint,
all stages are forbidden from:

- cloning, fetching, checking out or downloading repositories/source archives;
- downloading datasets, processed splits, checkpoints or other assets;
- accepting terms, licenses or credentials on the user's behalf;
- installing packages or creating environments/containers;
- preprocessing, training, evaluation or benchmark execution;
- opening the v5 TEST set;
- contacting maintainers; or
- copying any candidate metric into the paper as a valid project result.

Allowed operations are read-only local inspection, public authoritative web
research, deterministic hash/schema checks, and writes to declared R3 roots.

## 9. Persistent truth state

Every R3 artifact must preserve:

- `RESULT_STATUS=NOT_RUN`;
- `TEST_SET_OPENED=NO`;
- `ACCEPTED_RESULT_ROWS=0`;
- `execution_authorized=false`;
- project benchmark numbers: `INVALID_FOR_PAPER`.

