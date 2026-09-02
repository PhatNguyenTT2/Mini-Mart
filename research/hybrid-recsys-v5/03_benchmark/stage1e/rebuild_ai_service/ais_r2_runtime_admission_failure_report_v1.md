## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: run
- Origin Date: 2026-09-02T13:45:46Z
- Verification Status: UNVERIFIED
- Version Label: ais-r2-runtime-admission-failure-report-v1.0.0
- Upstream Dependencies: ais-r2-source-export-handoff-v1.0.0, ais-r2-catalog-private-research-authorization-v1.0.0, ais-r2-windows-checkout-binding-remediation-v1.0.0
- Repro Lock: source commit `1131e18d2a952855ceb128b4c472dba3a1c300e5`; catalog audit SHA-256 `94b4a5cb582a694860662fb7135f1f216bb4863119ffdea4561384e0de5fb884`; CA DER SHA-256 `807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa`
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# AIS-R2 runtime admission failure report

## Outcome

The private-research catalog authorization and Windows Git binding remediation
are accepted for AIS-R2. All static gates and the clean Git-archive replay pass.
The Source Bundle export nevertheless remains blocked before an attempt is
created because the required Supabase project bindings are not currently
resolvable by the provider.

No data query, source bundle, model training, benchmark row, or TEST access
occurred. Scientific state remains `RESULT_STATUS=NOT_RUN`,
`TEST_SET_OPENED=NO`, and `ACCEPTED_RESULT_ROWS=0`.

## What was resolved

1. The catalog may be exported for private research under the exact approved
   four-field projection. Redistribution remains prohibited.
2. The Windows CRLF checkout false positive was fixed and replayed from a clean
   Git archive.
3. A `Supabase Root 2021 CA` trust input was obtained outside Git. Its
   self-signature, validity, and SHA-256 fingerprint were checked. Both live
   Supabase pooler endpoints presented chains ending in that exact root.
4. The supplied CA moved the connection beyond TLS certificate validation.

Supabase's current guidance recommends `verify-full` and a downloaded project
CA. It does not support treating encrypted-but-unverified `require` mode as
equivalent to hostname and CA verification. The runtime therefore did not fall
back to `rejectUnauthorized=false`.

## Remaining blocker

With verified TLS active, the chat database pooler returned PostgreSQL code
`XX000` and the sanitized message `(ENOTFOUND) tenant/user <redacted> not
found`. The project references inferred from all three required database URLs
also had no direct `db.<project-ref>.supabase.co` DNS record. The same condition
was observed for both `backend/.env` and `backend/.env.prod`.

This evidence is consistent with stale connection strings, paused/restoring
projects, or deleted projects. It is not consistent with a Docker, WSL,
catalog-rights, source-code, or CA-validation failure. Dashboard state could
not be inspected because the available browser session is not signed in, and
the Supabase CLI is not installed.

## Minimal resume path

1. Sign in to the Supabase dashboard and verify that the projects backing the
   chatbot, catalog, and order databases are active.
2. Restore paused projects or replace the three database URLs in the local
   `backend/.env` with current Session Pooler/direct connection values. Secrets
   must not be committed.
3. Replay one verified-TLS, read-only preflight. It must open `REPEATABLE READ
   READ ONLY`, discover an immutable `ready` benchmark run, and close cleanly.
4. Only then execute one fresh Source Bundle export. The output and staging
   roots must not already exist.

The export must not be retried against the present bindings. A new preflight is
required after external project or credential state changes.
