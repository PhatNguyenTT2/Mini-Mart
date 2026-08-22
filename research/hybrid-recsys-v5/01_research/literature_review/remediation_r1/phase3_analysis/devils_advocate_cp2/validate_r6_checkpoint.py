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
BASE = HERE.parent.parent
ROOT = BASE.parents[4]
EXPECTED_R6_MANIFEST_SHA256 = "52caf72b133c1368b68afac8fbaf50a544ef9f92001b818b01a71b76e861546a"


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
    duplicates: list[str] = []

    def check(name: str, condition: bool, detail: Any) -> None:
        checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            failures.append(name)

    control = BASE / "00_control"
    phase3 = BASE / "phase3_analysis"
    manifest_path = control / "r6_input_manifest.json"
    manifest = load_json(manifest_path, duplicates)
    check(
        "r6_manifest_exact_hash",
        sha256(manifest_path) == EXPECTED_R6_MANIFEST_SHA256,
        {"actual": sha256(manifest_path), "expected": EXPECTED_R6_MANIFEST_SHA256},
    )

    frozen_failures: list[str] = []
    frozen_rows = [manifest["r6_contract"], *manifest["frozen_r5_files"]]
    for row in frozen_rows:
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            frozen_failures.append(row["path"])
    check("frozen_r6_inputs_match", not frozen_failures, {"checked": len(frozen_rows), "failures": frozen_failures})

    r5_validator_path = phase3 / "validate_r5_synthesis.py"
    spec = importlib.util.spec_from_file_location("r5_validator", r5_validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen R5 validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    r5_receipt = module.validate(final=True)
    check(
        "r5_final_validator_29_of_29",
        r5_receipt["result"] == "PASS"
        and r5_receipt["checks_run"] == 29
        and r5_receipt["checks_passed"] == 29
        and r5_receipt["checks_failed"] == 0
        and r5_receipt["receipt_payload_sha256"] == manifest["r5_gate"]["final_receipt_payload_sha256"],
        {
            "result": r5_receipt["result"],
            "passed": r5_receipt["checks_passed"],
            "run": r5_receipt["checks_run"],
            "payload_sha256": r5_receipt["receipt_payload_sha256"],
        },
    )

    findings = load_json(HERE / "r6_findings.json", duplicates)
    packet = load_json(HERE / "tension_adjudication_packet.json", duplicates)
    claim_map = load_json(phase3 / "claim_source_map_r1.json", duplicates)
    tensions = load_json(phase3 / "cross_paper_tensions_r1.json", duplicates)
    report = (HERE / "devils_advocate_checkpoint2_r1.md").read_text(encoding="utf-8")
    synthesis = (phase3 / "synthesis_report_r1.md").read_text(encoding="utf-8")

    check("duplicate_json_keys_zero", not duplicates, duplicates)
    check(
        "runtime_lock_preserved",
        findings["runtime_lock"] == manifest["runtime_lock"],
        findings["runtime_lock"],
    )

    actual_severity = Counter(row["severity"] for row in findings["findings"])
    expected_severity = findings["severity_counts"]
    check(
        "severity_counts_recompute",
        all(actual_severity.get(key, 0) == expected_severity[key] for key in ["Critical", "Major", "Minor", "Observation"]),
        {"recomputed": dict(actual_severity), "reported": expected_severity},
    )
    check(
        "verdict_arithmetic",
        findings["verdict"] == "REVISE"
        and expected_severity["Critical"] == 0
        and expected_severity["Major"] == 1,
        {"verdict": findings["verdict"], "severity": expected_severity},
    )

    expected_claim_ids = {row["claim_id"] for row in claim_map["claims"]}
    audited_claim_ids = findings["claim_bias_audit"]["audited_claim_ids"]
    check(
        "all_44_claims_audited",
        len(audited_claim_ids) == len(set(audited_claim_ids)) == 44
        and set(audited_claim_ids) == expected_claim_ids
        and findings["claim_bias_audit"]["audited_claims"] == 44,
        {"audited": len(audited_claim_ids), "unique": len(set(audited_claim_ids)), "expected": len(expected_claim_ids)},
    )
    dispositions = Counter(row["r5_disposition"] for row in claim_map["claims"])
    verdicts = Counter(row["support_verdict"] for row in claim_map["claims"])
    check(
        "claim_population_counts",
        dispositions == Counter({"citation_ready_candidate": 22, "planning_only": 22})
        and verdicts == Counter({"supported": 38, "partially_supported": 6})
        and findings["claim_bias_audit"]["counter_evidence"]["upstream_nonempty"] == 44,
        {"dispositions": dict(dispositions), "support_verdicts": dict(verdicts)},
    )

    robustness = findings["theme_robustness"]
    check(
        "five_theme_steelman_attack_robustness",
        len(robustness) == 5
        and [row["theme_id"] for row in robustness] == ["T1", "T2", "T3", "T4", "T5"]
        and all(row["strongest_removed_family"] and row["result"] for row in robustness),
        {"themes": len(robustness), "results": [row["result"] for row in robustness]},
    )

    visible_counts: dict[str, int] = {}
    for number in range(1, 6):
        start = synthesis.index(f"## Theme {number}")
        end = synthesis.index(f"## Theme {number + 1}") if number < 5 else synthesis.index("## Convergence and divergence")
        refs = set(re.findall(r"<!--ref:([^>]+)-->", synthesis[start:end]))
        visible_counts[f"T{number}"] = len(refs)
    recount = findings["family_recount"]["visible_themes"]
    check(
        "visible_theme_recount",
        visible_counts == {"T1": 6, "T2": 8, "T3": 8, "T4": 9, "T5": 2}
        and recount["T1"]["records"] == 6
        and recount["T2"]["records"] == 8
        and recount["T3"]["records"] == 8
        and recount["T4"]["records"] == 9
        and recount["T5"]["operational_records"] == 2,
        visible_counts,
    )
    check(
        "family_double_count_finding_present",
        findings["family_recount"]["prose_double_counting_or_miscount_detected"] is True
        and findings["family_recount"]["included_cross_family_dependency_edges"] == 3
        and recount["T4"]["dependency_adjusted_families_max"] <= 8,
        findings["family_recount"],
    )

    original_pairs = {row["pair_id"]: row for row in tensions["cross_paper_tensions"]}
    packet_pairs = {row["pair_id"]: row for row in packet["pairs"]}
    pair_failures: list[str] = []
    for pair_id, original in original_pairs.items():
        row = packet_pairs.get(pair_id)
        if row is None:
            pair_failures.append(f"{pair_id}:missing")
            continue
        expected_pointer = original.get("resolution_pointer")
        if row["paper_a"] != original["paper_a"] or row["paper_b"] != original["paper_b"]:
            pair_failures.append(f"{pair_id}:papers")
        if row["r5_pair_assessment"] != original["pair_assessment"] or row["r5_resolution_status"] != original["resolution_status"]:
            pair_failures.append(f"{pair_id}:state")
        if row["r5_resolution_pointer"] != expected_pointer:
            pair_failures.append(f"{pair_id}:pointer")
        if row["scholar_confirmation"] != "pending":
            pair_failures.append(f"{pair_id}:confirmation")
        if row["r6_recommendation"] not in {"confirm", "dispute"}:
            pair_failures.append(f"{pair_id}:recommendation")
    check(
        "twelve_pair_packet_preserves_legal_state",
        len(original_pairs) == len(packet_pairs) == 12 and not pair_failures,
        {"pairs": len(packet_pairs), "failures": pair_failures},
    )
    recommendations = Counter(row["r6_recommendation"] for row in packet["pairs"])
    check(
        "scholar_checkpoint_pending",
        recommendations == Counter({"confirm": 11, "dispute": 1})
        and packet["counts"]["scholar_confirmation_pending"] == 12
        and packet["counts"]["self_confirmed"] == packet["counts"]["self_disputed"] == 0,
        {"recommendations": dict(recommendations), "pending": packet["counts"]["scholar_confirmation_pending"]},
    )
    check(
        "no_pairwise_completeness_claim",
        "does not claim complete pairwise" in packet["coverage_boundary"]
        and "does not claim pairwise completeness" in report,
        packet["coverage_boundary"],
    )

    boundaries = findings["boundary_attacks"]
    check(
        "fixed_boundaries_preserved",
        boundaries["cold_item_not_cold_user"] == "PRESERVED"
        and boundaries["wide_deep_not_apriori_efficacy"] == "PRESERVED"
        and boundaries["transfer_not_h4"] == "PRESERVED"
        and boundaries["literature_not_empirical_results"] == "PRESERVED"
        and boundaries["official_reproduction_not_harmonized_benchmark"] == "PRESERVED",
        boundaries,
    )
    check(
        "complete_journey_and_liu_stress_tests",
        boundaries["complete_journey_rights_access_separation"] == "PRESERVED_PLANNING_ONLY"
        and boundaries["liu_2007_substitution"] == "PRESERVED_BOUNDED_METHOD_PRECEDENT_ONLY",
        boundaries,
    )
    check(
        "hostile_argument_and_minimum_concession_present",
        bool(findings["strongest_hostile_reviewer_counterargument"].strip())
        and bool(findings["minimum_defensible_concession"].strip()),
        {"hostile": True, "concession": True},
    )
    check(
        "no_manufactured_rebuttal",
        findings["concession_threshold_log"] == []
        and "No user or agent rebuttal" in findings["concession_protocol_note"],
        findings["concession_protocol_note"],
    )

    phase = findings["phase_boundary"]
    check(
        "r7_unauthorized_and_user_adjudication_required",
        phase["r7_authorized"] is False
        and packet["adjudication_requirement"]["r7_authorized"] is False
        and packet["adjudication_requirement"]["user_must_adjudicate_all_pairs"] is True,
        {"r7_authorized": phase["r7_authorized"], "user_adjudication": True},
    )
    check(
        "phase_boundaries_preserved",
        phase["r7_r9"] == "NOT_PERFORMED"
        and phase["manuscript_drafting"] == "NOT_PERFORMED"
        and phase["benchmark_training_evaluation"] == "NOT_RUN"
        and phase["h1_h4"] == "NOT_RUN"
        and phase["stage1b_sealed"] is False
        and phase["stage2_production_citations"] == "NOT_AUTHORIZED",
        phase,
    )
    check(
        "report_declares_exact_verdict_and_counts",
        "## Verdict: REVISE" in report
        and "Critical 0 · Major 1 · Minor 2 · Observation 5" in report
        and "All `scholar_confirmation` values remain `pending`" in report,
        {"verdict": "REVISE", "severity": expected_severity},
    )
    check(
        "report_contains_required_attacks",
        report.count("- **Steel-man:**") == 5
        and report.count("- **Attack:**") == 5
        and report.count("- **Removal test:**") == 5
        and "## Strongest hostile-reviewer counterargument" in report
        and "## Minimum defensible concession" in report,
        {
            "steelman": report.count("- **Steel-man:**"),
            "attack": report.count("- **Attack:**"),
            "removal": report.count("- **Removal test:**"),
        },
    )

    if final:
        receipt = load_json(HERE / "r6_validation_receipt.json", duplicates)
        handoff = load_json(HERE / "r6_handoff.json", duplicates)
        manifest_failures: list[str] = []
        for row in handoff["output_manifest"]:
            path = ROOT / row["path"]
            if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
                manifest_failures.append(row["path"])
        check(
            "r6_handoff_nonself_hashes",
            len(handoff["output_manifest"]) == 5 and not manifest_failures,
            {"checked": len(handoff["output_manifest"]), "failures": manifest_failures},
        )
        check(
            "r6_saved_receipt_scope",
            receipt["result"] == "PASS"
            and receipt["validation_mode"] == "pre_handoff"
            and receipt["checks_failed"] == 0,
            {"result": receipt["result"], "checks": f"{receipt['checks_passed']}/{receipt['checks_run']}"},
        )
        check(
            "r6_handoff_verdict_and_scope",
            handoff["verdict"] == "REVISE"
            and handoff["r7_authorized"] is False
            and handoff["user_adjudication_required"] is True
            and handoff["severity_counts"] == expected_severity,
            {"verdict": handoff["verdict"], "r7_authorized": handoff["r7_authorized"]},
        )

    result: dict[str, Any] = {
        "schema_version": "stage1b-r1-r6-validation-receipt-1.0",
        "validation_mode": "final" if final else "pre_handoff",
        "result": "PASS" if not failures else "FAIL",
        "checks_run": len(checks),
        "checks_passed": sum(row["status"] == "PASS" for row in checks),
        "checks_failed": sum(row["status"] == "FAIL" for row in checks),
        "checks": checks,
        "failures": failures,
        "recomputed": {
            "frozen_hash_mismatches": len(frozen_failures),
            "r5_final_validation": f"{r5_receipt['checks_passed']}/{r5_receipt['checks_run']} PASS",
            "claims_audited": len(audited_claim_ids),
            "citation_ready_candidate": dispositions["citation_ready_candidate"],
            "planning_only": dispositions["planning_only"],
            "tension_pairs": len(packet_pairs),
            "scholar_confirmation_pending": packet["counts"]["scholar_confirmation_pending"],
            "theme_robustness_results": len(robustness),
            "severity_counts": expected_severity,
            "visible_theme_records": visible_counts,
            "r7_authorized": phase["r7_authorized"],
        },
    }
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    result["receipt_payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    result = validate(final=args.final)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
