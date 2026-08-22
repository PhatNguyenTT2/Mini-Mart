# R6-C1 central validation contract

Date: 2026-08-23

## Fixed entry

R6-C1 entered from commit `60e51b017f5a37e9839c09e2ab014ba0f9a29b4d` after `PASS_R6_G0_FROZEN_31_OF_31_READY_FOR_R6_C1`. The decision-bearing inputs are `e4_r6_g0_decision_freeze.json`, `e4_r6_g0_frozen_input_manifest.json`, and `rebaseline_v2_e4_r6_g0_gate_receipt.json` at the fingerprints recorded in `rebaseline_v2_e4_r6_c1_dispatch.json`.

The worker is Sol High Fast (`gpt-5.6-sol`, reasoning `high`, service tier `priority`). It performs bounded mechanical assembly only. Central validation is Sol Max Standard.

## Exact output boundary

The only allowed output root is:

`research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ai/E4_R6C1_materialization_command_packet`

The root must contain exactly five regular UTF-8 JSON files and no directory, link, reparse point, binary or extra file:

1. `dataset_materialization_packet.json`
2. `environment_materialization_packet.json`
3. `recbole_dataset_bridge_packet.json`
4. `execution_boundary_and_negative_assertions.json`
5. `audit_handoff.json`

Every JSON object must pass duplicate-key and case-colliding-key rejection recursively. Central records exact raw and canonical-LF byte counts and SHA-256 values.

## Input and authorship replay

Central must require all of the following:

- R6-G0 validator still returns `PASS_R6_G0_FROZEN_31_OF_31_READY_FOR_R6_C1`.
- The worker reports the exact entry commit, 31/31 frozen inputs, 19/19 strict JSON inputs and the exact G0 decision/manifest/receipt hashes.
- The selected candidate, RecBole revision and Git tree equal the R6-G0 freeze.
- The actual worker model profile equals Sol High Fast.
- All five artifacts say proposal-only and no proposed command was executed.
- The worker changed no path outside its exclusive output root and made no commit.

## Dataset packet gate

The dataset packet must preserve the accepted R6-D1 scientific choices verbatim:

- current official GroupLens release page, README, checksum and archive endpoints only;
- current sidecar expectation `0e33842e24a9c977be4e0107933c0723`, never labeled historical;
- expected archive byte count `4,924,029`, with locally recomputed MD5 and SHA-256 required after acquisition;
- exact external `attempt-001` official-source root and no repository or harmonized-v5 write;
- no redirects, mirror, authenticated route, credential, cookie or RecBole S3 fallback;
- safe ZIP member allowlist, path containment, regular-file-only extraction, unexpected-file rejection and immutable-attempt retry policy;
- exactly 100,000 `u.data` rows mapped in ordinal order to one `ml-100k.inter`, with no filtering, deduplication, sorting, ID rewrite, timestamp rewrite or rating cutoff;
- exact reconciliation, domain and first-occurrence ID-map receipts; and
- literal ordered argv, exact persistent/ephemeral write sets, per-command timeouts and bounded retries/concurrency.

No command may load a RecBole Dataset, create a split, calculate a metric or access project-v5 data.

## Environment packet gate

The environment packet must implement the accepted R6-G0 profile without falling back to the current system Python 3.11.3 or the `py` launcher:

- external non-Git immutable environment `attempt-001` root;
- exact official CPython 3.11.9 AMD64 installer and Sigstore URLs;
- official-page MD5 `e8dcd502e34932eebcaf1be056d5cbcd`, locally computed SHA-256 and `Get-AuthenticodeSignature` status `Valid` before installation;
- local per-user `TargetDir`, no all-users install, PATH edit, launcher, association or shortcut;
- exact CPython 3.11.9, 64-bit, `win32`, `cp311-cp311-win_amd64` identity before venv creation;
- exactly the 20 ordered direct requirements frozen by R6-G0;
- Torch `2.2.2+cpu` from the official CPU index and every other third-party distribution as a binary wheel from the accepted official hosts;
- local wheel built only from RecBole revision `9a6f63d8d4a5b989fe27955a833f813a6d86041e`, tree `08915121fea069a30f7e3e97a72e16e7e76d43c6`;
- no PyPI RecBole, editable install, source distribution, unpinned VCS, CUDA or Hyperopt;
- wheel URL, filename, tag, size and locally computed SHA-256 receipts, a complete hash-locked offline install, `pip check`, exact package inventory, CPU assertions, imports and syntax-only checks; and
- literal ordered argv, exact writes, timeouts, disk budget, retry policy and concurrency one.

Central fails closed if a command uses a shell-composed unresolved path, an unapproved network host, an ambient interpreter or a write outside the two frozen external roots.

## Installed-package dataset bridge gate

The bridge packet must encode, not hide, the source behavior discovered at R6-G0:

- pinned `Config._set_default_parameters` forces `recbole/dataset_example/ml-100k` for dataset `ml-100k`;
- pinned `Dataset._load_data` calls `_download` when that path does not exist; and
- pinned `url.yaml` maps `ml-100k` to a noncanonical RecBole S3 artifact.

The only acceptable bridge is a binary copy of the canonical GroupLens-derived `ml-100k.inter` into a previously absent installed-package `recbole/dataset_example/ml-100k` directory under the frozen venv. The source and destination byte count, SHA-256 and row count must match. The destination exact file set is one `.inter` file; `.item`, `.user`, repository blobs, links, junctions and source edits are forbidden. The receipt lives outside the consumer dataset directory.

A config-only resolved-path assertion is allowed. `Dataset`, `create_dataset`, any row read and every S3 request remain forbidden.

## Cross-packet command-safety gate

Central must flatten every executable and argv token and mechanically reject commands or executable surfaces that invoke:

- `run_recbole`, quick-start execution, `Trainer`, `fit`, training or evaluation;
- `Dataset`, `create_dataset`, loader construction, split generation or metrics;
- HyperTuning, Hyperopt, Ray workers, distributed execution or WandB;
- checkpoint, pretrained weight or result-asset retrieval;
- project-v5 TEST discovery, path access or loading; or
- benchmark admission, result acceptance or paper-number generation.

Negative prose does not itself fail the scan; the scan applies to executable/argv fields. The boundary artifact must also independently enumerate command IDs, dependency order, network allowlists, aggregate write roots, CPU/memory/disk/time/retry/concurrency bounds and immutable failure behavior.

Dataset and environment materialization may be independent only after central packet validation. The bridge depends on successful, independently receipted R6-M0 and R6-M1. No scientific execution dependency may appear.

## Required verdicts

Central may return only:

- `PASS_R6_C1_EXACT_COMMAND_PACKET_READY_FOR_BOUNDED_R6_M0_R6_M1`, or
- `FAIL_R6_C1_REWORK_REQUIRED`.

A PASS opens only the already user-authorized dataset/environment materialization operations. It does not authorize RecBole Dataset loading, training, evaluation, TEST access, benchmark admission or a paper claim.

Persistent truth remains:

```text
RESULT_STATUS = NOT_RUN
TEST_SET_OPENED = NO
ACCEPTED_RESULT_ROWS = 0
execution_authorized = false
project_benchmark_numbers = INVALID_FOR_PAPER
```
