# Locked ablation matrix

`P0`–`P4` run on the immutable audit-reference snapshot. `V0`–`V4` run on the
new benchmark-v3 snapshot. Every invocation must provide a unique run ID and
must retain the generated `resolved-config.json` and training signature.

```powershell
$matrix = @('p0','p1','p2','p3','p4','v0','v1','v2','v3','v4')
foreach ($id in $matrix) {
  $snapshot = if ($id.StartsWith('p')) { $env:AI_CURRENT_SNAPSHOT_ID } else { $env:AI_V3_SNAPSHOT_ID }
  uv run ai-pipeline train `
    --config "configs/ablations/$id.toml" `
    --snapshot-id $snapshot `
    --run-id "ablation-$id-s42" `
    --seed 42 `
    --device cuda
}
```

Finalists are selected from validation reports only. Freeze each finalist's
training signature, then repeat it with seeds `42`, `2027`, and `31415` before
opening test metrics.

