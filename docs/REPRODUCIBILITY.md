# Reproducibility check

This pipeline replaces an earlier set of one-off research scripts. To show that the rewrite changes
no result, stages 4 and 5 were rerun from scratch on the same prepared inputs, and the resulting
`freeze.json` was compared with the freeze the earlier scripts produced.

## Scope

- **VALIDATION only.** The comparison uses stage 4 results and the stage 5 freeze. TEST was not
  opened. Stage 6 ran with `--dry-run` only, which scores VALIDATION and prints no metric.
- **Same inputs.** Same snapshot, item features (with the same `feature_identity`) and pair-rule
  table as the earlier run, verified by their manifest hashes.
- **Same settings.** Default `configs/pipeline/example.json` values: seeds 42, 2027 and 31415, the
  λ grid {0.25, 0.5, 1, 2}, the W&D wide learning-rate grid {0.001, 0.01}, and the default epoch
  budgets and patience.

## Environment

Windows 11, Python 3.11, one NVIDIA RTX 3060 Laptop GPU (6 GB), CUDA 12.1 build of
`torch==2.2.2`, `recbole==1.2.1`, `numpy<2`, `scipy<1.13`, `pandas<2.3`. Install with
`pip install -e ".[dev,baselines,train]"`, using the CUDA wheel index for torch. The full stage 4
run took about 1 h 45 min on this GPU.

## Criteria

| Check | Required |
|-------|----------|
| Selected λ | identical |
| Selected W&D wide learning rate | identical |
| Validation NDCG@10 of every method (seed mean) | absolute difference ≤ 0.002 |

## Outcome

All criteria were met. The results were closer than the tolerance requires:

- λ and the wide learning rate were selected identically. The λ selection values (mean NDCG@10
  per λ) were identical.
- For all eight methods (MostPop, ItemKNN, Rule-only, BPR-MF, LightGCN, Deep-only, W&D, Hybrid),
  validation NDCG@10 per seed was identical, and so was the best epoch of every trained unit. The
  largest difference on any validation metric (NDCG@10, HR@10, GAUC) was about 1e-9, in GAUC.
- The cohort counts and the candidate-order hash were identical.
- The Deep, W&D and BPR-MF checkpoints were byte-identical (same SHA-256). The LightGCN
  checkpoints had different hashes but gave identical validation metrics.

## Deviations

- **Dependency pins.** `torch==2.2.2` wheels are built against NumPy 1.x, and RecBole 1.2.1
  LightGCN calls a SciPy sparse-matrix API removed in SciPy 1.13. Without the pins `numpy<2`,
  `scipy<1.13` and `pandas<2.3`, stage 4 fails (it does not change results).
- **LightGCN checkpoint bytes.** RecBole runs with PyTorch deterministic mode turned off (the
  pipeline does this before building RecBole models). The saved LightGCN state differed in bytes
  while every evaluated ranking was the same. Stage 8 re-scores from checkpoints, so a later TEST
  run uses whatever checkpoint stage 5 hashed.
- **Stage 6 used `--dry-run` only.** It loaded every frozen checkpoint and produced 18 finite score
  sets on VALIDATION.

## Repeating the check

```
cd pipeline
python 04_train_validate.py --config <cfg>
python 05_freeze.py        --config <cfg>
python 06_score_test.py    --config <cfg> --dry-run
```

Then compare `selected`, `selection_values` and `validation.*` of the new `freeze.json` with the
reference freeze. The synthetic end-to-end test (`tests/test_pipeline_end_to_end.py`) covers
stages 4 to 8 on CPU, including the TEST open guards.
