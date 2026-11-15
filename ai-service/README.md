# POSMART AI Service (core v2)

Recommendation core for Mini-Mart: the **decoupled Hybrid** model from the ICCIES 2027 paper. A
two-tower Deep branch and an association-rule branch are fitted separately, then fused at score
level. The service ships with MostPop, ItemKNN-style, Rule-only and Wide&Deep baselines, plus a
full-catalog evaluator.

> **Status:** library only. There is no HTTP serving, Dockerfile or model bundle yet, so the chatbot
> runs on its built-in fallback. See [`../docs/ai-service.md`](../docs/ai-service.md) for the
> integration roadmap.

## Origin
- Copied from `ai-service-v2/` on the `paper` branch (snapshot `b3ee632`). That snapshot is the code
  that produced the paper's numbers.
- Only the core modules and their unit tests were kept. Benchmark runners, cost profiling and
  TEST-custody tooling stay on `paper`.
- The Python package is still named `ai_service_v2`, so it can be traced back to the paper code.
  Renaming it to `ai_service` is part of the roadmap.
- The previous v1 service (FastAPI + ONNX) is retired. It is no longer in the tree.

## Layout
| Path | Content |
|------|---------|
| `src/ai_service_v2/models/` | `proposed.py` (Hybrid, Rule-only, Deep two-tower), `confirmatory.py` (streaming Hybrid fusion), `wd_original.py`, `baselines.py`, `registry.py` |
| `src/ai_service_v2/data/` | Canonical snapshot I/O, Apriori/pair rule tables, suitability checks |
| `src/ai_service_v2/evaluation/` | Ranking metrics (NDCG@10, HR@10, GAUC), full-catalog evaluator, score artifacts |
| `src/ai_service_v2/statistics/` | Paired bootstrap and Holm correction |
| `src/ai_service_v2/training/` | Only the storage/serialization helpers the evaluator needs (technical debt, see roadmap) |
| `configs/` | Model specs (`hybrid.json`, `deep-two-tower.json`, `rule-only.json`, ...) |
| `tests/` | 60 unit tests on the `fixture-retail-v1` fixture |

## Develop
```bash
cd ai-service
python -m pip install torch==2.2.2 "numpy<2" --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
python -m pip install -e ".[dev]"
ruff check src tests && ruff format --check src tests
pytest -q
```
