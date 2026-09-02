# ai-service-v2

`ai-service-v2` is the clean research/benchmark runner for the hybrid
recommender paper. It is deliberately separate from the historical
`ai-service` directory.

## Status

AIS-R0 is design-frozen and AIS-R1 is implemented as a static, fixture-tested
foundation. AIS-R2 now has a strict file-only Source Bundle adapter, canonical
seven-file Dataset Snapshot v1.1, organic-only truth/rule separation, and a
validation-only suitability report. AIS-R2B additionally provides a v5.1
family-view adapter that preserves the parent behavior files byte-for-byte
while replacing raw catalog content with the frozen model-facing family view.
The audited v5.1 canonical snapshot passes schema, lineage, mapping, and
suitability replay, but remains an internal controlled/generated dataset and
does not authorize training or TEST. AIS-R3 remains pending independent metric
audit. No public dataset has been downloaded, no reference repository has been
executed, no training/evaluation benchmark has been run, and no paper result is
emitted by this package.

The old service is not a scientific baseline. Its checkpoints, embeddings,
rules, benchmark numbers, and configurations are not imported here.

## Design boundary

The runner has four independent seams:

1. an immutable dataset snapshot and manifest;
2. a frozen evaluation protocol;
3. a model/adapter that emits scores only;
4. a model-independent full-catalog evaluator that owns masking, ranking,
   metrics, and aggregation.

Reference repositories keep their native training objective and environment.
They will be integrated through adapters only after source-bound official
reproduction is admitted. The proposed Wide + Apriori + Deep Two-Tower model
is a candidate, not an accepted result.

## Local checks

From this directory, with a Python environment that has the declared
dependencies:

```text
python -m pytest -q
python -m ai_service_v2.cli validate-manifest <manifest.json>
python -m ai_service_v2.cli validate-snapshot tests/fixtures/fixture-retail-v1
python -m ai_service_v2.cli materialize-v5-source <source-bundle> <new-snapshot>
python -m ai_service_v2.cli assess-snapshot <snapshot>
python -m ai_service_v2.cli materialize-v5-family-view \
  <parent-snapshot> <family-view> <new-snapshot> \
  --amendment <benchmark-spec-v5.1.json>
```

The last two commands require an admitted immutable Source Bundle for research
use. The test helper builds fixture-only bytes and must never be used as a paper
dataset.

`train --model-kind` supports the local fixture registry (`random`, `mostpop`,
`rule_only`, `deep_two_tower`, and `hybrid`). These implementations exercise
the score-artifact and evaluator seams; they are not reference reproductions or
paper baselines.

The current tests use only small in-memory fixtures. They are not benchmark
results and must not be copied into the manuscript.
