## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-01T16:38:56Z
- Verification Status: UNVERIFIED
- Version Label: ais-r0-failure-retry-policy-v1.0.0
- Upstream Dependencies: ais-r0-architecture-decision-v1.0.0, ais-r0-protocol-evaluator-contract-v1.0.0
- Repro Lock: null
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# Failure and retry policy

## Fail-closed rules

- Every materialization, reproduction, training, evaluation, or audit execution
  receives a new immutable attempt root.
- A failed attempt is never rerun in place. A retry requires a new attempt ID,
  a recorded reason, and unchanged frozen inputs unless an amendment explicitly
  declares the change.
- There is no silent fallback to another repository, dataset, image, package,
  model, metric, sampler, split, evaluator, or tolerance.
- Missing provenance, an incomplete seed, a hash mismatch, premature TEST
  access, or a non-finite artifact produces `FAIL`, `INCOMPLETE`, `REJECTED`, or
  `INCOMPARABLE`; it never produces an Accepted Result Row.
- Logs and receipts are retained and labeled `FAILED`, `SUPERSEDED`, or
  `HISTORICAL`. They are not deleted to make a later attempt appear clean.

## Stage-specific recovery

- AIS-R0 through AIS-R3 must remain executable without Docker, WSL, TLS, network
  access, or a public dataset. Their fixtures verify contracts, not science.
- A source/data/environment admission failure blocks runtime but does not alter
  protocol semantics or comparator scope.
- Infrastructure failure closes the current runtime attempt. Read-only evidence
  may be collected, but repair occurs before a separately admitted new attempt.
- Code or probe defects receive a bounded remediation plan. Central integrates
  the repair and reruns static gates before authorizing a new runtime attempt.
- Resource-limit changes require a new environment receipt and new attempt; they
  may not be applied after observing a model result within the same attempt.

## Scientific recovery

- Failure to reproduce the source-bound center is reported as `REJECTED` or
  `INCOMPARABLE` with the exact failed bindings; it does not authorize copying
  the published value into the paper.
- A baseline or Hybrid result that is worse than expected remains a valid
  negative/null result. The dataset, metric, or cohort must not be changed after
  TEST access to reverse the conclusion.
- If the v5 Dataset Snapshot fails lineage or task-suitability checks, create a
  new version and amendment; preserve v5 and do not mutate it in place.

## State and authority

`pipeline_state_stage1e.json` remains unchanged until AIS-R7 independent audit
passes and the Stage-1E seal is issued. Fixture success, host-admission success,
or central review alone does not authorize benchmark execution.
