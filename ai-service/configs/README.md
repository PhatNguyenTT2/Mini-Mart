# Model configurations

Registry specifications for the models in `hybrid_recsys.models`: `random`, `mostpop`,
`rule-only`, `deep-two-tower` and `hybrid`. Each file is strict JSON and is validated by
`hybrid_recsys.models.registry`. Changing a weight, the normalization, the rule support or the
feature dimensions changes the model descriptor hash.

The `hybrid` entry applies a per-user z-score normalization to both branches before additive
fusion. `deep-two-tower` and `hybrid` use the deterministic hash-feature item encoder.
