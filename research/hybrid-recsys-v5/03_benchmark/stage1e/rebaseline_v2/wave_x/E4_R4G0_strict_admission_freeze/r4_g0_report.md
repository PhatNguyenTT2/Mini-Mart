# R4-G0 strict complete-bundle admission report

Date: 2026-08-22  
Central context: Sol Max Standard  
Verdict: NO_ADMISSIBLE_BUNDLE_STOP_FAIL_CLOSED

## Outcome

The strict discovery wave examined 18 distinct proposals across three independent
source families. No worker proposed a bundle for admission. All 18 were
excluded before central replay: 12 as incomplete bundles and 6 as dispositive
rejects.

| Lane | Source family | Examined | Admitted | Excluded | Source records |
|---|---|---:|---:|---:|---:|
| R4-D1A | Official artifact/reproduction packages | 5 | 0 | 5 | 20 |
| R4-D1B | Official benchmark suites/results packages | 5 | 0 | 5 | 23 |
| R4-D1C | Official framework complete packets | 8 | 0 | 8 | 47 |
| Total | — | 18 | 0 | 18 | 90 |

The central mechanical gate passed after one D1A carrier-only correction that
added the frozen truth object to three JSON files. No evidence record, count,
exclusion reason or verdict changed. The final frozen gate passed 22/22 inputs,
17/17 strict JSON inputs and 15/15 worker outputs.

## Why nothing was admitted

Admission required all twelve dimensions to pass. Four dimensions failed for
every proposal:

- D03 byte-verifiable dataset acquisition and transformation lineage: 18/18;
- D08 complete evaluator semantics, including candidate policy, masking,
  aggregation and deterministic tie handling: 18/18;
- D09 numeric target bound to the exact same revision, dataset, protocol,
  config and evaluator surface: 18/18;
- D11 bounded adaptation to v5 without changing objective/evaluator: 18/18.

Other frequent gaps were exact protocol/config/seeds (17/18), complete
environment lock (16/18), no-TEST derivation evidence (16/18), canonical dataset
rights/release identity (15/18), and affirmative code-license evidence at the
pinned revision (13/18).

This result explains why README numbers and generic runnable frameworks are not
usable reference benchmarks. They usually demonstrate capability but do not
prove that a published number was produced by the exact code, bytes, split,
configuration and evaluator that would be reproduced.

## Deduplication and replay

All 18 proposal IDs and all 18 exact eight-component provenance tuples were
unique. The Microsoft/Recommenders repository appeared in two proposals, but at
different revisions and on different protocol/config/result surfaces, so the
rows were not collapsed or cross-joined.

The 90 source records contained 88 unique exact URLs; the two duplicate mentions
were the canonical GroupLens MovieLens 100K and 1M pages. Because no worker
proposal passed the admission conjunction, the preregistered central replay
scope was zero proposals and zero URLs. R4-G0 did not replay excluded rows in an
attempt to repair them.

## Scientific and execution boundary

The empty freeze is a valid fail-closed result. No benchmark number from this
wave is valid for the paper, and cross-dataset numbers remain unsuitable for a
direct superiority claim. R4-A1, R4-A2 and R4-A3 are not launched; R4-G1 and
R4-M0 are not opened.

RESULT_STATUS remains NOT_RUN, TEST_SET_OPENED remains NO,
ACCEPTED_RESULT_ROWS remains 0, and execution_authorized remains false.
Repository/data acquisition, environment creation, training and evaluation
remain blocked.

## Required next checkpoint

Another blind broad-discovery wave is not automatic. The next decision must
choose one of three materially different paths:

1. authorize a narrowly scoped evidence-materialization redesign for named
   near-complete candidates, with a new contract and no training/TEST access;
2. redesign which admission dimensions must be established pre-materialization
   versus by an auditable local reproduction, without weakening the final
   benchmark gate; or
3. pause the external reference track and keep the paper benchmark claims
   explicitly NOT_RUN/INVALID_FOR_PAPER.
