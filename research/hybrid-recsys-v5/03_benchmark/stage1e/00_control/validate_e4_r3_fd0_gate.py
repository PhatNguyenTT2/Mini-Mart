from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r3_fd0_frozen_input_manifest.json"
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
CENTRAL_MODEL = {
    "display_name": "Sol Max Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "max",
    "service_tier": "standard",
}
WORKER_MODEL = {
    "display_name": "Sol XHigh Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "xhigh",
    "service_tier": "standard",
}


class ContractError(ValueError):
    pass


def reject_duplicate_or_case_colliding_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    lowered: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        folded = key.casefold()
        if folded in lowered and lowered[folded] != key:
            raise ContractError(f"case-colliding JSON keys: {lowered[folded]} / {key}")
        lowered[folded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_or_case_colliding_keys,
    )
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def check(checks: dict[str, bool], failures: list[str], name: str, condition: bool) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    try:
        manifest = load_json(MANIFEST)
    except Exception as exc:
        print(json.dumps({"passed": False, "failures": [f"manifest_parse:{exc}"]}, indent=2))
        return 1

    inputs = manifest.get("inputs")
    check(checks, failures, "manifest_inputs_is_list", isinstance(inputs, list))
    if not isinstance(inputs, list):
        inputs = []
    paths = [row.get("path") for row in inputs if isinstance(row, dict)]
    check(checks, failures, "manifest_input_count_17", manifest.get("input_count") == 17 == len(inputs))
    check(checks, failures, "manifest_rows_are_objects", len(paths) == len(inputs))
    check(checks, failures, "manifest_paths_unique", len(paths) == len(set(paths)))

    matched = 0
    json_verified = 0
    for index, row in enumerate(inputs):
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            failures.append(f"input_{index}_invalid")
            continue
        relative = row["path"]
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        try:
            payload = canonical_lf(path)
            digest = hashlib.sha256(payload).hexdigest()
        except Exception as exc:
            failures.append(f"read_or_utf8:{relative}:{exc}")
            continue
        if len(payload) != row.get("canonical_lf_bytes"):
            failures.append(f"byte_mismatch:{relative}")
            continue
        if digest != row.get("canonical_lf_sha256"):
            failures.append(f"hash_mismatch:{relative}")
            continue
        if path.suffix.lower() == ".json":
            try:
                load_json(path)
                json_verified += 1
            except Exception as exc:
                failures.append(f"strict_json:{relative}:{exc}")
                continue
        matched += 1

    check(checks, failures, "frozen_inputs_17_of_17", matched == 17)
    check(checks, failures, "strict_json_inputs_9_of_9", json_verified == 9)
    check(checks, failures, "manifest_model_policy", manifest.get("model_policy") == {
        "central": CENTRAL_MODEL,
        "workers": WORKER_MODEL,
    })
    check(checks, failures, "manifest_truth_state", manifest.get("truth_state") == TRUTH)

    stage_map = load_json(CONTROL / "e4_r3_stage_map.json")
    check(checks, failures, "user_scope_decision_frozen", stage_map.get("entry_checkpoint", {}).get("decision") == "CREATE_NEW_FRAMEWORK_DATASET_ROW")
    check(checks, failures, "seed_and_selection_cardinality", stage_map.get("candidate_policy", {}).get("seed_min") == 3 and stage_map.get("candidate_policy", {}).get("seed_max") == 5 and stage_map.get("candidate_policy", {}).get("selection_cardinality_max") == 1)
    map_models = stage_map.get("model_policy", {})
    check(checks, failures, "central_sol_max_standard", all(map_models.get("central", {}).get(k) == v for k, v in CENTRAL_MODEL.items()))
    check(checks, failures, "workers_sol_xhigh_standard", all(map_models.get("workers", {}).get(k) == v for k, v in WORKER_MODEL.items()))
    phases = {row.get("id"): row for row in stage_map.get("phases", []) if isinstance(row, dict)}
    check(checks, failures, "all_stage_ids_present", set(phases) == {"R3-FD0", "R3-FD1", "R3-FD2", "R3-FD3", "R3-FD4", "R3-G1", "R3-M0"})
    check(checks, failures, "fd2_fd4_share_parallel_group", {phases[s].get("parallel_group") for s in ("R3-FD2", "R3-FD3", "R3-FD4")} == {"R3-FD-V"})
    check(checks, failures, "execution_boundary_fail_closed", stage_map.get("execution_boundary") == {
        "public_primary_source_web_research": True,
        "read_only_local_inspection": True,
        "repository_clone_fetch_or_archive_download": False,
        "dataset_checkpoint_or_asset_download": False,
        "authenticated_access_or_terms_acceptance": False,
        "package_install_or_environment_creation": False,
        "preprocessing_training_evaluation": False,
        "test_access": False,
        "maintainer_contact": False,
        "execution_authorized": False,
    })

    bundle_contract = load_json(CONTROL / "e4_r3_candidate_bundle_contract.json")
    check(checks, failures, "candidate_id_pattern_valid", re.compile(bundle_contract.get("candidate_id_pattern", "")).pattern.startswith("^R3-BUNDLE-"))
    check(checks, failures, "bundle_cross_join_forbidden", bundle_contract.get("cross_join_allowed") is False)
    check(checks, failures, "bundle_truth_state", bundle_contract.get("truth_state") == TRUTH)

    matrix = load_json(ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_h/E4_R2G1_candidate_selection/candidate_decision_matrix.json")
    old_ids = {row.get("row_id") for row in matrix.get("rows", []) if isinstance(row, dict)}
    registry = load_json(CONTROL / "e4_r3_supersession_registry.json")
    archived_ids = {row.get("row_id") for row in registry.get("rows", []) if isinstance(row, dict)}
    check(checks, failures, "supersession_exact_old_id_set", len(old_ids) == 7 and archived_ids == old_ids)
    check(checks, failures, "all_old_rows_non_executable", all(row.get("new_status") == "ARCHIVED_SUPERSEDED_NOT_EXECUTION_ELIGIBLE" for row in registry.get("rows", []) if isinstance(row, dict)))
    check(checks, failures, "no_deletion_claim", registry.get("policy", {}).get("artifact_deletion_performed") is False and registry.get("policy", {}).get("model_asset_deletion_required") is False)

    prior = load_json(ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_o/E4_R2ER1G1_candidate_selection/selection_decision.json")
    options = {row.get("id") for row in prior.get("next_user_decision_options", []) if isinstance(row, dict)}
    check(checks, failures, "prior_no_selection", prior.get("decision", {}).get("verdict") == "NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT" and prior.get("decision", {}).get("selected_candidate_count") == 0)
    check(checks, failures, "chosen_option_was_offered", "CREATE_NEW_FRAMEWORK_DATASET_ROW" in options)
    check(checks, failures, "truth_state_unchanged_from_prior", prior.get("truth_state") == TRUTH)

    prior_receipt = load_json(CONTROL / "rebaseline_v2_e4_r2_er1_g1_validation_receipt.json")
    check(checks, failures, "prior_central_validation_passed", prior_receipt.get("passed") is True and prior_receipt.get("failure_count") == 0)

    contract = (CONTROL / "e4_r3_framework_dataset_change_control_contract.md").read_text(encoding="utf-8")
    markers = [
        "User scope decision: `CREATE_NEW_FRAMEWORK_DATASET_ROW`",
        "Execution authority: `DENIED`",
        "`Sol XHigh Standard`",
        "`Sol Max Standard`",
        "`service_tier=standard`",
        "RESULT_STATUS=NOT_RUN",
        "TEST_SET_OPENED=NO",
        "ACCEPTED_RESULT_ROWS=0",
    ]
    check(checks, failures, "contract_policy_markers", all(marker in contract for marker in markers))

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r3-fd0-gate-result-1.0",
        "passed": passed,
        "verdict": "PASS_R3_FD0_GATE_17_OF_17_READY_FOR_FD1" if passed else "FAIL_R3_FD0_GATE_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {"expected": 17, "matched": matched, "strict_json_verified": json_verified},
        "model_policy": {"central": CENTRAL_MODEL, "workers": WORKER_MODEL},
        "superseded_candidate_count": len(archived_ids),
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
