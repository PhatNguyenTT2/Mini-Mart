# POSMart AI Service

The only supported Python package is `src/ai_service`. Root-level Python modules, v1 checkpoints,
v1 ONNX graphs, compatibility shims, and the mutable `runs/main` convention are unsupported.

## Data and security contracts

Production training accepts only a published PostgreSQL benchmark run and real SBERT embeddings.
`synthetic` and `mock` adapters are explicit test inputs and are rejected when `AI_ENV=production`.
Remote PostgreSQL connections use `sslmode=verify-full`; download the project CA from the Supabase
Dashboard SSL configuration and set `SUPABASE_DB_CA_PATH` to the absolute PEM/CRT path. Disabling
certificate verification is not supported.

The Vietnamese encoder is pinned to:

```text
keepitreal/vietnamese-sbert@a9467ef2ef47caa6448edeabfd8e5e5ce0fa2a23
```

The Windows training lock resolves Torch 2.11 from the official CUDA 12.8 index. Linux CI and the
serving image resolve CPU-only dependencies; the serving dependency group contains no Torch,
Sentence Transformers, CUDA, or compiler toolchain.

## Rebuild and training

Run the database preflight before the explicitly confirmed store-scoped rebuild:

```powershell
node ..\backend\docs\chatbot\seed-product\seed-ml-benchmark.js `
  --store-id 1 --seed 42 --preflight-only

node ..\backend\docs\chatbot\seed-product\seed-ml-benchmark.js `
  --store-id 1 --seed 42 --confirm-rebuild

.\.venv\Scripts\python.exe `
  ..\backend\docs\chatbot\seed-product\validate_semantic_traps.py `
  --store-id 1 --strict
```

Install the immutable environment, materialize the shared lineage once, then train
and evaluate each finalist seed against that exact snapshot. `run-all` is a
single-seed smoke/orchestration command and deliberately cannot export an
unapproved run:

```powershell
uv sync --frozen --extra train --extra export --extra dev
.\.venv\Scripts\python.exe -m ai_service.cli snapshot --source postgres --store-id 1 `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --benchmark-run-id <published-benchmark-run-id>
.\.venv\Scripts\python.exe -m ai_service.cli features --embedding-source real `
  --snapshot-id benchmark-v3-20260810-9088b0f3
# Reuse these immutable, verified artifacts when their lineage/config identity matches:
#   embedding: benchmark-v3-20260810-9088b0f3-real-f0453078fd58
#   rules:     benchmark-v3-20260810-9088b0f3-rules-v2-ea0c72a89c41
# Run the rules command only when the full-stat artifact above is absent; never overwrite it.
.\.venv\Scripts\python.exe -m ai_service.cli rules `
  --snapshot-id benchmark-v3-20260810-9088b0f3

.\.venv\Scripts\python.exe -m ai_service.cli train `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --run-id deep-42-v5 `
  --variant deep_only --config configs\ablations\v3.toml --seed 42 --device cuda
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --snapshot-id benchmark-v3-20260810-9088b0f3 --run-id hybrid-42-v5 `
  --variant hybrid --config configs\ablations\v4.toml --seed 42 --device cuda
.\.venv\Scripts\python.exe -m ai_service.cli evaluate --split val --hybrid-run-id hybrid-42-v5 `
  --deep-run-id deep-42-v5 --device cuda

# Repeat the paired Deep/Hybrid train + VAL evaluate commands for 2027 and 31415:
# deep-2027-v5 / hybrid-2027-v5, then deep-31415-v5 / hybrid-31415-v5.
.\.venv\Scripts\python.exe -m ai_service.cli release-gate --split val `
  --hybrid-run-ids hybrid-42-v5 hybrid-2027-v5 hybrid-31415-v5 `
  --deep-run-ids deep-42-v5 deep-2027-v5 deep-31415-v5

# Evaluate TEST for every finalist pair (not only the validation winner).
.\.venv\Scripts\python.exe -m ai_service.cli evaluate --split test --hybrid-run-id hybrid-42-v5 `
  --deep-run-id deep-42-v5 --device cuda
.\.venv\Scripts\python.exe -m ai_service.cli evaluate --split test --hybrid-run-id hybrid-2027-v5 `
  --deep-run-id deep-2027-v5 --device cuda
.\.venv\Scripts\python.exe -m ai_service.cli evaluate --split test --hybrid-run-id hybrid-31415-v5 `
  --deep-run-id deep-31415-v5 --device cuda
.\.venv\Scripts\python.exe -m ai_service.cli release-gate --split test `
  --hybrid-run-ids hybrid-42-v5 hybrid-2027-v5 hybrid-31415-v5 `
  --deep-run-ids deep-42-v5 deep-2027-v5 deep-31415-v5
.\.venv\Scripts\python.exe -m ai_service.cli export --run-id <selected-hybrid-run-id> --device cuda
.\.venv\Scripts\python.exe -m ai_service.cli verify-bundle --run-id <selected-hybrid-run-id>
```

The aggregate TEST gate requires evaluation artifacts for all three paired seeds; a single
validation winner is not a substitute for the other two TEST pairs. `run-all` remains synthetic/
mock smoke only: it trains one bounded epoch and never publishes evaluation, release, seal, or
bundle artifacts.

Every stage is fail-closed. A snapshot, SBERT, training, evaluation, parity, or metric-gate failure
cannot silently switch adapters or publish a serving bundle.

The locked ablation definitions and their execution order are documented in
`configs/ablations/README.md`. Data diagnostics are available through
`.\.venv\Scripts\python.exe -m ai_service.cli audit-data` and
`.\.venv\Scripts\python.exe -m ai_service.cli probe-data` before any training run.

## Serving

Serving loads one immutable bundle from the absolute `AI_MODEL_BUNDLE_PATH`, verifies every SHA-256
checksum, creates one ONNX Runtime session per process, and performs no database read on the request
path.

```powershell
uv sync --frozen --extra serve
$env:AI_ENV = "production"
$env:AI_ARTIFACT_ROOT = "E:\models"
$env:AI_MODEL_BUNDLE_PATH = "E:\models\current"
$env:AI_STORE_ID = "1"
uv run ai-serve
```

Endpoints are `/health/live`, `/health/ready`, `/health`, `/recommend`, and `/metrics`. Missing or
corrupt bundles keep liveness available while readiness returns HTTP 503.

## Verification

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
.\.venv\Scripts\python.exe -m pytest --cov=ai_service --cov-branch --cov-fail-under=85 -q
```

Fixed-hardware serving benchmarks require an already verified bundle:

```powershell
$env:AI_BENCHMARK_BUNDLE_PATH = "E:\models\current"
.\.venv\Scripts\python.exe -m pytest tests\benchmark -q
```

Generated files use immutable namespaces: `artifacts/snapshots/<snapshot-id>`,
`artifacts/runs/<run-id>`, and `artifacts/bundles/<bundle-id>`.
