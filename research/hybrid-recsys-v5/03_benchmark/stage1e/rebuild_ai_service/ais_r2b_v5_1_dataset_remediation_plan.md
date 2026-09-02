## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-02T17:11:47.628Z
- Verification Status: VERIFIED_STATIC_AND_PARENT_REPLAY
- Version Label: ais-r2b-v5.1-dataset-remediation-plan-v1.0.0
- Upstream Dependencies: ais-r2-runtime-materialization-suitability-receipt-v1.0.0, ais-r2-handoff-v2.0.0
- Repro Lock: parent-dataset:ce92d7b057585cf6b64962780d6032333dfed68618a5b21e455b4c9684d3533d;parent-items:e47585dc226fb5e5421fb3463fc145b209efd85175d0d3775399473a7cd66249;v5.1-policy:39bb46ee5498ac74740ca71270042a2e357d5b8b2a5ac42952b243f83a57d360
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# AIS-R2B — Dataset v5.1 remediation plan

## Decision

The current 5,200-SKU catalog is the authoritative project seed. The historical
1,380-SKU catalog is not a v5.1 input and is not used to replace or reduce the
current candidate universe.

Dataset v5.1 is a versioned feature-view amendment over the admitted v5
snapshot. It preserves, by hash:

- all 5,200 raw SKU identifiers and the 250-item cold partition;
- all 5,000 generated users;
- all 823,371 generated events and the 658,697 / 82,337 / 82,337 temporal split;
- all 15,000 training baskets and their organic/semantic origin labels.

It does not regenerate behavior, change target truth, inspect model results, or
open TEST. This makes the correction independent of Docker, WSL, TLS, and the
availability of the original databases.

## Why a feature view is required

The accepted v5 language audit established Vietnamese-language coverage, but a
deterministic semantic review found strongly incompatible product/packaging
combinations in 28 of 74 reviewed rows. The sample was diagnostic rather than a
population estimate, but it is sufficient to block raw generated names and raw
generated prices from entering a content model.

The committed 5,200-SKU seed contains 77 clean anchor products: IDs 1001–1023
and 2001–2054. Every current SKU belongs to one of their category/vendor groups.
Only six groups contain two anchors, and each of those groups is resolved by a
frozen product-family phrase. A full committed-seed replay mapped 5,200/5,200
rows to exactly one anchor.

## v5.1 model-facing representation

For each SKU, v5.1 emits:

- the original `raw_item_id`, unchanged;
- an audit-only `family_id`;
- a model text constructed from the clean family-anchor name and category;
- the source category;
- the family-anchor price and a global family-price quartile;
- the unchanged warm/cold partition;
- a SHA-256 receipt for the complete raw source row.

The raw generated name and raw generated price remain available in the parent
Source Bundle for lineage review but are excluded from model input. Vendor is
used only to resolve the frozen family mapping; it is not introduced as a new
model feature. Family ID is also excluded as a model feature to avoid label-like
shortcuts.

## Scientific scope

The v5.1 candidate universe remains 5,200 SKUs, but the model-facing text has 77
controlled semantic families. Therefore:

- the primary use is an internal warm-item controlled comparison;
- cold-item results are diagnostic and cannot establish SKU-level cold-start
  generalization;
- v5.1 remains controlled/generated behavior, not observed customer behavior;
- production-realism and broad external-validity claims remain unauthorized;
- a public or observed-behavior dataset is still required for external
  sensitivity evidence.

This limitation is preferable to presenting incoherent generated names as real
retail metadata or reducing the authoritative catalog to a historical seed.

## Execution sequence

1. Freeze `benchmark-spec-v5.1.json`, the family-view builder, and its tests.
2. Require Node syntax validation and the focused test suite to pass.
3. Replay the builder against the audited parent `items.jsonl` in
   `VERIFY_ONLY` mode; require exact parent hash, 5,200 products, 77 families,
   and 250 cold products.
4. Commit the frozen implementation before creating a runtime artifact.
5. Materialize exactly one new two-file artifact under a fresh external attempt
   root. Never overwrite or reuse a failed attempt root.
6. Verify both output hashes and import the feature view through a v5.1 adapter;
   event and basket files must remain byte-identical to parent v5.
7. Run dataset suitability again without building a TEST protocol.

## Failure policy

Any source-hash mismatch, missing anchor, unknown category/vendor group,
ambiguous mapping, count mismatch, cold-partition mismatch, pre-existing output
root, or non-finite price closes the attempt as incomplete. There is no fallback
to the 1,380-SKU seed, no best-effort mapping, and no silent behavior
regeneration.

## Current scientific state

`RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`,
`ACCEPTED_RESULT_ROWS=0`, and `execution_authorized=false` for training,
evaluation, and benchmark claims. Authorization in this plan is limited to
v5.1 feature-view materialization and validation.
