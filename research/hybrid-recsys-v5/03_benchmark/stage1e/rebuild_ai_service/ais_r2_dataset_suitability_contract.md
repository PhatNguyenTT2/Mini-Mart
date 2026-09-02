## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-02T05:53:53Z
- Verification Status: UNVERIFIED
- Version Label: ais-r2-dataset-suitability-contract-v1.0.0
- Upstream Dependencies: ais-r2-source-bundle-contract-v1.0.0, experimental-log-preregistered-protocol
- Repro Lock: null; real canonical snapshot pending
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# AIS-R2 dataset-suitability contract

## Current classification

Benchmark v5 is a controlled/semi-synthetic Vietnamese retail benchmark. Its
user identities, personas, events, sessions, and baskets are generated with a
fixed seed. Product metadata comes from the project catalog and requires an
independent provenance, license, and Vietnamese-language audit. It is not
observed behavior from 5,000 verified customers and cannot support a
real-world-generalization claim by itself.

The following values remain contract targets until a real canonical snapshot
passes strict loading:

| Fact | Contract value |
|---|---:|
| users | 5,000 |
| items | 5,200 |
| cold items | 250 |
| events | 823,371 |
| train / validation / test events | 658,697 / 82,337 / 82,337 |
| baskets | 15,000 |
| organic / semantic baskets | 14,250 / 750 |
| distinct user-item cells | 356,181, pending runtime verification |
| distinct-cell density | 1.3699%, pending runtime verification |

Event-frequency density and distinct-cell density must remain separate. The
former uses all event rows; the latter uses unique `(user, item)` cells and is
the value used when describing matrix sparsity.

## Automated validation-only checks

`assess-snapshot` may inspect the canonical snapshot and validation truth, but
it may not prepare a TEST protocol or evaluate model scores. It reports:

- source-bundle and source-artifact bindings;
- non-empty temporal splits and exact split counts;
- unique user-item cells and both density definitions;
- organic, semantic-trap, and cold-start event counts;
- validation users with novel organic-purchase truth;
- organic and semantic TRAIN-basket counts;
- cold-item cohort presence;
- missing and normalized-duplicate item text;
- provenance, license, and language admission statuses.

The report always declares `test_set_opened=false` and
`accepted_result_rows=0`.

## Admission criteria

AIS-R2 dataset suitability requires all of the following:

1. Dataset Manifest v1.1 is bound to an immutable Source Bundle and exact source
   artifacts.
2. Users, items, events, baskets, split counts, cold items, and raw mappings
   reconcile with the admitted export and generator specification.
3. Validation contains at least one eligible user with a novel organic
   purchase; the real gate must additionally satisfy the preregistered minimum
   and report its denominator.
4. At least one organic TRAIN basket exists and no semantic basket contributes
   to the main Apriori table.
5. Item text is non-empty; provenance, license, and language audits are
   admitted.
6. The dataset is labeled `CONTROLLED_GENERATED_BEHAVIOR` and
   `observed_behavior=false` unless a new evidence-backed amendment proves
   otherwise.
7. No TEST model result, tuning decision, or Accepted Result Row exists.

Duplicate product text is diagnostic rather than an automatic failure because
variants can legitimately share normalized names; the count must be reported
and reviewed before content-feature training.

## If suitability fails

The v5 snapshot is immutable. A data correction requires a new source export,
new Source Bundle hash, and—if generator/data semantics change—a versioned
amendment such as v5.1. The process must not densify data, alter target truth,
or regenerate behavior after observing TEST model results. If basket or
co-purchase support is insufficient, the method is relabeled as a reduced
ablation rather than silently fabricating Wide signal.

Internal mechanism evidence must ultimately be complemented by a public or
observed-behavior sensitivity dataset before broad external-validity claims.
