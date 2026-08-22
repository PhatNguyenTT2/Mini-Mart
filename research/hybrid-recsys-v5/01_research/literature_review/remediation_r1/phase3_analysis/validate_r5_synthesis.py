from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[4]
EXPECTED_R5_MANIFEST_SHA256 = "9ed388e94ec44e1574ac370918cd4d6be2f321235fa63586845a0da76bbe6ba8"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, duplicate_failures: list[str]) -> Any:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                duplicate_failures.append(f"{path.as_posix()}::{key}")
            out[key] = value
        return out

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates)


def validate(final: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    duplicate_keys: list[str] = []

    def check(name: str, condition: bool, detail: Any) -> None:
        checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            failures.append(name)

    control = BASE / "00_control"
    integration = BASE / "phase2_investigation" / "integration"
    acquisition = BASE / "phase2_investigation" / "acquisition"

    r5_manifest_path = control / "r5_input_manifest.json"
    r5_manifest = load_json(r5_manifest_path, duplicate_keys)
    check(
        "r5_manifest_exact_hash",
        sha256(r5_manifest_path) == EXPECTED_R5_MANIFEST_SHA256,
        {"actual": sha256(r5_manifest_path), "expected": EXPECTED_R5_MANIFEST_SHA256},
    )

    contract = ROOT / r5_manifest["r5_contract"]["path"]
    check(
        "r5_contract_bytes_and_hash",
        contract.stat().st_size == r5_manifest["r5_contract"]["bytes"]
        and sha256(contract) == r5_manifest["r5_contract"]["sha256"],
        {"bytes": contract.stat().st_size, "sha256": sha256(contract)},
    )

    direct_r4_failures: list[str] = []
    for row in r5_manifest["frozen_r4_files"]:
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            direct_r4_failures.append(row["path"])
    check("frozen_r4_direct_hashes", not direct_r4_failures, {"checked": 7, "failures": direct_r4_failures})

    r4_input_row = r5_manifest["r3_gate"]["transitive_manifest"]
    r4_input_path = ROOT / r4_input_row["path"]
    r4_input = load_json(r4_input_path, duplicate_keys)
    check(
        "r4_input_manifest_bytes_and_hash",
        r4_input_path.stat().st_size == r4_input_row["bytes"] and sha256(r4_input_path) == r4_input_row["sha256"],
        {"bytes": r4_input_path.stat().st_size, "sha256": sha256(r4_input_path)},
    )

    frozen_r3_failures: list[str] = []
    for row in r4_input["integration_files"]:
        path = integration / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            frozen_r3_failures.append(row["path"])
    check("frozen_r3_direct_hashes", not frozen_r3_failures, {"checked": 12, "failures": frozen_r3_failures})

    r3_handoff = load_json(integration / "r3_handoff.json", duplicate_keys)
    audit = r3_handoff["independent_audit"]
    check(
        "r3_pass_and_independent_audit",
        r3_handoff["verdict"] == "PASS"
        and audit["result"] == "PASS"
        and audit["checks_run"] == 20
        and audit["checks_passed"] == 20
        and audit["checks_failed"] == 0,
        {"verdict": r3_handoff["verdict"], "audit": f"{audit['checks_passed']}/{audit['checks_run']}"},
    )

    r4_handoff = load_json(acquisition / "r4_handoff.json", duplicate_keys)
    source_artifact_failures: list[str] = []
    for row in r4_handoff["source_artifact_manifest"]:
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            source_artifact_failures.append(row["path"])
    check(
        "r4_source_artifacts_revalidated",
        len(r4_handoff["source_artifact_manifest"]) == 35 and not source_artifact_failures,
        {"checked": len(r4_handoff["source_artifact_manifest"]), "failures": source_artifact_failures},
    )

    preflight_failures: list[str] = []
    for row in r4_handoff["pdf_preflight_manifest"]:
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            preflight_failures.append(row["path"])
    check(
        "r4_pdf_sidecars_revalidated",
        len(r4_handoff["pdf_preflight_manifest"]) == 28 and not preflight_failures,
        {"checked": len(r4_handoff["pdf_preflight_manifest"]), "failures": preflight_failures},
    )

    spec = importlib.util.spec_from_file_location("r4_validator", acquisition / "validate_r4_acquisition.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen R4 validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    r4_receipt = module.validate_bundle(acquisition, require_handoff=True)
    check(
        "r4_validator_22_of_22",
        r4_receipt["result"] == "PASS"
        and r4_receipt["checks_run"] == 22
        and r4_receipt["checks_passed"] == 22
        and r4_receipt["checks_failed"] == 0,
        {"result": r4_receipt["result"], "passed": r4_receipt["checks_passed"], "run": r4_receipt["checks_run"]},
    )
    check(
        "r4_authorization_and_counts",
        r4_handoff["verdict"] == "PASS"
        and r4_handoff["r5_authorized"] is True
        and r4_handoff["stage2_production_citations_authorized"] is False
        and r4_handoff["counts"]["core"]["total"] == 24
        and r4_handoff["counts"]["core"]["acquired"] == 24
        and r4_handoff["counts"]["core"]["content_verified"] == 24
        and r4_handoff["counts"]["core"]["locator_ready"] == 24
        and r4_handoff["counts"]["queue"]["terminal_resolved"] == 13
        and r4_handoff["counts"]["claims"]["conditional_original_content_and_locator_satisfied"] == 22
        and r4_handoff["counts"]["production_ready"] == 0,
        r4_handoff["counts"],
    )

    source_registry = load_json(integration / "source_registry_r1.json", duplicate_keys)
    family_map = load_json(integration / "source_family_map_r1.json", duplicate_keys)
    resource_registry = load_json(integration / "operational_resource_registry.json", duplicate_keys)
    locator_registry = load_json(acquisition / "locator_registry.json", duplicate_keys)
    r4_claim_map = load_json(acquisition / "r4_claim_acquisition_map.json", duplicate_keys)
    intent = load_json(HERE / "claim_intent_manifest_r1.json", duplicate_keys)
    claim_map = load_json(HERE / "claim_source_map_r1.json", duplicate_keys)
    tensions = load_json(HERE / "cross_paper_tensions_r1.json", duplicate_keys)
    ledger = load_json(control / "synthesis_invocation_ledger.json", duplicate_keys)
    report = (HERE / "synthesis_report_r1.md").read_text(encoding="utf-8")

    source_keys = {row["source_key"] for row in source_registry["sources"]}
    family_ids = {row["source_family_id"] for row in family_map["families"]}
    resource_keys = {row["resource_key"] for row in resource_registry["resources"]}
    locator_by_id = {row["locator_id"]: row for row in locator_registry["locators"]}
    r4_claim_by_id = {row["claim_id"]: row for row in r4_claim_map["claims"]}

    check("duplicate_json_keys_zero", not duplicate_keys, duplicate_keys)
    intent_claim_ids = [row["source_claim_id"] for row in intent["claims"]]
    check(
        "one_shot_intent_covers_all_claims",
        intent["one_shot"] is True
        and len(intent["claims"]) == 44
        and len(set(intent_claim_ids)) == 44
        and set(intent_claim_ids) == set(r4_claim_by_id),
        {"claims": len(intent["claims"]), "unique": len(set(intent_claim_ids))},
    )

    claims = claim_map["claims"]
    disposition_counts = Counter(row["r5_disposition"] for row in claims)
    check(
        "claim_population_and_exclusive_dispositions",
        len(claims) == 44
        and disposition_counts == Counter({"citation_ready_candidate": 22, "planning_only": 22})
        and all(row["exclusive_disposition"] is True for row in claims),
        {"total": len(claims), "dispositions": dict(disposition_counts)},
    )

    dangling: list[str] = []
    for row in claims:
        for value in row["canonical_source_keys"]:
            if value not in source_keys:
                dangling.append(f"source:{row['claim_id']}:{value}")
        for value in row["operational_resource_keys"]:
            if value not in resource_keys:
                dangling.append(f"resource:{row['claim_id']}:{value}")
        for value in row["source_family_ids"]:
            if value not in family_ids:
                dangling.append(f"family:{row['claim_id']}:{value}")
        for value in row["locator_ids"]:
            if value not in locator_by_id:
                dangling.append(f"locator:{row['claim_id']}:{value}")
    check("claim_reference_graph_resolves", not dangling, dangling)

    planning_preserved = all(
        row["r5_disposition"] == ("planning_only" if r4_claim_by_id[row["claim_id"]]["central_disposition"] == "planning_only" else "citation_ready_candidate")
        for row in claims
    )
    check("planning_only_rows_preserved", planning_preserved, {"planning_only": disposition_counts["planning_only"]})

    ready_failures: list[str] = []
    for row in claims:
        if row["r5_disposition"] != "citation_ready_candidate":
            continue
        required = [
            "r4_acquisition_satisfied",
            "r4_original_content_satisfied",
            "r4_locator_satisfied",
            "frozen_r4_prerequisites_satisfied",
            "all_selected_locators_verified_non_none",
            "wording_bounded",
            "family_dependence_recorded",
            "liu_replacement_scope_honored",
        ]
        if not all(row["readiness_checks"].get(key) is True for key in required):
            ready_failures.append(row["claim_id"])
    check("conditional_candidates_all_ready", not ready_failures, {"checked": 22, "failures": ready_failures})

    legal = {
        "contradiction": {"resolved_in_synthesis", "flagged_unresolved"},
        "conditional_difference": {"resolved_in_synthesis", "flagged_unresolved"},
        "no_material_conflict": {"not_applicable"},
        "insufficient_overlap": {"not_applicable"},
    }
    tension_failures: list[str] = []
    for row in tensions["cross_paper_tensions"]:
        if row["paper_a"] not in source_keys or row["paper_b"] not in source_keys:
            tension_failures.append(f"{row['pair_id']}:paper")
        if row["a_evidence_pointer"] not in locator_by_id or row["b_evidence_pointer"] not in locator_by_id:
            tension_failures.append(f"{row['pair_id']}:pointer")
        if row["resolution_status"] not in legal.get(row["pair_assessment"], set()):
            tension_failures.append(f"{row['pair_id']}:state")
        if (row["resolution_status"] == "resolved_in_synthesis") != ("resolution_pointer" in row):
            tension_failures.append(f"{row['pair_id']}:resolution_pointer")
        if row["scholar_confirmation"] != "pending":
            tension_failures.append(f"{row['pair_id']}:confirmation")
    check(
        "tension_inventory_legal_and_pending",
        len(tensions["cross_paper_tensions"]) == 12 and not tension_failures and isinstance(tensions.get("coverage_note"), str),
        {"pairs": len(tensions["cross_paper_tensions"]), "failures": tension_failures},
    )

    ref_markers = re.findall(r"<!--ref:([^>]+)-->", report)
    anchor_markers = re.findall(r"<!--anchor:([^:>]+):(.*?)-->", report)
    paired_markers = re.findall(r"<!--ref:([^>]+)--><!--anchor:([^:>]+):(.*?)-->", report)
    check(
        "citation_markers_are_paired",
        len(ref_markers) == len(anchor_markers) == len(paired_markers),
        {"refs": len(ref_markers), "anchors": len(anchor_markers), "paired": len(paired_markers)},
    )

    allowed: set[tuple[str, str, str]] = set()
    for row in locator_registry["locators"]:
        ref = row["source_key"] or row["resource_key"]
        if row["verified_against_original"] and row["locator_type"] != "none":
            allowed.add((ref, row["locator_type"], row["locator_value"]))
    invalid_markers = [triple for triple in paired_markers if triple not in allowed]
    check("visible_citations_resolve_to_verified_locators", not invalid_markers, invalid_markers)
    check(
        "non_none_no_prohibited_page_anchors",
        all(kind != "none" and kind != "page" for _, kind, _ in paired_markers),
        {"none": sum(kind == "none" for _, kind, _ in paired_markers), "page": sum(kind == "page" for _, kind, _ in paired_markers)},
    )
    quote_over_cap = [value for _, kind, value in paired_markers if kind == "quote" and len(value.split()) > 25]
    check("quote_cap_25_words", not quote_over_cap, quote_over_cap)

    citation_ref_keys = {ref for ref, _, _ in paired_markers}
    ghost_refs = sorted(citation_ref_keys - source_keys - resource_keys)
    check("ghost_citations_zero", not ghost_refs, ghost_refs)

    headings = {line.strip().lower() for line in report.splitlines() if line.startswith("#")}
    prohibited_headings = {"# introduction", "## introduction", "# related work", "## related work"}
    check("phase3_no_manuscript_headings", not (headings & prohibited_headings), sorted(headings & prohibited_headings))

    positive_forbidden: list[str] = []
    for line in report.splitlines():
        lower = line.lower()
        if any(token in lower for token in ["does not", "do not", "cannot", "not justify", "remain `not_run`", "not automatically"]):
            continue
        if re.search(r"wide\s*&\s*deep\s+(proves|establishes)\s+apriori", lower):
            positive_forbidden.append(line)
        if re.search(r"architecture transfer\s+(proves|establishes)\s+h4", lower):
            positive_forbidden.append(line)
        if re.search(r"h[1-4]\s+(is|was)\s+(confirmed|supported|validated)", lower):
            positive_forbidden.append(line)
    check("forbidden_positive_extrapolations_zero", not positive_forbidden, positive_forbidden)

    unqualified_counts: list[str] = []
    for line in report.splitlines():
        lower = line.lower()
        if "converge" in lower or "convergence" in lower or "theme" in lower and "records" in lower:
            if re.search(r"\b\d+\s+(sources|records|papers)\b", lower) and not ("canonical" in lower and "independent" in lower):
                unqualified_counts.append(line)
    check("unqualified_independent_evidence_counts_zero", not unqualified_counts, unqualified_counts)

    ledger_events = ledger["events"]
    expected_sequences = [1, 2, 3] if final else [1, 2]
    event_names = [row["event"] for row in ledger_events]
    event_sequences = [row["sequence"] for row in ledger_events]
    intent_hash = sha256(HERE / "claim_intent_manifest_r1.json")
    ledger_ok = (
        event_sequences == expected_sequences
        and event_names[:2] == ["claim_intent_manifest_bound", "synthesis_started"]
        and ledger_events[0]["artifact_sha256"] == intent_hash
        and ledger_events[1]["intent_manifest_sha256"] == intent_hash
        and ledger_events[0]["recorded_at"] <= ledger_events[1]["recorded_at"]
    )
    if final:
        ledger_ok = ledger_ok and event_names == ["claim_intent_manifest_bound", "synthesis_started", "synthesis_finalized"]
        handoff_path = HERE / "r5_handoff.json"
        ledger_ok = ledger_ok and handoff_path.is_file() and ledger_events[2]["r5_handoff_sha256"] == sha256(handoff_path)
        ledger_ok = ledger_ok and ledger_events[2]["synthesis_report_sha256"] == sha256(HERE / "synthesis_report_r1.md")
    check("intent_ledger_one_shot_ordering", ledger_ok, {"events": event_names, "sequences": event_sequences})

    if final:
        handoff = load_json(HERE / "r5_handoff.json", duplicate_keys)
        manifest_failures: list[str] = []
        for row in handoff["output_manifest"]:
            path = ROOT / row["path"]
            if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
                manifest_failures.append(row["path"])
        check("r5_handoff_nonself_hashes", not manifest_failures, {"checked": len(handoff["output_manifest"]), "failures": manifest_failures})
        check(
            "r5_handoff_verdict_and_scope",
            handoff["verdict"] == "PASS"
            and handoff["r6_authorized"] is True
            and handoff["stage1b_sealed"] is False
            and handoff["stage2_production_citations_authorized"] is False,
            {"verdict": handoff["verdict"], "r6_authorized": handoff["r6_authorized"]},
        )

    check(
        "phase_boundaries_preserved",
        "H1–H4 remain `NOT_RUN`" in report
        and "Stage 2 production citations remain `NOT_AUTHORIZED`" in report
        and claim_map["phase_boundary"]["benchmark"] == "NOT_RUN"
        and claim_map["phase_boundary"]["r6"] == "NOT_PERFORMED",
        claim_map["phase_boundary"],
    )

    receipt: dict[str, Any] = {
        "schema_version": "stage1b-r1-r5-validation-receipt-1.0",
        "validation_mode": "final" if final else "pre_handoff",
        "result": "PASS" if not failures else "FAIL",
        "checks_run": len(checks),
        "checks_passed": sum(row["status"] == "PASS" for row in checks),
        "checks_failed": sum(row["status"] == "FAIL" for row in checks),
        "checks": checks,
        "failures": failures,
        "recomputed": {
            "frozen_r3_files": 12,
            "r3_independent_audit": "20/20 PASS",
            "r4_validator": "22/22 PASS",
            "r4_source_artifacts": 35,
            "r4_pdf_sidecars": 28,
            "claims": dict(disposition_counts),
            "tensions": tensions["counts"],
            "visible_citations": len(paired_markers),
            "verified_non_none_locators": len(paired_markers),
            "duplicate_keys": len(duplicate_keys),
            "dangling_references": len(dangling),
            "ghost_citations": len(ghost_refs),
            "prohibited_page_anchors": sum(kind == "page" for _, kind, _ in paired_markers),
            "forbidden_positive_extrapolations": len(positive_forbidden),
            "unqualified_independent_evidence_counts": len(unqualified_counts),
        },
    }
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt["receipt_payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    receipt = validate(args.final)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
