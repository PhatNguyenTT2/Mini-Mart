## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: run
- Origin Date: 2026-09-02T15:06:35.530Z
- Verification Status: UNVERIFIED
- Version Label: ais-r2-runtime-preflight-pass-v1.0.0
- Upstream Dependencies: catalog private-research authorization, Windows checkout remediation, prior fail-closed admission receipt
- Repro Lock: source commit `28f593b193e88df76e228fd383a11e694d29550e`; ready run `benchmark-v5-s42-7f40639b0d-1ace202aaa`; command SHA-256 `d9e66d3b70a726972cd5358959892c9e7241a631d3fd34482230c2c808fdfad7`
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# AIS-R2 runtime preflight admission

The restored external state passed a fresh runtime admission. All three
required Supabase databases completed verified TLS connections using the locked
Supabase Root 2021 CA, entered `REPEATABLE READ READ ONLY`, and exposed the
relations required by the Source Bundle exporter. The auth database was not
connected.

Exactly one published `ready` lineage was found for store 1:

- run: `benchmark-v5-s42-7f40639b0d-1ace202aaa`;
- seed: 42;
- expected events: 823,371;
- catalog SHA-256: `7f40639b0d9e35f0649d383067591892354d75a500b572922e0e98efa2c37d0c`;
- benchmark-spec SHA-256: `1ace202aaa8f54204ead66ceabe809b3c51795e097dd71c505f07b8367c80bd2`.

The fresh output and staging roots do not exist. Disk admission passes. The
locked command may therefore be executed once. This admission authorizes only
the AIS-R2 private Source Bundle export. It does not authorize training,
evaluation, benchmark claims, redistribution, or opening the project TEST set.

Failure of the locked export closes this attempt without automatic retry.
