## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-01T16:38:56Z
- Verification Status: UNVERIFIED
- Version Label: ais-r0-architecture-decision-v1.0.0
- Upstream Dependencies: academic-research-master-plan@89a746f3, standard-for-training@89c65832, stage1e-r6-g0-freeze@32f7e4c8
- Repro Lock: null
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# Use a contract-first independent research runner

Status: **Accepted for AIS-R0**.

The paper needs comparisons whose dataset, protocol, scores, evaluator, and
statistics can be audited independently. The historical service does not
provide that separation and cannot establish that the proposed architecture is
better than conventional methods. Therefore, the research runner is rebuilt in
`ai-service-v2` as an independent package with no dependency on the historical
service.

The accepted data flow is:

```text
Immutable Dataset Snapshot
        -> Frozen Protocol and TEST Seal
        -> Reference Adapter or Proposed Model
        -> Immutable Score Artifact
        -> Independent Shared Evaluator
        -> Per-user Metrics and Paired Statistics
        -> Audited Result Receipt
```

Models own training and score production only. The shared evaluator owns
seen-item masking, deterministic ranking, metric definitions, denominators, and
aggregation. Official-source reproduction and harmonized-v5 comparison remain
separate evidence namespaces and may not borrow centers, configurations, or
evaluators from each other.

## Scope consequences

- V1 is a research and benchmark runner; FastAPI, ONNX, database integration,
  background workers, and production serving are deferred until AIS-R8.
- `ai-service` remains read-only historical material. No checkpoint, rule,
  embedding, configuration, benchmark value, or superiority claim is inherited.
- AIS-R0 freezes the design. AIS-R1 has a fixture-tested implementation; the
  AIS-R2 and AIS-R3 code foundations are not admitted until a canonical snapshot
  and an independent metric audit are bound.
- Docker, WSL, TLS, repository downloads, public-dataset materialization,
  training, and benchmark evaluation are outside AIS-R0/R1.
- A negative or null Hybrid result is valid. Metrics, data, or scope must not be
  changed after TEST access to manufacture a positive outcome.

## Rejected alternatives

- Extending the historical service was rejected because it would preserve
  unverified architecture and result coupling.
- Letting each model calculate its own metrics was rejected because evaluator
  differences would make comparisons non-identifiable.
- Starting with container/runtime work was rejected because infrastructure
  faults should not block schema, protocol, evaluator, and fixture verification.
