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
uv run ai-pipeline snapshot --source postgres --store-id 1 `
  --snapshot-id benchmark-v3 --benchmark-run-id <published-benchmark-run-id>
uv run ai-pipeline features --embedding-source real --snapshot-id benchmark-v3
uv run ai-pipeline rules --snapshot-id benchmark-v3

uv run ai-pipeline train --snapshot-id benchmark-v3 --run-id finalist-42 `
  --config configs\ablations\v4.toml --seed 42 --device cuda
uv run ai-pipeline evaluate --run-id finalist-42 `
  --config configs\ablations\v4.toml --seed 42 --device cuda

uv run ai-pipeline train --snapshot-id benchmark-v3 --run-id finalist-2027 `
  --config configs\ablations\v4.toml --seed 2027 --device cuda
uv run ai-pipeline evaluate --run-id finalist-2027 `
  --config configs\ablations\v4.toml --seed 2027 --device cuda

uv run ai-pipeline train --snapshot-id benchmark-v3 --run-id finalist-31415 `
  --config configs\ablations\v4.toml --seed 31415 --device cuda
uv run ai-pipeline evaluate --run-id finalist-31415 `
  --config configs\ablations\v4.toml --seed 31415 --device cuda

uv run ai-pipeline release-gate `
  --run-ids finalist-42 finalist-2027 finalist-31415 `
  --config configs\ablations\v4.toml

uv run ai-pipeline export --run-id <selected-run-id> `
  --config configs\ablations\v4.toml
uv run ai-pipeline verify-bundle --bundle-id <bundle-id>
```

Every stage is fail-closed. A snapshot, SBERT, training, evaluation, parity, or metric-gate failure
cannot silently switch adapters or publish a serving bundle.

The locked ablation definitions and their execution order are documented in
`configs/ablations/README.md`. Data diagnostics are available through
`ai-pipeline audit-data` and `ai-pipeline probe-data` before any training run.

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
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src
uv run pytest --cov=ai_service --cov-fail-under=85 -q
```

Fixed-hardware serving benchmarks require an already verified bundle:

```powershell
$env:AI_BENCHMARK_BUNDLE_PATH = "E:\models\current"
uv run pytest tests\benchmark -q
```

Generated files use immutable namespaces: `artifacts/snapshots/<snapshot-id>`,
`artifacts/runs/<run-id>`, and `artifacts/bundles/<bundle-id>`.
