# ai-service-v2

`ai-service-v2` is the clean research/benchmark runner for the hybrid
recommender paper. It is deliberately separate from the historical
`ai-service` directory.

## Status

AIS-R0 is design-frozen and AIS-R1 is implemented as a static, fixture-tested
foundation. Dataset/protocol/evaluator/statistics modules needed by AIS-R2 and
AIS-R3 exist and pass fixture tests, but those stages are not admitted until a
canonical v5 snapshot and an independent metric audit are bound. No public
dataset has been downloaded, no reference repository has been executed, no
training/evaluation benchmark has been run, and no paper result is emitted by
this package.

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
```

`train --model-kind` supports the local fixture registry (`random`, `mostpop`,
`rule_only`, `deep_two_tower`, and `hybrid`). These implementations exercise
the score-artifact and evaluator seams; they are not reference reproductions or
paper baselines.

The current tests use only small in-memory fixtures. They are not benchmark
results and must not be copied into the manuscript.
