# E4 R6-PC1 alternative-containment central admission contract

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-23T23:24:25.5648042+07:00
- Verification Status: UNVERIFIED
- Version Label: stage1e_e4_r6_pc1_contract_v1
- Upstream Dependencies: [stage1e_e4_r6_pc0_failure_receipt_v1, stage1e_e4_r6_c1r2_runner_audit_v1]
- Repro Lock: null
- Experiment Intake Declaration: `{status: no_experiments_declared, declared_at: 2026-08-23T23:24:25.5648042+07:00, declared_by: scholar}`

This declaration is lane-local: PC1/PC2 carry no experiment result and do not replace the run-level scholar-owned experiment provenance in `research/hybrid-recsys-v5/00_control/material_passport.json`.

## Purpose

R6-PC0 rejected the frozen Microsoft MXC candidate on this host because the validated query returned a valid zero capability mask. R6-PC1 decides whether any alternative containment family can be admitted on the same host without executing, installing, downloading, enabling, probing, or mutating a backend.

This is a central evidence-admission gate. It is not a materialization, training, evaluation, benchmark, or TEST gate.

## Frozen upstream evidence

Hash policy: strict UTF-8 decode, normalize CRLF to LF, then SHA-256.

| Artifact | Canonical-LF SHA-256 |
|---|---|
| `e4_r6_pc0_mxc_containment_feasibility_contract.md` | `c12e9b4baebdafcb58a42c5618aa292dedb6e5740d533125659c1daa4f5dad65` |
| `rebaseline_v2_e4_r6_pc0_query_preflight_attempt002_failure_receipt.json` | `55ab3aa39a9bb5977c168edaeefe44ddf5049746f7e7a9642ce807aab6b3c92d` |
| `rebaseline_v2_e4_r6_c1r2_runner_compatibility_audit_receipt.json` | `e17cc02f8e7916db0ec382a76620a1b9e2ea8b1291e9a64e9078949e88c1635a` |
| pre-PC1 `pipeline_state_stage1e.json` | `834c85a059af0827c768534d7c3a7e26c7cff17185af0c62a88598e8b0efac44` |

Central entry checkpoint: `9355743be9c4e326f062e4413fe2c0652bcdfe71`.

## Evidence authority

Only current-host read-only observations and current official Microsoft documentation may establish admission. Discovery-task synthesis is advisory until replayed into this central contract and its receipt. Missing, access-denied, ambiguous, preview-only, unsupported-edition, or mutation-dependent evidence fails closed.

Official authority used by this gate:

- Windows container host requirements: <https://learn.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/system-requirements>
- Windows container environment prerequisites: <https://learn.microsoft.com/en-us/virtualization/windowscontainers/quick-start/set-up-environment>
- Windows 11 feature-specific requirements: <https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements>
- Windows container security boundaries: <https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/container-security>
- Windows container network isolation and default policy: <https://learn.microsoft.com/en-us/virtualization/windowscontainers/container-networking/network-isolation-security>
- PowerShell Direct requirements: <https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/powershell-direct>
- Hyper-V architecture: <https://learn.microsoft.com/en-us/virtualization/hyper-v-on-windows/reference/hyper-v-architecture>
- Windows container version compatibility: <https://learn.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/version-compatibility>

## Admission invariants

A candidate may advance only if all of the following are established for the exact host and exact packet:

1. The OS edition and enabled features officially support the backend.
2. The backend is a documented security boundary for the intended workload.
3. The entire descendant process tree is contained and can be deterministically terminated.
4. Filesystem access supports explicit read-only and read-write roots while denying access outside the declared namespace.
5. Outbound network is default-deny and permits only the declared hosts through a no-bypass policy with connection evidence.
6. Admission does not depend on ambient host DACL changes, host firewall changes, permissive learning mode, or argv-only observation.
7. Any required administrator action, feature enablement, restart, registry change, image acquisition, runtime installation, or license is declared before execution and requires separate authorization.
8. The exact CPython/PowerShell command packet, literal paths, environment identities, receipts, postconditions, retry count zero, and immutable roots remain enforceable.

## Current-host observations

The central task performed only read-only inventory:

- Registry `EditionID`: `CoreSingleLanguage`.
- Registry `ProductName`: `Windows 10 Home Single Language`.
- Registry `CurrentBuildNumber`: `26200`.
- `vmms`: absent.
- `vmcompute`: present, stopped, manual.
- `hns`: present, running, manual.
- Hyper-V PowerShell commands `New-VM` and `Get-VM`: absent.
- `hcsdiag.exe`: present.
- Docker CLI: present; only the selected `desktop-linux` endpoint was observed and it was absent. Windows-engine state is `UNOBSERVED_NOT_ESTABLISHED`.
- Optional-feature state queries require elevation and returned no feature state.
- CIM, `systeminfo`, and WSL distribution enumeration were access-denied in the current sandbox and are not treated as positive evidence.

No inference upgrades an unavailable observation into support.

## Central candidate disposition

### HCS Hyper-V-isolated Windows container

Disposition on the current host: `REJECTED_CURRENT_HOST_OS_EDITION_AND_RUNTIME_NOT_ADMISSIBLE`.

Official Windows-container requirements require Professional or Enterprise client editions and the Hyper-V role for Hyper-V isolation. The observed host edition is `CoreSingleLanguage`; no supported Windows container runtime was positively established; exact feature state is unproven. Filesystem and bounded-network enforcement also remain unresolved. Presence of `hcsdiag.exe`, `vmcompute`, `hns`, or the Docker CLI alone is not admission evidence.

### Dedicated full Windows Hyper-V VM

Disposition on the current host: `REJECTED_CURRENT_HOST_CLIENT_HYPERV_EDITION_NOT_SUPPORTED_AND_CMDLETS_ABSENT`.

Client Hyper-V is officially available on Pro editions and above. The observed host edition is `CoreSingleLanguage`; `vmms`, `New-VM`, and `Get-VM` are absent. PowerShell Direct would additionally require a running local Hyper-V VM and Hyper-V administrator authority. No VM, image, license, network relay, or host policy may be created under PC1.

## Verdict and next gate

PC1 verdict: `NO_ADMISSIBLE_CURRENT_HOST_BACKEND_CHANGED_HOST_REQUIRED`.

Admission cardinality is zero. No candidate is selected. No fallback or automatic retry is allowed on this host. R6-C1R3, materialization, bridge execution, training, evaluation, benchmark admission, and TEST access remain blocked.

The next allowed step is R6-PC2: independently audit this decision, then obtain an explicit changed-host decision and collect a fresh read-only host-evidence package against `e4_r6_pc2_changed_host_preflight_requirements.json`. A host change does not reuse the PC0 runtime result and does not itself authorize execution.

## Locked truth state

```text
RESULT_STATUS=NOT_RUN
TEST_SET_OPENED=NO
ACCEPTED_RESULT_ROWS=0
```

## Model policy

- Central synthesis: `gpt-5.6-sol`, reasoning `max`, service tier `default / Standard`.
- Independent admission audit: `gpt-5.6-sol`, reasoning `xhigh`, service tier `default / Standard`.
- Fast/Priority profiles are prohibited.
