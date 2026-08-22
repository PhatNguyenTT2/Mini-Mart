# R3-FD1A established-framework scout report

Status: `SCOUT_COMPLETE_NO_SELECTION`

Created: 2026-08-22 (web evidence checked through 2026-08-22)

Model profile: `Sol XHigh Standard` (`gpt-5.6-sol`, `reasoning_effort=xhigh`, `service_tier=standard`)

## Gate and scope receipt

The read-only FD0 validator returned `PASS_R3_FD0_GATE_17_OF_17_READY_FOR_FD1` with 17/17 checks passed. The scout then read the complete R3 change-control contract, candidate-bundle contract, supersession registry, FD1 recovery dispatch, FD1 scout contract, the Stage 1E/benchmark sections of the master plan, and the task/metric constraints in `inputs/idea.md` and `inputs/experimental_log.md`.

This lane searched only owner-maintained established recommender frameworks. Sources were restricted to owner GitHub surfaces, original publisher pages, and the canonical GroupLens provider/terms. Search snippets, forks, mirrors, blogs, and tutorials were not used to close fields. Search stopped after two strong proposals; it was not exhaustive.

## Proposal ledger

| Proposal | Framework surface | Same-surface reference target | Scout status |
| --- | --- | --- | --- |
| `R3-FD1A-PROP-001` | PreferredAI Cornac 2.6.0 at full SHA `42a327f26241790e99f56284e89c3ab903b69c45` | MovieLens 100K, shuffled 80/20 RatioSplit, BPR, NDCG@10 = 0.1500 | `PLAUSIBLE_COMPLETE_PROPOSAL` |
| `R3-FD1A-PROP-002` | LF AI & Data Recommenders at full SHA `6232b154548c955315650d58dca6bf1411c56020` | MovieLens 100K, stratified 75/25, LightGCN, NDCG@10 = 0.419100 | `PLAUSIBLE_COMPLETE_PROPOSAL` |

These numbers are owner-published external reproduction targets. They are not project results, were not reproduced by this scout, and cannot be compared with each other or with harmonized v5 because their protocols differ.

## R3-FD1A-PROP-001 — Cornac

Evidence:

- The [owner repository](https://github.com/PreferredAI/cornac) identifies Cornac as a comparative recommender framework, declares Apache-2.0, and publishes one executable quick-start that binds `load_feedback()`, `RatioSplit(test_size=0.2, rating_threshold=4.0, seed=123)`, BPR hyperparameters, the `Experiment` evaluator, ranking metrics, and the BPR output NDCG@10 = 0.1500.
- The [v2.6.0 release](https://github.com/PreferredAI/cornac/releases/tag/v2.6.0) binds to the [full immutable commit](https://github.com/PreferredAI/cornac/commit/42a327f26241790e99f56284e89c3ab903b69c45).
- The [owner license](https://github.com/PreferredAI/cornac/blob/master/LICENSE) is an affirmative Apache-2.0 grant. The [JMLR paper](https://www.jmlr.org/papers/v21/19-805.html) is the original framework publication.
- The dataset is the canonical [MovieLens 100K stable release](https://grouplens.org/datasets/movielens/100k/). Its [canonical terms](https://files.grouplens.org/datasets/movielens/ml-100k-README.txt) permit research use with acknowledgment, prohibit redistribution without separate permission, and prohibit commercial/revenue-bearing use without permission.
- Framework-owned loader, split, evaluator, and metric sources exist on the same repository surface. The split implementation confirms shuffling, the 0.2 default test proportion, rating threshold, seed, and exclusion of unknowns.

Inference:

The owner README and code surface plausibly bind all required fields at the verified release revision, so this is retained as a plausible complete proposal. It is not admitted or selected: direct web replay of several full-SHA blob URLs cache-missed, and byte-level equivalence between the framework-served MovieLens payload and canonical `ml-100k.zip` remains unresolved.

Protocol limitations:

- The reference recipe is shuffled, not temporal.
- Candidate-universe construction, seen-item masking, score-tie handling, and exact per-user aggregation are not completely stated in the README.
- A downstream verifier must replay the pinned blobs, establish dataset-byte lineage, and perform only an authorized reference replay before any adapter decision.

## R3-FD1A-PROP-002 — Recommenders

Evidence:

- The [owner repository](https://github.com/recommenders-team/recommenders) is an LF AI & Data framework and publishes a MovieLens benchmark notebook plus a current result table. The table binds MovieLens 100K, a 75/25 stratified split, k=10, and LightGCN NDCG@10 = 0.419100.
- The [owner commit history](https://github.com/recommenders-team/recommenders/commits/main/) resolves the [full immutable commit](https://github.com/recommenders-team/recommenders/commit/6232b154548c955315650d58dca6bf1411c56020). That merged history records evaluator corrections, LightGCN refactoring, notebook reruns, and benchmark-argument fixes.
- The [owner license](https://github.com/recommenders-team/recommenders/blob/main/LICENSE) is an affirmative MIT grant. The owner README identifies the original [ACM WWW 2020 framework paper](https://dl.acm.org/doi/10.1145/3366424.3382692); direct publisher replay returned HTTP 403 and remains unresolved rather than being filled from a secondary source.
- The [benchmark notebook](https://github.com/recommenders-team/recommenders/blob/main/examples/06_benchmarks/movielens.ipynb), [MovieLens loader](https://github.com/recommenders-team/recommenders/blob/main/recommenders/datasets/movielens.py), [splitters](https://github.com/recommenders-team/recommenders/blob/main/recommenders/datasets/python_splitters.py), and [Python evaluator](https://github.com/recommenders-team/recommenders/blob/main/recommenders/evaluation/python_evaluation.py) are source-owned and colocated with the result table.
- Dataset release and terms are the same canonical GroupLens MovieLens 100K release recorded above.

Inference:

The owner repository plausibly binds conversion, stratified split, training/configuration notebook, evaluator, and numeric target at a verified full SHA. The proposal remains only plausible because the full-SHA notebook and README URLs cache-missed in web replay; exact parameter cells, dependency lock, seed/run aggregation, and evaluator semantics must be verified downstream.

Protocol limitations:

- The reference split is random stratified, not temporal.
- The README does not completely expose the candidate universe, seen-item masking, score-tie handling, or seed/run aggregation.
- The owner reports specific benchmark hardware; runtime measurements are not targets for Stage 1E.
- No result can enter the paper until the pinned reference protocol and later harmonized-v5 adapter protocol are separately executed under authorization.

## Supersession and non-cross-join check

Neither proposal reuses the seven old candidate surfaces or their repositories: `gusye1234/LightGCN-PyTorch`, `Coder-Yu/QRec`, `Coder-Yu/SELFRec`, `HKUDS/LightGCL`, `RUCAIBox/UniSRec`, or `LehengTHU/AlphaRec`. Recommenders and Cornac are new framework-level bundles. Although model families overlap with prior work, no old source repository, configuration, dataset recipe, evaluator, or result was imported.

Each numeric target is kept with its own framework recipe and evaluator. No repository-A/dataset-recipe-B/result-C cross-join was performed. The canonical GroupLens provider and terms are used only because each owner framework expressly names MovieLens 100K on its own benchmark surface.

## Handoff constraints

No winner was selected and no final `R3-BUNDLE` ID was created. Downstream verification should first replay every pinned blob, confirm dataset checksum/lineage and terms, extract all hidden notebook/config semantics, and then decide whether an isolated adapter can reproduce the owner protocol before any separate temporal/full-catalog v5 evaluation.

Truth state remains:

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- `project_benchmark_numbers=INVALID_FOR_PAPER`

No repository/source/data/checkpoint was cloned, fetched, or downloaded; no environment or dependency was installed; no preprocessing, training, evaluation, TEST access, maintainer contact, selection, `git add`, or commit occurred.
