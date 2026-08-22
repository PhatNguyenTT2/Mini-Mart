#!/usr/bin/env python3
"""Deterministic validator for the fresh Stage 1B R6 remediation re-audit."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in (HERE, *HERE.parents) if (p / ".git").exists())
BASE = Path("research/hybrid-recsys-v5/01_research/literature_review/remediation_r1")
CONTROL = BASE / "00_control"
P2 = BASE / "phase2_investigation"
P3 = BASE / "phase3_analysis"
OUT = P3 / "devils_advocate_cp2_reaudit"

REAUDIT_MANIFEST = CONTROL / "r6_reaudit_input_manifest.json"
R5_MAP = P3 / "claim_source_map_r1.json"
R5_SYNTHESIS = P3 / "synthesis_report_r1.md"
TENSIONS = P3 / "cross_paper_tensions_r1.json"
FAMILY_MAP = P2 / "integration/source_family_map_r1.json"
LOCATORS = P2 / "acquisition/locator_registry.json"
R6_FINDINGS = P3 / "devils_advocate_cp2/r6_findings.json"
R6_PACKET = P3 / "devils_advocate_cp2/tension_adjudication_packet.json"
R6_HANDOFF = P3 / "devils_advocate_cp2/r6_handoff.json"
R5_HANDOFF = P3 / "r5_handoff.json"
DENOMS = P3 / "remediation_r6/theme_evidence_denominators.json"
OVERLAY = P3 / "remediation_r6/claim_counter_evidence_overlay.json"
REM_MAP = P3 / "remediation_r6/claim_source_map_r1_remediated.json"
REM_SYNTHESIS = P3 / "remediation_r6/synthesis_report_r1_remediated.md"
REM_HANDOFF = P3 / "remediation_r6/r6_remediation_handoff.json"
REM_RECEIPT = P3 / "remediation_r6/r6_remediation_validation_receipt.json"

REPORT = OUT / "r6_reaudit_report.md"
FINDINGS = OUT / "r6_reaudit_findings.json"
PACKET = OUT / "tension_adjudication_packet_reaudit.json"
RECEIPT = OUT / "r6_reaudit_validation_receipt.json"
HANDOFF = OUT / "r6_reaudit_handoff.json"
VALIDATOR = OUT / "validate_r6_reaudit.py"


def abspath(path: Path | str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def rel(path: Path) -> str:
    return abspath(path).relative_to(ROOT).as_posix()


def sha256(path: Path | str) -> str:
    return hashlib.sha256(abspath(path).read_bytes()).hexdigest()


def load_json(path: Path | str) -> Any:
    return json.loads(abspath(path).read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def resolve_declared(raw: str, declaring: Path, integration_root: str | None) -> Path:
    candidates = [abspath(raw)]
    if integration_root:
        candidates.append(abspath(Path(integration_root) / raw))
    candidates.append(declaring.parent / raw)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return candidates[0].resolve()


def recursive_declaration_audit(seed: Path) -> dict[str, Any]:
    queue: deque[Path] = deque([abspath(seed)])
    visited: set[Path] = set()
    rows: list[dict[str, Any]] = []
    seen_rows: set[tuple[str, str, int | None, str]] = set()

    def add_row(
        declaring: Path,
        raw_path: str,
        expected_sha: str,
        expected_bytes: int | None,
        integration_root: str | None,
    ) -> None:
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            return
        target = resolve_declared(raw_path, declaring, integration_root)
        key = (str(declaring), raw_path, expected_bytes, expected_sha)
        if key in seen_rows:
            return
        seen_rows.add(key)
        exists = target.is_file()
        actual_bytes = target.stat().st_size if exists else None
        actual_sha = sha256(target) if exists else None
        row = {
            "declared_in": rel(declaring),
            "declared_path": raw_path,
            "resolved_path": rel(target) if exists and ROOT in target.parents else str(target),
            "expected_bytes": expected_bytes,
            "actual_bytes": actual_bytes,
            "expected_sha256": expected_sha,
            "actual_sha256": actual_sha,
            "pass": exists
            and (expected_bytes is None or expected_bytes == actual_bytes)
            and expected_sha == actual_sha,
        }
        rows.append(row)
        if exists and target.suffix.lower() == ".json":
            queue.append(target)

    def walk(node: Any, declaring: Path, integration_root: str | None) -> None:
        if isinstance(node, dict):
            if {"path", "sha256"} <= node.keys() and isinstance(node["path"], str):
                add_row(declaring, node["path"], node["sha256"], node.get("bytes"), integration_root)

            for key, value in node.items():
                if key.endswith("_path") and isinstance(value, str):
                    prefix = key[:-5]
                    sha_key = f"{prefix}_sha256"
                    bytes_key = f"{prefix}_bytes"
                    if sha_key in node:
                        add_row(declaring, value, node[sha_key], node.get(bytes_key), integration_root)
                if isinstance(key, str) and isinstance(value, str):
                    if "/" in key and re.fullmatch(r"[0-9a-f]{64}", value):
                        add_row(declaring, key, value, None, integration_root)
            for value in node.values():
                walk(value, declaring, integration_root)
        elif isinstance(node, list):
            for value in node:
                walk(value, declaring, integration_root)

    while queue:
        current = queue.popleft().resolve()
        if current in visited:
            continue
        visited.add(current)
        try:
            obj = load_json(current)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        integration_root = obj.get("integration_root") if isinstance(obj, dict) else None
        walk(obj, current, integration_root)

    failures = [row for row in rows if not row["pass"]]
    return {
        "json_files_scanned": len(visited),
        "declarations_checked": len(rows),
        "unique_targets": len({row["resolved_path"] for row in rows}),
        "failures": failures,
    }


def json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError(f"invalid JSON pointer: {pointer}")
    value = document
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def extract_theme_refs(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for number in range(1, 6):
        match = re.search(
            rf"(?ms)^## Theme {number}\b.*?\n(.*?)(?=^## (?:Theme [1-5]\b|Convergence and divergence))",
            text,
        )
        if not match:
            result[f"T{number}"] = []
            continue
        refs = re.findall(r"<!--ref:([^>]+)-->", match.group(1))
        result[f"T{number}"] = list(dict.fromkeys(refs))
    return result


def citation_pairs(text: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(r"<!--ref:([^>]+)--><!--anchor:([^>]+)-->")
    return [(m.group(1), m.group(2), m.group(0)) for m in pattern.finditer(text)]


class DSU:
    def __init__(self, values: list[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true", help="write the deterministic final receipt")
    args = parser.parse_args()

    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any) -> None:
        checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})

    manifest = load_json(REAUDIT_MANIFEST)
    declaration_audit = recursive_declaration_audit(REAUDIT_MANIFEST)
    check(
        "fail_closed_recursive_byte_sha_gate",
        not declaration_audit["failures"]
        and declaration_audit["json_files_scanned"] >= 59
        and declaration_audit["declarations_checked"] >= 190,
        declaration_audit,
    )
    check(
        "runtime_lock_exact",
        manifest["runtime_lock"]
        == {
            "model": "gpt-5.6-sol",
            "reasoning": "high",
            "execution_mode": "fresh_dedicated_worktree_task",
        },
        manifest["runtime_lock"],
    )

    r5_handoff = load_json(R5_HANDOFF)
    r6_handoff = load_json(R6_HANDOFF)
    rem_handoff = load_json(REM_HANDOFF)
    rem_receipt = load_json(REM_RECEIPT)
    gates = manifest["gates"]
    gate_detail = {
        "r5": {"verdict": r5_handoff["verdict"], "sha256": sha256(R5_HANDOFF)},
        "r6": {"verdict": r6_handoff["verdict"], "sha256": sha256(R6_HANDOFF)},
        "remediation": {"verdict": rem_handoff["verdict"], "sha256": sha256(REM_HANDOFF)},
    }
    check(
        "signed_gate_handoffs_exact",
        gate_detail["r5"] == {"verdict": gates["r5"]["verdict"], "sha256": gates["r5"]["handoff_sha256"]}
        and gate_detail["r6"] == {"verdict": gates["r6_original"]["verdict"], "sha256": gates["r6_original"]["handoff_sha256"]}
        and gate_detail["remediation"]
        == {"verdict": gates["r6_remediation"]["verdict"], "sha256": gates["r6_remediation"]["handoff_sha256"]},
        gate_detail,
    )
    check(
        "declared_final_validation_gates",
        gates["r5"]["final_validation"] == "PASS_29_OF_29"
        and gates["r6_original"]["final_validation"] == "PASS_26_OF_26"
        and gates["r6_remediation"]["final_validation"] == "PASS_33_OF_33"
        and rem_receipt["result"] == "PASS"
        and rem_receipt["checks_run"] == rem_receipt["checks_passed"] == 33
        and rem_receipt["checks_failed"] == 0,
        {
            "r5": gates["r5"]["final_validation"],
            "r6_original": gates["r6_original"]["final_validation"],
            "r6_remediation": gates["r6_remediation"]["final_validation"],
        },
    )

    denom = load_json(DENOMS)
    family_map = load_json(FAMILY_MAP)
    original_text = abspath(R5_SYNTHESIS).read_text(encoding="utf-8")
    rem_text = abspath(REM_SYNTHESIS).read_text(encoding="utf-8")
    visible_sets = extract_theme_refs(original_text)
    family_by_source: dict[str, str] = {}
    family_by_resource: dict[str, str] = {}
    for family in family_map["families"]:
        for key in family["scholarly_source_keys"]:
            family_by_source[key] = family["source_family_id"]
        for key in family["operational_resource_keys"]:
            family_by_resource[key] = family["source_family_id"]

    theme_replay: dict[str, Any] = {}
    source_set_ok = family_ok = dependency_ok = arithmetic_ok = True
    expected_counts = {
        "T1": (6, 6, 6),
        "T2": (8, 8, 8),
        "T3": (8, 8, 8),
        "T4": (9, 9, 8),
        "T5": (2, 1, 1),
    }
    for theme_id, refs in visible_sets.items():
        theme = denom["themes"][theme_id]
        record_keys = [record["record_key"] for record in theme["records"]]
        source_set_ok &= refs == record_keys
        resolved_families = [family_by_source.get(key) or family_by_resource.get(key) for key in refs]
        unique_families = list(dict.fromkeys(resolved_families))
        family_ok &= None not in resolved_families and unique_families == theme["family_ids"]
        ref_set, family_set = set(refs), set(unique_families)
        relevant_dependencies = [
            dep
            for dep in family_map["dependencies"]
            if dep["source_family_id"] in family_set
            and dep["depends_on_family_id"] in family_set
            and ref_set.intersection(dep["source_keys"] + dep["resource_keys"])
        ]
        dependency_ok &= canonical(relevant_dependencies) == canonical(theme["dependency_edges"])
        dsu = DSU(unique_families)
        for dep in relevant_dependencies:
            if (
                dep["counting_effect"] == "not_an_additional_independent_source_family"
                and dep["source_family_id"] != dep["depends_on_family_id"]
            ):
                dsu.union(dep["source_family_id"], dep["depends_on_family_id"])
        replay_counts = (len(refs), len(unique_families), len({dsu.find(f) for f in unique_families}))
        stored_counts = theme["counts"]
        stored_tuple = (
            stored_counts["canonical_record_count"],
            stored_counts["nominal_family_count"],
            stored_counts["dependency_adjusted_family_count"],
        )
        arithmetic_ok &= replay_counts == stored_tuple == expected_counts[theme_id]
        theme_replay[theme_id] = {
            "records": refs,
            "families": unique_families,
            "relevant_dependency_edges": relevant_dependencies,
            "replayed_counts": {
                "canonical": replay_counts[0],
                "nominal": replay_counts[1],
                "dependency_adjusted": replay_counts[2],
            },
        }
    check("five_theme_source_sets_replayed_from_frozen_r5", source_set_ok, theme_replay)
    check("theme_family_resolution_exact", family_ok, theme_replay)
    check("theme_dependency_edges_exact", dependency_ok, theme_replay)
    check("canonical_nominal_adjusted_arithmetic_exact", arithmetic_ok, theme_replay)
    check(
        "theme5_operational_single_family_boundary",
        denom["themes"]["T5"]["evidence_domain"] == "operational"
        and denom["themes"]["T5"]["robustness"] == "FRAGILE_SINGLE_FAMILY"
        and all(record["record_kind"] == "operational" for record in denom["themes"]["T5"]["records"]),
        denom["themes"]["T5"],
    )

    denominator_pointers = re.findall(r"\[denominator: `theme_evidence_denominators\.json#([^`]+)`\]", rem_text)
    pointer_failures: list[str] = []
    for pointer in denominator_pointers:
        try:
            json_pointer(denom, pointer)
        except (KeyError, IndexError, ValueError, TypeError):
            pointer_failures.append(pointer)
    exact_list_failures: list[str] = []
    for theme_id, replay in theme_replay.items():
        if f"theme_evidence_denominators.json#/themes/{theme_id}" not in rem_text:
            exact_list_failures.append(f"missing_pointer:{theme_id}")
        source_line = "Exact source keys: " + ", ".join(replay["records"]) + "."
        if theme_id == "T5":
            source_line = "Exact operational resource keys: " + ", ".join(replay["records"]) + "."
        if source_line not in rem_text:
            exact_list_failures.append(f"source_list:{theme_id}")
    check(
        "prose_denominator_pointers_resolve",
        len(denominator_pointers) >= 15 and not pointer_failures,
        {"pointers": len(denominator_pointers), "failures": pointer_failures},
    )
    check("prose_exact_source_lists_match_arrays", not exact_list_failures, exact_list_failures)

    original_pairs = citation_pairs(original_text)
    rem_pairs = citation_pairs(rem_text)
    locator_registry = load_json(LOCATORS)
    locators_by_ref: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for locator in locator_registry["locators"]:
        key = locator.get("source_key") or locator.get("resource_key")
        anchor = f"{locator['locator_type']}:{locator['locator_value']}"
        locators_by_ref.setdefault((key, anchor), []).append(locator)
    locator_failures: list[dict[str, Any]] = []
    for ref_key, anchor, _ in rem_pairs:
        matches = [
            row
            for row in locators_by_ref.get((ref_key, anchor), [])
            if row["verified_against_original"] is True and row["page_anchor"] is False
        ]
        if len(matches) != 1:
            locator_failures.append({"ref": ref_key, "anchor": anchor, "matches": len(matches)})
    check(
        "citation_marker_anchor_pairs_unchanged_33_of_33",
        len(original_pairs) == len(rem_pairs) == 33
        and [row[2] for row in original_pairs] == [row[2] for row in rem_pairs]
        and len({row[2] for row in rem_pairs}) == 33,
        {"original": len(original_pairs), "remediated": len(rem_pairs)},
    )
    check(
        "citation_pairs_resolve_to_verified_nonpage_locators",
        not locator_failures,
        {"resolved": 33 - len(locator_failures), "failures": locator_failures},
    )

    original_map = load_json(R5_MAP)
    rem_map = load_json(REM_MAP)
    overlay = load_json(OVERLAY)
    original_by_id = {row["claim_id"]: row for row in original_map["claims"]}
    rem_by_id = {row["claim_id"]: row for row in rem_map["claims"]}
    overlay_by_id = {row["claim_id"]: row for row in overlay["entries"]}
    claim_ids = set(original_by_id)
    population_ok = (
        len(original_by_id) == len(rem_by_id) == len(overlay_by_id) == 44
        and claim_ids == set(rem_by_id) == set(overlay_by_id)
    )
    check("claim_population_44_unique_and_joined", population_ok, sorted(claim_ids))

    drift: list[str] = []
    counter_failures: list[str] = []
    locator_join_failures: list[str] = []
    locator_by_id = {row["locator_id"]: row for row in locator_registry["locators"]}
    counter_items = 0
    pointer_count = 0
    for claim_id in sorted(claim_ids):
        original_claim = original_by_id[claim_id]
        rem_claim = rem_by_id[claim_id]
        stripped = {key: value for key, value in rem_claim.items() if key != "counter_evidence_binding"}
        if canonical(stripped) != canonical(original_claim):
            drift.append(claim_id)
        entry = overlay_by_id[claim_id]
        basis = entry["upstream_basis"]
        upstream_path = abspath(basis["artifact_path"])
        try:
            upstream = load_json(upstream_path)
            upstream_claim = json_pointer(upstream, basis["claim_json_pointer"])
            upstream_counter = json_pointer(upstream, basis["json_pointer"])
        except (OSError, KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError):
            counter_failures.append(f"pointer:{claim_id}")
            continue
        if sha256(upstream_path) != basis["artifact_sha256"] or upstream_claim["claim_id"] != claim_id:
            counter_failures.append(f"basis:{claim_id}")
        items = entry["counter_evidence_items"]
        counter_items += len(items)
        if [item["text"] for item in items] != upstream_counter or not items:
            counter_failures.append(f"text:{claim_id}")
        for item in items:
            try:
                if json_pointer(upstream, item["upstream_json_pointer"]) != item["text"]:
                    counter_failures.append(f"item_pointer:{claim_id}:{item['item_id']}")
            except (KeyError, IndexError, ValueError, TypeError):
                counter_failures.append(f"item_pointer:{claim_id}:{item['item_id']}")
        pointers = entry["source_locator_pointers"]
        pointer_count += len(pointers)
        for pointer in pointers:
            locator = locator_by_id.get(pointer["locator_id"])
            if locator is None:
                locator_join_failures.append(f"missing:{claim_id}:{pointer['locator_id']}")
                continue
            expected = {
                "locator_id": locator["locator_id"],
                "source_key": locator.get("source_key"),
                "resource_key": locator.get("resource_key"),
                "family_id": locator["source_family_id"],
                "locator_type": locator["locator_type"],
                "locator_value": locator["locator_value"],
                "verified_against_original": locator["verified_against_original"],
            }
            if pointer != expected or pointer["locator_id"] not in original_claim["locator_ids"]:
                locator_join_failures.append(f"mismatch:{claim_id}:{pointer['locator_id']}")
        binding = rem_claim.get("counter_evidence_binding", {})
        if binding != {
            "overlay_entry_id": entry["overlay_entry_id"],
            "status": entry["status"],
            "counter_evidence_item_count": len(items),
            "source_locator_pointer_count": len(pointers),
        }:
            counter_failures.append(f"binding:{claim_id}")
    check("remediated_claim_rows_zero_intent_or_disposition_drift", not drift, drift)
    disposition_counts = Counter(row["r5_disposition"] for row in rem_map["claims"])
    check(
        "claim_dispositions_preserved_22_and_22",
        disposition_counts == Counter({"citation_ready_candidate": 22, "planning_only": 22}),
        dict(disposition_counts),
    )
    check(
        "counter_evidence_exact_upstream_44_of_44",
        not counter_failures and counter_items == 51,
        {"claims": 44, "items": counter_items, "failures": counter_failures},
    )
    check(
        "counter_evidence_locator_joins_resolve_136",
        not locator_join_failures and pointer_count == 136,
        {"pointers": pointer_count, "failures": locator_join_failures},
    )

    tension_source = load_json(TENSIONS)
    r6_packet = load_json(R6_PACKET)
    tension_rows = tension_source["cross_paper_tensions"]
    packet_rows = r6_packet["pairs"]
    tension_by_id = {row["pair_id"]: row for row in tension_rows}
    packet_by_id = {row["pair_id"]: row for row in packet_rows}
    tension_failures: list[str] = []
    for pair_id in sorted(tension_by_id):
        source = tension_by_id[pair_id]
        packet_row = packet_by_id.get(pair_id)
        if packet_row is None:
            tension_failures.append(f"missing:{pair_id}")
            continue
        if (
            packet_row["paper_a"] != source["paper_a"]
            or packet_row["paper_b"] != source["paper_b"]
            or packet_row["r5_pair_assessment"] != source["pair_assessment"]
            or packet_row["r5_resolution_status"] != source["resolution_status"]
            or packet_row["scholar_confirmation"] != source["scholar_confirmation"] != "pending"
        ):
            tension_failures.append(f"drift:{pair_id}")
    recommendations = Counter(row["r6_recommendation"] for row in packet_rows)
    check(
        "twelve_tensions_unchanged_pending_with_t002_dispute",
        len(tension_by_id) == len(packet_by_id) == 12
        and not tension_failures
        and recommendations == Counter({"confirm": 11, "dispute": 1})
        and packet_by_id["T-002"]["r6_recommendation"] == "dispute",
        {"recommendations": dict(recommendations), "failures": tension_failures},
    )

    findings = load_json(FINDINGS)
    reassessment = {row["finding_id"]: row for row in findings["original_finding_reassessments"]}
    expected_statuses = {
        "R6-MAJ-001": "CLOSED_BY_FRESH_REAUDIT",
        "R6-MIN-001": "OPEN_PENDING_SCHOLAR_ADJUDICATION",
        "R6-MIN-002": "CLOSED_BY_FRESH_REAUDIT",
        "R6-OBS-001": "PRESERVED_OBSERVATION",
        "R6-OBS-002": "PRESERVED_OBSERVATION",
        "R6-OBS-003": "PRESERVED_OBSERVATION",
        "R6-OBS-004": "PRESERVED_OBSERVATION",
        "R6-OBS-005": "PRESERVED_OBSERVATION",
    }
    check(
        "all_original_r6_findings_reassessed",
        set(reassessment) == set(expected_statuses)
        and all(reassessment[key]["reaudit_status"] == value for key, value in expected_statuses.items()),
        {key: row["reaudit_status"] for key, row in reassessment.items()},
    )
    expected_severity = {"Critical": 0, "Major": 0, "Minor": 1, "Observation": 5}
    check(
        "severity_arithmetic_and_no_new_critical_major",
        findings["severity_counts"] == expected_severity
        and findings["new_findings"] == []
        and findings["verdict"] == "PASS_PENDING_SCHOLAR_CONFIRMATION",
        {"severity_counts": findings["severity_counts"], "new_findings": findings["new_findings"]},
    )

    out_packet = load_json(PACKET)
    out_by_id = {row["pair_id"]: row for row in out_packet["pairs"]}
    packet_unchanged = len(out_by_id) == 12
    for pair_id, original_row in packet_by_id.items():
        row = out_by_id.get(pair_id, {})
        for field in (
            "paper_a",
            "paper_b",
            "r5_pair_assessment",
            "r5_resolution_status",
            "r5_resolution_pointer",
            "r6_recommendation",
            "rationale",
            "scholar_confirmation",
        ):
            packet_unchanged &= row.get(field) == original_row.get(field)
    check(
        "reaudit_tension_packet_preserves_scholar_authority",
        packet_unchanged
        and out_packet["counts"]["scholar_confirmation_pending"] == 12
        and out_packet["adjudication_requirement"]["r7_authorized"] is False,
        out_packet["counts"],
    )

    report_text = abspath(REPORT).read_text(encoding="utf-8")
    required_report_tokens = [
        "PASS_PENDING_SCHOLAR_CONFIRMATION",
        "Critical 0 · Major 0 · Minor 1 · Observation 5",
        "R6-MAJ-001",
        "R6-MIN-001",
        "R6-MIN-002",
        "Strongest hostile-reviewer counterargument",
        "Minimum defensible concession",
        "AI assistance disclosure",
        "H1–H4 remain `NOT_RUN`",
    ]
    check(
        "report_contract_and_devils_advocate_sections_complete",
        all(token in report_text for token in required_report_tokens),
        [token for token in required_report_tokens if token not in report_text],
    )

    handoff = load_json(HANDOFF)
    phase = handoff["phase_boundary"]
    check(
        "phase_boundary_fail_closed",
        handoff["verdict"] == "PASS_PENDING_SCHOLAR_CONFIRMATION"
        and handoff["r7_authorized"] is False
        and handoff["stage1b_sealed"] is False
        and handoff["stage2_production_citations_authorized"] is False
        and phase == {
            "r7_r9": "NOT_PERFORMED",
            "stage1b_seal": "NOT_PERFORMED",
            "stage2_authorization": "NOT_AUTHORIZED",
            "benchmark_training_evaluation": "NOT_RUN",
            "h1_h4": "NOT_RUN",
        },
        phase,
    )
    handoff_hash_failures = []
    for path_string, expected in handoff["artifact_sha256"].items():
        if sha256(path_string) != expected:
            handoff_hash_failures.append(path_string)
    check("handoff_nonself_artifact_hashes_resolve", not handoff_hash_failures, handoff_hash_failures)

    expected_roster = {
        "r6_reaudit_report.md",
        "r6_reaudit_findings.json",
        "tension_adjudication_packet_reaudit.json",
        "r6_reaudit_validation_receipt.json",
        "r6_reaudit_handoff.json",
        "validate_r6_reaudit.py",
    }
    actual_roster = {path.name for path in abspath(OUT).iterdir() if path.is_file()}
    check("output_roster_exact", actual_roster == expected_roster, sorted(actual_roster))

    failures = [row for row in checks if row["status"] == "FAIL"]
    receipt = {
        "schema_version": "stage1b-r1-r6-reaudit-validation-receipt-1.0",
        "validation_mode": "final" if args.final else "check",
        "result": "PASS" if not failures else "FAIL",
        "checks_run": len(checks),
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "check_names": [row["name"] for row in checks],
        "failures": failures,
        "recomputed": {
            "recursive_json_files_scanned": declaration_audit["json_files_scanned"],
            "recursive_declarations_checked": declaration_audit["declarations_checked"],
            "recursive_unique_targets": declaration_audit["unique_targets"],
            "themes": {key: value["replayed_counts"] for key, value in theme_replay.items()},
            "claims_joined": len(overlay_by_id),
            "counter_evidence_items": counter_items,
            "counter_evidence_locator_pointers": pointer_count,
            "citation_marker_anchor_pairs_unchanged": len(rem_pairs),
            "tension_pairs_pending": 12,
            "severity_counts": findings["severity_counts"],
            "pending_scholar_confirmations": 12,
        },
        "artifact_sha256": {
            rel(REPORT): sha256(REPORT),
            rel(FINDINGS): sha256(FINDINGS),
            rel(PACKET): sha256(PACKET),
            rel(HANDOFF): sha256(HANDOFF),
            rel(VALIDATOR): sha256(VALIDATOR),
        },
        "authority": "PASS validates only the fresh R6 re-audit bundle. It does not adjudicate tensions, authorize R7-R9, seal Stage 1B, authorize Stage 2, or run H1-H4.",
    }
    payload = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if args.final:
        abspath(RECEIPT).write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
