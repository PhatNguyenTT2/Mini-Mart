## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-02T05:53:53Z
- Verification Status: UNVERIFIED
- Version Label: ais-r2-source-bundle-contract-v1.0.0
- Upstream Dependencies: ais-r0-handoff-v1.0.0, ais-r0-protocol-evaluator-contract-v1.0.0
- Repro Lock: candidate generator tree `a15ad1beb8b728035e5cd333bf23c247c9c8b396519acd24ea7fcace01322587`; real export pending
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# AIS-R2 source bundle and canonical snapshot contract

## Purpose and authority boundary

AIS-R2 converts one authorized, immutable export of benchmark v5 into the only
Dataset Snapshot that later models may consume. The adapter is file-only: it
does not connect to PostgreSQL, run a generator, modify catalog data, open TEST,
train a model, or calculate a benchmark metric.

The historical snapshot under `ai-service/artifacts/` is excluded. It may be
used to understand historical fields, but its bytes, IDs, hashes, split files,
and derived artifacts are not an AIS-R2 source.

## Source Bundle v1.0

An admitted Source Bundle contains exactly six files:

```text
source_manifest.json
benchmark_spec.json
users.jsonl
items.jsonl
events.jsonl
baskets.jsonl
```

`benchmark_spec.json` is a normalized export projection containing only schema
version, generator version, seed, store, dataset counts, split counts, and the
six inclusive temporal boundaries. It is not allowed to impersonate the raw
generator specification. `source_manifest.json.generator_spec_source_sha256`
binds the original generator-spec bytes, while
`generator_source_tree_sha256` binds the declared generator implementation
tree.

The source manifest must bind:

- a full source commit and benchmark run ID;
- generator tree, original generator spec, and export-query SHA-256 values;
- raw SHA-256 for every other bundle file;
- expected users, items, events, baskets, cold items, and split counts;
- catalog provenance, license, and language-audit statuses;
- behavior classification and whether behavior is observed.

Every JSON object uses strict parsing: BOM, duplicate key, case-colliding key,
unknown contract field, malformed UTF-8, blank JSONL row, or hash mismatch is a
hard failure.

## Row schemas

```text
users:   raw_user_id
items:   raw_item_id, name, category, vendor, price, partition
events:  raw_event_id, raw_user_id, raw_item_id, event_type, event_ts,
         event_origin, session_id, cohort_id, persona_cluster,
         interaction_weight
baskets: raw_basket_id, raw_user_id, basket_ts, basket_origin, raw_item_ids
```

Allowed event types are `view` and `purchase`. Allowed event origins are
`organic`, `semantic_trap`, and `cold_start`. Training-basket origins are
`organic` and `semantic_trap`. Every basket must have at least two distinct
known items and lie inside the frozen TRAIN interval.

Source events must be ordered by `(event_ts, raw_event_id)` and baskets by
`(basket_ts, raw_basket_id)`. The adapter never silently sorts a defective
export. Dense internal IDs are assigned from ascending raw IDs; all raw IDs and
raw event IDs remain bound in the canonical artifact.

## Canonical Dataset Snapshot v1.1

Successful materialization atomically publishes exactly:

```text
manifest.json
users.jsonl
items.jsonl
baskets.jsonl
train.jsonl
val.jsonl
test.jsonl
```

The manifest binds the Source Bundle, each source artifact, raw user/item maps,
item features, training baskets, all three splits, cold-item IDs, behavior
classification, and catalog audit statuses. The full payload hash covers users,
items, baskets, and split rows. Existing output or staging roots are rejected;
there is no overwrite or in-place retry.

The frozen temporal intervals are taken from the normalized specification.
Rows outside all intervals, count disagreement, unknown IDs, duplicate IDs,
non-finite values, or unordered rows fail closed.

## Scientific semantics

- All prior interactions remain history for seen-item masking.
- Only novel `organic` purchases are validation or TEST relevance truth.
- Main Apriori features are fitted only from explicit organic TRAIN baskets.
- Semantic-trap baskets remain available for mechanism audit but cannot enter
  the main Wide rule table.
- Cold-start events and items remain explicit; cold-item results must not be
  described as cold-user results.
- Materialization and validation fixtures never create an Accepted Result Row.

## Commands and gate

```text
ai-v2 materialize-v5-source <admitted-source-root> <new-canonical-root>
ai-v2 assess-snapshot <canonical-root>
```

AIS-R2 can pass only when the real Source Bundle, catalog audits, canonical
manifest, dataset-suitability report, and exact output hashes are independently
verified. Static fixture success alone yields `SOURCE_EXPORT_PENDING`.
