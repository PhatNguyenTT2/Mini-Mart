# AI-service v5.0.0 — implementation verification

## Current status

`BLOCKED_BEFORE_PRODUCTION_TRAINING`.

Phase 0 provenance/lifecycle hardening is implemented and has passed the full
quality gate. Production training remains blocked until the resulting revision
is confirmed clean and synchronized with its upstream, the production
environment is configured, and the final readiness gate is rerun. No
production seed has been created.

Phase 5A–5D is complete. `Trainer.fit()` is now orchestration-only: it
preflights, restores state, delegates one epoch to `_train_epoch()`, validates,
applies stopping, publishes checkpoints/history, and writes the terminal
summary. Phase 0 additionally centralizes Git provenance, publishes lifecycle
directories atomically, locks resume to the recorded commit, and terminalizes
transition/setup failures. The production seed runs do not yet exist and Hybrid
victory is not established.

## Verification snapshot (2026-08-11)

- Full suite: **352 passed, 2 fixed-runner skips**.
- Phase 0 and campaign-freeze targeted contracts: **77 passed**.
- Branch coverage: **89.99%** (`--cov-branch`, threshold 85%).
- Critical files: checkpoint 97.24%, report 90.83%, bundle 98.79%, release
  90.85%, trainer 87.35%, pipeline 86.44%.
- Ruff format/check and mypy pass; `scripts/check_critical_coverage.py` passes.
- Static scans are clean: no Pareto/release-candidate checkpoints,
  `scores_by_user`, legacy Wide scaling, Softplus, or release signature
  fallbacks.

The locked snapshot remains `benchmark-v3-20260810-9088b0f3` with 823,371
events, 5,000 users, 5,200 items, and 250 cold items. Audit passed. Streaming
probe references remain permutation GAUC `0.501545`, Persona GAUC `0.782827`,
ItemCF GAUC `0.822937`, and SBERT NDCG@10 `0.014870`; parity tolerance is
`1e-6`.

The full-stat RuleArtifact
`benchmark-v3-20260810-9088b0f3-rules-v2-ea0c72a89c41` passed training
capability (`feature_schema_version=2.0.0`, 216 directed rules). The legacy
artifact remains audit-only and is rejected for training.

The production runbooks are now pinned to the same immutable lineage: snapshot
`benchmark-v3-20260810-9088b0f3`, embedding
`benchmark-v3-20260810-9088b0f3-real-f0453078fd58`, and the full-stat rules ID
above. The only production run IDs are `deep-42-v5`/`hybrid-42-v5`,
`deep-2027-v5`/`hybrid-2027-v5`, and `deep-31415-v5`/`hybrid-31415-v5`.

CUDA diagnostic smoke `smoke-v5-final-20260811-01` completed one epoch with
schema-v5 `best.pt` and `last.pt`, finite metrics, bfloat16 autocast, and no
evaluation/release/seal/export side effects. It is not a production seed.
`deep-42-v5` and `hybrid-42-v5` remain absent.

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

1. Confirm the Phase 0 revision is committed, pushed, clean, and identical to
   its upstream; then run the production-environment gate.
2. Train Deep seed 42, then Hybrid seed 42.
3. Evaluate the validation pair; stop immediately on any catastrophic signal,
   GAUC below 0.50, or failed single-seed Victory Gate.
4. Only after seed 42 passes, repeat Deep → Hybrid → validation for seeds 2027
   and 31415, then run aggregate validation 3+3 without sealing.
5. Evaluate TEST for all three pairs, run aggregate TEST, seal only the selected
   Hybrid, export and verify the v5 bundle.
6. Run ONNX parity and the fixed-runner benchmark. Only then may the document
   claim a Hybrid victory.

The source-level execution plan is maintained in
[`master/detail-plan.md`](master/detail-plan.md).
