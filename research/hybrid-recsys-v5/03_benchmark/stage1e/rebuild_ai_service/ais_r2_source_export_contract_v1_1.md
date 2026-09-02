## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-02T13:00:18Z
- Verification Status: UNVERIFIED
- Version Label: ais-r2-source-export-contract-v1.1.0
- Upstream Dependencies: ais-r2-source-bundle-contract-v1.0.0, ais-r2-source-admission-v1.0.0, ais-r2-catalog-rights-language-audit-v1.0.0
- Repro Lock: generator-tree `c3c4ba019308ed4d4984220ff3088aa2893e70cb78b56f8e9cf0c19c67befe00`; query-contract `fe8acb87f925dae04bfc5b9872338cdd9ea165f88275ee8665692badf08d9e1f`
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# AIS-R2 bounded source-export contract v1.1

## Scope

This amendment defines the database-facing edge that may create a candidate v5
Source Bundle. It supersedes only the runtime-export and manifest-version parts
of `ais-r2-source-bundle-contract-v1.0.0`; the canonical Dataset Snapshot,
organic-truth, TRAIN-basket, and TEST-seal rules remain unchanged.

The exporter is evidence preparation, not benchmark execution. It must not run
a generator, reset data, train a model, evaluate a model, open TEST, or create
an Accepted Result Row.

## Catalog access receipt

Before any database connection, the exporter requires one UTF-8
`catalog-audit/1.1` document serialized as canonical JSON plus exactly one LF.
It contains exactly:

```text
schema_version
catalog_provenance_status
catalog_license_status
catalog_language_status
export_authorized
redistribution_authorized
approved_fields
evidence_sha256
```

For a real export:

- provenance is exactly `VERIFIED`;
- license is exactly `APPROVED_PRIVATE_RESEARCH`,
  `APPROVED_RESEARCH_AND_REDISTRIBUTION`, or `OPEN_LICENSE_VERIFIED`;
- `export_authorized` is true;
- `redistribution_authorized` agrees with the license scope;
- approved fields are exactly `category`, `name`, `price`, and `vendor`;
- at least one immutable evidence SHA-256 is present;
- language is either `AUDITED` or `PENDING_POST_EXPORT_AUDIT`.

Prefix-like values such as `VERIFIED_BUT_PENDING` do not pass. A hash supplied
to the exporter must equal the canonical receipt bytes.

`PENDING_POST_EXPORT_AUDIT` resolves a necessary gate ordering: an authorized,
private item projection must exist before its 5,200 titles can be audited. Such
an export is quarantine evidence only. The resulting snapshot remains
scientifically inadmissible, and the CLI refuses training, until a language
audit is bound and the final dataset-suitability gate passes.

`TEST_ONLY` is accepted only when the declared source commit is forty zeroes,
all three catalog statuses are exactly `TEST_ONLY`, and redistribution is
false. This lane is a fixture and never paper evidence.

## Source and run binding

The real command must use the repository file
`backend/docs/chatbot/seed-product/benchmark-spec-v5.json`. The full lowercase
Git commit is not trusted as a label: each of the nine declared generator files
is read from that commit and compared byte-for-byte by SHA-256 with the working
input before a database connection.

The benchmark run must satisfy all of the following in one read-only view:

- exactly one row for the requested store and run;
- status `ready` and non-null publication time;
- exact seed, canonical full-spec hash, split boundaries, and event count;
- run ID derived from generator major version, seed, catalog hash, and spec
  hash;
- exact equality between catalog and item-partition ID sets;
- exact user, item, event, split, basket, and cold-item counts;
- exact event/basket order, valid origins, known IDs, and TRAIN-only baskets.

## Database and privacy boundary

Exactly three PostgreSQL clients are used:

- chatbot: benchmark-run, item-partition, and generated interaction rows;
- catalog: product/category projection;
- order: generated benchmark orders and details.

The auth database is never connected. Customer names, accounts, phones,
emails, addresses, demographics, and profile attributes are not selected.
Generated numeric benchmark user IDs are retained only to preserve joins and
must not be described as verified customers.

Each client starts `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ
ONLY`. The query contract contains no data mutation or DDL. Remote connections
require a supplied CA with certificate verification enabled; insecure TLS and
silent fallback are forbidden.

The three databases cannot share one PostgreSQL snapshot. Cross-service
consistency therefore relies on the immutable benchmark run ID, its published
`ready` state, exact counts, and hashes. A mismatch closes the attempt.

## Output and limitations

A successful fresh attempt atomically publishes exactly six files under a new
root:

```text
source_manifest.json
benchmark_spec.json
users.jsonl
items.jsonl
events.jsonl
baskets.jsonl
```

Source Bundle schema `v5-source-bundle/1.1` additionally binds the exact access
receipt and every receipt-evidence hash. Existing output or staging roots are
rejected; failure removes only the newly created staging root.

The benchmark-run catalog checksum covers product ID, category ID, and product
name. It does not establish that vendor, price, or category display name are
generation-time values. Those fields are classified as export-time metadata
unless a stronger historical snapshot is later produced. Their exported bytes
remain protected by the Source Bundle file hashes, but claims about historical
prices or vendors are prohibited.

## Gate result

Static tests may establish that the exporter follows this contract. They do
not authorize the real command. Runtime remains blocked until the catalog
access receipt, locked ready run ID, database/TLS preflight, fresh output root,
and exact command are separately admitted.
