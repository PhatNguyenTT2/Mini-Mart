# POSMART AI Service

Recommendation core for Mini-Mart. The package `hybrid_recsys` implements a **decoupled Hybrid**
recommender: a two-tower Deep branch and an association-rule branch, fitted separately and fused
at score level. It also includes MostPop, Rule-only and Wide&Deep baselines and a full-catalog
evaluator.

> **Status:** library only. HTTP serving, the Docker image and the model bundle are not built yet,
> so the chatbot runs on its built-in fallback. See [`../docs/ai-service.md`](../docs/ai-service.md)
> for the integration roadmap.

The research pipeline that trains and evaluates these models lives on the `paper` branch.

## Layout
| Path | Content |
|------|---------|
| `src/hybrid_recsys/models/` | `proposed.py` (Hybrid, Rule-only, Deep two-tower), `confirmatory.py` (streaming Hybrid fusion), `wd_original.py` (Wide&Deep), `baselines.py`, `registry.py` |
| `src/hybrid_recsys/data/` | Canonical snapshot I/O, Apriori/pair rule tables, negative sampling, suitability checks |
| `src/hybrid_recsys/evaluation/` | Ranking metrics (NDCG@10, HR@10, GAUC), full-catalog evaluator, score artifacts |
| `src/hybrid_recsys/statistics/` | Paired bootstrap and Holm correction |
| `src/hybrid_recsys/storage.py` | Write-once, size-capped storage for score chunks and manifests |
| `configs/` | Model specs (`hybrid.json`, `deep-two-tower.json`, `rule-only.json`, ...) |
| `tests/` | Unit tests on the `fixture-retail-v1` fixture |

## Develop
```bash
cd ai-service
python -m pip install torch==2.2.2 "numpy<2" --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
python -m pip install -e ".[dev]"
ruff check src tests && ruff format --check src tests
pytest -q
```
