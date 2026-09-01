# R6-C1R3 Attempt-009 provider TLS remediation plan

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: validate / run-blocker diagnosis
- Origin Date: 2026-09-01
- Verification Status: ANALYZED
- Version Label: stage1e_e4_r6_c1r3_attempt009_provider_tls_remediation_v1
- Upstream Dependencies: [stage1e_e4_r6_c1r3_linux_attempt008_runtime_v1, stage1e_minimal_execution_rebaseline_v1, stage1e_e4_r6_c1r3_linux_materialization_runner_v7_attempt008_escalated_external_root_write]
- Repro Lock: null

## 1. Decision

Attempt-008 is closed and immutable. A new materialization attempt is **not
admitted yet**. The first packet command failed because the canonical
`files.grouplens.org` server presented an expired leaf certificate. This is an
external provider-availability failure, not evidence of a dataset, RecBole,
Docker, WSL, memory, or benchmark defect.

The next runtime attempt may be created only after a read-only provider gate
shows that the exact canonical HTTPS endpoints validate normally, or after an
explicit change-control decision changes the source policy. No retry of
Attempt-008 is permitted.

## 2. Immutable Attempt-008 evidence

| Evidence | Observation |
|---|---|
| Attempt | `attempt-008-linux` |
| Runtime result | `HANDOFF_INCOMPLETE_R6_C1R3_LINUX_ATTEMPT008_CLOSED` |
| Docker/WSL | Start and readiness PASS; stop, WSL shutdown and 3/3 closure snapshots PASS |
| Packet progress | 3/17 commands; failed at `M00_ACQUIRE_OFFICIAL_GROUPLENS_BYTES` |
| Error | `ssl.SSLCertVerificationError: certificate has expired` |
| M00 stderr | 2,491 bytes; SHA-256 `bca990074a2967ae46bd71da3ba0a851cc1ac2763c101ad1f638598208b98e9e` |
| M00 argv | SHA-256 `5f2ea669a833d489e8543b1f02484f29517da47663f995e2d3084d13e98ca6cb` |
| `runner_result.json` | SHA-256 `9784ccc14024bfd2a935c29f5a94f7ea8814a1bd212276cd2bb9147cf594a9cd` |
| `command_journal.jsonl` | SHA-256 `7d41469b492da539ac18422a919753ede6e71b02ac600eedbbf6773a5ecd9d3e` |
| `preflight.json` | SHA-256 `360f0a4461c2d49936a8562a11d621794cf5387e3a81c8ebebf31aedf041a9c9` |
| Scientific truth | `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, `execution_authorized=false` |

The canonical M00 endpoints remain exactly:

- `https://files.grouplens.org/datasets/movielens/ml-100k-README.txt`
- `https://files.grouplens.org/datasets/movielens/ml-100k.zip.md5`
- `https://files.grouplens.org/datasets/movielens/ml-100k.zip`

## 3. Causal diagnosis

The diagnosis used a no-download TLS handshake and a standard verified HTTPS
request. The current machine time was 2026-09-01. OpenSSL reported:

```text
subject=C=US, ST=Minnesota, O=University of Minnesota, CN=files.grouplens.org
issuer=C=US, O=Internet2, CN=InCommon ECC Server CA 2
verify error:num=10:certificate has expired
notAfter=Aug 28 23:59:59 2026 GMT
```

The same expiration was observed by the pinned CPython 3.11.9 runtime. In the
same diagnostic, `grouplens.org` and `www.python.org` completed verified TLS
successfully. The official GroupLens 100K page and its WordPress API both
identify the `files.grouplens.org` URLs above as the distribution endpoints.
Therefore the evidence distinguishes a provider file-host certificate outage
from a stale local CA bundle or a bad system/container clock.

No archive bytes were acquired by Attempt-008. The prior Attempt-002 archive
and all of its extracted material remain explicitly immutable failed-attempt
evidence and are not eligible for reuse.

## 4. Docker runtime repair (separate, completed)

Before this plan, the two Docker runtime parents contained inaccessible
AF_UNIX socket/reparse-point entries:

- `C:\\Users\\ACER\\AppData\\Local\\Docker\\run\\dockerInference`
- `C:\\Users\\ACER\\AppData\\Local\\docker-secrets-engine\\engine.sock`

With Docker processes absent, the parents were moved recoverably and replaced
with ordinary empty directories:

- `C:\\Users\\ACER\\AppData\\Local\\Docker\\run.stale-20260901-1745`
- `C:\\Users\\ACER\\AppData\\Local\\docker-secrets-engine.stale-20260901-1745`

The replacement directories are ordinary and empty; the backups contain the
original entries. No Docker image, volume, setting, dataset, or environment
was deleted. Attempt-008 subsequently proved Docker readiness and clean
closure, so this socket issue is not the current blocker.

## 5. Forbidden shortcuts

The current frozen source contract continues to forbid:

1. disabling certificate verification or using `--insecure`;
2. changing HTTPS to HTTP;
3. accepting a redirect, proxy, mirror, RecBole S3 object, or alternate
   hostname as if it were the canonical provider endpoint;
4. copying bytes from Attempt-001/002 or any failed materialization root;
5. changing the provider checksum or inferring a new checksum from a
   non-authoritative transport.

These shortcuts would make the data transport and source authority
non-comparable even if the resulting bytes happened to hash to the expected
archive.

## 6. Attempt-009 admission gate

Attempt-009 remains `BLOCKED_PROVIDER_TLS_UNAVAILABLE` until all of the
following are true:

1. A no-download TLS check against `files.grouplens.org` reports certificate
   validation success and a not-after date after the check date.
2. A verified HEAD/metadata check for all three exact URLs reports the expected
   endpoint and no redirect.
3. The packet, runner, and source policy are unchanged except for a new
   attempt identifier and a newly bound central receipt.
4. A fresh `attempt-009-linux` root is absent before execution.
5. The exact runner command is launched once with host-write authority and
   the same no-retry/no-fallback policy.

The provider gate is diagnostic only. It must not create a materialization
root, start Docker, open the dataset, run RecBole, train, evaluate, calculate a
metric, open TEST, or admit a benchmark row.

## 7. Alternative requiring explicit author decision

If the provider certificate is not renewed, central may propose a separate
change-control amendment with a precisely identified transport mirror or a
new official dataset. That amendment must separately bind source authority,
rights, archive SHA-256, transformation, and benchmark comparability. It is
not an automatic fallback and does not authorize use of the current packet.

Until such a decision or provider recovery, Phase 1E remains scientifically
open:

```text
RESULT_STATUS=NOT_RUN
TEST_SET_OPENED=NO
ACCEPTED_RESULT_ROWS=0
execution_authorized=false
phase_1e_complete=false
project_benchmark_numbers=INVALID_FOR_PAPER
```

**Verdict:** `ATTEMPT009_BLOCKED_PROVIDER_TLS_UNAVAILABLE`
