from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Callable


BASE = Path("research/hybrid-recsys-v5/01_research/literature_review/remediation_r1")
CONTROL = BASE / "00_control"
R7 = BASE / "phase4_freeze/r7_packet_r1"
OUT = BASE / "phase5_audit/r8_independent_audit"

R8_CONTRACT = CONTROL / "r8_audit_contract.md"
R8_INPUT = CONTROL / "r8_input_manifest.json"
R7_MANIFEST = R7 / "stage1b_r1_audit_packet_manifest.json"
R7_ROOT = R7 / "stage1b_r1_root_hash.json"
R7_HANDOFF = R7 / "r7_handoff.json"
R7_RECEIPT = R7 / "r7_validation_receipt.json"

EXPECTED_ROOT = "f0f2d56e42ce0f181f83182ddffe1060bf8994f50ababd4b0dbe563a942370dd"
EXPECTED_R8_INPUT_SHA256 = "319e10f1fc26263179c3f16bbed91eebddf2c9a8f915aab9a5772a7f159e68cf"
EXPECTED_R8_CONTRACT_SHA256 = "b251f8e3f676a0dd3c0b3a3258e281ce312d7278c71a7343419ec054d9788b13"

EXPECTED_OUTPUTS = {
    "r8_independent_audit_report.md",
    "r8_findings.json",
    "r8_packet_replay.json",
    "r8_validation_receipt.json",
    "r8_handoff.json",
    "validate_r8_audit.py",
}

CHECK_NAMES = [
    "r8_direct_control_byte_sha_gate",
    "r8_runtime_lock_exact",
    "r7_control_output_bindings_exact",
    "r7_final_validator_29_of_29",
    "upstream_r4_validator_22_of_22",
    "upstream_r5_validator_29_of_29",
    "upstream_r6_original_validator_26_of_26",
    "upstream_r6_remediation_validator_33_of_33",
    "upstream_r6_reaudit_validator_26_of_26",
    "packet_member_count_193",
    "packet_member_paths_normalized_sorted_unique",
    "packet_member_roles_162_27_4",
    "packet_member_byte_sha_replay",
    "canonical_preimage_shape_only",
    "canonical_preimage_bytes_43928",
    "canonical_root_sha256_replay",
    "manifest_root_handoff_receipt_consistency",
    "root_preimage_forbidden_surfaces_absent",
    "packet_current_superseded_roster_complete",
    "packet_member_role_labels_and_reasons",
    "corpus_registry_counts_replay",
    "corpus_registry_exact_included_set",
    "recent_source_count_32",
    "source_quality_matrix_replay",
    "canonical_identity_deduplication",
    "source_alias_map_resolves",
    "source_family_membership_exact",
    "source_family_dependency_graph_replay",
    "operational_resource_separation",
    "core_source_contract_23_1_24",
    "acquisition_queue_13_of_13",
    "locator_counts_75_61_14",
    "locator_target_family_joins",
    "locator_non_none_nonpage_boundary",
    "pdf_preflight_27_pass_1_unavailable",
    "claim_population_44_unique",
    "claim_intent_exact_join_zero_drift",
    "claim_dispositions_22_and_22",
    "planning_only_preserved_and_stage2_false",
    "counter_overlay_44_claims",
    "counter_evidence_51_exact_upstream",
    "counter_locator_joins_136",
    "counter_locator_provenance_114_22",
    "citation_marker_anchor_pairs_33_unchanged",
    "citation_pairs_verified_nonpage_locator_resolution",
    "five_theme_exact_source_sets",
    "five_theme_denominator_arithmetic",
    "theme_dependency_adjustments_exact",
    "prose_theme_denominator_pointers_exact",
    "strongest_source_removal_replay",
    "hostile_reviewer_boundary_text_present",
    "original_tension_roster_12_preserved",
    "scholar_decisions_11_1_0",
    "t002_historical_and_effective_classification",
    "zero_pending_zero_unresolved",
    "phase_boundary_unsealed_unauthorized_not_run",
    "r8_findings_verdict_arithmetic",
    "r8_packet_replay_record_exact",
    "r8_report_and_handoff_contract_exact",
    "r8_output_roster_and_nonself_hashes_exact",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_json(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True, encoding="utf-8")
    require(proc.returncode == 0, f"command failed ({proc.returncode}): {' '.join(command)}\n{proc.stderr}")
    return json.loads(proc.stdout, object_pairs_hook=strict_object)


def normalized_title(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", value).casefold() if ch.isalnum())


def marker_pairs(text: str) -> list[tuple[str, str, str]]:
    return re.findall(r"<!--ref:([^>]+)--><!--anchor:([^:>]+):(.*?)-->", text)


def check_hash_map(mapping: dict[str, str], excluded: set[str] | None = None) -> None:
    excluded = excluded or set()
    for rel, expected in mapping.items():
        if rel in excluded:
            continue
        path = Path(rel)
        require(path.is_file(), f"missing artifact in hash map: {rel}")
        require(sha256(path) == expected, f"artifact hash mismatch: {rel}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("final",), default="final")
    parser.parse_args()

    checks: list[dict[str, Any]] = []

    def check(name: str, fn: Callable[[], Any]) -> None:
        try:
            detail = fn()
            checks.append({"name": name, "status": "PASS", "detail": detail})
        except Exception as exc:  # fail closed and keep the complete diagnostic roster
            checks.append({"name": name, "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})

    r8_input = load_json(R8_INPUT)
    r7_manifest = load_json(R7_MANIFEST)
    r7_root = load_json(R7_ROOT)
    r7_handoff = load_json(R7_HANDOFF)
    r7_receipt = load_json(R7_RECEIPT)
    members = r7_manifest["members"]
    member_paths = [row["path"] for row in members]
    member_by_path = {row["path"]: row for row in members}

    corpus = load_json(BASE / "phase2_investigation/integration/literature_corpus_r1.json")
    source_registry = load_json(BASE / "phase2_investigation/integration/source_registry_r1.json")
    family_map = load_json(BASE / "phase2_investigation/integration/source_family_map_r1.json")
    quality = load_json(BASE / "phase2_investigation/integration/source_quality_matrix_r1.json")
    operational = load_json(BASE / "phase2_investigation/integration/operational_resource_registry.json")
    acquisition = load_json(BASE / "phase2_investigation/acquisition/source_acquisition_manifest.json")
    locators_doc = load_json(BASE / "phase2_investigation/acquisition/locator_registry.json")
    r4_claims_doc = load_json(BASE / "phase2_investigation/acquisition/r4_claim_acquisition_map.json")
    intent = load_json(BASE / "phase3_analysis/claim_intent_manifest_r1.json")
    original_claims_doc = load_json(BASE / "phase3_analysis/claim_source_map_r1.json")
    rem_claims_doc = load_json(BASE / "phase3_analysis/remediation_r6/claim_source_map_r1_remediated.json")
    counter = load_json(BASE / "phase3_analysis/remediation_r6/claim_counter_evidence_overlay.json")
    denominators = load_json(BASE / "phase3_analysis/remediation_r6/theme_evidence_denominators.json")
    original_tensions = load_json(BASE / "phase3_analysis/cross_paper_tensions_r1.json")
    reaudit_packet = load_json(BASE / "phase3_analysis/devils_advocate_cp2_reaudit/tension_adjudication_packet_reaudit.json")
    reaudit_findings = load_json(BASE / "phase3_analysis/devils_advocate_cp2_reaudit/r6_reaudit_findings.json")
    scholar = load_json(CONTROL / "scholar_tension_adjudication_r1.json")

    sources = source_registry["sources"]
    source_by_key = {row["source_key"]: row for row in sources}
    resources = operational["resources"]
    resource_by_key = {row["resource_key"]: row for row in resources}
    families = family_map["families"]
    family_by_id = {row["source_family_id"]: row for row in families}
    locators = locators_doc["locators"]
    locator_by_id = {row["locator_id"]: row for row in locators}
    rem_claims = rem_claims_doc["claims"]
    rem_by_id = {row["claim_id"]: row for row in rem_claims}
    original_claim_by_id = {row["claim_id"]: row for row in original_claims_doc["claims"]}
    intent_by_source_id = {row["source_claim_id"]: row for row in intent["claims"]}
    overlay_by_claim = {row["claim_id"]: row for row in counter["entries"]}

    check(CHECK_NAMES[0], lambda: (
        require(R8_CONTRACT.stat().st_size == 3357, "R8 contract byte count"),
        require(sha256(R8_CONTRACT) == EXPECTED_R8_CONTRACT_SHA256, "R8 contract SHA-256"),
        require(R8_INPUT.stat().st_size == 3695, "R8 manifest byte count"),
        require(sha256(R8_INPUT) == EXPECTED_R8_INPUT_SHA256, "R8 manifest SHA-256"),
        {"contract": EXPECTED_R8_CONTRACT_SHA256, "input_manifest": EXPECTED_R8_INPUT_SHA256},
    )[-1])

    check(CHECK_NAMES[1], lambda: (
        require(r8_input["runtime_lock"] == {"model": "gpt-5.6-sol", "reasoning": "high", "execution_mode": "fresh_dedicated_worktree_task"}, "runtime lock"),
        r8_input["runtime_lock"],
    )[-1])

    def direct_r7_bindings() -> dict[str, Any]:
        entries = [r8_input["audit_contract"], *r8_input["r7_control_bindings"], *r8_input["frozen_r7_outputs"]]
        for row in entries:
            path = Path(row["path"])
            require(path.stat().st_size == row["bytes"], f"byte count: {path}")
            require(sha256(path) == row["sha256"], f"SHA-256: {path}")
        return {"checked": len(entries), "failures": []}

    check(CHECK_NAMES[2], direct_r7_bindings)

    validator_results: dict[str, dict[str, Any]] = {}

    def replay_validator(label: str, command: list[str], expected: int, verdict: str | None = None) -> dict[str, Any]:
        result = run_json(command)
        validator_results[label] = result
        require(result.get("result", "PASS") == "PASS" or result.get("verdict") == verdict, f"{label} result")
        require(result["checks_run"] == expected and result["checks_passed"] == expected, f"{label} count")
        require(not result.get("failures"), f"{label} failures")
        if verdict is not None:
            require(result.get("verdict") == verdict, f"{label} verdict")
        return {"checks": f"{expected}/{expected}", "result": result.get("result", result.get("verdict"))}

    check(CHECK_NAMES[3], lambda: replay_validator(
        "r7", [sys.executable, str(R7 / "validate_r7_freeze.py"), "--mode", "final"], 29,
        "PASS_READY_FOR_INDEPENDENT_AUDIT",
    ))
    check(CHECK_NAMES[4], lambda: replay_validator(
        "r4", [sys.executable, str(BASE / "phase2_investigation/acquisition/validate_r4_acquisition.py")], 22,
    ))
    check(CHECK_NAMES[5], lambda: replay_validator(
        "r5", [sys.executable, str(BASE / "phase3_analysis/validate_r5_synthesis.py"), "--final"], 29,
    ))
    check(CHECK_NAMES[6], lambda: replay_validator(
        "r6_original", [sys.executable, str(BASE / "phase3_analysis/devils_advocate_cp2/validate_r6_checkpoint.py"), "--final"], 26,
    ))
    check(CHECK_NAMES[7], lambda: replay_validator(
        "r6_remediation", [sys.executable, str(BASE / "phase3_analysis/remediation_r6/validate_r6_remediation.py"), "--final"], 33,
    ))
    check(CHECK_NAMES[8], lambda: replay_validator(
        "r6_reaudit", [sys.executable, str(BASE / "phase3_analysis/devils_advocate_cp2_reaudit/validate_r6_reaudit.py")], 26,
    ))

    check(CHECK_NAMES[9], lambda: (require(len(members) == 193, "member count"), {"members": len(members)})[-1])

    def paths_check() -> dict[str, Any]:
        require(member_paths == sorted(member_paths), "paths not sorted")
        require(len(member_paths) == len(set(member_paths)), "duplicate paths")
        for value in member_paths:
            pure = PurePosixPath(value)
            require(value == pure.as_posix(), f"path not normalized: {value}")
            require(not pure.is_absolute() and ".." not in pure.parts and "\\" not in value, f"unsafe path: {value}")
        return {"sorted": True, "unique": True, "normalized": True}

    check(CHECK_NAMES[10], paths_check)
    check(CHECK_NAMES[11], lambda: (
        require(collections.Counter(row["role"] for row in members) == {"payload": 162, "control": 27, "receipt": 4}, "role counts"),
        dict(collections.Counter(row["role"] for row in members)),
    )[-1])

    replay_tuples: list[list[Any]] = []

    def member_replay() -> dict[str, Any]:
        mismatches = []
        for row in members:
            path = Path(row["path"])
            actual = [row["path"], path.stat().st_size, sha256(path), row["role"]]
            declared = [row["path"], row["bytes"], row["sha256"], row["role"]]
            replay_tuples.append(actual)
            if actual != declared:
                mismatches.append(row["path"])
        require(not mismatches, f"member mismatches: {mismatches}")
        return {"checked": len(replay_tuples), "mismatches": []}

    check(CHECK_NAMES[12], member_replay)
    preimage = json.dumps(replay_tuples, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    check(CHECK_NAMES[13], lambda: (
        require(all(isinstance(row, list) and len(row) == 4 for row in replay_tuples), "tuple shape"),
        require(all(isinstance(row[0], str) and isinstance(row[1], int) and isinstance(row[2], str) and isinstance(row[3], str) for row in replay_tuples), "tuple types"),
        {"tuple_fields": ["path", "bytes", "sha256", "role"]},
    )[-1])
    check(CHECK_NAMES[14], lambda: (require(len(preimage) == 43928, "preimage bytes"), {"bytes": len(preimage)})[-1])
    replay_root = hashlib.sha256(preimage).hexdigest()
    check(CHECK_NAMES[15], lambda: (require(replay_root == EXPECTED_ROOT, "root SHA-256"), {"root_sha256": replay_root})[-1])
    check(CHECK_NAMES[16], lambda: (
        require(r7_manifest["canonical_root_sha256"] == EXPECTED_ROOT, "manifest root"),
        require(r7_root["canonical_root_sha256"] == EXPECTED_ROOT, "root record"),
        require(r7_handoff["canonical_root_sha256"] == EXPECTED_ROOT, "handoff root"),
        require(r7_receipt["recomputed"]["canonical_root_sha256"] == EXPECTED_ROOT, "receipt root"),
        require(r7_handoff["verdict"] == "PASS_READY_FOR_INDEPENDENT_AUDIT", "handoff verdict"),
        {"root_sha256": EXPECTED_ROOT, "verdict": r7_handoff["verdict"]},
    )[-1])
    check(CHECK_NAMES[17], lambda: (
        require(b"C:\\Users\\" not in preimage and b"/home/" not in preimage, "absolute/worktree path in preimage"),
        require(b"inclusion_reason" not in preimage and b"generated_at" not in preimage and b"updated_at" not in preimage, "non-tuple metadata in preimage"),
        require(all(not row["path"].startswith(str(R7).replace("\\", "/")) for row in members), "R7 output self-hash in root"),
        {"timestamps": False, "absolute_paths": False, "mutable_state": False, "r7_self_hashes": False},
    )[-1])

    def packet_roster() -> dict[str, Any]:
        required = {
            str(CONTROL / "scholar_tension_adjudication_r1.json").replace("\\", "/"),
            str(BASE / "phase3_analysis/claim_source_map_r1.json").replace("\\", "/"),
            str(BASE / "phase3_analysis/synthesis_report_r1.md").replace("\\", "/"),
            str(BASE / "phase3_analysis/devils_advocate_cp2/r6_findings.json").replace("\\", "/"),
            str(BASE / "phase3_analysis/remediation_r6/claim_source_map_r1_remediated.json").replace("\\", "/"),
            str(BASE / "phase3_analysis/remediation_r6/synthesis_report_r1_remediated.md").replace("\\", "/"),
            str(BASE / "phase3_analysis/devils_advocate_cp2_reaudit/r6_reaudit_findings.json").replace("\\", "/"),
            str(BASE / "phase3_analysis/devils_advocate_cp2_reaudit/tension_adjudication_packet_reaudit.json").replace("\\", "/"),
        }
        missing = sorted(required - set(member_paths))
        require(not missing, f"missing current/superseded roster: {missing}")
        return {"required_history_rows": len(required), "missing": []}

    check(CHECK_NAMES[18], packet_roster)
    check(CHECK_NAMES[19], lambda: (
        require(all(row["role"] in {"payload", "control", "receipt"} for row in members), "invalid role"),
        require(all(isinstance(row.get("inclusion_reason"), str) and row["inclusion_reason"].strip() for row in members), "missing inclusion reason"),
        {"members": len(members), "role_labelled": len(members), "reason_labelled": len(members)},
    )[-1])

    def corpus_counts() -> dict[str, Any]:
        included = [row for row in sources if row["corpus_included"]]
        actual = {
            "canonical": len(sources),
            "included": len(included),
            "registry_only": len(sources) - len(included),
            "core": sum(row["core_shortlist"] for row in sources),
        }
        require(actual == {"canonical": 74, "included": 52, "registry_only": 22, "core": 23}, "registry counts")
        return actual

    check(CHECK_NAMES[20], corpus_counts)
    check(CHECK_NAMES[21], lambda: (
        require({row["citation_key"] for row in corpus["literature_corpus"]} == {row["source_key"] for row in sources if row["corpus_included"]}, "corpus included set"),
        require(len(corpus["literature_corpus"]) == 52, "corpus length"),
        {"corpus": 52, "exact_set": True},
    )[-1])
    check(CHECK_NAMES[22], lambda: (
        require(sum(2022 <= row["publication_year"] <= 2026 for row in sources if row["corpus_included"]) == 32, "recent source count"),
        {"recent_2022_2026": 32},
    )[-1])

    def quality_replay() -> dict[str, Any]:
        records = quality["records"]
        require({row["source_key"] for row in records} == set(source_by_key), "quality source set")
        q = quality["counts"]
        recomputed = {
            "records": len(records),
            "corpus": sum(row["corpus_included"] for row in records),
            "recent_2022_2026": sum(2022 <= source_by_key[row["source_key"]]["publication_year"] <= 2026 for row in records if row["corpus_included"]),
            "peer_reviewed_true": sum(row["peer_reviewed"] is True for row in records if row["corpus_included"]),
            "source_acquired": sum(row["source_acquired"] for row in records if row["corpus_included"]),
            "source_content_verified": sum(row["source_content_verified"] for row in records if row["corpus_included"]),
            "locator_ready": sum(row["locator_ready"] for row in records if row["corpus_included"]),
            "grades": dict(collections.Counter(row["quality_grade"] for row in records)),
        }
        require(recomputed == q, f"quality counts: {recomputed} != {q}")
        return recomputed

    check(CHECK_NAMES[23], quality_replay)

    def identity_dedup() -> dict[str, Any]:
        require(len(source_by_key) == 74, "duplicate source key")
        doi_map: dict[str, list[str]] = collections.defaultdict(list)
        title_year: dict[tuple[str, int], list[str]] = collections.defaultdict(list)
        for row in sources:
            for doi in row.get("all_normalized_dois", []):
                doi_map[doi].append(row["source_key"])
            title_year[(normalized_title(row["title"]), row["publication_year"])].append(row["source_key"])
        doi_dups = {key: value for key, value in doi_map.items() if len(set(value)) > 1}
        title_dups = {str(key): value for key, value in title_year.items() if len(value) > 1}
        require(not doi_dups and not title_dups, f"identity duplicates: DOI={doi_dups}, title/year={title_dups}")
        return {"source_keys": 74, "duplicate_doi_identities": 0, "duplicate_title_year_identities": 0}

    check(CHECK_NAMES[24], identity_dedup)
    check(CHECK_NAMES[25], lambda: (
        require(len(source_registry["alias_map"]) == 79, "alias count"),
        require(all(value in source_by_key for value in source_registry["alias_map"].values()), "dangling alias"),
        {"aliases": 79, "dangling": 0},
    )[-1])

    def family_membership() -> dict[str, Any]:
        require(len(family_by_id) == 75, "family count/duplicates")
        scholarly_members: dict[str, list[str]] = collections.defaultdict(list)
        operational_members: dict[str, list[str]] = collections.defaultdict(list)
        for family in families:
            for key in family["scholarly_source_keys"]:
                scholarly_members[key].append(family["source_family_id"])
            for key in family["operational_resource_keys"]:
                operational_members[key].append(family["source_family_id"])
        require(set(scholarly_members) == set(source_by_key), "family scholarly set")
        require(set(operational_members) == set(resource_by_key), "family operational set")
        require(all(value == [source_by_key[key]["source_family_id"]] for key, value in scholarly_members.items()), "scholarly family mismatch")
        require(all(value == [resource_by_key[key]["source_family_id"]] for key, value in operational_members.items()), "operational family mismatch")
        return {"families": 75, "scholarly_members": 74, "operational_members": 14}

    check(CHECK_NAMES[26], family_membership)

    def dependency_replay() -> dict[str, Any]:
        dependencies = family_map["dependencies"]
        require(len(dependencies) == 13, "dependency count")
        seen = set()
        for row in dependencies:
            require(row["source_family_id"] in family_by_id and row["depends_on_family_id"] in family_by_id, "dependency endpoint")
            require(all(key in source_by_key for key in row["source_keys"]), "dependency source key")
            require(all(key in resource_by_key for key in row["resource_keys"]), "dependency resource key")
            require(row["counting_effect"] == "not_an_additional_independent_source_family", "counting effect")
            sig = (row["dependency_type"], row["source_family_id"], row["depends_on_family_id"], tuple(row["source_keys"]), tuple(row["resource_keys"]))
            require(sig not in seen, "duplicate dependency edge")
            seen.add(sig)
        source_families = {row["source_family_id"] for row in sources}
        resource_families = {row["source_family_id"] for row in resources}
        require((len(source_families), len(resource_families), len(source_families | resource_families)) == (71, 12, 75), "family population arithmetic")
        return {"dependencies": 13, "scholarly_families": 71, "operational_root_families": 12, "union": 75}

    check(CHECK_NAMES[27], dependency_replay)
    check(CHECK_NAMES[28], lambda: (
        require(set(source_by_key).isdisjoint(resource_by_key), "source/resource key collision"),
        require(all("publication_year" not in row for row in resources), "operational publication year inferred"),
        require(all(all(key in row for key in ("availability", "code_license", "paper_license", "dataset_rights", "redistribution_status")) for row in resources), "rights layers missing"),
        require(all(row["citation_key"] not in resource_by_key for row in corpus["literature_corpus"]), "operational record in scholarly corpus"),
        {"scholarly_records": 74, "operational_records": 14, "separated": True},
    )[-1])

    def core_contract() -> dict[str, Any]:
        core_sources = [row for row in sources if row["core_shortlist"]]
        core_op_families = {row["source_family_id"] for row in resources if row["core_operational_family"]}
        require(len(core_sources) == 23 and len(core_op_families) == 1, "core 23+1")
        require(all(row["source_content_verified"] and row["locator_ready"] for row in core_sources), "R3 core scholarly readiness")
        require(core_op_families == {"SF-R1-075"}, "core operational family")
        core_acquisitions = [row for row in acquisition["acquisitions"] if row["core_object"]]
        require(len(core_acquisitions) == 24, "R4 core acquisition population")
        require(all(row["source_acquired"] and row["source_content_verified"] and row["locator_ready"] and row["r4_contract_satisfied"] for row in core_acquisitions), "R4 core acquisition readiness")
        require(acquisition["counts"]["core_total"] == 24 and acquisition["counts"]["core_acquired"] == 24, "acquisition core")
        return {"core_scholarly": 23, "core_operational_families": 1, "core_total": 24}

    check(CHECK_NAMES[29], core_contract)
    check(CHECK_NAMES[30], lambda: (
        require(acquisition["counts"]["queue_targets"] == 13 and acquisition["counts"]["queue_terminal_resolved"] == 13, "queue counts"),
        {"queue": "13/13"},
    )[-1])
    check(CHECK_NAMES[31], lambda: (
        require(len(locators) == 75 and len(locator_by_id) == 75, "locator count/duplicates"),
        require(sum(row["source_key"] is not None for row in locators) == 61, "source locator count"),
        require(sum(row["resource_key"] is not None for row in locators) == 14, "resource locator count"),
        {"locators": 75, "source": 61, "resource": 14},
    )[-1])

    def locator_joins() -> dict[str, Any]:
        for row in locators:
            require((row["source_key"] is None) != (row["resource_key"] is None), f"locator XOR target: {row['locator_id']}")
            target = source_by_key[row["source_key"]] if row["source_key"] is not None else resource_by_key[row["resource_key"]]
            require(target["source_family_id"] == row["source_family_id"], f"locator family: {row['locator_id']}")
            if row["local_artifact_path"] is not None:
                require(Path(row["local_artifact_path"]).is_file(), f"locator artifact: {row['locator_id']}")
            else:
                require(isinstance(row["artifact_uri"], str) and row["artifact_uri"], f"locator artifact URI: {row['locator_id']}")
        return {"checked": len(locators), "dangling": 0}

    check(CHECK_NAMES[32], locator_joins)
    check(CHECK_NAMES[33], lambda: (
        require(all(row["locator_type"] in {"quote", "section", "paragraph", "table", "figure", "abstract"} and row["locator_value"] for row in locators), "none/invalid locator"),
        require(all(row["page_anchor"] is False and row["locator_type"] != "page" for row in locators), "page anchor"),
        require(all(row["production_citation_authorized"] is False for row in locators), "premature production authorization"),
        {"none": 0, "page": 0, "production_authorized": 0},
    )[-1])

    def pdf_preflight() -> dict[str, Any]:
        rows = locators_doc["pdf_preflight_manifest"]
        verdicts = collections.Counter(row["verdict"] for row in rows)
        require(len(rows) == 28 and verdicts == {"PASS": 27, "UNAVAILABLE": 1}, f"preflight counts: {verdicts}")
        for row in rows:
            for path_key, bytes_key, hash_key in (("pdf_path", "pdf_bytes", "pdf_sha256"), ("sidecar_path", "sidecar_bytes", "sidecar_sha256")):
                path = Path(row[path_key])
                require(path.stat().st_size == row[bytes_key] and sha256(path) == row[hash_key], f"preflight binding: {path}")
        unavailable = [row["pdf_path"] for row in rows if row["verdict"] == "UNAVAILABLE"]
        require(unavailable == [str(BASE / "phase2_investigation/acquisition/source_artifacts/li2023_repetition_exploration.pdf").replace("\\", "/")], "unexpected unavailable preflight")
        return {"PASS": 27, "UNAVAILABLE": 1, "unavailable": unavailable}

    check(CHECK_NAMES[34], pdf_preflight)

    check(CHECK_NAMES[35], lambda: (
        require(len(rem_claims) == 44 and len(rem_by_id) == 44, "remediated claim population"),
        require(len(intent["claims"]) == 44 and len(intent_by_source_id) == 44, "intent population"),
        require(len(r4_claims_doc["claims"]) == 44, "R4 claim population"),
        {"claims": 44, "unique": 44},
    )[-1])

    def intent_join() -> dict[str, Any]:
        require(set(rem_by_id) == set(original_claim_by_id) == set(intent_by_source_id), "claim ID sets")
        for claim_id, rem in rem_by_id.items():
            original = original_claim_by_id[claim_id]
            stripped = dict(rem)
            stripped.pop("counter_evidence_binding")
            require(stripped == original, f"remediated claim drift: {claim_id}")
            row = intent_by_source_id[claim_id]
            require(row["claim_text"] == rem["claim_text_bounded"], f"claim text: {claim_id}")
            require(row["planned_refs"] == rem["canonical_source_keys"], f"refs: {claim_id}")
            require(row["planned_resources"] == rem["operational_resource_keys"], f"resources: {claim_id}")
            require(row["planned_source_family_ids"] == rem["source_family_ids"], f"families: {claim_id}")
            require(row["planned_locator_ids"] == rem["locator_ids"], f"locators: {claim_id}")
            require([x["rule"] for x in row["negative_constraints"]] == rem["forbidden_extrapolations"], f"constraints: {claim_id}")
        return {"joins": 44, "drift": 0}

    check(CHECK_NAMES[36], intent_join)
    check(CHECK_NAMES[37], lambda: (
        require(collections.Counter(row["r5_disposition"] for row in rem_claims) == {"citation_ready_candidate": 22, "planning_only": 22}, "dispositions"),
        {"citation_ready_candidate": 22, "planning_only": 22},
    )[-1])
    check(CHECK_NAMES[38], lambda: (
        require(all(row["frozen_r3_disposition"] == "planning_only" for row in rem_claims if row["r5_disposition"] == "planning_only"), "planning-only promotion"),
        require(all(row["stage2_production_citation_authorized"] is False and row["h1_h4_status"] == "NOT_RUN" for row in rem_claims), "claim boundary"),
        require(rem_claims_doc["phase_boundary"]["stage2_production_citations"] == "NOT_AUTHORIZED", "claim map Stage 2"),
        {"planning_only": 22, "stage2_authorized": 0, "h1_h4": "NOT_RUN"},
    )[-1])
    check(CHECK_NAMES[39], lambda: (
        require(len(counter["entries"]) == 44 and len(overlay_by_claim) == 44 and set(overlay_by_claim) == set(rem_by_id), "counter overlay population"),
        require(all(row["status"] == "bounded_counter_evidence" for row in counter["entries"]), "counter status"),
        {"claims": 44, "bounded_counter_evidence": 44, "none_identified": 0},
    )[-1])

    def counter_exact() -> dict[str, Any]:
        total = 0
        for row in counter["entries"]:
            upstream = row["upstream_basis"]
            path = Path(upstream["artifact_path"])
            require(sha256(path) == upstream["artifact_sha256"], f"upstream hash: {row['claim_id']}")
            doc = load_json(path)
            pointer_parts = upstream["claim_json_pointer"].strip("/").split("/")
            require(len(pointer_parts) == 2, f"claim pointer shape: {row['claim_id']}")
            index = int(pointer_parts[1])
            claim = doc[pointer_parts[0]][index]
            require(claim["claim_id"] == row["claim_id"], f"upstream claim pointer: {row['claim_id']}")
            expected = claim["counter_evidence"]
            actual = [item["text"] for item in row["counter_evidence_items"]]
            require(actual == expected, f"upstream counter evidence: {row['claim_id']}")
            total += len(actual)
        require(total == 51, f"counter evidence item count: {total}")
        return {"claims": 44, "counter_evidence_items": total, "mismatches": 0}

    check(CHECK_NAMES[40], counter_exact)

    pointer_counts: collections.Counter[str] = collections.Counter()

    def counter_locator_joins() -> dict[str, Any]:
        total = 0
        for row in counter["entries"]:
            claim = rem_by_id[row["claim_id"]]
            binding = claim["counter_evidence_binding"]
            require(binding["overlay_entry_id"] == row["overlay_entry_id"], f"overlay binding: {row['claim_id']}")
            require(binding["counter_evidence_item_count"] == len(row["counter_evidence_items"]), f"item binding: {row['claim_id']}")
            require(binding["source_locator_pointer_count"] == len(row["source_locator_pointers"]), f"pointer binding: {row['claim_id']}")
            for pointer in row["source_locator_pointers"]:
                locator = locator_by_id[pointer["locator_id"]]
                require(pointer["locator_id"] in claim["locator_ids"], f"claim locator edge: {row['claim_id']}")
                require(pointer["source_key"] == locator["source_key"] and pointer["resource_key"] == locator["resource_key"], "locator target")
                require(pointer["family_id"] == locator["source_family_id"], "locator family")
                require(pointer["locator_type"] == locator["locator_type"] and pointer["locator_value"] == locator["locator_value"], "locator value")
                require(pointer["verified_against_original"] == locator["verified_against_original"], "locator provenance")
                pointer_counts["verified" if pointer["verified_against_original"] else "bounded_not_original_verified"] += 1
                total += 1
        require(total == 136, f"counter locator pointers: {total}")
        return {"pointers": total, "dangling": 0}

    check(CHECK_NAMES[41], counter_locator_joins)
    check(CHECK_NAMES[42], lambda: (
        require(pointer_counts == {"verified": 114, "bounded_not_original_verified": 22}, f"pointer provenance: {pointer_counts}"),
        dict(pointer_counts),
    )[-1])

    original_report = (BASE / "phase3_analysis/synthesis_report_r1.md").read_text(encoding="utf-8")
    rem_report = (BASE / "phase3_analysis/remediation_r6/synthesis_report_r1_remediated.md").read_text(encoding="utf-8")
    original_pairs = marker_pairs(original_report)
    rem_pairs = marker_pairs(rem_report)
    check(CHECK_NAMES[43], lambda: (
        require(len(original_pairs) == 33 and len(rem_pairs) == 33, "citation pair count"),
        require(original_pairs == rem_pairs, "citation pairs changed"),
        {"original": 33, "remediated": 33, "unchanged": 33},
    )[-1])

    def citation_locator_resolution() -> dict[str, Any]:
        for ref, kind, value in rem_pairs:
            matches = [row for row in locators if (row["source_key"] == ref or row["resource_key"] == ref) and row["locator_type"] == kind and row["locator_value"] == value]
            require(len(matches) == 1, f"citation locator resolution: {ref}/{kind}/{value}")
            require(matches[0]["verified_against_original"] is True and matches[0]["page_anchor"] is False, f"citation locator verification: {ref}")
        return {"pairs": len(rem_pairs), "verified_nonpage": len(rem_pairs)}

    check(CHECK_NAMES[44], citation_locator_resolution)

    expected_theme_sources = {
        "T1": ["krichene2020_sampled_metrics", "li2023_reliable_sampling", "zhao2020_alternative_settings", "gusak2025_time_split", "dacrema2021_reproducibility", "jannach2026_methodological_standards"],
        "T2": ["sarwar2001_itemcf", "rendle2009_bpr", "he2017_ncf", "guo2017_deepfm", "covington2016_youtube", "yi2019_ndr", "wang2022_directau", "he2020_lightgcn"],
        "T3": ["agrawal1994_apriori", "cheng2016_wide_deep", "liu2009_hybrid_seq_cf", "kang2018_sasrec", "sun2019_bert4rec", "li2023_nbr_reality", "li2023_repetition_exploration", "mansouri2026_repeat_explore_lightgcn"],
        "T4": ["volkovs2017_dropoutnet", "huang2023_aldi", "reimers2019_sbert", "sheng2025_alpharec", "hou2022_unisrec", "hou2023_vqrec", "zheng2026_utgrec", "meehan2025_cold_popbias", "meehan2026_semco"],
        "T5": ["R-L5-COMPLETE-JOURNEY-PROVIDER", "R-L5-COMPLETEJOURNEY-R-PACKAGE"],
    }
    expected_theme_counts = {"T1": (6, 6, 6), "T2": (8, 8, 8), "T3": (8, 8, 8), "T4": (9, 9, 8), "T5": (2, 1, 1)}

    def theme_sets() -> dict[str, Any]:
        require(set(denominators["themes"]) == set(expected_theme_sources), "theme roster")
        for theme, expected in expected_theme_sources.items():
            actual = [row["record_key"] for row in denominators["themes"][theme]["records"]]
            require(actual == expected, f"theme source set: {theme}")
            for row in denominators["themes"][theme]["records"]:
                target = source_by_key.get(row["record_key"]) or resource_by_key.get(row["record_key"])
                require(target is not None and target["source_family_id"] == row["family_id"], f"theme family join: {theme}/{row['record_key']}")
        return {key: len(value) for key, value in expected_theme_sources.items()}

    check(CHECK_NAMES[45], theme_sets)

    def theme_arithmetic() -> dict[str, Any]:
        replay = {}
        for theme, (canonical, nominal, adjusted) in expected_theme_counts.items():
            row = denominators["themes"][theme]
            actual = (len(row["records"]), len(set(row["family_ids"])), row["counts"]["dependency_adjusted_family_count"])
            require(actual == (canonical, nominal, adjusted), f"theme arithmetic: {theme}/{actual}")
            require((row["counts"]["canonical_record_count"], row["counts"]["nominal_family_count"]) == (canonical, nominal), f"declared theme counts: {theme}")
            replay[theme] = {"canonical": canonical, "nominal": nominal, "dependency_adjusted": adjusted}
        return replay

    check(CHECK_NAMES[46], theme_arithmetic)

    def theme_edges() -> dict[str, Any]:
        expected_edge_counts = {"T1": 2, "T2": 0, "T3": 1, "T4": 1, "T5": 1}
        frozen = family_map["dependencies"]
        for theme, count in expected_edge_counts.items():
            edges = denominators["themes"][theme]["dependency_edges"]
            require(len(edges) == count, f"theme edge count: {theme}")
            for edge in edges:
                require(edge in frozen, f"theme edge not frozen: {theme}")
        t4 = denominators["themes"]["T4"]["dependency_edges"]
        require(t4[0]["source_family_id"] == "SF-R1-052" and t4[0]["depends_on_family_id"] == "SF-R1-017", "T4 adjustment")
        require(denominators["themes"]["T5"]["evidence_domain"] == "operational", "T5 domain")
        return expected_edge_counts

    check(CHECK_NAMES[47], theme_edges)

    def prose_denominators() -> dict[str, Any]:
        expected_phrases = {
            "T1": "six canonical scholarly records across six nominal and six dependency-adjusted source families",
            "T2": "eight canonical scholarly records from eight nominal and eight dependency-adjusted source families",
            "T3": "eight canonical scholarly records across eight nominal and eight dependency-adjusted source families",
            "T4": "nine canonical scholarly records across nine nominal source families and at most eight dependency-adjusted families",
            "T5": "exactly two canonical operational resource records within one nominal and one dependency-adjusted operational source family",
        }
        for theme, sources_expected in expected_theme_sources.items():
            pointer = f"theme_evidence_denominators.json#/themes/{theme}"
            require(pointer in rem_report, f"missing prose pointer: {theme}")
            source_text = ", ".join(sources_expected)
            require(source_text in rem_report, f"prose source list: {theme}")
            require(expected_phrases[theme] in rem_report, f"prose denominator phrase: {theme}")
        return {"theme_pointers": 5, "source_lists": 5, "mismatches": 0}

    check(CHECK_NAMES[48], prose_denominators)

    def strongest_removal() -> dict[str, Any]:
        tests = {
            "T1": ("source", "dacrema2021_reproducibility", "SF-R1-009", ["L1-CC-005", "L1-CC-006", "L1-CC-007"], []),
            "T2": ("source", "rendle2009_bpr", "SF-R1-047", ["L2-CLAIM-HARMONIZED-EVAL-008", "L2-CLAIM-ITEMCF-BPR-001", "L2-CLAIM-OBJECTIVE-006"], []),
            "T3": ("source", "mansouri2026_repeat_explore_lightgcn", "SF-R1-035", ["L3-GAP-008", "L3-HYB-006", "L3-NBR-004"], []),
            "T4": ("source", "sheng2025_alpharec", "SF-R1-052", ["L4-CC-03", "L4-CC-04", "L4-CC-06", "L4-CC-08"], []),
            "T5": ("family", "SF-R1-075", "SF-R1-075", ["C-L5-EXT-03", "C-L5-RIGHTS-01", "C-L5-SCOPE-01"], ["C-L5-EXT-03"]),
        }
        replay = {}
        for theme, (kind, key, family_id, expected_touched, expected_orphans) in tests.items():
            touched = []
            orphans = []
            for claim in rem_claims:
                hit = key in (claim["canonical_source_keys"] if kind == "source" else claim["source_family_ids"])
                if hit:
                    touched.append(claim["claim_id"])
                    if not (set(claim["source_family_ids"]) - {family_id}):
                        orphans.append(claim["claim_id"])
            require(touched == expected_touched and orphans == expected_orphans, f"strongest removal: {theme}")
            replay[theme] = {"touched": touched, "orphaned": orphans}
        return replay

    check(CHECK_NAMES[49], strongest_removal)

    def hostile_boundaries() -> dict[str, Any]:
        report = (BASE / "phase3_analysis/devils_advocate_cp2_reaudit/r6_reaudit_report.md").read_text(encoding="utf-8")
        required = [
            "cold-item is not cold-user",
            "Wide & Deep is not Apriori efficacy",
            "architecture transfer is not H4",
            "literature rationale is not an empirical v5 result",
            "official reproduction is not a harmonized benchmark",
            "Strongest hostile-reviewer counterargument",
            "Minimum defensible concession",
        ]
        require(all(text in report for text in required), "hostile-reviewer boundary text")
        hostile = reaudit_findings["strongest_hostile_reviewer_counterargument"]
        require(all(term in hostile for term in ("not establish empirical robustness", "novelty", "external validity", "superiority")), "hostile boundary scope")
        require("## Introduction" not in rem_report and "## Related Work" not in rem_report, "manuscript heading")
        return {"fixed_boundaries": 7, "hostile_argument": True, "minimum_concession": True, "manuscript_prose": False}

    check(CHECK_NAMES[50], hostile_boundaries)

    original_pairs_by_id = {row["pair_id"]: row for row in original_tensions["cross_paper_tensions"]}
    packet_pairs_by_id = {row["pair_id"]: row for row in reaudit_packet["pairs"]}
    decisions_by_id = {row["pair_id"]: row for row in scholar["decisions"]}
    check(CHECK_NAMES[51], lambda: (
        require(len(original_pairs_by_id) == 12 and len(packet_pairs_by_id) == 12, "tension roster"),
        require(set(original_pairs_by_id) == set(packet_pairs_by_id) == {f"T-{index:03d}" for index in range(1, 13)}, "tension IDs"),
        require(all(packet_pairs_by_id[key]["r5_pair_assessment"] == original_pairs_by_id[key]["pair_assessment"] and packet_pairs_by_id[key]["r5_resolution_status"] == original_pairs_by_id[key]["resolution_status"] for key in original_pairs_by_id), "original tension drift"),
        {"pairs": 12, "historical_drift": 0},
    )[-1])
    check(CHECK_NAMES[52], lambda: (
        require(len(decisions_by_id) == 12 and set(decisions_by_id) == set(original_pairs_by_id), "decision roster"),
        require(collections.Counter(row["scholar_confirmation"] for row in scholar["decisions"]) == {"confirmed": 11, "disputed": 1}, "decision counts"),
        require(scholar["counts"] == {"pairs": 12, "confirmed": 11, "disputed": 1, "pending": 0, "reclassified": 1, "flagged_unresolved": 0}, "scholar counts"),
        {"pairs": 12, "confirmed": 11, "disputed": 1, "pending": 0},
    )[-1])

    def t002_check() -> dict[str, Any]:
        original = original_pairs_by_id["T-002"]
        decision = decisions_by_id["T-002"]
        require(original["pair_assessment"] == "conditional_difference" and original["resolution_status"] == "resolved_in_synthesis" and original["scholar_confirmation"] == "pending", "historical T-002")
        require(decision["scholar_confirmation"] == "disputed", "T-002 decision")
        require(decision["original_pair_assessment"] == original["pair_assessment"] and decision["original_resolution_status"] == original["resolution_status"], "T-002 original binding")
        require(decision["effective_pair_assessment"] == "no_material_conflict" and decision["effective_resolution_status"] == "not_applicable", "T-002 effective classification")
        require(decision["adjudication_outcome"] == "reclassified" and decision["flagged_unresolved"] is False, "T-002 resolution")
        return {"historical": "conditional_difference/resolved_in_synthesis/pending", "effective": "no_material_conflict/not_applicable/disputed", "unresolved": False}

    check(CHECK_NAMES[53], t002_check)
    check(CHECK_NAMES[54], lambda: (
        require(scholar["counts"]["pending"] == 0 and scholar["counts"]["flagged_unresolved"] == 0, "pending/unresolved"),
        require(all(row["scholar_confirmation"] != "pending" for row in scholar["decisions"]), "pending decision row"),
        {"pending": 0, "unresolved": 0},
    )[-1])

    def boundary_check() -> dict[str, Any]:
        handoff_boundary = r7_handoff["phase_boundary"]
        require(handoff_boundary["stage1b_sealed"] is False, "Stage 1B sealed")
        require(handoff_boundary["stage2_production_citations_authorized"] is False, "Stage 2 authorized")
        require(handoff_boundary["h1_h4"] == "NOT_RUN", "H1-H4")
        require(handoff_boundary["benchmark_training_evaluation"] == "NOT_RUN", "benchmark")
        manifest_boundary = r7_manifest["phase_boundary"]
        require(manifest_boundary["stage1b_seal"] == "NOT_PERFORMED", "manifest Stage 1B seal")
        require(manifest_boundary["stage2_authorization"] == "NOT_AUTHORIZED", "manifest Stage 2 authorization")
        require(manifest_boundary["h1_h4"] == "NOT_RUN", "manifest H1-H4")
        require(manifest_boundary["benchmark_training_evaluation"] == "NOT_RUN", "manifest benchmark")
        require(r8_input["r7_gate"]["stage1b_sealed"] is False and r8_input["r7_gate"]["stage2_production_citations_authorized"] is False, "R8 input boundary")
        return {"stage1b_sealed": False, "stage2_authorized": False, "benchmark": "NOT_RUN", "h1_h4": "NOT_RUN"}

    check(CHECK_NAMES[55], boundary_check)

    findings = load_json(OUT / "r8_findings.json")
    packet_replay = load_json(OUT / "r8_packet_replay.json")
    handoff = load_json(OUT / "r8_handoff.json")
    receipt = load_json(OUT / "r8_validation_receipt.json")
    report_text = (OUT / "r8_independent_audit_report.md").read_text(encoding="utf-8")

    check(CHECK_NAMES[56], lambda: (
        require(findings["verdict"] == "PASS_READY_TO_SEAL", "findings verdict"),
        require(findings["severity_counts"] == {"Critical": 0, "Major": 0, "Minor": 0, "Observation": 5}, "severity counts"),
        require(len(findings["findings"]) == 5 and all(row["severity"] == "Observation" for row in findings["findings"]), "finding rows"),
        require(len({row["finding_id"] for row in findings["findings"]}) == 5, "finding IDs"),
        {"verdict": findings["verdict"], "severity_counts": findings["severity_counts"]},
    )[-1])
    check(CHECK_NAMES[57], lambda: (
        require(packet_replay["packet_member_count"] == 193 and packet_replay["member_mismatches"] == [], "packet replay members"),
        require(packet_replay["canonical_preimage_bytes"] == 43928 and packet_replay["canonical_root_sha256"] == EXPECTED_ROOT, "packet replay root"),
        require(packet_replay["upstream_validators"] == {"R4": "PASS_22_OF_22", "R5": "PASS_29_OF_29", "R6_original": "PASS_26_OF_26", "R6_remediation": "PASS_33_OF_33", "R6_reaudit": "PASS_26_OF_26", "R7": "PASS_29_OF_29"}, "packet replay validator counts"),
        require(packet_replay["replayed_counts"] == {"claims": 44, "citation_ready_candidates": 22, "planning_only": 22, "counter_evidence_items": 51, "counter_evidence_locator_pointers": 136, "verified_citation_locator_pairs": 33, "themes": 5, "tension_pairs": 12, "scholar_confirmed": 11, "scholar_disputed_reclassified": 1, "scholar_pending": 0, "scholar_unresolved": 0}, "packet replay counts"),
        {"members": 193, "preimage_bytes": 43928, "root_sha256": EXPECTED_ROOT},
    )[-1])
    check(CHECK_NAMES[58], lambda: (
        require("Verdict: `PASS_READY_TO_SEAL`" in report_text, "report verdict"),
        require(EXPECTED_ROOT in report_text and "29/29" in report_text and "60/60" in report_text, "report replay/validator summary"),
        require(handoff["verdict"] == "PASS_READY_TO_SEAL", "handoff verdict"),
        require(handoff["severity_counts"] == findings["severity_counts"], "handoff severity"),
        require(handoff["canonical_root_sha256"] == EXPECTED_ROOT and handoff["final_validation"] == "PASS_60_OF_60", "handoff validation/root"),
        require(handoff["phase_boundary"] == {"r9": "NOT_PERFORMED_NOT_AUTHORIZED_UNTIL_CENTRAL_VALIDATION", "stage1b_seal": "NOT_PERFORMED", "stage1b_sealed": False, "stage2_authorization": "NOT_AUTHORIZED", "stage2_production_citations_authorized": False, "manuscript_drafting": "NOT_PERFORMED", "benchmark_training_evaluation": "NOT_RUN", "h1_h4": "NOT_RUN"}, "handoff boundary"),
        {"report": "complete", "handoff": handoff["verdict"], "final_validation": handoff["final_validation"]},
    )[-1])

    def output_roster_hashes() -> dict[str, Any]:
        present = {path.name for path in OUT.iterdir() if path.is_file()}
        require(present == EXPECTED_OUTPUTS, f"output roster: {sorted(present)}")
        require(receipt["checks_run"] == 60 and receipt["checks_passed"] == 60 and receipt["checks_failed"] == 0, "receipt counts")
        require(receipt["check_names"] == CHECK_NAMES, "receipt check roster")
        require(receipt["result"] == "PASS" and receipt["verdict"] == "PASS_READY_TO_SEAL", "receipt result")
        check_hash_map(handoff["artifact_sha256"])
        check_hash_map(receipt["artifact_sha256"])
        require(receipt["artifact_sha256"][str(OUT / "r8_handoff.json").replace("\\", "/")] == sha256(OUT / "r8_handoff.json"), "receipt handoff binding")
        require(str(OUT / "r8_validation_receipt.json").replace("\\", "/") not in receipt["artifact_sha256"], "receipt self-hash")
        require(str(OUT / "r8_handoff.json").replace("\\", "/") not in handoff["artifact_sha256"], "handoff self-hash")
        return {"outputs": 6, "missing": [], "extra": [], "receipt_nonself_hashes": len(receipt["artifact_sha256"]), "handoff_nonself_hashes": len(handoff["artifact_sha256"])}

    check(CHECK_NAMES[59], output_roster_hashes)

    require([row["name"] for row in checks] == CHECK_NAMES, "internal check ordering")
    failures = [row for row in checks if row["status"] == "FAIL"]
    result = {
        "schema_version": "stage1b-r1-r8-final-validation-1.0",
        "validation_mode": "final",
        "result": "PASS" if not failures else "FAIL",
        "verdict": "PASS_READY_TO_SEAL" if not failures else "REVISE",
        "checks_run": len(checks),
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "check_names": CHECK_NAMES,
        "failures": failures,
        "recomputed": {
            "r7_validator": "PASS_29_OF_29" if not failures else "SEE_FAILURES",
            "packet_member_count": len(members),
            "canonical_preimage_bytes": len(preimage),
            "canonical_root_sha256": replay_root,
            "claims": len(rem_claims),
            "citation_ready_candidates": sum(row["r5_disposition"] == "citation_ready_candidate" for row in rem_claims),
            "planning_only": sum(row["r5_disposition"] == "planning_only" for row in rem_claims),
            "counter_evidence_items": sum(len(row["counter_evidence_items"]) for row in counter["entries"]),
            "counter_evidence_locator_pointers": sum(len(row["source_locator_pointers"]) for row in counter["entries"]),
            "citation_locator_pairs": len(rem_pairs),
            "themes": len(denominators["themes"]),
            "scholar_pairs": len(scholar["decisions"]),
            "scholar_pending": scholar["counts"]["pending"],
            "scholar_unresolved": scholar["counts"]["flagged_unresolved"],
            "severity_counts": findings["severity_counts"],
        },
        "authority": "PASS validates only the frozen R7 packet and the read-only R8 audit bundle. It does not perform R9, seal Stage 1B, authorize Stage 2, draft manuscript prose, run benchmarks, or change H1-H4.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
