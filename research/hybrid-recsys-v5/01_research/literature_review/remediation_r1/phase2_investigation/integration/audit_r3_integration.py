#!/usr/bin/env python3
"""Independent, fail-closed audit of the generated R3 ten-output contract.

The receipt is embedded in r3_handoff.json so the fixed required-output roster
remains ten files.  The handoff itself is excluded from its embedded output
manifest to avoid a self-hash cycle.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[6]
REMEDIATION = HERE.parents[1]
LANES = REMEDIATION / "phase2_investigation" / "lanes"
SOURCE_SCHEMA_PATH = REMEDIATION / "00_control" / "source_schema_r1.json"
ARS_CORPUS_SCHEMA_PATH = Path(
    r"C:\Users\ACER\.codex\plugins\cache\ars-codex\ars-codex\0.1.26\skills\academic-research-suite\ars\shared\contracts\passport\literature_corpus_entry.schema.json"
)
AUDIT_TIMESTAMP = "2026-08-21T00:00:00+07:00"

REQUIRED_OUTPUTS = [
    "source_registry_r1.json",
    "operational_resource_registry.json",
    "source_family_map_r1.json",
    "deduplication_report_r1.md",
    "source_quality_matrix_r1.json",
    "source_verification_report_r1.md",
    "literature_corpus_r1.json",
    "annotated_bibliography_r1.md",
    "claim_source_map_r1.md",
    "r3_handoff.json",
]
JSON_OUTPUTS = [name for name in REQUIRED_OUTPUTS if name.endswith(".json")]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").casefold().replace("²", "2")
    return " ".join(re.findall(r"[a-z0-9]+", value))


def norm_doi(value) -> str | None:
    if not value:
        return None
    value = str(value).strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return re.sub(r"^doi:\s*", "", value).rstrip(" .") or None


failures = []
checks = []


def check(name: str, condition: bool, observed=None, expected=None, detail: str | None = None) -> None:
    row = {
        "check": name,
        "status": "PASS" if condition else "FAIL",
        "observed": observed,
        "expected": expected,
    }
    if detail:
        row["detail"] = detail
    checks.append(row)
    if not condition:
        failures.append({"check": name, "observed": observed, "expected": expected, "detail": detail})


# 1. Required output and JSON parse gate.
missing = [name for name in REQUIRED_OUTPUTS if not (HERE / name).is_file()]
check("required_outputs_exist", not missing, missing, [])
docs = {}
parse_errors = []
for name in JSON_OUTPUTS:
    try:
        docs[name] = load(HERE / name)
    except Exception as exc:  # receipt must list exact parse failures
        parse_errors.append({"path": name, "error": f"{type(exc).__name__}: {exc}"})
check("all_required_json_parses", not parse_errors, parse_errors, [])

if parse_errors or missing:
    # A malformed handoff may not be writable safely; emit a separate console
    # failure and stop without pretending the embedded receipt exists.
    raise SystemExit(json.dumps({"result": "FAIL", "failures": failures}, ensure_ascii=False, indent=2))

registry = docs["source_registry_r1.json"]
ops = docs["operational_resource_registry.json"]
families = docs["source_family_map_r1.json"]
quality = docs["source_quality_matrix_r1.json"]
corpus_doc = docs["literature_corpus_r1.json"]
handoff = docs["r3_handoff.json"]
sources = registry["sources"]
resources = ops["resources"]
family_rows = families["families"]
dependencies = families["dependencies"]
quality_rows = quality["records"]
corpus = corpus_doc["literature_corpus"]
claims = handoff["claim_dispositions"]

# 2. Embedded non-self manifest integrity.
manifest = handoff.get("output_manifest", [])
manifest_names = [row.get("path") for row in manifest]
expected_manifest_names = REQUIRED_OUTPUTS[:-1]
check("embedded_manifest_roster", manifest_names == expected_manifest_names, manifest_names, expected_manifest_names)
manifest_failures = []
for row in manifest:
    path = HERE / row["path"]
    if not path.is_file():
        manifest_failures.append({"path": row["path"], "error": "missing"})
        continue
    actual = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    expected = {"bytes": row.get("bytes"), "sha256": row.get("sha256")}
    if actual != expected:
        manifest_failures.append({"path": row["path"], "actual": actual, "expected": expected})
check("embedded_manifest_bytes_and_sha256", not manifest_failures, manifest_failures, [])

# 3. Source schema shape and enum checks (independent of the producer).
schema = load(SOURCE_SCHEMA_PATH)["$defs"]
sch = schema["scholarly_work"]
op_schema = schema["operational_resource"]
shape_failures = []
for row in sources:
    missing_fields = [key for key in sch["required"] if key not in row]
    if missing_fields:
        shape_failures.append({"source_key": row.get("source_key"), "missing": missing_fields})
        continue
    if row.get("record_type") != "scholarly_work":
        shape_failures.append({"source_key": row.get("source_key"), "field": "record_type", "value": row.get("record_type")})
    for field in ("document_type", "publication_status", "peer_reviewed"):
        allowed = sch["properties"][field]["enum"]
        if row.get(field) not in allowed:
            shape_failures.append({"source_key": row["source_key"], "field": field, "value": row.get(field), "allowed": allowed})
    if not isinstance(row.get("publication_year"), int) or not 1900 <= row["publication_year"] <= 2026:
        shape_failures.append({"source_key": row["source_key"], "field": "publication_year", "value": row.get("publication_year")})
    if not row.get("authors") or not all(isinstance(x, str) and x.strip() for x in row["authors"]):
        shape_failures.append({"source_key": row["source_key"], "field": "authors", "value": row.get("authors")})
    if not row.get("provenance") or not all(isinstance(x, str) for x in row["provenance"]):
        shape_failures.append({"source_key": row["source_key"], "field": "provenance", "value": row.get("provenance")})
    if not all(isinstance(x, str) for x in row.get("limitations", [])):
        shape_failures.append({"source_key": row["source_key"], "field": "limitations", "value": row.get("limitations")})
for row in resources:
    missing_fields = [key for key in op_schema["required"] if key not in row]
    if missing_fields:
        shape_failures.append({"resource_key": row.get("resource_key"), "missing": missing_fields})
        continue
    if row.get("record_type") != "operational_resource":
        shape_failures.append({"resource_key": row.get("resource_key"), "field": "record_type", "value": row.get("record_type")})
    for field in ("year_basis", "dataset_rights", "redistribution_status"):
        allowed = op_schema["properties"][field]["enum"]
        if row.get(field) not in allowed:
            shape_failures.append({"resource_key": row["resource_key"], "field": field, "value": row.get(field), "allowed": allowed})
    if not row.get("provenance") or not all(isinstance(x, str) for x in row["provenance"]):
        shape_failures.append({"resource_key": row["resource_key"], "field": "provenance", "value": row.get("provenance")})
check("source_schema_required_types_and_enums", not shape_failures, shape_failures, [])

# Validate the corpus against the applicable, additionalProperties=false ARS
# entry contract without relying on an uninstalled jsonschema dependency.
ars_corpus_schema = load(ARS_CORPUS_SCHEMA_PATH)
allowed_corpus_fields = set(ars_corpus_schema["properties"])
required_corpus_fields = set(ars_corpus_schema["required"])
corpus_shape_failures = []
for row in corpus:
    key = row.get("citation_key")
    missing_fields = sorted(required_corpus_fields - set(row))
    extra_fields = sorted(set(row) - allowed_corpus_fields)
    if missing_fields or extra_fields:
        corpus_shape_failures.append({"citation_key": key, "missing": missing_fields, "additional": extra_fields})
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_:-]*", key):
        corpus_shape_failures.append({"citation_key": key, "field": "citation_key", "error": "pattern"})
    if not isinstance(row.get("source_pointer"), str) or not row["source_pointer"].strip():
        corpus_shape_failures.append({"citation_key": key, "field": "source_pointer", "value": row.get("source_pointer")})
    if not isinstance(row.get("year"), int) or not 1000 <= row["year"] <= 2100:
        corpus_shape_failures.append({"citation_key": key, "field": "year", "value": row.get("year")})
    for author in row.get("authors", []):
        if not isinstance(author, dict) or set(author) != {"literal"} or not isinstance(author.get("literal"), str) or not author["literal"].strip():
            corpus_shape_failures.append({"citation_key": key, "field": "authors", "value": author})
    if row.get("obtained_via") == "other" and not row.get("adapter_name"):
        corpus_shape_failures.append({"citation_key": key, "field": "adapter_name", "error": "required_for_other"})
    doi = row.get("doi")
    if doi and not re.fullmatch(r"10\.[0-9]{4,9}/[^\s]+", doi):
        corpus_shape_failures.append({"citation_key": key, "field": "doi", "value": doi})
    signals = row.get("contamination_signals", {})
    omissions = row.get("contamination_signal_omissions", {})
    overlap = sorted(set(signals) & set(omissions))
    if overlap:
        corpus_shape_failures.append({"citation_key": key, "field": "contamination_signals", "overlap": overlap})
    if row.get("obtained_via") == "manual" and (set(signals) - {"preprint_post_llm_inflection"} or omissions):
        corpus_shape_failures.append({"citation_key": key, "field": "manual_lookup_exemption", "signals": signals, "omissions": omissions})
check("ars_v0_1_26_literature_corpus_entry_contract", not corpus_shape_failures, corpus_shape_failures, [])

# 4. Acquired artifact existence and exact hash.
artifact_failures = []
acquired_scholarly = [row for row in sources if row.get("source_acquired")]
acquired_operational = [row for row in resources if row.get("source_acquired")]
for kind, rows, key_name in (
    ("scholarly", acquired_scholarly, "source_key"),
    ("operational", acquired_operational, "resource_key"),
):
    for row in rows:
        rel = row.get("acquired_artifact")
        path = WORKSPACE / rel if rel else None
        if path is None or not path.is_file():
            artifact_failures.append({"kind": kind, "key": row[key_name], "path": rel, "error": "missing"})
            continue
        actual = sha256(path)
        if actual != row.get("acquired_artifact_sha256"):
            artifact_failures.append({"kind": kind, "key": row[key_name], "path": rel, "actual": actual, "expected": row.get("acquired_artifact_sha256")})
check(
    "all_acquired_artifacts_exist_and_hash_match",
    not artifact_failures,
    {"scholarly_checked": len(acquired_scholarly), "operational_checked": len(acquired_operational), "failures": artifact_failures},
    {"failures": []},
)

# 5. Identity uniqueness and reference graph.
source_keys = [row["source_key"] for row in sources]
resource_keys = [row["resource_key"] for row in resources]
family_ids = [row["source_family_id"] for row in family_rows]
titles = [norm_title(row["title"]) for row in sources]
dois = [norm_doi(row.get("doi")) for row in sources if norm_doi(row.get("doi"))]
duplicate_counts = {
    "source_keys": len(source_keys) - len(set(source_keys)),
    "titles": len(titles) - len(set(titles)),
    "dois": len(dois) - len(set(dois)),
    "resource_keys": len(resource_keys) - len(set(resource_keys)),
    "family_ids": len(family_ids) - len(set(family_ids)),
}
check("duplicate_canonical_identities", all(v == 0 for v in duplicate_counts.values()), duplicate_counts, {k: 0 for k in duplicate_counts})

source_set, resource_set, family_set = set(source_keys), set(resource_keys), set(family_ids)
dangling = []
for row in sources:
    if row["source_family_id"] not in family_set:
        dangling.append({"owner": row["source_key"], "field": "source_family_id", "value": row["source_family_id"]})
for row in resources:
    if row["source_family_id"] not in family_set:
        dangling.append({"owner": row["resource_key"], "field": "source_family_id", "value": row["source_family_id"]})
for row in family_rows:
    for key in row["scholarly_source_keys"]:
        if key not in source_set:
            dangling.append({"owner": row["source_family_id"], "field": "scholarly_source_keys", "value": key})
    for key in row["operational_resource_keys"]:
        if key not in resource_set:
            dangling.append({"owner": row["source_family_id"], "field": "operational_resource_keys", "value": key})
for edge in dependencies:
    for field in ("source_family_id", "depends_on_family_id"):
        if edge[field] not in family_set:
            dangling.append({"owner": "dependency", "field": field, "value": edge[field]})
    for key in edge["source_keys"]:
        if key not in source_set:
            dangling.append({"owner": "dependency", "field": "source_keys", "value": key})
    for key in edge["resource_keys"]:
        if key not in resource_set:
            dangling.append({"owner": "dependency", "field": "resource_keys", "value": key})
for claim in claims:
    for key in claim["canonical_source_keys"]:
        if key not in source_set:
            dangling.append({"owner": claim["claim_id"], "field": "canonical_source_keys", "value": key})
    for key in claim["operational_resource_keys"]:
        if key not in resource_set:
            dangling.append({"owner": claim["claim_id"], "field": "operational_resource_keys", "value": key})
    for key in claim["source_family_ids"]:
        if key not in family_set:
            dangling.append({"owner": claim["claim_id"], "field": "source_family_ids", "value": key})
check("dangling_source_family_resource_dependency_claim_references", not dangling, dangling, [])

# 6. Cross-output keyset agreement.
registry_set = set(source_keys)
quality_set = {row["source_key"] for row in quality_rows}
corpus_set = {row["citation_key"] for row in corpus}
selected_set = {row["source_key"] for row in sources if row["corpus_included"]}
family_scholarly_set = {key for row in family_rows for key in row["scholarly_source_keys"]}
family_resource_set = {key for row in family_rows for key in row["operational_resource_keys"]}
annotation_text = (HERE / "annotated_bibliography_r1.md").read_text(encoding="utf-8")
annotation_set = set(re.findall(r"^## ([A-Za-z0-9_-]+)\s*$", annotation_text, flags=re.MULTILINE))
claim_map_text = (HERE / "claim_source_map_r1.md").read_text(encoding="utf-8")
claim_map_ids = set(re.findall(r"^\| ([^|]+?) \| L[1-5] \|", claim_map_text, flags=re.MULTILINE))
claim_ids = {row["claim_id"] for row in claims}
keyset_observed = {
    "registry": len(registry_set), "quality": len(quality_set), "corpus": len(corpus_set),
    "selected": len(selected_set), "annotated": len(annotation_set), "family_scholarly": len(family_scholarly_set),
    "resources": len(resource_set), "family_resources": len(family_resource_set),
    "handoff_claims": len(claim_ids), "claim_map_claims": len(claim_map_ids),
}
keysets_agree = (
    registry_set == quality_set == family_scholarly_set and
    corpus_set == selected_set == annotation_set and
    resource_set == family_resource_set and
    claim_ids == claim_map_ids
)
check("cross_output_keysets_agree", keysets_agree, keyset_observed, {"registry_quality_family": 74, "corpus_selected_annotated": 52, "resources_family": 14, "claims": 44})

# 7. Prohibited fields, year, text-integrity, author, and peer-review gates.
prohibited = []


def scan_keys(value, path="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"human_read_source", "human_read_at"}:
                prohibited.append(f"{path}.{key}")
            scan_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            scan_keys(child, f"{path}[{i}]")


for name, doc in docs.items():
    scan_keys(doc, name)
check("prohibited_human_read_fields", not prohibited, prohibited, [])

placeholder_years = [row["source_key"] for row in sources if row["publication_year"] in {0, 1900, 9999}]
inferred_op_years = [row["resource_key"] for row in resources if row.get("release_year") is not None and not row.get("year_basis")]
mojibake = []
shortened_authors = []
for row in sources:
    serialized = json.dumps(row, ensure_ascii=False)
    if any(token in serialized for token in ("Ã", "Â", "�")):
        mojibake.append(row["source_key"])
    if any("et al" in author.casefold() for author in row["authors"]):
        shortened_authors.append(row["source_key"])
check("placeholder_and_operational_inferred_years", not placeholder_years and not inferred_op_years, {"placeholder": placeholder_years, "operational_inferred": inferred_op_years}, {"placeholder": [], "operational_inferred": []})
check("mojibake_and_shortened_canonical_authors", not mojibake and not shortened_authors, {"mojibake": mojibake, "shortened_authors": shortened_authors}, {"mojibake": [], "shortened_authors": []})

peer_missing = [row["source_key"] for row in sources if row["peer_reviewed"] is True and not row.get("peer_review_evidence_basis")]
check("peer_reviewed_true_has_direct_evidence_basis", not peer_missing, peer_missing, [])

# 8. Trust chain: registry and Material Passport corpus entries.
trust_failures = []
for row in sources:
    if row.get("source_verified_against_original"):
        if not row.get("source_acquired") or row.get("source_verification_method") not in {"codex_audit", "manual_grep", "vision_check"}:
            trust_failures.append({"source_key": row["source_key"], "error": "verified_without_acquired_and_real_method"})
    if not row.get("source_acquired") and row.get("source_verified_against_original"):
        trust_failures.append({"source_key": row["source_key"], "error": "not_acquired_but_verified"})
for row in corpus:
    if row.get("source_verified_against_original"):
        if not row.get("source_acquired") or row.get("source_verification_method") not in {"codex_audit", "manual_grep", "vision_check"}:
            trust_failures.append({"citation_key": row["citation_key"], "error": "corpus_verified_without_acquired_and_real_method"})
    if not row.get("source_acquired") and row.get("description_last_audit") != "none":
        trust_failures.append({"citation_key": row["citation_key"], "error": "not_acquired_without_literal_none_audit_sentinel", "value": row.get("description_last_audit")})
check("source_verified_against_original_trust_chain", not trust_failures, trust_failures, [])

# 9. Claim-state consistency and L4 ambiguity resolution.
allowed_states = {"planning_only", "conditional_production_candidate", "production_ready"}
central_counts = Counter(row["central_disposition"] for row in claims)
planning_counts = Counter(
    "true" if row["original_lane_state"]["planning_only"] is True else
    "false" if row["original_lane_state"]["planning_only"] is False else "absent"
    for row in claims
)
intent_counts = Counter(
    "true" if row["original_lane_state"]["production_intended"] is True else
    "false" if row["original_lane_state"]["production_intended"] is False else "absent"
    for row in claims
)
l4 = [row for row in claims if row["lane"] == "L4"]
claim_state_valid = (
    len(claims) == len({row["claim_id"] for row in claims}) == 44 and
    set(central_counts) <= allowed_states and sum(central_counts.values()) == 44 and
    planning_counts == Counter({"true": 30, "false": 14}) and
    intent_counts == Counter({"absent": 36, "true": 8}) and
    central_counts == Counter({"conditional_production_candidate": 22, "planning_only": 22}) and
    len(l4) == 8 and all(
        row["original_lane_state"]["planning_only"] is True and
        row["original_lane_state"]["production_intended"] is True and
        row["central_disposition"] == "conditional_production_candidate"
        for row in l4
    )
)
check(
    "claim_counts_and_exclusive_central_dispositions",
    claim_state_valid,
    {"claims": len(claims), "planning": dict(planning_counts), "intent": dict(intent_counts), "central": dict(central_counts), "l4": len(l4)},
    {"claims": 44, "planning": {"true": 30, "false": 14}, "intent": {"true": 8, "false": 0, "absent": 36}, "central": {"conditional_production_candidate": 22, "planning_only": 22, "production_ready": 0}, "l4": 8},
)

# 10. Recompute all reported counts, including the actual core decomposition.
raw_before = 0
for lane in ("L1", "L2", "L3", "L4", "L5"):
    reg = load(LANES / lane / "candidate_registry.json")
    raw_before += len(reg.get("scholarly_works", reg.get("records", [])))
actual_scholarly_core = sum(bool(row["core_shortlist"]) for row in sources)
actual_operational_core_families = {row["source_family_id"] for row in resources if row.get("core_operational_family")}
actual_core_total = actual_scholarly_core + len(actual_operational_core_families)
actual_counts = {
    "scholarly_rows_before_deduplication": raw_before,
    "canonical_scholarly_records_after_deduplication": len(sources),
    "scholarly_independent_families": len({row["source_family_id"] for row in sources}),
    "operational_records": len(resources),
    "operational_root_families": len({row["source_family_id"] for row in resources}),
    "unique_families_across_registries": len(family_set),
    "scholarly_corpus": len(corpus_set),
    "recent_2022_2026": sum(2022 <= row["publication_year"] <= 2026 and row["corpus_included"] for row in sources),
    "peer_reviewed_true": sum(row["peer_reviewed"] is True and row["corpus_included"] for row in sources),
    "source_acquired": sum(row["source_acquired"] and row["corpus_included"] for row in sources),
    "source_content_verified": sum(row["source_content_verified"] and row["corpus_included"] for row in sources),
    "locator_ready": sum(row["locator_ready"] and row["corpus_included"] for row in sources),
    "core_scholarly": actual_scholarly_core,
    "core_operational_families": len(actual_operational_core_families),
    "core_total": actual_core_total,
    "claim_cards": len(claims),
    "original_planning_only_true": planning_counts["true"],
    "original_planning_only_false": planning_counts["false"],
    "original_production_intended_true": intent_counts["true"],
    "original_production_intended_false": intent_counts["false"],
    "original_production_intended_absent": intent_counts["absent"],
    "central_conditional_production_candidates": central_counts["conditional_production_candidate"],
    "central_planning_only": central_counts["planning_only"],
    "central_production_ready": central_counts["production_ready"],
    "unresolved_r4_queue": len(handoff["unresolved_r4_queue"]),
}
reported_counts = handoff["counts"]
count_mismatches = {key: {"actual": value, "reported": reported_counts.get(key)} for key, value in actual_counts.items() if reported_counts.get(key) != value}
check("handoff_counts_recompute_exactly", not count_mismatches, count_mismatches, {})
check(
    "actual_core_count_rule_and_target",
    actual_scholarly_core == 23 and len(actual_operational_core_families) == 1 and actual_core_total == 24 and 18 <= actual_core_total <= 24,
    {"scholarly": actual_scholarly_core, "operational_families": len(actual_operational_core_families), "total": actual_core_total},
    {"scholarly": 23, "operational_families": 1, "total": 24},
)

# 11. Phase fence and generator-side validation receipt.
expected_phase = {
    "phase3_synthesis": "not_performed",
    "stage2_production_citations": "not_authorized",
    "hypotheses_h1_h4": "NOT_RUN",
    "r4_bulk_acquisition": "not_performed",
}
check("phase_boundary_intact", handoff.get("phase_boundary") == expected_phase, handoff.get("phase_boundary"), expected_phase)
generator_validation_failures = {
    key: value for key, value in handoff.get("validation", {}).items()
    if (isinstance(value, bool) and not value) or (isinstance(value, int) and not isinstance(value, bool) and value != 0)
}
check("generator_validation_all_pass", not generator_validation_failures, generator_validation_failures, {})

receipt = {
    "schema_version": "r3-independent-audit-receipt-1.0",
    "audited_at": AUDIT_TIMESTAMP,
    "auditor_scope": "Independent post-generation schema, trust-chain, reference-graph, count, hash, claim-state, and phase-boundary audit.",
    "ars_codex_version": "0.1.26",
    "result": "PASS" if not failures else "FAIL",
    "checks_run": len(checks),
    "checks_passed": sum(row["status"] == "PASS" for row in checks),
    "checks_failed": sum(row["status"] == "FAIL" for row in checks),
    "artifact_hashes_checked": len(acquired_scholarly) + len(acquired_operational),
    "counts_recomputed": actual_counts,
    "checks": checks,
    "failures": failures,
}
receipt_payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
receipt["receipt_payload_sha256"] = hashlib.sha256(receipt_payload).hexdigest()

handoff["independent_audit"] = receipt
handoff["completed_at"] = AUDIT_TIMESTAMP
if failures:
    handoff["verdict"] = "FAIL"
    handoff["verdict_scope"] = "Independent audit failed; no downstream authorization. Exact failures are embedded in independent_audit.failures."
else:
    handoff["verdict"] = "PASS"
    handoff["verdict_scope"] = "PASS authorizes only R4 source acquisition; it neither seals Stage 1B nor authorizes Stage 2 production citations."
dump(HERE / "r3_handoff.json", handoff)

print(json.dumps({
    "result": receipt["result"],
    "checks_run": receipt["checks_run"],
    "checks_failed": receipt["checks_failed"],
    "artifact_hashes_checked": receipt["artifact_hashes_checked"],
    "receipt_payload_sha256": receipt["receipt_payload_sha256"],
    "r3_handoff_sha256": sha256(HERE / "r3_handoff.json"),
    "failures": failures,
}, ensure_ascii=False, indent=2))

raise SystemExit(0 if not failures else 1)
