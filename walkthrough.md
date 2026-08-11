# AI-service v5.0.0 — implementation verification

## Current status

`R3_DIAGNOSTIC_FAILED / PRODUCTION_TRAINING_BLOCKED`.

R1 source contracts and R2 seed/data readiness are complete. The real v4
database seed, snapshot, embedding, RuleArtifact, audit, probes and epoch-one
rule scan pass. Legacy duplicate seed spec/validator sources have been removed,
and the four Deep diagnostics plus the selected Hybrid diagnostic have run on
the frozen source. R3 is blocked because the selected Hybrid VAL matrix failed
dominance and semantic-trap gates; no v5/v6 promotion or production training
is permitted.

Phase 5A–5D is complete. `Trainer.fit()` is now orchestration-only: it
preflights, restores state, delegates one epoch to `_train_epoch()`, validates,
applies stopping, publishes checkpoints/history, and writes the terminal
summary. Phase 0 additionally centralizes Git provenance, publishes lifecycle
directories atomically, locks resume to the recorded commit, and terminalizes
transition/setup failures. The production seed runs do not yet exist and Hybrid
victory is not established.

Final two-axis review is green: Standards and Spec both pass after closing the
archived-runbook conflict, R3 NPZ integrity binding, full rule-selector
thresholds, epoch reset, and immutable affinity contracts.

## Verification snapshot (2026-08-11, canonical benchmark v4)

- AI-service suite: **377 passed, 2 fixed-runner skips**; seed-product Node
  contracts **9 passed**.
- Branch coverage: **88.24%** (`--cov-branch`, threshold 85%).
- Critical files: checkpoint 97.24%, report 90.79%, bundle 98.79%, release
  90.22%, trainer 86.68%, pipeline 85.03%.
- Ruff format/check and mypy pass; `scripts/check_critical_coverage.py` passes.
- Root `backend npm test` is not green: pre-existing Catalog/Chatbot Jest suites
  fail outside the R2 seed-product files. This remains a monorepo gate blocker,
  while the seed-product contract suite itself is green.
- Static scans are clean: no Pareto/release-candidate checkpoints,
  `scores_by_user`, legacy Wide scaling, Softplus, or release signature
  fallbacks.

The v4 snapshot is `benchmark-v4-20260811-49b2cdb902b1`, SHA-256
`1eb1d07759a9e1ca6521794673e761b10bfc2919eb5018fa897d0a31f4b53fa6`,
with 823,371 events, 5,000 users, 5,200 items and 250 cold items. Audit passes.
Probe references are permutation GAUC `0.497918`, Persona GAUC `0.786681`,
ItemCF GAUC `0.827843`, SBERT NDCG@10 `0.012888`, and Apriori GAUC/NDCG
`0.514162`/`0.028210`. Apriori beats Random by paired CI for GAUC and NDCG.

The training-capable RuleArtifact is
`benchmark-v4-20260811-49b2cdb902b1-rules-v3-d7ba48f8b8b5`: 14,106 directed
rules, 14,086 non-trap, 20 trap-anchored, 4,143 organic items, VAL context
coverage `0.835377`, novel VAL rule-target alignment `0.076382`, and epoch-one
row coverage `0.690971`. Semantic trap readiness is `10/10` (75 baskets/count
per trap, lift 200).

The canonical database run is
`benchmark-v4-s42-7f40639b0d-ca692e71b3`, spec SHA
`ca692e71b3fa166dd9c5ae59405e3edb15efc554c19ac8b0b136e892cad0d7ce`.
An earlier execution exposed destructive legacy reclaim behavior and removed
the prior event lineage from the database. Local superseded artifacts remain
audit-only; they are not represented as complete database lineages. The source
now rejects duplicate run IDs before mutation and has immutability regression
tests.

The next campaign is pinned to the v4 snapshot above, embedding
`benchmark-v4-20260811-49b2cdb902b1-real-f0453078fd58`, and the canonical v3
RuleArtifact above. Planned production IDs are `deep-r4-42-v5`/
`hybrid-r4-42-v5`, `deep-r4-2027-v5`/`hybrid-r4-2027-v5`, and
`deep-r4-31415-v5`/`hybrid-r4-31415-v5`; none exists yet.

CUDA diagnostic smoke `smoke-r4-readiness-20260811-2042` completed one epoch with
schema-v5 `best.pt` and `last.pt`, finite metrics, bfloat16 autocast, and no
evaluation/release/seal/export side effects. It is not a production seed.
R3 diagnostics are retained as immutable audit evidence. The selected Deep
configuration is `deep-no-price-no-user-id` with best GAUC `0.772305854`.
The paired Hybrid diagnostic reached GAUC `0.775218972` and passed the minimum
GAUC/cold-parity checks, but failed ItemCF GAUC dominance, Persona HR
dominance, Apriori NDCG dominance and all `10/10` semantic traps. Its lifecycle
is `FAILED`; production seed IDs remain absent and R4 is blocked.

## R3 diagnostic result (2026-08-12)

Frozen source: `15860af0d5002297baf38e0df20f761332897700`.
Deep ablation receipt:
`12dcf8cbd6fe6f4bbcaf1a038e77d280484f94e34eca5db7d5544ef45d80ebd5`.
Selected Deep run: `diag-r3-deep-both-s42` (`GAUC=0.772305854`,
`HR@10=0.051477981`, `NDCG@10=0.010313758`).

Selected Hybrid run `diag-r3-hybrid-both-s42` (`GAUC=0.775218972`,
`HR@10=0.054092097`, `NDCG@10=0.011513037`) passed the absolute GAUC floor
and cold parity, but its VAL Victory Matrix failed:

- GAUC dominance: `0.775218972 < ItemCF 0.827843070`.
- HR dominance: `0.054092097 < Persona 0.080836517`.
- NDCG dominance: `0.011513037 < Apriori 0.028209886`.
- Semantic traps: `0/10`.

This is a legitimate model-quality failure, not a training crash. Do not
promote v5/v6, create production seed IDs, seal, export, or declare Hybrid
victory. The next phase must repair the objective/data-alignment issue and
rerun R3 on a new immutable campaign revision.

## Quality commands

Run from `E:\UIT\cv\backend\ai-service`:

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
$coverageJson = Join-Path $env:TEMP "ai-service-phase5-final.json"
.\.venv\Scripts\python.exe -m pytest --cov=ai_service --cov-branch `
  --cov-report=term-missing --cov-report=json:$coverageJson `
  --cov-fail-under=85 -q
.\.venv\Scripts\python.exe scripts\check_critical_coverage.py $coverageJson
```

## Locked contracts

- `MODEL_SCHEMA_VERSION` is `5.0.0`; v4 checkpoints and bundles are rejected.
- Wide scoring is additive with a zero-initialized final layer; no Softplus or
  dynamic `_wide_logit_scale` remains.
- Early stopping is GAUC-primary with patience 4 and a catastrophic failure
  for non-finite validation metrics or `val_gauc < 0.50`.
- Full-catalog evaluation is streaming and shares one prepared split. Model-hard
  cache rows are Deep top-64 warm unseen IDs with row 0 set to `-1`.
- Evaluation artifacts are Hybrid-owned and bind the paired Deep checkpoint,
  lineage, comparison signature, per-user NPZ, and canonical Victory Matrix SHA.
- Aggregate release requires exact paired seeds `{42, 2027, 31415}` and test
  evaluation for all three pairs; only the selected Hybrid may be sealed.

## Next execution sequence

1. Review, commit and push the R1–R4 source/data-contract changes; require a
   clean worktree and `HEAD == upstream`.
2. Run four Deep R3 diagnostics on seed 42 and publish the immutable ablation
   comparison. Stop on `diagnostic_pause=true` or a missing selected run.
3. Train exactly one Hybrid diagnostic with the selected feature flags and
   evaluate it against the selected Deep run on VAL. Require Wide signal and
   all seven strengthened gates.
4. Promote the selected flags into new paired v5/v6 ablation configs, rerun
   quality/CUDA gates, then commit/push/freeze the final production revision.
5. Train production Deep → Hybrid → VAL for seed 42. Only after it passes,
   repeat for 2027 and 31415, aggregate VAL, evaluate TEST for all three pairs,
   and aggregate TEST.
6. Seal only the selected Hybrid, export/verify the bundle, run ONNX parity and
   the fixed-runner benchmark. Only then may the document claim Hybrid victory.

The source-level execution plan is maintained in
[`master/detail-plan.md`](master/detail-plan.md).
