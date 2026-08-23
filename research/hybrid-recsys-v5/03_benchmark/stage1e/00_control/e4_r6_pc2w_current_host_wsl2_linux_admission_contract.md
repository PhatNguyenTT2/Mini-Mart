# E4 R6-PC2W current-host WSL2 Linux admission contract

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-24T00:41:27.8278889+07:00
- Verification Status: UNVERIFIED
- Version Label: stage1e_e4_r6_pc2w_contract_v1
- Upstream Dependencies: [stage1e_e4_r6_pc1_admission_receipt_v1, stage1e_e4_r6_pc2_changed_host_requirements_v1]
- Repro Lock: null
- Experiment Intake Declaration: `{status: no_experiments_declared, declared_at: 2026-08-24T00:41:27.8278889+07:00, declared_by: scholar}`

This declaration is lane-local. PC2W carries no experiment result and does not replace the run-level scholar-owned experiment provenance.

## User decision and purpose

The scholar selected the no-OS-upgrade, current-machine, cost-constrained direction and authorized continuation of the planning and read-only preflight needed to evaluate it. This contract opens a previously unevaluated candidate:

`DOCKER_DESKTOP_WSL2_LINUX_CONTAINER_FOR_TRUSTED_PINNED_RESEARCH_CODE`.

PC1 remains dispositive for the two candidates it actually evaluated: HCS Hyper-V-isolated Windows containers and a dedicated full Windows Hyper-V VM. PC2W does not repair, overwrite, or reinterpret either PC1 rejection. It supersedes only the inference that a changed physical host is the sole possible next direction.

PC2W is an admission-design and read-only evidence gate. It does not authorize starting Docker Desktop, pulling or building an image, installing a distro or package, changing Docker/WSL settings, creating a container, downloading data, materializing an environment, training, evaluation, benchmark admission, or TEST access.

## Revised threat model

The WSL2 lane is admissible for consideration only under the narrower threat model `TRUSTED_PINNED_RESEARCH_CODE`:

- code must originate from the already locked official RecBole source identity;
- data must originate from the locked official GroupLens MovieLens 100K authority route;
- every downloaded byte must be source-bound and hash-checked before it becomes an offline execution input;
- no newly discovered, unpinned, forked, user-provided, or hostile repository may enter this lane;
- standard Docker Desktop WSL2 isolation is not represented as equivalent to a Hyper-V-isolated Windows container, Windows Sandbox, Enhanced Container Isolation, or a hostile-code security boundary.

If the project retains the prior hostile-workload/no-bypass boundary as an invariant, this lane fails and a supported stronger host remains required. For the narrower trusted-source reproducibility objective, container controls may be evaluated as risk reduction and provenance controls rather than as a proof against a malicious workload.

## Official authority

- Microsoft WSL FAQ: <https://learn.microsoft.com/en-us/windows/wsl/faq>
- Microsoft WSL architecture: <https://learn.microsoft.com/en-us/windows/wsl/about>
- Microsoft CUDA in WSL: <https://learn.microsoft.com/en-us/windows/ai/directml/gpu-cuda-in-wsl>
- Docker Desktop WSL2 backend: <https://docs.docker.com/desktop/features/wsl/>
- Docker Desktop Windows installation and requirements: <https://docs.docker.com/desktop/setup/install/windows-install/>
- Docker Desktop GPU support: <https://docs.docker.com/desktop/features/gpu/>
- Docker run networking and mount behavior: <https://docs.docker.com/engine/containers/run/>
- Docker bind-mount controls: <https://docs.docker.com/engine/storage/bind-mounts/>
- Docker Desktop license: <https://docs.docker.com/subscription/desktop-license/>

These sources establish that WSL2 is available on Home desktop editions; WSL2 uses a lightweight utility VM; Docker Desktop can operate through a WSL2 Linux backend without a user-installed Linux distribution; Linux containers are the Home-edition lane; standard containers have outbound connectivity by default; bind mounts are writable by default unless explicitly read-only; and Docker Desktop is free for education, personal use, qualifying small businesses, and non-commercial open source use. They do not establish that the exact current backend is running or that this project already has a compliant container image and packet.

## Current-host read-only observations

Observation timestamp: `2026-08-24T00:41:27.8278889+07:00`.

| Dimension | Observation | Admission interpretation |
|---|---|---|
| OS | CIM: `Microsoft Windows 11 Home Single Language`, `10.0.26200`, 64-bit; registry `EditionID=CoreSingleLanguage`, `DisplayVersion=25H2`, build `26200.9168` | Home is not admitted for the rejected Windows-container/Client-Hyper-V lanes; it remains eligible for WSL2 evaluation. The stale registry `ProductName=Windows 10 Home Single Language` is retained as an ambiguity, not used as OS-caption authority. |
| CPU | AMD Ryzen 7 5800H, 16 logical processors, 64-bit | Adequate for the CPU-only materialization envelope. |
| Virtualization | `HypervisorPresent=true`, firmware virtualization observed true; operational WSL2 v2 distro exists | Positive operational evidence for WSL2. Raw CIM `SLAT=false` and `VMMonitorModeExtensions=false` are contradictory while the hypervisor is active and remain an explicit ambiguity, not silently changed to true. |
| RAM | `25,077,805,056` bytes, approximately 23.35 GiB | Meets the current 4 GiB process limit and is sufficient for bounded CPU materialization; concurrent training remains prohibited. |
| Disk | `E:` free `121,980,530,688` bytes; `C:` free `32,812,396,544` bytes | `E:` has sufficient bounded-attempt headroom. Docker Desktop stores engine data under the user profile by default, so `C:` headroom must be rechecked before each image operation and may block a large image/build. |
| WSL | WSL `2.6.1.0`, kernel `6.6.87.2-1`, default version 2; `WslService` running | Meets Docker's stated minimum WSL version. No WSL update is authorized or required by this gate. |
| Distro inventory | Only `docker-desktop`, WSL version 2, stopped; no user Ubuntu/Debian distro | Direct-Ubuntu execution is not immediately available. Docker Desktop does not require a separate user distro, so this does not reject the Docker-backed candidate. |
| Docker binary | Docker Desktop `4.78.0.229452`; executable SHA-256 `5b8ab7161b88c45bd4b036e9988349356c18cf5409adb77fdfb8c73b279d8fce`; Docker client `29.5.3` | Installed source identity is observed, but support, runtime components, image store, daemon API and security controls remain unproven until a separately authorized query-only probe. |
| Docker context | `desktop-linux` points to `npipe:////./pipe/dockerDesktopLinuxEngine`; current endpoint unavailable; Docker Desktop stopped | Correct candidate family is configured, but the backend is not admitted or running. |
| User authority | Actual Windows identity is a member of `docker-users`; not an active Administrators-group member | Sufficient to attempt a normal Docker Desktop start only after authorization; no elevation is assumed. |
| GPU | NVIDIA GeForce RTX 3060 Laptop GPU, 6,144 MiB total, 5,586 MiB free at observation, driver `610.62` | Not required for PC2W or CPU-only R6-M0/R6-M1. Later GPU training needs a separate compatibility/resource gate and cannot inherit this observation. |
| License | Docker documentation identifies education and personal use as free | Project eligibility remains scholar-attested; this contract does not make a legal determination. |

Optional-feature state could not be queried without an elevated Windows token. Operational WSL2 evidence is sufficient to keep the candidate open, but no absent feature is inferred to be enabled. Docker settings-file hash was observed as `b0bd046928a80e18777ef7af0f504375b5f1f1a8bdb504d983a240beff3f260a`; its schema did not expose a decisive WSL-backend boolean. The `desktop-linux` context plus the version-2 `docker-desktop` distro are the positive backend-family evidence.

## Candidate container policy to be proven later

The eventual container command packet must be rebuilt and independently audited. At minimum it must prove:

1. An immutable Linux image identity by registry source, manifest digest, architecture, license and locally observed image ID. Tags alone are insufficient.
2. Linux CPython and package identities; the Windows CPython NuGet runtime is not reused.
3. `--pull=never` for every offline execution command and a failure if the exact image digest is absent.
4. `--network none` for offline environment assembly, dataset transformation, checks and later scientific execution. Docker's default outbound-enabled network is prohibited for these phases.
5. Networked acquisition is a separate phase limited to exact official URLs, expected sizes and digests. Acquired bytes cross into the offline phase only after verification.
6. A read-only container root filesystem, an isolated tmpfs scratch root, a non-root user, dropped capabilities, no-new-privileges, PID, CPU and memory limits, deterministic timeout and descendant termination.
7. Only exact input-cache/source roots are mounted read-only. Only one new immutable attempt root is mounted read-write. The whole `E:` drive, repository root, user profile and Docker socket are never mounted.
8. Host and container path pairs are recorded. Existing `E:\...` Windows argv are replaced by audited Linux paths; `/mnt/e` is not accepted as an implicit semantic equivalence.
9. All 37 attempt-003 commands are superseded by a new R6-C1R3 packet. Function-level intent may be preserved, but literal argv equality is not claimed.
10. Materialization, training, evaluation, benchmark admission and TEST remain separately authorized gates.

## Admission decision

PC2W preflight disposition:

`CONDITIONAL_CURRENT_HOST_WSL2_DOCKER_LINUX_LANE_DISCOVERED_QUERY_ONLY_BACKEND_PROBE_REQUIRED`.

Positive findings are sufficient to reject the statement that an OS-edition upgrade or a different physical machine is mandatory before any further progress. They are not sufficient to admit Docker Desktop for materialization.

The next gate is `R6-PC2W-P1`: authorize one start of the already installed Docker Desktop backend followed by query-only runtime inventory. The probe may read daemon/server version, backend OS/architecture, storage driver, security options, root directory, WSL context, image/container cardinalities, default address pools, proxy declaration, GPU runtime exposure and current disk usage. It may not pull/build/run/create/remove/prune/update/sign in/change settings, access TEST, or contact an experiment/data source.

If P1 passes, the next design sequence is:

1. `R6-PC2W-G1`: central backend admission under the narrowed trusted-source threat model;
2. `R6-C1R3-LINUX`: fresh Linux/container command packet and typed postcondition adapters;
3. independent packet/runner audit on Sol XHigh Standard;
4. a new explicit user authorization before any image acquisition, environment creation or materialization;
5. R6-M0/R6-M1 bounded CPU-only materialization;
6. R6-A1 independent audit, then R6-G1 central admission proposal.

## Locked truth state

```text
RESULT_STATUS=NOT_RUN
TEST_SET_OPENED=NO
ACCEPTED_RESULT_ROWS=0
```

No scientific execution occurred. No result row is accepted. Phase 1E remains incomplete.

## Model policy

- Central contract and synthesis: `gpt-5.6-sol`, reasoning `max`, service tier `default / Standard`.
- Independent packet/backend audit: `gpt-5.6-sol`, reasoning `xhigh`, service tier `default / Standard`.
- Fast/Priority profiles are prohibited for future PC2W work.
