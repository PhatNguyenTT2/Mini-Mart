# E4-R6 Fallback Distribution Plan — MovieLens 100K

## Material Passport

- Origin Skill: `deep-research`
- Origin Mode: `fact-check`
- Origin Date: `2026-09-03T17:20:02+07:00`
- Verification Status: `UNVERIFIED`
- Version Label: `e4_r6_fallback_distribution_plan_v1`
- Upstream Dependencies: `e4_r6_s0_frozen_input_manifest`, `rebaseline_v2_e4_r6_s0_gate_receipt`, `e4_r5_candidate_lock`
- Repro Lock: `null` (planning artifact; no bytes acquired)

## Decision summary

This document opens a controlled transport-candidate lane for the public
MovieLens 100K reference dataset. It does not change the selected RecBole
source, does not replace the GroupLens authority, and does not authorize an
acquisition or experiment.

The primary lane remains the canonical GroupLens surface:

- dataset page: `https://grouplens.org/datasets/movielens/100k/`
- archive: `https://files.grouplens.org/datasets/movielens/ml-100k.zip`
- checksum sidecar: `https://files.grouplens.org/datasets/movielens/ml-100k.zip.md5`

The archive and checksum host currently present a certificate-validation
failure in the observed browser session (`ERR_CERT_DATE_INVALID`). The
alternate University of Minnesota host is indexed as a MovieLens 100K page,
but its certificate currently fails hostname validation
(`ERR_CERT_COMMON_NAME_INVALID`). Neither failure may be bypassed.

The fallback lane therefore has the following current verdict:

```text
FALLBACK_PLAN_READY_NO_SOURCE_ADMITTED
RESULT_STATUS=NOT_RUN
TEST_SET_OPENED=NO
ACCEPTED_RESULT_ROWS=0
execution_authorized=false
phase_1e_complete=false
```

The fallback is for the reference dataset used to reproduce the official
public-data protocol. It is not a replacement for the project dataset
(5,200 SKUs / approximately 5,000 users), and it does not alter the latter's
lineage.

## Non-negotiable boundaries

1. The pinned source revision remains
   `9a6f63d8d4a5b989fe27955a833f813a6d86041e`.
2. A mirror is a transport candidate, not automatically a dataset authority.
3. No HTTP, `--insecure`, certificate bypass, unverified proxy, or silent
   fallback is allowed.
4. No archive was downloaded, extracted, installed, trained, evaluated, or
   opened against the project TEST set while this plan was prepared.
5. No candidate is benchmark-admitted until every gate below passes.
6. Official-protocol reproduction and harmonized-v5 results remain separate
   namespaces and separate result tables.
7. Existing failed attempts and the untracked manuscript directory are
   preserved; this plan does not clean, overwrite, or reinterpret them.

## Candidate lanes and intended use

| Priority | Surface | Current classification | Permitted now |
|---|---|---|---|
| 0 | GroupLens canonical page/files | `OFFICIAL_PRIMARY_PENDING_TLS` | Cite as authority; wait for a valid TLS retrieval |
| 1 | `cse-movie-teapot.cs.umn.edu` | `OFFICIAL_OWNER_ALTERNATE_HOST_PENDING_TLS_AND_BYTE_REPLAY` | Re-check only after valid TLS; no acquisition yet |
| 2 | Internet Archive capture of the GroupLens URL | `ELIGIBLE_PENDING_BYTE_EQUIVALENCE` | Preserve as a possible transport candidate; no paper result |
| 3 | Hugging Face upload | `NONAUTHORITATIVE_DIAGNOSTIC_ONLY` | Schema/fixture inspection after a separate authorization |
| 4 | Kaggle upload | `NONAUTHORITATIVE_DIAGNOSTIC_ONLY` | Metadata comparison only |
| 5 | TensorFlow Datasets | `TRANSFORMED_DIAGNOSTIC_ONLY` | Adapter/schema smoke tests only |
| 6 | D2L documentation | `DOCUMENTATION_ONLY` | Corroborate the canonical URL and published checksum reference |
| 7 | Netzschleuder network artifact | `REJECTED_FOR_OFFICIAL_REPRODUCTION` | No use for the raw rating benchmark |
| 8 | RecBole processed-data S3 route | `PROCESSED_NONAUTHORITATIVE_DIAGNOSTIC_ONLY` | Do not use as raw official data |

The numeric priority is an investigation order, not an automatic selection
order. The central context must issue a new admission decision for any actual
acquisition.

## Evidence observed during the discovery wave

The candidate register records the URLs, locators, observed facts, and
unresolved gaps in machine-readable form. The important observations are:

- The GroupLens page identifies MovieLens 100K as a stable benchmark, links to
  `ml-100k.zip`, a checksum sidecar, and an unzipped-file index.
- The expected canonical archive identity is 4,924,029 bytes with MD5
  `0e33842e24a9c977be4e0107933c0723`; the release label is 4/1998, with
  100,000 ratings, 943 users, and 1,682 movies.
- Google-indexed results identify the University of Minnesota alternate host
  and the same MovieLens 100K description, but the host cannot currently be
  read through a valid certificate. The exact archive href must be read from a
  valid page rather than guessed.
- The Internet Archive CDX observation contains a 20260721193850 capture with
  WARC digest `ZVG4VRBEDSFEVV523R6KMNO2RJU53W4D` and a CDX record length of
  4,924,759 bytes. A CDX/WARC record length is not the canonical ZIP payload
  size, so byte equivalence remains unproved.
- The Hugging Face upload exposes 23 files and an approximately 16.1 MB
  repository, but has no provider checksum or GroupLens authorization. Its
  card reproduces terms that prohibit redistribution; the host's displayed
  Apache-2.0 label does not resolve that conflict.
- The Kaggle card repeats the GroupLens facts and terms, but its CC0 label does
  not establish that the uploader had authority to redistribute the data.
- TFDS exposes a transformed `100k-ratings`/`100k-movies` representation and
  attributes collection and maintenance to GroupLens, but it is not the raw
  GroupLens ZIP and has no raw-byte equivalence receipt.
- D2L points consumers back to GroupLens and records a SHA-1 reference in its
  code sample; it is a consumer document, not an independent distribution
  authority.
- Netzschleuder is a transformed network artifact. Its page reports 24,129
  nodes and 95,580 edges and points upstream to KONECT's
  `movielens-10m_ti`, which is not the raw ML-100K archive.

## Admission gate for a transport candidate

A candidate can be used to materialize the official reference dataset only if
all of the following checks pass in one fresh, separately identified attempt:

### A. Secure retrieval and URL identity

- HTTPS certificate chain and hostname validation pass.
- Final URL, redirects, response metadata, and retrieval timestamp are
  recorded.
- No TLS bypass, HTTP downgrade, or unverified mirror redirect is used.

### B. Exact archive identity

- Payload size is exactly `4,924,029` bytes.
- Provider MD5 is exactly
  `0e33842e24a9c977be4e0107933c0723`.
- A local SHA-256 is calculated and recorded.
- The checksum is obtained from an authoritative sidecar or an independently
  justified, immutable provider record; a search snippet alone is not enough.

### C. Archive and extraction lineage

- ZIP inventory is exactly the expected 23-file ML-100K inventory.
- Every member's path, size, and hash is recorded before conversion.
- `README`, `u.data`, `u.item`, `u.user`, and the predefined split files are
  present and internally consistent.
- Raw-to-RecBole conversion produces only the declared atomic input and keeps
  a hash-bound mapping from raw IDs to internal IDs.
- Reconciliation confirms 100,000 ratings, 943 users, and 1,682 movies; any
  discrepancy closes the attempt as `INCOMPLETE` or `REJECTED`.

### D. Provenance and rights

- The candidate is shown to be a copy of the same GroupLens ML-100K release,
  not merely a dataset with the same name and cardinalities.
- The release date/label and file inventory are consistent with the canonical
  source.
- The permission to retrieve and use the bytes for research is documented
  separately from checksum evidence. A host's self-declared license is not
  treated as proof of redistribution authority.

### E. Reproduction binding

- RecBole source, configuration, split, seed, checkpoint rule, and evaluator
  remain those of the locked official protocol.
- The transport candidate never changes the metric implementation or tolerance.
- If exact byte equivalence is demonstrated, the result may be recorded as a
  GroupLens-source reproduction using an alternate transport, with the
  transport and equivalence receipt disclosed. If equivalence is not proven,
  the row is `INCOMPARABLE` or diagnostic only.

## Minimal execution sequence after central admission

1. Central reviews this plan and the candidate register; no acquisition occurs
   before that review.
2. Central opens a new acquisition attempt root. Failed attempts are not
   reused.
3. The approved HTTPS URL is retrieved once with normal certificate
   validation; the final URL and response metadata are frozen.
4. Size, MD5, SHA-256, ZIP inventory, rights record, and raw-to-RecBole
   reconciliation are produced before any model execution.
5. An independent source/lineage check replays the receipts.
6. Only a passing candidate can enter the later environment/materialization
   gate. Official reproduction remains a separate subsequent gate.

No retry or candidate substitution is implicit in these steps. A failed
attempt is closed with a failure receipt and a new plan is required for a new
attempt.

## Failure handling

| Failure | Disposition |
|---|---|
| Certificate or hostname failure | Close candidate as pending; do not bypass TLS |
| Unknown archive href | Do not guess; re-read the valid owner page later |
| Size/MD5 mismatch | Reject for official reproduction; quarantine evidence and preserve receipt |
| ZIP inventory mismatch | `INCOMPARABLE` or reject; no conversion into the official namespace |
| Rights/authority unresolved | Diagnostic only; no paper benchmark |
| Transformed representation only | Use only in a separately named diagnostic lane |
| Docker/WSL failure during later execution | Close that execution attempt; do not silently switch dataset or source |
| No candidate passes | Keep official reproduction sealed; continue only with non-result unit/fixture work |

## What can proceed without a passing fallback

The following work can continue on the project dataset or synthetic fixtures,
without creating a paper benchmark row:

- `ai-service-v2` schema and manifest validation;
- shared evaluator and deterministic ranking fixtures;
- leakage, masking, tie-breaking, and score-shape tests;
- adapter/interface work that does not claim MovieLens reproduction;
- a dataset-suitability report for the 5,200-SKU project snapshot.

The following must remain sealed until a valid reference source is admitted:

- official RecBole BPR/ML-100K reproduction;
- use of `NDCG@10=0.2768` as a paper baseline;
- accepted benchmark rows;
- harmonized-v5 TEST execution and Phase 1E seal.

## Controlled outputs and write policy

This discovery wave writes only the following control artifacts:

- `e4_r6_fallback_distribution_plan.md` (this file);
- `e4_r6_fallback_candidate_register.json`;
- `e4_r6_fallback_handoff.json`.

No `pipeline_state_stage1e.json`, manuscript file, prior attempt, source tree,
dataset root, Docker/WSL setting, or benchmark result is modified. The
untracked `05_manuscript/` directory is outside the write set and is preserved.

## Next gate

`R6-FALLBACK-CENTRAL-REVIEW` is the next gate. It may either:

1. keep the primary GroupLens lane pending and wait for valid TLS;
2. authorize a fresh read-only verification of the UMN alternate page after
   its certificate is valid; or
3. authorize one explicitly named archival/mirror acquisition attempt with the
   full byte/provenance/rights gate above.

Until that decision is recorded, the fallback is a documented contingency,
not an execution path and not a benchmark result.
