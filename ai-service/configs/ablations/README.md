# Archived ablations and active R3 promotion policy

`v3.toml` (`deep_only`) and `v4.toml` (`hybrid`) describe the archived v3
campaign. They remain in Git for audit and config-regression tests, but they are
not production commands and must not be used with the v4 benchmark lineage.
The archived data lineage is:

```text
snapshot:  benchmark-v3-20260810-9088b0f3
embedding: benchmark-v3-20260810-9088b0f3-real-f0453078fd58
rules:     benchmark-v3-20260810-9088b0f3-rules-v2-ea0c72a89c41
```

The active source campaign is pinned to:

```text
snapshot:  benchmark-v4-20260811-49b2cdb902b1
embedding: benchmark-v4-20260811-49b2cdb902b1-real-f0453078fd58
rules:     benchmark-v4-20260811-49b2cdb902b1-rules-v3-d7ba48f8b8b5
```

Production training is blocked because the first R3 selected Hybrid VAL
matrix failed. R3 uses the four Deep
diagnostic configs under `configs/diagnostics/r3/`, publishes a verified
immutable comparison artifact, and either selects exactly one feature-flag pair
or returns `diagnostic_pause=true`. Only the selected flags may be mirrored into
one Hybrid diagnostic. The selected Deep/Hybrid pair must then pass the VAL
Wide-signal and seven-gate contracts.

After R3 passes, create a new reviewed v5/v6 config pair in this directory. The
pair must be identical except for `training_variant`; it must bind the selected
`use_user_id_embedding` and `use_price_features` values. Do not modify archived
`v3.toml`/`v4.toml` and do not create production run IDs before this promotion.

The authoritative commands, exact diagnostic IDs, stop conditions, and
promotion checklist are maintained in
[`master/detail-plan.md`](../../../master/detail-plan.md). The root
[`README.md`](../../README.md) intentionally contains no executable archived-v3
training command.

Resume is allowed only for an `INTERRUPTED` run with the same config, seed,
lineage, and exact Git commit recorded in its run manifest. Do not edit tracked
source, configs, or documentation between frozen diagnostic or production runs.
