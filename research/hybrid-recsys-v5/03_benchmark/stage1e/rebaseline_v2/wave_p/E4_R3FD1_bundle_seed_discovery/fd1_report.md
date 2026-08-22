# Stage 1E — R3-FD1 candidate bundle seed discovery

Verdict: `THREE_PLAUSIBLE_COMPLETE_SEEDS_READY_FOR_PARALLEL_VERIFICATION`  
Final composer: `Sol Max Standard` (`gpt-5.6-sol`, reasoning `max`, service tier `standard`)  
Evidence scouts: three fresh `Sol XHigh Standard` contexts  
Selection: `NOT_PERFORMED`

## Outcome

The three scout carriers passed central structural validation: seven proposals,
four scout-plausible rows and 81 authoritative source records. Central
deduplication admitted three non-duplicate seeds:

1. `R3-BUNDLE-CORNAC-ML100K-001` — Cornac 2.6.0, MovieLens 100K, BPR,
   NDCG@10 owner target;
2. `R3-BUNDLE-ELLIOT-ML1M-001` — Elliot v0.3.1, MovieLens 1M, BPRMF,
   nDCG@50 paper target;
3. `R3-BUNDLE-DAISYREC-ML1M-001` — DaisyRec 2.0, MovieLens 1M TSBR,
   BPRMF NDCG@10 source-owned target.

These are candidate seeds, not approved repositories and not project benchmark
results. FD2 must verify code/data rights and lineage, FD3 must verify the exact
training/config/evaluator/result join, and FD4 must stress-test bounded v5
adaptation. No winner has been selected.

## Exclusions and deduplication

The Recommenders MovieLens 100K surface appeared independently in FD1A and FD1C
with conflicting plausibility statuses. Central immutable notebook/license/result
replay cache-missed, so the surface was excluded rather than promoted by merging
partial evidence. TensorFlow Recommenders lacked an immutable tutorial/result
binding and original paper locator. ReChorus lacked affirmative canonical Amazon
dataset terms and exact derivative lineage.

All seven old R2 candidate rows remain archived and non-executable. No prior
artifact or model asset was deleted because no repository, dataset, checkpoint,
environment or run had been materialized.

## Source replay boundary

Central replay confirmed the Cornac commit identity and the canonical MovieLens
100K/1M usage terms. Several GitHub pinned blob/commit routes returned web-client
cache misses. Those failures remain explicit unresolved fields and cannot count
as positive evidence; they are routed to FD2/FD3 for independent replay.

The GroupLens terms allow research use subject to acknowledgement, prohibit
redistribution without permission and prohibit commercial/revenue-bearing use
without permission. Any future acquisition must preserve those boundaries.

## Benchmark interpretation

All three numbers are frozen only as future reference-reproduction targets on
their own dataset/protocol surfaces. They cannot be compared directly with v5 or
copied into the manuscript as project results. Harmonized v5 evaluation still
requires same split, candidate policy, tuning budget, seeds and shared evaluator
for every baseline and the proposed model.

## Truth state

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- project benchmark numbers remain `INVALID_FOR_PAPER`

No clone, fetch, archive/data/checkpoint download, terms acceptance, package
installation, environment creation, preprocessing, training, evaluation, TEST
access, maintainer contact or candidate selection occurred.

