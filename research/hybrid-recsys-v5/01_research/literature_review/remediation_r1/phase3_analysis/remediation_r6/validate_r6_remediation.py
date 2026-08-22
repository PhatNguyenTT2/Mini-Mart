#!/usr/bin/env python3
"""Semantic replay validator for the Stage 1B R6 remediation overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[7]
R1 = ROOT / "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1"
CONTROL = R1 / "00_control"
INTEGRATION = R1 / "phase2_investigation/integration"
ACQUISITION = R1 / "phase2_investigation/acquisition"
PHASE3 = R1 / "phase3_analysis"
R6 = PHASE3 / "devils_advocate_cp2"
OUT = PHASE3 / "remediation_r6"

EXPECTED_MANIFEST_SHA256 = "9c9a60463106a7ba21ad8f24600db9688a56c7efa5986b33db2b232a2505dabb"
EXPECTED_THEME_COUNTS = {
    "T1": (6, 6, 6),
    "T2": (8, 8, 8),
    "T3": (8, 8, 8),
    "T4": (9, 9, 8),
    "T5": (2, 1, 1),
}
EXPECTED_FILES = {
    "theme_evidence_denominators.json",
    "claim_counter_evidence_overlay.json",
    "claim_source_map_r1_remediated.json",
    "synthesis_report_r1_remediated.md",
    "r6_remediation_report.md",
    "r6_remediation_validation_receipt.json",
    "r6_remediation_handoff.json",
    "build_r6_remediation.py",
    "validate_r6_remediation.py",
}

CHECK_NAMES = [
    "remediation_manifest_exact_hash",
    "remediation_contract_bytes_and_hash",
    "frozen_r6_files_match_manifest",
    "r5_final_replay_29_of_29",
    "r6_final_replay_26_of_26",
    "runtime_lock_exact",
    "r6_verdict_finding_and_pending_state",
    "phase_boundary_fail_closed",
    "five_theme_exact_source_set_replay",
    "theme_source_family_resolution",
    "relevant_dependency_edges_exact",
    "theme_denominator_arithmetic_replay",
    "canonical_nominal_adjusted_separated",
    "theme5_operational_scholarly_separation",
    "prose_denominator_pointers_complete",
    "prose_denominator_values_match_arrays",
    "claim_population_44_unique",
    "counter_overlay_44_of_44",
    "upstream_counter_evidence_exact",
    "counter_evidence_source_locator_pointers_resolve",
    "duplicate_and_dangling_references_zero",
    "remediated_claim_rows_zero_drift",
    "one_shot_intent_join_zero_drift",
    "claim_dispositions_22_and_22",
    "citation_marker_identity_33_of_33",
    "citation_anchors_non_none_and_valid",
    "tension_packet_12_unchanged_pending",
    "r6_finding_statuses_exact",
    "r7_unauthorized_only_reaudit_authorized",
    "downstream_work_not_performed",
    "receipt_nonself_hashes_resolve",
    "handoff_nonself_hashes_resolve",
    "output_roster_complete",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def tokens(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    return value if isinstance(value, list) else value.split()


def marker_pairs(text: str) -> list[str]:
    pattern = r"<!--ref:[^>]+--><!--anchor:[^>]+-->"
    return re.findall(pattern, text)


def extract_theme_refs(text: str, theme_id: str) -> list[str]:
    n = int(theme_id[1:])
    start = re.search(rf"^## Theme {n}\b", text, re.MULTILINE)
    if not start:
        raise ValueError(f"missing Theme {n} heading")
    end = re.search(rf"^## Theme {n + 1}\b", text[start.end():], re.MULTILINE) if n < 5 else re.search(
        r"^## Convergence and divergence\b", text[start.end():], re.MULTILINE
    )
    stop = start.end() + end.start() if end else len(text)
    block = text[start.start():stop]
    ordered: list[str] = []
    for key in re.findall(r"<!--ref:([^>]+)-->", block):
        if key not in ordered:
            ordered.append(key)
    return ordered


def family_index(family_map: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    source_to_family: dict[str, str] = {}
    resource_to_family: dict[str, str] = {}
    for family in family_map["families"]:
        family_id = family["source_family_id"]
        for key in tokens(family.get("scholarly_source_keys")):
            source_to_family[key] = family_id
        for key in tokens(family.get("operational_resource_keys")):
            resource_to_family[key] = family_id
    return source_to_family, resource_to_family


def relevant_edges(theme: dict[str, Any], family_map: dict[str, Any]) -> list[dict[str, Any]]:
    keys = {record["record_key"] for record in theme["records"]}
    families = {record["family_id"] for record in theme["records"]}
    result = []
    for edge in family_map["dependencies"]:
        edge_keys = set(tokens(edge.get("source_keys"))) | set(tokens(edge.get("resource_keys")))
        if (
            edge["source_family_id"] in families
            and edge["depends_on_family_id"] in families
            and edge_keys.intersection(keys)
        ):
            result.append(edge)
    return result


def adjusted_family_count(theme: dict[str, Any]) -> int:
    families = {record["family_id"] for record in theme["records"]}
    parent = {family: family for family in families}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[a] = b

    for edge in theme["dependency_edges"]:
        if edge["counting_effect"] == "not_an_additional_independent_source_family":
            if edge["source_family_id"] != edge["depends_on_family_id"]:
                union(edge["source_family_id"], edge["depends_on_family_id"])
    return len({find(family) for family in families})


def run_validator(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(path), "--final"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + proc.stderr)
    return json.loads(proc.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true", help="validate final report, receipt, and handoff too")
    args = parser.parse_args()
    checks: list[dict[str, Any]] = []

    def check(name: str, function) -> None:
        try:
            detail = function()
            checks.append({"name": name, "status": "PASS", "detail": detail})
        except Exception as exc:  # fail closed and keep the full checklist visible
            checks.append({"name": name, "status": "FAIL", "detail": str(exc)})

    manifest_path = CONTROL / "r6_remediation_input_manifest.json"
    contract_path = CONTROL / "r6_remediation_contract.md"
    manifest = load_json(manifest_path)
    findings = load_json(R6 / "r6_findings.json")
    family_map = load_json(INTEGRATION / "source_family_map_r1.json")
    denominators = load_json(OUT / "theme_evidence_denominators.json")
    counter = load_json(OUT / "claim_counter_evidence_overlay.json")
    original_map = load_json(PHASE3 / "claim_source_map_r1.json")
    remediated_map = load_json(OUT / "claim_source_map_r1_remediated.json")
    intent = load_json(PHASE3 / "claim_intent_manifest_r1.json")
    locators = load_json(ACQUISITION / "locator_registry.json")
    tensions = load_json(PHASE3 / "cross_paper_tensions_r1.json")
    tension_packet = load_json(R6 / "tension_adjudication_packet.json")
    original_text = (PHASE3 / "synthesis_report_r1.md").read_text(encoding="utf-8")
    remediated_text = (OUT / "synthesis_report_r1_remediated.md").read_text(encoding="utf-8")
    receipt = load_json(OUT / "r6_remediation_validation_receipt.json") if args.final else {}
    handoff = load_json(OUT / "r6_remediation_handoff.json") if args.final else {}
    report_text = (OUT / "r6_remediation_report.md").read_text(encoding="utf-8") if args.final else ""
    source_to_family, resource_to_family = family_index(family_map)
    locator_index = {row["locator_id"]: row for row in locators["locators"]}

    check(CHECK_NAMES[0], lambda: (
        {"actual": sha256(manifest_path), "expected": EXPECTED_MANIFEST_SHA256}
        if sha256(manifest_path) == EXPECTED_MANIFEST_SHA256 else (_ for _ in ()).throw(AssertionError("manifest digest mismatch"))
    ))

    def contract_check():
        spec = manifest["remediation_contract"]
        assert contract_path.stat().st_size == spec["bytes"]
        assert sha256(contract_path) == spec["sha256"]
        return {"bytes": spec["bytes"], "sha256": spec["sha256"]}
    check(CHECK_NAMES[1], contract_check)

    def frozen_r6_check():
        failures = []
        for spec in manifest["frozen_r6_files"]:
            path = ROOT / spec["path"]
            if path.stat().st_size != spec["bytes"] or sha256(path) != spec["sha256"]:
                failures.append(spec["path"])
        assert not failures, failures
        return {"checked": len(manifest["frozen_r6_files"]), "failures": failures}
    check(CHECK_NAMES[2], frozen_r6_check)

    r5_result: dict[str, Any] = {}
    r6_result: dict[str, Any] = {}
    def r5_check():
        nonlocal r5_result
        r5_result = run_validator(PHASE3 / "validate_r5_synthesis.py")
        assert (r5_result["result"], r5_result["checks_passed"], r5_result["checks_run"]) == ("PASS", 29, 29)
        return {"result": "PASS", "checks": "29/29", "receipt_payload_sha256": r5_result["receipt_payload_sha256"]}
    check(CHECK_NAMES[3], r5_check)

    def r6_check():
        nonlocal r6_result
        r6_result = run_validator(R6 / "validate_r6_checkpoint.py")
        assert (r6_result["result"], r6_result["checks_passed"], r6_result["checks_run"]) == ("PASS", 26, 26)
        return {"result": "PASS", "checks": "26/26", "receipt_payload_sha256": r6_result["receipt_payload_sha256"]}
    check(CHECK_NAMES[4], r6_check)

    check(CHECK_NAMES[5], lambda: manifest["runtime_lock"] if manifest["runtime_lock"] == {
        "model": "gpt-5.6-sol", "reasoning": "high", "execution_mode": "fresh_dedicated_worktree_task"
    } else (_ for _ in ()).throw(AssertionError("runtime lock mismatch")))

    def r6_state_check():
        assert findings["verdict"] == "REVISE"
        assert findings["severity_counts"] == {"Critical": 0, "Major": 1, "Minor": 2, "Observation": 5}
        blocker = [f for f in findings["findings"] if f.get("r7_blocking")]
        assert [f["finding_id"] for f in blocker] == ["R6-MAJ-001"]
        assert findings["scholar_checkpoint"]["pending"] == 12
        return {"verdict": "REVISE", "blocker": "R6-MAJ-001", "pending": 12}
    check(CHECK_NAMES[6], r6_state_check)

    def phase_check():
        phase = findings["phase_boundary"]
        assert phase["r7_authorized"] is False and phase["stage1b_sealed"] is False
        assert phase["stage2_production_citations"] == "NOT_AUTHORIZED"
        assert phase["h1_h4"] == "NOT_RUN"
        return phase
    check(CHECK_NAMES[7], phase_check)

    def source_set_check():
        assert set(denominators["themes"]) == set(EXPECTED_THEME_COUNTS)
        for theme_id, theme in denominators["themes"].items():
            assert [r["record_key"] for r in theme["records"]] == extract_theme_refs(original_text, theme_id)
        return {theme_id: [r["record_key"] for r in denominators["themes"][theme_id]["records"]] for theme_id in denominators["themes"]}
    check(CHECK_NAMES[8], source_set_check)

    def family_resolution_check():
        failures = []
        for theme in denominators["themes"].values():
            for record in theme["records"]:
                index = resource_to_family if record["record_kind"] == "operational" else source_to_family
                if index.get(record["record_key"]) != record["family_id"]:
                    failures.append(record)
        assert not failures, failures
        return {"records_checked": sum(len(t["records"]) for t in denominators["themes"].values()), "failures": failures}
    check(CHECK_NAMES[9], family_resolution_check)

    def dependency_check():
        result = {}
        for theme_id, theme in denominators["themes"].items():
            expected = relevant_edges(theme, family_map)
            assert theme["dependency_edges"] == expected
            result[theme_id] = len(expected)
        return result
    check(CHECK_NAMES[10], dependency_check)

    def denominator_check():
        replay = {}
        for theme_id, theme in denominators["themes"].items():
            canonical = len(theme["records"])
            nominal = len({record["family_id"] for record in theme["records"]})
            adjusted = adjusted_family_count(theme)
            assert (canonical, nominal, adjusted) == EXPECTED_THEME_COUNTS[theme_id]
            assert canonical == theme["counts"]["canonical_record_count"]
            assert nominal == theme["counts"]["nominal_family_count"]
            assert adjusted == theme["counts"]["dependency_adjusted_family_count"]
            replay[theme_id] = {"canonical": canonical, "nominal": nominal, "adjusted": adjusted}
        return {"mismatches": 0, "replay": replay}
    check(CHECK_NAMES[11], denominator_check)

    def separated_check():
        for theme in denominators["themes"].values():
            assert set(theme["counts"]) == {"canonical_record_count", "nominal_family_count", "dependency_adjusted_family_count"}
        return "three separately named count fields per theme"
    check(CHECK_NAMES[12], separated_check)

    def t5_check():
        t5 = denominators["themes"]["T5"]
        assert t5["evidence_domain"] == "operational"
        assert all(row["record_kind"] == "operational" for row in t5["records"])
        assert t5["robustness"] == "FRAGILE_SINGLE_FAMILY"
        assert all(denominators["themes"][t]["evidence_domain"] == "scholarly" for t in ("T1", "T2", "T3", "T4"))
        return t5["counts"]
    check(CHECK_NAMES[13], t5_check)

    def pointer_check():
        missing = [theme_id for theme_id in EXPECTED_THEME_COUNTS if f"theme_evidence_denominators.json#/themes/{theme_id}" not in remediated_text]
        assert not missing, missing
        return {"theme_pointers": 5, "missing": missing}
    check(CHECK_NAMES[14], pointer_check)

    def prose_value_check():
        for theme_id, values in EXPECTED_THEME_COUNTS.items():
            canonical, nominal, adjusted = values
            pointer = f"theme_evidence_denominators.json#/themes/{theme_id}"
            assert pointer in remediated_text
            window_start = max(0, remediated_text.index(pointer) - 240)
            window = remediated_text[window_start:remediated_text.index(pointer)]
            for value in {canonical, nominal, adjusted}:
                assert str(value) in window or {1: "one", 2: "two", 6: "six", 8: "eight", 9: "nine"}[value] in window.lower()
        return {"prose_denominator_mismatches": 0}
    check(CHECK_NAMES[15], prose_value_check)

    check(CHECK_NAMES[16], lambda: {"claims": 44, "unique": 44} if len(original_map["claims"]) == len({c["claim_id"] for c in original_map["claims"]}) == 44 else (_ for _ in ()).throw(AssertionError("claim population mismatch")))

    def counter_count_check():
        entries = counter["entries"]
        assert len(entries) == len({e["claim_id"] for e in entries}) == 44
        assert set(e["claim_id"] for e in entries) == set(c["claim_id"] for c in original_map["claims"])
        assert all(e["status"] == "bounded_counter_evidence" for e in entries)
        assert counter["counts"]["none_identified"] == 0
        return counter["counts"]
    check(CHECK_NAMES[17], counter_count_check)

    def upstream_exact_check():
        for entry in counter["entries"]:
            path = ROOT / entry["upstream_basis"]["artifact_path"]
            assert sha256(path) == entry["upstream_basis"]["artifact_sha256"]
            lane_json = load_json(path)
            pointer = entry["upstream_basis"]["json_pointer"].strip("/").split("/")
            target: Any = lane_json
            for part in pointer:
                target = target[int(part)] if isinstance(target, list) else target[part]
            assert target == [item["text"] for item in entry["counter_evidence_items"]]
            assert target
        return {"entries_replayed": 44, "mismatches": 0}
    check(CHECK_NAMES[18], upstream_exact_check)

    def pointer_resolution_check():
        checked = 0
        verified = 0
        not_verified = 0
        for entry in counter["entries"]:
            assert entry["source_locator_pointers"]
            for pointer in entry["source_locator_pointers"]:
                locator = locator_index[pointer["locator_id"]]
                assert pointer["source_key"] == locator.get("source_key")
                assert pointer["resource_key"] == locator.get("resource_key")
                assert pointer["family_id"] == locator["source_family_id"]
                assert pointer["verified_against_original"] == locator["verified_against_original"]
                verified += locator["verified_against_original"] is True
                not_verified += locator["verified_against_original"] is not True
                checked += 1
        return {"pointers_checked": checked, "verified_against_original": verified, "bounded_not_original_verified": not_verified, "dangling": 0}
    check(CHECK_NAMES[19], pointer_resolution_check)

    def graph_check():
        all_ids = [p["locator_id"] for e in counter["entries"] for p in e["source_locator_pointers"]]
        assert len(all_ids) == len(set((e["claim_id"], p["locator_id"]) for e in counter["entries"] for p in e["source_locator_pointers"]))
        assert all(locator_id in locator_index for locator_id in all_ids)
        return {"duplicate_claim_locator_edges": 0, "dangling_locator_edges": 0}
    check(CHECK_NAMES[20], graph_check)

    def row_drift_check():
        assert len(remediated_map["claims"]) == 44
        for old, new in zip(original_map["claims"], remediated_map["claims"]):
            reduced = deepcopy(new)
            reduced.pop("counter_evidence_binding")
            assert reduced == old
        return {"rows_compared": 44, "intended_claim_drift": 0}
    check(CHECK_NAMES[21], row_drift_check)

    def intent_join_check():
        by_source = {row["source_claim_id"]: row for row in intent["claims"]}
        assert len(by_source) == 44
        for row in remediated_map["claims"]:
            intended = by_source[row["claim_id"]]
            assert row["claim_text_bounded"] == intended["claim_text"]
            assert row["canonical_source_keys"] == intended["planned_refs"]
            assert row["source_family_ids"] == intended["planned_source_family_ids"]
        return {"one_shot_manifest_sha256": sha256(PHASE3 / "claim_intent_manifest_r1.json"), "joins": 44, "drift": 0}
    check(CHECK_NAMES[22], intent_join_check)

    def disposition_check():
        values = [row["r5_disposition"] for row in remediated_map["claims"]]
        assert values.count("citation_ready_candidate") == 22 and values.count("planning_only") == 22
        return {"citation_ready_candidate": 22, "planning_only": 22}
    check(CHECK_NAMES[23], disposition_check)

    def citation_identity_check():
        old, new = marker_pairs(original_text), marker_pairs(remediated_text)
        assert old == new and len(old) == 33
        return {"original": len(old), "remediated": len(new), "byte_identical_pairs": 33}
    check(CHECK_NAMES[24], citation_identity_check)

    def anchor_check():
        pairs = marker_pairs(remediated_text)
        assert all("<!--anchor:none:" not in pair for pair in pairs)
        assert all(re.match(r"<!--ref:[^>]+--><!--anchor:(quote|page|section|paragraph|table|figure):.+-->", pair) for pair in pairs)
        return {"checked": len(pairs), "none": 0, "invalid": 0}
    check(CHECK_NAMES[25], anchor_check)

    def tension_check():
        assert sha256(PHASE3 / "cross_paper_tensions_r1.json") == "56a16ed2f19b7467b5d43ff4d2136fa72dd5ecf9e04bd7ac826a3025ab032943"
        rows = tensions["cross_paper_tensions"]
        assert len(rows) == 12 and all(row["scholar_confirmation"] == "pending" for row in rows)
        assert tension_packet["counts"]["scholar_confirmation_pending"] == 12
        t2 = next(row for row in tension_packet["pairs"] if row["pair_id"] == "T-002")
        assert t2["r5_pair_assessment"] == "conditional_difference" and t2["r5_resolution_status"] == "resolved_in_synthesis"
        assert t2["r6_recommendation"] == "dispute" and t2["scholar_confirmation"] == "pending"
        return {"pairs": 12, "pending": 12, "T-002": "unchanged_pending_with_DA_dispute_recommendation"}
    check(CHECK_NAMES[26], tension_check)

    def finding_status_check():
        required = {
            "R6-MAJ-001": "REMEDIATED_PENDING_REAUDIT",
            "R6-MIN-001": "PENDING_SCHOLAR_ADJUDICATION",
            "R6-MIN-002": "ADDRESSED_PENDING_REAUDIT",
        }
        assert handoff.get("finding_statuses") == required if args.final else all(value in report_text for value in required.values())
        if args.final:
            for key, value in required.items():
                assert key in report_text and value in report_text
        return required
    check(CHECK_NAMES[27], finding_status_check)

    def authorization_check():
        if args.final:
            assert handoff["r7_authorized"] is False
            assert handoff["authorized_next_action"] == "fresh_R6_reaudit_only"
        return {"r7_authorized": False, "authorized_next_action": "fresh_R6_reaudit_only"}
    check(CHECK_NAMES[28], authorization_check)

    def downstream_check():
        expected = {
            "r6_reaudit": "NOT_PERFORMED",
            "r7_r9": "NOT_PERFORMED",
            "manuscript_drafting": "NOT_PERFORMED",
            "benchmark_training_evaluation": "NOT_RUN",
            "h1_h4": "NOT_RUN",
        }
        if args.final:
            assert handoff["phase_boundary"] == expected
        return expected
    check(CHECK_NAMES[29], downstream_check)

    def hash_map_check(binding: dict[str, str], owner: str):
        assert owner not in binding
        for path_text, digest in binding.items():
            assert sha256(ROOT / path_text) == digest
        return {"checked": len(binding), "self_hash_present": False}
    check(CHECK_NAMES[30], lambda: hash_map_check(receipt["artifact_sha256"], rel(OUT / "r6_remediation_validation_receipt.json")) if args.final else {"skipped": "requires --final"})
    check(CHECK_NAMES[31], lambda: hash_map_check(handoff["artifact_sha256"], rel(OUT / "r6_remediation_handoff.json")) if args.final else {"skipped": "requires --final"})

    def roster_check():
        present = {path.name for path in OUT.iterdir() if path.is_file()}
        missing = EXPECTED_FILES - present
        assert not missing, sorted(missing)
        return {"required_and_support_files": len(EXPECTED_FILES), "missing": []}
    check(CHECK_NAMES[32], roster_check)

    failed = [item for item in checks if item["status"] == "FAIL"]
    result = {
        "schema_version": "stage1b-r1-r6-remediation-semantic-validation-1.0",
        "validation_mode": "final" if args.final else "core",
        "result": "PASS" if not failed else "FAIL",
        "checks_run": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "checks": checks,
        "failures": failed,
        "recomputed": {
            "denominator_mismatches": 0 if not any(c["name"] == CHECK_NAMES[11] and c["status"] == "FAIL" for c in checks) else None,
            "claims_bound": len(counter["entries"]),
            "citation_marker_pairs": len(marker_pairs(remediated_text)),
            "tension_pairs": len(tensions["cross_paper_tensions"]),
            "scholar_confirmations_pending": sum(row["scholar_confirmation"] == "pending" for row in tensions["cross_paper_tensions"]),
            "r7_authorized": False,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
