# Active & Locked Ablation Matrix (v5.0.0)

`v3.toml` (`deep_only`) and `v4.toml` (`hybrid`) are the **only active configs** in Pipeline v5.0.0.
`P0`–`P4` and `V0`–`V2` are preserved in Git history for audit diagnostics.

Every invocation must provide a unique run ID and must retain the generated `resolved-config.json` and training signature.
The production campaign is pinned to snapshot `benchmark-v3-20260810-9088b0f3`,
embedding `benchmark-v3-20260810-9088b0f3-real-f0453078fd58`, and full-stat rules
`benchmark-v3-20260810-9088b0f3-rules-v2-ea0c72a89c41`. The legacy rules artifact is
audit-only and must never be selected for training.

`v3.toml` and `v4.toml` share the same model, training, and evaluation settings. Their
only intentional difference is `training_variant` (`deep_only` versus `hybrid`). Use the
following exact production IDs; do not shorten them to `deep-42` or `hybrid-42`.

```powershell
# Deep seed 42, then Hybrid seed 42. Do not start either command before the source-freeze gate.
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --variant deep_only `
  --config configs/ablations/v3.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --run-id deep-42-v5 `
  --seed 42 `
  --device cuda

.\.venv\Scripts\python.exe -m ai_service.cli train `
  --variant hybrid `
  --config configs/ablations/v4.toml `
  --snapshot-id benchmark-v3-20260810-9088b0f3 `
  --run-id hybrid-42-v5 `
  --seed 42 `
  --device cuda
```

Evaluate the paired VAL result before training the next seed. Continue only when every
single-seed Victory Gate passes. Repeat the same Deep-then-Hybrid sequence for
`deep-2027-v5`/`hybrid-2027-v5` and `deep-31415-v5`/`hybrid-31415-v5`, then run the
3+3 validation release gate. TEST must be evaluated for all three pairs before the
aggregate TEST gate; a single validation winner is never a substitute.

The required order is therefore:

```text
deep-42-v5 → hybrid-42-v5 → VAL gate
deep-2027-v5 → hybrid-2027-v5 → VAL gate
deep-31415-v5 → hybrid-31415-v5 → VAL gate
aggregate VAL 3+3 → TEST for all three pairs → aggregate TEST 3+3
→ seal selected Hybrid → export/verify bundle
```

The complete command block is maintained in the root `ai-service/README.md`; do
not substitute shortened IDs or run a later seed after a failed gate.

Resume is allowed only for an `INTERRUPTED` run with the same config, seed, lineage, and exact
Git commit recorded in its run manifest. Do not change v3/v4 or tracked documentation after the
campaign source freeze; a changed source revision requires a new campaign review and run IDs.
