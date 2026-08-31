# R6-C1R3-LINUX checkout-provenance remediation plan

Date: 2026-08-31

## Incident and evidence

The fresh independent audit task for packet commit
`210c1edfd432e19b0007b3ba39528bcdb73c2288` returned
`HANDOFF_INCOMPLETE` before runtime.  Its exact validator invocation exited
zero but returned only `70/72` checks:

- `utf8_lf_final_newline` failed because the fresh audit worktree had
  `core.autocrlf=true` and converted the five packet blobs from LF to CRLF.
- `g1_receipt_raw_binding` failed because the same checkout converted the
  expected G1 blob from `6003` bytes / SHA-256
  `7fac9ee1377ad183f12d3acb04061700d5218642d809dd54fe35ad79388605b1` to
  `6143` bytes / SHA-256
  `cedddcd5e7237703583dbf432c3d2297bb908f61868db26abe83348cf55543fc`.

An in-memory normalization check showed that all six working-tree files become
byte-identical to their immutable Git blobs after CRLF→LF normalization.  This
establishes one root cause for both findings; it is not evidence of a dataset,
Docker daemon, WSL, training, or metric failure.  The audit also confirmed that
the subject tree contains no compatible R6-C1R3 execution runner.  The older
`execute_e4_r6_materialization.py` consumes a different Windows packet contract
and is not an authorized substitute.

## Chosen minimal remediation

1. Add the repository-root `.gitattributes` rules in this central commit.  The
   exact byte-bound R6-C1R3 packet, its builder/validator, the central receipt,
   and the G1 receipt are marked `-text`; no checkout may perform EOL
   conversion, regardless of a user's `core.autocrlf` setting.
2. Preserve commit `210c1ed...`, its packet files, and the failed audit as
   immutable history.  Create a new packet revision that carries the policy
   and binds the exact raw Git blobs again.  Do not repair the old checkout or
   reuse its failed attempt.
3. Add a fresh static regression check at the central gate: for each bound
   artifact, `git cat-file blob <commit>:<path>` must equal the bytes that the
   validator will execute/read.  A mismatch is a hard fail; normalization in
   the validator is not an acceptable workaround.
4. Build a minimal R6-C1R3 Linux materialization runner in the central
   lineage.  It must consume only the frozen literal argv records, verify the
   central and fresh-audit bindings before root creation, use `shell=False`,
   stop on the first non-zero/timeout/postcondition failure, and never retry or
   fall back to the legacy Windows runner.  Its implementation and tests are
   separate from the scientific runtime task.

## Required gate sequence

1. Central static validation of the new packet revision, including the EOL
   regression and the G1 raw binding; target is `72/72` (or the revision's
   explicitly frozen count), with `RESULT_STATUS=NOT_RUN`,
   `TEST_SET_OPENED=NO`, and `ACCEPTED_RESULT_ROWS=0`.
2. Fresh independent XHigh Standard audit in a newly created context.  The
   auditor may inspect and test statically but may not repair files, start
   Docker/WSL, download data, or run the runner.
3. Central runner static validation and exact-command authorization.  The
   absence of a compatible runner remains a blocker until this step passes.
4. Open a separate runtime context only after both receipts and the exact
   command binding pass.  Run the new `attempt-004-linux` materialization
   lanes once; do not open the project TEST set and do not train/evaluate in
   this gate.
5. If runtime fails, close that immutable attempt, retain its evidence, and
   return to this central context for diagnosis and a new attempt/plan.  Never
   retry the failed attempt in place.

## Acceptance and truth conditions

The remediation is complete only when the fresh checkout reproduces the raw
Git packet/G1 hashes, the new runner has an independent audit receipt, and the
runtime lane produces typed M0/M1 receipts.  Until then the authoritative
scientific state remains:

```text
RESULT_STATUS=NOT_RUN
TEST_SET_OPENED=NO
ACCEPTED_RESULT_ROWS=0
execution_authorized=false
phase_1e_complete=false
project_benchmark_numbers=INVALID_FOR_PAPER
```

No benchmark number may be imported into the paper from this remediation.
