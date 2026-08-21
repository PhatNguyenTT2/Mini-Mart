# E4 reproduction execution plan

## Material Passport

- `origin_skill`: `ars-codex:academic-research-suite`
- `mode`: `experiment-agent / planning-only`
- `date`: `2026-08-22`
- `status`: `UNVERIFIED`
- `version`: `0.1.26`

`RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `ACCEPTED_RESULT_ROWS=0`, and `execution_authorized=false` are immutable entry truths for this plan. This document writes commands but authorizes none.

## Entry gate and decision

The E4 contract, frozen input manifest, and Wave A validation receipt matched their required canonical-LF SHA-256 values. All 28 manifest entries were present and matched; there were no missing or mismatched inputs.

The reconciliation produced no `READY_FOR_E5_AUDIT` row. Seven source bindings remain `PENDING_EVIDENCE` and six are `REJECTED`. The minimum defensible bundle is therefore empty. `E3-LIGHTGCN-GOWALLA-PYTORCH-001` is only the first lock-resolution target because its pinned README binds an exact seed/configuration to a reported result. It is not selected for execution.

Fail-closed verdict: `BLOCKED_NO_READY_REFERENCE_BUNDLE`.

## Non-negotiable sequence

The following gates are serial. Passing a later gate can never cure failure of an earlier gate.

1. **Official reproduction acceptance.** Reproduce a source-bound center on the official dataset pipeline, command/configuration, sampler, checkpoint rule, and evaluator. Accept only after E5 audits all receipts and the frozen tolerance.
2. **Method-faithful v5 adaptation.** Freeze the accepted model mathematics and expose only the bounded adapter in `v5_adapter_and_evaluator_contract.md`. Any method change creates a new method and returns to Gate 1.
3. **Harmonized v5 comparison.** Train and evaluate all eligible methods on the same v5 split, full candidate universe, seen-item mask, seed schedule, checkpoint rule, and evaluator.
4. **Separate external validation.** Run only on a dataset that independently clears identity, history, order/basket, rights, version, hash, split, and evaluator gates. Never pool it with official reproduction or harmonized v5 results.

## Lock-resolution target: LightGCN / Gowalla

Primary source: [pinned author README](https://raw.githubusercontent.com/gusye1234/LightGCN-PyTorch/947ca2b3b1d2d3545b114145710cb06c4e57b3d2/README.md), accessed 2026-08-22, environment/data/command at lines 22–39, fixed-seed output at lines 60–64, and final result/stopping description at lines 69–82. Repository state: [immutable commit](https://github.com/gusye1234/LightGCN-PyTorch/tree/947ca2b3b1d2d3545b114145710cb06c4e57b3d2), accessed 2026-08-22.

Frozen source-bound command:

```powershell
python main.py --decay=1e-4 --lr=0.001 --layer=3 --seed=2020 --dataset="gowalla" --topks="[20]" --recdim=64
```

Frozen centers and tolerances are Recall@20 `0.1824 ± 0.00912`, NDCG@20 `0.1547 ± 0.007735`, and Precision@20 `0.05589 ± 0.005`. These tolerances came from Wave A; they are acceptance bands, not empirical uncertainty estimates.

This target stays blocked because the repository-bundled processed pack lacks a canonical raw-to-processed receipt and rights chain; the pinned state has no license file; the environment is not locked with hashes; candidate/tie semantics are incomplete; and no immutable checkpoint/result receipt exists. The source evaluator is integrated into training, so no separate authoritative evaluate-only command exists. E4 will not invent one.

## Planned isolated namespaces

No directory below is created by E4. If the user later confirms an E5 execution packet, the executor must use these exact namespaces and refuse pre-existing unreceipted contents:

| Purpose | Exact namespace |
|---|---|
| Runtime root | `C:\recsys_stage1e_runtime\e4_v1` |
| Immutable repo checkout | `C:\recsys_stage1e_runtime\e4_v1\repos\lightgcn_pytorch\947ca2b3b1d2d3545b114145710cb06c4e57b3d2` |
| Environment | `C:\recsys_stage1e_runtime\e4_v1\envs\lightgcn_pytorch_source_locked` |
| Dataset receipts | `C:\recsys_stage1e_runtime\e4_v1\receipts\datasets` |
| Run receipts | `C:\recsys_stage1e_runtime\e4_v1\receipts\runs\E3-LIGHTGCN-GOWALLA-PYTORCH-001` |
| Logs | `C:\recsys_stage1e_runtime\e4_v1\logs\E3-LIGHTGCN-GOWALLA-PYTORCH-001` |
| Harmonized v5 artifacts | `C:\recsys_stage1e_runtime\e4_v1\v5_harmonized` |
| External artifacts | `C:\recsys_stage1e_runtime\e4_v1\external` |

Official, v5, and external namespaces must not contain symlinks or junctions to each other. A resolved-path containment check is mandatory before every write.

## Command stages and receipts

The exact strings, working directories, timeouts, confirmation fields, and failure behavior are in `exact_command_confirmation_packet.json`. That packet is blocked and non-executable. The intended stages are:

1. **Clone and pin.** Clone without checkout, detach at SHA `947ca2b3b1d2d3545b114145710cb06c4e57b3d2`, verify `HEAD`, record remote URL, submodule state, and canonical file manifest. Network receipt: start/end UTC, resolved commit, Git version, exit code, stdout/stderr hashes.
2. **Install.** The source README gives `pip install -r requirements.txt` but does not identify an exact Python runtime. E4 therefore supplies no environment-creation command. Only after E5 locks the runtime identity and supplies a fully hashed lock at `C:\recsys_stage1e_runtime\e4_v1\locks\lightgcn_pytorch_source_requirements.txt` may the exact offline install command in the packet be considered. Record Python/pip/CUDA/PyTorch versions, wheel filenames and hashes, `pip freeze`, and import metadata. No package substitution is allowed.
3. **Preprocess gate.** There is no source-authoritative raw preprocessing command. The executor must require `gowalla_raw_to_processed.json` with provider URL, access terms, raw hashes, transformation code SHA, exact argv, output hashes, counts, and split/candidate semantics. Missing receipt is a hard failure; repository-bundled files alone do not pass.
4. **Train and integrated evaluate.** Run the exact source command once after all gates pass. Capture a timestamped immutable log, exit code, GPU telemetry, final metrics, stopping event, configuration dump, and produced artifact hashes. Because evaluation is integrated, a second invented evaluate command is forbidden.
5. **Acceptance.** A parser may copy the three reported metrics into a candidate receipt, but only E5 may audit the parser, source row, tolerance test, and receipt completeness. E4 never changes status from `NOT_RUN`.

Every receipt is UTF-8 JSON with a duplicate-key rejection pass, sorted stable artifact paths, SHA-256 per byte artifact, canonical-LF SHA-256 for text artifacts, and these required fields: `row_id`, `phase`, `command_id`, `argv`, `cwd`, `environment_hash`, `repo_sha`, `input_hashes`, `output_hashes`, `started_at_utc`, `ended_at_utc`, `exit_code`, `timeout_seconds`, `resource_observations`, `retry_count`, `test_set_opened`, and `operator_confirmation_id`.

## Local RTX 3060 6 GB schedule

The read-only inventory exposed one NVIDIA GeForce RTX 3060 Laptop GPU with 6144 MiB. CPU and host RAM inventory was not accessible, so the following are planning ceilings, not claims about available capacity:

- One GPU process at a time on physical GPU 0; no concurrent official, v5, or external jobs.
- Preflight requires at least 5120 MiB free VRAM. Planned job ceiling is 5120 MiB; exceeding it is a hard failure.
- Maximum four logical CPU workers and 12 GiB host RAM per job. If the executor cannot enforce a Windows Job Object or equivalent limit, execution fails before launch.
- Clone timeout 600 seconds; environment creation 300 seconds; package install 1800 seconds; lineage/preprocess gate 3600 seconds; LightGCN train-plus-integrated-evaluate timeout 21600 seconds; receipt finalization 300 seconds.
- Telemetry interval 10 seconds, containing UTC time, PID tree, GPU memory/utilization, CPU utilization, and resident memory. Failure to write telemetry for 60 seconds terminates the run as infrastructure failure.

## No-auto-retry and failure semantics

`retry_policy=NO_AUTO_RETRY` applies to every stage. Timeout, nonzero exit, CUDA OOM, dependency resolution, hash mismatch, pre-existing unreceipted namespace, missing lineage, missing checkpoint/result artifact, metric parse ambiguity, telemetry loss, or TEST access produces exactly one failed receipt and stops the row. No seed is replaced, no batch size is reduced, no layer count or sampler is changed, and no command is resumed automatically.

A manual retry requires a new confirmation packet and a new run namespace; the failed receipt is retained. A retry does not overwrite or supersede a failure. Any source/config/data/evaluator change creates a new candidate row and cannot be compared to the frozen center.

## MovieLens framework-center assessment

The [official RecBole-GNN MovieLens 1M page](https://github.com/RUCAIBox/RecBole-GNN/blob/818babfe03268c78a01215376f7ceea48df159f8/results/general/ml-1m.md), accessed 2026-08-22, provides BPR and LightGCN centers with an interaction filter, 8:1:1 ratio split, full-sort evaluator, metrics, and common configuration. The official repository was resolved to SHA `632ef888589944c190ad8f449b49ca559618d4df`. The canonical GroupLens archive has provider MD5 `c4d9eecfca2ab87c1945afe126590906` ([sidecar](https://files.grouplens.org/datasets/movielens/ml-1m.zip.md5), accessed 2026-08-22), but the provider README supplies no official top-N split.

That evidence does **not** establish an exact framework-authoritative reproduction center under this contract: result-bound seed/run identity, checkpoint policy/artifact, dependency lock, raw-byte-to-split receipt, and tie policy are absent. MovieLens 10M has provider MD5 `ce571fd55effeba0271552578f2648bd` ([sidecar](https://files.grouplens.org/datasets/movielens/ml-10m.zip.md5), accessed 2026-08-22), but its provider scripts are five-fold rating-prediction utilities rather than a framework-owned top-N center. Neither dataset is promoted.

## Exit criteria for a future E5 audit

E5 may audit a row only when every field below is immutable and mutually source-bound:

- repository SHA and license decision;
- lawful dataset provider, terms snapshot, version, provider digest, acquired byte hashes, and raw-to-split transformation receipt;
- exact dependency lock and verified environment receipt;
- exact non-interactive command/config, seed/run schedule, sampler, layers, batch size, checkpoint rule/artifact, candidate universe, negative-sampling rule, evaluator, and tie policy;
- reported center with exact source locator and frozen tolerance;
- confirmation packet with `user_confirmation_required=true`, `confirmed=true`, and explicit execution authorization issued after this E4 handoff.

Until then, the correct operational action is to execute nothing.
