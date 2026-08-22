# R3-FD3 benchmark and evaluator verification report

Date: `2026-08-22`  
Stage: `R3-FD3`  
Runtime profile: `Sol XHigh Standard` (`gpt-5.6-sol`, reasoning `xhigh`, service tier `standard`)

## Outcome

FD3 preserved the frozen candidate order and emitted one row per seed. No row reaches `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`; all three are `EVIDENCE_INCOMPLETE`. No candidate was selected, ranked, repaired, merged, cloned, downloaded, installed, trained, evaluated, or materialized.

| Candidate | FD3 status | Decision-bearing reason |
|---|---|---|
| `R3-BUNDLE-CORNAC-ML100K-001` | `EVIDENCE_INCOMPLETE` | The pinned recipe and target replayed, but there is no exact environment/transitive lock, no independently replayed dataset-byte checksum binding, and no explicit stable tie rule. |
| `R3-BUNDLE-ELLIOT-ML1M-001` | `EVIDENCE_INCOMPLETE` | The release, config, runner, split/model seeds, evaluator, and paper target replayed, but archive-to-TSV byte lineage, a complete environment lock, the selected BPRMF trial realization, and an explicit stable tie rule remain unresolved. |
| `R3-BUNDLE-DAISYREC-ML1M-001` | `EVIDENCE_INCOMPLETE` | The frozen official locators were retained, but the immutable code/result/config/evaluator surfaces did not independently replay in FD3; no positive same-surface join was inferred. |

## Candidate findings

### R3-BUNDLE-CORNAC-ML100K-001

The immutable owner commit replayed as Cornac 2.6.0. The revision-pinned README binds a source-owned executable Python recipe to MovieLens 100K, shuffled `RatioSplit(test_size=0.2, rating_threshold=4.0, seed=123)`, `BPR(k=10, max_iter=200, learning_rate=0.001, lambda_reg=0.01, seed=123)`, and `NDCG(k=10)`, and reports `0.1500` for BPR.

Pinned evaluator code establishes full known-catalog evaluation after excluding train/validation positive items, truncation to training-known items when unknown exclusion is active, per-user binary NDCG, omission of users without test positives, and macro user averaging. Ranking uses NumPy `argpartition`/`argsort`; no source-owned secondary tie key was observed. The pinned `pyproject.toml` is a dependency recipe, not a complete lock, and the loader's canonical GroupLens `u.data` URL is not accompanied by an independently replayed checksum binding. The numeric value remains a future reference target only.

### R3-BUNDLE-ELLIOT-ML1M-001

The owner release binds Elliot v0.3.1 to commit `641100a89c707619e557eafc46df7ff46c359a73`. Revision-pinned requirements, entrypoint, advanced configuration, runner, splitter, model seed path, BPRMF scorer, candidate-mask code, and nDCG implementation replayed.

The advanced configuration specifies MovieLens 1M TSV input, iterative 10-core filtering, user-wise 20% random holdout, five validation folds, relevance threshold 1, top-k 50, five random BPRMF trials, and 50 epochs. Source code fixes HyperOpt, split, and model random-state defaults at 42. Without a negative-sampling block, training-known unrated items form the candidate set; nDCG is macro-averaged over test users. The author-hosted SIGIR paper explicitly binds Configuration 3 to Table 3 and reports BPRMF `nDCG@50 = 0.2390`.

The row remains incomplete because the canonical MovieLens archive/checksum and generated TSV bytes were not independently joined, the dependency recipe is not a complete platform/transitive lock, the paper does not print the selected BPRMF trial realization, and top-k ranking has no explicit stable secondary tie key. The numeric value remains a future reference target only.

### R3-BUNDLE-DAISYREC-ML1M-001

FD1 froze official owner locators for code commit `e9d0326457fb8aa138f7bb04ab751b17345cdb65`, README, `main.py`, splitter, metrics, appendix, result commit `440c95534cbb21dd0f7b8a7d551bfddbfcb2422e`, and the BPRMF TSBR result row. Those required surfaces were not independently replayed before FD3 closure. The frozen `0.5275` assertion is recorded only as unresolved provenance and is not accepted or promoted.

## Boundaries and limitations

- Decision-bearing claims use only independently replayed owner/author sources; unreplayed frozen locators remain `UNRESOLVED`.
- Search snippets, current unpinned repository summaries, and prior scout replay labels do not close FD3 fields.
- Failed replay is not evidence of nonexistence and therefore does not produce `DISPOSITIVE_REJECT` here.
- No same-surface join is positive, no winner is selected, and all candidate values remain invalid as project or paper results.

## Persistent truth state

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- `project_benchmark_numbers=INVALID_FOR_PAPER`

The next action, if any, belongs to the central validation/import gate. FD3 grants no materialization or execution authority.
