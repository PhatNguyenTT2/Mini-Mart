# E4-R1C Cross-Dataset Reporting Contract

> Material Passport: `stage1e_rebaseline_v2_wave_e_e4_r1c_cross_dataset_reporting_contract` · status `UNVERIFIED`  
> Origin: `ars-codex:academic-research-suite/experiment-agent` · mode `central-synthesis/freeze-only` · date `2026-08-22`  
> Empirical state: `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`.

## 1. Purpose

This contract prevents a numerically convenient but scientifically invalid comparison across different datasets, splits, candidate universes, evaluators, checkpoints, or metric definitions. The current project has no accepted benchmark row; all numerical centers in the evidence packet are source-reported targets, not project results.

## 2. Non-interchangeable reporting scopes

Every future result row must belong to exactly one scope.

### Scope O — official-source reproduction

Purpose: test whether an exact source implementation reproduces its own source-bound center.

Required row identity:

- method and candidate-row ID;
- repository URL and full commit;
- source dataset provider/release/rights, raw and processed hashes, split ID/hash;
- source model argv/config/seed/checkpoint/sampler;
- source candidate universe, masks, tie policy, evaluator, metric, cutoff, and averaging unit;
- source-reported center, locator, frozen tolerance, reproduced value, absolute delta, and pass/fail rule;
- run/evaluator/receipt hashes.

Only the corresponding source center may be used as the reproduction target. A center from another implementation, layer count, sampler, task, batch regime, dataset, or evaluator is a prohibited join.

### Scope V — harmonized v5 evaluation

Purpose: compare eligible methods under one frozen v5 data and evaluator seam.

Required row identity:

- frozen v5 benchmark specification path `backend/docs/chatbot/seed-product/benchmark-spec-v5.json`;
- canonical-LF SHA-256 `acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d`;
- one dataset snapshot and split identity;
- one candidate/mask/tie contract;
- one adapter/evaluator identity and hash;
- metric/cutoff/averaging/denominator contract;
- exact run, prediction, adapter, evaluator, and receipt hashes.

Only rows sharing every harmonization key may appear in the same comparative block.

### Scope X — external validation

Purpose: assess transfer or robustness on a separately eligible external dataset and protocol.

Required row identity includes canonical provider/release/rights/hash, task and identity compatibility, frozen external split/protocol, independently justified metrics, and complete lineage and receipts. An anonymous-session dataset cannot silently substitute for a persistent-user/order/basket external contract.

### Scope F — framework reference assessment

Purpose: document useful official framework configurations or reported centers that do not yet form an exact reproduction lock.

MovieLens 1M/10M framework references remain in this scope until their result-bound seed/run/checkpoint, dependency, split-lineage, candidate/tie, and evaluator identities are closed. Scope F rows are context, not project benchmark rows.

## 3. Join key

Two numerical rows may be compared as a direct performance contrast only when this complete key is equal:

`{scope, task, dataset_provider, release, raw_hash_set, transformation_commit, split_hash, candidate_universe, mask_policy, tie_policy, method_variant, checkpoint_rule, evaluator_hash, metric_formula_version, cutoff, averaging_unit, denominator_rule}`

A shared metric label such as `Recall@20` or `NDCG@20` is not sufficient. If any key component is unknown, different, or inferred, the rows cannot enter the same league table.

## 4. Current prohibited joins

The following five joins remain explicitly rejected:

1. LightGCL's current Appendix E interaction-sampler command with older Table 1 centers;
2. XSimGCL's three-layer repository configuration with a four-layer paper center;
3. the public Mask-Swap item-selection/batch-64 command with BTBR Table 5 joint-task/batch-128 centers;
4. the LightGCN PyTorch README command with a center from a different implementation or paper pipeline;
5. any official-source metric used as evidence of superiority on the harmonized v5 seam.

Correcting the SimGCL paper identity or the v5 specification path does not legalize any prohibited join.

## 5. Allowed table design

Future paper tables must be separated by scope and carry enough columns to make the evaluation seam visible.

### Official reproduction table

Minimum columns:

`candidate row | source commit | source dataset/split | source evaluator | metric/cutoff/unit | reported center | frozen tolerance | reproduced value | delta | receipt | status`

This table answers reproducibility only. It does not rank the current method against unrelated source centers.

### Harmonized v5 table

Minimum columns:

`method variant | v5 spec hash | dataset snapshot/split | adapter/evaluator hash | candidate/tie contract | seeds/runs | metric/cutoff/unit | center | dispersion/CI | receipt | status`

All compared rows must share the full join key. Seed-level outcomes and aggregation rules must be retained.

### External-validation table

Minimum columns:

`external dataset/release/hash | task/identity fit | split/protocol | method variant | evaluator hash | metric/cutoff/unit | center | uncertainty | limitations | receipt | status`

The table must be labeled external validation or sensitivity analysis, never merged with official reproduction or v5 benchmarking.

### Framework-reference table

Minimum columns:

`framework | dataset | documented protocol | reported center | missing locks | evidence locator | status`

No project-generated result or superiority conclusion may be implied.

## 6. Missingness and eligibility

- Ineligible rows are shown as `INELIGIBLE` with a reason, not zero.
- Not-run rows are shown as `NOT_RUN`, not blank and not zero.
- Missing evidence is shown as `PENDING_EVIDENCE` with blockers.
- Failed runs, if ever authorized, remain failed and are not silently retried, tuned, or omitted.
- No best-value highlighting, ranking, mean, or percentage gain is computed across incompatible or missing rows.
- A rejected join remains rejected; it is not repaired by choosing a different tolerance.

## 7. Statistical and numerical reporting

When harmonized comparison eventually becomes valid:

- predeclare seed count, seed values, aggregation unit, center statistic, dispersion, and confidence-interval method;
- retain seed-level and run-level receipts;
- distinguish tolerance for reproducing a reported center from uncertainty around a new estimate;
- report exact sample and eligible-subject counts per metric;
- use paired analysis only when methods share the exact same evaluation units and split;
- do not interpret non-overlapping point estimates as significance without a preregistered inferential procedure;
- disclose exclusions, failed runs, resource limits, and deviations.

Source-provided tolerances in the candidate registry are frozen reproduction acceptance bands, not newly estimated confidence intervals.

## 8. Paper-use gate

A numerical row is eligible for manuscript Results, Abstract, Introduction claims, or Conclusion claims only if:

1. the row belongs to one declared scope;
2. every identity and hash required by that scope is present;
3. its command packet was independently audited, explicitly confirmed, separately authorized, and executed without retry or unapproved deviation;
4. all receipts and final manifest strict-validate;
5. the row is marked accepted by a post-execution audit;
6. limitations and scope labels remain attached.

At present, none of these conditions is met for a project-generated benchmark. All project benchmark numbers remain `INVALID_FOR_PAPER`.

## 9. Current scope status

| Scope | Current state | Direct comparison allowed? |
|---|---|---|
| official reproduction | 0 ready; 7 pending; 6 rejected | no |
| harmonized v5 | adapter/evaluator and candidate bindings null | no |
| external validation | no dataset passes the frozen full contract | no |
| framework reference | evidence context only | no project comparison |

## 10. Audit rule

The future E5-R1 auditor must fail the packet if it finds a raw cross-dataset leaderboard, an official-source center relabeled as a v5 result, hidden missingness, a prohibited join, or a comparison whose complete join key is not equal. The auditor may not repair the table; remediation belongs to E4.

