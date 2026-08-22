from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
CONTROL = Path(__file__).resolve().parent
OUTPUT_ROOT = (
    REPO_ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_af"
    / "E4_R5G1_source_evidence_selection"
)
EXPECTED_OUTPUTS = {
    "source_audit_merge.json",
    "candidate_gap_comparison.json",
    "selection_decision.json",
    "r5_g1_report.md",
    "r5_g1_handoff.json",
}
EXPECTED_CANDIDATES = {
    "R5-CAND-RECBOLE-BPR-ML100K-001",
    "R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001",
}
SELECTED_CANDIDATE = "R5-CAND-RECBOLE-BPR-ML100K-001"
EXPECTED_TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
EXPECTED_MANIFEST_BYTES = 6814
EXPECTED_MANIFEST_SHA256 = (
    "8ef3d2ef000051fdb69edea75297e1a6a5d5434d6abce5e7693ae506f0f38400"
)


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def canonical_lf_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def canonical_lf_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_lf_bytes(path)).hexdigest()


failures: list[str] = []
checks = 0


def check(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(message)


def check_truth(document: dict[str, Any], label: str) -> None:
    check(document.get("truth_state") == EXPECTED_TRUTH, f"{label}: truth_state mismatch")


def main() -> int:
    check(OUTPUT_ROOT.is_dir(), "R5-G1 output root is missing")
    if not OUTPUT_ROOT.is_dir():
        return finish()

    actual_outputs = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    check(actual_outputs == EXPECTED_OUTPUTS, f"exact output set mismatch: {sorted(actual_outputs)}")
    check(
        not any(path.is_dir() for path in OUTPUT_ROOT.iterdir()),
        "output root contains an unexpected directory",
    )

    json_names = sorted(name for name in EXPECTED_OUTPUTS if name.endswith(".json"))
    documents: dict[str, dict[str, Any]] = {}
    for name in json_names:
        path = OUTPUT_ROOT / name
        try:
            documents[name] = load_json(path)
            check(True, f"{name}: strict JSON parse")
        except Exception as exc:  # noqa: BLE001 - validator must collect all failures
            check(False, f"{name}: strict JSON parse failed: {exc}")

    if len(documents) != 4:
        return finish()

    contract = load_json(CONTROL / "e4_r5_g1_central_synthesis_contract.json")
    manifest_path = CONTROL / "e4_r5_g1_frozen_input_manifest.json"
    manifest = load_json(manifest_path)
    gate = load_json(CONTROL / "rebaseline_v2_e4_r5_g1_frozen_input_gate_receipt.json")
    policy_path = CONTROL / "e4_r5_future_subagent_model_policy.json"
    policy = load_json(policy_path)

    manifest_bytes = canonical_lf_bytes(manifest_path)
    check(len(manifest_bytes) == EXPECTED_MANIFEST_BYTES, "frozen manifest canonical byte count changed")
    check(
        hashlib.sha256(manifest_bytes).hexdigest() == EXPECTED_MANIFEST_SHA256,
        "frozen manifest canonical SHA-256 changed",
    )
    check(manifest.get("input_count") == 23, "frozen manifest input_count must be 23")
    check(manifest.get("json_input_count") == 18, "frozen manifest json_input_count must be 18")
    check(gate.get("passed") is True and gate.get("failure_count") == 0, "frozen-input gate is not PASS")
    check(
        gate.get("verdict") == "PASS_R5_G1_FROZEN_23_OF_23_READY_FOR_CENTRAL_SYNTHESIS",
        "unexpected frozen-input gate verdict",
    )

    matched_inputs = 0
    parsed_json_inputs = 0
    for entry in manifest["inputs"]:
        path = REPO_ROOT / entry["path"]
        check(path.is_file(), f"frozen input missing: {entry['path']}")
        if not path.is_file():
            continue
        data = canonical_lf_bytes(path)
        check(len(data) == entry["canonical_lf_bytes"], f"byte mismatch: {entry['path']}")
        check(
            hashlib.sha256(data).hexdigest() == entry["canonical_lf_sha256"],
            f"SHA-256 mismatch: {entry['path']}",
        )
        matched_inputs += 1
        if path.suffix == ".json":
            try:
                load_json(path)
                parsed_json_inputs += 1
                check(True, f"strict JSON frozen input: {entry['path']}")
            except Exception as exc:  # noqa: BLE001
                check(False, f"strict JSON frozen input failed: {entry['path']}: {exc}")
    check(matched_inputs == 23, "not all 23 frozen inputs were present")
    check(parsed_json_inputs == 18, "not all 18 JSON frozen inputs parsed strictly")

    check(
        set(contract["output_contract"]["exact_filenames"]) == EXPECTED_OUTPUTS,
        "validator output set differs from preregistered contract",
    )
    check(contract["selection_cardinality_max"] == 1, "contract selection maximum changed")
    check(contract["selection_is_benchmark_admission"] is False, "contract admission boundary changed")

    merge = documents["source_audit_merge.json"]
    comparison = documents["candidate_gap_comparison.json"]
    decision = documents["selection_decision.json"]
    handoff = documents["r5_g1_handoff.json"]

    merge_candidates = {row["candidate_id"] for row in merge["candidates"]}
    check(merge_candidates == EXPECTED_CANDIDATES, "source merge candidate set mismatch")
    check(sum(row["source_fact_count"] for row in merge["candidates"]) == 75, "source fact total mismatch")
    check(sum(row["dispositive_conflicts"] for row in merge["candidates"]) == 0, "dispositive conflict count must be zero")
    check(merge["lane_validation"]["positive_hash_bound_source_facts"] == 56, "positive hash-bound fact count mismatch")
    check(merge["lane_validation"]["hash_binding_failures"] == 0, "hash-binding failures must be zero")
    check(merge["merge_invariants"]["cross_candidate_fact_borrowing_detected"] is False, "cross-candidate fact borrowing detected")
    check(merge["merge_invariants"]["numeric_target_magnitude_used_for_selection"] is False, "numeric target magnitude was used")
    check(merge["merge_invariants"]["benchmark_admitted_candidates"] == 0, "source merge admitted a benchmark")
    check(
        merge["frozen_input_binding"]["canonical_lf_sha256"] == EXPECTED_MANIFEST_SHA256,
        "source merge frozen-manifest binding mismatch",
    )

    comparison_candidates = {row["candidate_id"]: row for row in comparison["candidates"]}
    check(set(comparison_candidates) == EXPECTED_CANDIDATES, "comparison candidate set mismatch")
    expected_check_ids = {f"G0{index}_" for index in range(1, 9)}
    for candidate_id, row in comparison_candidates.items():
        ids = [item["check_id"] for item in row["checks"]]
        check(len(ids) == 8 and len(set(ids)) == 8, f"{candidate_id}: G01-G08 coverage mismatch")
        check(
            all(any(check_id.startswith(prefix) for check_id in ids) for prefix in expected_check_ids),
            f"{candidate_id}: one or more mandatory central checks missing",
        )
    check(
        comparison_candidates[SELECTED_CANDIDATE]["central_status"]
        == "PROVISIONALLY_ELIGIBLE_FOR_R5_M2_PROPOSAL",
        "selected candidate comparison status mismatch",
    )
    check(
        comparison_candidates["R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001"]["central_status"]
        == "NOT_SELECTED_SOURCE_GAPS_LARGER",
        "LightGCN comparison status mismatch",
    )
    check(comparison["comparison_policy"]["numeric_target_magnitude_used"] is False, "comparison used a numeric target")

    check(
        decision["decision"] == "PROVISIONAL_SINGLE_CANDIDATE_FOR_DATA_ENVIRONMENT_PROPOSAL",
        "selection decision is outside the expected positive decision",
    )
    check(decision["decision"] in contract["allowed_decisions"], "selection decision is not allowed by contract")
    check(decision["selected_count"] == 1, "selected_count must equal one")
    check(decision["selected_count"] <= contract["selection_cardinality_max"], "selection cardinality exceeded")
    check(decision["selected_candidate"]["candidate_id"] == SELECTED_CANDIDATE, "wrong candidate selected")
    check(
        decision["selected_candidate"]["central_status"] == "PROVISIONALLY_ELIGIBLE_FOR_R5_M2_PROPOSAL",
        "selected candidate status mismatch",
    )
    check(
        decision["r5_m2_checkpoint"]["status"] == "OPEN_AWAITING_EXPLICIT_USER_SCOPE_APPROVAL",
        "R5-M2 must await explicit user scope approval",
    )
    check(
        not any(decision["selection_boundaries"].values()),
        "one or more prohibited selection authorizations became true",
    )
    check("documented NDCG@10 magnitude" in decision["selection_basis"]["not_used"], "numeric exclusion missing")

    check(handoff["decision"] == decision["decision"], "handoff decision mismatch")
    check(handoff["selected_candidate_id"] == SELECTED_CANDIDATE, "handoff selected candidate mismatch")
    check(handoff["selection_count"] == 1, "handoff selection count mismatch")
    check(handoff["benchmark_admitted_candidates"] == 0, "handoff admitted benchmark candidate")
    check(handoff["verified_reproducibility_claims"] == 0, "handoff claims verified reproducibility")
    check(handoff["accepted_numeric_targets"] == 0, "handoff accepted a numeric target")
    check(
        handoff["next_gate"]["status"] == "OPEN_AWAITING_EXPLICIT_USER_SCOPE_APPROVAL",
        "handoff R5-M2 status mismatch",
    )
    check(set(handoff["output_contract"]["files"]) == EXPECTED_OUTPUTS, "handoff output set mismatch")

    expected_central_model = {
        "display_name": "Sol Max Standard",
        "runtime_model_id": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "service_tier": "standard",
    }
    check(merge["model_profile"] == expected_central_model, "merge central model profile mismatch")
    check(decision["model_profile"] == expected_central_model, "decision central model profile mismatch")
    check(handoff["model_profile"] == expected_central_model, "handoff central model profile mismatch")

    check(policy["effective_scope"] == "SUBAGENT_DISPATCHES_CREATED_AFTER_THIS_CHANGE_CONTROL_RECORD", "policy scope mismatch")
    check(policy["historical_artifact_policy"]["retroactive_rewrite_allowed"] is False, "policy rewrites history")
    check(policy["historical_artifact_policy"]["rerun_completed_valid_stages_required"] is False, "policy requires invalid rerun")
    check(
        policy["future_subagent_profiles"]["critical_judgment"]
        == {
            **policy["future_subagent_profiles"]["critical_judgment"],
            "display_name": "Sol XHigh Fast",
            "runtime_model_id": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "service_tier": "priority",
        },
        "critical subagent profile mismatch",
    )
    check(
        policy["future_subagent_profiles"]["bounded_execution"]
        == {
            **policy["future_subagent_profiles"]["bounded_execution"],
            "display_name": "Sol High Fast",
            "runtime_model_id": "gpt-5.6-sol",
            "reasoning_effort": "high",
            "service_tier": "priority",
        },
        "bounded subagent profile mismatch",
    )
    check(policy["central_profile"] == {**policy["central_profile"], **expected_central_model}, "central policy profile mismatch")
    check(policy["r5_g1_disposition"]["profile"] == "Sol Max Standard", "R5-G1 policy disposition mismatch")
    check(
        all(entry["path"] != str(policy_path.relative_to(REPO_ROOT)).replace("\\", "/") for entry in manifest["inputs"]),
        "post-freeze operational policy was incorrectly added to scientific frozen inputs",
    )

    report = (OUTPUT_ROOT / "r5_g1_report.md").read_text(encoding="utf-8")
    required_report_markers = [
        "PROVISIONAL_SINGLE_CANDIDATE_FOR_DATA_ENVIRONMENT_PROPOSAL",
        SELECTED_CANDIDATE,
        "not benchmark admission",
        "OPEN_AWAITING_EXPLICIT_USER_SCOPE_APPROVAL",
        "RESULT_STATUS=NOT_RUN",
        "TEST_SET_OPENED=NO",
        "Sol XHigh Fast",
        "Sol High Fast",
    ]
    for marker in required_report_markers:
        check(marker in report, f"report marker missing: {marker}")

    for label, document in documents.items():
        check_truth(document, label)

    return finish()


def finish() -> int:
    verdict = (
        "PASS_R5_G1_PROVISIONAL_BPR_SELECTION_R5_M2_USER_CHECKPOINT_REQUIRED"
        if not failures
        else "FAIL_R5_G1_VALIDATION"
    )
    print(
        json.dumps(
            {
                "passed": not failures,
                "verdict": verdict,
                "mechanical_checks_passed": checks - len(failures),
                "mechanical_checks_expected": checks,
                "failure_count": len(failures),
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
