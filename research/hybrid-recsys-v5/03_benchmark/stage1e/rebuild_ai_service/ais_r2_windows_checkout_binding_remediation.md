## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: run
- Origin Date: 2026-09-02T13:28:03Z
- Verification Status: UNVERIFIED
- Version Label: ais-r2-windows-checkout-binding-remediation-v1.0.0
- Upstream Dependencies: ais-r2-source-export-handoff-v1.0.0, ais-r2-catalog-private-research-authorization-v1.0.0
- Repro Lock: parent commit `03fb6cf0f78d8ce111ed8fec4e4831de454f8530`; regression command `node --test ai-service-v2/tools/tests/export_v5_source_bundle.test.cjs`
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# Windows checkout binding remediation

## Preflight result

The first runtime preflight stopped before opening a database connection. Disk
capacity passed (`C:` 24.21 GiB free; `E:` 112.64 GiB free), but generator
binding returned:

```text
generator source differs from
03fb6cf0f78d8ce111ed8fec4e4831de454f8530:
backend/docs/chatbot/seed-product/benchmark-lib.js
```

No Source Bundle root, database transaction, model run, benchmark row, or TEST
access was created. This preflight is not an experiment attempt and is retained
as a corrected admission finding.

## Reproduction and root cause

The minimized regression fixture creates a temporary Git repository, commits
an LF JavaScript file, restores a clean CRLF checkout under `core.autocrlf`, and
passes it through the production binding seam. Before remediation, the fixture
failed deterministically even though Git reported the checkout clean.

Ranked hypotheses were:

1. Windows clean-checkout LF-to-CRLF conversion changed raw bytes.
2. A generator source was genuinely modified.
3. The declared source commit resolved to a different file.
4. A BOM or unrelated encoding conversion was present.

The evidence confirmed hypothesis 1. For `benchmark-lib.js`, the committed and
working inputs had the same Git object ID
`3f436eefe00e6c214154fba54ddd22ef7b2cc860`, while their raw checkout sizes and
SHA-256 values differed solely because the working representation used CRLF.

## Correction

- Working files are now passed through Git's path-aware clean filter and
  compared by object identity with `sourceCommit:path`.
- A genuine content edit still produces a different object ID and fails.
- The generator tree and original spec hashes written to the Source Bundle are
  computed from committed Git blob bytes, not platform-dependent checkout
  bytes.
- The source-export core receives these prevalidated hashes; it cannot silently
  recompute a Windows-specific tree.

The regression test and the five existing exporter tests pass after the fix.
The correction does not relax source lineage, catalog rights, TLS, run status,
output immutability, dataset suitability, training, or TEST gates.

## Runtime disposition

The failed preflight command must not be reused as evidence of admission. After
this remediation is committed and all static gates pass, a new read-only
preflight may be run. If that preflight fails for a different reason, the
runtime stops without automatic retry.
