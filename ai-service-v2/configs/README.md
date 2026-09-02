# Local model configurations

These files are registry specifications for fixture and future validation-only
runs. They do not contain an environment lock, a dataset snapshot, a
checkpoint, or an empirical result. A paper run must copy the selected
specification into its immutable run namespace and bind its canonical hash in
the run manifest.

The `deep_two_tower` and `hybrid` entries currently use the deterministic
hash-feature encoder as the bounded AIS-R5 candidate transform. Its feature
bytes are hash-bound, but it remains unadmitted for a paper run until the R5
model-scope audit accepts the transform and the validation-only runtime packet.
The Hybrid entry preregisters per-user z-score normalization before additive
fusion; changing the normalization, weight, rule support, or feature dimensions
changes the model descriptor hash.
