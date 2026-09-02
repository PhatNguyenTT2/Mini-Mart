## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-01T16:38:56Z
- Verification Status: UNVERIFIED
- Version Label: ais-r0-old-service-exclusion-v1.0.0
- Upstream Dependencies: ais-r0-architecture-decision-v1.0.0
- Repro Lock: null
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# Historical `ai-service` exclusion record

The directory `ai-service/` is classified as **HISTORICAL/QUARANTINED**. Its
presence is not evidence that a method is correct, reproducible, comparable, or
better than a baseline.

## Permitted inventory use

- identify field names and business concepts previously represented;
- inventory API surfaces for a later migration plan;
- identify known design and validation failure modes;
- understand historical data shapes without accepting their values;
- compare names only when the new contract defines their semantics independently.

## Prohibited scientific inheritance

- architecture, training code, objective, sampler, or evaluator;
- checkpoints, embeddings, association rules, or fitted artifacts;
- training configurations, environment assumptions, or random seeds;
- benchmark values, latency values, result tables, or thresholds;
- any claim that Hybrid outperforms a conventional architecture;
- any use of the old service as an official or harmonized comparator.

## Historical snapshot observation

The historical manifest
`ai-service/artifacts/snapshots/benchmark-v5-s42-7f40639b0d-1ace202aaa/manifest.json`
has SHA-256
`ed15a867dcb4c6e0bab0735e042c89e310e7cded87ad1fbc7875022907e23dd2`.
It reports 5,000 users, 5,200 items, 823,371 events, 250 cold items, and split
counts of 658,697/82,337/82,337.

These numbers are classified as
**HISTORICAL_CONTRACT_ASSERTION_ONLY**. They are not accepted dataset facts,
must not be copied into an experiment receipt, and become paper data facts only
after AIS-R2 reconstructs and verifies a canonical Dataset Snapshot from
admitted source bytes.

## Enforcement

- Source and tests under `ai-service-v2` must not import the old package.
- No path under `ai-service/` may appear as a runtime input to AIS-R2 through
  AIS-R7 without an explicit amendment and independent gate.
- If a historical field is retained, its meaning must be restated in the new
  contract and traced to admitted source data.
- Any accidental old-service dependency is a major finding and blocks the
  affected stage.
