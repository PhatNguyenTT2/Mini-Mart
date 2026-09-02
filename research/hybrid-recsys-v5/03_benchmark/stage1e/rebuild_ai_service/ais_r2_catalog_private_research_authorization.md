## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: run
- Origin Date: 2026-09-02T13:12:00Z
- Verification Status: UNVERIFIED
- Version Label: ais-r2-catalog-private-research-authorization-v1.0.0
- Upstream Dependencies: ais-r2-catalog-rights-language-audit-v1.0.0, ais-r2-source-export-contract-v1.1.0
- Repro Lock: null
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# Project-controller authorization

## User authorization

On 2026-09-02, the project user explicitly instructed:

> “Có thể chấp thuận bằng chứng và sử dụng ngay. Tiếp tục bước kế tiếp theo plan (mở runtime).”

For this research pipeline, that instruction is recorded as authorization from
the project/dataset controller to use the existing project-controlled catalog
and generated benchmark data for private academic research execution.

## Authorized scope

- Read the locked benchmark run from the chatbot, catalog, and order databases.
- Export only product name, category, vendor, and price, plus generated numeric
  benchmark IDs and generated interaction/order fields required by AIS-R2.
- Materialize and audit an immutable internal Dataset Snapshot.
- Use the admitted snapshot in subsequent private benchmark experiments after
  all dataset, protocol, environment, and TEST gates separately pass.
- Publish aggregate statistics, methodological descriptions, and artifact
  hashes that do not reconstruct the raw catalog.

## Restrictions

- Raw product metadata and Source Bundle rows are not authorized for public
  redistribution.
- No auth database, customer profile, name, account, phone, email, address, or
  other personal attribute is authorized for access or export.
- This project-controller declaration is not represented as permission from
  Bách Hóa Xanh, an open-data license, or a legal determination about the
  upstream website content.
- The interaction stream remains controlled/generated behavior and must not be
  described as observed customer behavior.
- Language coverage remains pending until it is measured on the exact exported
  5,200-item artifact.

## Gate effect

This authorization satisfies the internal private-research access decision for
`catalog-audit/1.1`. It does not by itself admit the dataset, authorize public
redistribution, open TEST, run training, or create an Accepted Result Row.
