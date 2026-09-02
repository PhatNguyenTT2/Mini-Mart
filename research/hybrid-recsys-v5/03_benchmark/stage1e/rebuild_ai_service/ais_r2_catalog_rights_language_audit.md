## Material Passport

- Origin Skill: academic-research-suite/experiment-agent
- Origin Mode: evidence
- Origin Date: 2026-09-02T05:53:53Z
- Verification Status: UNVERIFIED
- Version Label: ais-r2-catalog-rights-language-audit-v1.0.0
- Upstream Dependencies: ais-r2-source-bundle-contract-v1.0.0, local-catalog-seed@7b9361f4
- Repro Lock: null; real 5,200-item export and permission evidence pending
- Experiment Intake Declaration: experiments_declared at 2026-09-01T16:38:56Z by scholar

# Catalog provenance, rights, privacy, and language audit

## Verdict

```text
CATALOG_PROVENANCE_STATUS = PARTIAL_LOCAL_EVIDENCE
CATALOG_LICENSE_STATUS    = PENDING_AFFIRMATIVE_PERMISSION_OR_REPLACEMENT
CATALOG_LANGUAGE_STATUS   = PENDING_REAL_SNAPSHOT_AUDIT
PII_EXPORT_STATUS         = PASS_BY_EXPORT_SCHEMA
OVERALL_VERDICT           = INCOMPLETE_CATALOG_AUDIT
```

This verdict blocks creation of an admitted `catalog-audit/1.1` access receipt and
therefore blocks a real Source Bundle export. It does not claim that research
use is prohibited; it records that the current evidence is insufficient to
authorize redistribution or a public-dataset claim.

## Evidence examined

### Local source evidence

The catalog seed declares that it was generated from a scraped Bách Hóa Xanh
product/category catalog. The file contains product names, categories, vendors,
prices, and remote image URLs.

```text
path   = backend/services/catalog/src/db/seed-1000.sql
sha256 = 7b9361f47fbc552cab3997672cabe7883b3c058f7e811d2e6e14b98062207c79
scope  = historical/local seed evidence; not a license and not a complete
         immutable snapshot of the current 5,200-item catalog
```

The repository does not contain a source manifest explaining how the catalog
grew from this seed to exactly 5,200 products, nor a field-level acquisition
date, original URL inventory, permission letter, or redistribution license.

### Official public pages checked on 2026-09-02

- `https://www.bachhoaxanh.com/chinh-sach-sieu-thi`
- `https://www.bachhoaxanh.com/privacy-policy-app.html`
- `https://www.bachhoaxanh.com/gioi-thieu`

The official pages identify Công Ty Cổ Phần Thương Mại Bách Hóa Xanh as the
operator, display a copyright notice and contact channel, and describe website,
application, and privacy policies. The retrieved evidence did not provide an
affirmative open-data or content-redistribution license for product metadata.
The privacy policy addresses personal information and does not establish reuse
rights for the product catalog.

Absence of an identified open license is not proof that no permission can be
obtained. It is sufficient, however, to keep `catalog_license_status` pending
under a fail-closed research workflow.

## Privacy and PII boundary

The Source Bundle exporter reads numeric generated user IDs only from benchmark
events/orders. It does not connect to the auth database and does not export
customer name, account ID, phone, email, address, gender, date of birth, or
other profile attributes. Generated numeric identities must still be described
as generated benchmark IDs, not verified customers.

## Gate ordering and language evidence still required

The access receipt must verify provenance and authorize the exact private
research export fields before any database connection. Language status may
then be `PENDING_POST_EXPORT_AUDIT`: the immutable item projection is the
necessary input to the audit. That pending status allows only source export and
canonical materialization; it does not admit the Dataset Snapshot, open TEST,
or authorize training. This ordering removes a circular dependency without
relaxing the final evidence gate.

Vietnamese-looking product titles in the local seed establish plausibility, not
coverage. After an authorized 5,200-item export, the audit must report:

- non-empty title/category/vendor coverage;
- normalized duplicate and collision rates;
- Vietnamese language-ID rate with model/version/hash and confidence policy;
- a stratified manual review sample and disagreement handling;
- counts for original catalog items, controlled additions, and semantic-trap
  items;
- whether price and vendor are generation-time or export-time metadata.

Until those checks pass, the paper may say only “Vietnamese-language retail
catalog context” as a design intention, not as an audited dataset fact.

## Resolution paths

1. Obtain written permission that states allowed research use, publication, and
   redistribution fields; hash and archive the permission receipt.
2. If redistribution is not authorized, keep raw catalog bytes private and
   define exactly which derived artifacts/hashes may be published, subject to
   institutional approval.
3. Replace the product metadata with an openly licensed public source or a
   disclosed synthetic catalog, creating a new dataset version and lineage.

No option permits relabeling scraped metadata as public/open without affirmative
evidence. Dataset replacement or field removal requires a versioned amendment;
v5 is never modified in place after TEST access.
