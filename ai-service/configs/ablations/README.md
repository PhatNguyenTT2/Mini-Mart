# Archived ablations and v5 R3/R4 promotion policy

`v3.toml` (`deep_only`) and `v4.toml` (`hybrid`) describe the archived v3
campaign. They remain in Git for audit and config-regression tests, but they are
not production commands and must not be used with the v4 benchmark lineage.
The archived data lineage is:

```text
snapshot:  benchmark-v3-20260810-9088b0f3
embedding: benchmark-v3-20260810-9088b0f3-real-f0453078fd58
rules:     benchmark-v3-20260810-9088b0f3-rules-v2-ea0c72a89c41
```

The v4 source campaign is also archived. The active source campaign is the
newly seeded v5 lineage selected by R0-R2 readiness; its snapshot/rule IDs are
recorded in the immutable snapshot manifest, never inferred from these files.

Production training is blocked until R3/R4 pass. R3 uses the four Deep
diagnostic configs under `configs/diagnostics/r3-v5/`, publishes a verified
immutable comparison artifact, and either selects exactly one feature-flag pair
or returns `diagnostic_pause=true`. Only the selected flags may be mirrored into
the five Hybrid diagnostics (`h0`, `h1`, `h2`, `h3a`, `h3b`), each configured
with `r3_feature_selection_mode="selection_artifact"`. The selected Deep/Hybrid
pair must then pass the VAL Wide-signal and seven-gate contracts.

After R3 passes, create a new reviewed production config pair in
`configs/production/`. The
pair must be identical except for `training_variant`; it must bind the selected
`use_user_id_embedding` and `use_price_features` values. Do not modify archived
`v3.toml`/`v4.toml` and do not create production run IDs before this promotion.

The authoritative commands, exact diagnostic IDs, stop conditions, and
promotion checklist are maintained in
[`master/detail-plan-r3-r4.md`](../../../master/detail-plan-r3-r4.md). The root
[`README.md`](../../README.md) intentionally contains no executable archived-v3
training command.

Resume is allowed only for an `INTERRUPTED` run with the same config, seed,
lineage, and exact Git commit recorded in its run manifest. Do not edit tracked
source, configs, or documentation between frozen diagnostic or production runs.
