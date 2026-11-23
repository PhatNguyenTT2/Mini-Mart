# Hybrid Recommender Research Pipeline

This branch holds the standard research pipeline for the recommendation model used by Mini-Mart:
data generation, training and validation, configuration freeze, one-time TEST scoring, and
statistical verification. The Mini-Mart application lives on `main`.

**Model.** `hybrid_recsys` implements a *decoupled Hybrid* for novel-purchase recommendation (items
a customer has not bought before). It has two branches, fitted separately and combined only at
score level:
- a **Deep** branch in the two-tower layout (user tower with history, item tower with text and
  category features),
- an **association-rule** branch (pairwise co-purchase rules mined from TRAIN baskets).

Both branches are z-scored per user over the unseen candidates and summed with weight λ.

**Comparators.** MostPop, ItemKNN (with and without the extra history the Hybrid sees), BPR-MF,
LightGCN, Wide&Deep, and the two Hybrid branches on their own.

## Layout
| Path | Content |
|------|---------|
| `src/hybrid_recsys/` | Library: data I/O, rule tables, models, full-catalog evaluator, bootstrap/Holm, training loops |
| `pipeline/` | The eight stages (`01_…` to `08_…`) and their shared helpers |
| `configs/*.json` | Model specifications validated by `hybrid_recsys.models.registry` |
| `configs/pipeline/example.json` | Pipeline configuration template (data paths, seeds, grids, gates) |
| `tests/` | Unit tests on a small fixture dataset |
| `docs/PIPELINE.md` | What each stage does, its inputs and outputs, and the evaluation rules |

## Quick start
```bash
python -m pip install torch==2.2.2 "numpy<2" --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
python -m pip install -e ".[dev,baselines]"
pytest -q

cp configs/pipeline/example.json configs/pipeline/local.json   # point it at your data
cd pipeline
python 04_train_validate.py --config ../configs/pipeline/local.json --smoke
```

Datasets, checkpoints and run outputs are never committed. Each stage writes under the configured
`work_root`.
