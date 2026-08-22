# R3-FD1B academic benchmark-suite scout report

Created: `2026-08-22T13:27:05Z`  
Stage: `R3-FD1B`  
Scope: `academic_benchmark_and_reproducibility_suites`  
Model profile required by dispatch: `Sol XHigh Standard` / `gpt-5.6-sol` / `xhigh` / `standard`

## Gate and operating boundary

The read-only FD0 validator returned `PASS_R3_FD0_GATE_17_OF_17_READY_FOR_FD1` with 17/17 frozen inputs matched and zero failures. Research then remained inside the FD1 boundary: public authoritative web inspection and local read-only inspection only.

No repository, source archive, dataset, checkpoint or asset was downloaded. No environment or package was installed. No preprocessing, training, evaluation or test access occurred. No maintainer was contacted. No selection was performed.

## Search method and stopping rule

The scout searched for peer-reviewed or author-maintained suites explicitly designed for rigorous, fair or reproducible recommender comparison. A surface was retained only when official-owner and canonical-provider sources plausibly joined code license, immutable code revision, exact dataset release and terms, preprocessing/split, entrypoint/config, evaluator and a numeric same-suite result target.

Search stopped after two strong, non-superseded surfaces met the plausibility gate. This is a bounded shortlist, not an exhaustive review. Search snippets were used only to locate official pages; decision-bearing records in `scout_candidates.json` point to owner repositories/commits/blobs, original papers and the canonical GroupLens dataset provider.

## Proposal R3-FD1B-PROP-001 — Elliot v0.3.1

Status: `PLAUSIBLE_COMPLETE_PROPOSAL`

Elliot is explicitly presented by its maintainers and SIGIR 2021 paper as a framework for complete, reproducible recommender experiments driven by configuration. The owner release identifies v0.3.1 and commit `641100a`; read-only GitHub metadata resolved the full immutable SHA to `641100a89c707619e557eafc46df7ff46c359a73`. The exact revision carries an Apache-2.0 license, a MovieLens conversion recipe, experiment entrypoints, a frozen advanced configuration, split code and nDCG evaluator.

The canonical dataset is [MovieLens 1M](https://grouplens.org/datasets/movielens/1m/), stable release February 2003. Its [provider README and terms](https://files.grouplens.org/datasets/movielens/ml-1m-README.txt) affirm research use subject to acknowledgement, no redistribution and no commercial/revenue-bearing use without permission.

The same paper surface binds Configuration 3 to Table 3. Frozen reference target: BPRMF `nDCG@50 = 0.2390` on MovieLens 1M after iterative 10-core prefiltering, a 20% random-subsampling test split and five-fold random-cross-validation model selection. The [author-hosted paper PDF](https://abellogin.github.io/2021/sigir.pdf) is the numeric result locator; exact recipe/evaluator locators are pinned in the candidate JSON.

Protocol caveat: this random holdout/CV, relevance-threshold and nDCG@50 surface is not v5's temporal novel-purchase full-catalog protocol. The number is only a future reproduction target and remains invalid as a project result.

## Proposal R3-FD1B-PROP-002 — DaisyRec 2.0

Status: `PLAUSIBLE_COMPLETE_PROPOSAL`

DaisyRec 2.0 is explicitly built for rigorous evaluation and fair comparison. The owner repository maps the paper's stable code to `main`; read-only GitHub metadata pinned it at `e9d0326457fb8aa138f7bb04ab751b17345cdb65`. That revision carries an MIT license and source-owned entrypoint, configuration, splitter, evaluator and hyperparameter appendix.

The suite directly links the same canonical MovieLens 1M provider and describes a source-owned time-aware split-by-ratio protocol: global `rho=80%`, latest 10% of training held out for validation, 30 Bayesian HyperOpt trials on NDCG@10, original model objective and uniform negative sampling. Its owner-hosted ranking documentation identifies revision `440c9553`; read-only metadata resolved the immutable result commit to `440c95534cbb21dd0f7b8a7d551bfddbfcb2422e`.

Frozen reference target: BPRMF on MovieLens 1M origin view under TSBR, `NDCG@10 = 0.5275`, from the [exact source-owned result blob](https://github.com/recsys-benchmark/DaisyRec-v2.0-Ranking_results/blob/440c95534cbb21dd0f7b8a7d551bfddbfcb2422e/docs/source/tsbr_results/BPRMF.rst). Best TSBR settings are bound by the code repository's appendix Tables 16–18.

Protocol caveat: DaisyRec's preprocessing, uniform negative sampler and evaluator are distinct from the v5 candidate/masking/eligibility contract. The target is for reference reproduction only; it cannot be compared directly with v5 metrics or copied into the paper as a project result.

## Fit to Stage 1E and handoff boundary

Both proposals are new repository/result surfaces relative to the seven archived R2 candidates. They implement familiar recommender families inside different benchmark-suite repositories; no old source bundle was reused and no repository–dataset–result cross-join was made. In each proposal, the suite itself points to MovieLens and binds its own recipe/evaluator to its own published or source-owned result table, while GroupLens supplies the release identity and terms.

The central composer and later FD2/FD3/FD4 lanes must independently replay all decision-bearing locators, verify exact data acquisition/rights, freeze environment details, test evaluator semantics and assess bounded adaptation to v5. This scout does not choose a winner and does not create an `R3-BUNDLE-*` identifier.

## Persistent truth state

```text
RESULT_STATUS=NOT_RUN
TEST_SET_OPENED=NO
ACCEPTED_RESULT_ROWS=0
execution_authorized=false
project_benchmark_numbers=INVALID_FOR_PAPER
```
