# Local model configurations

These files are registry specifications for fixture and future validation-only
runs. They do not contain an environment lock, a dataset snapshot, a
checkpoint, or an empirical result. A paper run must copy the selected
specification into its immutable run namespace and bind its canonical hash in
the run manifest.

The `deep_two_tower` and `hybrid` entries use the deterministic hash-feature
encoder only as an AIS-R1 fixture implementation. It is not the source-bound
content encoder for the eventual paper benchmark.
