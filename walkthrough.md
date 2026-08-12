# AI-service v5 — implementation verification

## Current status

```text
SOURCE_IMPLEMENTATION_IN_PROGRESS
R3_CONTRACT_REPAIR_IN_PROGRESS
R4_DIAGNOSTIC_BLOCKED
PRODUCTION_TRAINING_BLOCKED
Hybrid victory not established
```

The current working tree contains the R3-C2 implementation: typed R3
preflight, fail-closed probes, snapshot-owned semantic cohort loading,
selection-report locking, candidate-failure isolation, six-field v5 lineage
checks, immutable R4 promotion receipt, and read-only training-run verifier.
These changes are not source-frozen yet. No R3/R4 GPU run, production seed,
release, seal, export, or victory claim is valid.

## Verified baseline before the current repair

- Previous pushed baseline: `f96a247470b408f29185e1a9d9610516705df898`.
- Previous Python receipt: 439 passed, 2 fixed-runner skips.
- Previous branch coverage: 85.01%; six critical-file thresholds passed.
- Database v5 receipt exists, but the local Python snapshot is rejected because
  its benchmark spec/cohort lineage does not match the active v5 loader.
- The prior Hybrid VAL evidence is historical failure evidence: GAUC
  `0.775218972`, HR@10 `0.054092097`, NDCG@10 `0.011513037`, ItemCF GAUC
  dominance failed, Persona HR dominance failed, Apriori NDCG dominance
  failed, and semantic traps `0/10`.

## Current source validation receipt

The targeted R3-C2 tests pass, and Ruff/mypy pass after the implementation.
The full branch gate is still below the required 85% while new preflight,
promotion and pipeline branches are being covered; therefore readiness remains
blocked. The required full gate is:

```powershell
cd E:\UIT\cv\backend\ai-service
npm.cmd run test:seed-product
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
.\.venv\Scripts\python.exe -m pytest --cov=ai_service --cov-branch --cov-fail-under=85 -q
.\.venv\Scripts\python.exe scripts\check_critical_coverage.py <coverage.json>
git diff --check
```

The two fixed-runner benchmark skips are allowed during source validation, but
must become passes before deployment. No coverage threshold may be lowered and
no production path may be excluded.

## Data and artifact gates still required

Before R4, rebuild the local Python lineage from the verified v5 database run
using an explicit `benchmark-spec-v5.json`, real SBERT features and a full-stat
RuleArtifact. Require 823371 events, 5000 users, 5200 items, 15000 orders,
TRAIN/VAL strict target-rule rates >=0.40, all ten semantic cohort traps,
>=5000 non-trap rules and >=3000 organic rule items. Verify the six hashes for
snapshot, embedding, rules, benchmark spec, semantic cohort and order metadata.

Production preflight must validate absolute artifact/CA paths, three distinct
PostgreSQL identities, TLS and redacted read-only `SELECT 1` receipts. The
current shell has not been accepted as a production shell until these checks
pass.

## Locked execution sequence

```text
source exit gate
→ rebuild snapshot/features/rules
→ four Deep R3 ablations on seed 42
→ verified selection report
→ Hybrid H0 → H1 → H2 → H3a → H3b
→ H3b promotion receipt and production-config freeze
→ deep-42-v5 → hybrid-42-v5 → VAL
→ seeds 2027 and 31415
→ aggregate VAL 3+3
→ TEST all three pairs
→ aggregate TEST
→ seal selected Hybrid
→ export/verify bundle
→ ONNX parity and fixed-runner benchmark
```

R3/R4 diagnostic failure, corruption, non-finite metrics, GAUC below 0.50,
coverage regression, missing lineage, or a failed absolute Victory gate stops
the campaign. Do not weaken GAUC `.75`, HR@10 `.15`, or NDCG@10 `.08`.

The active source-level plan is
[`detail-plan-r3-r4.md`](master/detail-plan-r3-r4.md). The master plan remains
the authority. `Hybrid victory not established` until every listed gate is
backed by immutable artifacts and runtime evidence.
