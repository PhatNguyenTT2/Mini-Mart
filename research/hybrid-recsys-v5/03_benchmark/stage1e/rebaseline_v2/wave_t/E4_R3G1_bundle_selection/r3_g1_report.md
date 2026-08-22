# Stage 1E — R3-G1 central bundle selection

Date: `2026-08-22`

Runtime: `Sol Max Standard` (`gpt-5.6-sol`, reasoning `max`, service tier `standard`)

Verdict: `NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT`

## Entry validation

- FD2–FD4 central lane validator: `PASS`, `53/53` checks.
- Exact worker output set: `12/12` files.
- G1 frozen input replay: `20/20` files and `14/14` strict JSON inputs.
- Candidate order and seed SHA-256 remained unchanged.
- Carrier-only corrections embedded existing source records; no scientific status or claim changed.

## Exact intersection

| Candidate | FD2 | FD3 | FD4 | G1 eligibility |
|---|---|---|---|---|
| `R3-BUNDLE-CORNAC-ML100K-001` | `EVIDENCE_INCOMPLETE` | `EVIDENCE_INCOMPLETE` | `COMPATIBILITY_INCOMPLETE` | Ineligible |
| `R3-BUNDLE-ELLIOT-ML1M-001` | `EVIDENCE_INCOMPLETE` | `EVIDENCE_INCOMPLETE` | `COMPATIBILITY_INCOMPLETE` | Ineligible |
| `R3-BUNDLE-DAISYREC-ML1M-001` | `EVIDENCE_INCOMPLETE` | `EVIDENCE_INCOMPLETE` | `COMPATIBILITY_INCOMPLETE` | Ineligible |

No row passes the frozen prerequisite statuses. The evidence intersection therefore contains zero eligible candidates and selection cardinality is zero.

## Verification, deduplication and replay

The three repository–revision–dataset–protocol tuples are distinct, so no candidate row was collapsed. Across the worker lanes, 77 decision-bearing source mentions reduce to 61 unique exact URLs; 16 repeated mentions were not counted as independent evidence.

Central locator replay is required only for a row that could otherwise pass after the exact FD1–FD4 status intersection. That trigger set is empty. Replay attempts are therefore `0`, not because a positive row was accepted without replay, but because replay is prohibited from repairing an incomplete worker status.

## Why each row remains incomplete

- Cornac lacks closed archive-to-input byte lineage, a complete environment/tie contract, and a materialized full-catalog v5 adapter with parity receipts.
- Elliot lacks a checksum chain from MovieLens archive to its TSV, the exact producing BPRMF configuration/environment, and a complete-catalog adapter for train-unseen items.
- DaisyRec lacks closed acquisition lineage and same-surface benchmark verification; its frozen seed also mislabels Apache-2.0 as MIT, and the native item-cardinality path depends on train-plus-TEST data.

These findings do not establish that the frameworks are unusable. They establish that the current frozen evidence cannot support a single reproducibility bundle under the predeclared gate.

## Decision and boundary

No bundle is selected. `R3-M0` is not opened. Clone, download, terms acceptance, installation, environment creation, preprocessing, training, evaluation and TEST access remain blocked.

Persistent truth:

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- project benchmark numbers: `INVALID_FOR_PAPER`

